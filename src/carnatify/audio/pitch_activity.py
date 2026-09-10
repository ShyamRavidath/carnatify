"""Small pitch-contour activity descriptor; not a semantic raga feature."""
import numpy as np
import hashlib
import json
from pathlib import Path

VERSION='pitch_activity_elapsed_v1'


def activity_features(f0,hop_s):
    f0=np.asarray(f0,dtype=float)
    if f0.ndim!=1 or not np.isfinite(hop_s) or hop_s<=0:
        raise ValueError('Invalid activity contour')
    voiced=np.isfinite(f0)&(f0>0)
    output=np.zeros(10,dtype=np.float32)
    if not len(f0) or not voiced.any():return output
    output[0]=voiced.mean()
    cents=1200*np.log2(f0[voiced])
    bins=np.floor((cents%1200+1e-7)/50).astype(int)%24
    hist=np.bincount(bins,minlength=24).astype(float);hist/=hist.sum()
    output[1]=-np.sum(hist[hist>0]*np.log(hist[hist>0]))/np.log(24)
    output[2]=hist.max();output[3]=np.mean(hist>.01)
    output[4]=min(5,(np.percentile(cents,90)-np.percentile(cents,10))/1200)
    adjacent=voiced[:-1]&voiced[1:]
    all_cents=np.zeros(len(f0));all_cents[voiced]=cents
    steps=np.abs(np.diff(all_cents)[adjacent])
    if len(steps):
        # Express motion over elapsed time, not compressed voiced samples.
        speed=steps/hop_s
        output[5]=np.mean(speed<300)
        output[6]=np.mean(speed>3000)
        output[7]=min(10,np.median(speed)/1000)
        output[8]=min(10,np.percentile(speed,90)/1000)
    edges=np.flatnonzero(np.diff(np.r_[False,voiced,False]))
    output[9]=min(1,np.mean(edges[1::2]-edges[::2])*hop_s/5)
    return output


def extract_activity_query(audio_path,audio_sha256,start_s,cache_dir):
    from .melody_frontend import query_contract
    from .cache_io import atomic_npz
    query_contract(audio_sha256,start_s,10)
    contract=dict(audio_sha256=audio_sha256,start_s=start_s,duration_s=10,
                  frontend='default_melodia_no_tonic_required',hop_s=128/44100)
    key=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    path=Path(cache_dir)/f'{key}.npz'
    if path.exists():
        with np.load(path,allow_pickle=False) as z:
            if json.loads(str(z['contract']))!=contract:raise ValueError('Activity cache mismatch')
            f0=z['f0']
        if f0.ndim!=1 or not len(f0) or not np.isfinite(f0).all() or np.any(f0<0):
            raise ValueError('Invalid cached activity contour')
    else:
        import essentia.standard as es
        from .utils import load_audio_window
        audio,sr,_=load_audio_window(audio_path,start_s,10,44100)
        if len(audio)/sr<9.99:raise ValueError('Activity query extends beyond audio')
        f0,_=es.PredominantPitchMelodia(sampleRate=sr,frameSize=2048,hopSize=128)(es.EqualLoudness(sampleRate=sr)(audio))
        atomic_npz(path,f0=f0,contract=json.dumps(contract))
    return activity_features(f0,128/44100)


def refine_event(event,percussion_probability,threshold=.5):
    if not np.isfinite(percussion_probability) or not 0<=percussion_probability<=1 or not 0<=threshold<=1:
        raise ValueError('Invalid pitch activity probability or threshold')
    result=dict(event,pitch_percussion_probability=float(percussion_probability),
                pitch_activity_status='development_candidate',state_before_pitch_activity=event['state'])
    # This binary model was not trained to identify speech, applause, silence,
    # or arbitrary unknown sounds. Preserve those states rather than forcing music.
    if event['state'] in {'music','percussion'}:
        result['state']='percussion' if percussion_probability>=threshold else 'music'
    return result


class PitchActivityAnnotator:
    def __init__(self,path):
        import joblib
        path=Path(path);bundle=joblib.load(path)
        digest=hashlib.sha256((path.parent/'result.json').read_bytes()).hexdigest()
        if bundle['version']!=VERSION or digest!=bundle['training_report_sha256']:
            raise ValueError('Activity artifact/report mismatch')
        self.model=bundle['model'];self.threshold=bundle['threshold']
        if not np.isfinite(self.threshold) or not 0<=self.threshold<=1:
            raise ValueError('Invalid activity artifact threshold')
        if not np.array_equal(self.model.classes_,[0,1]):raise ValueError('Unexpected activity class encoding')

    def annotate(self,audio_path,audio_sha256,events,cache_dir):
        result=[]
        for event in events:
            if abs(event['end_s']-event['start_s']-10)>1e-6 or event['state'] not in {'music','percussion'}:
                result.append(dict(event));continue
            vector=extract_activity_query(audio_path,audio_sha256,event['start_s'],cache_dir)
            p=float(self.model.predict_proba(vector[None])[0,1])
            result.append(refine_event(event,p,self.threshold))
        return result
