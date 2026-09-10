"""Fixed three-tonic posterior mixture on the inspected development queries.

No oracle tonic/raga enters scoring. Original confidence gates are not reused.
"""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from normalize_ragas import fold
from scripts.raga_pipeline import sha,write_json
from scripts.benchmark_melody_retrieval import load_query
from carnatify.audio.tonic_evidence import tonic_candidates
from carnatify.ml.melody_features import feature_vector
from carnatify.ml.evaluation_integrity import assert_unseen_audio,assert_unseen_tracks


def mixture(probabilities,weights=(.8,.1,.1)):
    p=np.asarray(probabilities,dtype=float);w=np.asarray(weights,dtype=float)
    if p.ndim!=2 or p.shape[0]!=3 or w.shape!=(3,) or not np.isfinite(p).all() or not np.isfinite(w).all():
        raise ValueError('Invalid tonic posterior layout')
    if (p<0).any() or (w<0).any() or not np.isclose(w.sum(),1) or not np.allclose(p.sum(1),1):
        raise ValueError('Expected normalized nonnegative probabilities')
    return w@p


def main():
    run=ROOT/'data/overhaul/file_tag_guarded'
    model_path=run/'raga.joblib';baseline=run/'evaluation.json'
    out=ROOT/'data/overhaul/tonic_marginalization'
    prior=json.loads(baseline.read_text());bundle=joblib.load(model_path);model=bundle['model']
    if prior['model_sha256']!=sha(model_path):raise ValueError('Baseline model changed')
    if not bundle.get('training_audio_sha256'):raise ValueError('Unverified training audio split')
    assert_unseen_tracks(bundle,prior['rows'])
    plan=dict(model_sha256=sha(model_path),baseline_sha256=sha(baseline),script_sha256=sha(Path(__file__)),
        weights=[.8,.1,.1],tonic_offsets_semitones=[0,5,7],queries=[r['track'] for r in prior['rows']],
        policy='fixed posterior mixture; no raga-conditioned tonic selection, threshold fitting or model export')
    pp=out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Frozen protocol changed')
    write_json(pp,plan);results=[];classes=np.asarray(model.classes_)
    with threadpool_limits(limits=4):
        for row in prior['rows']:
            meta=row['metadata'];assert_unseen_audio(bundle,meta['audio_sha256'])
            f,loaded=load_query(ROOT/'data/overhaul/cache/saraga_audio',meta,180)
            if loaded!=meta:raise ValueError('Baseline query metadata changed')
            candidates=tonic_candidates(meta['tonic_estimated'])
            vectors=[feature_vector(f,t,128/44100,bundle['representation']) for t in candidates]
            if any(v is None for v in vectors):raise ValueError('Unexpected missing baseline feature')
            p=model.predict_proba(np.stack(vectors));combined=mixture(p)
            order=np.argsort(-p[0])[:3]
            if classes[order].tolist()!=row['predictions']['candidate_estimated']['top3']:
                raise ValueError('Baseline predictions not reproduced')
            ranking=np.argsort(-combined);truth=fold(row['raga'])
            results.append(dict(track=row['track'],raga=row['raga'],
                in_vocabulary=row['predictions']['candidate_estimated']['in_vocabulary'],
                baseline_correct=row['predictions']['candidate_estimated']['correct'],
                mixture_correct=fold(classes[ranking[0]])==truth,
                mixture_top3_correct=truth in [fold(c) for c in classes[ranking[:3]]],
                tonic_candidates_hz=candidates.tolist(),top3=classes[ranking[:3]].tolist(),
                mixture_max_probability=float(combined.max())))
    known=[r for r in results if r['in_vocabulary']]
    summary=dict(n=len(results),n_known=len(known),baseline_correct=sum(r['baseline_correct'] for r in results),
        mixture_correct=sum(r['mixture_correct'] for r in results),
        mixture_top3_known=sum(r['mixture_top3_correct'] for r in known))
    write_json(out/'result.json',dict(plan_sha256=sha(pp),rows=results,summary=summary,
        status='inspected development ablation; no production rejection gate or independent accuracy claim'))
    print(json.dumps(summary))


if __name__=='__main__':main()
