"""Feature extraction for Model A: Saraga real-audio training pipeline.

Runs the ACTUAL production inference pipeline (Demucs vocal separation ->
librosa.pyin) over real Saraga Carnatic audio, instead of using any
pre-extracted pitch source. This closes the train/inference domain mismatch
that the original train_raga.py had (it used CompMusic's own pitch
extraction via mirdata's compmusic_raga.track.pitch).

CompMusic's raga-labeled 477-track dataset (compmusic_raga) does NOT have
its raw audio available locally or via mirdata's automated .download() --
audio access there requires an out-of-band request to the CompMusic/Dunya
team. Saraga Carnatic is the one raga-labeled dataset with real audio
already on disk (saraga1.5_carnatic/), so it's used here instead. It is
smaller and sparser per-class (184 labeled tracks over 96 ragas, most with
1-2 tracks) than compmusic_raga's 477 tracks over 40 ragas -- see
train_raga_v2_compmusic.py for a same-augmentation reference point built on
the larger (but pipeline-mismatched) CompMusic pitch data.

Must run under venv_train (isolated Python 3.11 env with demucs + pinned
torch==2.5.1/torchaudio==2.5.1 CPU wheels -- the project's main venv is
Python 3.14, which has no compatible torch/demucs wheels).

Per-track results are cached as individual .npz files under
data/raga_v2_cache/saraga/ so a long run can be safely interrupted and
resumed (already-cached track_ids are skipped).

Usage:
    venv_train/bin/python train_raga_v2_saraga.py [--limit N]
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import librosa
import mirdata
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent / "src"))
from carnatify.ml.raga_features import extract_features  # noqa: E402

ROOT = Path(__file__).parent
CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "saraga"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

SEGMENT_SKIP_S = 30.0     # skip a probable tuning/alapana intro
SEGMENT_LEN_S = 65.0      # ~ the window predict-audio actually analyses (<=60s post-load)
MIN_TRACK_LEN_S = 50.0    # skip tracks too short to get a usable segment
PYIN_FMIN, PYIN_FMAX = 60, 1000
TARGET_SR = 22050
NOISE_SNR_DB = 20.0


def _pitch_shift_sign(track_id: str) -> int:
    """Deterministic +-1 semitone choice per track (reproducible, no RNG state needed)."""
    h = int(hashlib.sha1(track_id.encode()).hexdigest(), 16)
    return 1 if h % 2 == 0 else -1


def _pyin_tonic_and_frequencies(y: np.ndarray, sr: int) -> tuple[float | None, np.ndarray]:
    f0, voiced_flag, _ = librosa.pyin(y, fmin=PYIN_FMIN, fmax=PYIN_FMAX, sr=sr)
    frequencies = f0[voiced_flag].astype(np.float64)
    if len(frequencies) < 10:
        return None, frequencies
    tonic = float(np.median(frequencies))
    return tonic, frequencies


def _add_white_noise(y: np.ndarray, snr_db: float) -> np.ndarray:
    signal_power = float(np.mean(y.astype(np.float64) ** 2)) + 1e-12
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = np.random.default_rng(0).normal(0.0, np.sqrt(noise_power), size=y.shape)
    return (y + noise).astype(np.float32)


def _separate_vocals(audio_path: str, out_dir: str) -> str:
    """Identical to backend/main.py's _separate_vocals_sync."""
    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems=vocals",
        "-n", "htdemucs",
        "-o", out_dir,
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Demucs failed (rc={result.returncode}): {result.stderr[-500:]}")
    track_name = Path(audio_path).stem
    vocal_path = Path(out_dir) / "htdemucs" / track_name / "vocals.wav"
    if not vocal_path.exists():
        raise RuntimeError(f"Vocals file not found at {vocal_path}")
    return str(vocal_path)


def process_track(track_id: str, raga: str, audio_path: str) -> dict | None:
    cache_path = CACHE_DIR / f"{track_id}.npz"
    if cache_path.exists():
        return {"status": "cached"}

    info = sf.info(audio_path)
    if info.duration < MIN_TRACK_LEN_S:
        return None

    start_s = min(SEGMENT_SKIP_S, max(0.0, info.duration - SEGMENT_LEN_S - 1.0))
    seg_len_s = min(SEGMENT_LEN_S, info.duration - start_s)
    start_frame = int(start_s * info.samplerate)
    n_frames = int(seg_len_s * info.samplerate)

    data, sr = sf.read(audio_path, start=start_frame, frames=n_frames, always_2d=True)

    with tempfile.TemporaryDirectory() as tmp_root:
        seg_path = Path(tmp_root) / "segment.wav"
        sf.write(seg_path, data, sr)

        demucs_dir = Path(tmp_root) / "demucs_out"
        vocal_path = _separate_vocals(str(seg_path), str(demucs_dir))

        y, sr = librosa.load(vocal_path, sr=TARGET_SR, mono=True)

    tonic, frequencies = _pyin_tonic_and_frequencies(y, sr)
    if tonic is None:
        return None
    feat = extract_features(frequencies, tonic)
    if feat is None:
        return None

    # ── Augmentation 1: pitch shift +-1 semitone, re-run the full pyin step ──
    shift = _pitch_shift_sign(track_id)
    y_shift = librosa.effects.pitch_shift(y, sr=sr, n_steps=shift)
    tonic_shift, freq_shift = _pyin_tonic_and_frequencies(y_shift, sr)
    feat_shift = extract_features(freq_shift, tonic_shift) if tonic_shift else None

    # ── Augmentation 2: light white noise (~20dB SNR), re-run the full pyin step ──
    y_noisy = _add_white_noise(y, NOISE_SNR_DB)
    tonic_noisy, freq_noisy = _pyin_tonic_and_frequencies(y_noisy, sr)
    feat_noisy = extract_features(freq_noisy, tonic_noisy) if tonic_noisy else None

    variants = [("orig", feat, tonic)]
    if feat_shift is not None:
        variants.append(("pitch_shift", feat_shift, tonic_shift))
    if feat_noisy is not None:
        variants.append(("noise", feat_noisy, tonic_noisy))

    X = np.stack([v[1] for v in variants])
    kinds = np.array([v[0] for v in variants])
    tonics = np.array([v[2] for v in variants], dtype=np.float64)

    np.savez_compressed(
        cache_path, X=X, kinds=kinds, tonics=tonics,
        raga=raga, track_id=track_id, segment_start_s=start_s,
    )
    return {"status": "ok", "n_variants": len(variants)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--min-tracks-per-raga", type=int, default=2)
    args = parser.parse_args()

    ds = mirdata.initialize("saraga_carnatic", data_home=str(ROOT))
    tracks = ds.load_tracks()

    from collections import Counter
    counts = Counter()
    candidates = []
    for tid, t in tracks.items():
        raagas = t.metadata.get("raaga", []) if t.metadata else []
        if not raagas or not t.audio_path:
            continue
        if not Path(t.audio_path).exists():
            continue
        name = raagas[0]["name"]
        counts[name] += 1
        candidates.append((tid, name, t.audio_path))

    keep_ragas = {r for r, n in counts.items() if n >= args.min_tracks_per_raga}
    candidates = [c for c in candidates if c[1] in keep_ragas]
    print(f"Tracks with usable audio+raga: {sum(counts.values())}")
    print(f"Ragas with >= {args.min_tracks_per_raga} tracks: {len(keep_ragas)}  "
          f"({len(candidates)} tracks kept)")

    if args.limit:
        candidates = candidates[: args.limit]

    n_ok, n_skip, n_cached = 0, 0, 0
    t_start = time.time()
    for i, (tid, raga, audio_path) in enumerate(candidates, 1):
        try:
            result = process_track(tid, raga, audio_path)
        except Exception as exc:
            print(f"[{i}/{len(candidates)}] {tid} FAILED: {exc}")
            n_skip += 1
            continue
        if result is None:
            print(f"[{i}/{len(candidates)}] {tid} skipped (too short / unvoiced)")
            n_skip += 1
        elif result["status"] == "cached":
            n_cached += 1
        else:
            n_ok += 1
            elapsed = time.time() - t_start
            print(f"[{i}/{len(candidates)}] {tid} ({raga}) ok, "
                  f"{result['n_variants']} variants, {elapsed:.0f}s elapsed")

    print(f"\nDone. ok={n_ok} cached={n_cached} skipped={n_skip} "
          f"total_time={time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
