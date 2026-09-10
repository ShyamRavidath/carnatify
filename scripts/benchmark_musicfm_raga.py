"""Matched 10s MusicFM/pitch ablation with connected artist/source holdouts.

Small, selected-vocabulary development probe, not production accuracy. No
hyperparameter search or acceptance threshold is fitted to held-out outcomes.
"""
import argparse,collections,hashlib,importlib.metadata,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['HF_HOME']=str(ROOT/'data/overhaul/cache/huggingface')
sys.path[:0]=[str(ROOT/'data/overhaul/runtime_deps'),str(ROOT),str(ROOT/'src')]
import numpy as np
import soundfile as sf
from sklearn.kernel_ridge import KernelRidge
from sklearn.utils.class_weight import compute_sample_weight
from normalize_ragas import fold
from scripts.raga_audit_protocol import DSU
from scripts.raga_pipeline import sha,write_json
from scripts.summarize_overhaul import paired_interval
from carnatify.audio.musicfm_frontend import MusicFM,VERSION,HASHES,TONIC_SHIFT_POLICY,tonic_normalize_audio
from carnatify.audio.melody_frontend import extract_query,HOP_S,VERSION as PITCH_VERSION
from carnatify.audio.utils import load_audio_window
from carnatify.audio.cache_io import atomic_npz
from carnatify.ml.melody_features import feature_vector,FEATURE_VERSIONS


def admit(rows,audio_hashes,min_count=5):
    by_hash=collections.defaultdict(list)
    for row in rows:by_hash[audio_hashes[row['track']]].append(row)
    unique=[];conflicts=[]
    for digest,bucket in sorted(by_hash.items()):
        if len({fold(r['raga']) for r in bucket})!=1:
            conflicts.append(digest);continue
        row=min(bucket,key=lambda r:r['track'])
        if fold(row['raga'])=='ragamalika':continue
        unique.append(row)
    counts=collections.Counter(fold(r['raga']) for r in unique)
    return [r for r in unique if counts[fold(r['raga'])]>=min_count],conflicts


def groups_for(rows):
    dsu=DSU()
    for row in rows:
        key='track:'+row['track']
        if not row['artists'] or not row['source']:raise ValueError('Missing group provenance')
        for artist in row['artists']:
            if not fold(artist):raise ValueError('Empty normalized artist')
            dsu.union(key,'artist:'+fold(artist))
        dsu.union(key,'source:'+row['source'])
        dsu.union(key,'audio:'+row['audio_sha256'])
    return np.array([dsu.find('track:'+r['track']) for r in rows])


def unit_rows(X):
    X=np.asarray(X,dtype=float)
    return X/np.maximum(np.linalg.norm(X,axis=1,keepdims=True),1e-12)


def crossfit(X,valid,y,groups):
    X=unit_rows(X);valid=np.asarray(valid,dtype=bool);y=np.asarray(y);groups=np.asarray(groups)
    if not np.isfinite(X).all():raise ValueError('Nonfinite features')
    if len(np.unique(groups))<2:raise ValueError('No independent holdout')
    predictions=[None]*len(y);folds=[]
    for group in np.unique(groups):
        tr=(groups!=group)&valid;te=(groups==group)&valid
        classes=np.unique(y[tr])
        if len(classes):
            Y=(y[tr,None]==classes[None,:]).astype(float)
            model=KernelRidge(alpha=.1,kernel='rbf',gamma=2).fit(
                X[tr],Y,sample_weight=compute_sample_weight('balanced',y[tr]))
            if te.any():
                values=model.predict(X[te])
                for index,label in zip(np.flatnonzero(te),classes[values.argmax(axis=1)]):
                    predictions[index]=str(label)
        folds.append(dict(group=str(group),n_train=int(tr.sum()),n_test=int((groups==group).sum()),
                          training_classes=classes.tolist()))
    correct=np.array([p==t for p,t in zip(predictions,y)])
    return dict(n=len(y),n_valid=int(valid.sum()),n_correct=int(correct.sum()),
                accuracy=float(correct.mean()),macro_recall=float(np.mean([
                    correct[y==c].mean() for c in np.unique(y)])),predictions=predictions,folds=folds)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tonic-normalize',action='store_true',help='Separate fixed estimated-tonic waveform ablation')
    args=ap.parse_args()
    base=ROOT/'data/overhaul/musicfm_raga_probe'
    out=base.with_name(base.name+'_tonic') if args.tonic_normalize else base
    out.mkdir(parents=True,exist_ok=True)
    cp=ROOT/'data/overhaul/annotated_corpus_v2.json'
    source=ROOT/'data/overhaul/saraga_audio_results.json'
    audio_report=json.loads(source.read_text())
    if audio_report['corpus_sha256']!=sha(ROOT/'data/overhaul/annotated_corpus.json'):
        raise ValueError('Audio source provenance changed')
    hashes={r['track']:r['metadata']['audio_sha256'] for r in audio_report['rows']}
    chosen,conflicts=admit(json.loads(cp.read_text())['rows'],hashes)
    chosen=sorted(chosen,key=lambda r:hashlib.sha256(r['track'].encode()).hexdigest())
    queries=[]
    for row in chosen:
        audio=ROOT/row['audio']
        if sha(audio)!=hashes[row['track']]:raise ValueError('Audio changed')
        duration=sf.info(audio).duration
        if duration<10:raise ValueError('Admitted source shorter than fixed context')
        queries.append(dict(track=row['track'],audio=row['audio'],audio_sha256=hashes[row['track']],
                            artists=row['artists'],source=row['source'],raga=row['raga'],
                            start_s=(duration-10)/2,duration_s=10.))
    groups=groups_for(queries)
    plan=dict(corpus_sha256=sha(cp),audio_report_sha256=sha(source),queries=queries,
        policy='>=5 unique recordings per single raga; exact-hash conflicts excluded; centered 10s; connected artist/source holdouts',
        excluded_conflicting_hashes=conflicts,groups=groups.tolist(),musicfm_version=VERSION,artifacts=HASHES,
        pitch_version=PITCH_VERSION,feature_version=FEATURE_VERSIONS['voiced'],layer=7,
        classifier='class-balanced RBF kernel ridge; alpha=.1 gamma=2; per-arm L2-normalized vectors; no tuning',
        runtime={p:importlib.metadata.version(p) for p in ['torch','torchaudio','transformers','einops','scikit-learn']})
    if args.tonic_normalize:
        original=json.loads((base/'plan.json').read_text())
        if original!=plan:raise ValueError('Normalized arm must match the original cohort/runtime/classifier')
        plan.update(base_plan_sha256=sha(base/'plan.json'),tonic_shift_policy=TONIC_SHIFT_POLICY,
                    librosa_version=importlib.metadata.version('librosa'))
    pp=out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Frozen ablation protocol changed')
    if not pp.exists():write_json(pp,plan)
    print(f'Frozen {len(queries)} recordings / {len(set(q["raga"] for q in queries))} ragas / {len(np.unique(groups))} groups',flush=True)
    import torch
    torch.set_num_threads(4);model=None;pitch=[];embeddings=[];valid=[];embedding_valid=[];started=time.monotonic()
    for index,query in enumerate(queries):
        target=out/(hashlib.sha256(query['track'].encode()).hexdigest()+'.npz')
        if target.exists():
            with np.load(target,allow_pickle=False) as z:
                metadata=json.loads(str(z['metadata']))
                if metadata['plan_sha256']!=sha(pp) or metadata['query']!=query:
                    raise ValueError('Feature receipt mismatch')
                p=z['pitch'];e=z['embedding'];ok=bool(z['pitch_valid'])
                eok=bool(z['embedding_valid']) if 'embedding_valid' in z.files else True
        else:
            if model is None:model=MusicFM(ROOT/'data/overhaul/models/musicfm')
            y,sr,diagnostics=load_audio_window(ROOT/query['audio'],query['start_s'],10.,24000)
            f,meta=extract_query(ROOT/query['audio'],query['audio_sha256'],query['start_s'],10.,
                                 ROOT/'data/overhaul/cache/concerts/queries')
            p=feature_vector(f,meta['tonic_hz'],HOP_S,'voiced') if meta['tonic_hz'] else None
            ok=p is not None
            if not ok:p=np.zeros(4800)
            metadata=dict(plan_sha256=sha(pp),query=query,pitch=meta,audio=diagnostics,
                          waveform_sha256=hashlib.sha256(y.tobytes()).hexdigest())
            eok=True
            if args.tonic_normalize:
                if meta['tonic_hz']:
                    y,steps=tonic_normalize_audio(y,sr,meta['tonic_hz'])
                    metadata.update(pitch_shift_semitones=steps,
                                    normalized_waveform_sha256=hashlib.sha256(y.tobytes()).hexdigest())
                else:eok=False
            e=model.encode(y,sr).mean(axis=0) if eok else np.zeros(1024)
            atomic_npz(target,pitch=p,embedding=e,pitch_valid=ok,embedding_valid=eok,
                       metadata=json.dumps(metadata,allow_nan=False))
        if p.shape!=(4800,) or e.shape!=(1024,) or not np.isfinite(p).all() or not np.isfinite(e).all():
            raise ValueError('Invalid feature receipt')
        pitch.append(p);embeddings.append(e);valid.append(ok);embedding_valid.append(eok)
        write_json(out/'progress.json',dict(plan_sha256=sha(pp),n_complete=index+1,n_total=len(queries)))
        print(f'{index+1}/{len(queries)} {query["track"]}; pitch valid={ok}; elapsed {time.monotonic()-started:.1f}s',flush=True)
    P=unit_rows(pitch);E=unit_rows(embeddings);y=np.array([q['raga'] for q in queries]);arms={}
    for name,X,mask in [('pitch',P,valid),('musicfm',E,embedding_valid),
                        ('combined',np.c_[P,E]/np.sqrt(2),np.asarray(valid)&embedding_valid)]:
        arms[name]=crossfit(X,mask,y,groups)
    base=np.array(arms['pitch']['predictions'])==y
    comparisons={name:paired_interval((np.array(arm['predictions'])==y).astype(int)-base.astype(int),groups)
                 for name,arm in arms.items() if name!='pitch'}
    report=dict(status='selected-vocabulary grouped development ablation; not natural-concert production accuracy',
                plan_sha256=sha(pp),n_queries=len(y),n_groups=len(np.unique(groups)),arms=arms,
                paired_artist_component_differences=comparisons,elapsed_s=time.monotonic()-started)
    write_json(out/'result.json',report)
    print(json.dumps({name:{k:v for k,v in arm.items() if k not in ('predictions','folds')} for name,arm in arms.items()},indent=2))


if __name__=='__main__':main()
