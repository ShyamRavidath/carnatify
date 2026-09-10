"""Bounded CPU ONNX RMVPE frontend, following the pinned RVC mel/decoder contract.

See THIRD_PARTY_RMVPE.md for attribution, version and license. No remote Python
or pickle is loaded. This frontend is experimental, not the production default.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from .cache_io import atomic_npz

VERSION='rmvpe_onnx_16k_10ms_context1s_v1'
MODEL_SHA256='5370e71ac80af8b4b7c793d27efd51fd8bf962de3a7ede0766dac0befa3660fd'
HOP_S=.01


def log_mel(audio):
    import torch
    import librosa
    audio=np.asarray(audio,dtype=np.float32)
    if audio.ndim!=1 or len(audio)<=512 or not np.isfinite(audio).all():
        raise ValueError('RMVPE expects finite mono 16 kHz audio longer than 512 samples')
    tensor=torch.from_numpy(np.ascontiguousarray(audio))
    spectrum=torch.stft(tensor,n_fft=1024,hop_length=160,win_length=1024,
                        window=torch.hann_window(1024),center=True,return_complex=True)
    magnitude=torch.sqrt(spectrum.real.square()+spectrum.imag.square())
    basis=torch.from_numpy(librosa.filters.mel(sr=16000,n_fft=1024,n_mels=128,
                                             fmin=30,fmax=8000,htk=True))
    return torch.log(torch.clamp(basis@magnitude,min=1e-5)).numpy()[None]


def decode_salience(salience,threshold=.03):
    salience=np.asarray(salience,dtype=np.float32)
    if salience.ndim!=2 or salience.shape[1]!=360 or not np.isfinite(salience).all() or np.any(salience<0):
        raise ValueError('Invalid RMVPE salience')
    if not np.isfinite(threshold) or not 0<=threshold<=1:raise ValueError('Invalid voicing threshold')
    centers=salience.argmax(1)
    neighbors=centers[:,None]+np.arange(-4,5)[None]
    valid=(neighbors>=0)&(neighbors<360)
    indices=np.clip(neighbors,0,359)
    weights=np.take_along_axis(salience,indices,axis=1)*valid
    cents=20*indices+1997.3794084376191
    average=(weights*cents).sum(1)/np.maximum(weights.sum(1),1e-20)
    f0=10*np.exp2(average/1200)
    f0[salience.max(1)<=threshold]=0
    return f0.astype(np.float32)


class RMVPEOnnx:
    def __init__(self,path):
        import onnxruntime as ort
        digest=hashlib.sha256()
        with open(path,'rb') as stream:
            for block in iter(lambda:stream.read(4*1024*1024),b''):digest.update(block)
        if digest.hexdigest()!=MODEL_SHA256:raise ValueError('Unverified RMVPE model artifact')
        options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
        self.input=self.session.get_inputs()[0].name
        self.output=self.session.get_outputs()[0].name

    def _chunk(self,audio):
        mel=log_mel(audio);n=mel.shape[-1]
        mel=np.pad(mel,((0,0),(0,0),(0,(-n)%32)))
        hidden=self.session.run([self.output],{self.input:mel})[0]
        return decode_salience(hidden[0,:n])

    def extract(self,audio,sr=16000):
        audio=np.asarray(audio,dtype=np.float32)
        if sr!=16000 or audio.ndim!=1 or not len(audio) or not np.isfinite(audio).all():
            raise ValueError('RMVPE requires nonempty finite mono 16 kHz input')
        # Ten-second central regions with one second of context on each side.
        # Grid-aligned cuts preserve timestamps and explicit unvoiced frames.
        out=np.zeros(int(np.ceil(len(audio)/160)),dtype=np.float32)
        for start in range(0,len(audio),160000):
            end=min(start+160000,len(audio));left=max(0,start-16000);right=min(len(audio),end+16000)
            clip=audio[left:right]
            if len(clip)<=512:continue
            f0=self._chunk(clip);offset=(start-left)//160;count=int(np.ceil((end-start)/160))
            out[start//160:start//160+count]=f0[offset:offset+count]
        return out


def cached_query(path,audio_sha256,start_s,duration_s,cache_dir,model):
    from .melody_frontend import query_contract
    # Reuse its bound/hash validation, but explicitly replace the DSP contract.
    query_contract(audio_sha256,start_s,duration_s)
    contract=dict(version=VERSION,model_sha256=MODEL_SHA256,audio_sha256=audio_sha256,
                  start_s=float(start_s),duration_s=float(duration_s),hop_s=HOP_S)
    key=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    target=Path(cache_dir)/f'{key}.npz'
    if target.exists():
        with np.load(target,allow_pickle=False) as z:
            if json.loads(str(z['contract']))!=contract:raise ValueError('RMVPE cache mismatch')
            f0=z['f0']
        if f0.ndim!=1 or not np.isfinite(f0).all() or np.any(f0<0):raise ValueError('Invalid cached RMVPE contour')
        return f0,contract
    from .utils import load_audio_window
    audio,sr,_=load_audio_window(path,start_s,duration_s,16000)
    f0=model.extract(audio,sr)
    target.parent.mkdir(parents=True,exist_ok=True)
    atomic_npz(target,f0=f0,contract=json.dumps(contract))
    return f0,contract
