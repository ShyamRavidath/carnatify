"""Offline, checksum-pinned vocal-separation diagnostic; never a default."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import numpy as np
from .cache_io import atomic_npz
from .melody_frontend import query_contract,HOP_S
from .pitch_profiles import melodia_parameters

CHECKPOINT_SHA256='8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4'
VERSION='htdemucs_955717e8_mono_duplicate_shifts0_melodia_v1'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


class VocalSeparator:
    def __init__(self,checkpoint):
        # Authenticate the publisher-named, locally cached legacy checkpoint
        # before the upstream loader is allowed to deserialize its Python class.
        if digest(checkpoint)!=CHECKPOINT_SHA256:raise ValueError('Demucs checkpoint checksum mismatch')
        from demucs.states import load_model
        self.model=load_model(Path(checkpoint),strict=True).cpu().eval()
        if self.model.samplerate!=44100 or self.model.audio_channels!=2 or 'vocals' not in self.model.sources:
            raise ValueError('Unexpected Demucs model contract')

    def separate(self,audio,sr=44100):
        import torch
        from demucs.apply import apply_model
        y=np.asarray(audio,dtype=np.float32)
        if y.ndim!=1 or not np.isfinite(y).all() or sr!=44100 or not 0<len(y)<=180*sr:
            raise ValueError('Expected a finite bounded 44.1 kHz mono query')
        if np.std(y)<1e-8:return np.zeros_like(y)
        # Independent channels avoid the aliased mono upmix used by old CLIs.
        wave=torch.from_numpy(np.repeat(y[None],2,axis=0))
        ref=wave.mean(0);mean=ref.mean();scale=ref.std()
        wave=(wave-mean)/scale
        with torch.inference_mode():
            sources=apply_model(self.model,wave[None],device='cpu',shifts=0,
                                split=True,overlap=.25,progress=False,num_workers=0)[0]
        vocal=(sources[self.model.sources.index('vocals')]*scale+mean).mean(0).numpy()
        if vocal.shape!=y.shape or not np.isfinite(vocal).all():raise ValueError('Invalid separated vocal')
        return vocal


def cached_query(path,audio_sha256,start_s,duration_s,cache_dir,separator):
    contract=dict(query=query_contract(audio_sha256,start_s,duration_s),version=VERSION,
        checkpoint_sha256=CHECKPOINT_SHA256,shifts=0,overlap=.25,device='cpu',
        demucs_version=importlib.metadata.version('demucs'),torch_version=importlib.metadata.version('torch'),
        hop_s=HOP_S,tonic_policy='retain independently estimated original-mix tonic')
    key=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    target=Path(cache_dir)/(key+'.npz')
    if target.exists():
        with np.load(target,allow_pickle=False) as saved:
            meta=json.loads(str(saved['meta']));f0=saved['f0']
        if meta['contract']!=contract:raise ValueError('Separated pitch cache contract mismatch')
        if f0.ndim!=1 or not np.isfinite(f0).all() or np.any(f0<0):raise ValueError('Invalid separated pitch cache')
        return f0,meta
    from .utils import load_audio_window
    import essentia.standard as es
    y,sr,diagnostics=load_audio_window(path,start_s,duration_s,44100)
    vocal=separator.separate(y,sr)
    f0,_=es.PredominantPitchMelodia(**melodia_parameters())(es.EqualLoudness(sampleRate=sr)(vocal))
    f0=f0[:int(np.ceil(len(vocal)/sr/HOP_S))]
    meta=dict(contract=contract,audio=diagnostics,vocal_sha256=hashlib.sha256(vocal.tobytes()).hexdigest(),
              vocal_rms=float(np.sqrt(np.mean(vocal**2))),mix_rms=float(np.sqrt(np.mean(y**2))))
    atomic_npz(target,f0=f0,meta=json.dumps(meta,allow_nan=False))
    return f0,meta
