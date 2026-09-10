"""Bounded nested source-grouped kernel tuning; no validation audio consulted."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits
from scripts.raga_pipeline import load_features,sha,write_json
from carnatify.ml.distribution_classifier import DistributionKernelRidge
from carnatify.ml.melody_features import FEATURE_VERSIONS

CONFIGS=[dict(alpha=a,gamma=g) for a in [.01,.1,1.] for g in [.5,2.,8.]]


def track_accuracy(p,indices,tracks,y):
    unique=np.unique(tracks[indices]);correct=[]
    for track in unique:
        local=np.flatnonzero(tracks[indices]==track)
        correct.append(p[local].mean(0).argmax()==y[indices[local[0]]])
    return float(np.mean(correct))


def main():
    base=ROOT/'data/overhaul/combined';out=ROOT/'data/overhaul/kernel_tuning';out.mkdir(parents=True,exist_ok=True)
    z=load_features(base);X=z['legacy'];classes,y=np.unique(z['y'],return_inverse=True)
    tracks=z['track'];groups=z['group'];n=len(y);indices=np.arange(n)
    foldfile=base/'folds.json';fixed=json.loads(foldfile.read_text())
    if fixed['feature_sha256']!=sha(base/'features.npz'):raise ValueError('Stale folds')
    folds=np.array([fixed['folds'][str(t)] for t in tracks])
    oof=np.zeros((n,len(classes)));global_oof=np.zeros((len(CONFIGS),n,len(classes)))
    selected=[];started=time.monotonic()

    def predict(cfg,tr,te):
        if set(groups[tr])&set(groups[te]):raise ValueError('Source leakage')
        _,inv,count=np.unique(tracks[tr],return_inverse=True,return_counts=True)
        weight=1/count[inv];weight/=weight.mean()
        m=DistributionKernelRidge(**cfg).fit(X[tr],y[tr],sample_weight=weight)
        p=np.zeros((len(te),len(classes)))
        p[:,m.classes_]=m.predict_proba(X[te]);return p

    with threadpool_limits(limits=4):
        for outer in np.unique(folds):
            tr=indices[folds!=outer];te=indices[folds==outer]
            inner=list(GroupKFold(3).split(tr,groups=groups[tr]));scores=[]
            for ci,cfg in enumerate(CONFIGS):
                p=np.zeros((len(tr),len(classes)))
                for a,b in inner:p[b]=predict(cfg,tr[a],tr[b])
                scores.append(track_accuracy(p,tr,tracks,y))
                global_oof[ci,te]=predict(cfg,tr,te)
            best=int(np.argmax(scores));oof[te]=global_oof[best,te]
            selected.append(dict(fold=int(outer),config=CONFIGS[best],inner_scores=scores))
            write_json(out/'progress.json',dict(completed_folds=selected,configs=CONFIGS,
                                               elapsed_s=time.monotonic()-started))
            print(f'Nested fold {outer}: {CONFIGS[best]}; {time.monotonic()-started:.1f}s',flush=True)
        grid_scores=[track_accuracy(p,indices,tracks,y) for p in global_oof]
        best=int(np.argmax(grid_scores));cfg=CONFIGS[best]
        report=dict(status='nested grouped development CV; best flat-CV score is selection-biased',
            feature_sha256=sha(base/'features.npz'),fold_sha256=sha(foldfile),configs=CONFIGS,
            nested_top1=track_accuracy(oof,indices,tracks,y),flat_cv_scores=grid_scores,
            selected_config=cfg,outer_selections=selected)
        write_json(out/'result.json',report)
        np.savez_compressed(out/'oof.npz',nested_p=oof,grid_p=global_oof,classes=classes,track=tracks,fold=folds)
        _,inv,count=np.unique(tracks,return_inverse=True,return_counts=True)
        weight=1/count[inv];weight/=weight.mean()
        model=DistributionKernelRidge(**cfg,temperature=.07200885).fit(X,z['y'],sample_weight=weight)
        joblib.dump(dict(model=model,representation='voiced',feature_version=FEATURE_VERSIONS['voiced'],
            training_report_sha256=sha(out/'result.json'),status='training-only selected kernel candidate',
            calibration=dict(status='uncalibrated after kernel selection',gate=dict(threshold=1.000001))),out/'raga.joblib')
    print(report,flush=True)


if __name__=='__main__':main()
