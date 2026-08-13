"""JOB A — the within-class learning curve: does more audio per class buy
accuracy, or is r(tracks, top-1) = 0.519 a popularity confound?

`data/RAGA_CEILING_EVALUATION.md` reports a clean monotone relationship between
a class's track count and its accuracy, ACROSS classes. That comparison is
confounded: the well-stocked classes are exactly the ones
`scratch_archive_0711/dl_deficits30.py` deliberately topped up because they are
popular and canonical. This module compares every class **against itself**
instead, by subsampling it, which holds popularity, recording quality and
melodic distinctiveness constant by construction.

Protocol is `data/raga_coverage/PREREGISTRATION_FOLLOWUP.md` §A and is not to be
changed after seeing the numbers:

- tier held at min_tracks >= 10, 54 classes, computed on FULL uncapped
  level-(a) track counts — the cap never moves the class set;
- for cap c, each class keeps the first c of one permutation of its own tracks,
  so the c=10 subset is nested inside c=15 and the arms are paired;
- cap seeds 0, 1, 2, all reported, spread reported;
- level (c) source-disjoint only;
- Gate A: no class has more than 30 tracks, so c=30 must reproduce the committed
  649/1139 and 812/1139 exactly, for every seed.

`run_cv`, the features and the forest are IMPORTED from
`scripts/raga_audit_levels.py` — the same code objects that passed the
reproduction gate. Nothing under `models/` is written.

Usage: venv/bin/python scripts/raga_coverage_within_class.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import raga_audit_levels as L  # noqa: E402
import raga_coverage_matrix as M  # noqa: E402

ROOT = HERE.parent
DIR = ROOT / 'data' / 'raga_coverage'
MIN_TRACKS = 10
CAPS = (10, 15, 20, 25, 30)
CAP_SEEDS = (0, 1, 2)
RESTRICT_MIN = 25          # read-out (ii): the classes that vary across the grid


def capped_mask(y, g, keep, cap, seed):
    """Nested per-class subsample. One permutation per class per seed; cap c
    takes its first c entries, so c=10 is a subset of c=15 and so on."""
    rng = np.random.default_rng(seed)
    chosen = set()
    for r in keep:
        tids = sorted(set(g[y == r]))
        order = rng.permutation(len(tids))
        chosen.update(tids[i] for i in order[:cap])
    return np.isin(y, keep) & np.isin(g, sorted(chosen))


def main() -> None:
    X, y, g, gc, ntr = M.get()
    keep = M.tier(ntr, MIN_TRACKS)
    restrict = set(M.tier(ntr, RESTRICT_MIN))
    print(f'tier min>={MIN_TRACKS}: {len(keep)} classes, '
          f'{int(np.isin(y, keep).sum())} tracks; read-out (ii) restricted to '
          f'{len(restrict)} classes with >={RESTRICT_MIN} tracks', flush=True)

    out_path = DIR / 'within_class.json'
    out = {'tier': {'min_tracks': MIN_TRACKS, 'classes': keep},
           'caps': list(CAPS), 'cap_seeds': list(CAP_SEEDS),
           'restrict_min_tracks': RESTRICT_MIN,
           'restricted_classes': sorted(restrict), 'cells': {}}

    for cap in CAPS:
        for seed in CAP_SEEDS:
            key = f'c{cap}_s{seed}'
            m = capped_mask(y, g, keep, cap, seed)
            Xc, yc, gk, gcc = X[m], y[m], g[m], gc[m]
            r = L.run_cv(Xc, yc, gk, gcc, keep)

            # read-out (ii): same 54-way model, evaluation restricted
            sel = [t for t, lab in r['label_of'].items() if lab in restrict]
            n_r = len(sel)
            t1_r = sum(r['correct1'][t] for t in sel)
            t3_r = sum(r['correct3'][t] for t in sel)
            per_class = {}
            for cls in sorted(restrict):
                ts = [t for t, lab in r['label_of'].items() if lab == cls]
                per_class[cls] = dict(n=len(ts),
                                      top1=float(np.mean([r['correct1'][t] for t in ts])))
            cell = dict(
                cap=cap, seed=seed,
                n_tracks=r['n_tracks'], n_groups=r['n_groups'],
                n_classes=r['n_ragas'], n_folds=r['n_folds'],
                class_prior_expectation=r['class_prior_expectation'],
                all54_top1=r['top1'], all54_top3=r['top3'],
                all54_top1_rate=r['top1_rate'], all54_top3_rate=r['top3_rate'],
                restricted_n=n_r, restricted_top1=int(t1_r), restricted_top3=int(t3_r),
                restricted_top1_rate=t1_r / n_r, restricted_top3_rate=t3_r / n_r,
                per_class_restricted=per_class,
            )
            out['cells'][key] = cell
            print(f"cap {cap:>2} seed {seed}:  tracks {r['n_tracks']:>4} "
                  f"groups {r['n_groups']:>3}  |  all-54 "
                  f"{r['top1']:>4}/{r['n_tracks']:<4} {r['top1_rate']:>6.1%}  |  "
                  f"restricted-18 {t1_r:>3}/{n_r:<3} {t1_r / n_r:>6.1%} "
                  f"(top3 {t3_r / n_r:>5.1%})", flush=True)
            # written after EVERY cell, never at the end
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    # ---------------------------------------------------------------- Gate A
    gate = []
    for seed in CAP_SEEDS:
        c = out['cells'][f'c30_s{seed}']
        gate.append(c['all54_top1'] == 649 and c['all54_top3'] == 812
                    and c['n_tracks'] == 1139)
    out['gate_a'] = dict(passed=bool(all(gate)), per_seed=gate,
                         expected='649/1139 top-1 and 812/1139 top-3')
    print(f"\nGATE A (c=30 is the whole tier, must reproduce 649/1139 and 812/1139): "
          f"{'PASS' if all(gate) else 'FAIL'}  per-seed {gate}", flush=True)

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f'\nwrote {out_path}')


if __name__ == '__main__':
    main()
