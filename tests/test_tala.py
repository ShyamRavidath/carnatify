"""Tests for the tala detection module."""

from __future__ import annotations

import numpy as np
import pytest

from carnatify.config import TALA_CONFIDENCE_THRESHOLD
from carnatify.schemas import AudioFeatures, TalaPrediction
from carnatify.ml.tala_analyzer import TalaAnalyzer
from carnatify.ml.tala_detector import TalaDetector
from carnatify.ml.tala_validator import TalaValidator, normalize_tala_name


def cyclic_beats(
    beat_interval: float, beats_per_cycle: int, n_cycles: int, accent: float = 0.15
) -> np.ndarray:
    """Build beat times with a metrical accent at each cycle boundary (sama).

    The first beat of every cycle arrives slightly early, mimicking the stronger
    onset detection at the sama. This gives the autocorrelation a real period to
    lock onto, as in actual beat-tracked audio.
    """
    times = []
    t = 0.0
    total_beats = beats_per_cycle * n_cycles
    for i in range(total_beats):
        times.append(t)
        # Shorten the interval just before a downbeat to create periodic accent.
        is_pre_downbeat = (i + 1) % beats_per_cycle == 0
        step = beat_interval * (1.0 - accent) if is_pre_downbeat else beat_interval
        t += step
    return np.asarray(times, dtype=np.float32)


def make_features(beat_times: np.ndarray | None) -> AudioFeatures:
    return AudioFeatures(
        pitch_contour=np.zeros(0, dtype=np.float32),
        tonic_hz=0.0,
        normalized_pitch_contour=np.zeros(0, dtype=np.float32),
        pitch_class_distribution=np.zeros(12, dtype=np.float32),
        sample_rate=22050,
        duration_seconds=0.0,
        onset_times=np.zeros(0, dtype=np.float32),
        beat_times=beat_times,
    )


class TestCycleLength:
    def test_eight_beat_cycle(self):
        analyzer = TalaAnalyzer()
        beats = cyclic_beats(beat_interval=0.5, beats_per_cycle=8, n_cycles=6)
        cycle = analyzer.estimate_cycle_length(beats)
        # Eight beats of ~0.5s, with one shortened, is roughly 3.9s per cycle.
        assert cycle == pytest.approx(3.9, abs=0.4)

    def test_too_few_beats_returns_zero(self):
        analyzer = TalaAnalyzer()
        assert analyzer.estimate_cycle_length(np.array([1.0], dtype=np.float32)) == 0.0

    def test_empty_returns_zero(self):
        analyzer = TalaAnalyzer()
        assert analyzer.estimate_cycle_length(np.zeros(0, dtype=np.float32)) == 0.0


class TestBeatsPerCycle:
    def test_eight_beats_per_cycle(self):
        analyzer = TalaAnalyzer()
        beats = cyclic_beats(beat_interval=0.5, beats_per_cycle=8, n_cycles=6)
        cycle = analyzer.estimate_cycle_length(beats)
        assert analyzer.estimate_beats_per_cycle(beats, cycle) == 8

    def test_seven_beats_per_cycle(self):
        analyzer = TalaAnalyzer()
        beats = cyclic_beats(beat_interval=0.4, beats_per_cycle=7, n_cycles=8)
        cycle = analyzer.estimate_cycle_length(beats)
        assert analyzer.estimate_beats_per_cycle(beats, cycle) == 7

    def test_zero_cycle_duration(self):
        analyzer = TalaAnalyzer()
        beats = cyclic_beats(beat_interval=0.5, beats_per_cycle=8, n_cycles=4)
        assert analyzer.estimate_beats_per_cycle(beats, 0.0) == 0


class TestClassification:
    def test_eight_is_adi(self):
        name, conf = TalaAnalyzer().classify_tala(8, 4.0, 120.0)
        assert name == "Adi"
        assert conf > TALA_CONFIDENCE_THRESHOLD

    def test_seven_is_misra_chapu(self):
        name, _ = TalaAnalyzer().classify_tala(7, 3.5, 120.0)
        assert name == "Misra Chapu"

    def test_five_is_khanda_chapu(self):
        name, _ = TalaAnalyzer().classify_tala(5, 2.5, 120.0)
        assert name == "Khanda Chapu"

    @pytest.mark.parametrize("beats", [3, 6])
    def test_three_and_six_are_rupaka(self, beats):
        name, _ = TalaAnalyzer().classify_tala(beats, 3.0, 120.0)
        assert name == "Rupaka"

    def test_unknown_beat_count(self):
        name, conf = TalaAnalyzer().classify_tala(11, 5.0, 120.0)
        assert name == "Unknown"
        assert conf < TALA_CONFIDENCE_THRESHOLD


class TestAnalyzePipeline:
    def test_adi_end_to_end(self):
        beats = cyclic_beats(beat_interval=0.5, beats_per_cycle=8, n_cycles=6)
        pred = TalaAnalyzer().analyze(make_features(beats))
        assert pred.tala_name == "Adi"
        assert pred.beats_per_cycle == 8
        assert pred.cycle_duration_seconds is not None

    def test_no_beats_is_unknown(self):
        pred = TalaAnalyzer().analyze(make_features(None))
        assert pred.tala_name == "Unknown"
        assert pred.confidence == 0.0


class TestDetectorThreshold:
    def test_low_confidence_becomes_unknown(self):
        # 11 beats/cycle classifies as Unknown with confidence below threshold.
        beats = cyclic_beats(beat_interval=0.5, beats_per_cycle=11, n_cycles=6)
        pred = TalaDetector().detect(make_features(beats))
        assert pred.tala_name == "Unknown"
        assert pred.confidence < TALA_CONFIDENCE_THRESHOLD

    def test_high_confidence_passes_through(self):
        beats = cyclic_beats(beat_interval=0.5, beats_per_cycle=8, n_cycles=6)
        pred = TalaDetector().detect(make_features(beats))
        assert pred.tala_name == "Adi"

    def test_custom_threshold_demotes(self):
        beats = cyclic_beats(beat_interval=0.5, beats_per_cycle=8, n_cycles=6)
        detector = TalaDetector(confidence_threshold=0.99)
        pred = detector.detect(make_features(beats))
        assert pred.tala_name == "Unknown"
        # Underlying analysis metadata is preserved on demotion.
        assert pred.beats_per_cycle == 8


class TestNormalization:
    @pytest.mark.parametrize(
        "raw",
        ["Adi", "adi tala", "Chatusra Jati Triputa", "Chatusra Jati Triputa Tala"],
    )
    def test_adi_aliases(self, raw):
        assert normalize_tala_name(raw) == "adi"

    def test_misra_aliases(self):
        assert normalize_tala_name("Mishra Chapu") == "misra chapu"
        assert normalize_tala_name("Tisra Triputa") == "misra chapu"

    def test_unknown_passthrough(self):
        assert normalize_tala_name("Dhruva") == "dhruva"

    def test_empty(self):
        assert normalize_tala_name("") == ""


class TestValidatorSingle:
    def test_match_across_alias(self):
        validator = TalaValidator()
        pred = TalaPrediction(tala_name="Adi", confidence=0.9)
        assert validator.validate_single(pred, "Chatusra Jati Triputa Tala")

    def test_mismatch(self):
        validator = TalaValidator()
        pred = TalaPrediction(tala_name="Adi", confidence=0.9)
        assert not validator.validate_single(pred, "Misra Chapu")
