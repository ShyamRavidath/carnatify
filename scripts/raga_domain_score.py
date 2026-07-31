"""Domain decomposition, stage 3 — score every cell, the 2x2, and the drift.

Source-disjoint throughout. The fold assignment is computed **once**, at the
track level, over the inherited level-(c) group vector, with exactly the code
`scripts/raga_duration_score.py` uses — `StratifiedGroupKFold(n_splits=5,
shuffle=True, random_state=42)` over the 518 tier tracks in
`data/raga_duration/protocol.json` order. Every cell and every arm reuses it, so
all cells are exactly paired.

Arms, per `data/raga_domain/PREREGISTRATION.md` §5 and §7:

  mismatched  (PRIMARY, the only arm the interpretation table is read on)
              train on CLEAN FULL-TRACK TDMS — the existing
              `data/raga_duration/tdms_full.npz` shard — and test on the cell's
              degraded 60 s window. Five forests, one per fold, reused by every
              cell and every 2x2 arm.
  matched     (registered secondary, non-gating) train on the same cell's
              degraded windows in the train folds.
  2x2         clean/degraded contour x clean/estimated tonic, all four scored
              with the mismatched forests. A TDMS recomputation only — no new
              audio work — so it is computed for every cell and, per the
              prereg, INTERPRETED only where a cell costs more than ~10 points.

For the `pitch` cell the clean tonic is analytic, not estimated:
`tonic_ref * 2**(s/12)` with `s` the recorded `pitch_semitones`. The
"degraded tonic on the clean contour" arm therefore applies that cell's tonic
*error ratio* `t_est / t_true` to the clean contour's true tonic, which reduces
to the raw estimate in every cell whose true tonic is unchanged.

Reproduction gates (prereg §2), both run before any cell is reported:
  1. bit-level — the TDMS recomputed here from the cached contour at offset 0
     must match `data/raga_duration/tdms_60.npz` to 1e-6;
  2. score-level — the `cached` mismatched top-1 must equal the offset-0 subset
     of the duration curve's own `mismatched:60` cell.

Resumable: per-cell prediction rows land in `data/raga_domain/preds_<cell>.json`
as each cell finishes. `--aggregate-only` rebuilds `results.json` from disk.

Read-only. Nothing under `models/` is written.

Usage: venv/bin/python scripts/raga_domain_score.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from raga_domain_cells import feature_from_voiced, MEL_HOP_S, NB, TAUS  # noqa: E402

OUT_DIR = ROOT / 'data' / 'raga_domain'
DUR_DIR = ROOT / 'data' / 'raga_duration'

N_SPLITS = 5
SEED = 42
ORDER = ['cached', 'clean', 'noise', 'reverb', 'phone',
         'field_all', 'all', 'pitch', 'stretch', 'field_all_demucs']
REF_TONIC_CELLS = {'cached'}
# prereg §2's `clean_reftonic` row IS the `cd_tc` arm of the `clean` cell —
# melodia-on-clean-audio renormalised by the reference tonic. Same construction,
# one melodia pass instead of two.
DRIFT_TOL = 50.0          # cents, for the +-700 / +-1200 confusion buckets


def load_cell(cell):
    p = OUT_DIR / f'cell_{cell}.npz'
    if not p.exists():
        return None
    z = np.load(p, allow_pickle=True)
    meta = json.loads(str(z['meta']))
    off = z['contour_off']
    C = z['contour']
    contours = {}
    for m in meta:
        if m['findex'] >= 0:
            i = m['findex']
            contours[m['stem']] = C[off[i]:off[i + 1]]
    return dict(X=z['X'], meta=meta, contours=contours,
                by_stem={m['stem']: m for m in meta})


def true_tonic(m):
    """The cell's TRUE tonic: the reference, except under a global pitch shift
    where it is analytic — `tonic_ref * 2**(s/12)`."""
    s = m.get('params', {}).get('pitch_semitones')
    return m['tonic_ref'] * (2.0 ** (s / 12.0)) if s is not None else m['tonic_ref']


def cents(a, b):
    return 1200.0 * np.log2(a / b)


def fold_octave(c):
    """Fold a cents drift into (-600, +600]."""
    return c - 1200.0 * np.round(c / 1200.0)


def drift_stats(cellmeta):
    d, dfail = [], 0
    for m in cellmeta:
        if m['cell'] in REF_TONIC_CELLS:
            continue
        if m.get('tonic_est') is None:
            dfail += 1
            continue
        d.append(cents(m['tonic_est'], true_tonic(m)))
    if not d:
        return dict(n=0, n_tonic_fail=dfail)
    d = np.array(d)
    fo = fold_octave(d)
    near = lambda v, t: float(np.mean(np.abs(np.abs(v) - t) <= DRIFT_TOL))
    return dict(
        n=int(d.size), n_tonic_fail=int(dfail),
        median_abs_cents=float(np.median(np.abs(d))),
        mean_abs_cents=float(np.mean(np.abs(d))),
        p90_abs_cents=float(np.percentile(np.abs(d), 90)),
        frac_within_25=float(np.mean(np.abs(d) <= 25)),
        frac_within_50=float(np.mean(np.abs(d) <= 50)),
        frac_near_700=near(d, 700.0), frac_near_1200=near(d, 1200.0),
        median_abs_cents_octfold=float(np.median(np.abs(fo))),
        frac_within_25_octfold=float(np.mean(np.abs(fo) <= 25)),
        frac_near_700_octfold=near(fo, 700.0),
    )


def tally(meta):
    t = Counter(m['outcome'] for m in meta)
    return dict(n_windows=len(meta), scored=t.get('scored', 0),
                no_contour=t.get('no_contour', 0), min_voiced=t.get('min_voiced', 0),
                tdms_none=t.get('tdms_none', 0), error=t.get('error', 0),
                tonic_fail=sum(1 for m in meta if m.get('tonic_fail')))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--aggregate-only', action='store_true')
    ap.add_argument('--cells', default=','.join(ORDER))
    args = ap.parse_args()

    dproto = json.loads((DUR_DIR / 'protocol.json').read_text())
    recs = dproto['tracks']
    stem_order = [r['stem'] for r in recs]
    stem_ix = {s: i for i, s in enumerate(stem_order)}
    y = np.array([r['raga'] for r in recs])
    gc = np.array([r['group_c'] for r in recs])
    le = LabelEncoder()
    yi = le.fit_transform(y)
    group_of = {r['stem']: r['group_c'] for r in recs}

    # ---- clean full-track training features, verbatim from the duration curve
    z = np.load(DUR_DIR / 'tdms_full.npz', allow_pickle=True)
    fmeta = json.loads(str(z['meta']))
    frow = {m['stem']: m['findex'] for m in fmeta if m['ok']}
    Xf = np.stack([z['X'][frow[s]] for s in stem_order])
    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    folds = list(cv.split(Xf, yi, groups=gc))
    print(f'{len(stem_order)} tracks, {len(set(gc))} level-(c) groups, '
          f'{N_SPLITS} folds; full-track train matrix {Xf.shape}', flush=True)

    names = [c for c in args.cells.split(',') if (OUT_DIR / f'cell_{c}.npz').exists()]
    cells = {c: load_cell(c) for c in names}
    print('cells on disk:', names, flush=True)

    # ---- gate 1: bit-level reproduction against the duration curve ----------
    gates = {}
    if 'cached' in cells:
        z60 = np.load(DUR_DIR / 'tdms_60.npz', allow_pickle=True)
        m60 = json.loads(str(z60['meta']))
        first_rand = {}
        for m in m60:
            if m['kind'] == 'rand' and m['stem'] not in first_rand:
                first_rand[m['stem']] = m
        worst, n_cmp = 0.0, 0
        for m in cells['cached']['meta']:
            ref = first_rand.get(m['stem'])
            if ref is None or not ref['ok'] or m['findex'] < 0:
                continue
            d = float(np.max(np.abs(cells['cached']['X'][m['findex']]
                                    - z60['X'][ref['findex']])))
            worst = max(worst, d)
            n_cmp += 1
        gates['bitlevel_max_abs_diff'] = worst
        gates['bitlevel_n'] = n_cmp
        gates['bitlevel_pass'] = bool(worst <= 1e-6 and n_cmp == len(stem_order))
        print(f'GATE 1 (bit-level vs tdms_60.npz offset-0): n={n_cmp} '
              f'max|diff|={worst:.3e} -> {"PASS" if gates["bitlevel_pass"] else "FAIL"}',
              flush=True)
        if not gates['bitlevel_pass']:
            raise SystemExit('reproduction gate 1 failed; no cell is reported')

    # ---- score ------------------------------------------------------------
    if not args.aggregate_only:
        clean = cells.get('clean')
        for cell in names:
            fp = OUT_DIR / f'preds_{cell}.json'
            if fp.exists():
                print(f'-- {cell}: preds exist, skipping', flush=True)
                continue
            sh = cells[cell]
            t0 = time.time()
            rows = []
            for k, (tr, te) in enumerate(folds):
                te_stems = [stem_order[i] for i in te]
                clf = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                             random_state=SEED, n_jobs=-1)
                clf.fit(Xf[tr], yi[tr])
                cs = clf.classes_

                def emit(arm, items):
                    """items: list of (stem, feature vector)"""
                    if not items:
                        return
                    proba = clf.predict_proba(np.stack([f for _, f in items]))
                    for (s, _), p in zip(items, proba):
                        o = np.argsort(-p)
                        true = int(yi[stem_ix[s]])
                        rows.append(dict(arm=arm, cell=cell, stem=s,
                                         top1=bool(cs[o[0]] == true),
                                         top3=bool(true in cs[o[:3]]),
                                         pred=int(cs[o[0]]), true=true))

                # --- primary: mismatched, the cell as built
                prim = [(s, sh['X'][sh['by_stem'][s]['findex']]) for s in te_stems
                        if sh['by_stem'][s]['findex'] >= 0]
                emit('mismatched', prim)

                # --- 2x2, only meaningful for degraded cells
                if cell not in REF_TONIC_CELLS and clean is not None:
                    a_cd_tc, a_cc_td = [], []
                    for s in te_stems:
                        m = sh['by_stem'][s]
                        mc = clean['by_stem'][s]
                        if m['findex'] < 0 or mc['findex'] < 0:
                            continue
                        tt = true_tonic(m)
                        # degraded contour + the cell's CLEAN (true) tonic
                        f1 = feature_from_voiced(sh['contours'][s], tt, m['hop'])
                        if f1 is not None:
                            a_cd_tc.append((s, np.asarray(f1, np.float32)))
                        # clean contour + the cell's tonic ERROR ratio
                        if m.get('tonic_est') is not None:
                            t_on_clean = mc['tonic_ref'] * (m['tonic_est'] / tt)
                            f2 = feature_from_voiced(clean['contours'][s],
                                                     t_on_clean, mc['hop'])
                            if f2 is not None:
                                a_cc_td.append((s, np.asarray(f2, np.float32)))
                    emit('cd_tc', a_cd_tc)      # contour damage alone
                    emit('cc_td', a_cc_td)      # tonic damage alone

                # --- registered secondary: matched
                tr_items = [(stem_order[i], sh['X'][sh['by_stem'][stem_order[i]]['findex']])
                            for i in tr if sh['by_stem'][stem_order[i]]['findex'] >= 0]
                if len(tr_items) > 20:
                    clfm = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                                  random_state=SEED, n_jobs=-1)
                    clfm.fit(np.stack([f for _, f in tr_items]),
                             np.array([yi[stem_ix[s]] for s, _ in tr_items]))
                    csm = clfm.classes_
                    if prim:
                        pm = clfm.predict_proba(np.stack([f for _, f in prim]))
                        for (s, _), p in zip(prim, pm):
                            o = np.argsort(-p)
                            true = int(yi[stem_ix[s]])
                            rows.append(dict(arm='matched', cell=cell, stem=s,
                                             top1=bool(csm[o[0]] == true),
                                             top3=bool(true in csm[o[:3]]),
                                             pred=int(csm[o[0]]), true=true))
            fp.write_text(json.dumps(rows))
            print(f'   {cell}: {len(rows)} rows in {time.time() - t0:.0f}s', flush=True)

    # ---- aggregate ---------------------------------------------------------
    rows = []
    for cell in names:
        fp = OUT_DIR / f'preds_{cell}.json'
        if fp.exists():
            rows += json.loads(fp.read_text())
    print(f'\naggregating {len(rows)} predictions over {len(names)} cells')

    all_groups = sorted(set(group_of.values()))
    rng = np.random.default_rng(SEED)
    boot_ix = [rng.choice(len(all_groups), len(all_groups), replace=True)
               for _ in range(2000)]

    def gvec(cell, arm):
        by_g = defaultdict(list)
        for r in rows:
            if r['cell'] == cell and r['arm'] == arm:
                by_g[group_of[r['stem']]].append(r['top1'])
        return [np.array(by_g.get(g, []), dtype=float) for g in all_groups]

    def ci(vecs):
        reps = [np.concatenate([vecs[i] for i in ix if vecs[i].size]).mean()
                for ix in boot_ix]
        return [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]

    def paired(a, b):
        reps = []
        for ix in boot_ix:
            va = np.concatenate([a[i] for i in ix if a[i].size])
            vb = np.concatenate([b[i] for i in ix if b[i].size])
            reps.append(va.mean() - vb.mean())
        return [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]

    out = dict(tier_ragas=list(le.classes_), level_c_groups=len(set(gc)),
               n_tracks=len(stem_order), gates=gates, cells={}, drift={},
               voicing={}, arms={}, paired={}, per_raga={})

    for cell in names:
        sh = cells[cell]
        out['cells'][cell] = tally(sh['meta'])
        out['cells'][cell]['components'] = None
        out['drift'][cell] = drift_stats(sh['meta'])
        ok = [m for m in sh['meta'] if m['outcome'] == 'scored']
        if ok:
            dens = np.array([m['density'] for m in ok])
            rs = np.array([m['real_s'] for m in ok])
            nv = np.array([m['n_voiced'] for m in ok])
            out['voicing'][cell] = dict(
                n=len(ok), density_mean=float(dens.mean()), density_sd=float(dens.std()),
                density_p05=float(np.percentile(dens, 5)),
                voiced_frames_mean=float(nv.mean()), voiced_frames_min=int(nv.min()),
                voiced_frames_p05=float(np.percentile(nv, 5)),
                mean_real_s=float(rs.mean()), min_real_s=float(rs.min()),
                max_real_s=float(rs.max()),
                effective_tau_s={f'{t}': float(t / dens.mean()) for t in TAUS})
        for arm in ('mismatched', 'matched', 'cd_tc', 'cc_td'):
            sel = [r for r in rows if r['cell'] == cell and r['arm'] == arm]
            if not sel:
                continue
            cnt = Counter(r['true'] for r in sel)
            prior = np.array([c / len(sel) for c in cnt.values()])
            out['arms'][f'{cell}:{arm}'] = dict(
                cell=cell, arm=arm, n=len(sel),
                n_all_windows=len(sh['meta']),
                top1=sum(r['top1'] for r in sel), top3=sum(r['top3'] for r in sel),
                top1_rate=sum(r['top1'] for r in sel) / len(sel),
                top3_rate=sum(r['top3'] for r in sel) / len(sel),
                top1_rate_all_windows=sum(r['top1'] for r in sel) / len(sh['meta']),
                majority_class_rate=float(prior.max()),
                class_prior_expectation=float((prior ** 2).sum()),
                boot_ci95=ci(gvec(cell, arm)))

    if 'clean' in names:
        gclean = gvec('clean', 'mismatched')
        for cell in names:
            if f'{cell}:mismatched' not in out['arms'] or cell == 'clean':
                continue
            g = gvec(cell, 'mismatched')
            out['paired'][f'clean-minus-{cell}'] = dict(
                delta=float(out['arms']['clean:mismatched']['top1_rate']
                            - out['arms'][f'{cell}:mismatched']['top1_rate']),
                ci95=paired(gclean, g))

    for cell in names:
        sel = [r for r in rows if r['cell'] == cell and r['arm'] == 'mismatched']
        if not sel:
            continue
        pr = {}
        for i, rname in enumerate(le.classes_):
            a = [r for r in sel if r['true'] == i]
            if a:
                pr[rname] = dict(n=len(a), top1=float(np.mean([r['top1'] for r in a])),
                                 top3=float(np.mean([r['top3'] for r in a])))
        out['per_raga'][cell] = pr

    (OUT_DIR / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))

    # ---- print -------------------------------------------------------------
    print(f"\n{'cell':18s} {'win':>4s} {'scored':>6s} {'noCtr':>6s} {'minV':>5s} "
          f"{'tdmsN':>6s} {'tFail':>6s}   mismatched top-1 (of scored)        "
          f"of all 518   top-3")
    for cell in names:
        c = out['cells'][cell]
        a = out['arms'].get(f'{cell}:mismatched')
        s = (f"{a['top1']:4d}/{a['n']:<4d}={a['top1_rate']:6.1%} "
             f"[{a['boot_ci95'][0]:.1%}-{a['boot_ci95'][1]:.1%}]"
             f"  {a['top1_rate_all_windows']:6.1%}   {a['top3_rate']:6.1%}") if a else ''
        print(f"{cell:18s} {c['n_windows']:4d} {c['scored']:6d} {c['no_contour']:6d} "
              f"{c['min_voiced']:5d} {c['tdms_none']:6d} {c['tonic_fail']:6d}   {s}")

    print('\ntonic drift vs the cell TRUE tonic (analytic for `pitch`):')
    print(f"{'cell':18s} {'n':>4s} {'fail':>5s} {'med|d|':>8s} {'p90|d|':>8s} "
          f"{'<=25c':>7s} {'<=50c':>7s} {'~700c':>7s} {'~1200c':>7s} "
          f"{'octfold med':>12s} {'octfold<=25':>12s}")
    for cell in names:
        d = out['drift'][cell]
        if not d.get('n'):
            continue
        print(f"{cell:18s} {d['n']:4d} {d['n_tonic_fail']:5d} "
              f"{d['median_abs_cents']:8.1f} {d['p90_abs_cents']:8.1f} "
              f"{d['frac_within_25']:7.1%} {d['frac_within_50']:7.1%} "
              f"{d['frac_near_700']:7.1%} {d['frac_near_1200']:7.1%} "
              f"{d['median_abs_cents_octfold']:12.1f} {d['frac_within_25_octfold']:12.1%}")

    print('\nthe 2x2 (all four arms on the mismatched forests):')
    print(f"{'cell':18s} {'Cc/Tc (clean_reftonic)':>22s} {'Cd/Tc contour only':>20s} "
          f"{'Cc/Td tonic only':>18s} {'Cd/Td the cell':>16s}")
    base = out['arms'].get('clean:cd_tc')
    for cell in names:
        if cell in REF_TONIC_CELLS:
            continue
        g = lambda k: out['arms'].get(f'{cell}:{k}')
        f = lambda a: f"{a['top1_rate']:6.1%} (n={a['n']})" if a else '     -'
        print(f"{cell:18s} {f(base):>22s} {f(g('cd_tc')):>20s} "
              f"{f(g('cc_td')):>18s} {f(g('mismatched')):>16s}")

    print('\nmatched arm (registered secondary, non-gating):')
    for cell in names:
        a = out['arms'].get(f'{cell}:matched')
        if a:
            print(f"  {cell:18s} {a['top1']:4d}/{a['n']:<4d} = {a['top1_rate']:6.1%}"
                  f"  top3 {a['top3_rate']:6.1%}")

    print('\npaired clean-minus-cell (2000x source-group bootstrap, post-hoc):')
    for k, v in out['paired'].items():
        print(f"  {k:30s} {100 * v['delta']:+6.1f}pp  95% CI "
              f"{100 * v['ci95'][0]:+6.1f} .. {100 * v['ci95'][1]:+6.1f}pp")

    print('\nvoicing / real window length:')
    for cell in names:
        v = out['voicing'].get(cell)
        if v:
            print(f"  {cell:18s} n={v['n']:4d} density {v['density_mean']:.3f} "
                  f"(sd {v['density_sd']:.3f}, p05 {v['density_p05']:.3f})  "
                  f"voiced frames mean {v['voiced_frames_mean']:8.0f} min "
                  f"{v['voiced_frames_min']:6d}  real {v['mean_real_s']:.1f}s "
                  f"[{v['min_real_s']:.1f}-{v['max_real_s']:.1f}]  "
                  f"eff tau(0.1) {v['effective_tau_s']['0.1']:.3f}s")
    print(f"\nwrote {OUT_DIR / 'results.json'}")


if __name__ == '__main__':
    main()
