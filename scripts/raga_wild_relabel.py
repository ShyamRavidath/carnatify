#!/usr/bin/env python3
"""Re-score the frozen wild raga measurement under Deepti's label audit.

`data/RAGA_WILD_MEASUREMENT.md` published 16/29 = 55.2% with the labels
*unaudited*, and said in as many words that the number was a floor pending
review. On 2026-08-13 Deepti — the domain expert — read all 29 rows and
returned four corrections. This script applies them and nothing else.

It does NOT re-run the model. Predictions come verbatim from
`data/raga_wild/results.json`, which was written before any label was
questioned. Only the truth column moves, so no prediction can be tuned to a
label and the frozen selection in `FROZEN_CLIPS.json` is untouched.

The eligibility rule is the one the preregistration already fixed: a clip is
in-tier iff its true raga is a class the model can emit. Correcting a label to
a raga outside the class list therefore *removes* the clip from the
denominator — it does not convert to a miss, because the model was never able
to be right. Both corrected clips were misses, so the headline can only rise;
that direction was stated in `HANDOFF_SESSION_0731.md` §6.1 before the audit
came back.

Usage: python3 scripts/raga_wild_relabel.py
"""
from __future__ import annotations

import json
import math
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / 'data' / 'raga_wild' / 'results.json'

# Deepti's audit, 2026-08-13. `raga` is the corrected true raga; `title` is a
# corrected transliteration of the composition name (cosmetic, no effect on
# any count). `None` means the row was confirmed correct.
CORRECTIONS = {
    'Maithreem Bhajata__Kalyani__OOC.mp3': {
        'raga': 'Yamunākalyāṇi',
        'note': 'a janya of Kalyāṇi, not Kalyāṇi itself; distinct raga label',
    },
    'nagumomu ganaleni__Saveri.m4a': {
        'raga': 'Ābhēri',
        'note': 'filed Sāvēri; the kriti is Ābhēri (Karaharapriya janya)',
    },
    'yEnATi mOmu palamu__Bhairavi.m4a': {
        'raga': 'Bhairavi',
        'title': 'EnATi nOmu phalamO',
        'note': 'title transliteration only; raga confirmed correct',
    },
    'bhajarE bhaja mAnasa__Kanada.m4a': {
        'raga': 'Kānaḍa',
        'note': 'confirmed correct by audit',
    },
}


def fold(name: str) -> str:
    d = unicodedata.normalize('NFKD', str(name))
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0.0, c - h), 100 * min(1.0, c + h))


def fmt(k: int, n: int, label: str) -> str:
    lo, hi = wilson(k, n)
    return f'{label}: {k}/{n} = {100 * k / n:.1f}% [{lo:.1f}, {hi:.1f}]'


def main() -> None:
    res = json.loads(RESULTS.read_text())
    classes = {fold(c) for c in res['model_classes']}
    tier = {fold(t) for t in res['tier']}
    rows = [r for r in res['per_clip'] if r['window'] == 'whole' and r['arm'] == 'mix']
    assert len(rows) == 29, len(rows)

    kept, dropped = [], []
    for r in rows:
        corr = CORRECTIONS.get(r['file'])
        truth = corr['raga'] if corr else r['truth']
        changed = fold(truth) != fold(r['truth'])
        row = dict(r, truth=truth, truth_changed=changed)
        if fold(truth) in classes:
            kept.append(row)
        else:
            row['drop_reason'] = f'{truth} is not one of the {len(classes)} model classes'
            dropped.append(row)

    print(f'frozen rows: {len(rows)}   corrections applied: '
          f'{sum(1 for r in kept + dropped if r["truth_changed"])}')
    print()
    print('DROPPED — corrected truth is outside the model\'s label set:')
    for r in dropped:
        print(f'  {r["file"]}')
        print(f'    was {r["prev"] if "prev" in r else CORRECTIONS[r["file"]]["note"]}')
        print(f'    predicted {r["fused_all_top1"]} (p={r["fused_all_p"]}), '
              f'was scored a MISS -> now ineligible')
    print()

    for scope in ('all', 'tier'):
        c1 = sum(1 for r in kept if r[f'fused_{scope}_c1'])
        c3 = sum(1 for r in kept if r[f'fused_{scope}_c3'])
        n = len(kept)
        print(f'--- fused | {scope} | mix | whole | corrected labels ---')
        print('  ' + fmt(c1, n, 'top-1'))
        print('  ' + fmt(c3, n, 'top-3'))
        was1 = sum(1 for r in rows if r[f'fused_{scope}_c1'])
        was3 = sum(1 for r in rows if r[f'fused_{scope}_c3'])
        print('  ' + fmt(was1, len(rows), 'was  top-1'))
        print('  ' + fmt(was3, len(rows), 'was  top-3'))
        print()

    # --- abstain gate: does top-1 probability separate hits from catastrophes?
    print('--- abstain gate on fused|all|mix|whole p(top-1), corrected set ---')
    print('  thr | kept | fired% | top-1 among kept | catastrophes kept (rank>10)')
    for thr in (0.00, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.35):
        sel = [r for r in kept if r['fused_all_p'] >= thr]
        if not sel:
            continue
        hits = sum(1 for r in sel if r['fused_all_c1'])
        cat = sum(1 for r in sel if r['fused_all_rank'] > 10)
        lo, hi = wilson(hits, len(sel))
        print(f'  {thr:.2f} | {len(sel):4d} | {100 * len(sel) / len(kept):5.1f}% | '
              f'{hits}/{len(sel)} = {100 * hits / len(sel):5.1f}% [{lo:.1f}, {hi:.1f}] | {cat}')
    print()
    ranks = sorted(r['fused_all_rank'] for r in kept if not r['fused_all_c1'])
    print(f'  miss ranks (32-class): {ranks}')


if __name__ == '__main__':
    main()
