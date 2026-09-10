"""Artist-disjoint Sa/Pa disambiguation from stationary audio harmonics."""
from __future__ import annotations
import hashlib,json,sys,time,multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from scripts.raga_pipeline import sha,write_json
from normalize_ragas import fold
from carnatify.audio.tonic_evidence import harmonic_evidence,TONIC_EVIDENCE_VERSION


def evidence_contract(row):
    return dict(audio_sha256=row['audio_sha256'],start_s=row['start_s'],end_s=row['end_s'],
                base_tonic=row['tonic_estimated'],feature_version=TONIC_EVIDENCE_VERSION)


def extract_evidence(row):
    cache=ROOT/'data/overhaul/cache/tonic_evidence';cache.mkdir(parents=True,exist_ok=True)
    contract=evidence_contract(row)
    encoded=json.dumps(contract,sort_keys=True,allow_nan=False)
    path=cache/(hashlib.sha256(encoded.encode()).hexdigest()+'_'+TONIC_EVIDENCE_VERSION+'.npz')
    if path.exists():
        with np.load(path) as z:
            if str(z['contract'])!=encoded:raise ValueError('Tonic cache contract mismatch')
        return str(path)
    from carnatify.audio.utils import load_audio_window
    if sha(ROOT/row['audio'])!=row['audio_sha256']:raise ValueError('Tonic audio provenance mismatch')
    audio,sr,_=load_audio_window(ROOT/row['audio'],row['start_s'],row['end_s']-row['start_s'],11025)
    candidates,X=harmonic_evidence(audio,sr,row['tonic_estimated'])
    np.savez_compressed(path,candidates=candidates,X=X,contract=encoded)
    return str(path)


def estimator():
    return make_pipeline(StandardScaler(),LogisticRegression(C=.1,class_weight='balanced',max_iter=1000,random_state=42))


def guarded_choices(scores, margin):
    """Change Sa only when acoustic evidence exceeds the base hypothesis."""
    choice=scores.argmax(1)
    gain=scores[np.arange(len(scores)),choice]-scores[:,0]
    return np.where(gain>margin,choice,0)


def choose_margin(X,labels,groups):
    """Select conservatism inside the training fold, never on outer artists."""
    covered=labels.any(1);scores=np.zeros(labels.shape)
    for tr,te in StratifiedGroupKFold(3,shuffle=True,random_state=17).split(X,labels[:,0],groups):
        tr=tr[covered[tr]]
        model=estimator().fit(X[tr].reshape(-1,X.shape[-1]),labels[tr].ravel())
        scores[te]=model.decision_function(X[te].reshape(-1,X.shape[-1])).reshape(-1,3)
    # Ties favor keeping the independently estimated tonic.
    margins=[float('inf'),4.,3.,2.,1.,.5,0.]
    counts=[labels[np.arange(len(labels)),guarded_choices(scores,m)].sum() for m in margins]
    return margins[int(np.argmax(counts))]


def main():
    corpus_path=ROOT/'data/overhaul/annotated_corpus.json';audio_path=ROOT/'data/overhaul/saraga_audio_results.json'
    corpus={r['track']:r for r in json.loads(corpus_path.read_text())['rows']}
    audio=json.loads(audio_path.read_text())['rows']
    rows=[{**a['metadata'],'track':a['track'],'audio':corpus[a['track']]['audio'],'tonic':corpus[a['track']]['tonic'],
               'group':'|'.join(sorted(fold(s) for s in corpus[a['track']]['artists']))} for a in audio]
    X=[];candidates=[];started=time.monotonic()
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        for i,path in enumerate(pool.map(extract_evidence,rows)):
            with np.load(path) as z:X.append(z['X']);candidates.append(z['candidates'])
            if (i+1)%25==0:print(f'{i+1}/{len(rows)} harmonic evidence; {time.monotonic()-started:.1f}s',flush=True)
    X=np.array(X);candidates=np.array(candidates)
    truth=np.array([r['tonic'] for r in rows]);groups=np.array([r['group'] for r in rows])
    error=np.abs((1200*np.log2(candidates/truth[:,None])+600)%1200-600)
    labels=error<50;covered=labels.any(1);oof=np.zeros((len(rows),3));fold_ids=np.zeros(len(rows),dtype=int)
    guarded=np.zeros(len(rows),dtype=int);margins=[]
    splits=StratifiedGroupKFold(5,shuffle=True,random_state=42).split(np.arange(len(rows)),labels[:,0],groups)
    for fold_id,(tr,te) in enumerate(splits):
        if set(groups[tr])&set(groups[te]):raise ValueError('Artist leakage')
        margin=choose_margin(X[tr],labels[tr],groups[tr]);margins.append(margin if np.isfinite(margin) else None)
        tr=tr[covered[tr]]
        model=estimator().fit(X[tr].reshape(-1,X.shape[-1]),labels[tr].ravel())
        oof[te]=model.decision_function(X[te].reshape(-1,X.shape[-1])).reshape(-1,3);fold_ids[te]=fold_id
        guarded[te]=guarded_choices(oof[te],margin)
    unguarded=oof.argmax(1)
    choice=guarded;selected=candidates[np.arange(len(rows)),choice]
    correct=error[np.arange(len(rows)),choice]<50
    report=dict(feature_version=TONIC_EVIDENCE_VERSION,corpus_sha256=sha(corpus_path),audio_report_sha256=sha(audio_path),
        n=len(rows),n_artists=len(set(groups)),baseline_correct=int(labels[:,0].sum()),candidate_pool_recall=int(covered.sum()),
        oof_correct=int(correct.sum()),oof_accuracy=float(correct.mean()),
        unguarded_correct=int(labels[np.arange(len(rows)),unguarded].sum()),inner_selected_margins=margins,
        status='five-fold artist-disjoint development evidence; no raga probabilities used',
        rows=[dict(track=r['track'],group=r['group'],fold=int(fold_ids[i]),base_tonic=r['tonic_estimated'],
                   selected_tonic=float(selected[i]),annotated_tonic=r['tonic'],correct=bool(correct[i]),
                   base_correct=bool(labels[i,0]),candidate_index=int(choice[i])) for i,r in enumerate(rows)])
    out=ROOT/'data/overhaul/tonic';out.mkdir(parents=True,exist_ok=True)
    write_json(out/'result.json',report)
    model=estimator().fit(X[covered].reshape(-1,X.shape[-1]),labels[covered].ravel())
    final_margin=choose_margin(X,labels,groups)
    joblib.dump(dict(model=model,margin=final_margin,feature_version=TONIC_EVIDENCE_VERSION,training_report_sha256=sha(out/'result.json'),
                    status='development tonic disambiguator; use OOF decisions for training-corpus evaluation'),out/'model.joblib')
    print({k:v for k,v in report.items() if k!='rows'},flush=True)


if __name__=='__main__':main()
