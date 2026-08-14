"""The 2x2 registered in `data/raga_tier/PREREGISTRATION.md`:
{TDMS-only, fused} x {54 classes, 51 classes}, level (c), track-level.

Why this exists at all. `handoff.md` §5.2 reads as a script run — retrain at
`min_tracks = 10` and export. It is not, because of the gap
`data/RAGA_COVERAGE_CURVE.md` §8 names: **every number on the coverage curve is
TDMS-only and the exported model is fused** (`P = 0.6*P_tdms + 0.4*P_hist`). At
18 classes fusion is worth +1.4 pp top-1 and -0.4 pp top-3 at level (c). Nobody
has measured it at 54.

Two things this harness does that matter:

* **fused and TDMS-only come out of the same forests and the same folds.** Each
  fold fits `rf_t` and `rf_h` once; the TDMS arm reads `pt`, the fused arm reads
  `0.6*pt + 0.4*ph`. So the arm contrast is exactly paired at the track level and
  costs nothing extra. This is a strictly better comparison than running the two
  arms as separate jobs, which is how the series has done it until now.
* **the tier is the only thing that moves.** Features, taus, `nb`, `sigma`,
  `alpha`, the forest, the splitter, the seed, the level-(c) group construction
  and the track-level read-out are all imported from the gated harness
  (`raga_audit_protocol`, `raga_audit_score`), not reimplemented.

The 51-class arm is the 54-class tier minus the three classes the nested
admission arm never admitted in any fold (`data/RAGA_COVERAGE_CURVE.md` §11.4).
It is a **named list applied after the tier rule**, never a threshold — the
threshold sweep is dead (§11.2) and is not resurrected here.

Read-only: fits happen in memory, nothing under `models/` is written.
Writes `data/raga_tier/results.json`.

Usage: venv/bin/python scripts/raga_tier_score.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import raga_audit_protocol as P  # noqa: E402  — the gated harness itself
from raga_audit_protocol import fold as rfold  # noqa: E402
from raga_audit_score import wilson  # noqa: E402
from train_raga_v3_tdms import FUSION_W_HIST  # noqa: E402

ROOT = HERE.parent
OUT_DIR = ROOT / 'data' / 'raga_tier'
COMPS = ROOT / 'data' / 'scraped_compositions.json'

MIN_TRACKS = 10
LEVEL = 'c'
N_SPLITS = P.N_SPLITS
SEED = 42
N_BOOT = 2000

# Registered in the prereg §1. Provenance: the classes the NESTED admission arm
# never admitted in any of five outer folds at t = 0.10. Not re-derivable here
# and deliberately not re-derived — it is a fixed list, not a tunable.
DROP_NAMES = ('Nāṭakurinji', 'Janaranjani', 'Haṁsānandi')

# The committed integers this harness must reproduce (Gate 2).
GATE2 = {'top1': 649, 'top3': 812, 'n': 1139}


def repertoire():
    items = json.loads(COMPS.read_text())
    c = Counter(rfold(i['raga_canonical']) for i in items if i.get('raga_canonical'))
    return c, sum(c.values())


def cluster_bootstrap(correct, group_of, n_boot=N_BOOT, seed=SEED):
    """Resample level-(c) SOURCE GROUPS with replacement, not tracks.

    Verbatim in method from `scripts/raga_coverage_curve.py`: the tracks are not
    independent, 1,139 of them sit in 204 source clusters, and a binomial
    interval on the track count is far too narrow.
    """
    by_group = {}
    for t, ok in correct.items():
        by_group.setdefault(group_of[t], []).append(bool(ok))
    keys = sorted(by_group)
    arrs = [np.array(by_group[k], dtype=float) for k in keys]
    rng = np.random.default_rng(seed)
    n = len(keys)
    reps = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        hit = tot = 0.0
        for i in idx:
            a = arrs[i]
            hit += a.sum()
            tot += a.size
        reps[b] = hit / tot
    return float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))


def run_cell(M, gc, classes, label):
    """One tier. Returns BOTH arms from the same forests and the same folds."""
    m = np.isin(M['y'], classes)
    Xt, Xh = M['Xt'][m], M['Xh'][m]
    y, tid, g = M['y'][m], M['tid'][m], gc[m]

    cls_index = {c: i for i, c in enumerate(classes)}
    yi = np.array([cls_index[c] for c in y])
    nC = len(classes)

    skf = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    Pt = np.zeros((len(yi), nC))
    Ph = np.zeros((len(yi), nC))
    fold_of = np.full(len(yi), -1)

    t0 = time.time()
    for k, (tr, te) in enumerate(skf.split(Xt, yi, groups=g)):
        rf_t = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                      random_state=SEED, n_jobs=-1).fit(Xt[tr], yi[tr])
        rf_h = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                      random_state=SEED, n_jobs=-1).fit(Xh[tr], yi[tr])
        Pt[np.ix_(te, rf_t.classes_)] = rf_t.predict_proba(Xt[te])
        Ph[np.ix_(te, rf_h.classes_)] = rf_h.predict_proba(Xh[te])
        fold_of[te] = k
        print(f'    {label}: fold {k} done ({time.time()-t0:.0f}s)', flush=True)

    uniq = sorted(set(tid))
    ytrack = {t: yi[tid == t][0] for t in uniq}
    gtrack = {t: g[tid == t][0] for t in uniq}

    arms = {}
    for arm, Pm in (('tdms', Pt), ('fused', (1 - FUSION_W_HIST) * Pt + FUSION_W_HIST * Ph)):
        # track-level: average the augmented rows' posteriors, as the frozen
        # harness does it — one prediction per track, never per row.
        agg = {t: Pm[tid == t].mean(axis=0) for t in uniq}
        c1, c3 = {}, {}
        for t in uniq:
            order = np.argsort(-agg[t])
            c1[t] = bool(order[0] == ytrack[t])
            c3[t] = bool(ytrack[t] in order[:3])
        n = len(uniq)
        k1, k3 = sum(c1.values()), sum(c3.values())
        lo, hi = cluster_bootstrap(c1, gtrack)
        per_class = {}
        for c in classes:
            ts = [t for t in uniq if classes[ytrack[t]] == c]
            if ts:
                per_class[c] = dict(
                    n_tracks=len(ts),
                    n_groups=len({gtrack[t] for t in ts}),
                    top1=float(np.mean([c1[t] for t in ts])),
                    top3=float(np.mean([c3[t] for t in ts])))
        arms[arm] = dict(
            n_classes=nC, n_tracks=n, n_rows=int(m.sum()),
            n_groups=int(len(set(g))),
            top1=int(k1), top3=int(k3),
            top1_rate=k1 / n, top3_rate=k3 / n,
            top1_ci95_cluster=[round(lo, 5), round(hi, 5)],
            top1_ci95_wilson=[round(x, 5) for x in wilson(k1, n)],
            per_class=per_class,
            correct1={t: c1[t] for t in uniq},
            group_of={t: str(gtrack[t]) for t in uniq},
        )
    return arms, time.time() - t0


def mcnemar(a, b, keys):
    """Exact two-sided binomial on the discordant pairs. `a` is the baseline."""
    nb = sum(1 for t in keys if a[t] and not b[t])
    nc = sum(1 for t in keys if b[t] and not a[t])
    p = binomtest(nb, nb + nc, 0.5).pvalue if (nb + nc) else 1.0
    return dict(b=nb, c=nc, n_pairs=len(keys), p_exact=float(p))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rep, rep_tot = repertoire()

    M = P.build_matrix()
    groups, notes = P.build_groups(M)
    gc = groups[LEVEL]
    keep54, ntr = P.frozen_tier(M['y'], M['tid'], min_tracks=MIN_TRACKS)
    keep51 = [c for c in keep54 if c not in DROP_NAMES]

    missing = [d for d in DROP_NAMES if d not in keep54]
    print(f'corpus: {len(M["y"])} rows, {len(set(M["tid"]))} tracks, '
          f'{len(set(M["y"]))} ragas; skipped {M["skipped"]}; provenance {notes}')
    print(f'tier min_tracks >= {MIN_TRACKS}: {len(keep54)} classes')
    print(f'drop list {DROP_NAMES} -> {len(keep51)} classes'
          + (f'   *** NOT IN TIER: {missing} ***' if missing else ''))
    if missing:
        sys.exit('drop list names a class that is not in the tier — stopping')

    out = {'preregistration': 'data/raga_tier/PREREGISTRATION.md',
           'min_tracks': MIN_TRACKS, 'level': LEVEL,
           'fusion_w_hist': FUSION_W_HIST, 'n_splits': N_SPLITS, 'seed': SEED,
           'n_boot': N_BOOT, 'drop_names': list(DROP_NAMES),
           'repertoire_denominator': rep_tot,
           'notes': notes, 'skipped': M['skipped'], 'cells': {}}
    out_path = OUT_DIR / 'results.json'

    for tier_label, classes in (('54', keep54), ('51', keep51)):
        print(f'\n=== tier {tier_label}: {len(classes)} classes ===', flush=True)
        arms, secs = run_cell(M, gc, classes, tier_label)
        cov = sum(v for k, v in rep.items()
                  if k in {rfold(c) for c in classes}) / rep_tot
        for arm, r in arms.items():
            r['coverage'] = cov
            r['expected_hits_per_100'] = 100 * cov * r['top1_rate']
            r['expected_top3_hits_per_100'] = 100 * cov * r['top3_rate']
            r['fit_seconds'] = round(secs, 1)
            out['cells'][f'{tier_label}_{arm}'] = r
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        for arm in ('tdms', 'fused'):
            r = arms[arm]
            print(f"  {arm:6s} top-1 {r['top1']:4d}/{r['n_tracks']} = {r['top1_rate']:.3%} "
                  f"CI {r['top1_ci95_cluster'][0]:.1%}-{r['top1_ci95_cluster'][1]:.1%}   "
                  f"top-3 {r['top3']:4d} = {r['top3_rate']:.3%}   "
                  f"cov {cov:.1%}   exp hits {r['expected_hits_per_100']:.2f}", flush=True)

    # ---------------------------------------------------------------- Gate 2
    g2 = out['cells']['54_tdms']
    passed = (g2['top1'] == GATE2['top1'] and g2['top3'] == GATE2['top3']
              and g2['n_tracks'] == GATE2['n'])
    out['gate2'] = dict(passed=bool(passed), expected=GATE2,
                        got={'top1': g2['top1'], 'top3': g2['top3'],
                             'n': g2['n_tracks']})
    print(f"\nGATE 2 (TDMS-only at min>=10 level (c) must reproduce the committed "
          f"integers {GATE2['top1']}/{GATE2['n']} and {GATE2['top3']}/{GATE2['n']}): "
          f"{'PASS' if passed else 'FAIL'}  "
          f"got {g2['top1']}/{g2['n_tracks']} and {g2['top3']}/{g2['n_tracks']}")

    # ------------------------------------------------------ paired contrasts
    k54 = set(out['cells']['54_tdms']['correct1'])
    out['mcnemar_fused_vs_tdms_54'] = mcnemar(
        out['cells']['54_tdms']['correct1'], out['cells']['54_fused']['correct1'],
        sorted(k54))
    shared = sorted(k54 & set(out['cells']['51_tdms']['correct1']))
    for arm in ('tdms', 'fused'):
        out[f'mcnemar_51_vs_54_{arm}'] = mcnemar(
            out['cells'][f'54_{arm}']['correct1'],
            out['cells'][f'51_{arm}']['correct1'], shared)
        out[f'mcnemar_51_vs_54_{arm}']['note'] = (
            'paired at the track level but NOT at the fold level — the two tiers '
            'present a different row set to StratifiedGroupKFold, so some of the '
            'discordance is re-randomised fold membership rather than the drop. '
            'Same caveat as data/RAGA_COVERAGE_CURVE.md §5.')

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    # ------------------------------------------------------------- the table
    print('\n=== the 2x2, level (c), track-level ===')
    print(f"{'cell':>12} {'cls':>4} {'top-1':>16} {'top-3':>8} {'cov':>7} {'exp hits/100':>13}")
    for key in ('54_tdms', '54_fused', '51_tdms', '51_fused'):
        r = out['cells'][key]
        print(f"{key:>12} {r['n_classes']:>4} {r['top1']:>5}/{r['n_tracks']:<5} "
              f"{r['top1_rate']:>6.1%} {r['top3_rate']:>7.1%} {r['coverage']:>7.1%} "
              f"{r['expected_hits_per_100']:>13.2f}")
    print(f"\nwrote {out_path}")


if __name__ == '__main__':
    main()
