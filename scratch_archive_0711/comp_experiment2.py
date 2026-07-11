"""Round 2: melodic n-gram shingles + multi-snippet subsequence DTW."""
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

def median_decimate(c, factor):
    n = c.size // factor
    return np.median(c[:n * factor].reshape(n, factor), axis=1)

def note_string(c, factor=34, quant=100.0):
    """Decimate (~10Hz), quantize to semitones, collapse runs."""
    d = median_decimate(c, factor)
    q = np.round(d / quant).astype(np.int64)
    keep = np.ones(q.size, dtype=bool)
    keep[1:] = q[1:] != q[:-1]
    return q[keep]

def kgrams(notes, k):
    if notes.size < k: return set()
    base = np.int64(97)
    out = set()
    for i in range(notes.size - k + 1):
        h = np.int64(0)
        for j in range(k):
            h = h * base + notes[i + j]
        out.add(int(h))
    return out

def run_eval(score_fn, name, higher_better=True):
    t1 = t5 = 0
    t0 = time.time()
    for i in eval_idx:
        s = np.array([score_fn(i, j) if j != i else (-np.inf if higher_better else np.inf) for j in range(N)])
        order = np.argsort(-s) if higher_better else np.argsort(s)
        ranked = [works[j] for j in order[:5]]
        t1 += ranked[0] == works[i]
        t5 += works[i] in ranked
    ne = len(eval_idx)
    print(f'{name:44s} top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%}  ({time.time()-t0:.0f}s)', flush=True)

# C: k-gram containment
for k in (3, 4, 5):
    for quant in (100.0, 200.0):
        grams = [kgrams(note_string(c, quant=quant), k) for c in cents]
        def sc(i, j, g=grams):
            if not g[i] or not g[j]: return 0.0
            return len(g[i] & g[j]) / len(g[i])
        run_eval(sc, f'C: {k}-gram containment quant={int(quant)}c')

# D: multi-snippet subsequence DTW
@njit(cache=True)
def subseq_dtw(q, r):
    n, m = q.shape[0], r.shape[0]
    INF = 1e18
    prev = np.zeros(m + 1)          # free start on reference
    cur = np.empty(m + 1)
    for i in range(1, n + 1):
        cur[0] = INF
        for j in range(1, m + 1):
            d = q[i - 1] - r[j - 1]
            d = d * d
            best = prev[j]
            if prev[j - 1] < best: best = prev[j - 1]
            if cur[j - 1] < best: best = cur[j - 1]
            cur[j] = d + best
        prev, cur = cur, prev
    return np.sqrt(prev[1:].min()) / n   # free end

subseq_dtw(np.zeros(5), np.zeros(20))

FACTOR = 40  # ~8.6 Hz
refs_ds = [median_decimate(c, FACTOR) for c in cents]
SNIP = 250   # ~29 s of voiced melody
def snippets(c, n_snip=5):
    d = median_decimate(c, FACTOR)
    if d.size <= SNIP: return [d]
    starts = np.linspace(0, d.size - SNIP, n_snip).astype(int)
    return [d[s:s + SNIP] for s in starts]

snips = [snippets(c) for c in cents]
def sc_dtw(i, j):
    r = refs_ds[j]
    return min(subseq_dtw(q, r) for q in snips[i])
run_eval(sc_dtw, 'D: 5x29s snippet subseq-DTW raw cents', higher_better=False)
