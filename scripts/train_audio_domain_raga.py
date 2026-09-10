"""Artist-held-out domain adaptation using existing labeled mixed-audio clips.

The old archive/reference corpus remains fixed. Saraga is explicitly development
data, not an independent test after this experiment. Every Saraga prediction is
made without training on that artist. No query annotation supplies its tonic.
"""
from __future__ import annotations
import json,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits
from normalize_ragas import fold
from scripts.raga_pipeline import sha,write_json,load_features
from scripts.merge_raga_training import artist_key,known_artist
from carnatify.ml.melody_features import feature_vector,FEATURE_VERSIONS
from carnatify.ml.distribution_classifier import DistributionKernelRidge


def main():
    base=ROOT/'data/overhaul/combined';out=ROOT/'data/overhaul/audio_domain';out.mkdir(parents=True,exist_ok=True)
    corpus_path=ROOT/'data/overhaul/annotated_corpus.json'
    baseline_path=ROOT/'data/overhaul/saraga_combined_results.json'
    corpus={r['track']:r for r in json.loads(corpus_path.read_text())['rows']}
    baseline=json.loads(baseline_path.read_text());rows=baseline['rows']
    original=joblib.load(base/'raga_ridge.joblib');classes=original['model'].classes_
    canonical={fold(c):str(c) for c in classes}
    z=load_features(base);Xbase=z['legacy'];ybase=z['y'];tracks=z['track']
    prov={r['stem']:r for r in json.loads((ROOT/'data/qmax_audit/provenance.json').read_text())}
    manifest=json.loads((base/'manifest.json').read_text())['rows']
    trained={artist_key(a) for r in manifest if (a:=known_artist(r,prov))}
    groups=[];estimated=[];annotated=[];labels=[]
    for row in rows:
        truth=corpus[row['track']];artists={artist_key(a) for a in truth['artists']}
        if not artists or artists&trained:raise ValueError('Missing artist or overlap with fixed base corpus')
        groups.append('|'.join(sorted(artists)));labels.append(canonical.get(fold(truth['raga'])))
        meta=row['metadata'];path=ROOT/f'data/overhaul/cache/saraga_audio/{meta["audio_sha256"][:32]}_center60_v1.npz'
        with np.load(path) as cache:f=cache['f0']
        estimated.append(feature_vector(f,meta['tonic_estimated'],128/44100,'voiced'))
        annotated.append(feature_vector(f,truth['tonic'],128/44100,'voiced'))
    if any(v is None for v in estimated+annotated):raise ValueError('Missing feature; add explicit abstention handling')
    Xe=np.stack(estimated);Xa=np.stack(annotated);groups=np.array(groups);labels=np.array(labels,dtype=object)
    # Corpus currently has one lead artist per recording. Guard future ensemble
    # metadata: string group equality alone is insufficient for partial overlap.
    group_artists=[set(g.split('|')) for g in groups]
    count=Counter(tracks);base_weight=np.array([1/count[t] for t in tracks])
    oof=np.zeros((len(rows),len(classes)));fold_ids=np.zeros(len(rows),dtype=int)
    started=time.monotonic()
    with threadpool_limits(limits=4):
        for fold_id,(tr,te) in enumerate(GroupKFold(5).split(Xe,groups=groups)):
            if set.union(*[group_artists[i] for i in tr])&set.union(*[group_artists[i] for i in te]):
                raise ValueError('Artist leakage in adaptation split')
            tr=tr[np.array([labels[i] is not None for i in tr])]
            X=np.r_[Xbase,Xa[tr]];y=np.r_[ybase,labels[tr].astype(str)]
            weight=np.r_[base_weight,np.ones(len(tr))];weight/=weight.mean()
            model=DistributionKernelRidge(mode='tdms',temperature=original['model'].temperature).fit(X,y,sample_weight=weight)
            if not np.array_equal(model.classes_,classes):raise ValueError('Adaptation changed frozen vocabulary')
            oof[te]=model.predict_proba(Xe[te]);fold_ids[te]=fold_id
            print(f'Fold {fold_id+1}/5: {len(tr)} added tracks, {len(te)} held-out queries; {time.monotonic()-started:.1f}s',flush=True)
        pred=classes[oof.argmax(1)]
        correct=np.array([fold(p)==fold(r['raga']) for p,r in zip(pred,rows)])
        known=np.array([v is not None for v in labels])
        report=dict(protocol='fixed base plus annotated-tonic mixed-audio training; artist-held-out estimated-tonic inference',
            status='domain adaptation development CV; not a new independent test',
            corpus_sha256=sha(corpus_path),base_feature_sha256=sha(base/'features.npz'),baseline_sha256=sha(baseline_path),
            n=len(rows),n_known=int(known.sum()),correct=int(correct.sum()),known_top1=float(correct[known].mean()),
            baseline_correct=sum(r['predictions']['combined_estimated']['correct'] for r in rows),
            rows=[dict(track=r['track'],raga=r['raga'],group=str(groups[i]),fold=int(fold_ids[i]),
                       prediction=str(pred[i]),correct=bool(correct[i]),in_vocabulary=bool(known[i])) for i,r in enumerate(rows)])
        write_json(out/'result.json',report)
        np.savez_compressed(out/'oof.npz',p=oof,track=np.array([r['track'] for r in rows]),classes=classes,fold=fold_ids)
        # Full fit is a separate candidate. Do not score it on Saraga as held-out.
        X=np.r_[Xbase,Xa[known]];y=np.r_[ybase,labels[known].astype(str)]
        weight=np.r_[base_weight,np.ones(known.sum())];weight/=weight.mean()
        model=DistributionKernelRidge(mode='tdms',temperature=original['model'].temperature).fit(X,y,sample_weight=weight)
        joblib.dump(dict(model=model,representation='voiced',feature_version=FEATURE_VERSIONS['voiced'],
            training_report_sha256=sha(out/'result.json'),status='development; includes Saraga training audio',
            training_track_ids=[r['track'] for i,r in enumerate(rows) if known[i]],
            calibration=dict(status='uncalibrated after domain adaptation',gate=dict(threshold=1.000001))),out/'raga.joblib')
    print({k:v for k,v in report.items() if k!='rows'},flush=True)


if __name__=='__main__':main()
