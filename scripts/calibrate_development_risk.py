"""Cross-fit a selective gate by artist, including out-of-vocabulary negatives.

This evaluates gate transfer within development artists, not production safety.
No full-fit acceptance gate is exported or enabled by this script.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from sklearn.model_selection import GroupKFold
from scripts.raga_pipeline import sha,write_json
from normalize_ragas import fold


def choose_threshold(confidence,correct,target=.9,min_answers=10):
    choices=[]
    for t in np.unique(confidence):
        accepted=confidence>=t
        if accepted.sum()>=min_answers and correct[accepted].mean()>=target:
            choices.append(float(t))
    return min(choices) if choices else 1.000001


def main():
    base=ROOT/'data/overhaul';rp=base/'saraga_v2_broader_180.json';cp=base/'annotated_corpus_v2.json'
    report=json.loads(rp.read_text());corpus={r['track']:r for r in json.loads(cp.read_text())['rows']}
    if report['corpus_sha256']!=sha(cp):raise ValueError('Calibration corpus mismatch')
    rows=report['rows'];p=[r['predictions']['broader_estimated'] for r in rows]
    confidence=np.array([r.get('confidence',0) for r in p]);correct=np.array([r['correct'] for r in p])
    known=np.array([r['in_vocabulary'] for r in p])
    groups=np.array(['|'.join(sorted(fold(a) for a in corpus[r['track']]['artists'])) for r in rows])
    accepted=np.zeros(len(rows),dtype=bool);thresholds=[]
    for fold_id,(tr,te) in enumerate(GroupKFold(5).split(confidence,groups=groups)):
        threshold=choose_threshold(confidence[tr],correct[tr])
        accepted[te]=confidence[te]>=threshold
        thresholds.append(dict(fold=fold_id,threshold=threshold,n_test=len(te)))
    keys=np.unique(groups);counts=np.array([accepted[groups==g].sum() for g in keys])
    hits=np.array([(accepted&correct)[groups==g].sum() for g in keys])
    sample=np.random.default_rng(42).integers(0,len(keys),size=(5000,len(keys)))
    den=counts[sample].sum(1);num=hits[sample].sum(1);valid=den>0
    result=dict(status='artist-cross-fitted development gate; not exported or production validated',
        report_sha256=sha(rp),corpus_sha256=sha(cp),target_precision=.9,min_calibration_answers=10,
        n=len(rows),n_accepted=int(accepted.sum()),n_correct_accepted=int((accepted&correct).sum()),
        coverage=float(accepted.mean()),accepted_precision=float(correct[accepted].mean()) if accepted.any() else None,
        precision_artist_bootstrap_ci95=np.percentile(num[valid]/den[valid],[2.5,97.5]).tolist() if valid.any() else None,
        oov_false_acceptance=float(accepted[~known].mean()),folds=thresholds,
        rows=[dict(track=r['track'],accepted=bool(accepted[i]),correct=bool(correct[i]),group=str(groups[i])) for i,r in enumerate(rows)])
    write_json(base/'broader_risk_crossfit.json',result)
    print({k:v for k,v in result.items() if k!='rows'})


if __name__=='__main__':main()
