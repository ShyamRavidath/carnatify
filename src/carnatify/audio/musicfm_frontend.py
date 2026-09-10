"""Pinned MusicFM encoder pilot; CPU preprocessing, optional MPS backbone."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

VERSION='musicfm_msd_25hz_layer7_cpu_v1'


def encoder_version(device):
    if device not in {'cpu','mps'}:raise ValueError('Explicit CPU or MPS device required')
    return VERSION if device=='cpu' else 'musicfm_msd_25hz_layer7_cpu_mel_mps_backbone_v1'

HASHES={
    'pretrained_msd.pt':'218b483a0256ddef736267425fabb166fd97008983696bb9270def464b47bded',
    'config.json':'7a63cb5706c9a37483f1973a3c226d54eb504ce15cf62cb52637019540c8a75d',
    'msd_stats.json':'c36c61ab10ca4d2e7fdfefc3fcc15205316bec276a06a47baa3641a62c546f22',
    'musicfm/modules/features.py':'aa8e99711f4a4eab522ff89fe86fc27e281e373ed0ae416743736da229f171da',
    'musicfm/modules/conv.py':'585705a6450db374e8c411034e846491f7f48d4ed0516fbf8d3b84855ef0d7d1'}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def validate_waveform(audio,sr):
    y=np.asarray(audio,dtype=np.float32)
    if sr!=24000 or y.ndim!=1 or not 24000<=len(y)<=30*24000 or not np.isfinite(y).all():
        raise ValueError('Expected finite mono 24 kHz audio, 1–30 seconds')
    return np.ascontiguousarray(y)


TONIC_SHIFT_POLICY=dict(reference_hz=220.,octave_policy='nearest_pitch_class_shift_in_[-6,6)',
                        n_fft=2048,hop_length=512,res_type='soxr_hq',scale=False)


def tonic_shift_steps(tonic):
    if tonic is None or not np.isfinite(tonic) or tonic<=0:
        raise ValueError('A finite positive estimated tonic is required')
    return float((-12*np.log2(tonic/220.)+6)%12-6)


def tonic_normalize_audio(audio,sr,tonic):
    """Map estimated Sa's pitch class to A; preserve length and nearest register.

    A controlled experiment, not proof that the estimate is correct or that
    phase-vocoder pitch shifting preserves every Carnatic ornament faithfully.
    """
    y=validate_waveform(audio,sr);steps=tonic_shift_steps(tonic)
    if abs(steps)<1e-6:return y.copy(),steps
    import librosa
    shifted=librosa.effects.pitch_shift(y,sr=sr,n_steps=steps,bins_per_octave=12,
        n_fft=2048,hop_length=512,res_type='soxr_hq',scale=False)
    if shifted.shape!=y.shape or not np.isfinite(shifted).all():
        raise ValueError('Invalid tonic-normalized waveform')
    return np.ascontiguousarray(shifted,dtype=np.float32),steps


def _module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def migrate_weight_norm(state,expected):
    """Exact PyTorch weight-norm state-name migration; no weight approximation."""
    state=dict(state)
    prefix='conformer.pos_conv_embed.conv.'
    for old,new in [('weight_g','parametrizations.weight.original0'),
                    ('weight_v','parametrizations.weight.original1')]:
        old=prefix+old;new=prefix+new
        if old in state and new in expected:
            if new in state:raise ValueError('Duplicate weight-normalization state')
            state[new]=state.pop(old)
    return state


class MusicFM:
    def __init__(self,root,device='cpu'):
        self.version=encoder_version(device);self.device=device
        root=Path(root)
        for name,expected in HASHES.items():
            if digest(root/name)!=expected:raise ValueError(f'MusicFM checksum mismatch: {name}')
        import torch
        if device=='mps' and not torch.backends.mps.is_available():
            raise RuntimeError('MPS unavailable in this execution context; no silent CPU fallback')
        from torch import nn
        from transformers.models.wav2vec2_conformer.modeling_wav2vec2_conformer import Wav2Vec2ConformerEncoder
        from transformers import Wav2Vec2ConformerConfig
        features=_module(root/'musicfm/modules/features.py','_carnatify_musicfm_features')
        conv=_module(root/'musicfm/modules/conv.py','_carnatify_musicfm_conv')
        config=Wav2Vec2ConformerConfig.from_dict(json.loads((root/'config.json').read_text()))
        config.num_hidden_layers=12;config.hidden_size=1024
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(142)
            core=nn.Module()
            core.preprocessor_melspec_2048=features.MelSTFT(n_fft=2048,hop_length=240,is_db=True)
            core.conv=conv.Conv2dSubsampling(1,512,1024,strides=[2,2],n_bands=128)
            core.conformer=Wav2Vec2ConformerEncoder(config)
        with torch.serialization.safe_globals([set]):
            checkpoint=torch.load(root/'pretrained_msd.pt',map_location='cpu',weights_only=True,mmap=True)
        raw=checkpoint['state_dict']
        if not all(k.startswith('model.') for k in raw):raise ValueError('Unexpected checkpoint prefix')
        state={k[6:]:v for k,v in raw.items()}
        expected=set(core.state_dict())
        state=migrate_weight_norm(state,expected)
        extras=set(state)-expected
        allowed={'cls_token','linear.weight','linear.bias',
                 'quantizer_melspec_2048_0.random_projection','quantizer_melspec_2048_0.codebook'}
        if extras!=allowed:raise ValueError(f'Unexpected unused checkpoint state: {extras}')
        core.load_state_dict({k:v for k,v in state.items() if k in expected},strict=True)
        self.core=core.eval().requires_grad_(False)
        if device!='cpu':
            self.core.conv.to(device)
            self.core.conformer.to(device)
        self.stats=json.loads((root/'msd_stats.json').read_text())

    def hidden_tensor(self,audio,sr=24000,layer=7):
        """Differentiable path; parameters remain frozen unless explicitly enabled."""
        y=validate_waveform(audio,sr)
        if not isinstance(layer,int) or not 0<=layer<=12:raise ValueError('Invalid hidden layer')
        import torch
        mel=self.core.preprocessor_melspec_2048(torch.from_numpy(y)[None])[...,:-1]
        mel=(mel-self.stats['melspec_2048_mean'])/self.stats['melspec_2048_std']
        frames=self.core.conv(mel.to(self.device))
        hidden=self.core.conformer(frames,output_hidden_states=True)['hidden_states'][layer]
        if hidden.ndim!=3 or hidden.shape[0]!=1 or hidden.shape[2]!=1024 or not torch.isfinite(hidden).all():
            raise ValueError('Unexpected/nonfinite MusicFM latent layout')
        return hidden[0]

    def encode(self,audio,sr=24000,layer=7):
        import torch
        with torch.inference_mode():
            return self.hidden_tensor(audio,sr,layer).cpu().numpy().copy()
