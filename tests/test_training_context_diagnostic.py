import numpy as np
import pytest
from scripts import diagnose_training_audio_context as module


def test_identical_frontends_produce_zero_tonic_difference_and_matching_features(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'sha',lambda p:'fixed')
    f=np.tile(np.r_[np.full(500,220.),np.full(500,247.)],10).astype(np.float32)
    np.save(tmp_path/'contour.npy',f)
    monkeypatch.setattr(module,'extract_query',lambda *a:(f.copy(),{'tonic_hz':220.}))
    row=dict(track='synthetic',label='test',group='one',audio='audio.wav',audio_sha256='fixed',
        contour='contour.npy',contour_sha256='fixed',hop_s=module.HOP_S,tonic=220.)
    result=module.compare(row)
    assert result['tonic_pitch_class_difference_cents']==0
    assert result['pitch_class_agreement_50c']==1
    assert result['feature_cosine']==pytest.approx(1.,abs=1e-6)


def test_changed_training_input_is_rejected_before_dsp(monkeypatch):
    monkeypatch.setattr(module,'sha',lambda p:'changed')
    monkeypatch.setattr(module,'extract_query',lambda *a:pytest.fail('Changed source reached DSP'))
    with pytest.raises(ValueError,match='input changed'):
        module.compare(dict(audio='no.wav',audio_sha256='expected'))
