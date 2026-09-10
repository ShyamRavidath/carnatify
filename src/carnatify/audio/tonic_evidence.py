"""Stationary harmonic evidence for Sa/Pa ambiguity; no raga scores enter it."""
import numpy as np
from scipy.signal import stft
from scipy.ndimage import median_filter

TONIC_EVIDENCE_VERSION='stationary_harmonics_11025_v1'
HARMONICS=(.5,1.,1.5,2.,3.,4.,6.,8.)


def tonic_candidates(base):
    if not np.isfinite(base) or base<=0:raise ValueError('Invalid base tonic')
    result=base*2**(np.array([0.,5.,7.])/12)
    while np.any(result>400):result=np.where(result>400,result/2,result)
    while np.any(result<80):result=np.where(result<80,result*2,result)
    return result


def harmonic_evidence(audio,sr,base):
    x=np.asarray(audio,dtype=np.float32)
    if sr!=11025 or x.ndim!=1 or len(x)<sr*2 or not np.isfinite(x).all():
        raise ValueError('Expected at least two seconds of finite mono 11025 Hz audio')
    frequencies,_,s=stft(x,fs=sr,nperseg=16384,noverlap=16384-2756,boundary=None,padded=False)
    power=np.abs(s)**2
    profiles=np.r_[np.quantile(power,[.1,.5,.9],axis=1),power.mean(axis=1)[None]]
    whitened=np.log1p(np.minimum(1000,profiles/(median_filter(profiles,size=(1,31))+1e-15)))
    candidates=tonic_candidates(base);features=[]
    for candidate in candidates:
        parts=[]
        for h in HARMONICS:
            center=candidate*h;lo=center*2**(-35/1200);hi=center*2**(35/1200)
            ix=(frequencies>=lo)&(frequencies<=hi)
            parts.extend(whitened[:,ix].max(axis=1).tolist() if ix.any() else [0.]*4)
        features.append(parts)
    features=np.array(features)
    # Compare candidates within one recording; absolute recording gain and
    # long-term spectral coloration must not become artist identifiers.
    features-=features.mean(0,keepdims=True)
    return candidates,np.c_[features,np.eye(3)]
