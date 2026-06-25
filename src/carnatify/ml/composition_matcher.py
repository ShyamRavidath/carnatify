"""Match a query pitch contour against the pre-computed reference catalog via DTW."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from carnatify.audio.catalog import ReferenceCatalog
from carnatify.audio.feature_extractor import FeatureExtractor
from carnatify.config import COMPOSITION_CONFIDENCE_THRESHOLD, TOP_K_RESULTS
from carnatify.ml.contour_preprocessor import ContourPreprocessor
from carnatify.ml.dtw_matcher import DTWMatcher
from carnatify.schemas import AudioFeatures, CompositionMatch


class CompositionMatcher:
    """Match a query AudioFeatures against a reference catalog using DTW."""

    def __init__(
        self,
        catalog: ReferenceCatalog,
        dtw_matcher: DTWMatcher | None = None,
        preprocessor: ContourPreprocessor | None = None,
        use_subsequence: bool = True,
    ):
        self.catalog = catalog
        self.dtw = dtw_matcher or DTWMatcher(window_size=100)
        self.preprocessor = preprocessor or ContourPreprocessor()
        self.use_subsequence = use_subsequence

    def match(
        self, features: AudioFeatures, top_k: int = TOP_K_RESULTS
    ) -> list[CompositionMatch]:
        """Return top-k compositions ranked by DTW similarity."""
        query_contour = self.preprocessor.preprocess(features.normalized_pitch_contour)
        if query_contour.size == 0:
            return []

        results: list[tuple[float, dict]] = []
        for meta in self.catalog.list_compositions():
            composition_id = meta["composition_id"]
            ref_features = self.catalog.get_reference(composition_id)
            ref_contour = self.preprocessor.preprocess(ref_features.normalized_pitch_contour)
            if ref_contour.size == 0:
                continue

            if self.use_subsequence:
                score = self.dtw.match_subsequence(query_contour, ref_contour)
            else:
                score = self.dtw.compute_similarity(query_contour, ref_contour)

            results.append((score, meta))

        results.sort(key=lambda x: x[0], reverse=True)
        top = results[:top_k]

        return [
            CompositionMatch(
                composition_id=meta["composition_id"],
                composition_name=meta.get("composition_name", ""),
                composer=meta.get("composer", ""),
                raga=meta.get("raga", ""),
                tala=meta.get("tala", ""),
                similarity_score=score,
            )
            for score, meta in top
        ]

    def match_audio(
        self, audio: NDArray[np.float32], sr: int, top_k: int = TOP_K_RESULTS
    ) -> list[CompositionMatch]:
        extractor = FeatureExtractor()
        features = extractor.extract(audio, sr)
        return self.match(features, top_k=top_k)
