"""Saraga Carnatic dataset loader built on top of mirdata."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

import mirdata

from carnatify.config import SARAGA_DIR


class SaragaLoader:
    """Thin wrapper around mirdata's ``saraga_carnatic`` dataset."""

    def __init__(self, data_dir: str | Path = SARAGA_DIR):
        self.data_dir = Path(data_dir)
        self._dataset = mirdata.initialize(
            "saraga_carnatic", data_home=str(self.data_dir)
        )
        self._tracks = self._dataset.load_tracks()

    def _track_metadata(self, track_id: str, track) -> dict:
        """Build a plain metadata dict from a mirdata track, tolerating missing fields."""
        meta: dict = {"track_id": track_id}
        for attr in ("title", "artists", "raaga", "taala", "form", "work", "album_artists"):
            meta[attr] = getattr(track, attr, None)
        return meta

    def get_track(self, track_id: str) -> dict:
        """Return metadata for a single track."""
        track = self._tracks[track_id]
        return self._track_metadata(track_id, track)

    def list_tracks(self) -> list[dict]:
        """List all tracks with their metadata."""
        return [self._track_metadata(tid, t) for tid, t in self._tracks.items()]

    def _raga_names(self, track) -> list[str]:
        """Extract raga name strings from a track's ``raaga`` annotation."""
        raaga = getattr(track, "raaga", None)
        if not raaga:
            return []
        names: list[str] = []
        for entry in raaga:
            if isinstance(entry, dict):
                name = entry.get("name")
                if name:
                    names.append(name)
            elif entry:
                names.append(str(entry))
        return names

    def get_tracks_by_raga(self, raga_name: str) -> list[dict]:
        """Return metadata for all tracks whose raga matches ``raga_name`` (case-insensitive)."""
        target = raga_name.strip().lower()
        matches = []
        for tid, track in self._tracks.items():
            if any(target == name.strip().lower() for name in self._raga_names(track)):
                matches.append(self._track_metadata(tid, track))
        return matches

    def get_audio(self, track_id: str) -> tuple[NDArray[np.float32], int]:
        """Load the audio for a track as ``(samples, sample_rate)``."""
        track = self._tracks[track_id]
        audio, sr = track.audio
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=0)
        return audio, int(sr)

    def get_annotations(self, track_id: str) -> dict:
        """Load pitch, tonic, and section annotations, returning None for any that are missing."""
        track = self._tracks[track_id]
        annotations: dict = {}

        pitch = getattr(track, "pitch", None)
        if pitch is not None:
            annotations["pitch"] = {
                "times": np.asarray(getattr(pitch, "times", []), dtype=np.float32),
                "frequencies": np.asarray(
                    getattr(pitch, "frequencies", []), dtype=np.float32
                ),
            }
        else:
            annotations["pitch"] = None

        annotations["tonic"] = getattr(track, "tonic", None)

        sections = getattr(track, "sections", None)
        if sections is not None:
            annotations["sections"] = {
                "intervals": np.asarray(getattr(sections, "intervals", []), dtype=np.float32),
                "labels": list(getattr(sections, "labels", []) or []),
            }
        else:
            annotations["sections"] = None

        return annotations
