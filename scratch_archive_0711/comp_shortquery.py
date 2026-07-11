"""Product-setting eval: 60s query clip vs full-track reference catalog (LOO).

Query: contiguous voiced slice (~60s audio equivalent) drawn from several
positions in the eval track. Reference: 3 windows (start/mid/end) per track.
Score: min Qmax distance over (query, ref-window) pairs.
"""
import json, time, sys
from pathlib import Path
from collections import Counter
import numpy as np
import essentia.standard as es

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
meta = json.load(open(CACHE / 'meta.json'))
DEC = 80
DT = 0.0029024943310657597
W_REF = 1000
Q_FRAMES = int(60.0 / (DT * DEC))  # ~258 chroma frames = 60 s of voiced melody
POSITIONS = (0.35, 0.6)            # where user might hit record (post-opening)

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

def ref_windows(c):
    n = c.shape[0]
    if n <= W_REF: return [c]
    starts = sorted({0, (n - W_REF) // 2, n - W_REF})
    return [c[s:s + W_REF] for s in starts]

chromas = []
for m in meta:
    d = np.load(CACHE / m['file'])
    chromas.append(chroma_from_pitch(d['f']))
ok = [i for i, c in enumerate(chromas) if c is not None]
meta = [meta[i] for i in ok]; chromas = [chromas[i] for i in ok]
N = len(meta)
works = [m['work_mbid'] for m in meta]
wc = Counter(works)
eval_idx = [i for i in range(N) if wc[works[i]] >= 2 and chromas[i].shape[0] >= Q_FRAMES + 30]
refs = [ref_windows(c) for c in chromas]
print(f'{N} tracks, {len(eval_idx)} short-query evals, q_frames={Q_FRAMES}', flush=True)

ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')

t0 = time.time()
n_eval = t1 = t5 = 0
for k, i in enumerate(eval_idx):
    c = chromas[i]
    for pos in POSITIONS:
        s0 = min(int(c.shape[0] * pos), c.shape[0] - Q_FRAMES)
        q = c[s0:s0 + Q_FRAMES]
        s = np.full(N, np.inf)
        for j in range(N):
            if j == i: continue
            best = np.inf
            for rb in refs[j]:
                try:
                    _, d = csm(ccs(q, rb))
                    if d < best: best = d
                except Exception:
                    pass
            s[j] = best
        order = np.argsort(s)
        ranked = [works[j] for j in order[:5]]
        hit1 = ranked[0] == works[i]; hit5 = works[i] in ranked
        t1 += hit1; t5 += hit5; n_eval += 1
        print(f'[{k+1}/{len(eval_idx)} pos={pos}] {meta[i]["tid"][:30]:30s} {"OK" if hit1 else "--"}/{"OK" if hit5 else "--"} best={meta[order[0]]["title"][:20]} ({time.time()-t0:.0f}s)', flush=True)
print(f'H: 60s-query Qmax: top1={t1}/{n_eval}={t1/n_eval:.1%} top5={t5}/{n_eval}={t5/n_eval:.1%}', flush=True)
