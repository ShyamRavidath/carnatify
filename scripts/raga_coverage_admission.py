"""JOB B — pricing per-class admission, honestly.

`data/RAGA_COVERAGE_CURVE.md` §4 argues that a global `min_tracks` cannot
separate Saurāṣtraṁ (13 tracks, 92.3%) from Nāṭakurinji (11 tracks, 0.0%) and
that the lever is per-class admission. This prices that claim by admitting
classes on **measured per-class accuracy** instead of track count, sweeping a
threshold t over {0, 0.10, 0.20, 0.30, 0.40}.

The trap, named in `data/raga_coverage/PREREGISTRATION_FOLLOWUP.md` §B.2 before
any score: selecting classes on the same folds you then score on is selection on
noise. With 10-30 tracks per class a class's measured top-1 has a standard error
of 9-15 pp, so thresholding on it keeps whichever classes got lucky, and the
gain is real in the table and absent in the field.

So the primary arm is **nested**:

  outer folds = StratifiedGroupKFold(5, shuffle, seed 42) over the full 54-class
      tier with the level-(c) group vector, computed ONCE, identical at every
      threshold, so two thresholds cannot differ by fold churn;
  for each outer fold k, an INNER 5-fold group CV over fold k's TRAINING rows
      only supplies per-class top-1; classes with inner top-1 >= t are admitted;
  the forest is then fit on outer-train restricted to the admitted classes and
      scored on outer-test restricted to the admitted classes.

The selection for fold k never sees fold k. A secondary in-sample arm — admitted
from the committed full-tier per-class numbers, i.e. from the folds it is then
scored on — is reported beside it and labelled as an optimistic bound, because
the gap between the two arms IS the measurement of selection on noise.

Gate B: at t = 0 every class is admitted and both arms must return the committed
649/1139 and 812/1139.

The forest, the splitter, the seed and the features are IMPORTED from
`scripts/raga_audit_levels.py`. Nothing under `models/` is written.

Usage: venv/bin/python scripts/raga_coverage_admission.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import raga_audit_levels as L  # noqa: E402  — N_SPLITS, SEED, the frozen config
import raga_coverage_matrix as M  # noqa: E402
from raga_audit_protocol import fold as rfold  # noqa: E402

ROOT = HERE.parent
DIR = ROOT / 'data' / 'raga_coverage'
COMPS = ROOT / 'data' / 'scraped_compositions.json'
MIN_TRACKS = 10
THRESHOLDS = (0.0, 0.10, 0.20, 0.30, 0.40)


def repertoire():
    items = json.loads(COMPS.read_text())
    c = Counter(rfold(i['raga_canonical']) for i in items if i.get('raga_canonical'))
    return c, sum(c.values())


def fit_predict(Xtr, ytr, Xte):
    """The frozen forest, exactly as `raga_audit_levels.run_cv` fits it."""
    le = LabelEncoder()
    yi = le.fit_transform(ytr)
    clf = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                 random_state=L.SEED, n_jobs=-1)
    clf.fit(Xtr, yi)
    return clf.predict_proba(Xte), le.inverse_transform(clf.classes_)


def score(proba, classes, g_te, y_te):
    """Per-track mean posterior read-out, as the frozen harness does it."""
    agg = defaultdict(list)
    for i, t in enumerate(g_te):
        agg[t].append(proba[i])
    lab = {t: y_te[i] for i, t in enumerate(g_te)}
    c1, c3 = {}, {}
    for t, ps in agg.items():
        mean = np.mean(ps, 0)
        order = np.argsort(-mean)
        c1[t] = bool(classes[order[0]] == lab[t])
        c3[t] = bool(lab[t] in classes[order[:3]])
    return c1, c3, lab


def inner_per_class(X, y, g, gc, keep):
    """Per-class top-1 from a 5-fold group CV over the rows handed in."""
    m = np.isin(y, keep)
    r = L.run_cv(X[m], y[m], g[m], gc[m], keep)
    per = {}
    for cls in keep:
        ts = [t for t, lab in r['label_of'].items() if lab == cls]
        per[cls] = float(np.mean([r['correct1'][t] for t in ts])) if ts else 0.0
    return per


def main() -> None:
    X, y, g, gc, ntr = M.get()
    keep = M.tier(ntr, MIN_TRACKS)
    m = np.isin(y, keep)
    X, y, g, gc = X[m], y[m], g[m], gc[m]
    rep, rep_tot = repertoire()
    print(f'{len(keep)} classes, {len(set(g))} tracks, {len(set(gc))} level-(c) '
          f'groups; repertoire denominator {rep_tot}', flush=True)

    # ---- the outer split, computed ONCE, identical at every threshold -------
    le = LabelEncoder()
    yi = le.fit_transform(y)
    cv = StratifiedGroupKFold(n_splits=L.N_SPLITS, shuffle=True, random_state=L.SEED)
    outer = list(cv.split(X, yi, groups=gc))

    # ---- the in-sample per-class numbers, from the committed full-tier run --
    committed = {r['raga']: r['top1']
                 for r in json.loads((DIR / 'curve.json').read_text())['per_class_min10']}

    out = {'tier': {'min_tracks': MIN_TRACKS, 'classes': keep},
           'thresholds': list(THRESHOLDS), 'repertoire_denominator': rep_tot,
           'arms': {}}
    out_path = DIR / 'admission.json'

    for arm in ('nested', 'in_sample'):
        print(f"\n=== arm: {arm}"
              f"{'  (OPTIMISTIC BOUND — selection sees the evaluation folds)' if arm == 'in_sample' else ''}"
              f" ===", flush=True)
        # per-outer-fold admitted-class source
        sel_source = {}
        for k, (tr, te) in enumerate(outer):
            if arm == 'nested':
                sel_source[k] = inner_per_class(X[tr], y[tr], g[tr], gc[tr], keep)
                print(f'  fold {k}: inner selection CV done', flush=True)
            else:
                sel_source[k] = committed

        res = {}
        print(f"\n{'t':>5} {'admitted':>18} {'coverage':>16} {'top-1':>17} "
              f"{'top-3':>8} {'exp hits/100':>13}")
        for t in THRESHOLDS:
            folds = []
            c1_all, c3_all = {}, {}
            for k, (tr, te) in enumerate(outer):
                adm = sorted(c for c in keep if sel_source[k][c] >= t)
                mtr = np.isin(y[tr], adm)
                mte = np.isin(y[te], adm)
                if mtr.sum() == 0 or mte.sum() == 0:
                    continue
                proba, classes = fit_predict(X[tr][mtr], y[tr][mtr], X[te][mte])
                c1, c3, _ = score(proba, classes, g[te][mte], y[te][mte])
                c1_all.update(c1)
                c3_all.update(c3)
                cov = sum(v for kk, v in rep.items()
                          if kk in {rfold(a) for a in adm}) / rep_tot
                h1 = sum(c1.values())
                folds.append(dict(fold=k, n_admitted=len(adm), admitted=adm,
                                  n_tracks=len(c1), coverage=cov,
                                  top1=h1, top1_rate=h1 / len(c1),
                                  top3=sum(c3.values()),
                                  top3_rate=sum(c3.values()) / len(c1),
                                  expected_hits_per_100=100 * cov * h1 / len(c1)))
            na = [f['n_admitted'] for f in folds]
            covs = [f['coverage'] for f in folds]
            eh = [f['expected_hits_per_100'] for f in folds]
            pooled1 = sum(c1_all.values()) / len(c1_all)
            pooled3 = sum(c3_all.values()) / len(c1_all)
            res[f'{t:.2f}'] = dict(
                threshold=t, folds=folds,
                n_admitted_mean=float(np.mean(na)), n_admitted_min=int(min(na)),
                n_admitted_max=int(max(na)),
                coverage_mean=float(np.mean(covs)),
                n_tracks_pooled=len(c1_all),
                top1_pooled=int(sum(c1_all.values())), top1_rate_pooled=pooled1,
                top3_pooled=int(sum(c3_all.values())), top3_rate_pooled=pooled3,
                expected_hits_per_100=float(np.mean(eh)),
                expected_hits_min=float(min(eh)), expected_hits_max=float(max(eh)))
            print(f"{t:>5.2f} {np.mean(na):>7.1f} [{min(na)}-{max(na)}] "
                  f"{np.mean(covs):>15.1%} {sum(c1_all.values()):>5}/{len(c1_all):<5} "
                  f"{pooled1:>6.1%} {pooled3:>7.1%} {np.mean(eh):>12.1f}", flush=True)
            out['arms'][arm] = res
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    # ------------------------------------------------------------- Gate B
    z = out['arms']['nested']['0.00']
    gate = (z['top1_pooled'] == 649 and z['top3_pooled'] == 812
            and z['n_tracks_pooled'] == 1139)
    out['gate_b'] = dict(passed=bool(gate), expected='649/1139 and 812/1139',
                         got=[z['top1_pooled'], z['top3_pooled'], z['n_tracks_pooled']])
    print(f"\nGATE B (t=0 admits everything, must reproduce 649/1139 and 812/1139): "
          f"{'PASS' if gate else 'FAIL'}  got {z['top1_pooled']}/{z['n_tracks_pooled']} "
          f"and {z['top3_pooled']}/{z['n_tracks_pooled']}", flush=True)

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f'\nwrote {out_path}')


if __name__ == '__main__':
    main()
