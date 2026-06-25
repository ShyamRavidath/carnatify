"""Datasets, label encoding, and augmentation for raga classification.

Two feature modes are supported:

* ``"pcd"`` — the 12-bin pitch-class distribution. A compact, octave-folded
  summary that works well as a baseline for the TDNN/MLP classifier.
* ``"contour"`` — fixed-length windows of the normalized (cents) pitch contour,
  consumed by the 1D CNN.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import json
import numpy as np
from numpy.typing import NDArray

import torch
from torch.utils.data import Dataset

from carnatify.schemas import AudioFeatures

Transform = Callable[[NDArray[np.float32]], NDArray[np.float32]]

PCD_BINS = 12
DEFAULT_CONTOUR_LENGTH = 4000


class RagaLabelEncoder:
    """Bidirectional mapping between raga name strings and integer indices.

    Labels are sorted so the index assignment is deterministic regardless of the
    order ragas are first observed.
    """

    def __init__(self, raga_names: Sequence[str] | None = None):
        self._name_to_index: dict[str, int] = {}
        self._index_to_name: list[str] = []
        if raga_names is not None:
            self.fit(raga_names)

    def fit(self, raga_names: Sequence[str]) -> "RagaLabelEncoder":
        unique = sorted({name for name in raga_names})
        self._index_to_name = list(unique)
        self._name_to_index = {name: i for i, name in enumerate(unique)}
        return self

    def encode(self, raga_name: str) -> int:
        try:
            return self._name_to_index[raga_name]
        except KeyError:
            raise KeyError(f"Unknown raga: {raga_name!r}") from None

    def decode(self, index: int) -> str:
        if not 0 <= index < len(self._index_to_name):
            raise IndexError(f"Label index out of range: {index}")
        return self._index_to_name[index]

    def encode_many(self, names: Sequence[str]) -> NDArray[np.int64]:
        return np.array([self.encode(n) for n in names], dtype=np.int64)

    @property
    def classes(self) -> list[str]:
        return list(self._index_to_name)

    def __len__(self) -> int:
        return len(self._index_to_name)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._index_to_name), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "RagaLabelEncoder":
        names = json.loads(Path(path).read_text(encoding="utf-8"))
        encoder = cls()
        encoder._index_to_name = list(names)
        encoder._name_to_index = {name: i for i, name in enumerate(names)}
        return encoder


def fixed_length_contour(
    contour: NDArray[np.float32], length: int = DEFAULT_CONTOUR_LENGTH
) -> NDArray[np.float32]:
    """Crop or zero-pad a 1D contour to ``length`` frames.

    Longer contours are center-cropped; shorter ones are symmetrically padded.
    """
    contour = np.asarray(contour, dtype=np.float32).ravel()
    n = contour.size
    if n == length:
        return contour
    if n > length:
        start = (n - length) // 2
        return contour[start : start + length]
    pad_total = length - n
    left = pad_total // 2
    right = pad_total - left
    return np.pad(contour, (left, right), mode="constant")


def features_to_vector(
    features: AudioFeatures,
    mode: str = "pcd",
    contour_length: int = DEFAULT_CONTOUR_LENGTH,
) -> NDArray[np.float32]:
    """Extract the model input array from :class:`AudioFeatures` for a given mode."""
    if mode == "pcd":
        return np.asarray(features.pitch_class_distribution, dtype=np.float32)
    if mode == "contour":
        return fixed_length_contour(features.normalized_pitch_contour, contour_length)
    raise ValueError(f"Unknown feature mode: {mode!r}")


# --- Augmentation transforms ------------------------------------------------


class PitchShiftPCD:
    """Rotate PCD bins to simulate a tonic shift (circular over the 12 semitones)."""

    def __init__(self, max_shift: int = 11):
        self.max_shift = max_shift

    def __call__(self, x: NDArray[np.float32]) -> NDArray[np.float32]:
        shift = int(np.random.randint(-self.max_shift, self.max_shift + 1))
        return np.roll(x, shift).astype(np.float32)


class PitchShiftContour:
    """Add a constant cents offset to voiced frames (tonic shift in cents space).

    Unvoiced frames (exactly 0) are left untouched so they stay distinguishable.
    """

    def __init__(self, max_cents: float = 100.0):
        self.max_cents = max_cents

    def __call__(self, x: NDArray[np.float32]) -> NDArray[np.float32]:
        offset = float(np.random.uniform(-self.max_cents, self.max_cents))
        out = x.astype(np.float32, copy=True)
        voiced = out != 0
        out[voiced] += offset
        return out


class AddGaussianNoise:
    """Add small zero-mean Gaussian noise."""

    def __init__(self, std: float = 0.01):
        self.std = std

    def __call__(self, x: NDArray[np.float32]) -> NDArray[np.float32]:
        noise = np.random.normal(0.0, self.std, size=x.shape).astype(np.float32)
        return (x + noise).astype(np.float32)


class Compose:
    """Apply a list of transforms left to right."""

    def __init__(self, transforms: Sequence[Transform]):
        self.transforms = list(transforms)

    def __call__(self, x: NDArray[np.float32]) -> NDArray[np.float32]:
        for t in self.transforms:
            x = t(x)
        return x


def default_augmentation(mode: str = "pcd") -> Compose:
    """A reasonable default augmentation pipeline for the given feature mode."""
    if mode == "pcd":
        return Compose([PitchShiftPCD(), AddGaussianNoise(std=0.01)])
    if mode == "contour":
        return Compose([PitchShiftContour(), AddGaussianNoise(std=2.0)])
    raise ValueError(f"Unknown feature mode: {mode!r}")


# --- Dataset ----------------------------------------------------------------


class RagaDataset(Dataset):
    """Raga classification dataset over pre-extracted features.

    Parameters
    ----------
    features_list:
        Either a list of :class:`AudioFeatures` or a list of raw numpy arrays
        already in the chosen feature representation.
    labels:
        Raga name strings (one per item), or pre-encoded integer indices.
    label_encoder:
        Used to convert string labels to indices. Built from ``labels`` if not
        provided and ``labels`` are strings.
    mode:
        ``"pcd"`` or ``"contour"`` — selects which feature is fed to the model.
    transform:
        Optional augmentation applied to the feature array (training only).
    """

    def __init__(
        self,
        features_list: Sequence[AudioFeatures] | Sequence[NDArray[np.float32]],
        labels: Sequence[str] | Sequence[int],
        label_encoder: RagaLabelEncoder | None = None,
        mode: str = "pcd",
        transform: Transform | None = None,
        contour_length: int = DEFAULT_CONTOUR_LENGTH,
    ):
        if len(features_list) != len(labels):
            raise ValueError("features_list and labels must have the same length")
        if mode not in ("pcd", "contour"):
            raise ValueError(f"Unknown feature mode: {mode!r}")

        self.mode = mode
        self.transform = transform
        self.contour_length = contour_length
        self._vectors = [self._to_vector(f) for f in features_list]

        string_labels = len(labels) > 0 and isinstance(labels[0], str)
        if string_labels:
            if label_encoder is None:
                label_encoder = RagaLabelEncoder(list(labels))  # type: ignore[arg-type]
            self.label_encoder = label_encoder
            self.labels = label_encoder.encode_many(list(labels))  # type: ignore[arg-type]
        else:
            self.label_encoder = label_encoder or RagaLabelEncoder()
            self.labels = np.asarray(labels, dtype=np.int64)

    def _to_vector(self, item) -> NDArray[np.float32]:
        if isinstance(item, AudioFeatures):
            return features_to_vector(item, self.mode, self.contour_length)
        arr = np.asarray(item, dtype=np.float32)
        if self.mode == "contour":
            return fixed_length_contour(arr, self.contour_length)
        return arr

    @property
    def num_classes(self) -> int:
        return len(self.label_encoder)

    def __len__(self) -> int:
        return len(self._vectors)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self._vectors[idx]
        if self.transform is not None:
            x = self.transform(x)
        x = np.asarray(x, dtype=np.float32)
        if self.mode == "contour":
            # CNN expects a channel dimension: (1, length).
            x = x[np.newaxis, :]
        return torch.from_numpy(x), torch.tensor(int(self.labels[idx]), dtype=torch.long)
