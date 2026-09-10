"""Bounded SPD-variant ablation on the existing artist-disjoint reference corpus."""
import json,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from threadpoolctl import threadpool_limits
from scripts.raga_pipeline import sha,write_json,load_features
from carnatify.ml.sequential_pitch import sequential_pitch_distribution,SPD_VERSION
from carnatify.ml.distribution_classifier import DistributionKernelRidge
from carnatify.ml.melody_features import feature_vector


def main():
    base=ROOT/'data/overhaul/compmusic';out=ROOT/'data/overhaul/sequential_pitch';out.mkdir(parents=True,exist_ok=True)
    z=load_features(base);manifest=json.loads((base/'manifest.json').read_text());cache=out/'features.npz'
    started=time.monotonic()
    if cache.exists():
        with np.load(cache) as d:
            if str(d['base_sha256'])!=sha(base/'features.npz') or str(d['version'])!=SPD_VERSION:
                raise ValueError('Stale SPD cache')
            X=d['X']
    else:
        by_track={r['track']:r for r in manifest['rows']};vectors={}
        for i,tid in enumerate(dict.fromkeys(z['track'])):
            row=by_track[str(tid)];path=ROOT/row['contour']
            if sha(path)!=row['contour_sha256']:raise ValueError('Changed reference pitch')
            f=np.loadtxt(path,usecols=1);width=round(60/row['hop_s']);parts=[]
            for start in sorted({round(max(0,len(f)-width)*q) for q in [.2,.5,.8]}):
                clip=f[start:start+width]
                if np.sum(np.isfinite(clip)&(clip>0))*row['hop_s']<10:continue
                if feature_vector(clip,row['tonic'],row['hop_s'],'elapsed') is None:continue
                parts.append(sequential_pitch_distribution(clip,row['tonic']).ravel())
            if len(parts)!=np.sum(z['track']==tid):raise ValueError('Window alignment differs from baseline')
            vectors[str(tid)]=iter(parts)
            if (i+1)%25==0:print(f'SPD {i+1}/{len(by_track)} tracks; {time.monotonic()-started:.1f}s',flush=True)
        X=np.stack([next(vectors[str(t)]) for t in z['track']])
        np.savez_compressed(cache,X=X,version=SPD_VERSION,base_sha256=sha(base/'features.npz'))
    classes,y=np.unique(z['y'],return_inverse=True);tracks=z['track'];groups=z['group']
    fp=base/'folds.json';foldmeta=json.loads(fp.read_text())
    if foldmeta['feature_sha256']!=sha(base/'features.npz'):raise ValueError('Stale source folds')
    folds=np.array([foldmeta['folds'][str(t)] for t in tracks]);p=np.zeros((len(y),len(classes)))
    with threadpool_limits(limits=4):
        for fold_id in np.unique(folds):
            tr,te=np.flatnonzero(folds!=fold_id),np.flatnonzero(folds==fold_id)
            if set(groups[tr])&set(groups[te]):raise ValueError('Artist leakage')
            count=Counter(tracks[tr]);weight=np.array([1/count[t] for t in tracks[tr]]);weight/=weight.mean()
            model=DistributionKernelRidge(mode='spd').fit(X[tr],y[tr],sample_weight=weight)
            p[np.ix_(te,model.classes_)]=model.predict_proba(X[te])
            print(f'SPD fold {fold_id}; {time.monotonic()-started:.1f}s',flush=True)
    tids,first=np.unique(tracks,return_index=True);mean=np.stack([p[tracks==t].mean(0) for t in tids])
    report=dict(version=SPD_VERSION,status='Bounded-excursion variant, not exact published SPD ensemble reproduction',
        feature_sha256=sha(cache),base_feature_sha256=sha(base/'features.npz'),fold_sha256=sha(fp),
        n_tracks=len(tids),n_classes=len(classes),top1=float(np.mean(mean.argmax(1)==y[first])),
        elapsed_s=time.monotonic()-started)
    write_json(out/'result.json',report)
    np.savez_compressed(out/'oof.npz',p=mean,classes=classes,track=tids,y=classes[y[first]])
    print(report,flush=True)


if __name__=='__main__':main()
