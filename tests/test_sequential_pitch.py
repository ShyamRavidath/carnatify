import numpy as np
import pytest
from carnatify.ml.sequential_pitch import sequential_pitch_distribution


def hz(cents):
    return 138.*2**(np.asarray(cents)/1200)


def test_shape_normalization_and_tonic_invariance():
    f=np.r_[hz(np.arange(0,701,10)),np.zeros(20),hz(np.arange(700,-1,-10))]
    expected=sequential_pitch_distribution(f,138.)
    assert expected.shape==(12,12,2,120)
    np.testing.assert_allclose(expected.sum(-1),1,atol=1e-6)
    actual=sequential_pitch_distribution(f*2**(.31),138.*2**(.31))
    np.testing.assert_allclose(actual,expected,atol=1e-6)


def test_direction_and_silence_change_excursion_not_global_pitch():
    a=hz([0,100,200,400,700])
    # Include a separate high-pitch dwell to distinguish fallback distribution.
    f=np.r_[a,hz(np.full(10,1000))]
    split=np.insert(f,2,0.)
    forward=sequential_pitch_distribution(f,138.,relaxation=0)
    interrupted=sequential_pitch_distribution(split,138.,relaxation=0)
    assert forward[0,7,0,100]==0
    assert interrupted[0,7,0,100]>0  # Broken excursion falls back to global PD.


def test_silence_is_not_sa_and_invalid_parameters_fail():
    assert not sequential_pitch_distribution(np.zeros(10),138.).any()
    with pytest.raises(ValueError):sequential_pitch_distribution(hz([0]),np.nan)
