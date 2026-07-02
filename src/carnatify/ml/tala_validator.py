"""Evaluate tala detection against Saraga ground-truth annotations."""

from __future__ import annotations

import unicodedata
from typing import Any

import numpy as np

from carnatify.schemas import TalaPrediction

# Canonical tala name -> the set of surface forms that should map to it. Saraga
# annotations use a variety of spellings, transliterations, and full classical
# names (e.g. Adi tala is "Chatusra Jati Triputa"), so each form is normalised
# to a single canonical key before comparison.
_TALA_ALIASES: dict[str, set[str]] = {
    "adi": {
        "adi",
        "adi tala",
        "adi taala",
        "aadi",
        "chatusra jati triputa",
        "chatusra jati triputa tala",
        "chaturasra triputa",
    },
    "rupaka": {
        "rupaka",
        "rupaka tala",
        "roopaka",
        "rupakam",
        "chatusra rupaka",
    },
    "misra chapu": {
        "misra chapu",
        "mishra chapu",
        "misra chaapu",
        "misrachapu",
        "tisra triputa",
    },
    "khanda chapu": {
        "khanda chapu",
        "khanda chaapu",
        "kanda chapu",
        "khandachapu",
    },
}


def normalize_tala_name(name: str) -> str:
    """Reduce a tala name to its canonical key (lowercase canonical form).

    Unrecognised names are returned lowercased and stripped so they can still be
    compared by equality, but they will not match any canonical tala.
    """
    if not name:
        return ""
    # Saraga metadata spells talas with diacritics ("Ādi", "Rūpaka"); fold to
    # ASCII before alias lookup or nothing ever matches.
    folded = "".join(
        c
        for c in unicodedata.normalize("NFD", name)
        if not unicodedata.combining(c)
    )
    key = " ".join(folded.strip().lower().split())
    for canonical, aliases in _TALA_ALIASES.items():
        if key == canonical or key in aliases:
            return canonical
    return key


class TalaValidator:
    """Compare tala predictions against Saraga ground truth."""

    def validate_single(
        self, predicted: TalaPrediction, ground_truth_tala: str
    ) -> bool:
        """Return True when the predicted tala matches the ground truth name."""
        return normalize_tala_name(predicted.tala_name) == normalize_tala_name(
            ground_truth_tala
        )

    def _ground_truth_tala(self, meta: dict[str, Any]) -> str | None:
        """Extract a tala name string from a Saraga track's ``taala`` metadata."""
        taala = meta.get("taala")
        if not taala:
            return None
        if isinstance(taala, str):
            return taala
        if isinstance(taala, dict):
            return taala.get("name")
        if isinstance(taala, (list, tuple)):
            for entry in taala:
                if isinstance(entry, dict) and entry.get("name"):
                    return entry["name"]
                if isinstance(entry, str) and entry:
                    return entry
        return None

    def validate_against_saraga(
        self, saraga_loader: Any, tala_detector: Any
    ) -> dict[str, Any]:
        """Run detection on every annotated Saraga track and score it.

        A track is included only when it carries a ground-truth ``taala`` label.
        Returns aggregate accuracy plus per-track results for inspection.
        """
        from carnatify.audio.feature_extractor import FeatureExtractor

        extractor = FeatureExtractor()
        results: list[dict[str, Any]] = []
        correct = 0
        evaluated = 0

        for meta in saraga_loader.list_tracks():
            track_id = meta["track_id"]
            ground_truth = self._ground_truth_tala(meta)
            if not ground_truth:
                continue

            audio, sr = saraga_loader.get_audio(track_id)
            features = extractor.extract(audio, sr)
            prediction = tala_detector.detect(features)
            is_correct = self.validate_single(prediction, ground_truth)

            evaluated += 1
            correct += int(is_correct)
            results.append(
                {
                    "track_id": track_id,
                    "ground_truth": ground_truth,
                    "predicted": prediction.tala_name,
                    "confidence": prediction.confidence,
                    "correct": is_correct,
                }
            )

        accuracy = correct / evaluated if evaluated else 0.0
        return {
            "accuracy": accuracy,
            "correct": correct,
            "evaluated": evaluated,
            "results": results,
        }
