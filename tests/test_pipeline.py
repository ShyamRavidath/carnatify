"""Tests for the end-to-end CarnatifyPipeline runner."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from carnatify.schemas import (
    CarnatifyResult,
    CompositionMatch,
    LyricsEntry,
    MeaningEntry,
    RagaPrediction,
    TalaPrediction,
)
from carnatify.ui.pipeline import CarnatifyPipeline


def _sine_audio(duration: float = 12.0, sr: int = 44100, freq: float = 220.0) -> np.ndarray:
    t = np.linspace(0, duration, int(duration * sr), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


@pytest.fixture
def sine() -> tuple[np.ndarray, int]:
    return _sine_audio(), 44100


def _untrained_pipeline(tmp_path) -> CarnatifyPipeline:
    """Pipeline pointed at non-existent artifacts to force graceful degradation."""
    return CarnatifyPipeline(
        raga_model_path=tmp_path / "missing.pt",
        raga_labels_path=tmp_path / "missing.json",
        catalog_path=tmp_path / "missing.npz",
    )


class TestGracefulDegradation:
    def test_run_without_models_does_not_crash(self, sine, tmp_path):
        audio, sr = sine
        result = _untrained_pipeline(tmp_path).run(audio, sr)
        assert isinstance(result, CarnatifyResult)

    def test_missing_models_yield_empty_lists(self, sine, tmp_path):
        audio, sr = sine
        result = _untrained_pipeline(tmp_path).run(audio, sr)
        assert result.raga_predictions == []
        assert result.composition_matches == []
        assert result.lyrics is None
        assert result.meaning is None

    def test_tala_runs_without_trained_model(self, sine, tmp_path):
        audio, sr = sine
        result = _untrained_pipeline(tmp_path).run(audio, sr)
        # Tala detection is heuristic and always produces a prediction.
        assert result.tala_prediction is None or isinstance(
            result.tala_prediction, TalaPrediction
        )


class TestResultTypes:
    def test_result_field_types_with_mocked_stages(self, sine, tmp_path):
        audio, sr = sine
        pipeline = _untrained_pipeline(tmp_path)
        pipeline._ensure_loaded()

        raga = [RagaPrediction("Kalyani", 0.8), RagaPrediction("Todi", 0.1)]
        tala = TalaPrediction("Adi", 0.7, cycle_duration_seconds=4.0, beats_per_cycle=8)
        match = CompositionMatch("c1", "Vatapi", "Dikshitar", "Hamsadhwani", "Adi", 0.9)
        lyrics = LyricsEntry("c1", "Vatapi", "Dikshitar", "Hamsadhwani", "Adi", "Sanskrit", "Vatapi Ganapatim")
        meaning = MeaningEntry("c1", "A prayer to Ganesha.")

        pipeline._raga_classifier = MagicMock()
        pipeline._raga_classifier.classify.return_value = raga
        pipeline._tala_detector = MagicMock()
        pipeline._tala_detector.detect.return_value = tala
        pipeline._composition_matcher = MagicMock()
        pipeline._composition_matcher.match.return_value = [match]

        db = MagicMock()
        db.__enter__.return_value = db
        db.__exit__.return_value = False
        db.get_by_id.return_value = lyrics
        pipeline._lookup_lyrics = lambda matches: (lyrics, meaning)

        result = pipeline.run(audio, sr)

        assert result.raga_predictions == raga
        assert all(isinstance(r, RagaPrediction) for r in result.raga_predictions)
        assert result.tala_prediction == tala
        assert [m for m in result.composition_matches] == [match]
        assert isinstance(result.composition_matches[0], CompositionMatch)
        assert result.lyrics == lyrics
        assert result.meaning == meaning

    def test_stage_exception_is_isolated(self, sine, tmp_path):
        audio, sr = sine
        pipeline = _untrained_pipeline(tmp_path)
        pipeline._ensure_loaded()

        pipeline._raga_classifier = MagicMock()
        pipeline._raga_classifier.classify.side_effect = RuntimeError("boom")

        # A failing raga stage must not break the whole run.
        result = pipeline.run(audio, sr)
        assert result.raga_predictions == []
        assert isinstance(result, CarnatifyResult)


class TestLyricsLookup:
    def test_no_matches_returns_no_lyrics(self, tmp_path):
        pipeline = _untrained_pipeline(tmp_path)
        pipeline._ensure_loaded()
        assert pipeline._lookup_lyrics([]) == (None, None)
