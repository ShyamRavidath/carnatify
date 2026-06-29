"""Match a query pitch contour against the pre-computed reference catalog via DTW."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from carnatify.audio.catalog import ReferenceCatalog
from carnatify.audio.feature_extractor import FeatureExtractor
from carnatify.config import COMPOSITION_CONFIDENCE_THRESHOLD, MODELS_DIR, TOP_K_RESULTS
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


# ── Flat catalog API ──────────────────────────────────────────────────────────
# Append-friendly design: add new data by dropping files in a folder and
# re-running build_catalog.py — no code or schema changes required.

_N_POINTS = 500  # fixed contour length; resampling normalizes tempo differences
_CATALOG_NPZ = MODELS_DIR / "composition_catalog.npz"
_CATALOG_META_JSON = MODELS_DIR / "composition_catalog_meta.json"


def _preprocess_contour(
    frequencies: NDArray,
    tonic: float,
    n_points: int = _N_POINTS,
) -> NDArray[np.float32] | None:
    """Tonic-normalize, resample to n_points, and z-score a pitch contour.

    Returns None when the clip is too short or entirely silent.
    """
    freqs = np.asarray(frequencies, dtype=np.float64)
    voiced = freqs[(freqs > 0) & np.isfinite(freqs)]
    if voiced.size < 50 or tonic <= 0:
        return None

    cents = 1200.0 * np.log2(voiced / float(tonic))

    # Resample to fixed length — this normalizes tempo between renditions so
    # that euclidean distance on the resulting vectors is tempo-invariant.
    x_old = np.linspace(0.0, 1.0, voiced.size)
    x_new = np.linspace(0.0, 1.0, n_points)
    resampled = np.interp(x_new, x_old, cents)

    mu, sigma = resampled.mean(), resampled.std()
    if sigma < 1e-6:
        return None
    return ((resampled - mu) / sigma).astype(np.float32)


def build_catalog(
    tracks_iter,
    catalog_npz: str | Path = _CATALOG_NPZ,
    catalog_meta_json: str | Path = _CATALOG_META_JSON,
) -> int:
    """Build a flat composition catalog from an iterable of track tuples.

    Parameters
    ----------
    tracks_iter:
        Iterable of ``(track_id, title, pitch_frequencies, tonic)`` tuples.
        Accepts any iterable — mirdata tracks, JSON files, generators.
    catalog_npz:
        Output path for the numpy contour array (N × _N_POINTS float32).
    catalog_meta_json:
        Output path for the JSON metadata list (one dict per track).

    Returns
    -------
    Number of tracks successfully indexed.
    """
    catalog_npz = Path(catalog_npz)
    catalog_meta_json = Path(catalog_meta_json)
    catalog_npz.parent.mkdir(parents=True, exist_ok=True)

    contours: list[NDArray[np.float32]] = []
    meta_list: list[dict] = []

    for track_id, title, frequencies, tonic in tracks_iter:
        contour = _preprocess_contour(frequencies, float(tonic))
        if contour is None:
            continue
        contours.append(contour)
        meta_list.append({"track_id": str(track_id), "title": str(title)})

    if not contours:
        return 0

    np.savez_compressed(str(catalog_npz), contours=np.stack(contours, axis=0))
    with open(catalog_meta_json, "w") as f:
        json.dump(meta_list, f, indent=2)

    return len(contours)


@lru_cache(maxsize=1)
def _load_flat_catalog(
    npz_path: str, meta_path: str
) -> tuple[NDArray[np.float32], list[dict]]:
    """Load and in-process-cache the flat catalog."""
    data = np.load(npz_path)
    contours = data["contours"].astype(np.float32)
    with open(meta_path) as f:
        meta = json.load(f)
    return contours, meta


def match_composition(
    frequencies: NDArray,
    tonic: float,
    top_k: int = 5,
    catalog_npz: str | Path = _CATALOG_NPZ,
    catalog_meta_json: str | Path = _CATALOG_META_JSON,
) -> list[tuple[str, float, str]]:
    """Return the top-k compositions matching a pitch contour.

    Similarity is the L2 distance on fixed-length tonic-normalized z-scored
    contours, mapped to ``(0, 1]`` via ``1 / (1 + dist / N_POINTS)``.

    Parameters
    ----------
    frequencies:
        Raw F0 array in Hz (unvoiced = 0 or NaN).
    tonic:
        Tonic frequency in Hz.
    top_k:
        Number of results to return.

    Returns
    -------
    List of ``(title, similarity_score, track_id)`` tuples, sorted by score
    descending.  Empty list when the catalog is absent or the contour is invalid.
    """
    npz = Path(catalog_npz)
    meta_path = Path(catalog_meta_json)

    if not npz.exists() or not meta_path.exists():
        return []

    query = _preprocess_contour(frequencies, tonic)
    if query is None:
        return []

    contours, meta = _load_flat_catalog(str(npz), str(meta_path))

    dists = np.linalg.norm(
        contours.astype(np.float64) - query.astype(np.float64), axis=1
    )
    sims = 1.0 / (1.0 + dists / _N_POINTS)

    k = min(top_k, len(meta))
    top_idx = np.argsort(sims)[::-1][:k]

    return [(meta[i]["title"], float(sims[i]), meta[i]["track_id"]) for i in top_idx]
