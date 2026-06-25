"""End-to-end Carnatify inference pipeline wiring every module together.

The pipeline is built to degrade gracefully: if a trained model or reference
catalog is missing, the corresponding stage returns an empty result instead of
raising, so the UI can always render.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from carnatify.audio.catalog import ReferenceCatalog
from carnatify.audio.feature_extractor import FeatureExtractor
from carnatify.config import MODELS_DIR
from carnatify.ml.composition_matcher import CompositionMatcher
from carnatify.ml.raga_classifier import RagaClassifier
from carnatify.ml.tala_detector import TalaDetector
from carnatify.lyrics.database import LyricsDatabase
from carnatify.lyrics.meaning_generator import MeaningGenerator
from carnatify.schemas import (
    AudioFeatures,
    CarnatifyResult,
    CompositionMatch,
    LyricsEntry,
    MeaningEntry,
    RagaPrediction,
    TalaPrediction,
)

RAGA_MODEL_PATH = MODELS_DIR / "raga_model.pt"
RAGA_LABELS_PATH = MODELS_DIR / "raga_labels.json"
REFERENCE_CATALOG_PATH = MODELS_DIR / "reference_catalog.npz"


class CarnatifyPipeline:
    """Single entry point that runs raga, tala, composition, and lyrics stages."""

    def __init__(
        self,
        raga_model_path: str | Path = RAGA_MODEL_PATH,
        raga_labels_path: str | Path = RAGA_LABELS_PATH,
        catalog_path: str | Path = REFERENCE_CATALOG_PATH,
        feature_mode: str = "pcd",
    ):
        self.raga_model_path = Path(raga_model_path)
        self.raga_labels_path = Path(raga_labels_path)
        self.catalog_path = Path(catalog_path)
        self.feature_mode = feature_mode

        self._feature_extractor: FeatureExtractor | None = None
        self._raga_classifier: RagaClassifier | None = None
        self._tala_detector: TalaDetector | None = None
        self._composition_matcher: CompositionMatcher | None = None
        self._meaning_generator: MeaningGenerator | None = None
        self._loaded = False

    # -- lazy loading -------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Initialize every stage once, tolerating missing model artifacts."""
        if self._loaded:
            return

        self._feature_extractor = FeatureExtractor()
        self._tala_detector = TalaDetector()
        self._raga_classifier = self._load_raga_classifier()
        self._composition_matcher = self._load_composition_matcher()
        self._meaning_generator = MeaningGenerator()
        self._loaded = True

    def _load_raga_classifier(self) -> RagaClassifier | None:
        if not (self.raga_model_path.exists() and self.raga_labels_path.exists()):
            return None
        try:
            return RagaClassifier(
                model_path=self.raga_model_path,
                label_encoder_path=self.raga_labels_path,
                feature_mode=self.feature_mode,
            )
        except Exception:
            return None

    def _load_composition_matcher(self) -> CompositionMatcher | None:
        if not self.catalog_path.exists():
            return None
        try:
            catalog = ReferenceCatalog(self.catalog_path)
            catalog.load()
            return CompositionMatcher(catalog)
        except Exception:
            return None

    # -- stages -------------------------------------------------------------

    def _classify_raga(self, features: AudioFeatures) -> list[RagaPrediction]:
        if self._raga_classifier is None:
            return []
        try:
            return self._raga_classifier.classify(features)
        except Exception:
            return []

    def _detect_tala(self, features: AudioFeatures) -> TalaPrediction | None:
        if self._tala_detector is None:
            return None
        try:
            return self._tala_detector.detect(features)
        except Exception:
            return None

    def _match_composition(self, features: AudioFeatures) -> list[CompositionMatch]:
        if self._composition_matcher is None:
            return []
        try:
            return self._composition_matcher.match(features)
        except Exception:
            return []

    def _lookup_lyrics(
        self, matches: list[CompositionMatch]
    ) -> tuple[LyricsEntry | None, MeaningEntry | None]:
        if not matches:
            return None, None

        try:
            with LyricsDatabase() as db:
                entry = db.get_by_id(matches[0].composition_id)
                if entry is None:
                    found = db.search_by_name(matches[0].composition_name)
                    entry = found[0] if found else None
        except Exception:
            return None, None

        if entry is None:
            return None, None

        meaning = self._lookup_meaning(entry)
        return entry, meaning

    def _lookup_meaning(self, entry: LyricsEntry) -> MeaningEntry | None:
        if self._meaning_generator is None:
            return None
        # Prefer a cached meaning; only hit the Claude API if a key is configured.
        cached = self._meaning_generator.get_cached(entry.composition_id)
        if cached is not None:
            return cached
        try:
            return self._meaning_generator.generate(entry)
        except Exception:
            return None

    # -- public API ---------------------------------------------------------

    def run(self, audio: NDArray[np.float32], sr: int) -> CarnatifyResult:
        """Run all stages and return a populated :class:`CarnatifyResult`."""
        self._ensure_loaded()

        features = self._feature_extractor.extract(audio, sr)

        with ThreadPoolExecutor(max_workers=3) as executor:
            raga_future = executor.submit(self._classify_raga, features)
            tala_future = executor.submit(self._detect_tala, features)
            comp_future = executor.submit(self._match_composition, features)

            raga_predictions = raga_future.result()
            tala_prediction = tala_future.result()
            composition_matches = comp_future.result()

        lyrics, meaning = self._lookup_lyrics(composition_matches)

        return CarnatifyResult(
            raga_predictions=raga_predictions,
            tala_prediction=tala_prediction,
            composition_matches=composition_matches,
            lyrics=lyrics,
            meaning=meaning,
        )
