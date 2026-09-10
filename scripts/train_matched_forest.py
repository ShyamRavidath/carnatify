"""Fit v4-style 800+800-tree baseline on exactly the candidate archive cohort.

Existing deployed v4 includes Saraga training data, so scoring that pickle on
Saraga would contaminate the comparison. This retrains without any Saraga data.
"""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from scripts.raga_pipeline import load_features,sha,write_json
from carnatify.ml.melody_features import melody_features,FEATURE_VERSIONS
from carnatify.ml.fused_forest import FusedForest


def main():
    run=ROOT/'data/architecture_audit';z=load_features(run)
    rows=json.loads((run/'manifest.json').read_text())['rows']
    hist=[];tracks=[];start=time.monotonic()
    for row in rows:
        f=np.load(ROOT/row['contour']);width=round(60/row['hop_s'])
        for a in sorted({round(max(0,len(f)-width)*q) for q in [.2,.5,.8]}):
            clip=f[a:a+width]
            if np.sum(np.isfinite(clip)&(clip>0))*row['hop_s']<10:continue
            # Match the original cache's admission test for elapsed transitions.
            current=melody_features(clip,row['tonic'],row['hop_s'])
            old=melody_features(clip,row['tonic'],row['hop_s'],legacy=True)
            if current is None or old is None:continue
            hist.append(old[0]);tracks.append(row['track'])
    if not np.array_equal(tracks,z['track']):raise ValueError('Window alignment mismatch')
    X=np.c_[hist,z['legacy']]
    print(f'Fitting 800+800 trees on {len(X)} matched windows; extraction {time.monotonic()-start:.1f}s',flush=True)
    m=FusedForest().fit(X,z['y'])
    out=ROOT/'data/overhaul/raga_forest800.joblib'
    bundle=dict(model=m,representation='legacy_fused',feature_version=FEATURE_VERSIONS['legacy_fused'],
        window_s=60,training_manifest=str(run/'manifest.json'),manifest_sha256=sha(run/'manifest.json'),
        feature_sha256=sha(run/'features.npz'),
        calibration=dict(status='uncalibrated matched baseline',gate=dict(threshold=1.000001)),
        status='v4-style forest; matched archive-only data, no Saraga training')
    joblib.dump(bundle,out)
    write_json(out.with_suffix('.json'),dict(model_sha256=sha(out),elapsed_s=time.monotonic()-start,
        n_windows=len(X),n_tracks=len(set(tracks)),n_classes=len(m.classes_),status=bundle['status']))
    print(f'Wrote {out}; elapsed {time.monotonic()-start:.1f}s')


if __name__=='__main__':main()
