"""Artist-held-out activity development diagnostic using existing annotations.

Then apply the fixed full fit to known intervals of concert 1, without using
those field labels for fitting or selecting a threshold. No detector promotion.
"""
import argparse,json,sys,time,multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from scripts.raga_pipeline import sha,write_json
from normalize_ragas import fold
from carnatify.audio.pitch_activity import activity_features,VERSION
from carnatify.audio.sections import plan_activity_queries,artist_class_weights
from carnatify.audio.pitch_activity import extract_activity_query


def extract(row):
    return extract_activity_query(ROOT/row['audio'],row.get('audio_sha256') or sha(ROOT/row['audio']),
                                  row['start_s'],ROOT/'data/overhaul/cache/activity_pitch')


def estimator(weighted=False):
    return make_pipeline(StandardScaler(),LogisticRegression(C=.1,class_weight=None if weighted else 'balanced',max_iter=1000,random_state=42))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--expanded',action='store_true',help='All supported annotated sections; three fixed windows per section')
    ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--field-exact',action='store_true',help='Extract each field query at the same 10s context used for training')
    args=ap.parse_args()
    out=ROOT/('data/overhaul/pitch_activity_expanded' if args.expanded else 'data/overhaul/pitch_activity')
    if args.field_exact:out=out.with_name(out.name+'_exact')
    source=ROOT/'data/overhaul/activity_evaluation.json'
    previous=json.loads(source.read_text());rows=previous['rows']
    corpus_path=ROOT/'data/overhaul/annotated_corpus.json'
    if sha(corpus_path)!=previous['corpus_sha256']:raise ValueError('Activity annotation corpus changed')
    corpus={r['track']:r for r in json.loads(corpus_path.read_text())['rows']}
    if args.expanded:
        rows=plan_activity_queries(list(corpus.values()))
        hashes={r['audio']:sha(ROOT/r['audio']) for r in corpus.values() if r['sections']}
        rows=[dict(r,audio_sha256=hashes[r['audio']]) for r in rows]
        source=out/'query_plan.json'
        plan=dict(corpus_sha256=sha(corpus_path),rows=rows,policy='all supported sections >=12s; positions .2/.5/.8; 10s queries')
        if source.exists() and json.loads(source.read_text())!=plan:raise ValueError('Expanded activity plan changed')
        if not source.exists():write_json(source,plan)
    groups=np.array(['|'.join(sorted(fold(a) for a in corpus[r['track']]['artists'])) for r in rows])
    if any(not g for g in groups):raise ValueError('Missing activity artist group')
    started=time.monotonic();vectors=[]
    if args.expanded:
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for vector in pool.map(extract,rows):
                vectors.append(vector)
                if len(vectors)%50==0 or len(vectors)==len(rows):print(f'{len(vectors)}/{len(rows)} activity contours',flush=True)
    else:
        for row in rows:
            vectors.append(extract(row));print(f'{len(vectors)}/{len(rows)} activity contours',flush=True)
    X=np.stack(vectors);y=np.array([r['truth']=='percussion' for r in rows],dtype=int)
    p=np.zeros(len(y))
    for tr,te in LeaveOneGroupOut().split(X,y,groups):
        if len(np.unique(y[tr]))<2:raise ValueError('Insufficient held-out class support')
        if set.union(*[set(g.split('|')) for g in groups[tr]])&set.union(*[set(g.split('|')) for g in groups[te]]):
            raise ValueError('Partial ensemble artist overlap')
        if args.expanded:
            fit=estimator(True).fit(X[tr],y[tr],logisticregression__sample_weight=artist_class_weights(y[tr],groups[tr]))
        else:fit=estimator().fit(X[tr],y[tr])
        p[te]=fit.predict_proba(X[te])[:,1]
    model=(estimator(True).fit(X,y,logisticregression__sample_weight=artist_class_weights(y,groups))
           if args.expanded else estimator().fit(X,y))
    report=dict(status='artist-held-out development activity diagnostic; not production validated',
                version=VERSION,source_sha256=sha(source),n=len(y),correct=int(np.sum((p>=.5)==y)),
                n_percussion=int(y.sum()),percussion_recall=float(np.mean(p[y==1]>=.5)),
                melody_recall=float(np.mean(p[y==0]<.5)),threshold=.5,
                rows=[dict(track=r['track'],truth=r['truth'],artist=str(groups[i]),percussion_probability=float(p[i]))
                      for i,r in enumerate(rows)],field_rows=[])
    report.update(n_artists=len(np.unique(groups)),n_percussion_artists=len(np.unique(groups[y==1])))
    if args.expanded:
        section_ids=np.array([r['section_id'] for r in rows]);unique,first=np.unique(section_ids,return_index=True)
        sp=np.array([p[section_ids==s].mean() for s in unique]);sy=y[first]
        report['sections']=dict(n=len(unique),n_percussion=int(sy.sum()),correct=int(np.sum((sp>=.5)==sy)),
            percussion_recall=float(np.mean(sp[sy==1]>=.5)),melody_recall=float(np.mean(sp[sy==0]<.5)))
    labels_path=ROOT/'data/architecture_audit/label_intervals.json'
    labels=json.loads(labels_path.read_text())
    if sha(ROOT/labels['source'])!=labels['source_sha256']:raise ValueError('User label source changed')
    field_path=ROOT/'data/overhaul/long_concert_1_context180.json'
    field=json.loads(field_path.read_text());audio=ROOT/field['audio']
    if sha(audio)!=field['audio_sha256']:raise ValueError('Field audio changed')
    cache=ROOT/'data/overhaul/cache/concerts'/f'{field["audio_sha256"][:24]}_{field["event_model_sha256"][:12]}_concert_mix_melodia_events_v1'
    f=[];times=[]
    for start in ([] if args.field_exact else np.arange(0,field['duration_s'],60.)):
        length=min(60.,field['duration_s']-start)
        path=cache/f'{start:.3f}_{length:.3f}.npz'
        with np.load(path) as z:f.append(z['f0']);times.append(z['times'])
    if not args.field_exact:f=np.concatenate(f);times=np.concatenate(times)
    field_queries=[];field_vectors=[]
    for event in field['events']:
        a,b=event['start_s'],event['end_s'];truth=None
        if any(r['concert']=='long_concert_1' and r['primary'] and r['confidence']=='high'
               and r['start_s']<=a<b<=r['end_s'] for r in labels['intervals']):truth=0
        if any(r['concert']=='long_concert_1' and r['kind']=='tani' and r['start_s']<=a<b<=r['end_s']
               for r in labels['exclusions']):truth=1
        if truth is None:continue
        if b-a!=10:raise ValueError('Field query must match 10-second training context')
        field_queries.append(dict(track=audio.stem,audio=str(audio.relative_to(ROOT)),
            audio_sha256=field['audio_sha256'],start_s=a,end_s=b,truth=truth))
        if not args.field_exact:
            i,j=np.searchsorted(times,[a,b]);field_vectors.append(activity_features(f[i:j],128/44100))
    if args.field_exact:
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for vector in pool.map(extract,field_queries):
                field_vectors.append(vector)
                if len(field_vectors)%25==0 or len(field_vectors)==len(field_queries):
                    print(f'{len(field_vectors)}/{len(field_queries)} exact field contours',flush=True)
    probabilities=model.predict_proba(np.stack(field_vectors))[:,1]
    for query,prob in zip(field_queries,probabilities):
        report['field_rows'].append(dict(start_s=query['start_s'],end_s=query['end_s'],truth=query['truth'],
            percussion_probability=float(prob),correct=bool((prob>=.5)==bool(query['truth']))))
    field_rows=report['field_rows']
    report['field']=dict(status='existing-label field diagnostic; artist identity not verified',
        frontend='exact_10s_queries' if args.field_exact else 'slices_from_60s_blocks',
        n=len(field_rows),correct=sum(r['correct'] for r in field_rows),
        percussion_recall=float(np.mean([r['correct'] for r in field_rows if r['truth']==1])),
        melody_recall=float(np.mean([r['correct'] for r in field_rows if r['truth']==0])))
    report['elapsed_s']=time.monotonic()-started
    write_json(out/'result.json',report)
    joblib.dump(dict(model=model,version=VERSION,threshold=.5,status='experimental; not promoted',
                     training_report_sha256=sha(out/'result.json')),out/'model.joblib')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','field_rows')},indent=2))


if __name__=='__main__':main()
