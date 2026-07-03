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

# Tonic estimation window — longer than the feature segment because the
# drone-based estimator needs more evidence (87% within ±50 cents at 180s on
# Saraga vs 70% at 60s; the residual errors are Sa/Pa confusions).
TONIC_OFFSET_S = 30.0
TONIC_LEN_S = 180.0
TONIC_MIN_HZ, TONIC_MAX_HZ = 80.0, 400.0


def _pitch_shift_sign(track_id: str) -> int:
    """Deterministic +-1 semitone choice per track (reproducible, no RNG state needed)."""
    h = int(hashlib.sha1(track_id.encode()).hexdigest(), 16)
    return 1 if h % 2 == 0 else -1


def _pyin_frequencies(y: np.ndarray, sr: int) -> np.ndarray:
    f0, voiced_flag, _ = librosa.pyin(y, fmin=PYIN_FMIN, fmax=PYIN_FMAX, sr=sr)
    return f0[voiced_flag].astype(np.float64)


def estimate_tonic_from_mix(audio_path: str) -> float | None:
    """Drone-based tonic (Sa) estimation on the *mixed* recording.

    Must run before vocal separation — Demucs strips the tambura drone the
    estimator relies on. Validated on Saraga annotated tonics: 87% within
    ±50 cents (residual errors are Sa/Pa fifth confusions). The previous
    median-of-voiced-F0 "tonic" was within ±50 cents only 10% of the time,
    which rotated every tonic-normalized feature by a random offset and sank
    the first real-audio retrain (5-9% CV).
    """
    try:
        import essentia.standard as es
    except ImportError:
        return None
    try:
        info = sf.info(audio_path)
        start_s = min(TONIC_OFFSET_S, max(0.0, info.duration - TONIC_LEN_S))
        y, _ = librosa.load(
            audio_path, sr=44100, mono=True, offset=start_s, duration=TONIC_LEN_S
        )
        if len(y) < 44100 * 10:
            return None
        tonic = float(es.TonicIndianArtMusic()(y.astype(np.float32)))
    except Exception:
        return None
    return tonic if TONIC_MIN_HZ <= tonic <= TONIC_MAX_HZ else None


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


def process_track(
    track_id: str,
    raga: str,
    audio_path: str,
    cache_dir: Path,
    tonic_hz: float | None = None,
) -> dict | None:
    """Extract 480-dim features for one track.

    ``tonic_hz``: ground-truth tonic when available (Saraga annotations);
    otherwise the tonic is estimated from the mixed audio via essentia, with
    median-of-voiced-F0 as a last-resort fallback.
    """
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

    frequencies = _pyin_frequencies(y, sr)
    if len(frequencies) < 10:
        return None

    # Tonic: annotated > drone-estimated (on the mix) > median-F0 fallback.
    if tonic_hz is not None:
        tonic, tonic_method = float(tonic_hz), "annotated"
    else:
        est = estimate_tonic_from_mix(audio_path)
        if est is not None:
            tonic, tonic_method = est, "essentia"
        else:
            tonic, tonic_method = float(np.median(frequencies)), "median_f0"

    feat = extract_features(frequencies, tonic)
    if feat is None:
        return None

    # ── Augmentation 1: pitch shift ±1 semitone; the tonic shifts with it ──
    shift = _pitch_shift_sign(track_id)
    y_shift = librosa.effects.pitch_shift(y, sr=sr, n_steps=shift)
    freq_shift = _pyin_frequencies(y_shift, sr)
    tonic_shift = tonic * (2.0 ** (shift / 12.0))
    feat_shift = (
        extract_features(freq_shift, tonic_shift) if len(freq_shift) >= 10 else None
    )

    # ── Augmentation 2: light white noise (~20dB SNR); tonic unchanged ──
    y_noisy = _add_white_noise(y, NOISE_SNR_DB)
    freq_noisy = _pyin_frequencies(y_noisy, sr)
    feat_noisy = (
        extract_features(freq_noisy, tonic) if len(freq_noisy) >= 10 else None
    )

    variants = [("orig", feat, tonic)]
    if feat_shift is not None:
        variants.append(("pitch_shift", feat_shift, tonic_shift))
    if feat_noisy is not None:
        variants.append(("noise", feat_noisy, tonic))

    X = np.stack([v[1] for v in variants])
    kinds = np.array([v[0] for v in variants])
    tonics = np.array([v[2] for v in variants], dtype=np.float64)

    np.savez_compressed(
        cache_path, X=X, kinds=kinds, tonics=tonics,
        raga=raga, track_id=track_id, segment_start_s=start_s,
        frequencies=frequencies, tonic_method=tonic_method,
    )
    return {"status": "ok", "n_variants": len(variants), "tonic_method": tonic_method}
