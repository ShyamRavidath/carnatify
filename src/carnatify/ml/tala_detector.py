"""High-level tala detection API wrapping :class:`TalaAnalyzer`."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from carnatify.config import TALA_CONFIDENCE_THRESHOLD
from carnatify.schemas import AudioFeatures, TalaPrediction

from carnatify.ml.tala_analyzer import TalaAnalyzer


class TalaDetector:
    """Detect the tala of a clip, applying a confidence threshold."""

    def __init__(
        self,
        analyzer: TalaAnalyzer | None = None,
        confidence_threshold: float = TALA_CONFIDENCE_THRESHOLD,
    ):
        self.analyzer = analyzer or TalaAnalyzer()
        self.confidence_threshold = confidence_threshold

    def detect(self, features: AudioFeatures) -> TalaPrediction:
        """Analyze features; demote low-confidence predictions to 'Unknown'."""
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
        """Convenience: extract features from raw audio, then detect."""
        from carnatify.audio.feature_extractor import FeatureExtractor

        features = FeatureExtractor().extract(audio, sr)
        return self.detect(features)
