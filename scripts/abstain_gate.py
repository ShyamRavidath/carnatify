"""Leave-class-bin-out abstain gate for a fitted kernel-ridge raga candidate.

Implements data/overhaul/ABSTAIN_GATE_PREREG.md. Builds a group- and
class-disjoint pool of scored windows (known and simulated-OOV) on the fixed
training folds, selects a signal and threshold on that pool only, and applies
it exactly once to the cached 184 Saraga development queries.

Usage:
  venv_train/bin/python scripts/abstain_gate.py \
      --run data/overhaul/context180_recovered_experiment/training \
      --out data/overhaul/context180_recovered_experiment/abstain_gate.json
"""
from __future__ import annotations
import argparse, json, sys, time
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import joblib
from scipy.special import softmax
from threadpoolctl import threadpool_limits
from carnatify.ml.distribution_classifier import DistributionKernelRidge
from carnatify.ml.melody_features import feature_vector
from carnatify.audio.pitch_profiles import cache_suffix
from normalize_ragas import fold
from scripts.raga_pipeline import load_features, sha, write_json
from scripts.summarize_overhaul import paired_interval

N_BINS = 5
SEED, N_BOOT = 42, 5000
BAR = dict(precision=.85, oov_false_accept=.15, min_dev_accepted=20)
SIGNALS = ('max_score', 'margin', 'softmax_max')


def class_bins(y):
    support = Counter(y)
    ordered = sorted(support, key=lambda c: (-support[c], c))
    return {c: i % N_BINS for i, c in enumerate(ordered)}


def fit_ridge(X, y, track):
    count = Counter(track)
    w = np.array([1 / count[t] for t in track]); w /= w.mean()
    model = DistributionKernelRidge(alpha=.1, gamma=2, mode='tdms')
    with threadpool_limits(limits=4):
        model.fit(X, y, sample_weight=w)
    return model


def signals_from(d, temperature):
    d = np.asarray(d, dtype=float)
    top = np.sort(d, axis=1)[:, ::-1]
    return dict(max_score=top[:, 0], margin=top[:, 0] - top[:, 1],
                softmax_max=softmax(d / temperature, axis=1).max(1))


def sweep(score, correct_known, is_oov, bar):
    """Largest-coverage threshold meeting the bar; None if infeasible."""
    order = np.argsort(-score)
    s = score[order]; ck = correct_known[order].astype(float); ov = is_oov[order].astype(float)
    n = len(s); n_oov = max(ov.sum(), 1)
    cum_ck = np.cumsum(ck); cum_ov = np.cumsum(ov); k = np.arange(1, n + 1)
    # Only thresholds at the last index of each distinct score value are valid.
    last = np.r_[s[1:] != s[:-1], True]
    precision = cum_ck / k; oov_fa = cum_ov / n_oov; coverage = k / n
    ok = last & (precision >= bar['precision']) & (oov_fa <= bar['oov_false_accept'])
    if not ok.any():
        return None
    i = np.flatnonzero(ok)[-1]  # largest k => largest coverage
    return dict(threshold=float(s[i]), coverage=float(coverage[i]), precision=float(precision[i]),
                oov_false_accept=float(oov_fa[i]), accepted=int(k[i]))


def apply(score, threshold, correct_known, is_oov):
    acc = score >= threshold
    n_acc = int(acc.sum())
    return dict(accepted=n_acc, coverage=float(acc.mean()),
                precision=float(correct_known[acc].mean()) if n_acc else None,
                oov_false_accept=float(acc[is_oov].mean()) if is_oov.any() else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--corpus', type=Path, default=ROOT / 'data/overhaul/annotated_corpus_v2.json')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    started = time.monotonic()
    bundle = joblib.load(a.run / 'raga.joblib')
    z = load_features(a.run)
    folds_doc = json.loads((a.run / 'folds.json').read_text())
    # Gate 1: identity between features, bundle and folds.
    if bundle['feature_sha256'] != sha(a.run / 'features.npz'): raise SystemExit('Gate 1 FAIL: feature hash')
    if folds_doc['feature_sha256'] != bundle['feature_sha256']: raise SystemExit('Gate 1 FAIL: folds hash')
    if bundle.get('representation') != 'voiced': raise SystemExit('Gate 1 FAIL: bundle representation is not voiced')
    T = float(bundle['calibration']['temperature'])
    X, y, track, group = z['legacy'], z['y'], z['track'], z['group']
    fold_of = np.array([folds_doc['folds'][str(t)] for t in track])
    bins = class_bins(y)
    bin_of = np.array([bins[c] for c in y])
    inputs = dict(model_sha256=sha(a.run / 'raga.joblib'), features=bundle['feature_sha256'],
                  manifest=sha(a.run / 'manifest.json'), folds=sha(a.run / 'folds.json'),
                  corpus=sha(a.corpus), script=sha(Path(__file__)),
                  prereg=sha(ROOT / 'data/overhaul/ABSTAIN_GATE_PREREG.md'), temperature=T)

    # Pool: 25 leave-class-bin-out fits on the fixed folds.
    pool = {s: [] for s in SIGNALS}
    pool_meta = dict(correct_known=[], is_oov=[], group=[], fold=[], bin=[], track=[])
    fits = []
    for f in sorted(set(fold_of)):
        for b in range(N_BINS):
            tr = (fold_of != f) & (bin_of != b); te = fold_of == f
            model = fit_ridge(X[tr], y[tr], track[tr])
            d = model.decision_function(X[te])
            pred = model.classes_[d.argmax(1)]
            oov = bin_of[te] == b
            sig = signals_from(d, T)
            for s in SIGNALS: pool[s].append(sig[s])
            pool_meta['correct_known'].append((pred == y[te]) & ~oov)
            pool_meta['is_oov'].append(oov); pool_meta['group'].append(group[te])
            pool_meta['fold'].append(np.full(te.sum(), f)); pool_meta['bin'].append(np.full(te.sum(), b))
            pool_meta['track'].append(track[te])
            fits.append(dict(fold=int(f), bin=b, n_train=int(tr.sum()), n_test=int(te.sum()),
                             n_classes=len(model.classes_), n_oov=int(oov.sum())))
            print(f'fold {f} bin {b}: train {tr.sum()} windows / {len(model.classes_)} classes; '
                  f'test {te.sum()} ({oov.sum()} oov); {time.monotonic()-started:.1f}s', flush=True)
    pool = {s: np.concatenate(v) for s, v in pool.items()}
    meta = {k: np.concatenate(v) for k, v in pool_meta.items()}
    ck, ov = meta['correct_known'], meta['is_oov']

    # Selection on the pool only.
    selection = {}
    for s in SIGNALS:
        pt = sweep(pool[s], ck, ov, BAR)
        # Cross-fit over pool folds to measure selection optimism.
        cf = dict(accepted=0, correct_known=0, oov=0, oov_accepted=0, n=0)
        for f in sorted(set(meta['fold'])):
            tr = meta['fold'] != f; te = ~tr
            ptf = sweep(pool[s][tr], ck[tr], ov[tr], BAR)
            thr = ptf['threshold'] if ptf else np.inf
            acc = pool[s][te] >= thr
            cf['accepted'] += int(acc.sum()); cf['correct_known'] += int((acc & ck[te]).sum())
            cf['oov'] += int(ov[te].sum()); cf['oov_accepted'] += int((acc & ov[te]).sum()); cf['n'] += int(te.sum())
        cross = dict(coverage=cf['accepted'] / cf['n'],
                     precision=cf['correct_known'] / cf['accepted'] if cf['accepted'] else None,
                     oov_false_accept=cf['oov_accepted'] / cf['oov'])
        selection[s] = dict(in_pool=pt, cross_fit=cross)
    feasible = {s: v['in_pool'] for s, v in selection.items() if v['in_pool']}
    if feasible:
        chosen = max(feasible, key=lambda s: (feasible[s]['coverage'], s == 'max_score'))
        threshold = feasible[chosen]['threshold']
    else:
        chosen, threshold = None, None

    # Dev queries: reproduce the reference model's answers from the cache (Gate 2).
    verdict = json.loads((a.run.parent / 'verdict.json').read_text())
    mixed = set(verdict['analyses']['B1m_dev_est_top1_mixed_only']['tracks'])
    ev = json.loads((a.run / 'evaluation180.json').read_text())
    ev_key = [k for k in ev['summary'] if k.endswith('_estimated')][0]
    corpus = {r['track']: r for r in json.loads(a.corpus.read_text())['rows']}
    clf = bundle['model']
    class_keys = [fold(c) for c in clf.classes_]
    dev = []
    cache = ROOT / 'data/overhaul/cache/saraga_audio'
    for r in ev['rows']:
        m = r['metadata']; p_ref = r['predictions'][ev_key]
        path = cache / f"{m['audio_sha256'][:32]}_{cache_suffix('default', 180)}.npz"
        with np.load(path) as q:
            f0 = q['f0']; qm = json.loads(str(q['meta']))
        if qm['audio_sha256'] != m['audio_sha256']: raise SystemExit(f'Gate 2 FAIL: cache identity {r["track"]}')
        tonic = qm['tonic_estimated']; voiced = float(np.sum(f0 > 0) * 128 / 44100)
        truth = fold(r['raga']); known = truth in class_keys
        row = dict(track=r['track'], raga=r['raga'], known=known, mixed=r['track'] in mixed,
                   cluster='|'.join(sorted(fold(x) for x in corpus[r['track']]['artists'])) or corpus[r['track']]['group'],
                   answered=False, correct=False)
        if tonic and np.isfinite(tonic) and tonic > 0 and voiced >= 10:
            v = feature_vector(f0, tonic, 128 / 44100, 'voiced')
            if v is not None:
                d = clf.decision_function(v[None])
                top = str(clf.classes_[d.argmax(1)[0]])
                sig = signals_from(d, T)
                row.update(answered=True, top1=top, correct=fold(top) == truth,
                           **{s: float(sig[s][0]) for s in SIGNALS})
        if row['answered'] != p_ref['answered'] or (row['answered'] and row['top1'] != p_ref['top3'][0]):
            raise SystemExit(f'Gate 2 FAIL: {r["track"]} answer differs from evaluation180.json')
        dev.append(row)
    n_known_correct = sum(r['correct'] for r in dev if r['known'])
    if n_known_correct != verdict['gate2']['dev_known_candidate']:
        raise SystemExit(f'Gate 2 FAIL: {n_known_correct} known correct, expected {verdict["gate2"]["dev_known_candidate"]}')

    def dev_eval(rows, signal, thr):
        sc = np.array([r.get(signal, -np.inf) for r in rows])
        ckd = np.array([r['correct'] and r['known'] for r in rows])
        ovd = np.array([not r['known'] for r in rows])
        acc = sc >= thr
        out = apply(sc, thr, ckd, ovd)
        out.update(n=len(rows), n_known=int((~ovd).sum()), n_oov=int(ovd.sum()),
                   correct_accepted=int((acc & ckd).sum()), oov_accepted=int((acc & ovd).sum()))
        if acc.any():
            groups = np.array([r['cluster'] for r in rows])
            keys = np.unique(groups)
            hits = np.array([(acc & ckd)[groups == g].sum() for g in keys])
            counts = np.array([acc[groups == g].sum() for g in keys])
            idx = np.random.default_rng(SEED).integers(0, len(keys), size=(N_BOOT, len(keys)))
            den = counts[idx].sum(1); num = hits[idx].sum(1); valid = den > 0
            out['precision_cluster_ci95'] = np.percentile(num[valid] / den[valid], [2.5, 97.5]).tolist()
            out['n_clusters'] = int(len(keys))
        return out

    dev_result = None
    if chosen:
        dev_result = dict(all_184=dev_eval(dev, chosen, threshold),
                         single_raga_176=dev_eval([r for r in dev if not r['mixed']], chosen, threshold))
        d = dev_result['all_184']
        bar_pass = bool(d['accepted'] >= BAR['min_dev_accepted'] and d['precision'] is not None
                        and d['precision'] >= BAR['precision'] and d['oov_false_accept'] <= BAR['oov_false_accept'])
    else:
        bar_pass = False
    # Current bundle gate on the same dev rows, for reference.
    current = dev_eval(dev, 'softmax_max', float(bundle['calibration']['gate']['threshold']))
    # Full dev trade-off curve for the chosen signal (published, not used for selection).
    curve = None
    if chosen:
        sc = np.array([r.get(chosen, -np.inf) for r in dev])
        ckd = np.array([r['correct'] and r['known'] for r in dev]); ovd = np.array([not r['known'] for r in dev])
        curve = []
        for thr in np.quantile(sc[np.isfinite(sc)], np.linspace(0, .95, 20)):
            curve.append(dict(threshold=float(thr), **apply(sc, float(thr), ckd, ovd)))

    pool_summary = dict(n_windows=int(len(ck)), n_known=int((~ov).sum()), n_oov=int(ov.sum()),
                        known_top1=float(ck[~ov].mean()), n_fits=len(fits), fits=fits,
                        bins={str(b): sorted(c for c in bins if bins[c] == b) for b in range(N_BINS)})
    predictions = dict(
        P1_raw_signal_beats_softmax=bool(feasible and chosen != 'softmax_max' and
            (not selection['softmax_max']['in_pool'] or
             feasible[chosen]['coverage'] > selection['softmax_max']['in_pool']['coverage'])),
        P2_pool_feasible_with_coverage_ge_040=bool(feasible and feasible[chosen]['coverage'] >= .4),
        P3_dev_precision_ok_but_oov_fa_in_015_030=bool(dev_result and dev_result['all_184']['precision'] >= .85
            and .15 < dev_result['all_184']['oov_false_accept'] <= .30),
        P4_selection_optimism_under_3pp=bool(chosen and selection[chosen]['cross_fit']['precision'] is not None
            and feasible[chosen]['precision'] - selection[chosen]['cross_fit']['precision'] < .03))
    report = dict(status='gate selected on a group- and class-disjoint training pool; dev applied once; not production proof',
                  prereg='data/overhaul/ABSTAIN_GATE_PREREG.md', inputs=inputs, bar=BAR,
                  gate1='pass', gate2=dict(status='pass', dev_known_correct=n_known_correct),
                  pool=pool_summary, selection=selection,
                  chosen=dict(signal=chosen, threshold=threshold),
                  dev=dev_result, dev_bar_pass=bar_pass, current_bundle_gate_on_dev=current,
                  dev_curve=curve, predictions=predictions,
                  dev_rows=[{k: v for k, v in r.items()} for r in dev],
                  elapsed_s=time.monotonic() - started, seed=SEED, bootstrap=N_BOOT)
    write_json(a.out, report)
    print(json.dumps(dict(pool={k: v for k, v in pool_summary.items() if k not in ('fits', 'bins')},
                          selection=selection, chosen=report['chosen'], dev=dev_result,
                          dev_bar_pass=bar_pass, current=current, predictions=predictions), indent=1))


if __name__ == '__main__':
    main()
