"""Acoustic tonic candidate contracts, independent of any raga classifier."""
import numpy as np
import pytest

from carnatify.audio.tonic_evidence import harmonic_evidence, tonic_candidates


def test_candidates_preserve_pitch_classes_across_octaves():
    expected = tonic_candidates(138.)
    for ratio in (.25, .5, 2, 4):
        actual = tonic_candidates(138. * ratio)
        cents = (1200 * np.log2(actual / expected) + 600) % 1200 - 600
        np.testing.assert_allclose(cents, 0, atol=1e-10)
        assert np.all((actual >= 80) & (actual <= 400))


@pytest.mark.parametrize('base', [0, -1, np.nan, np.inf])
def test_invalid_tonic(base):
    with pytest.raises(ValueError):
        tonic_candidates(base)


def test_ten_second_stationary_harmonics_gain_invariance():
    sr = 11025
    t = np.arange(sr * 10) / sr
    rng = np.random.default_rng(42)
    audio = sum(np.sin(2 * np.pi * 138 * h * t) / h for h in (1, 2, 3, 4))
    audio += .01 * rng.normal(size=len(t))
    candidates, features = harmonic_evidence(audio, sr, 138.)
    _, quieter = harmonic_evidence(audio * .2, sr, 138.)
    assert features.shape == (3, 35)
    assert np.isfinite(features).all()
    np.testing.assert_allclose(features, quieter, atol=.001)
    np.testing.assert_allclose(features[:, -3:], np.eye(3))
    np.testing.assert_allclose(features[:, :-3].mean(0), 0, atol=1e-12)
    # Fundamental's stationary harmonic evidence favors the injected drone;
    # this is a feature sanity check, not a trained-model accuracy assertion.
    assert features[0, 4:8].mean() > features[1:, 4:8].mean()


def test_bad_audio_contract():
    for audio, sr in [(np.zeros(11025), 11025), (np.zeros(22050), 22050),
                      (np.full(22050, np.nan), 11025), (np.zeros((22050, 2)), 11025)]:
        with pytest.raises(ValueError):
            harmonic_evidence(audio, sr, 138.)


def test_guard_never_changes_tonic_without_sufficient_margin():
    from scripts.train_tonic_disambiguator import guarded_choices
    scores = np.array([[0., .1, -.1], [0., 2., 1.], [3., 2., 1.]])
    np.testing.assert_array_equal(guarded_choices(scores, .5), [0, 1, 0])
    np.testing.assert_array_equal(guarded_choices(scores, np.inf), [0, 0, 0])


def test_tonic_cache_contract_tracks_window_and_base():
    from scripts.train_tonic_disambiguator import evidence_contract
    row = dict(audio_sha256='a' * 64, start_s=10., end_s=70., tonic_estimated=138.)
    assert evidence_contract(row) != evidence_contract({**row, 'start_s': 20.})
    assert evidence_contract(row) != evidence_contract({**row, 'tonic_estimated': 184.})
