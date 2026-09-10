#!/usr/bin/env python3
"""Score independent window predictions against explicit held-out intervals.

Boundary-crossing windows are excluded, extraction failures count as no answer,
and vocabulary coverage and missing items are reported explicitly. This is an
oracle-boundary evaluation, NOT evidence that song segmentation works.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.raga_pipeline import sha, write_json


def validate_intervals(manifest, frozen):
    concerts = {Path(c['file']).stem: c for c in frozen['concerts']}
    by_concert = defaultdict(list)
    for row in manifest['intervals']:
        if row['concert'] not in concerts:
            raise ValueError('unknown concert')
        a, b = row['start_s'], row['end_s']
        if not (np.isfinite(a) and np.isfinite(b) and 0 <= a < b <= concerts[row['concert']]['duration_s']):
            raise ValueError('invalid interval')
        by_concert[row['concert']].append(row)
        for ex in manifest.get('exclusions', []):
            if ex['concert'] == row['concert'] and min(b, ex['end_s']) > max(a, ex['start_s']):
                raise ValueError('labeled interval overlaps an exclusion')
    for rows in by_concert.values():
        rows = sorted(rows, key=lambda r:r['start_s'])
        if any(a['end_s'] > b['start_s'] for a,b in zip(rows,rows[1:])):
            raise ValueError('overlapping intervals')
    return concerts


def score(manifest, predictions, classes):
    primary = {r['item_id']:r for r in manifest['intervals'] if r['primary'] and r['confidence']=='high'}
    by_item = defaultdict(list)
    rejected = []
    for concert, w in predictions:
        candidates = [r for r in manifest['intervals'] if r['concert']==concert
                      and r['start_s'] <= w['start_s'] and w['end_s'] <= r['end_s']]
        if len(candidates) != 1:
            rejected.append(dict(concert=concert, start_s=w['start_s'],reason='unknown_or_crossing_boundary'))
            continue
        by_item[candidates[0]['item_id']].append(w)
    rows = []
    for item_id, label in primary.items():
        windows = by_item[item_id]
        votes = defaultdict(float)
        for w in windows:
            for raga, probability in w.get('probabilities', {}).items():
                votes[raga] += probability
        top = sorted(votes, key=lambda k:(-votes[k],k))[:3]
        rows.append(dict(item_id=item_id, concert=label['concert'], truth=label['raga'],
                         in_vocabulary=label['raga'] in classes,
                         measured=bool(windows), answered=bool(top),
                         top3=top, correct=bool(top and top[0]==label['raga']),
                         top3_correct=label['raga'] in top,
                         n_windows=len(windows)))
    measured = [r for r in rows if r['measured']]
    in_vocab = [r for r in measured if r['in_vocabulary']]
    answered = [r for r in measured if r['answered']]
    return dict(status='partial oracle-boundary evaluation; not automatic segmentation performance',
        n_primary_items=len(rows), n_measured=len(measured), n_missing=len(rows)-len(measured),
        n_in_vocabulary=sum(r['in_vocabulary'] for r in rows),
        vocabulary_coverage=sum(r['in_vocabulary'] for r in rows)/len(rows) if rows else None,
        top1_all_measured=sum(r['correct'] for r in measured)/len(measured) if measured else None,
        top1_in_vocabulary=sum(r['correct'] for r in in_vocab)/len(in_vocab) if in_vocab else None,
        precision_answered=sum(r['correct'] for r in answered)/len(answered) if answered else None,
        rows=rows, rejected_windows=rejected)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--labels',type=Path,default=ROOT/'data/architecture_audit/label_intervals.json')
    ap.add_argument('--model',type=Path,default=ROOT/'data/architecture_audit/candidate.joblib')
    ap.add_argument('--predictions',type=Path,nargs='+',required=True)
    ap.add_argument('--out',type=Path,default=ROOT/'data/architecture_audit/long_concert_score.json')
    args = ap.parse_args()
    labels = json.loads(args.labels.read_text())
    if sha(ROOT/labels['source']) != labels['source_sha256']:
        raise ValueError('Label source changed; review interval copy before scoring')
    frozen = json.loads((ROOT/'data/long_concerts/FROZEN_CONCERTS.json').read_text())
    concerts = validate_intervals(labels, frozen)
    import joblib
    classes = set(joblib.load(args.model)['model'].classes_)
    predictions, seen = [], set()
    for path in args.predictions:
        data=json.loads(path.read_text()); concert=Path(data['audio']).stem
        if data['model_sha256'] != sha(args.model):
            raise ValueError('model/prediction mismatch')
        if data['audio_sha256'] != concerts[concert]['sha256']:
            raise ValueError('prediction audio differs from frozen concert')
        for w in data['windows']:
            key=(concert,w['start_s'],w['end_s'])
            if key in seen:
                raise ValueError('duplicate prediction window')
            seen.add(key); predictions.append((concert,w))
    report=score(labels,predictions,classes)
    report.update(label_manifest_sha256=sha(args.labels),model_sha256=sha(args.model))
    write_json(args.out,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','rejected_windows')},indent=2))


if __name__=='__main__':
    main()
