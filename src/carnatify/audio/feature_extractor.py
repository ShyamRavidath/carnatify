"""Core audio feature extraction shared across all ML modules.

Internal pitch is always represented in Hz. Cents are only produced when
normalizing a pitch contour relative to the detected tonic. Unvoiced frames are
encoded as a frequency of 0 Hz throughout.
"""

from __future__ import annotations

import librosa
import numpy as np
from numpy.typing import NDArray

from carnatify.schemas import AudioFeatures

try:
    import essentia.standard as es

    HAS_ESSENTIA = True
except ImportError:
    HAS_ESSENTIA = False

# librosa.pyin search range; covers the vocal/instrumental range of Carnatic music.
_PYIN_FMIN = float(librosa.note_to_hz("C2"))
_PYIN_FMAX = float(librosa.note_to_hz("C7"))


class FeatureExtractor:
    """Deterministic feature extractor producing :class:`AudioFeatures`."""

    def __init__(
        self, sample_rate: int = 44100, hop_size: int = 128, frame_size: int = 2048
    ):
        self.sample_rate = sample_rate
        self.hop_size = hop_size
        self.frame_size = frame_size

    def extract(self, audio: NDArray[np.float32], sr: int) -> AudioFeatures:
        """Run the full extraction pipeline on a mono audio clip."""
        audio = np.asarray(audio, dtype=np.float32)

        tonic_hz = self._detect_tonic(audio, sr)
        pitch_contour = self._extract_pitch_contour(audio, sr)
        normalized = self._normalize_pitch_contour(pitch_contour, tonic_hz)
        pcd = self._compute_pitch_class_distribution(normalized)
        beat_times, onset_times = self._detect_beats(audio, sr)

        duration = float(audio.size) / sr if sr else 0.0

        return AudioFeatures(
            pitch_contour=pitch_contour.astype(np.float32),
            tonic_hz=float(tonic_hz),
            normalized_pitch_contour=normalized.astype(np.float32),
            pitch_class_distribution=pcd.astype(np.float32),
            sample_rate=int(sr),
            duration_seconds=duration,
            onset_times=onset_times.astype(np.float32),
            beat_times=beat_times.astype(np.float32),
        )

    def _detect_tonic(self, audio: NDArray[np.float32], sr: int) -> float:
        """Detect the tonic (Sa) frequency in Hz."""
        if HAS_ESSENTIA:
            try:
                resampled = self._resample_for_essentia(audio, sr)
                tonic = es.TonicIndianArtMusic()(resampled)
                if tonic and np.isfinite(tonic) and tonic > 0:
                    return float(tonic)
            except Exception:
                pass
        return self._detect_tonic_librosa(audio, sr)

    def _detect_tonic_librosa(self, audio: NDArray[np.float32], sr: int) -> float:
        """Fallback tonic detection: median of the voiced pyin pitch track."""
        contour = self._pyin_contour(audio, sr)
        voiced = contour[contour > 0]
        if voiced.size == 0:
            return 0.0
        return float(np.median(voiced))

    def _extract_pitch_contour(
        self, audio: NDArray[np.float32], sr: int
    ) -> NDArray[np.float32]:
        """Extract the predominant pitch contour in Hz, 0 for unvoiced frames."""
        if HAS_ESSENTIA:
            try:
                resampled = self._resample_for_essentia(audio, sr)
                pitch, _ = es.PredominantPitchMelodia(
                    hopSize=self.hop_size, frameSize=self.frame_size
                )(resampled)
                contour = np.asarray(pitch, dtype=np.float32)
                contour[~np.isfinite(contour)] = 0.0
                contour[contour < 0] = 0.0
                return contour
            except Exception:
                pass
        return self._pyin_contour(audio, sr)

    def _pyin_contour(
        self, audio: NDArray[np.float32], sr: int
    ) -> NDArray[np.float32]:
        """librosa.pyin pitch track in Hz with unvoiced frames set to 0."""
        if audio.size == 0:
            return np.zeros(0, dtype=np.float32)
        f0, voiced_flag, _ = librosa.pyin(
            audio,
            fmin=_PYIN_FMIN,
            fmax=_PYIN_FMAX,
            sr=sr,
            frame_length=self.frame_size,
            hop_length=self.hop_size,
        )
        contour = np.nan_to_num(f0, nan=0.0).astype(np.float32)
        contour[~np.asarray(voiced_flag, dtype=bool)] = 0.0
        contour[contour < 0] = 0.0
        return contour

    def _normalize_pitch_contour(
        self, contour: NDArray[np.float32], tonic_hz: float
    ) -> NDArray[np.float32]:
        """Convert a Hz contour to cents relative to the tonic.

        cents = 1200 * log2(freq / tonic). Unvoiced frames (freq == 0) stay 0.
        """
        contour = np.asarray(contour, dtype=np.float32)
        normalized = np.zeros_like(contour, dtype=np.float32)
        if tonic_hz <= 0:
            return normalized
        voiced = contour > 0
        normalized[voiced] = 1200.0 * np.log2(contour[voiced] / tonic_hz)
        return normalized

    def _compute_pitch_class_distribution(
        self, normalized_contour: NDArray[np.float32]
    ) -> NDArray[np.float32]:
        """12-bin pitch-class histogram from a cents contour, normalized to sum to 1.

        Each voiced frame is folded into one of 12 semitone bins (mod octave).
        Unvoiced frames (value == 0, the silent baseline) are excluded.
        """
        pcd = np.zeros(12, dtype=np.float32)
        normalized_contour = np.asarray(normalized_contour, dtype=np.float32)
        voiced = normalized_contour != 0
        if not np.any(voiced):
            return pcd
        semitones = normalized_contour[voiced] / 100.0
        pitch_classes = np.mod(np.round(semitones).astype(int), 12)
        for pc in pitch_classes:
            pcd[pc] += 1.0
        total = pcd.sum()
        if total > 0:
            pcd /= total
        return pcd

    def _detect_beats(
        self, audio: NDArray[np.float32], sr: int
    ) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
        """Beat and onset tracking via librosa. Returns ``(beat_times, onset_times)``."""
        if audio.size == 0:
            empty = np.zeros(0, dtype=np.float32)
            return empty, empty.copy()

        onset_env = librosa.onset.onset_strength(
            y=audio, sr=sr, hop_length=self.hop_size
        )
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env, sr=sr, hop_length=self.hop_size
        )
        onset_times = librosa.frames_to_time(
            onset_frames, sr=sr, hop_length=self.hop_size
        ).astype(np.float32)

        _, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env, sr=sr, hop_length=self.hop_size
        )
        beat_times = librosa.frames_to_time(
            beat_frames, sr=sr, hop_length=self.hop_size
        ).astype(np.float32)

        return beat_times, onset_times

    def _resample_for_essentia(
        self, audio: NDArray[np.float32], sr: int
    ) -> NDArray[np.float32]:
        """Essentia pitch algorithms expect the configured sample rate."""
        if sr != self.sample_rate:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sample_rate)
        return np.ascontiguousarray(audio, dtype=np.float32)
