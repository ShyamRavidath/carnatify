import pytest
import numpy as np
from carnatify.audio.pitch_profiles import cache_suffix, melodia_parameters,pitch_audio


def test_default_preserves_cache_and_parameters():
    assert cache_suffix() == 'center60_v1'
    assert melodia_parameters() == dict(sampleRate=44100, frameSize=2048, hopSize=128)


def test_profile_cannot_reuse_default_cache():
    assert cache_suffix('legacy_vocal') != cache_suffix()
    assert melodia_parameters('legacy_vocal')['maxFrequency'] == 900
    with pytest.raises(ValueError):
        melodia_parameters('default', 22050)
    with pytest.raises(ValueError):
        cache_suffix('typo')


def test_duration_has_distinct_cache_contract():
    assert cache_suffix(window_s=180)=='center180_v1'
    assert cache_suffix('legacy_vocal',180)=='center180_legacy_vocal_v1'
    with pytest.raises(ValueError):
        cache_suffix(window_s=60.001)


def test_ten_second_harmonic_profile_preserves_tone_and_reduces_impulses():
    sr=44100;t=np.arange(sr*10)/sr;tone=np.sin(2*np.pi*220*t)
    noise=np.random.default_rng(42).normal(size=len(t))
    impulses=(np.arange(len(t))%(sr//4))<441
    mixed=(.2*tone+.5*noise*impulses).astype(np.float32)
    output=pitch_audio(mixed,'harmonic')
    assert output.shape==mixed.shape and np.isfinite(output).all()
    amplitude=np.dot(output,tone)/np.dot(tone,tone)
    assert amplitude>.1
    assert np.mean((output-amplitude*tone)**2)<np.mean((mixed-.2*tone)**2)
    assert pitch_audio(mixed) is mixed
    assert cache_suffix('harmonic')!=cache_suffix()
