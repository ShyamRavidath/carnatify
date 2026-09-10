"""Create a separate feature run excluding connected groups with audio overlap.

This is a minimum exact-byte guard, not proof of artist independence or absence
of transcoded/excerpt copies. Original runs and model artifacts are untouched.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
from scripts.raga_pipeline import sha, write_json, load_features


def quarantined_groups(rows, identities, evaluation_hashes, require_source_match=False):
    reasons = {}
    for r in rows:
        evidence = identities.get(r['track'])
        if r.get('corpus') == 'archive' and evidence is None:
            raise ValueError(f'Missing archival byte audit: {r["track"]}')
        if evidence is None:
            continue
        if evidence['audio'] != r['audio']:
            raise ValueError('Audio path differs from audited path')
        cause = []
        if evidence['sha256'] in evaluation_hashes:
            cause.append('exact_evaluation_audio_overlap')
        if evidence['status'] == 'assigned_source_mismatch':
            cause.append('assigned_source_mismatch')
        if require_source_match and evidence['status'] not in {'assigned_source_confirmed','shared_across_items'}:
            cause.append('unverified_source_bytes')
        if cause:
            reasons.setdefault(r['group'], []).append(dict(track=r['track'], reasons=cause))
    return reasons


def deduplicate_rows(rows, identities):
    """One deterministic representative per exact audio; never pick by score."""
    first, kept, removed = {}, [], []
    for row in sorted(rows, key=lambda r: r['track']):
        evidence = identities.get(row['track'])
        if evidence is None:
            kept.append(row)
            continue
        digest = evidence['sha256']
        if digest not in first:
            first[digest] = row
            kept.append(row)
            continue
        original = first[digest]
        if row['label'] != original['label']:
            raise ValueError('Conflicting labels for identical audio; quarantine before deduplication')
        if row['group'] != original['group']:
            raise ValueError('Identical audio crosses groups; union before deduplication')
        removed.append(dict(track=row['track'], representative=original['track'], audio_sha256=digest))
    return kept, removed


def exclude_documented_supervision(rows,identities,exclusions,root):
    for evidence in exclusions['rows']:
        if sha(root/evidence['evidence_path'])!=evidence['evidence_sha256']:
            raise ValueError('Documentary supervision exclusion evidence changed')
    denied={r['audio_sha256'] for r in exclusions['rows']}
    kept=[];removed=[]
    for row in rows:
        if identities.get(row['track'],{}).get('sha256') in denied:removed.append(row['track'])
        else:kept.append(row)
    return kept,removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--identity', type=Path, default=ROOT / 'data/overhaul/archive_audio_identity.json')
    parser.add_argument('--evaluation', type=Path, default=ROOT / 'data/overhaul/saraga_audio_results.json')
    parser.add_argument('--deduplicate-audio', action='store_true')
    parser.add_argument('--require-source-match', action='store_true')
    parser.add_argument('--supervision-exclusions',type=Path,default=ROOT/'configs/known_audio_exclusions.json')
    args = parser.parse_args()
    if args.out.resolve() == args.run.resolve() or (args.out / 'manifest.json').exists():
        raise ValueError('Output must be a new, separate run')
    manifest = json.loads((args.run / 'manifest.json').read_text())
    identities = {r['track']: r for r in json.loads(args.identity.read_text())['rows']}
    evaluation = json.loads(args.evaluation.read_text())
    evaluation_hashes = {r['metadata']['audio_sha256'] for r in evaluation['rows']}
    for r in manifest['rows']:
        if r.get('corpus') == 'archive':
            e = identities[r['track']]
            if sha(ROOT / r['audio']) != e['sha256']:
                raise ValueError(f'Stale byte audit: {r["track"]}')
    reasons = quarantined_groups(manifest['rows'], identities, evaluation_hashes,args.require_source_match)
    kept = [r for r in manifest['rows'] if r['group'] not in reasons]
    kept,supervision_removed=exclude_documented_supervision(kept,identities,
        json.loads(args.supervision_exclusions.read_text()),ROOT)
    duplicate_rows = []
    if args.deduplicate_audio:
        kept, duplicate_rows = deduplicate_rows(kept, identities)
    allowed = {r['track'] for r in kept}
    features = load_features(args.run)
    mask = np.isin(features['track'], list(allowed))
    arrays = {}
    for key, value in features.items():
        arrays[key] = value[mask] if value.ndim and len(value) == len(mask) else value
    removed = [r for r in manifest['rows'] if r['group'] in reasons]
    report = dict(policy='quarantine entire connected groups; no relabeling',
                  reasons=reasons, removed_tracks=[r['track'] for r in removed],
                  retained_tracks=len(kept), removed_tracks_count=len(removed),
                  duplicate_rows=duplicate_rows,
                  invalid_supervision_tracks=supervision_removed,
                  duplicate_policy='lexically first track per exact audio' if args.deduplicate_audio else 'unchanged',
                  limitation='Exact bytes only; transformed copies, unknown artists and contour/audio joins remain unaudited.')
    inputs = {str(p.resolve().relative_to(ROOT)): sha(p) for p in
              (args.run / 'manifest.json', args.run / 'features.npz', args.identity, args.evaluation,args.supervision_exclusions)}
    write_json(args.out / 'manifest.json', dict(manifest, rows=kept, inputs=inputs,
               audio_overlap_quarantine=report, role='development_after_exact_audio_quarantine'))
    arrays['manifest_sha256'] = np.array(sha(args.out / 'manifest.json'))
    np.savez_compressed(args.out / 'features.npz', **arrays)
    write_json(args.out / 'quarantine.json', report)
    print(json.dumps(dict(retained=len(kept), removed=len(removed),
                          removed_groups=len(reasons), duplicates_removed=len(duplicate_rows),
                          invalid_supervision_removed=len(supervision_removed),windows=int(mask.sum()))))


if __name__ == '__main__':
    main()
