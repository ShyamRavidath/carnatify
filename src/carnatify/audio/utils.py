"""Audio loading and preprocessing utilities."""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from numpy.typing import NDArray


def load_audio(
    file_path: str | Path, target_sr: int = 44100
) -> tuple[NDArray[np.float32], int]:
    """Load a complete clip using the shared finite/phase-safe downmix policy.

    Concert ingestion must use load_audio_window; this clip convenience API
    intentionally returns the whole decoded recording.
    """
    duration = sf.info(str(file_path)).duration
    audio, sr, _ = load_audio_window(file_path, 0., duration, target_sr)
    return audio, sr


def load_audio_window(file_path: str | Path, start_s: float = 0,
                      duration_s: float = 60, target_sr: int = 44100):
    """Bounded decoding with diagnostics and an anti-phase downmix guard.

    Sample layout is explicitly (frames, channels). No normalization or clipping
    is applied: clipping evidence remains available to the caller.
    """
    if (not np.isfinite(start_s) or start_s < 0 or
            not np.isfinite(duration_s) or duration_s <= 0 or target_sr <= 0):
        raise ValueError("invalid audio window or sample rate")
    with sf.SoundFile(str(file_path)) as f:
        source_sr, channels = f.samplerate, f.channels
        f.seek(min(len(f), round(start_s * source_sr)))
        data = f.read(round(duration_s * source_sr), dtype="float32", always_2d=True)
    mono, diagnostics = phase_safe_mono(data)
    diagnostics['source_sr'] = source_sr
    if source_sr != target_sr:
        mono = librosa.resample(mono, orig_sr=source_sr, target_sr=target_sr)
    return np.ascontiguousarray(mono, dtype=np.float32), target_sr, diagnostics


def phase_safe_mono(data):
    """Downmix finite (frames, channels) audio without phase cancellation."""
    data = np.asarray(data, dtype=np.float32)
    if data.ndim != 2 or not data.size or not np.isfinite(data).all():
        raise ValueError("empty or non-finite audio window")
    channels = data.shape[1]
    power = np.mean(data.astype(np.float64) ** 2, axis=0)
    mono = data.mean(axis=1)
    ratio = float(np.mean(mono.astype(np.float64) ** 2) / max(power.max(), 1e-20))
    cancelled = channels > 1 and power.max() > 1e-12 and ratio < 0.05
    if cancelled:
        mono = data[:, int(power.argmax())]
    diagnostics = dict(channels=channels,
                       downmix="strongest_channel" if cancelled else "mean",
                       downmix_power_ratio=ratio,
                       clipping_fraction=float(np.mean(np.abs(data) >= 0.999)),
                       rms=float(np.sqrt(np.mean(mono.astype(np.float64) ** 2))))
    return np.ascontiguousarray(mono, dtype=np.float32), diagnostics


def load_upload_audio(file_path, target_sr, duration_s):
    """Bounded browser-upload decoder, preserving WebM/audioread fallback.

    Decode native channels before the shared downmix and resample once. Unlike
    whole-clip convenience loading, this API requires an explicit <=180s bound.
    """
    if not np.isfinite(duration_s) or not 0 < duration_s <= 180 or target_sr <= 0:
        raise ValueError('Invalid upload decode bounds')
    audio, source_sr = librosa.load(str(file_path), sr=None, mono=False,
                                    duration=float(duration_s))
    audio = np.asarray(audio)
    if audio.ndim == 1:
        audio = audio[:, None]
    elif audio.ndim == 2:
        audio = audio.T  # librosa uses (channels, frames)
    mono, _ = phase_safe_mono(audio)
    if source_sr != target_sr:
        mono = librosa.resample(mono, orig_sr=source_sr, target_sr=target_sr)
    return np.ascontiguousarray(mono, dtype=np.float32), target_sr


def trim_silence(
    audio: NDArray[np.float32], sr: int, threshold_db: float = -40
) -> NDArray[np.float32]:
    """Trim leading and trailing silence below ``threshold_db`` (relative to peak)."""
    if audio.size == 0:
        return audio
    trimmed, _ = librosa.effects.trim(audio, top_db=-threshold_db)
    return trimmed.astype(np.float32)


def segment_audio(
    audio: NDArray[np.float32], sr: int, segment_duration: float = 30
) -> list[NDArray[np.float32]]:
    """Split audio into consecutive segments of ``segment_duration`` seconds.

    A trailing remainder shorter than the segment length is kept as a final segment.
    """
    segment_len = int(round(segment_duration * sr))
    if segment_len <= 0 or audio.size == 0:
        return []
    return [audio[start : start + segment_len] for start in range(0, audio.size, segment_len)]


def validate_audio(audio: NDArray[np.float32], sr: int, min_duration: float = 10) -> bool:
    """Return True if the clip has enough samples and contains non-silent signal."""
    if audio is None or audio.size == 0:
        return False
    if sr <= 0 or not np.isfinite(audio).all():
        return False
    if audio.size < int(round(min_duration * sr)):
        return False
    if not np.any(np.abs(audio) > 0):
        return False
    return True
