"""Train a taxonomy-admitted candidate, preserving original grouped CV folds.

Do not compare this CV accuracy directly with the old cohort: report denominators
and use identical independent audio queries for the model comparison.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from carnatify.ml.distribution_classifier import DistributionKernelRidge
from carnatify.ml.calibration import fit_temperature,temperature_scale,selective_threshold
from carnatify.ml.melody_features import FEATURE_VERSIONS
from scripts.raga_pipeline import load_features,sha,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--policy',choices=['quarantine','strict'],default='quarantine')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    run=ROOT/'data/architecture_audit';admission=ROOT/'data/overhaul/taxonomy_admission.json'
    a=json.loads(admission.read_text())
    for path,digest in a['inputs'].items():
        if sha(ROOT/path)!=digest:raise ValueError(f'Stale admission: {path}')
    allowed={r['track'] for r in a['rows'] if r['status']=='strict_tag_consistent' or
             (args.policy=='quarantine' and r['status']=='no_exact_title_provenance')}
    z=load_features(run);mask=np.isin(z['track'],list(allowed))
    X,y,track,group=[z[k][mask] for k in ['legacy','y','track','group']]
    classes,yi=np.unique(y,return_inverse=True)
    if len(classes)<2:raise ValueError('Insufficient admitted classes')
    folds=json.loads((run/'benchmark.json').read_text())['folds']
    f=np.array([folds[str(t)] for t in track]);p=np.zeros((len(y),len(classes)))
    counts=Counter(track)
    weights=np.array([1/counts[t] for t in track]);weights/=weights.mean()
    with threadpool_limits(limits=4):
        for fold in np.unique(f):
            tr,te=f!=fold,f==fold
            if set(group[tr])&set(group[te]):raise AssertionError('Source leakage')
            m=DistributionKernelRidge().fit(X[tr],y[tr],sample_weight=weights[tr])
            cols=np.searchsorted(classes,m.classes_)
            p[np.ix_(np.flatnonzero(te),cols)]=m.predict_proba(X[te])
        calibration=fit_temperature(p,yi,group)
        cp=temperature_scale(p,calibration['temperature'])
        calibration['gate']=selective_threshold(cp,yi)
        calibration['status']='OOF admission-cohort calibration; external coverage not guaranteed'
        m=DistributionKernelRidge(temperature=calibration['temperature']).fit(X,y,sample_weight=weights)
    tids,first=np.unique(track,return_index=True)
    aggregated=np.stack([cp[track==t].mean(0) for t in tids])
    summary=dict(policy=args.policy,n_tracks=len(tids),n_windows=len(y),n_classes=len(classes),
        n_groups=len(set(group)),cv_top1=float(np.mean(aggregated.argmax(1)==yi[first])),
        classes=classes.tolist(),admission_sha256=sha(admission),feature_sha256=sha(run/'features.npz'),
        calibration=calibration,status='development; cohort changed; no SOTA claim')
    bundle=dict(model=m,feature_version=FEATURE_VERSIONS['voiced'],representation='voiced',window_s=60,
        training_manifest=str(run/'manifest.json'),manifest_sha256=sha(run/'manifest.json'),
        admitted_tracks=tids.tolist(),admission_sha256=sha(admission),calibration=calibration,
        feature_sha256=summary['feature_sha256'],status=summary['status'])
    args.out.parent.mkdir(parents=True,exist_ok=True);joblib.dump(bundle,args.out)
    summary['model_sha256']=sha(args.out)
    write_json(args.out.with_suffix('.json'),summary)
    np.savez_compressed(args.out.with_suffix('.oof.npz'),p=cp,y=yi,track=track,group=group,classes=classes,fold=f)
    print(json.dumps({k:v for k,v in summary.items() if k!='classes'},indent=2))


if __name__=='__main__':main()
