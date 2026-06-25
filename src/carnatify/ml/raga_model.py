"""Raga classification model architectures (CNN over contour, TDNN/MLP over PCD)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from carnatify.config import TOP_K_RESULTS
from carnatify.schemas import AudioFeatures, RagaPrediction

from carnatify.ml.raga_dataset import (
    DEFAULT_CONTOUR_LENGTH,
    PCD_BINS,
    RagaLabelEncoder,
    features_to_vector,
)


def _topk_predictions(
    probs: np.ndarray,
    label_encoder: RagaLabelEncoder | None,
    top_k: int,
) -> list[RagaPrediction]:
    """Build sorted :class:`RagaPrediction` list from a 1D probability vector."""
    probs = np.asarray(probs, dtype=np.float32).ravel()
    k = min(top_k, probs.size)
    top_idx = np.argsort(probs)[::-1][:k]
    predictions = []
    for idx in top_idx:
        if label_encoder is not None and len(label_encoder) > 0:
            name = label_encoder.decode(int(idx))
        else:
            name = str(int(idx))
        predictions.append(RagaPrediction(raga_name=name, confidence=float(probs[idx])))
    return predictions


class _RagaModelMixin:
    """Shared save/load and predict logic for both architectures."""

    feature_mode: str = "pcd"

    def set_label_encoder(self, encoder: RagaLabelEncoder | None) -> None:
        self.label_encoder = encoder

    def _input_tensor(self, features: AudioFeatures) -> torch.Tensor:
        vec = features_to_vector(features, self.feature_mode)
        tensor = torch.from_numpy(np.asarray(vec, dtype=np.float32))
        if self.feature_mode == "contour":
            tensor = tensor.unsqueeze(0).unsqueeze(0)  # (1, 1, length)
        else:
            tensor = tensor.unsqueeze(0)  # (1, dim)
        return tensor

    @torch.no_grad()
    def predict(
        self,
        features: AudioFeatures,
        top_k: int = TOP_K_RESULTS,
        label_encoder: RagaLabelEncoder | None = None,
    ) -> list[RagaPrediction]:
        """Return the top-``k`` raga predictions sorted by descending confidence."""
        self.eval()  # type: ignore[attr-defined]
        encoder = label_encoder or getattr(self, "label_encoder", None)
        x = self._input_tensor(features)
        logits = self(x)  # type: ignore[operator]
        probs = F.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
        return _topk_predictions(probs, encoder, top_k)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.state_dict(), path)  # type: ignore[attr-defined]

    def load(self, path: str | Path, map_location: str = "cpu") -> None:
        state = torch.load(Path(path), map_location=map_location)
        self.load_state_dict(state)  # type: ignore[attr-defined]


class RagaCNN(_RagaModelMixin, nn.Module):
    """1D CNN over a fixed-length normalized pitch contour."""

    feature_mode = "contour"

    def __init__(
        self,
        num_ragas: int,
        input_length: int = DEFAULT_CONTOUR_LENGTH,
        channels: tuple[int, int, int] = (16, 32, 64),
        label_encoder: RagaLabelEncoder | None = None,
    ):
        super().__init__()
        self.num_ragas = num_ragas
        self.input_length = input_length
        self.label_encoder = label_encoder

        c1, c2, c3 = channels
        self.block1 = self._conv_block(1, c1)
        self.block2 = self._conv_block(c1, c2)
        self.block3 = self._conv_block(c2, c3)
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(c3, c3),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(c3, num_ragas),
        )

    @staticmethod
    def _conv_block(in_ch: int, out_ch: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv1d(in_ch, out_ch, kernel_size=7, padding=3),
            nn.BatchNorm1d(out_ch),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=4),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 2:
            x = x.unsqueeze(1)  # (batch, length) -> (batch, 1, length)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.global_pool(x).squeeze(-1)  # (batch, channels)
        return self.fc(x)


class RagaTDNN(_RagaModelMixin, nn.Module):
    """MLP/TDNN baseline over the 12-bin pitch-class distribution."""

    feature_mode = "pcd"

    def __init__(
        self,
        num_ragas: int,
        input_dim: int = PCD_BINS,
        hidden_dims: tuple[int, int] = (128, 64),
        dropout: float = 0.3,
        label_encoder: RagaLabelEncoder | None = None,
    ):
        super().__init__()
        self.num_ragas = num_ragas
        self.input_dim = input_dim
        self.label_encoder = label_encoder

        h1, h2 = hidden_dims
        self.net = nn.Sequential(
            nn.Linear(input_dim, h1),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(h1, h2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(h2, num_ragas),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
