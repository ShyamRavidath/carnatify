"""STATUS: CLOSED WORKSTREAM — see carnatify.ml.tala_analyzer.

Tala detection measured 16.5% vs a 72% majority baseline and was closed.
This module is the public API wrapper over that dead analyzer.

Refs: handoff_state_and_progress.md section 4.

High-level tala detection API wrapping :class:`TalaAnalyzer`."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from carnatify.config import TALA_CONFIDENCE_THRESHOLD
from carnatify.schemas import AudioFeatures, TalaPrediction

from carnatify.ml.tala_analyzer import TalaAnalyzer


class TalaDetector:
    """
    STATUS: CLOSED WORKSTREAM — tala detection abandoned. See ARCHITECTURE.md.
    Detect the tala of a clip, applying a confidence threshold."""

    def __init__(
        self,
        analyzer: TalaAnalyzer | None = None,
        confidence_threshold: float = TALA_CONFIDENCE_THRESHOLD,
    ):
        self.analyzer = analyzer or TalaAnalyzer()
        self.confidence_threshold = confidence_threshold

    def detect(self, features: AudioFeatures) -> TalaPrediction:
        """
        STATUS: CLOSED WORKSTREAM — tala detection abandoned. See ARCHITECTURE.md.
        Analyze features; demote low-confidence predictions to 'Unknown'."""
        prediction = self.analyzer.analyze(features)
        if prediction.confidence < self.confidence_threshold:
            return TalaPrediction(
                tala_name="Unknown",
                confidence=prediction.confidence,
                cycle_duration_seconds=prediction.cycle_duration_seconds,
                beats_per_cycle=prediction.beats_per_cycle,
            )
        return prediction

    def detect_audio(self, audio: NDArray[np.float32], sr: int) -> TalaPrediction:
        """
        STATUS: CLOSED WORKSTREAM — tala detection abandoned. See ARCHITECTURE.md.
        Convenience: extract features from raw audio, then detect."""
        from carnatify.audio.feature_extractor import FeatureExtractor

        features = FeatureExtractor().extract(audio, sr)
        return self.detect(features)


# ── Standalone function API ───────────────────────────────────────────────────

def detect_tala(audio_path: str | Path) -> dict[str, object]:
    """
    STATUS: CLOSED WORKSTREAM — tala detection abandoned. See ARCHITECTURE.md.
    Detect the tala of an audio file.

    Loads the audio from ``audio_path``, runs librosa beat tracking, then uses
    autocorrelation of inter-beat intervals to estimate the number of beats per
    tala cycle. The beat count is mapped to a named Carnatic tala.

    Parameters
    ----------
    audio_path:
        Path to any audio file supported by librosa (MP3, WAV, FLAC, …).

    Returns
    -------
    dict with keys:
        ``"tala"``           – name string (e.g. ``"Adi"``, ``"Unknown"``)
        ``"beats_per_cycle"``– estimated integer beats per cycle (0 if unknown)
        ``"confidence"``     – float in [0, 1]
    """
    import librosa  # lazy import — not needed unless this function is called

    audio, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    _, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Extended range covers 14-beat Misra cycles; default cap of 12 misses them.
    analyzer = TalaAnalyzer(max_beats_per_cycle=16)
    cycle_duration = analyzer.estimate_cycle_length(beat_times)
    beats_per_cycle = analyzer.estimate_beats_per_cycle(beat_times, cycle_duration)
    tempo_bpm = analyzer.estimate_tempo(beat_times)
    tala_name, confidence = analyzer.classify_tala(beats_per_cycle, cycle_duration, tempo_bpm)

    return {
        "tala": tala_name,
        "beats_per_cycle": beats_per_cycle,
        "confidence": float(confidence),
    }
