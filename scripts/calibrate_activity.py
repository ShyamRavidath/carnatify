"""Learn a monotonic percussion/melody gate from existing section annotations.

Leave-primary-artist-out readout is reported separately from the full fit.
Four percussion sections are limited evidence, not production validation.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json
from normalize_ragas import fold


def fit_threshold(x,y):
    if len(set(y))<2:raise ValueError('Both activity classes required')
    values=np.unique(x);thresholds=np.r_[0,(values[:-1]+values[1:])/2,1.000001]
    scores=[.5*(np.mean((x[y==1]>=t))+np.mean(x[y==0]<t)) for t in thresholds]
    return float(thresholds[int(np.argmax(scores))])


def main():
    path=ROOT/'data/overhaul/activity_evaluation.json';r=json.loads(path.read_text())
    corpus={x['track']:x for x in json.loads((ROOT/'data/overhaul/annotated_corpus.json').read_text())['rows']}
    rows=r['rows'];y=np.array([x['truth']=='percussion' for x in rows],dtype=int)
    x=np.array([a['prediction']['percussion']/max(1e-9,a['prediction']['percussion']+a['prediction']['melodic']) for a in rows])
    group=np.array(['|'.join(sorted(fold(a) for a in corpus[z['track']]['artists'])) for z in rows])
    predicted=np.zeros(len(y),dtype=bool);folds=[]
    for g in np.unique(group):
        tr,te=group!=g,group==g
        threshold=fit_threshold(x[tr],y[tr]);predicted[te]=x[te]>=threshold
        folds.append(dict(group=g,threshold=threshold,n=int(te.sum())))
    out=dict(model_sha256=r['model_sha256'],training_report_sha256=sha(path),
        ratio_threshold=fit_threshold(x,y),min_percussion_score=.35,
        definition='percussion / (percussion + melodic)',n=len(y),n_percussion=int(y.sum()),
        leave_artist_out=dict(n_groups=len(folds),correct=int(np.sum(predicted==y)),
            percussion_correct=int(np.sum(predicted[y==1])),melodic_correct=int(np.sum(~predicted[y==0])),folds=folds),
        status='small existing-section development calibration; no production guarantee')
    write_json(ROOT/'data/overhaul/activity_calibration.json',out);print(json.dumps(out,indent=2))


if __name__=='__main__':main()
