"""Why does the fused harness get 653/1139 where the levels harness got 649/1139?

`data/raga_tier/PREREGISTRATION.md` §2 Gate 2 required the TDMS-only arm at
`min_tracks = 10`, level (c), to reproduce the committed integers from
`data/raga_coverage/levels_min10.json` — **649/1139 top-1 and 812/1139 top-3**.
It returned **653 and 816**. Prereg §7.4 registered that a Gate 2 failure is a
more important finding than anything else in the job, so this isolates it
instead of proceeding.

The two harnesses agree on the features, the tier rule, the forest, the seed,
the splitter, the level-(c) groups and the track-level read-out. They differ in
exactly one thing:

  levels harness  (`raga_audit_levels.build`)   — ONE row per track
  fused harness   (`raga_audit_protocol.build_matrix`) — THREE rows per track,
      the three augmented histogram rows of `d['X']`, with the SAME TDMS vector
      replicated across all three

Replication is not a no-op even for an arm that ignores the histogram. It
changes what `StratifiedGroupKFold` is handed (3,417 rows instead of 1,139, so
fold boundaries can fall differently) and it changes the forest's bootstrap
draw. This script tests that explanation directly by running the fused
harness's own matrix **deduplicated to one row per track** through the same
code. If dedup returns 649/812, row multiplicity is the whole cause and the
disagreement is a quantified noise floor rather than a substantive one.

Read-only. Writes `data/raga_tier/gate2_diagnosis.json`.

Usage: venv/bin/python scripts/raga_tier_gate2_diag.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import raga_audit_protocol as P  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / 'data' / 'raga_tier' / 'gate2_diagnosis.json'
MIN_TRACKS = 10
SEED = 42
N_SPLITS = 5
COMMITTED = {'top1': 649, 'top3': 812, 'n': 1139}


def tdms_only(Xt, y, tid, g, classes, label):
    """TDMS-only, track-level, level (c). The frozen forest and splitter."""
    cls_index = {c: i for i, c in enumerate(classes)}
    yi = np.array([cls_index[c] for c in y])
    skf = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    Pm = np.zeros((len(yi), len(classes)))
    for tr, te in skf.split(Xt, yi, groups=g):
        rf = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                    random_state=SEED, n_jobs=-1).fit(Xt[tr], yi[tr])
        Pm[np.ix_(te, rf.classes_)] = rf.predict_proba(Xt[te])
    uniq = sorted(set(tid))
    k1 = k3 = 0
    for t in uniq:
        mean = Pm[tid == t].mean(axis=0)
        order = np.argsort(-mean)
        true = yi[tid == t][0]
        k1 += int(order[0] == true)
        k3 += int(true in order[:3])
    print(f'  {label:34s} rows {len(yi):5d}  tracks {len(uniq)}  '
          f'top-1 {k1}/{len(uniq)} = {k1/len(uniq):.3%}  top-3 {k3}', flush=True)
    return dict(label=label, n_rows=int(len(yi)), n_tracks=len(uniq),
                top1=int(k1), top3=int(k3), top1_rate=k1 / len(uniq))


def main() -> None:
    M = P.build_matrix()
    groups, _ = P.build_groups(M)
    gc = groups['c']
    classes, _ = P.frozen_tier(M['y'], M['tid'], min_tracks=MIN_TRACKS)

    m = np.isin(M['y'], classes)
    Xt, y, tid, g = M['Xt'][m], M['y'][m], M['tid'][m], gc[m]

    rows_per_track = len(y) / len(set(tid))
    print(f'{len(classes)} classes, {len(set(tid))} tracks, {len(y)} rows '
          f'({rows_per_track:.2f} rows/track), {len(set(g))} level-(c) groups\n')

    # Sanity: the three rows of a track really do carry an identical TDMS vector.
    sample = sorted(set(tid))[:50]
    identical = all(np.allclose(Xt[tid == t], Xt[tid == t][0]) for t in sample)
    print(f'  TDMS vectors identical within a track (50 sampled): {identical}\n')

    arms = [tdms_only(Xt, y, tid, g, classes, 'replicated (3 rows/track)')]

    # ---- deduplicated to one row per track, first row of each -------------
    first = {}
    for i, t in enumerate(tid):
        first.setdefault(t, i)
    keep = np.array(sorted(first.values()))
    arms.append(tdms_only(Xt[keep], y[keep], tid[keep], g[keep], classes,
                          'deduplicated (1 row/track)'))

    dedup = arms[1]
    explained = (dedup['top1'] == COMMITTED['top1']
                 and dedup['top3'] == COMMITTED['top3'])
    out = dict(committed=COMMITTED, arms=arms,
               tdms_identical_within_track=bool(identical),
               row_multiplicity_explains_gate2=bool(explained),
               delta_top1_replicated_minus_committed=arms[0]['top1'] - COMMITTED['top1'],
               delta_top1_dedup_minus_committed=dedup['top1'] - COMMITTED['top1'])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')

    print(f"\ncommitted (levels harness, 1 row/track): "
          f"{COMMITTED['top1']}/{COMMITTED['n']} and {COMMITTED['top3']}")
    print(f"row multiplicity explains the Gate 2 gap: "
          f"{'YES' if explained else 'NO — something else differs'}")
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
