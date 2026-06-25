"""Audio loading and preprocessing utilities."""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
from numpy.typing import NDArray


def load_audio(
    file_path: str | Path, target_sr: int = 44100
) -> tuple[NDArray[np.float32], int]:
    """Load an audio file (MP3/WAV/FLAC) as mono and resample to ``target_sr``."""
    audio, sr = librosa.load(str(file_path), sr=target_sr, mono=True)
    return audio.astype(np.float32), sr


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
    if audio.size < int(round(min_duration * sr)):
        return False
    if not np.any(np.abs(audio) > 0):
        return False
    return True
