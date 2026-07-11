"""Windowed Qmax: 3 windows per track (start/mid/end), min distance over window pairs."""
import json, time
from pathlib import Path
from collections import Counter
import numpy as np
import essentia.standard as es

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
meta = json.load(open(CACHE / 'meta.json'))
DEC = 80
W = 1000  # ~4 min voiced melody per window

def chroma_from_pitch(f):
    f = np.asarray(f, dtype=np.float64)
    n = f.size // DEC
    if n < 30: return None
    fr = f[:n * DEC].reshape(n, DEC)
    out = np.zeros((n, 12), dtype=np.float32)
    valid = np.zeros(n, dtype=bool)
    for i in range(n):
        v = fr[i]; v = v[(v > 0) & np.isfinite(v)]
        if v.size < DEC // 4: continue
        pc = np.mod(12.0 * np.log2(np.median(v) / 440.0), 12.0)
        b = int(round(pc)) % 12
        out[i, b] = 1.0
        out[i, (b + 1) % 12] = 0.3; out[i, (b - 1) % 12] = 0.3
        valid[i] = True
    out = out[valid]
    return out if out.shape[0] >= 30 else None

def windows(c):
    n = c.shape[0]
    if n <= W: return [c]
    starts = sorted({0, (n - W) // 2, n - W})
    return [c[s:s + W] for s in starts]

chromas = []
for m in meta:
    d = np.load(CACHE / m['file'])
    chromas.append(chroma_from_pitch(d['f']))
ok = [i for i, c in enumerate(chromas) if c is not None]
meta = [meta[i] for i in ok]; chromas = [chromas[i] for i in ok]
N = len(meta)
works = [m['work_mbid'] for m in meta]
wc = Counter(works)
eval_idx = [i for i in range(N) if wc[works[i]] >= 2]
wins = [windows(c) for c in chromas]
print(f'{N} tracks, eval {len(eval_idx)}, windows/track median {np.median([len(w) for w in wins]):.0f}', flush=True)

ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')

t1 = t5 = 0
t0 = time.time()
for k, i in enumerate(eval_idx):
    s = np.full(N, np.inf)
    for j in range(N):
        if j == i: continue
        best = np.inf
        for qa in wins[i]:
            for rb in wins[j]:
                try:
                    _, d = csm(ccs(qa, rb))
                    if d < best: best = d
                except Exception:
                    pass
        s[j] = best
    order = np.argsort(s)
    ranked = [works[j] for j in order[:5]]
    hit1 = ranked[0] == works[i]; hit5 = works[i] in ranked
    t1 += hit1; t5 += hit5
    print(f'[{k+1}/{len(eval_idx)}] {meta[i]["tid"][:34]:34s} {"OK" if hit1 else "--"}/{"OK" if hit5 else "--"} best={meta[order[0]]["title"][:22]} ({time.time()-t0:.0f}s)', flush=True)
ne = len(eval_idx)
print(f'G: windowed Qmax W={W}: top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%}', flush=True)
