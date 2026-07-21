"""STATUS: LIVE (production) — handle with sign-off.

This is the raga path currently serving the deployed HF Space via
predict_raga(). The production artifact models/raga_classifier.pkl (~40.5%)
must NOT be overwritten without Deepti's explicit sign-off.

Honest accuracy picture: full-track raga is the strong case (72.8% top-1 /
84.7% top-3, grouped CV, 18 ragas). Short wild clips are weak (9/43 top-1) —
tonic estimation on wild audio is unsolved, and a confident composition match
backfills raga from the registry better than this model predicts it.

The RagaClassifier CNN path in this module is a documented dead end: it
memorized per-recording and sat at chance on validation for 60 epochs. The
binding constraint is tracks per raga, not epochs or architecture.

Refs: handoff_state_and_progress.md sections 2.1 and 4, HANDOFF_RAGA_DATA.md.

High-level raga classification inference API.

Two entry points:
  - RagaClassifier  : PyTorch-based classifier (CNN or TDNN) using AudioFeatures
  - predict_raga()  : sklearn-based function using the joblib pkl models produced
                      by train_raga.py — takes raw F0 arrays directly
"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import numpy as np
from numpy.typing import NDArray
import torch

from carnatify.audio.feature_extractor import FeatureExtractor
from carnatify.config import MODELS_DIR, RAGA_CONFIDENCE_THRESHOLD, TOP_K_RESULTS
from carnatify.schemas import AudioFeatures, RagaPrediction

from carnatify.ml.raga_dataset import RagaLabelEncoder
from carnatify.ml.raga_model import RagaCNN, RagaTDNN
from carnatify.ml.raga_features import extract_features

_MODELS = {"pcd": RagaTDNN, "contour": RagaCNN}


class RagaClassifier:
    """
    STATUS: LIVE (production) — do not overwrite models/raga_classifier.pkl without sign-off. See ARCHITECTURE.md.
    Loads a trained raga model and exposes a simple classification API.

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
        """
        STATUS: LIVE (production) — do not overwrite models/raga_classifier.pkl without sign-off. See ARCHITECTURE.md.
        Return top-K raga predictions for already-extracted features."""
        return self.model.predict(
            features, top_k=self.top_k, label_encoder=self.label_encoder
        )

    def classify_audio(
        self, audio: NDArray[np.float32], sr: int
    ) -> list[RagaPrediction]:
        """
        STATUS: LIVE (production) — do not overwrite models/raga_classifier.pkl without sign-off. See ARCHITECTURE.md.
        Extract features from raw audio, then classify."""
        if self._feature_extractor is None:
            self._feature_extractor = FeatureExtractor()
        features = self._feature_extractor.extract(audio, sr)
        return self.classify(features)

    def is_uncertain(self, predictions: list[RagaPrediction]) -> bool:
        """
        STATUS: LIVE (production) — do not overwrite models/raga_classifier.pkl without sign-off. See ARCHITECTURE.md.
        True if the top prediction falls below the confidence threshold."""
        if not predictions:
            return True
        return predictions[0].confidence < self.confidence_threshold


# ── sklearn-based predict_raga() ──────────────────────────────────────────────

_DEFAULT_MODEL_PATH = MODELS_DIR / "raga_classifier.pkl"
_DEFAULT_ENCODER_PATH = MODELS_DIR / "raga_label_encoder.pkl"


@lru_cache(maxsize=1)
def _load_sklearn_model(model_path: str, encoder_path: str):
    """
    STATUS: LIVE (production) — do not overwrite models/raga_classifier.pkl without sign-off. See ARCHITECTURE.md.
    Load and cache the joblib sklearn bundle (called once per path pair)."""
    import joblib  # optional dep; only needed for sklearn inference

    bundle = joblib.load(model_path)
    le = joblib.load(encoder_path)
    return bundle["model"], le, bundle.get("metadata", {})


def predict_raga(
    frequencies: NDArray[np.float32 | np.float64],
    tonic: float,
    model_path: str | Path = _DEFAULT_MODEL_PATH,
    label_encoder_path: str | Path = _DEFAULT_ENCODER_PATH,
    top_k: int = TOP_K_RESULTS,
) -> list[RagaPrediction]:
    """
    STATUS: LIVE (production) — do not overwrite models/raga_classifier.pkl without sign-off. See ARCHITECTURE.md.
    Return top-k raga predictions from a raw F0 contour.

    Uses the sklearn model produced by ``train_raga.py``, not the PyTorch
    models. Designed for direct use when only a pitch array is available
    (e.g. from mirdata track objects or Essentia output).

    Parameters
    ----------
    frequencies:
        F0 array in Hz (voiced frames > 0; silence / unvoiced = 0 or NaN).
    tonic:
        Estimated tonic frequency in Hz.
    model_path:
        Path to ``raga_classifier.pkl`` (joblib bundle with ``model`` and
        ``metadata`` keys).
    label_encoder_path:
        Path to ``raga_label_encoder.pkl`` (sklearn LabelEncoder).
    top_k:
        Number of predictions to return (default 3).

    Returns
    -------
    Sorted list of :class:`RagaPrediction` (highest confidence first).
    Returns an empty list if the model files are absent or feature extraction
    fails (e.g. clip is too short / all-silence).
    """
    model_path = Path(model_path)
    label_encoder_path = Path(label_encoder_path)

    if not model_path.exists() or not label_encoder_path.exists():
        return []

    feat = extract_features(frequencies, tonic)
    if feat is None:
        return []

    clf, le, meta = _load_sklearn_model(str(model_path), str(label_encoder_path))

    # Some sklearn classifiers expose predict_proba; fall back to a one-hot
    # hard decision if the model was fitted without probability support.
    X = feat.reshape(1, -1)
    if hasattr(clf, "predict_proba"):
        probs = clf.predict_proba(X)[0]
    else:
        idx = int(clf.predict(X)[0])
        probs = np.zeros(len(le.classes_), dtype=np.float64)
        probs[idx] = 1.0

    k = min(top_k, len(probs))
    top_idx = np.argsort(probs)[::-1][:k]

    return [
        RagaPrediction(
            raga_name=str(le.inverse_transform([i])[0]),
            confidence=float(probs[i]),
        )
        for i in top_idx
    ]
