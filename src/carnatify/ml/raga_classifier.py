"""High-level raga classification inference API."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
import torch

from carnatify.audio.feature_extractor import FeatureExtractor
from carnatify.config import RAGA_CONFIDENCE_THRESHOLD, TOP_K_RESULTS
from carnatify.schemas import AudioFeatures, RagaPrediction

from carnatify.ml.raga_dataset import RagaLabelEncoder
from carnatify.ml.raga_model import RagaCNN, RagaTDNN

_MODELS = {"pcd": RagaTDNN, "contour": RagaCNN}


class RagaClassifier:
    """Loads a trained raga model and exposes a simple classification API.

    Parameters
    ----------
    model_path:
        Path to a saved ``state_dict`` checkpoint.
    label_encoder_path:
        Path to the JSON label encoder saved via :meth:`RagaLabelEncoder.save`.
    feature_mode:
        ``"pcd"`` (TDNN) or ``"contour"`` (CNN); selects the architecture and
        feature representation. Must match what the checkpoint was trained with.
    """

    def __init__(
        self,
        model_path: str | Path,
        label_encoder_path: str | Path,
        feature_mode: str = "pcd",
        device: str | torch.device = "cpu",
        top_k: int = TOP_K_RESULTS,
        confidence_threshold: float = RAGA_CONFIDENCE_THRESHOLD,
    ):
        if feature_mode not in _MODELS:
            raise ValueError(f"Unknown feature mode: {feature_mode!r}")

        self.device = torch.device(device)
        self.feature_mode = feature_mode
        self.top_k = top_k
        self.confidence_threshold = confidence_threshold

        self.label_encoder = RagaLabelEncoder.load(label_encoder_path)
        num_ragas = len(self.label_encoder)

        model_cls = _MODELS[feature_mode]
        self.model = model_cls(num_ragas=num_ragas, label_encoder=self.label_encoder)
        self.model.load(model_path, map_location=str(self.device))
        self.model.to(self.device)
        self.model.eval()

        self._feature_extractor: FeatureExtractor | None = None

    def classify(self, features: AudioFeatures) -> list[RagaPrediction]:
        """Return top-K raga predictions for already-extracted features."""
        return self.model.predict(
            features, top_k=self.top_k, label_encoder=self.label_encoder
        )

    def classify_audio(
        self, audio: NDArray[np.float32], sr: int
    ) -> list[RagaPrediction]:
        """Extract features from raw audio, then classify."""
        if self._feature_extractor is None:
            self._feature_extractor = FeatureExtractor()
        features = self._feature_extractor.extract(audio, sr)
        return self.classify(features)

    def is_uncertain(self, predictions: list[RagaPrediction]) -> bool:
        """True if the top prediction falls below the confidence threshold."""
        if not predictions:
            return True
        return predictions[0].confidence < self.confidence_threshold
