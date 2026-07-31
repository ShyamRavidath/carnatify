"""Score the rebuilt raga CV harness at four levels of disjointness.

One feature matrix, built once by `raga_audit_protocol.py`. The levels differ
ONLY in the `groups` vector handed to `StratifiedGroupKFold`. The tier
(`min_tracks >= 25` on level-(a) track counts), the fusion weight
(`P = 0.6*P_tdms + 0.4*P_hist`), the forest
(`RandomForestClassifier(n_estimators=800, max_features='sqrt',
random_state=42)`) and the split seed (`n_splits=5, shuffle=True,
random_state=42`) are frozen across all four.

Two read-outs are computed for every level, both declared in
`data/raga_audit/PREREGISTRATION.md` before the first fold was scored, because
the original harness was never committed and both are natural readings of it:

  row-level   — one prediction per augmented row (3 per track: orig, pitch_shift,
                noise), which is the unit `train_raga_v3_tdms.py` fits on
  track-level — the 3 rows' fused posteriors averaged, one prediction per track

Level (a) is the reproduction gate: it must land within +/-2pp of 72.8 top-1 and
84.7 top-3 on 18 ragas under one of the two read-outs, or the audit stops.

Read-only: fits happen in memory only; nothing under `models/` is written.
Writes `data/raga_audit/results.json`.

Usage: venv/bin/python scripts/raga_audit_score.py
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold

import raga_audit_protocol as P  # noqa: E402
from train_raga_v3_tdms import FUSION_W_HIST  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'data' / 'raga_audit'
N_SPLITS = 5
SEED = 42


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fused_posteriors(Xt, Xh, yi, groups, n_classes):
    """5-fold grouped CV; return the fused posterior for every row, out-of-fold."""
    skf = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    Pf = np.zeros((len(yi), n_classes))
    fold_of = np.full(len(yi), -1)
    for k, (tr, te) in enumerate(skf.split(Xt, yi, groups)):
        rf_t = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                      random_state=SEED, n_jobs=-1).fit(Xt[tr], yi[tr])
        rf_h = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                      random_state=SEED, n_jobs=-1).fit(Xh[tr], yi[tr])
        pt = np.zeros((len(te), n_classes))
        ph = np.zeros((len(te), n_classes))
        pt[:, rf_t.classes_] = rf_t.predict_proba(Xt[te])
        ph[:, rf_h.classes_] = rf_h.predict_proba(Xh[te])
        Pf[te] = (1 - FUSION_W_HIST) * pt + FUSION_W_HIST * ph
        fold_of[te] = k
    return Pf, fold_of


def readout(Pm, ytrue, n_classes):
    order = np.argsort(-Pm, axis=1)
    top1 = int((order[:, 0] == ytrue).sum())
    top3 = int(sum(ytrue[i] in order[i, :3] for i in range(len(ytrue))))
    n = len(ytrue)
    return dict(n=n, top1=top1, top3=top3,
                top1_rate=top1 / n if n else 0.0, top3_rate=top3 / n if n else 0.0,
                top1_ci95=[round(x, 4) for x in wilson(top1, n)])


def score_level(M, groups, survivors, classes):
    m = np.isin(M['y'], survivors)
    Xt, Xh = M['Xt'][m], M['Xh'][m]
    y, tid = M['y'][m], M['tid'][m]
    g = groups[m]
    cls_index = {c: i for i, c in enumerate(classes)}
    yi = np.array([cls_index[c] for c in y])

    t0 = time.time()
    Pf, fold_of = fused_posteriors(Xt, Xh, yi, g, len(classes))
    secs = time.time() - t0

    row = readout(Pf, yi, len(classes))

    # track-level: average the 3 augmented rows' fused posteriors
    uniq = sorted(set(tid))
    Pt = np.array([Pf[tid == t].mean(axis=0) for t in uniq])
    yt = np.array([yi[tid == t][0] for t in uniq])
    trk = readout(Pt, yt, len(classes))

    order_t = np.argsort(-Pt, axis=1)
    per_raga = {}
    for ci, c in enumerate(classes):
        sel = yt == ci
        if sel.sum():
            per_raga[c] = dict(
                n_tracks=int(sel.sum()),
                top1=float((order_t[sel, 0] == ci).mean()),
                top3=float(np.mean([ci in order_t[i, :3] for i in np.where(sel)[0]])),
            )

    cnt = Counter(y)
    tot = sum(cnt.values())
    prior = np.array([c / tot for c in cnt.values()])
    return dict(
        n_ragas=len(classes), n_tracks=len(uniq), n_groups=int(len(set(g))),
        n_rows=int(m.sum()), n_folds=int(len(set(fold_of[fold_of >= 0]))),
        folds_used=sorted(int(x) for x in set(fold_of[fold_of >= 0])),
        majority_class_rate=float(prior.max()),
        class_prior_expectation=float((prior ** 2).sum()),
        row_level=row, track_level=trk, per_raga=per_raga,
        fit_seconds=round(secs, 1),
    )


def main() -> None:
    M = P.build_matrix()
    groups, notes = P.build_groups(M)
    keep, ntr = P.frozen_tier(M['y'], M['tid'])
    print(f'frozen tier: {len(keep)} ragas at min_tracks >= {P.MIN_TRACKS} '
          f'(level-(a) track counts), {len(set(M["tid"][np.isin(M["y"], keep)]))} tracks')

    out = {'tier': {'min_tracks': P.MIN_TRACKS, 'ragas': keep,
                    'track_counts': {r: ntr[r] for r in keep}},
           'notes': notes, 'fusion_w_hist': FUSION_W_HIST, 'levels': {}}

    for lv in P.LEVELS:
        st = P.level_stats(M['y'], groups[lv], keep)
        survivors = st['survivors']
        res = score_level(M, groups[lv], survivors, survivors)
        res['ragas_dropped'] = st['ragas_dropped']
        out['levels'][lv] = res
        r, t = res['row_level'], res['track_level']
        print(f"\n({lv}) {P.LEVEL_NAMES[lv]}")
        print(f"     n: tracks {res['n_tracks']}  groups {res['n_groups']}  "
              f"rows {res['n_rows']}  ragas {res['n_ragas']}  folds {res['n_folds']}")
        print(f"     floors: majority {res['majority_class_rate']:.4f}  "
              f"class-prior {res['class_prior_expectation']:.4f}")
        print(f"     row-level  : top-1 {r['top1']}/{r['n']} = {r['top1_rate']:.3%}   "
              f"top-3 {r['top3']}/{r['n']} = {r['top3_rate']:.3%}")
        print(f"     track-level: top-1 {t['top1']}/{t['n']} = {t['top1_rate']:.3%}   "
              f"top-3 {t['top3']}/{t['n']} = {t['top3_rate']:.3%}  "
              f"CI95 {t['top1_ci95']}")
        if res['ragas_dropped']:
            print(f"     dropped (<{N_SPLITS} groups): {res['ragas_dropped']}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nwrote {OUT_DIR / 'results.json'}")


if __name__ == '__main__':
    main()
