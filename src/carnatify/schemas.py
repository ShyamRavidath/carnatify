"""Shared data models used across all Carnatify modules."""

from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray


@dataclass
class AudioFeatures:
    """Extracted audio features from a single audio clip."""

    pitch_contour: NDArray[np.float32]
    tonic_hz: float
    normalized_pitch_contour: NDArray[np.float32]
    pitch_class_distribution: NDArray[np.float32]
    sample_rate: int
    duration_seconds: float
    onset_times: NDArray[np.float32] | None = None
    beat_times: NDArray[np.float32] | None = None


@dataclass
class RagaPrediction:
    """A single raga classification result."""

    raga_name: str
    confidence: float


@dataclass
class TalaPrediction:
    """A single tala detection result."""

    tala_name: str
    confidence: float
    cycle_duration_seconds: float | None = None
    beats_per_cycle: int | None = None


@dataclass
class CompositionMatch:
    """A single composition matching result."""

    composition_id: str
    composition_name: str
    composer: str
    raga: str
    tala: str
    similarity_score: float


@dataclass
class LyricsEntry:
    """Lyrics for a single composition."""

    composition_id: str
    composition_name: str
    composer: str
    raga: str
    tala: str
    language: str
    pallavi: str
    anupallavi: str = ""
    charanam: list[str] = field(default_factory=list)
    source: str = ""


@dataclass
class MeaningEntry:
    """English meaning for a composition's lyrics."""

    composition_id: str
    meaning: str
    generated_by: str = "claude"


@dataclass
class CarnatifyResult:
    """Complete result from the Carnatify pipeline."""

    raga_predictions: list[RagaPrediction]
    tala_prediction: TalaPrediction | None
    composition_matches: list[CompositionMatch]
    lyrics: LyricsEntry | None = None
    meaning: MeaningEntry | None = None
