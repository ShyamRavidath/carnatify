"""Score the coverage/accuracy curve from the per-tier level files.

Consumes `data/raga_coverage/levels_min<N>.json` (written by
`scripts/raga_audit_levels.py --min-tracks ... --per-track`) and
`data/raga_coverage/coverage.json`, and produces every number
`WORKHORSE_RAGA_COVERAGE_BRIEF.md` §4 asks for. It fits nothing and trains
nothing — all of it is arithmetic over per-track correctness that already
exists on disk, so it can be re-run at zero cost and the curve can be rebuilt
by anyone from the committed json.

Methods are those registered in `data/raga_coverage/PREREGISTRATION.md` §8 and
are not to be changed after seeing the numbers:

- uncertainty = cluster bootstrap over the tier's own level-(c) source groups,
  2000 replicates, `default_rng(42)`, percentile interval. Wilson on the raw
  track count is printed beside it, labelled as the too-narrow comparator;
- expected hits per 100 heard items = repertoire coverage x level-(c) top-1;
- the paired flip test is restricted to the 518 tracks of the `min>=25` tier,
  McNemar exact two-sided binomial on the discordant pairs.

Usage: venv/bin/python scripts/raga_coverage_curve.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / 'data' / 'raga_coverage'
TIERS = (25, 20, 15, 10)
N_BOOT = 2000
SEED = 42


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def cluster_bootstrap(correct, group_of, n_boot=N_BOOT, seed=SEED):
    """Resample level-(c) SOURCE GROUPS with replacement, not tracks.

    The tracks are not independent: 518-1139 of them sit in 155-204 source
    clusters and the folds are disjoint on those clusters, so a binomial
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
    return float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5)), reps


def load(mt):
    return json.loads((DIR / f'levels_min{mt}.json').read_text())


def main() -> None:
    cov = json.loads((DIR / 'coverage.json').read_text())
    D = {mt: load(mt) for mt in TIERS}
    out = {'tiers': {}, 'method': {
        'bootstrap': f'cluster bootstrap over level-(c) source groups, '
                     f'{N_BOOT} replicates, default_rng({SEED}), percentile',
        'expected_hits': 'repertoire coverage x level-(c) top-1, per 100 items',
        'mcnemar': 'exact two-sided binomial on discordant pairs, 518 tracks '
                   'of the min>=25 tier, level (c)'}}

    # ---------------------------------------------------------------- curve
    print('=== the curve: level (c), source-disjoint ===\n')
    print(f"{'tier':>6} {'cls':>4} {'trk':>5} {'grp':>4} {'fold':>4} "
          f"{'top1':>16} {'95% CI (cluster)':>18} {'95% CI (Wilson)':>17} "
          f"{'floor':>7} {'x floor':>8} {'top3':>16}")
    for mt in TIERS:
        d = D[mt]
        c = d['levels']['c']
        pt = d['per_track']['c']
        lo, hi, _ = cluster_bootstrap(pt['correct1'], pt['group_of'])
        lo3, hi3, _ = cluster_bootstrap(pt['correct3'], pt['group_of'])
        wlo, whi = wilson(c['top1'], c['n_tracks'])
        floor = c['class_prior_expectation']
        rep = cov['tiers'][str(mt)]['repertoire_coverage']
        hits = rep * c['top1_rate']
        out['tiers'][str(mt)] = dict(
            classes=c['n_ragas'], n_tracks=c['n_tracks'], n_groups=c['n_groups'],
            n_folds=c['n_folds'],
            top1=c['top1'], top1_rate=c['top1_rate'], top1_ci=[lo, hi],
            top1_wilson=[wlo, whi],
            top3=c['top3'], top3_rate=c['top3_rate'], top3_ci=[lo3, hi3],
            majority_class_rate=c['majority_class_rate'],
            class_prior_expectation=floor,
            top1_minus_floor=c['top1_rate'] - floor,
            top1_over_floor=c['top1_rate'] / floor,
            level_a_top1_rate=d['levels']['a']['top1_rate'],
            level_a_top1=d['levels']['a']['top1'],
            level_a_top3=d['levels']['a']['top3'],
            level_a_top3_rate=d['levels']['a']['top3_rate'],
            repertoire_coverage=rep,
            expected_hits_per_100=100 * hits,
        )
        print(f"{mt:>6} {c['n_ragas']:>4} {c['n_tracks']:>5} {c['n_groups']:>4} "
              f"{c['n_folds']:>4} "
              f"{c['top1']:>5}/{c['n_tracks']:<4} {c['top1_rate']:>5.1%} "
              f"{lo:>8.1%} - {hi:<7.1%} {wlo:>7.1%} - {whi:<6.1%} "
              f"{floor:>7.4f} {c['top1_rate'] / floor:>7.1f}x "
              f"{c['top3']:>5}/{c['n_tracks']:<4} {c['top3_rate']:>5.1%}")

    print('\n=== expected hits per 100 heard concert items ===\n')
    print(f"{'tier':>6} {'cls':>4} {'coverage':>9} {'top-1':>7} "
          f"{'expected hits/100':>18} {'top3 hits/100':>14}")
    for mt in TIERS:
        t = out['tiers'][str(mt)]
        print(f"{mt:>6} {t['classes']:>4} {t['repertoire_coverage']:>8.1%} "
              f"{t['top1_rate']:>6.1%} {t['expected_hits_per_100']:>17.1f} "
              f"{100 * t['repertoire_coverage'] * t['top3_rate']:>13.1f}")

    # ------------------------------------------------- per class, widest tier
    print('\n=== per-class level-(c) top-1 at min>=10 (54 classes), sorted ===\n')
    d10 = D[10]
    inv = json.loads((DIR / 'inventory.json').read_text())['tiers']['10']
    gpr = inv['levels']['c']['groups_per_raga']
    floor10 = d10['levels']['c']['class_prior_expectation']
    rows = []
    for r, v in d10['per_raga_level_c'].items():
        rows.append((r, v['n_tracks'], gpr.get(r, 0), v['top1_c'], v['top3_c']))
    rows.sort(key=lambda x: (-x[3], x[0]))
    in25 = set(D[25]['tier']['ragas'])
    err_total = d10['levels']['c']['n_tracks'] - d10['levels']['c']['top1']
    err_below40 = 0
    below_floor = []
    for r, n, ng, t1, t3 in rows:
        tag = ' ' if r in in25 else '+'
        print(f"{tag}{r:<22} n={n:>4} grp={ng:>3}  top1={t1:>6.1%}  top3={t3:>6.1%}")
        if t1 < 0.40:
            err_below40 += n * (1 - t1)
        if t1 < floor10:
            below_floor.append(r)
    print(f"\n('+' = class added since the min>=25 tier)")
    print(f"classes below 40% top-1 account for {err_below40:.0f} of {err_total} "
          f"top-1 errors = {err_below40 / err_total:.1%}")
    print(f"classes below the class-prior floor ({floor10:.4f}): "
          f"{below_floor if below_floor else 'none'}")
    out['per_class_min10'] = [dict(raga=r, n_tracks=n, n_groups=ng, top1=t1, top3=t3,
                                   added_since_min25=r not in in25)
                              for r, n, ng, t1, t3 in rows]
    out['errors_from_classes_below_40pct'] = dict(
        errors_attributed=float(err_below40), errors_total=int(err_total),
        share=float(err_below40 / err_total))
    out['classes_below_class_prior_floor_min10'] = below_floor

    # ------------------------------------------------------- the flip test
    print('\n=== the crux: do the added classes poison the original 18? ===')
    print('    (level (c), restricted to the 518 tracks of the min>=25 tier)\n')
    base = D[25]['per_track']['c']['correct1']
    keys = sorted(base)
    out['flips'] = {}
    print(f"{'tier':>6} {'cls':>4} {'top1 on the 518':>16} {'delta':>8} "
          f"{'b (25 ok -> wrong)':>19} {'c (wrong -> ok)':>16} {'McNemar exact p':>16}")
    b25 = sum(base[k] for k in keys)
    print(f"{25:>6} {18:>4} {b25:>5}/518 {b25 / 518:>7.1%} {'—':>8} "
          f"{'—':>19} {'—':>16} {'—':>16}")
    for mt in (20, 15, 10):
        other = D[mt]['per_track']['c']['correct1']
        missing = [k for k in keys if k not in other]
        assert not missing, f'{len(missing)} of the 518 tracks absent at min>={mt}'
        hit = sum(other[k] for k in keys)
        b = sum(1 for k in keys if base[k] and not other[k])
        c = sum(1 for k in keys if not base[k] and other[k])
        p = binomtest(b, b + c, 0.5, alternative='two-sided').pvalue if b + c else 1.0
        out['flips'][str(mt)] = dict(n=len(keys), top1_at_25=b25, top1_at_tier=hit,
                                     delta_pp=100 * (hit - b25) / len(keys),
                                     b_correct_to_wrong=b, c_wrong_to_correct=c,
                                     mcnemar_exact_p=float(p))
        print(f"{mt:>6} {D[mt]['levels']['c']['n_ragas']:>4} {hit:>5}/518 "
              f"{hit / 518:>7.1%} {100 * (hit - b25) / 518:>+7.1f}pp "
              f"{b:>19} {c:>16} {p:>16.4g}")

    # ------------------------------------- who pays: incumbents or the newcomers
    print('\n=== who pays: the 18 incumbent classes vs the 36 added ones ===\n')
    print(f"{'tier':>6} {'incumbent 518':>16} {'added tracks':>18} {'all':>16}")
    out['incumbent_vs_added'] = {}
    for mt in TIERS:
        pt = D[mt]['per_track']['c']['correct1']
        inc = {k: v for k, v in pt.items() if k in base}
        add = {k: v for k, v in pt.items() if k not in base}
        ih, it = sum(inc.values()), len(inc)
        ah, at = sum(add.values()), len(add)
        row = dict(incumbent_hits=ih, incumbent_n=it, incumbent_rate=ih / it,
                   added_hits=ah, added_n=at,
                   added_rate=(ah / at) if at else None)
        out['incumbent_vs_added'][str(mt)] = row
        astr = f"{ah:>5}/{at:<5} {ah / at:>6.1%}" if at else f"{'—':>18}"
        tot = D[mt]['levels']['c']
        print(f"{mt:>6} {ih:>5}/{it:<4} {ih / it:>7.1%} {astr:>18} "
              f"{tot['top1']:>5}/{tot['n_tracks']:<4} {tot['top1_rate']:>6.1%}")

    # ---------------------------------------- is the fall log-linear in classes?
    ks = np.array([out['tiers'][str(mt)]['classes'] for mt in TIERS], dtype=float)
    ts = np.array([out['tiers'][str(mt)]['top1_rate'] for mt in TIERS])
    slope, intercept = np.polyfit(np.log(ks), ts, 1)
    pred = slope * np.log(ks) + intercept
    r2 = 1 - ((ts - pred) ** 2).sum() / ((ts - ts.mean()) ** 2).sum()
    out['log_linear_fit'] = dict(slope_pp_per_ln_class=100 * float(slope),
                                 intercept=float(intercept), r2=float(r2),
                                 residuals_pp=[float(100 * r) for r in (ts - pred)])
    print(f"\nlog-linear fit of top-1 on ln(classes): "
          f"{100 * slope:+.1f} pp per natural-log unit of class count, "
          f"R^2 = {r2:.4f}, residuals "
          f"{', '.join(f'{100 * r:+.2f}' for r in ts - pred)} pp")

    # -------------------------------------------------- weak classes, per tier
    print('\n=== registered watch: Vasanta, and the sub-40% tail, per tier ===\n')
    out['weak_classes'] = {}
    for mt in TIERS:
        pr = D[mt]['per_raga_level_c']
        below = sorted((r for r, v in pr.items() if v['top1_c'] < 0.40),
                       key=lambda r: pr[r]['top1_c'])
        errs = sum(pr[r]['n_tracks'] * (1 - pr[r]['top1_c']) for r in below)
        tot_err = D[mt]['levels']['c']['n_tracks'] - D[mt]['levels']['c']['top1']
        out['weak_classes'][str(mt)] = dict(
            vasanta_top1=pr.get('Vasanta', {}).get('top1_c'),
            n_below_40pct=len(below), classes_below_40pct=below,
            errors_from_them=float(errs), errors_total=int(tot_err),
            share_of_errors=float(errs / tot_err))
        print(f"min>={mt:<3} Vasanta {pr['Vasanta']['top1_c']:>6.1%}   "
              f"{len(below):>2} classes below 40% top-1, carrying "
              f"{errs:>5.0f}/{tot_err} = {errs / tot_err:>5.1%} of all top-1 errors")

    (DIR / 'curve.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nwrote {DIR / 'curve.json'}")


if __name__ == '__main__':
    main()
