"""Persist paired source-disjoint kernel-model development experiments.

All configs below are fixed before scoring this run. No evaluation label is
fed to fit. Outputs live separately from the audited RF reference.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from sklearn.metrics import balanced_accuracy_score,f1_score
from threadpoolctl import threadpool_limits
from carnatify.ml.distribution_classifier import DistributionSVC,DistributionKernelRidge
from scripts.raga_pipeline import load_features,sha,write_json

CONFIGS={
    'legacy_hellinger_svc':dict(source='legacy',mode='tdms',C=10,gamma=2),
    'elapsed_hellinger_svc':dict(source='X',mode='tdms',C=10,gamma=2),
    'fused_hellinger_svc':dict(source='X',mode='fused',C=10,gamma=2),
    'elapsed_kernel_ridge':dict(source='X',mode='tdms',alpha=.1,gamma=2),
    'legacy_kernel_ridge':dict(source='legacy',mode='tdms',alpha=.1,gamma=2),
}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,default=ROOT/'data/architecture_audit')
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/kernel_benchmark.json')
    ap.add_argument('--arms',nargs='+',choices=CONFIGS,default=list(CONFIGS))
    args=ap.parse_args()
    z=load_features(args.run)
    reference_path=args.run/'benchmark.json'
    if not reference_path.exists():
        reference_path=args.run/'folds.json'
        if not reference_path.exists():
            from sklearn.model_selection import StratifiedGroupKFold
            tids,first=np.unique(z['track'],return_index=True)
            folds={}
            for fold,(_,te) in enumerate(StratifiedGroupKFold(5,shuffle=True,random_state=42).split(
                    first,z['y'][first],z['group'][first])):
                folds.update({str(tids[i]):fold for i in te})
            write_json(reference_path,dict(feature_sha256=sha(args.run/'features.npz'),folds=folds,
                                          group='manifest group, all track windows together',seed=42))
    reference=json.loads(reference_path.read_text())
    if reference['feature_sha256']!=sha(args.run/'features.npz'):
        raise ValueError('Reference does not match feature cache')
    report=dict(feature_sha256=reference['feature_sha256'],reference_sha256=sha(reference_path),
                protocol=CONFIGS,status='development CV; not final held-out accuracy',arms={})
    if args.out.exists():
        old=json.loads(args.out.read_text())
        if old['feature_sha256']!=report['feature_sha256'] or old['protocol']!=CONFIGS:
            raise ValueError('Existing experiment uses different data/configs')
        report=old
    y,track,group=z['y'],z['track'],z['group']
    classes=np.array(sorted(set(y))); yi=np.searchsorted(classes,y)
    tids,first=np.unique(track,return_index=True)
    folds=np.array([reference['folds'][str(t)] for t in track])
    for arm in args.arms:
        if arm in report['arms']:
            print(f'{arm}: already complete',flush=True);continue
        cfg=CONFIGS[arm];X=z[cfg['source']]
        proba=np.zeros((len(y),len(classes)));start=time.monotonic()
        for fold in sorted(set(folds)):
            tr=np.flatnonzero(folds!=fold);te=np.flatnonzero(folds==fold)
            if set(group[tr]) & set(group[te]): raise ValueError('source leakage')
            # Rescale weights to mean 1 so C keeps its conventional meaning.
            count=Counter(track[tr]);weights=np.array([1/count[t] for t in track[tr]])
            weights/=weights.mean()
            model=(DistributionSVC(C=cfg['C'],gamma=cfg['gamma'],mode=cfg['mode']) if 'C' in cfg else
                   DistributionKernelRidge(alpha=cfg['alpha'],gamma=cfg['gamma'],mode=cfg['mode']))
            with threadpool_limits(limits=4):
                model.fit(X[tr],yi[tr],sample_weight=weights)
                proba[np.ix_(te,model.classes_)]=model.predict_proba(X[te])
            print(f'{arm} fold {fold}: {time.monotonic()-start:.1f}s',flush=True)
        p=np.stack([proba[track==t].mean(axis=0) for t in tids])
        order=np.argsort(-p,axis=1);truth=yi[first]
        rows=[dict(track=str(t),group=str(group[i]),truth=str(y[i]),prediction=str(classes[o[0]]),
                   correct=bool(o[0]==yi[i]),top3=bool(yi[i] in o[:3]))
              for t,i,o in zip(tids,first,order)]
        result=dict(top1=float(np.mean(order[:,0]==truth)),
                    top3=float(np.mean([r['top3'] for r in rows])),
                    macro_recall=float(balanced_accuracy_score(truth,order[:,0])),
                    macro_f1=float(f1_score(truth,order[:,0],average='macro',zero_division=0)),
                    fit_seconds=time.monotonic()-start,per_track=rows)
        report['arms'][arm]=result
        write_json(args.out,report)
        print(arm,{k:v for k,v in result.items() if k!='per_track'},flush=True)
        np.savez_compressed(args.out.parent/f'{arm}_oof.npz',p=p,y=classes[truth],
                            track=tids,group=group[first],classes=classes,
                            feature_sha256=reference['feature_sha256'],config=json.dumps(cfg),
                            window_p=proba,window_y=yi,window_track=track,
                            window_group=group,window_fold=folds)


if __name__=='__main__':main()
