"""Pre-computed reference catalog of composition features."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from carnatify.schemas import AudioFeatures


def _first(value):
    """Return the first element of a list-like annotation, or the value itself."""
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def _name_of(value) -> str:
    """Extract a display name from a mirdata-style annotation entry."""
    entry = _first(value)
    if isinstance(entry, dict):
        return entry.get("name", "") or ""
    return str(entry) if entry is not None else ""


class ReferenceCatalog:
    """Stores and retrieves pre-computed features for reference compositions.

    Features persist as a numpy ``.npz`` archive (the variable-length contours and
    distributions) alongside a sidecar JSON file holding per-composition metadata.
    """

    def __init__(self, catalog_path: str | Path):
        self.catalog_path = Path(catalog_path)
        self._entries: dict[str, dict] = {}

    @property
    def _metadata_path(self) -> Path:
        return self.catalog_path.with_suffix(".json")

    def build_from_saraga(self, saraga_loader, feature_extractor) -> None:
        """Extract and store features for every track in the Saraga loader."""
        for meta in saraga_loader.list_tracks():
            track_id = meta["track_id"]
            try:
                audio, sr = saraga_loader.get_audio(track_id)
                features = feature_extractor.extract(audio, sr)
            except Exception:
                continue

            self._entries[track_id] = {
                "composition_id": track_id,
                "composition_name": meta.get("title") or "",
                "composer": _name_of(meta.get("artists")) or _name_of(meta.get("album_artists")),
                "raga": _name_of(meta.get("raaga")),
                "tala": _name_of(meta.get("taala")),
                "normalized_pitch_contour": features.normalized_pitch_contour,
                "pitch_class_distribution": features.pitch_class_distribution,
            }

    def add_entry(
        self,
        composition_id: str,
        composition_name: str,
        composer: str,
        raga: str,
        tala: str,
        normalized_pitch_contour: NDArray[np.float32],
        pitch_class_distribution: NDArray[np.float32],
    ) -> None:
        """Insert or replace a single catalog entry."""
        self._entries[composition_id] = {
            "composition_id": composition_id,
            "composition_name": composition_name,
            "composer": composer,
            "raga": raga,
            "tala": tala,
            "normalized_pitch_contour": np.asarray(
                normalized_pitch_contour, dtype=np.float32
            ),
            "pitch_class_distribution": np.asarray(
                pitch_class_distribution, dtype=np.float32
            ),
        }

    def save(self) -> None:
        """Persist features to ``.npz`` and metadata to the sidecar JSON file."""
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)

        arrays: dict[str, NDArray] = {}
        metadata: list[dict] = []
        for cid, entry in self._entries.items():
            arrays[f"{cid}::contour"] = entry["normalized_pitch_contour"]
            arrays[f"{cid}::pcd"] = entry["pitch_class_distribution"]
            metadata.append(
                {
                    "composition_id": entry["composition_id"],
                    "composition_name": entry["composition_name"],
                    "composer": entry["composer"],
                    "raga": entry["raga"],
                    "tala": entry["tala"],
                }
            )

        np.savez_compressed(self.catalog_path, **arrays)
        self._metadata_path.write_text(json.dumps(metadata, indent=2))

    def load(self) -> None:
        """Load features and metadata from disk into memory."""
        npz_path = self.catalog_path
        if npz_path.suffix != ".npz":
            npz_path = npz_path.with_suffix(".npz")

        metadata = json.loads(self._metadata_path.read_text())
        archive = np.load(npz_path, allow_pickle=False)

        self._entries = {}
        for meta in metadata:
            cid = meta["composition_id"]
            self._entries[cid] = {
                **meta,
                "normalized_pitch_contour": archive[f"{cid}::contour"],
                "pitch_class_distribution": archive[f"{cid}::pcd"],
            }

    def get_reference(self, composition_id: str) -> AudioFeatures:
        """Return stored features for a composition as an :class:`AudioFeatures`.

        Only the fields persisted in the catalog are populated; the rest carry
        neutral defaults since the catalog stores a reduced feature set.
        """
        entry = self._entries[composition_id]
        contour = np.asarray(entry["normalized_pitch_contour"], dtype=np.float32)
        return AudioFeatures(
            pitch_contour=np.zeros(0, dtype=np.float32),
            tonic_hz=0.0,
            normalized_pitch_contour=contour,
            pitch_class_distribution=np.asarray(
                entry["pitch_class_distribution"], dtype=np.float32
            ),
            sample_rate=0,
            duration_seconds=0.0,
        )

    def list_compositions(self) -> list[dict]:
        """List metadata for all stored compositions."""
        return [
            {
                "composition_id": e["composition_id"],
                "composition_name": e["composition_name"],
                "composer": e["composer"],
                "raga": e["raga"],
                "tala": e["tala"],
            }
            for e in self._entries.values()
        ]
