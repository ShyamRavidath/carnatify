"""Shared feature-extraction pipeline for the raga classifier retrain.

Runs the ACTUAL production inference pipeline (Demucs vocal separation ->
librosa.pyin) over a real audio file and returns tonic-normalized 480-dim
features for the original clip plus 2 augmented variants (pitch shift +-1
semitone, light white noise), matching backend/main.py's predict_audio
exactly. Shared by train_raga_v2_saraga.py (Saraga Carnatic) and
train_raga_v2_archive.py (shankarkrish.blog / archive.org downloads) so both
real-audio sources feed the same, single feature pipeline.

Must run under venv_train (isolated Python 3.11 env with demucs + pinned
torch==2.5.1/torchaudio==2.5.1 CPU wheels).
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent / "src"))
from carnatify.ml.raga_features import extract_features  # noqa: E402

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


def process_track(track_id: str, raga: str, audio_path: str, cache_dir: Path) -> dict | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{track_id}.npz"
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
    if data.shape[1] == 1:
        # Demucs's own mono->stereo upmix uses tensor.expand(), which creates a
        # memory-aliased view; an in-place op on it later crashes on torch>=2.x
        # with "more than one element of the written-to tensor refers to a
        # single memory location". Writing a real (non-aliased) 2-channel file
        # here sidesteps that entirely.
        data = np.repeat(data, 2, axis=1)

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
