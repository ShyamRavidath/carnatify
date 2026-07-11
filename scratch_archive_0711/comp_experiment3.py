"""Round 3: Smith-Waterman local alignment on note strings."""
import json, time
from pathlib import Path
from collections import Counter
import numpy as np
from numba import njit

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
meta = json.load(open(CACHE / 'meta.json'))

def voiced_cents(f, tonic):
    f = np.asarray(f, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 50: return None
    return 1200.0 * np.log2(v / tonic)

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
print(f'{N} tracks, eval {len(eval_idx)} tracks / {len({works[i] for i in eval_idx})} works', flush=True)

from scipy.ndimage import median_filter

def smooth_median(c, win):
    if win <= 1: return c
    return median_filter(c, size=win, mode='nearest')

def note_string(c, smooth=103, quant=100.0, min_run=3):
    """~344Hz cents -> median smooth (~0.3s) -> quantize -> collapse runs, drop blips."""
    s = smooth_median(c, smooth)
    q = np.round(s / quant).astype(np.int64)
    # run-length encode, keep runs >= min_run frames
    notes = []
    start = 0
    for i in range(1, q.size + 1):
        if i == q.size or q[i] != q[start]:
            if i - start >= min_run:
                if not notes or notes[-1] != q[start]:
                    notes.append(q[start])
            start = i
    return np.array(notes, dtype=np.int64)

@njit(cache=True)
def sw_score(a, b, fold):
    """Smith-Waterman: match +2 (within tolerance), mismatch -1, gap -1. Returns max local score."""
    n, m = a.shape[0], b.shape[0]
    prev = np.zeros(m + 1)
    cur = np.zeros(m + 1)
    best = 0.0
    for i in range(1, n + 1):
        cur[0] = 0.0
        for j in range(1, m + 1):
            d = a[i - 1] - b[j - 1]
            if fold > 0:
                d = d % fold
                if d > fold // 2: d = fold - d
            if d < 0: d = -d
            s = 2.0 if d == 0 else (0.5 if d == 1 else -1.0)
            v = prev[j - 1] + s
            if prev[j] - 1.0 > v: v = prev[j] - 1.0
            if cur[j - 1] - 1.0 > v: v = cur[j - 1] - 1.0
            if v < 0.0: v = 0.0
            cur[j] = v
            if v > best: best = v
        prev, cur = cur, prev
    return best

sw_score(np.zeros(4, np.int64), np.zeros(4, np.int64), 0)

def run_eval(score_fn, name, higher_better=True):
    t1 = t5 = 0
    t0 = time.time()
    for i in eval_idx:
        s = np.array([score_fn(i, j) if j != i else -np.inf for j in range(N)])
        order = np.argsort(-s)
        ranked = [works[j] for j in order[:5]]
        t1 += ranked[0] == works[i]
        t5 += works[i] in ranked
    ne = len(eval_idx)
    print(f'{name:52s} top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%}  ({time.time()-t0:.0f}s)', flush=True)

for smooth, quant, min_run in ((103, 100.0, 3), (35, 100.0, 5), (103, 50.0, 3)):
    notes = [note_string(c, smooth, quant, min_run) for c in cents]
    lens = np.array([n.size for n in notes])
    print(f'note lens smooth={smooth} quant={quant}: median {np.median(lens):.0f} max {lens.max()}', flush=True)
    if np.median(lens) > 4000:
        print('too long, skip'); continue
    for fold_flag, fname in ((0, 'abs'), (12 if quant == 100.0 else 24, 'octfold')):
        def sc(i, j, ns=notes, ff=fold_flag):
            if ns[i].size == 0 or ns[j].size == 0: return 0.0
            return sw_score(ns[i], ns[j], ff) / min(ns[i].size, ns[j].size)
        run_eval(sc, f'E: SW sm={smooth} q={int(quant)} mr={min_run} {fname}')
