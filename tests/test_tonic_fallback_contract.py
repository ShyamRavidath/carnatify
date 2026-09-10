import numpy as np
import pytest
import soundfile as sf
from carnatify.audio import feature_extractor as module
from carnatify.audio.utils import load_audio, load_audio_window


def test_missing_tonic_backend_never_uses_phrase_median(monkeypatch):
    monkeypatch.setattr(module, 'HAS_ESSENTIA', False)
    extractor=module.FeatureExtractor()
    monkeypatch.setattr(extractor, '_pyin_contour',
                        lambda *args: pytest.fail('Pitch tracking cannot establish tonic'))
    with pytest.raises(RuntimeError, match='median pitch is not'):
        extractor._detect_tonic(np.ones(16000,dtype=np.float32),16000)


def test_failed_tonic_backend_never_uses_phrase_median(monkeypatch):
    from types import SimpleNamespace
    def fail(*args,**kwargs):
        raise RuntimeError('estimator failure')
    monkeypatch.setattr(module,'HAS_ESSENTIA',True)
    monkeypatch.setattr(module,'es',SimpleNamespace(TonicIndianArtMusic=fail),raising=False)
    extractor=module.FeatureExtractor()
    monkeypatch.setattr(extractor,'_resample_for_essentia',lambda y,sr:y)
    with pytest.raises(RuntimeError,match='Tonic estimation unavailable'):
        extractor._detect_tonic(np.ones(16000,dtype=np.float32),16000)


def test_full_clip_loader_shares_phase_safe_policy(tmp_path):
    sr=16000
    tone=(.2*np.sin(2*np.pi*220*np.arange(sr)/sr)).astype(np.float32)
    path=tmp_path/'anti_phase.wav'
    sf.write(path,np.c_[tone,-tone],sr,subtype='FLOAT')
    full,rate=load_audio(path,sr)
    bounded,_,diagnostics=load_audio_window(path,0,1,sr)
    assert rate==sr and diagnostics['downmix']=='strongest_channel'
    np.testing.assert_array_equal(full,bounded)
    assert np.sqrt(np.mean(full**2))>.1
