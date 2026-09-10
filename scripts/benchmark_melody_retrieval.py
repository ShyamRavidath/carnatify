"""Independent-artist song retrieval from real mixed-audio center-60s queries.

References use distributed pitch/tonic annotations. Work IDs define evaluation
truth only; neither names nor oracle ragas enter the distance calculation.
"""
from __future__ import annotations
import argparse,json,os,sys,time
from collections import Counter
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from threadpoolctl import threadpool_limits
from scripts.raga_pipeline import sha,write_json
from normalize_ragas import fold
from carnatify.ml.melody_retrieval import melody_sequence,subsequence_distance,composed_reference_sequences
from carnatify.ml.composition_catalog import CompositionCatalog
from scripts.merge_raga_training import artist_key
from scripts.saraga_recording_identity import attach_recording_ids,same_recording
from carnatify.ml.retrieval_prior import raga_prior_cost
from carnatify.audio.pitch_profiles import cache_suffix
from carnatify.ml.melody_retrieval import directional_distances,directional_cost


def load_query(cache,original_metadata,window_s=60):
    """Load the exact centered query, never slice a differently sized contour."""
    digest=original_metadata['audio_sha256']
    path=Path(cache)/f'{digest[:32]}_{cache_suffix("default",window_s)}.npz'
    with np.load(path,allow_pickle=False) as saved:
        f=saved['f0'];meta=json.loads(str(saved['meta']))
    start,end=meta['start_s'],meta['end_s']
    old_start,old_end=original_metadata['start_s'],original_metadata['end_s']
    # For a centered query, start + end equals the recording duration, even
    # when the entire recording is shorter than the requested context.
    duration=old_start+old_end
    expected_start=max(0.,(duration-window_s)/2.)
    expected_end=expected_start+min(window_s,duration)
    if (meta['audio_sha256']!=digest or meta.get('extraction_profile','default')!='default'
        or not np.isfinite([start,end]).all() or not 0<=start<end
        or end-start>window_s+1e-6 or abs(start+end-old_start-old_end)>1e-6
        or abs(start-expected_start)>1e-6 or abs(end-expected_end)>1e-6
        or start>old_start+1e-6 or end<old_end-1e-6):
        raise ValueError('Exact centered query cache provenance mismatch')
    if window_s==60 and (abs(start-old_start)>1e-6 or abs(end-old_end)>1e-6
                        or meta['tonic_estimated']!=original_metadata['tonic_estimated']):
        raise ValueError('Original query metadata changed')
    return f,meta


def retrieval_summary(rows):
    """Answerability is catalog coverage, independent of extraction success."""
    known=[r for r in rows if r['answerable']]
    return dict(n_queries=len(rows),n_answerable=len(known),
        top1=sum(r['rank']==1 for r in known)/len(known) if known else None,
        top5=sum(r['rank'] is not None and r['rank']<=5 for r in known)/len(known) if known else None,
        mrr=sum(1/r['rank'] if r['rank'] is not None else 0 for r in known)/len(known) if known else None)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--include-unknown',action='store_true')
    ap.add_argument('--transposition-invariant',action='store_true')
    ap.add_argument('--frame-s',type=float,choices=[.25,.5,1.],default=.5)
    ap.add_argument('--reference-scope',choices=['whole','composed'],default='whole')
    ap.add_argument('--query-patches',type=int,choices=[1,3],default=1)
    ap.add_argument('--query-window-s',type=int,choices=[60,180],default=60)
    ap.add_argument('--directional-contrast',action='store_true')
    ap.add_argument('--extra-catalog',type=Path,help='Additional verified references; requires --include-unknown')
    ap.add_argument('--raga-model',type=Path,help='Optional independently trained estimated-raga prior; no oracle raga')
    ap.add_argument('--raga-weight',type=float,default=.1)
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/composition_retrieval.json')
    args=ap.parse_args()
    if not 0<=args.raga_weight<=1:ap.error('--raga-weight must be between zero and one')
    if args.directional_contrast and (args.reference_scope!='whole' or args.query_patches!=1):
        ap.error('Directional contrast is defined only for whole-query, whole-reference alignment')
    if (args.reference_scope!='whole' or args.query_patches!=1 or args.query_window_s!=60 or args.directional_contrast or args.extra_catalog or args.raga_model) and args.out==ROOT/'data/overhaul/composition_retrieval.json':
        ap.error('Use an explicit --out for experimental retrieval settings')
    if args.extra_catalog and (not args.include_unknown or args.reference_scope!='whole' or args.frame_s!=.5):
        ap.error('Extra references require --include-unknown, whole-reference scope and matching 0.5s frames')
    corpus_path=ROOT/'data/overhaul/annotated_corpus.json'
    corpus=json.loads(corpus_path.read_text())['rows']
    if args.extra_catalog:corpus=attach_recording_ids(corpus)
    audio_report_path=ROOT/'data/overhaul/saraga_audio_results.json'
    audio_report=json.loads(audio_report_path.read_text())
    if audio_report['corpus_sha256']!=sha(corpus_path):raise ValueError('Query/corpus provenance mismatch')
    audio_rows={r['track']:r for r in audio_report['rows']}
    raga_bundle=None
    if args.raga_model:
        import joblib
        from carnatify.ml.evaluation_integrity import assert_unseen_tracks,assert_unseen_audio
        from carnatify.ml.inference_runtime import serial_forest_prediction
        from carnatify.ml.melody_features import feature_vector
        raga_bundle=joblib.load(args.raga_model)
        if not raga_bundle.get('training_audio_sha256'):
            raise ValueError('Raga prior requires a training audio hash inventory; legacy Saraga scores were contaminated')
        assert_unseen_tracks(raga_bundle,corpus)
        for audio_row in audio_rows.values():
            assert_unseen_audio(raga_bundle,audio_row['metadata']['audio_sha256'])
        serial_forest_prediction(raga_bundle['model'])
    refs=[];seqs=[];started=time.monotonic()
    for row in corpus:
        if not row['work_id'] or not row['pitch'] or not row['tonic']:continue
        d=np.loadtxt(ROOT/row['pitch']);hop=float(np.median(np.diff(d[:,0])))
        sequence=melody_sequence(d[:,1],row['tonic'],hop,args.frame_s)
        if len(sequence)<8:continue
        refs.append(row)
        seqs.append(composed_reference_sequences(d[:,1],d[:,0],row['tonic'],hop,row['sections'],args.frame_s)
                    if args.reference_scope=='composed' else [sequence])
    counts=Counter(r['work_id'] for r in refs)
    queries=[r for r in refs if r['track'] in audio_rows and (args.include_unknown or counts[r['work_id']]>1)]
    n_original_references=len(refs)
    if args.extra_catalog:
        extra=CompositionCatalog(args.extra_catalog)
        receipt=json.loads(args.extra_catalog.with_suffix('.json').read_text())
        if receipt['catalog_sha256']!=sha(args.extra_catalog):raise ValueError('Additional catalog hash mismatch')
        seen={r['track'] for r in refs}
        for i,meta in enumerate(extra.metadata):
            if meta['track'] in seen:continue
            if not meta.get('artists') or meta.get('identity_evidence')!='explicit_musicbrainz_performance_work_relation':
                raise ValueError('Additional references require artist and explicit work relation provenance')
            a,b=extra.offsets[i:i+2];refs.append(meta);seqs.append([extra.frames[a:b]]);seen.add(meta['track'])
    report=dict(protocol=f'mixed-audio center {args.query_window_s}s; {args.reference_scope} reference annotated melody; no oracle raga or title filter',
        query_window_s=args.query_window_s,
        directional_contrast=args.directional_contrast,
        directional_policy='forward/(forward+reverse); shared pitch shifts; zero/zero maps to .5' if args.directional_contrast else 'disabled',
        corpus_sha256=sha(corpus_path),audio_report_sha256=sha(audio_report_path),
        n_references=len(refs),rows=[],summary={},requires_new_manual_labels=False,
        n_original_references=n_original_references,
        extra_catalog_sha256=sha(args.extra_catalog) if args.extra_catalog else None,
        raga_model_sha256=sha(args.raga_model) if args.raga_model else None,
        raga_prior_weight=args.raga_weight if args.raga_model else 0.,
        raga_prior_policy='estimated posterior only, applied above the model development gate; not production calibrated' if args.raga_model else 'disabled',
        recording_metadata_sha256={r['track']:r['recording_metadata_sha256'] for r in corpus if r.get('recording_metadata_sha256')},
        transposition_invariant=args.transposition_invariant,
        frame_s=args.frame_s,
        reference_scope=args.reference_scope,n_reference_passages=sum(map(len,seqs)),
        query_patches=args.query_patches,query_patch_policy='voiced-time thirds; median independent alignment costs; shared global pitch shift' if args.query_patches==3 else 'whole query',
        coverage_policy='Original whole-reference eligibility retained; removed or too-short passages count as misses',
        status='development retrieval experiment, no validated acceptance threshold')
    with threadpool_limits(limits=1):
        for row in queries:
            ar=audio_rows[row['track']]
            f,meta=load_query(ROOT/'data/overhaul/cache/saraga_audio',ar['metadata'],args.query_window_s)
            digest=meta['audio_sha256']
            query=melody_sequence(f,meta['tonic_estimated'],128/44100,args.frame_s)
            raga_probabilities={}
            if raga_bundle and meta['tonic_estimated'] and np.sum(f>0)*128/44100>=10:
                vector=feature_vector(f,meta['tonic_estimated'],128/44100,raga_bundle['representation'])
                if vector is not None:
                    model=raga_bundle['model'];p=model.predict_proba(vector[None])[0]
                    if p.max()>=raga_bundle['calibration']['gate']['threshold']:
                        raga_probabilities={str(c):float(v) for c,v in zip(model.classes_,p)}
            candidates=[];answerable=False
            for ref,sequences in zip(refs,seqs):
                if (ref['track']==row['track'] or same_recording(ref,row) or ref['source']==row['source'] or
                    ref.get('group')==row['group'] or
                    {artist_key(a) for a in ref['artists']}&{artist_key(a) for a in row['artists']}):continue
                ref_audio=audio_rows.get(ref['track'],{}).get('metadata',{}).get('audio_sha256')
                if ref_audio==digest:continue
                if ref['work_id']==row['work_id']:answerable=True
                reverse=None
                if args.directional_contrast:
                    distance,reverse=directional_distances(query,sequences[0],args.transposition_invariant)
                else:
                    distance=min((subsequence_distance(query,sequence,args.transposition_invariant,args.query_patches)
                                  for sequence in sequences),default=float('inf'))
                if np.isfinite(distance):
                    alignment=directional_cost(distance,reverse) if args.directional_contrast else distance
                    candidates.append(dict(track=ref['track'],work_id=ref['work_id'],title=ref['title'],
                                           raga=ref['raga'],distance=distance,reverse_distance=reverse,
                                           alignment_cost=alignment,
                                           ranking_cost=raga_prior_cost(alignment,ref['raga'],raga_probabilities,args.raga_weight)))
            candidates.sort(key=lambda r:r['ranking_cost'])
            # Rank work identities, not multiple renditions of the same identity.
            unique=[];seen=set()
            for c in candidates:
                if c['work_id'] not in seen:unique.append(c);seen.add(c['work_id'])
            rank=next((i+1 for i,c in enumerate(unique) if c['work_id']==row['work_id']),None)
            result=dict(track=row['track'],work_id=row['work_id'],raga=row['raga'],
                n_candidates=len(unique),answerable=answerable,rank=rank,
                top5=unique[:5],query_voiced_frames=len(query),query_metadata=meta)
            result['estimated_raga_prior_applied']=bool(raga_probabilities)
            result['estimated_raga_probabilities']=raga_probabilities
            report['rows'].append(result)
            report['summary']=retrieval_summary(report['rows'])
            report['elapsed_s']=time.monotonic()-started;write_json(args.out,report)
            if len(report['rows'])%25==0 or len(report['rows'])==len(queries):
                print(f'{len(report["rows"])}/{len(queries)} queries; {report["elapsed_s"]:.1f}s',flush=True)
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__':main()
