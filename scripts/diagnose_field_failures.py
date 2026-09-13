"""Position, duration and tonic-candidate sweeps on labelled field items.

Implements data/overhaul/FIELD_FAILURE_PREREG.md. Every query goes through
the shared bounded frontend and raga_runtime; nothing is tuned.

Usage:
  venv_train/bin/python scripts/diagnose_field_failures.py --items c1_1 c2_1 \
      --out data/overhaul/context180_recovered_experiment/field_failures.json
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
from normalize_ragas import fold
from scripts.raga_pipeline import sha, write_json
from scripts.long_concert_score import validate_intervals
from carnatify.audio.melody_frontend import extract_query, HOP_S
from carnatify.audio.tonic_evidence import tonic_candidates
from carnatify.ml.raga_runtime import RagaCandidate, RagaGate, score_contour

CACHE = ROOT / 'data/overhaul/cache/concerts/queries'


def cents_mod_octave(a, b):
    c = 1200 * np.log2(a / b)
    return float(((c + 600) % 1200) - 600)


def summarize(result, truth):
    if not result['answered']:
        return dict(answered=False, reason=result['reason'])
    top3 = [r['raga'] for r in result['ranked'][:3]]
    return dict(answered=True, top3=top3, correct=fold(top3[0]) == fold(truth),
                top3_correct=fold(truth) in {fold(c) for c in top3},
                margin=result['signals']['margin'], accepted=result['accepted'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--items', nargs='+', required=True)
    ap.add_argument('--model', default='context180')
    ap.add_argument('--gate', type=Path, default=ROOT / 'data/overhaul/context180_recovered_experiment/gate.json')
    ap.add_argument('--labels', type=Path, default=ROOT / 'data/architecture_audit/label_intervals.json')
    ap.add_argument('--step-s', type=float, default=30.)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    started = time.monotonic()
    labels = json.loads(a.labels.read_text())
    if sha(ROOT / labels['source']) != labels['source_sha256']:
        raise SystemExit('Label source changed')
    frozen = json.loads((ROOT / 'data/long_concerts/FROZEN_CONCERTS.json').read_text())
    concerts = validate_intervals(labels, frozen)
    candidate = RagaCandidate.load(a.model)
    gate = RagaGate.load(a.gate)
    report = dict(status='diagnostic sweeps on labelled items; no tuning, no model change',
                  prereg='data/overhaul/FIELD_FAILURE_PREREG.md', model=candidate.describe(),
                  gate=gate.describe(), step_s=a.step_s, items={})
    for item in a.items:
        rows = [r for r in labels['intervals'] if r['item_id'] == item]
        if not rows: raise SystemExit(f'Unknown item {item}')
        row = max(rows, key=lambda r: r['end_s'] - r['start_s'])
        concert = row['concert']; truth = row['raga']
        path = ROOT / 'data/long_concerts/audio' / concerts[concert]['file']
        digest = concerts[concert]['sha256']
        if sha(path) != digest: raise SystemExit('Frozen concert changed')
        lo, hi = row['start_s'], row['end_s']

        def run(start, dur, tonic_override=None):
            f0, meta = extract_query(path, digest, float(start), float(dur), CACHE)
            tonic = meta['tonic_hz'] if tonic_override is None else tonic_override
            res = score_contour(candidate, f0, tonic, HOP_S, gate)
            out = summarize(res, truth)
            out.update(start_s=float(start), duration_s=float(dur), tonic_hz=tonic,
                       tonic_estimated_hz=meta['tonic_hz'], voiced_s=res['voiced_s'])
            return out

        position = []
        start = lo
        while start + 180 <= hi:
            position.append(run(start, 180)); start += a.step_s
            print(f'{item} pos {position[-1]["start_s"]:.0f}s {position[-1].get("top3")} margin {position[-1].get("margin")}', flush=True)
        center = (lo + hi - 180) / 2
        duration = [run((lo + hi - d) / 2, d) for d in (60, 120, 180)]
        base = run(center, 180)
        tonic_sweep = []
        if base['tonic_estimated_hz']:
            for semis, t in zip((0, 5, 7), tonic_candidates(base['tonic_estimated_hz'])):
                r = run(center, 180, float(t)); r['semitones'] = semis; tonic_sweep.append(r)
        tonics = [p['tonic_estimated_hz'] for p in position if p['tonic_estimated_hz']]
        ref = float(np.median(tonics)) if tonics else None
        spread = [cents_mod_octave(t, ref) for t in tonics] if ref else []
        n = len(position); answered = [p for p in position if p['answered']]
        report['items'][item] = dict(
            concert=concert, truth=truth, interval_s=[lo, hi], n_position_windows=n,
            position_top1_correct=sum(p['correct'] for p in answered),
            position_top3_correct=sum(p['top3_correct'] for p in answered),
            position_accepted=sum(p['accepted'] for p in answered),
            position_accepted_correct=sum(p['accepted'] and p['correct'] for p in answered),
            tonic_median_hz=ref, tonic_cents_from_median=spread,
            tonic_windows_over_50c=int(sum(abs(c) > 50 for c in spread)),
            position=position, duration=duration, tonic_sweep=tonic_sweep)
        write_json(a.out, report)
    report['elapsed_s'] = time.monotonic() - started
    write_json(a.out, report)
    for item, r in report['items'].items():
        print(f"\n{item} {r['truth']}: top-1 {r['position_top1_correct']}/{r['n_position_windows']} windows, "
              f"top-3 {r['position_top3_correct']}, accepted {r['position_accepted']} ({r['position_accepted_correct']} correct); "
              f"tonic >50c in {r['tonic_windows_over_50c']}/{len(r['tonic_cents_from_median'])}")
        print('  duration:', [(d['duration_s'], d.get('top3', [None])[0], round(d.get('margin', 0) or 0, 3)) for d in r['duration']])
        print('  tonic sweep:', [(t['semitones'], t.get('top3', [None])[0], round(t.get('margin', 0) or 0, 3)) for t in r['tonic_sweep']])


if __name__ == '__main__':
    main()
