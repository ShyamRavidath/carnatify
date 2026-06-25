"""Tests for the audio utilities and feature extraction pipeline."""

import numpy as np
import pytest

from carnatify.audio.feature_extractor import FeatureExtractor
from carnatify.audio.utils import segment_audio, validate_audio
from carnatify.schemas import AudioFeatures


def make_sine(freq: float, duration: float, sr: int = 22050) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


class TestTonicNormalization:
    def test_unison_is_zero_cents(self):
        fx = FeatureExtractor()
        contour = np.array([220.0, 220.0], dtype=np.float32)
        out = fx._normalize_pitch_contour(contour, tonic_hz=220.0)
        np.testing.assert_allclose(out, [0.0, 0.0], atol=1e-4)

    def test_octave_is_1200_cents(self):
        fx = FeatureExtractor()
        contour = np.array([440.0], dtype=np.float32)
        out = fx._normalize_pitch_contour(contour, tonic_hz=220.0)
        np.testing.assert_allclose(out, [1200.0], atol=1e-3)

    def test_fifth_is_700_cents_approx(self):
        fx = FeatureExtractor()
        # An equal-tempered perfect fifth is 700 cents (ratio 2^(7/12)).
        freq = 220.0 * 2 ** (7 / 12)
        out = fx._normalize_pitch_contour(np.array([freq], dtype=np.float32), 220.0)
        np.testing.assert_allclose(out, [700.0], atol=1e-2)

    def test_unvoiced_stays_zero(self):
        fx = FeatureExtractor()
        contour = np.array([0.0, 440.0, 0.0], dtype=np.float32)
        out = fx._normalize_pitch_contour(contour, tonic_hz=220.0)
        assert out[0] == 0.0
        assert out[2] == 0.0
        np.testing.assert_allclose(out[1], 1200.0, atol=1e-3)

    def test_zero_tonic_returns_zeros(self):
        fx = FeatureExtractor()
        contour = np.array([220.0, 440.0], dtype=np.float32)
        out = fx._normalize_pitch_contour(contour, tonic_hz=0.0)
        np.testing.assert_array_equal(out, np.zeros(2, dtype=np.float32))


class TestPitchClassDistribution:
    def test_single_class_concentration(self):
        fx = FeatureExtractor()
        # All frames at exactly the tonic (0 cents -> pitch class 0) except unvoiced.
        normalized = np.array([1200.0, 1200.0, 2400.0], dtype=np.float32)
        pcd = fx._compute_pitch_class_distribution(normalized)
        assert pytest.approx(pcd.sum(), abs=1e-6) == 1.0
        assert pcd[0] == 1.0
        assert np.count_nonzero(pcd) == 1

    def test_two_classes_even_split(self):
        fx = FeatureExtractor()
        # 700 cents -> class 7, 1200 cents -> class 0.
        normalized = np.array([700.0, 700.0, 1200.0, 1200.0], dtype=np.float32)
        pcd = fx._compute_pitch_class_distribution(normalized)
        assert pytest.approx(pcd[7], abs=1e-6) == 0.5
        assert pytest.approx(pcd[0], abs=1e-6) == 0.5

    def test_excludes_unvoiced_frames(self):
        fx = FeatureExtractor()
        normalized = np.array([0.0, 0.0, 1200.0], dtype=np.float32)
        pcd = fx._compute_pitch_class_distribution(normalized)
        assert pcd[0] == 1.0
        assert pytest.approx(pcd.sum(), abs=1e-6) == 1.0

    def test_all_unvoiced_returns_zeros(self):
        fx = FeatureExtractor()
        pcd = fx._compute_pitch_class_distribution(np.zeros(5, dtype=np.float32))
        np.testing.assert_array_equal(pcd, np.zeros(12, dtype=np.float32))

    def test_has_twelve_bins(self):
        fx = FeatureExtractor()
        pcd = fx._compute_pitch_class_distribution(np.array([100.0], dtype=np.float32))
        assert pcd.shape == (12,)


class TestAudioUtils:
    def test_validate_audio_too_short(self):
        sr = 22050
        audio = make_sine(440, duration=2, sr=sr)
        assert validate_audio(audio, sr, min_duration=10) is False

    def test_validate_audio_long_enough(self):
        sr = 22050
        audio = make_sine(440, duration=11, sr=sr)
        assert validate_audio(audio, sr, min_duration=10) is True

    def test_validate_audio_empty(self):
        assert validate_audio(np.zeros(0, dtype=np.float32), 22050) is False

    def test_validate_audio_silent(self):
        sr = 22050
        audio = np.zeros(sr * 11, dtype=np.float32)
        assert validate_audio(audio, sr, min_duration=10) is False

    def test_segment_audio_exact_split(self):
        sr = 1000
        audio = np.ones(3000, dtype=np.float32)
        segments = segment_audio(audio, sr, segment_duration=1)
        assert len(segments) == 3
        assert all(len(s) == 1000 for s in segments)

    def test_segment_audio_with_remainder(self):
        sr = 1000
        audio = np.ones(2500, dtype=np.float32)
        segments = segment_audio(audio, sr, segment_duration=1)
        assert len(segments) == 3
        assert len(segments[-1]) == 500

    def test_segment_audio_empty(self):
        assert segment_audio(np.zeros(0, dtype=np.float32), 1000) == []


class TestFeatureExtractor:
    def test_extract_on_sine_wave(self):
        sr = 22050
        audio = make_sine(220.0, duration=3, sr=sr)
        fx = FeatureExtractor(sample_rate=sr)
        features = fx.extract(audio, sr)

        assert isinstance(features, AudioFeatures)
        assert features.sample_rate == sr
        assert pytest.approx(features.duration_seconds, abs=0.05) == 3.0
        assert features.pitch_class_distribution.shape == (12,)
        assert features.tonic_hz > 0
        # A 220 Hz sine should be detected near A3.
        assert 200 < features.tonic_hz < 240

    def test_pcd_sums_to_one_or_zero(self):
        sr = 22050
        audio = make_sine(330.0, duration=3, sr=sr)
        fx = FeatureExtractor(sample_rate=sr)
        features = fx.extract(audio, sr)
        total = features.pitch_class_distribution.sum()
        assert pytest.approx(total, abs=1e-5) == 1.0 or total == 0.0

    def test_deterministic(self):
        sr = 22050
        audio = make_sine(294.0, duration=2, sr=sr)
        fx = FeatureExtractor(sample_rate=sr)
        a = fx.extract(audio, sr)
        b = fx.extract(audio, sr)
        np.testing.assert_array_equal(
            a.pitch_class_distribution, b.pitch_class_distribution
        )
        np.testing.assert_array_equal(a.pitch_contour, b.pitch_contour)
        assert a.tonic_hz == b.tonic_hz
