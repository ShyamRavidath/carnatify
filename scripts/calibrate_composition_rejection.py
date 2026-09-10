"""Development-only rejection diagnostic with artist/work connected holdouts.

No gate is exported. All unanswerable queries remain negatives. Report both
predeclared scalar signals, without choosing a winner on held-out outcomes.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json
from scripts.raga_audit_protocol import DSU
from scripts.merge_raga_training import artist_key
from scripts.calibrate_development_risk import choose_threshold


def connected_groups(rows,corpus):
    dsu=DSU();seen=set()
    for row in rows:
        track=row['track'];meta=corpus[track]
        if track in seen or not meta['artists'] or not meta['work_id']:
            raise ValueError('Duplicate query or missing grouping provenance')
        if row['work_id']!=meta['work_id']:raise ValueError('Work identity mismatch')
        seen.add(track);key='track:'+track
        for artist in meta['artists']:
            name=artist_key(artist)
            if not name:raise ValueError('Missing artist identity')
            dsu.union(key,'artist:'+name)
        dsu.union(key,'work:'+meta['work_id'])
        if meta.get('source'):dsu.union(key,'source:'+meta['source'])
    return np.array([dsu.find('track:'+r['track']) for r in rows])


def signals(row,score_field='distance'):
    if score_field not in ('distance','ranking_cost'):raise ValueError('Unknown ranking score field')
    candidates=row['top5']
    if not candidates:return 0.,0.
    distances=np.array([r[score_field] for r in candidates],dtype=float)
    if not np.isfinite(distances).all() or np.any(distances<0) or np.any(np.diff(distances)<0):
        raise ValueError('Invalid retrieval distances')
    proximity=1/(1+distances[0])
    margin=(distances[1]-distances[0])/max(distances[1],1e-12) if len(distances)>1 else 0.
    return proximity,float(margin)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--report',type=Path,default=ROOT/'data/overhaul/composition_transposition_open.json')
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/composition_rejection_crossfit.json')
    ap.add_argument('--score-field',choices=['distance','ranking_cost'],default='distance')
    args=ap.parse_args();cp=ROOT/'data/overhaul/annotated_corpus.json'
    report=json.loads(args.report.read_text())
    if (report.get('raga_prior_weight',0)>0 or report.get('directional_contrast',False)) and args.score_field!='ranking_cost':
        ap.error('Adjusted ranks require --score-field ranking_cost; raw distances are not rank ordered')
    if report['corpus_sha256']!=sha(cp):raise ValueError('Retrieval/corpus mismatch')
    rows=report['rows'];corpus={r['track']:r for r in json.loads(cp.read_text())['rows']}
    groups=connected_groups(rows,corpus);unique=np.unique(groups)
    if len(unique)<2:raise ValueError('No independent calibration holdout')
    correct=np.array([r['rank']==1 for r in rows]);known=np.array([r['answerable'] for r in rows])
    if np.any(correct&~known):raise ValueError('Correct identity cannot be unanswerable')
    X=np.array([signals(r,args.score_field) for r in rows]);arms={}
    for column,name in enumerate(['distance_proximity','relative_margin']):
        confidence=X[:,column];accepted=np.zeros(len(rows),dtype=bool);folds=[]
        for group in unique:
            te=groups==group;tr=~te
            threshold=choose_threshold(confidence[tr],correct[tr],target=.9,min_answers=10)
            accepted[te]=confidence[te]>=threshold
            folds.append(dict(group=str(group),n_test=int(te.sum()),n_train_correct=int(correct[tr].sum()),
                threshold=float(threshold),feasible=threshold<=1,n_accepted=int(accepted[te].sum())))
        arms[name]=dict(n_accepted=int(accepted.sum()),n_correct_accepted=int((accepted&correct).sum()),
            coverage=float(accepted.mean()),precision=float(correct[accepted].mean()) if accepted.any() else None,
            unknown_false_acceptance=float(accepted[~known].mean()) if (~known).any() else None,folds=folds,
            rows=[dict(track=r['track'],accepted=bool(accepted[i]),correct=bool(correct[i])) for i,r in enumerate(rows)])
    result=dict(status='connected artist/work held-out development diagnostic; no production gate exported',
        report_sha256=sha(args.report),corpus_sha256=sha(cp),target_precision=.9,min_calibration_answers=10,
        score_field=args.score_field,
        n_queries=len(rows),n_answerable=int(known.sum()),n_top1_correct=int(correct.sum()),
        groups=[dict(group=str(g),n=int((groups==g).sum()),n_answerable=int(known[groups==g].sum()),
                     n_correct=int(correct[groups==g].sum())) for g in unique],arms=arms)
    write_json(args.out,result)
    print(json.dumps({**{k:v for k,v in result.items() if k!='arms'},
        'arms':{k:{a:b for a,b in v.items() if a!='rows'} for k,v in arms.items()}},indent=2))


if __name__=='__main__':main()
