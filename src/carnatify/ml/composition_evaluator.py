"""Evaluation utilities for the composition matching pipeline."""

from __future__ import annotations

from carnatify.audio.catalog import ReferenceCatalog
from carnatify.audio.feature_extractor import FeatureExtractor
from carnatify.audio.data_loader import SaragaLoader
from carnatify.ml.composition_matcher import CompositionMatcher
from carnatify.schemas import AudioFeatures


class CompositionEvaluator:
    """Benchmark the composition matcher on a labeled test set."""

    def evaluate(
        self,
        matcher: CompositionMatcher,
        test_pairs: list[tuple[AudioFeatures, str]],
    ) -> dict:
        """Compute top-1, top-3 accuracy and mean reciprocal rank.

        Args:
            matcher: Configured CompositionMatcher with catalog loaded.
            test_pairs: List of (query_features, correct_composition_id).

        Returns:
            Dict with keys: top1_accuracy, top3_accuracy, mrr, n_queries.
        """
        top1_hits = 0
        top3_hits = 0
        reciprocal_ranks: list[float] = []

        for features, correct_id in test_pairs:
            matches = matcher.match(features, top_k=max(3, len(matcher.catalog.list_compositions())))
            ids = [m.composition_id for m in matches]

            if ids and ids[0] == correct_id:
                top1_hits += 1

            if correct_id in ids[:3]:
                top3_hits += 1

            if correct_id in ids:
                rank = ids.index(correct_id) + 1
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)

        n = len(test_pairs)
        return {
            "n_queries": n,
            "top1_accuracy": top1_hits / n if n > 0 else 0.0,
            "top3_accuracy": top3_hits / n if n > 0 else 0.0,
            "mrr": sum(reciprocal_ranks) / n if n > 0 else 0.0,
        }

    def cross_rendition_test(
        self,
        saraga_loader: SaragaLoader,
        feature_extractor: FeatureExtractor,
        matcher: CompositionMatcher,
    ) -> dict:
        """Use one rendition as query, others as reference, report accuracy.

        Groups Saraga tracks by composition name. For any composition with
        ≥2 renditions, uses the first as the reference and the rest as queries.
        """
        tracks = saraga_loader.list_tracks()

        # Group by composition name (title)
        by_composition: dict[str, list[dict]] = {}
        for track in tracks:
            name = track.get("title") or track.get("composition_name") or "unknown"
            by_composition.setdefault(name, []).append(track)

        test_pairs: list[tuple[AudioFeatures, str]] = []
        for name, group in by_composition.items():
            if len(group) < 2:
                continue
            for track in group[1:]:
                try:
                    audio, sr = saraga_loader.get_audio(track["track_id"])
                    features = feature_extractor.extract(audio, sr)
                    # composition_id in the catalog is keyed by the first rendition's id
                    reference_id = group[0]["track_id"]
                    test_pairs.append((features, reference_id))
                except Exception:
                    continue

        if not test_pairs:
            return {"n_queries": 0, "top1_accuracy": 0.0, "top3_accuracy": 0.0, "mrr": 0.0}

        return self.evaluate(matcher, test_pairs)
