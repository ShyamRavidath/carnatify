import numpy as np
import pytest
from carnatify.audio import musicfm_frontend as module


def test_device_policy_is_explicit_and_separately_versioned():
    assert module.encoder_version('cpu')==module.VERSION
    assert module.encoder_version('mps')!=module.VERSION
    with pytest.raises(ValueError,match='Explicit'):
        module.encoder_version('cuda')


def test_differentiable_path_keeps_gradients_but_encode_returns_numpy():
    import torch
    from types import SimpleNamespace
    class Conv(torch.nn.Module):
        def __init__(self):
            super().__init__();self.scale=torch.nn.Parameter(torch.tensor(.1))
        def forward(self,x):
            return torch.ones(1,2,1024)*self.scale*x.mean()
    class Encoder(torch.nn.Module):
        def forward(self,x,output_hidden_states):return {'hidden_states':(x,)*13}
    m=module.MusicFM.__new__(module.MusicFM);m.device='cpu'
    m.stats=dict(melspec_2048_mean=0.,melspec_2048_std=1.)
    m.core=SimpleNamespace(preprocessor_melspec_2048=torch.nn.Identity(),conv=Conv(),conformer=Encoder())
    y=np.ones(24000,dtype=np.float32)
    hidden=m.hidden_tensor(y);hidden.sum().backward()
    assert m.core.conv.scale.grad.item()>0
    np.testing.assert_array_equal(m.encode(y),hidden.detach().numpy())


def test_musicfm_rejects_corrupt_artifacts_before_importing_vendor_code(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'digest',lambda path:'wrong')
    monkeypatch.setattr(module,'_module',lambda *a:pytest.fail('Unverified source executed'))
    with pytest.raises(ValueError,match='checksum'):module.MusicFM(tmp_path)


def test_musicfm_input_is_bounded_and_explicit_rate():
    assert module.validate_waveform(np.zeros(240000),24000).dtype==np.float32
    for y,sr in [(np.zeros(24000),16000),(np.zeros(23999),24000),
                 (np.zeros(720001),24000),(np.zeros((24000,2)),24000),
                 (np.full(24000,np.nan),24000)]:
        with pytest.raises(ValueError):module.validate_waveform(y,sr)


def test_legacy_weight_norm_mapping_preserves_convolution():
    import torch
    from torch import nn
    old=nn.utils.weight_norm(nn.Conv1d(4,4,3),dim=2)
    new=nn.utils.parametrizations.weight_norm(nn.Conv1d(4,4,3),dim=2)
    prefix='conformer.pos_conv_embed.conv.'
    state={prefix+k:v for k,v in old.state_dict().items()}
    expected={prefix+k for k in new.state_dict()}
    mapped=module.migrate_weight_norm(state,expected)
    new.load_state_dict({k[len(prefix):]:v for k,v in mapped.items()},strict=True)
    x=torch.arange(80,dtype=torch.float32).reshape(1,4,20)/80
    torch.testing.assert_close(old(x),new(x))
    assert prefix+'weight_g' in state  # caller state was not mutated


def test_tonic_shift_is_octave_equivalent_and_has_no_fallback():
    for tonic in [110,220,440]:assert module.tonic_shift_steps(tonic)==pytest.approx(0)
    assert module.tonic_shift_steps(220*2**(2/12))==pytest.approx(-2)
    for tonic in [None,0,-1,np.nan,np.inf]:
        with pytest.raises(ValueError):module.tonic_shift_steps(tonic)


def test_tonic_normalization_preserves_length_and_moves_tone_to_reference():
    sr=24000;hz=220*2**(2/12)
    y=(.2*np.sin(2*np.pi*hz*np.arange(sr*2)/sr)).astype(np.float32)
    before=y.copy();shifted,steps=module.tonic_normalize_audio(y,sr,hz)
    assert shifted.shape==y.shape and steps==pytest.approx(-2)
    np.testing.assert_array_equal(y,before)
    spectrum=np.abs(np.fft.rfft(shifted));freq=np.fft.rfftfreq(len(y),1/sr)
    assert freq[spectrum.argmax()]==pytest.approx(220,abs=1)
