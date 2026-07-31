"""Duration curve, stage 3 — the matched and mismatched arms at every duration.

Source-disjoint throughout: the fold assignment is computed **once**, at the
track level, over the inherited level-(c) group vector, and every cell of both
arms reuses it. The two arms therefore share identical test window sets and are
exactly paired.

  matched     — train on windows of duration d, test on windows of duration d
  mismatched  — train on FULL tracks, test on windows of duration d

The mismatched arm's model for a fold *is* the full-track model of that fold, so
it is fitted once per fold and reused at every duration: 5 full-track fits + 25
matched fits = 30 forests, not 60.

The full-track matched cell is the audit's level (c) re-run through this
pipeline and is the reproduction gate: it must land within ±0.5 pp of
374/518 = 72.2% top-1 and 435/518 = 84.0% top-3.

Resumable: per-fold predictions are written to
`data/raga_duration/preds_fold{k}.json` as each fold completes; a fold whose
file exists is skipped. `--aggregate-only` rebuilds
`data/raga_duration/results.json` from whatever folds are on disk.

Read-only. Nothing under `models/` is written.

Usage: venv/bin/python scripts/raga_duration_score.py
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'data' / 'raga_duration'

N_SPLITS = 5
SEED = 42
DUR_LABELS = ('30', '60', '120', '300', '600', 'full')
TRAIN_KINDS = ('rand', 'short', 'full')      # `start` is test-only
PRIMARY_KINDS = ('rand', 'short', 'full')    # primary read-out; `start` secondary


def load_shard(label):
    z = np.load(OUT_DIR / f'tdms_{label}.npz', allow_pickle=True)
    meta = json.loads(str(z['meta']))
    return z['X'], meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--aggregate-only', action='store_true')
    args = ap.parse_args()

    proto = json.loads((OUT_DIR / 'protocol.json').read_text())
    recs = proto['tracks']
    stem_order = [r['stem'] for r in recs]
    stem_ix = {s: i for i, s in enumerate(stem_order)}
    y = np.array([r['raga'] for r in recs])
    gc = np.array([r['group_c'] for r in recs])
    le = LabelEncoder()
    yi = le.fit_transform(y)

    shards = {}
    for lab in DUR_LABELS:
        X, meta = load_shard(lab)
        # row index into X for each scored window, grouped by track
        by_track = defaultdict(list)
        for m in meta:
            if m['ok']:
                by_track[m['stem']].append(m)
        shards[lab] = dict(X=X, meta=meta, by_track=by_track)
        print(f'shard {lab}: X {X.shape}  windows {len(meta)}  '
              f'scored {sum(1 for m in meta if m["ok"])}', flush=True)

    Xfull = shards['full']['X']
    full_row = {}
    for m in shards['full']['meta']:
        if m['ok']:
            full_row[m['stem']] = m['findex']
    keep_ix = np.array([i for i, s in enumerate(stem_order) if s in full_row])
    assert len(keep_ix) == len(stem_order), 'a tier track lost its full-track feature'
    Xf = np.stack([Xfull[full_row[s]] for s in stem_order])

    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    folds = list(cv.split(Xf, yi, groups=gc))

    if not args.aggregate_only:
        for k, (tr, te) in enumerate(folds):
            fp = OUT_DIR / f'preds_fold{k}.json'
            if fp.exists():
                print(f'-- fold {k}: exists, skipping', flush=True)
                continue
            t0 = time.time()
            te_stems = {stem_order[i] for i in te}
            clf_full = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                              random_state=SEED, n_jobs=-1)
            clf_full.fit(Xf[tr], yi[tr])
            print(f'fold {k}: full-track forest fitted in {time.time() - t0:.0f}s '
                  f'({len(tr)} train tracks)', flush=True)
            rows = []

            def score(clf, X, metas, arm, dur):
                if not metas:
                    return
                proba = clf.predict_proba(np.stack([X[m['findex']] for m in metas]))
                cs = clf.classes_
                for m, p in zip(metas, proba):
                    true = int(yi[stem_ix[m['stem']]])
                    order = np.argsort(-p)
                    rows.append(dict(arm=arm, dur=dur, stem=m['stem'], kind=m['kind'],
                                     n_voiced=m['n_voiced'], n_raw=m['n_raw'],
                                     real_s=m['real_s'], short=m['short'],
                                     top1=bool(cs[order[0]] == true),
                                     top3=bool(true in cs[order[:3]]),
                                     pred=int(cs[order[0]]), true=true))

            for lab in DUR_LABELS:
                sh = shards[lab]
                te_meta = [m for s in te_stems for m in sh['by_track'].get(s, [])]
                tr_meta = [m for i in tr for m in sh['by_track'].get(stem_order[i], [])
                           if m['kind'] in TRAIN_KINDS]
                if lab == 'full':
                    score(clf_full, sh['X'], te_meta, 'matched', lab)
                else:
                    score(clf_full, sh['X'], te_meta, 'mismatched', lab)
                    t1 = time.time()
                    clf_d = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                                   random_state=SEED, n_jobs=-1)
                    clf_d.fit(np.stack([sh['X'][m['findex']] for m in tr_meta]),
                              np.array([yi[stem_ix[m['stem']]] for m in tr_meta]))
                    score(clf_d, sh['X'], te_meta, 'matched', lab)
                    print(f'   fold {k} d={lab}: matched forest on {len(tr_meta)} '
                          f'windows in {time.time() - t1:.0f}s, tested on {len(te_meta)}',
                          flush=True)
            fp.write_text(json.dumps(rows))
            print(f'fold {k} done in {time.time() - t0:.0f}s -> {fp.name}', flush=True)

    # ---- aggregate ---------------------------------------------------------
    rows = []
    nf = 0
    for k in range(N_SPLITS):
        fp = OUT_DIR / f'preds_fold{k}.json'
        if fp.exists():
            rows += json.loads(fp.read_text())
            nf += 1
    print(f'\naggregating {len(rows)} window predictions from {nf}/{N_SPLITS} folds')

    classes = list(le.classes_)
    out = dict(n_folds_scored=nf, tier_ragas=classes,
               level_c_groups=proto['level_c_groups'], cells={}, per_raga_60s={},
               voicing={}, secondary_start={})

    for lab in DUR_LABELS:
        sh = shards[lab]
        meta = sh['meta']
        prim = [m for m in meta if m['kind'] in PRIMARY_KINDS]
        disc_mv = sum(1 for m in prim if not m['ok'] and m['drop'] == 'min_voiced')
        disc_tn = sum(1 for m in prim if not m['ok'] and m['drop'] == 'tdms_none')
        n_short = len({m['stem'] for m in meta if m['short']})
        dens = np.array([m['n_voiced'] / m['n_raw'] for m in prim if m['ok']])
        nv = np.array([m['n_voiced'] for m in prim if m['ok']])
        out['voicing'][lab] = dict(
            n=int(dens.size), density_mean=float(dens.mean()),
            density_sd=float(dens.std()), density_p05=float(np.percentile(dens, 5)),
            density_p95=float(np.percentile(dens, 95)),
            voiced_frames_mean=float(nv.mean()), voiced_frames_min=int(nv.min()),
            voiced_frames_p05=float(np.percentile(nv, 5)),
            effective_tau_s={f'{t}': float(t / dens.mean()) for t in (0.1, 0.15, 0.25)},
        )
        for arm in ('matched', 'mismatched'):
            sel = [r for r in rows if r['dur'] == lab and r['arm'] == arm
                   and r['kind'] in PRIMARY_KINDS]
            if not sel:
                continue
            cnt = Counter(r['true'] for r in sel)
            tot = sum(cnt.values())
            prior = np.array([c / tot for c in cnt.values()])
            out['cells'][f'{arm}:{lab}'] = dict(
                arm=arm, duration=lab, n_scored=len(sel),
                n_discard_min_voiced=disc_mv, n_discard_tdms_none=disc_tn,
                n_tracks_short=n_short,
                n_tracks=len({r['stem'] for r in sel}),
                top1=sum(r['top1'] for r in sel), top3=sum(r['top3'] for r in sel),
                top1_rate=sum(r['top1'] for r in sel) / len(sel),
                top3_rate=sum(r['top3'] for r in sel) / len(sel),
                majority_class_rate=float(prior.max()),
                class_prior_expectation=float((prior ** 2).sum()),
                mean_real_s=float(np.mean([r['real_s'] for r in sel])),
                # registered disaggregation: tracks shorter than d contribute
                # their WHOLE length once, so they are not a point on the curve
                by_kind={
                    kd: dict(n=len(s), top1=sum(r['top1'] for r in s),
                             top1_rate=sum(r['top1'] for r in s) / len(s),
                             top3_rate=sum(r['top3'] for r in s) / len(s),
                             mean_real_s=float(np.mean([r['real_s'] for r in s])))
                    for kd in ('rand', 'short', 'full')
                    if (s := [r for r in sel if r['kind'] == kd])
                },
            )
            st = [r for r in rows if r['dur'] == lab and r['arm'] == arm
                  and r['kind'] == 'start']
            if st:
                out['secondary_start'][f'{arm}:{lab}'] = dict(
                    n=len(st), top1=sum(r['top1'] for r in st),
                    top3=sum(r['top3'] for r in st),
                    top1_rate=sum(r['top1'] for r in st) / len(st),
                    top3_rate=sum(r['top3'] for r in st) / len(st))

    # ---- uncertainty, computed AFTER the cells and labelled as post-hoc -----
    # Windows are not independent: 1554 windows come from 518 tracks in 155
    # level-(c) source groups. A binomial interval on n=1554 would be far too
    # narrow. This resamples the 155 SOURCE GROUPS with replacement, which is
    # the unit the folds are disjoint on.
    group_of = {r['stem']: r['group_c'] for r in recs}
    rng = np.random.default_rng(SEED)
    all_groups = sorted(set(group_of.values()))
    boot_ix = [rng.choice(len(all_groups), len(all_groups), replace=True)
               for _ in range(2000)]
    for key, cell in out['cells'].items():
        lab, arm = cell['duration'], cell['arm']
        sel = [r for r in rows if r['dur'] == lab and r['arm'] == arm
               and r['kind'] in PRIMARY_KINDS]
        by_g = defaultdict(list)
        for r in sel:
            by_g[group_of[r['stem']]].append(r['top1'])
        hits = [np.array(by_g.get(g, []), dtype=float) for g in all_groups]
        reps = []
        for ix in boot_ix:
            v = np.concatenate([hits[i] for i in ix if hits[i].size])
            reps.append(v.mean())
        cell['boot_ci95'] = [float(np.percentile(reps, 2.5)),
                             float(np.percentile(reps, 97.5))]

    # paired differences, resampled on the same source groups: matched minus
    # mismatched at each duration (identical test windows), and full-track
    # minus duration d on the matched arm (identical tracks).
    def gvec(lab, arm):
        by_g = defaultdict(list)
        for r in rows:
            if r['dur'] == lab and r['arm'] == arm and r['kind'] in PRIMARY_KINDS:
                by_g[group_of[r['stem']]].append(r['top1'])
        return [np.array(by_g.get(g, []), dtype=float) for g in all_groups]

    def paired(a, b):
        reps = []
        for ix in boot_ix:
            va = np.concatenate([a[i] for i in ix if a[i].size])
            vb = np.concatenate([b[i] for i in ix if b[i].size])
            reps.append(va.mean() - vb.mean())
        return (float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5)))

    gfull = gvec('full', 'matched')
    out['paired'] = {}
    for lab in DUR_LABELS:
        gm = gvec(lab, 'matched')
        if lab != 'full':
            gx = gvec(lab, 'mismatched')
            out['paired'][f'matched-minus-mismatched:{lab}'] = dict(
                delta=float(out['cells'][f'matched:{lab}']['top1_rate']
                            - out['cells'][f'mismatched:{lab}']['top1_rate']),
                ci95=paired(gm, gx))
        out['paired'][f'full-minus-matched:{lab}'] = dict(
            delta=float(out['cells']['matched:full']['top1_rate']
                        - out['cells'][f'matched:{lab}']['top1_rate']),
            ci95=paired(gfull, gm))

    sel60 = [r for r in rows if r['dur'] == '60' and r['arm'] == 'matched'
             and r['kind'] in PRIMARY_KINDS]
    selfull = [r for r in rows if r['dur'] == 'full' and r['arm'] == 'matched']
    for i, rname in enumerate(classes):
        a = [r for r in sel60 if r['true'] == i]
        b = [r for r in selfull if r['true'] == i]
        if a:
            out['per_raga_60s'][rname] = dict(
                n_windows=len(a), top1_60=float(np.mean([r['top1'] for r in a])),
                top3_60=float(np.mean([r['top3'] for r in a])),
                n_tracks_full=len(b),
                top1_full=float(np.mean([r['top1'] for r in b])) if b else None)

    (OUT_DIR / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))

    print(f"\n{'cell':22s} {'n':>6s} {'disc':>5s} {'short':>6s} {'top1':>16s} {'top3':>16s}")
    for lab in DUR_LABELS:
        for arm in ('matched', 'mismatched'):
            c = out['cells'].get(f'{arm}:{lab}')
            if not c:
                continue
            print(f"{arm + ':' + lab:22s} {c['n_scored']:6d} "
                  f"{c['n_discard_min_voiced'] + c['n_discard_tdms_none']:5d} "
                  f"{c['n_tracks_short']:6d} "
                  f"{c['top1']:5d}/{c['n_scored']:<5d}={c['top1_rate']:6.1%} "
                  f"{c['top3']:5d}/{c['n_scored']:<5d}={c['top3_rate']:6.1%}"
                  f"   [95% CI on top-1, 2000x source-group bootstrap: "
                  f"{c['boot_ci95'][0]:.1%}-{c['boot_ci95'][1]:.1%}]")
    g = out['cells'].get('matched:full')
    if g:
        ok = abs(g['top1_rate'] * 100 - 72.2) <= 0.5 and abs(g['top3_rate'] * 100 - 84.0) <= 0.5
        print(f"\nREPRODUCTION GATE (matched:full vs audit level (c) 72.2% / 84.0%): "
              f"{g['top1_rate']:.1%} / {g['top3_rate']:.1%}  ->  "
              f"{'PASS' if ok else 'FAIL'}")
    print('\npaired differences (same source-group bootstrap, 2000x):')
    for k, v in out['paired'].items():
        print(f"  {k:34s} {100 * v['delta']:+5.1f}pp   "
              f"95% CI {100 * v['ci95'][0]:+5.1f} .. {100 * v['ci95'][1]:+5.1f}pp")

    print('\nfull-duration windows only (`rand`; short tracks excluded):')
    for lab in DUR_LABELS:
        for arm in ('matched', 'mismatched'):
            c = out['cells'].get(f'{arm}:{lab}', {}).get('by_kind', {}).get('rand')
            if c:
                print(f"  {arm + ':' + lab:22s} {c['top1']:5d}/{c['n']:<5d} = "
                      f"{c['top1_rate']:6.1%}  top3 {c['top3_rate']:6.1%}")

    print('\nfrom-the-start windows (registered secondary, non-gating):')
    for lab in DUR_LABELS:
        for arm in ('matched', 'mismatched'):
            s = out['secondary_start'].get(f'{arm}:{lab}')
            if s:
                print(f"  {arm + ':' + lab:22s} {s['top1']:5d}/{s['n']:<5d} = "
                      f"{s['top1_rate']:6.1%}  top3 {s['top3_rate']:6.1%}")

    print('\nper-raga at 60 s matched (registered secondary, non-gating):')
    for r, v in sorted(out['per_raga_60s'].items(), key=lambda kv: -kv[1]['top1_60']):
        print(f"  {r:20s} n={v['n_windows']:4d}  60s {v['top1_60']:6.1%}  "
              f"top3 {v['top3_60']:6.1%}   full-track {v['top1_full']:6.1%}")

    print('\nvoicing density (Trap 2 confound):')
    for lab in DUR_LABELS:
        v = out['voicing'][lab]
        print(f"  {lab:5s} n={v['n']:5d}  density {v['density_mean']:.3f} "
              f"(sd {v['density_sd']:.3f})  voiced frames mean {v['voiced_frames_mean']:.0f} "
              f"min {v['voiced_frames_min']}  effective tau for 0.1s = "
              f"{v['effective_tau_s']['0.1']:.3f}s")
    print(f"\nwrote {OUT_DIR / 'results.json'}")


if __name__ == '__main__':
    main()
