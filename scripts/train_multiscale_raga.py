"""Fixed six-scale ablation: extend voiced-time TDMS to .5, 1 and 2 seconds.

Uses exactly the combined cohort/folds; no validation audio or labels select
scales or hyperparameters. Calibrated scores remain development-only.
"""
import json,sys,time
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from scripts.raga_pipeline import sha,write_json,load_features
from carnatify.ml.melody_features import FEATURE_VERSIONS,feature_vector,MULTISCALE_TAUS
from carnatify.ml.distribution_classifier import DistributionKernelRidge
from carnatify.ml.calibration import fit_temperature,temperature_scale,selective_threshold


def main():
    base=ROOT/'data/overhaul/combined';out=ROOT/'data/overhaul/multiscale';out.mkdir(parents=True,exist_ok=True)
    z=load_features(base);manifest=json.loads((base/'manifest.json').read_text())
    cache=out/'features.npz';started=time.monotonic()
    if cache.exists():
        with np.load(cache) as d:
            if str(d['base_sha256'])!=sha(base/'features.npz'):raise ValueError('Stale multiscale features')
            X=d['X']
    else:
        by_track={r['track']:r for r in manifest['rows']};vectors={}
        for ti,tid in enumerate(dict.fromkeys(z['track'])):
            row=by_track[str(tid)];p=ROOT/row['contour']
            if sha(p)!=row['contour_sha256']:raise ValueError('Contour input changed')
            f=np.load(p) if p.suffix=='.npy' else np.loadtxt(p)[:,1]
            width=round(60/row['hop_s']);parts=[]
            for a in sorted({round(max(0,len(f)-width)*q) for q in [.2,.5,.8]}):
                clip=f[a:a+width]
                if np.sum(np.isfinite(clip)&(clip>0))*row['hop_s']<10:continue
                if feature_vector(clip,row['tonic'],row['hop_s'],'elapsed') is None:continue
                v=feature_vector(clip,row['tonic'],row['hop_s'],'multiscale_voiced')
                if v is None:raise ValueError('Unexpected missing six-scale window')
                parts.append(v)
            if len(parts)!=np.sum(z['track']==tid):raise ValueError('Multiscale window alignment mismatch')
            vectors[str(tid)]=iter(parts)
            if (ti+1)%100==0:print(f'Extracted {ti+1} tracks; {time.monotonic()-started:.1f}s',flush=True)
        X=np.stack([next(vectors[str(t)]) for t in z['track']])
        np.savez_compressed(cache,X=X,base_sha256=sha(base/'features.npz'))
    y=z['y'];classes,yi=np.unique(y,return_inverse=True);track=z['track'];groups=z['group']
    folds=json.loads((base/'folds.json').read_text())['folds'];f=np.array([folds[str(t)] for t in track])
    p=np.zeros((len(y),len(classes)));counts=Counter(track);weight=np.array([1/counts[t] for t in track]);weight/=weight.mean()
    with threadpool_limits(limits=4):
        for fold in np.unique(f):
            tr,te=f!=fold,f==fold
            if set(groups[tr])&set(groups[te]):raise ValueError('Source leakage')
            m=DistributionKernelRidge(mode='multiscale').fit(X[tr],y[tr],sample_weight=weight[tr])
            p[np.ix_(np.flatnonzero(te),np.searchsorted(classes,m.classes_))]=m.predict_proba(X[te])
        tids,first=np.unique(track,return_index=True)
        avg=np.stack([p[track==t].mean(0) for t in tids])
        cv=float(np.mean(avg.argmax(1)==yi[first]))
        calibration=fit_temperature(p,yi,groups)
        calibration['gate']=selective_threshold(temperature_scale(p,calibration['temperature']),yi)
        calibration['status']='OOF training calibration; not production validated'
        m=DistributionKernelRidge(mode='multiscale',temperature=calibration['temperature']).fit(X,y,sample_weight=weight)
    bundle=dict(model=m,representation='multiscale_voiced',feature_version=FEATURE_VERSIONS['multiscale_voiced'],
        window_s=60,training_manifest=str(base/'manifest.json'),manifest_sha256=sha(base/'manifest.json'),
        feature_sha256=sha(cache),calibration=calibration,status='fixed six-scale development ablation')
    joblib.dump(bundle,out/'raga.joblib')
    write_json(out/'result.json',dict(top1=cv,n_tracks=len(tids),n_classes=len(classes),taus=MULTISCALE_TAUS,
        model_sha256=sha(out/'raga.joblib'),classes=classes.tolist(),calibration=calibration,
        elapsed_s=time.monotonic()-started,base_feature_sha256=sha(base/'features.npz')))
    print(f'Six-scale matched CV: {cv:.4%}; {time.monotonic()-started:.1f}s',flush=True)


if __name__=='__main__':main()
