"""Independent Saraga audio evaluation using only existing annotations.

Both the candidate and the audited RF process the identical bounded audio query.
Estimated-tonic and annotated-tonic readouts separate front-end and classifier
errors. Predictions are not used to alter labels or select clips.
"""
from __future__ import annotations
import argparse,json,os,sys,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json
from normalize_ragas import fold
from carnatify.ml.melody_features import feature_vector
from carnatify.audio.pitch_profiles import PROFILES,melodia_parameters,cache_suffix,HPSS_PARAMETERS
from carnatify.ml.evaluation_integrity import assert_unseen_tracks,assert_unseen_audio
from carnatify.ml.raga_runtime import RagaCandidate,RagaGate,score_contour
from carnatify.audio.melody_frontend import extract_waveform
from carnatify.audio.cache_io import atomic_npz


def extract(row):
    path=ROOT/row['audio'];audio_hash=sha(path)
    cache=ROOT/'data/overhaul/cache/saraga_audio';cache.mkdir(parents=True,exist_ok=True)
    profile=row.get('extraction_profile','default');window_s=row.get('window_s',60)
    target=cache/f'{audio_hash[:32]}_{cache_suffix(profile,window_s)}.npz'
    if target.exists():return str(target)
    # A cache hit needs no DSP imports or decoder initialization. In spawned
    # workers these imports previously added ~95 seconds to every cached run.
    import soundfile as sf
    from carnatify.audio.utils import load_audio_window
    length=sf.info(str(path)).duration
    start=max(0,(length-window_s)/2);duration=min(window_s,length)
    y,sr,diag=load_audio_window(path,start,duration)
    tonic=None;failure=None
    try:
        f0,tonic=extract_waveform(y,sr,profile)
    except RuntimeError as exc:
        f0=np.zeros(0);failure=str(exc)
    meta=dict(audio_sha256=audio_hash,start_s=start,end_s=start+duration,
              tonic_estimated=tonic,audio=diag,extraction_failure=failure,extraction_profile=profile,
              hpss_parameters=HPSS_PARAMETERS if profile=='harmonic' else None)
    atomic_npz(target,f0=f0,meta=json.dumps(meta,allow_nan=False))
    return str(target)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--limit',type=int,default=0)
    ap.add_argument('--corpus',type=Path,default=ROOT/'data/overhaul/annotated_corpus.json')
    ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--extraction-profile',choices=sorted(PROFILES),default='default')
    ap.add_argument('--window-s',type=int,choices=[60,180],default=60)
    ap.add_argument('--model',default=str(ROOT/'data/overhaul/raga_ridge.joblib'),
                    help='Registry name from configs/raga_candidates.json or a bundle path')
    ap.add_argument('--gate',type=Path,help='Registered gate JSON; without it the bundle legacy gate is reported')
    ap.add_argument('--name',default='ridge',help='Candidate name in the result arms')
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/saraga_audio_results.json')
    ap.add_argument('--skip-baseline',action='store_true',help='Evaluate candidate alone; legacy baseline has incomplete byte provenance')
    ap.add_argument('--allow-unverified-audio-split',action='store_true',
                    help='Explicit contaminated/unverified development diagnostic; never an independent score')
    args=ap.parse_args()
    corpus=json.loads(args.corpus.read_text())
    rows=sorted([r for r in corpus['rows'] if not r['known_source_overlap']],key=lambda r:r['track'])
    if args.limit:rows=rows[:args.limit]
    rows=[{**r,'extraction_profile':args.extraction_profile,'window_s':args.window_s} for r in rows]
    if args.name=='audited_rf':raise ValueError('Candidate name collides with baseline')
    candidates={args.name:RagaCandidate.load(args.model)}
    if not args.skip_baseline:
        candidates['audited_rf']=RagaCandidate.load(str(ROOT/'data/architecture_audit/candidate.joblib'))
    gate=RagaGate.load(args.gate) if args.gate else None
    models={}
    for name,candidate in candidates.items():
        bundle=candidate.bundle
        if not bundle.get('training_audio_sha256') and not args.allow_unverified_audio_split:
            raise ValueError(f'{name} has no training audio hash inventory; use an audited candidate, '
                             '--skip-baseline, or explicitly --allow-unverified-audio-split for diagnostics')
        assert_unseen_tracks(bundle,rows)
        models[name]=bundle
    report=dict(protocol=f'all eligible Saraga tracks; deterministic center {args.window_s} seconds; existing labels only',
        corpus_sha256=sha(args.corpus),model_sha256=candidates[args.name].sha256,
        models={name:c.describe() for name,c in candidates.items()},gate=gate.describe() if gate else None,
        baseline_sha256=sha(ROOT/'data/architecture_audit/candidate.joblib'),
        n_selected=len(rows),rows=[],summary={},requires_new_manual_labels=False,
        extraction_profile=args.extraction_profile,window_s=args.window_s,
        melodia_parameters=melodia_parameters(args.extraction_profile))
    report['audio_identity_scope']={name:bundle.get('audio_identity_scope','no training audio hash inventory')
                                    for name,bundle in models.items()}
    report['split_status']='exact-byte guarded development; transformed copies and unknown artists unresolved'
    if args.allow_unverified_audio_split:
        report['split_status']='explicitly unverified development diagnostic; not independent accuracy'
    if args.skip_baseline:report['baseline_sha256']=None
    start=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        for row,path in zip(rows,pool.map(extract,rows)):
            with np.load(path) as z:
                f0=z['f0'];meta=json.loads(str(z['meta']))
            result=dict(track=row['track'],source=row['source'],raga=row['raga'],metadata=meta,predictions={})
            voiced=float(np.sum(f0>0)*128/44100)
            for name,candidate in candidates.items():
                bundle=candidate.bundle
                assert_unseen_audio(bundle,meta['audio_sha256'])
                for tonic_name,tonic in [('estimated',meta['tonic_estimated']),('annotated',row['tonic'])]:
                    key=f'{name}_{tonic_name}'
                    truth_key=fold(row['raga']);class_keys=[fold(c) for c in candidate.classes]
                    if len(set(class_keys))!=len(class_keys):raise ValueError('Duplicate canonical model classes')
                    tonic=tonic if tonic is not None and np.isfinite(float(tonic)) else None
                    scored=score_contour(candidate,f0,float(tonic) if tonic else None,128/44100,gate)
                    pred=dict(in_vocabulary=truth_key in class_keys,correct=False,top3_correct=False,
                              answered=scored['answered'],accepted=False,top3=[],voiced_s=voiced,
                              reason=scored['reason'],signals=scored['signals'])
                    if scored['answered']:
                        top=[r['raga'] for r in scored['ranked'][:3]]
                        pred.update(top3=top,correct=fold(top[0])==truth_key,
                                    top3_correct=truth_key in [fold(c) for c in top],
                                    confidence=scored['ranked'][0]['probability'])
                        if gate is not None:pred['accepted']=scored['accepted']
                        else:
                            # Legacy in-bundle gate on the calibrated posterior; measured unsafe (ABSTAIN_GATE.md).
                            threshold=bundle.get('calibration',{}).get('gate',{}).get('threshold',1.000001)
                            pred['accepted']=bool(scored['ranked'][0]['probability']>=threshold)
                    result['predictions'][key]=pred
            report['rows'].append(result)
            for arm in result['predictions']:
                all_preds=[r['predictions'][arm] for r in report['rows']]
                known=[r for r in all_preds if r['in_vocabulary']]
                accepted=[r for r in all_preds if r['accepted']]
                unknown=[r for r in all_preds if not r['in_vocabulary']]
                report['summary'][arm]=dict(n=len(all_preds),n_in_vocabulary=len(known),
                    n_answered=sum(p['answered'] for p in all_preds),
                    correct=sum(p['correct'] for p in all_preds),
                    top1_all=float(np.mean([p['correct'] for p in all_preds])),
                    top1_in_vocabulary=float(np.mean([p['correct'] for p in known])) if known else None,
                    top3_in_vocabulary=float(np.mean([p['top3_correct'] for p in known])) if known else None,
                    n_accepted=len(accepted),coverage=len(accepted)/len(all_preds),
                    accepted_precision=float(np.mean([p['correct'] for p in accepted])) if accepted else None,
                    oov_false_acceptance=float(np.mean([p['accepted'] for p in unknown])) if unknown else None)
            report['elapsed_s']=time.monotonic()-start
            write_json(args.out,report)
            if len(report['rows'])%25==0 or len(report['rows'])==len(rows):
                print(f'{len(report["rows"])}/{len(rows)} tracks; {report["elapsed_s"]:.1f}s',flush=True)
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__':main()
