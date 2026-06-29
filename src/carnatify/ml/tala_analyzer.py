"""Rule-based tala analysis from beat-tracking features.

The pipeline estimates the duration of one tala cycle from the periodic
structure of beat intervals, infers how many beats fall within a cycle, and
maps that beat count to a named Carnatic tala. No deep learning is involved.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from carnatify.schemas import AudioFeatures, TalaPrediction

# Mapping from beats-per-cycle to (tala name, base confidence). Adi tala is the
# most common Carnatic tala, so an 8-beat cycle is the most reliable inference.
_BEATS_TO_TALA: dict[int, tuple[str, float]] = {
    8: ("Adi", 0.9),
    14: ("Misra", 0.7),
    7: ("Misra Chapu", 0.75),
    6: ("Rupaka", 0.7),
    5: ("Khanda Chapu", 0.75),
    3: ("Rupaka", 0.65),
}


class TalaAnalyzer:
    """Estimate the metrical cycle of a clip and classify its tala."""

    def __init__(self, min_beats_per_cycle: int = 3, max_beats_per_cycle: int = 12):
        self.min_beats_per_cycle = min_beats_per_cycle
        self.max_beats_per_cycle = max_beats_per_cycle

    def estimate_cycle_length(self, beat_times: NDArray[np.float32]) -> float:
        """Estimate the duration of one tala cycle in seconds.

        Beats are converted to a sequence of inter-beat intervals, and the
        dominant period of that sequence is found via autocorrelation. The lag
        with the strongest correlation (beyond lag 0) gives the number of beats
        per cycle, which scaled by the median interval yields a duration.
        """
        beat_times = np.asarray(beat_times, dtype=np.float64)
        if beat_times.size < 2:
            return 0.0

        intervals = np.diff(beat_times)
        if intervals.size == 0:
            return 0.0

        median_interval = float(np.median(intervals))
        if median_interval <= 0:
            return 0.0

        period = self._dominant_period(intervals)
        if period <= 0:
            # No clear periodicity: fall back to the total span as a single cycle.
            return float(beat_times[-1] - beat_times[0])

        return period * median_interval

    def _dominant_period(self, intervals: NDArray[np.float64]) -> int:
        """Return the dominant period (in beats) of an interval sequence.

        Uses the autocorrelation of the mean-removed interval sequence, scanning
        lags within ``[min_beats_per_cycle, max_beats_per_cycle]`` for the peak.
        Returns 0 when the sequence is too short to expose any period.
        """
        n = intervals.size
        if n < self.min_beats_per_cycle * 2:
            return 0

        centered = intervals - np.mean(intervals)
        norm = float(np.dot(centered, centered))
        if norm <= 0:
            # Perfectly uniform beats carry no metrical accent information.
            return 0

        full = np.correlate(centered, centered, mode="full")
        autocorr = full[full.size // 2:] / norm

        max_lag = min(self.max_beats_per_cycle, n - 1)
        best_lag = 0
        best_score = -np.inf
        for lag in range(self.min_beats_per_cycle, max_lag + 1):
            score = autocorr[lag]
            if score > best_score:
                best_score = score
                best_lag = lag

        # Require a positive correlation to treat the lag as a real period.
        if best_score <= 0:
            return 0
        return best_lag

    def estimate_beats_per_cycle(
        self, beat_times: NDArray[np.float32], cycle_duration: float
    ) -> int:
        """Estimate beats per cycle from cycle duration and median beat interval."""
        beat_times = np.asarray(beat_times, dtype=np.float64)
        if beat_times.size < 2 or cycle_duration <= 0:
            return 0

        intervals = np.diff(beat_times)
        median_interval = float(np.median(intervals))
        if median_interval <= 0:
            return 0

        beats = int(round(cycle_duration / median_interval))
        return max(beats, 0)

    def classify_tala(
        self, beats_per_cycle: int, cycle_duration: float, tempo_bpm: float
    ) -> tuple[str, float]:
        """Map a beat count to a tala name and confidence.

        ``cycle_duration`` and ``tempo_bpm`` are accepted for future refinement
        (e.g. penalising implausibly fast or slow cycles); the MVP classifies
        purely on ``beats_per_cycle``.
        """
        if beats_per_cycle in _BEATS_TO_TALA:
            name, confidence = _BEATS_TO_TALA[beats_per_cycle]
            return name, confidence
        return "Unknown", 0.2

    def estimate_tempo(self, beat_times: NDArray[np.float32]) -> float:
        """Estimate tempo in beats per minute from beat spacing."""
        beat_times = np.asarray(beat_times, dtype=np.float64)
        if beat_times.size < 2:
            return 0.0
        median_interval = float(np.median(np.diff(beat_times)))
        if median_interval <= 0:
            return 0.0
        return 60.0 / median_interval

    def analyze(self, features: AudioFeatures) -> TalaPrediction:
        """Full pipeline: AudioFeatures -> TalaPrediction."""
        beat_times = features.beat_times
        if beat_times is None or np.asarray(beat_times).size < 2:
            return TalaPrediction(tala_name="Unknown", confidence=0.0)

        beat_times = np.asarray(beat_times, dtype=np.float64)
        cycle_duration = self.estimate_cycle_length(beat_times)
        beats_per_cycle = self.estimate_beats_per_cycle(beat_times, cycle_duration)
        tempo_bpm = self.estimate_tempo(beat_times)
        tala_name, confidence = self.classify_tala(
            beats_per_cycle, cycle_duration, tempo_bpm
        )

        return TalaPrediction(
            tala_name=tala_name,
            confidence=confidence,
            cycle_duration_seconds=cycle_duration if cycle_duration > 0 else None,
            beats_per_cycle=beats_per_cycle if beats_per_cycle > 0 else None,
        )
