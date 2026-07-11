"""LOO composition-matching experiments on saraga multi-rendition works."""
import json, sys, time
from pathlib import Path
from collections import Counter
import numpy as np

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
meta = json.load(open(CACHE / 'meta.json'))
N = len(meta)

def voiced_cents(f, tonic):
    f = np.asarray(f, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 50: return None
    return 1200.0 * np.log2(v / tonic)

# load all
cents = []
for m in meta:
    d = np.load(CACHE / m['file'])
    cents.append(voiced_cents(d['f'], float(d['tonic'])))
ok = [i for i, c in enumerate(cents) if c is not None]
meta = [meta[i] for i in ok]; cents = [cents[i] for i in ok]
N = len(meta)
works = [m['work_mbid'] for m in meta]
wc = Counter(works)
eval_idx = [i for i in range(N) if wc[works[i]] >= 2]
print(f'{N} tracks, eval on {len(eval_idx)} tracks / {len({works[i] for i in eval_idx})} works', flush=True)

def resample(c, n):
    return np.interp(np.linspace(0, 1, n), np.linspace(0, 1, c.size), c)

def zscore(x):
    s = x.std()
    return (x - x.mean()) / s if s > 1e-6 else x

def run_eval(dist_fn, reps, name):
    t1 = t5 = 0
    t0 = time.time()
    for i in eval_idx:
        ds = np.array([dist_fn(reps[i], reps[j]) if j != i else np.inf for j in range(N)])
        order = np.argsort(ds)
        ranked = [works[j] for j in order[:5]]
        t1 += ranked[0] == works[i]
        t5 += works[i] in ranked
    print(f'{name:38s} top1={t1}/{len(eval_idx)}={t1/len(eval_idx):.1%} top5={t5/len(eval_idx)}={t5/len(eval_idx):.1%}  ({time.time()-t0:.0f}s)', flush=True)

# A. baseline: 500pt z-scored L2
repA = [zscore(resample(c, 500)).astype(np.float64) for c in cents]
run_eval(lambda a, b: np.linalg.norm(a - b), repA, 'A: L2 500pt zscore (shipped)')

# A2: raw cents (no zscore), 500pt
repA2 = [resample(c, 500) for c in cents]
run_eval(lambda a, b: np.linalg.norm(a - b), repA2, 'A2: L2 500pt raw cents')

# B. DTW on downsampled cents (numba banded DTW)
from numba import njit

@njit(cache=True)
def dtw_band(a, b, w):
    n, m = a.shape[0], b.shape[0]
    INF = 1e18
    prev = np.full(m + 1, INF)
    cur = np.full(m + 1, INF)
    prev[0] = 0.0
    for i in range(1, n + 1):
        cur[:] = INF
        j0 = max(1, i - w); j1 = min(m, i + w)
        for j in range(j0, j1 + 1):
            d = a[i - 1] - b[j - 1]
            d = d * d
            best = prev[j]
            if prev[j - 1] < best: best = prev[j - 1]
            if cur[j - 1] < best: best = cur[j - 1]
            cur[j] = d + best
        prev, cur = cur, prev
    return np.sqrt(prev[m])

dtw_band(np.zeros(10), np.zeros(10), 5)  # compile

for n, win in ((500, 50), (1000, 100), (1000, 250)):
    rep = [np.ascontiguousarray(resample(c, n)) for c in cents]
    run_eval(lambda a, b, w=win: dtw_band(a, b, w) / len(a), rep, f'B: DTW {n}pt win={win} raw cents')

# B2: DTW z-scored
rep = [np.ascontiguousarray(zscore(resample(c, 1000))) for c in cents]
run_eval(lambda a, b: dtw_band(a, b, 100) / len(a), rep, 'B2: DTW 1000pt win=100 zscore')
