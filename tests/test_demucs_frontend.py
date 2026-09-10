import numpy as np
import pytest
from carnatify.audio.demucs_frontend import VocalSeparator


def test_checkpoint_rejected_before_deserialization(tmp_path):
    path=tmp_path/'wrong.th';path.write_bytes(b'not a checkpoint')
    with pytest.raises(ValueError,match='checksum'):VocalSeparator(path)


def test_silence_and_invalid_audio_require_no_model_execution():
    separator=object.__new__(VocalSeparator)
    np.testing.assert_array_equal(separator.separate(np.zeros(44100)),np.zeros(44100))
    for audio,sr in [(np.zeros((2,100)),44100),(np.array([np.nan]),44100),(np.ones(100),16000)]:
        with pytest.raises(ValueError,match='bounded'):separator.separate(audio,sr)


def test_normalization_restored_without_mutating_input(monkeypatch):
    import torch
    import demucs.apply
    from types import SimpleNamespace
    separator=object.__new__(VocalSeparator)
    separator.model=SimpleNamespace(sources=['vocals'])
    def apply(model,wave,**kwargs):
        assert kwargs['shifts']==0 and kwargs['split'] and kwargs['num_workers']==0
        assert wave.shape==(1,2,44100)
        return wave[:,None]
    monkeypatch.setattr(demucs.apply,'apply_model',apply)
    y=(.1+.2*np.sin(np.arange(44100)*.1)).astype(np.float32);original=y.copy()
    np.testing.assert_allclose(separator.separate(y),y,rtol=1e-5,atol=1e-7)
    np.testing.assert_array_equal(y,original)
