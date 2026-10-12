"""Oracle-boundary field diagnostic from existing labels; no new labeling.

One deterministic centered query per high-confidence primary item. This does
not evaluate automatic boundaries or establish source/artist independence.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
import numpy as np
from normalize_ragas import fold
from scripts.raga_pipeline import sha, write_json
from scripts.long_concert_score import validate_intervals
from carnatify.audio.melody_frontend import extract_query, HOP_S, VERSION
from carnatify.ml.melody_features import feature_vector
from carnatify.ml.raga_runtime import RagaCandidate, RagaGate, score_contour


def plan_queries(labels, duration=180):
    if duration not in (60, 180):
        raise ValueError('Unsupported query duration')
    items = {}
    for row in labels['intervals']:
        if row['primary'] and row['confidence'] == 'high':
            items.setdefault(row['item_id'], []).append(row)
    queries = []
    for item, intervals in sorted(items.items()):
        if len({(r['concert'], r['raga']) for r in intervals}) != 1:
            raise ValueError('Contradictory item identity')
        row = min(intervals, key=lambda r: (-(r['end_s']-r['start_s']), r['start_s']))
        length = min(duration, row['end_s']-row['start_s'])
        start = (row['start_s']+row['end_s']-length)/2
        queries.append(dict(item_id=item, concert=row['concert'], truth=row['raga'],
                            start_s=start, duration_s=length))
    return queries


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--models', nargs='+', required=True,
                    help='Registry names from configs/raga_candidates.json or bundle paths')
    ap.add_argument('--gate', type=Path, help='Registered gate JSON to report (never tuned here)')
    ap.add_argument('--labels', type=Path, default=ROOT/'data/architecture_audit/label_intervals.json')
    ap.add_argument('--window-s', type=int, choices=[60, 180], default=180)
    ap.add_argument('--profile', choices=['default', 'harmonic'], default='default')
    ap.add_argument('--pitch-frontend',choices=['melodia','rmvpe','demucs'],default='melodia')
    ap.add_argument('--demucs-checkpoint',type=Path,help='Locally cached checksum-pinned htdemucs checkpoint')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--tonic-mixture',action='store_true',help='Fixed experimental 0.8/0.1/0.1 Sa/Pa posterior mixture; no gate')
    args = ap.parse_args()
    if args.tonic_mixture and args.gate:
        ap.error('--tonic-mixture replaces the ranking the gate scored; it cannot be combined with --gate')
    if args.pitch_frontend!='melodia' and args.profile!='default':
        ap.error('Alternative frontends require the unchanged original-mix tonic profile')
    separator=None
    if args.pitch_frontend=='demucs':
        if not args.demucs_checkpoint:ap.error('Demucs requires an explicit local --demucs-checkpoint')
        import torch
        torch.set_num_threads(4)
        from carnatify.audio.demucs_frontend import VocalSeparator,cached_query as separated_query
        separator=VocalSeparator(args.demucs_checkpoint)
    rmvpe=None
    if args.pitch_frontend=='rmvpe':
        import torch
        torch.set_num_threads(4)
        from carnatify.audio.rmvpe_frontend import RMVPEOnnx,cached_query
        rmvpe=RMVPEOnnx(ROOT/'data/overhaul/models/rmvpe/rmvpe.onnx')
    labels = json.loads(args.labels.read_text())
    if sha(ROOT/labels['source']) != labels['source_sha256']:
        raise ValueError('Existing label source changed')
    frozen = json.loads((ROOT/'data/long_concerts/FROZEN_CONCERTS.json').read_text())
    concerts = validate_intervals(labels, frozen)
    queries = plan_queries(labels, args.window_s)
    candidates = {ref: RagaCandidate.load(ref) for ref in args.models}
    gate = RagaGate.load(args.gate) if args.gate else None
    paths = {}
    for concert in {q['concert'] for q in queries}:
        path = ROOT/'data/long_concerts/audio'/concerts[concert]['file']
        if sha(path) != concerts[concert]['sha256']:
            raise ValueError('Frozen concert changed')
        paths[concert] = path
    report = dict(status='existing-label oracle-boundary field diagnostic; not fresh or artist-independence proof',
                  query_policy='longest explicit interval per primary item; centered fixed-duration query',
                  label_manifest_sha256=sha(args.labels), query_frontend=VERSION,
                  model_sha256={ref: c.sha256 for ref, c in candidates.items()},
                  models={ref: c.describe() for ref, c in candidates.items()},
                  gate=gate.describe() if gate else None,
                  profile=args.profile, window_s=args.window_s, rows=[], summary={})
    report['pitch_frontend']=args.pitch_frontend
    if args.tonic_mixture:
        report['tonic_policy']='fixed posterior mixture at 0,5,7 semitones with weights 0.8,0.1,0.1; no production gate'
    totals = {name: dict(n=0, correct=0, n_in_vocabulary=0, correct_in_vocabulary=0, top3_in_vocabulary=0,
                         n_accepted=0, accepted_correct=0, accepted_oov=0) for name in candidates}
    report['summary'] = totals
    for query in queries:
        concert = query['concert']
        f0, meta = extract_query(paths[concert], concerts[concert]['sha256'],
                                query['start_s'], query['duration_s'],
                                ROOT/'data/overhaul/cache/concerts/queries', args.profile)
        row = {**query, 'metadata': meta, 'predictions': {}}
        hop_s=HOP_S
        if rmvpe is not None:
            f0,rmvpe_contract=cached_query(paths[concert],concerts[concert]['sha256'],
                query['start_s'],query['duration_s'],ROOT/'data/overhaul/cache/rmvpe',rmvpe)
            hop_s=rmvpe_contract['hop_s'];row['rmvpe_contract']=rmvpe_contract
        if separator is not None:
            f0,separation=separated_query(paths[concert],concerts[concert]['sha256'],
                query['start_s'],query['duration_s'],ROOT/'data/overhaul/cache/demucs',separator)
            row['separation']=separation
        for name, candidate in candidates.items():
            result = score_contour(candidate, f0, meta['tonic_hz'], hop_s, gate)
            pred = dict(correct=False, answered=result['answered'], top3=[], reason=result['reason'],
                        in_vocabulary=fold(query['truth']) in {fold(c) for c in candidate.classes},
                        accepted=result['accepted'], signals=result['signals'])
            if result['answered']:
                top = [r['raga'] for r in result['ranked'][:3]]
                confidence = result['ranked'][0]['probability']
                if args.tonic_mixture:
                    from carnatify.audio.tonic_evidence import tonic_candidates
                    from scripts.benchmark_tonic_marginalization import mixture
                    model = candidate.model
                    vectors=[feature_vector(f0,t,hop_s,candidate.representation)
                             for t in tonic_candidates(meta['tonic_hz'])]
                    if any(v is None for v in vectors):raise ValueError('Missing tonic candidate feature')
                    p=mixture(model.predict_proba(np.stack(vectors)))
                    order = np.argsort(-p)[:3]
                    top = [str(model.classes_[i]) for i in order]; confidence = float(p[order[0]])
                pred.update(top3=top, confidence=confidence, correct=fold(top[0]) == fold(query['truth']))
            row['predictions'][name] = pred
        report['rows'].append(row)
        for name, p in row['predictions'].items():
            t = totals[name]
            t['n'] += 1
            t['correct'] += p['correct']
            t['n_accepted'] += p['accepted']
            t['accepted_correct'] += p['accepted'] and p['correct']
            if p['in_vocabulary']:
                t['n_in_vocabulary'] += 1
                t['correct_in_vocabulary'] += p['correct']
                t['top3_in_vocabulary'] += fold(query['truth']) in {fold(c) for c in p['top3']}
            else:
                t['accepted_oov'] += p['accepted']
        write_json(args.out, report)
        print(query['item_id'], {k: v['top3'] for k,v in row['predictions'].items()}, flush=True)
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
