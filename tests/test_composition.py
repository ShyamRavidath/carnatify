"""Tests for DTW matcher, contour preprocessor, and composition matcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from carnatify.ml.contour_preprocessor import ContourPreprocessor
from carnatify.ml.dtw_matcher import DTWMatcher
from carnatify.ml.composition_matcher import CompositionMatcher
from carnatify.schemas import AudioFeatures, CompositionMatch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_features(contour: np.ndarray) -> AudioFeatures:
    return AudioFeatures(
        pitch_contour=np.zeros_like(contour),
        tonic_hz=220.0,
        normalized_pitch_contour=contour.astype(np.float32),
        pitch_class_distribution=np.ones(12, dtype=np.float32) / 12,
        sample_rate=44100,
        duration_seconds=float(contour.size) / 44100,
    )


def _make_catalog(entries: list[dict]) -> MagicMock:
    """Mock ReferenceCatalog returning preset entries."""
    catalog = MagicMock()
    catalog.list_compositions.return_value = entries

    def get_reference(cid):
        for e in entries:
            if e["composition_id"] == cid:
                return _make_features(e["_contour"])
        raise KeyError(cid)

    catalog.get_reference.side_effect = get_reference
    return catalog


# ---------------------------------------------------------------------------
# DTWMatcher
# ---------------------------------------------------------------------------

class TestDTWMatcher:
    def setup_method(self):
        self.matcher = DTWMatcher()

    def test_identical_sequences_distance_zero(self):
        seq = np.array([100.0, 200.0, 300.0, 200.0, 100.0], dtype=np.float32)
        dist = self.matcher.compute_distance(seq, seq)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_different_sequences_positive_distance(self):
        a = np.array([100.0, 200.0, 300.0], dtype=np.float32)
        b = np.array([500.0, 600.0, 700.0], dtype=np.float32)
        assert self.matcher.compute_distance(a, b) > 0

    def test_empty_contour_returns_inf(self):
        empty = np.zeros(10, dtype=np.float32)  # all unvoiced
        voiced = np.array([100.0, 200.0], dtype=np.float32)
        assert self.matcher.compute_distance(empty, voiced) == float("inf")

    def test_similarity_identical_is_one(self):
        seq = np.array([100.0, 200.0, 300.0, 200.0, 100.0], dtype=np.float32)
        sim = self.matcher.compute_similarity(seq, seq)
        assert sim == pytest.approx(1.0, abs=0.01)

    def test_similarity_in_range(self):
        a = np.array([100.0, 200.0, 300.0], dtype=np.float32)
        b = np.array([300.0, 100.0, 200.0], dtype=np.float32)
        sim = self.matcher.compute_similarity(a, b)
        assert 0.0 <= sim <= 1.0

    def test_similarity_decreases_with_divergence(self):
        base = np.array([100.0, 200.0, 300.0, 200.0, 100.0], dtype=np.float32)
        close = base + 10.0
        far = base + 500.0
        sim_close = self.matcher.compute_similarity(base, close)
        sim_far = self.matcher.compute_similarity(base, far)
        assert sim_close > sim_far

    def test_subsequence_match_returns_nonnegative(self):
        query = np.array([200.0, 300.0, 200.0], dtype=np.float32)
        reference = np.array([100.0, 200.0, 300.0, 200.0, 100.0, 50.0], dtype=np.float32)
        score = self.matcher.match_subsequence(query, reference)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# ContourPreprocessor
# ---------------------------------------------------------------------------

class TestContourPreprocessor:
    def setup_method(self):
        self.pp = ContourPreprocessor()

    def test_remove_unvoiced_drops_zeros(self):
        contour = np.array([0.0, 100.0, 200.0, 0.0, 300.0], dtype=np.float32)
        result = self.pp.remove_unvoiced(contour)
        assert (result != 0.0).all()
        assert result.size == 3

    def test_interpolate_fills_interior_zeros(self):
        contour = np.array([100.0, 0.0, 0.0, 400.0], dtype=np.float32)
        result = self.pp.interpolate_unvoiced(contour)
        assert result.size == 4
        assert result[1] > 0.0 and result[2] > 0.0

    def test_smooth_preserves_length(self):
        contour = np.random.rand(100).astype(np.float32) * 1200
        result = self.pp.smooth(contour, window_size=5)
        assert result.size == contour.size

    def test_downsample_reduces_length(self):
        contour = np.ones(100, dtype=np.float32)
        result = self.pp.downsample(contour, factor=4)
        assert result.size == 25

    def test_downsample_factor_1_noop(self):
        contour = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        result = self.pp.downsample(contour, factor=1)
        np.testing.assert_array_equal(result, contour)

    def test_preprocess_pipeline_reduces_size(self):
        contour = np.array([0.0, 100.0, 200.0, 0.0, 300.0, 400.0, 500.0, 600.0], dtype=np.float32)
        result = self.pp.preprocess(contour, remove_silence=True, smooth_window=3, downsample_factor=2)
        # voiced frames = 6, after downsample by 2 = 3
        assert result.size <= contour.size


# ---------------------------------------------------------------------------
# CompositionMatcher
# ---------------------------------------------------------------------------

class TestCompositionMatcher:
    def _make_matcher(self, entries):
        catalog = _make_catalog(entries)
        return CompositionMatcher(catalog=catalog, use_subsequence=False)

    def test_returns_sorted_by_score(self):
        base = np.array([200.0, 300.0, 400.0, 300.0, 200.0] * 10, dtype=np.float32)
        far = np.array([800.0, 900.0, 1000.0, 900.0, 800.0] * 10, dtype=np.float32)

        entries = [
            {"composition_id": "a", "composition_name": "A", "composer": "X", "raga": "R1",
             "tala": "Adi", "_contour": base.copy()},
            {"composition_id": "b", "composition_name": "B", "composer": "X", "raga": "R2",
             "tala": "Adi", "_contour": far.copy()},
        ]
        matcher = self._make_matcher(entries)
        query_features = _make_features(base)
        results = matcher.match(query_features, top_k=2)

        assert len(results) == 2
        assert all(isinstance(r, CompositionMatch) for r in results)
        assert results[0].similarity_score >= results[1].similarity_score

    def test_top_k_respected(self):
        entries = [
            {"composition_id": f"id{i}", "composition_name": f"C{i}", "composer": "X",
             "raga": "R", "tala": "Adi", "_contour": np.ones(50, dtype=np.float32) * (i * 100)}
            for i in range(5)
        ]
        matcher = self._make_matcher(entries)
        query = _make_features(np.ones(50, dtype=np.float32) * 200)
        results = matcher.match(query, top_k=3)
        assert len(results) == 3

    def test_empty_catalog_returns_empty(self):
        catalog = MagicMock()
        catalog.list_compositions.return_value = []
        matcher = CompositionMatcher(catalog=catalog)
        query = _make_features(np.array([100.0, 200.0], dtype=np.float32))
        assert matcher.match(query) == []

    def test_all_unvoiced_query_returns_empty(self):
        entries = [
            {"composition_id": "x", "composition_name": "X", "composer": "Y",
             "raga": "R", "tala": "Adi", "_contour": np.array([100.0, 200.0], dtype=np.float32)},
        ]
        matcher = self._make_matcher(entries)
        query = _make_features(np.zeros(50, dtype=np.float32))
        results = matcher.match(query)
        assert results == []
