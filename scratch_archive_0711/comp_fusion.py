"""Fusion: Qmax (best config) + L2-500pt baseline. Saves Qmax matrix for reuse."""
import json, time
from pathlib import Path
from collections import Counter
import numpy as np
import essentia.standard as es

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
meta = json.load(open(CACHE / 'meta.json'))
DEC = 80

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

def l2_rep(f, tonic):
    f = np.asarray(f, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 50 or tonic <= 0: return None
    c = 1200.0 * np.log2(v / tonic)
    r = np.interp(np.linspace(0, 1, 500), np.linspace(0, 1, c.size), c)
    s = r.std()
    return (r - r.mean()) / s if s > 1e-6 else None

chromas, l2s = [], []
for m in meta:
    d = np.load(CACHE / m['file'])
    chromas.append(chroma_from_pitch(d['f']))
    l2s.append(l2_rep(d['f'], float(d['tonic'])))
ok = [i for i in range(len(meta)) if chromas[i] is not None and l2s[i] is not None]
meta = [meta[i] for i in ok]; chromas = [chromas[i][:1500] for i in ok]; l2s = [l2s[i] for i in ok]
N = len(meta)
works = [m['work_mbid'] for m in meta]
wc = Counter(works)
eval_idx = [i for i in range(N) if wc[works[i]] >= 2]
print(f'{N} tracks, eval {len(eval_idx)}', flush=True)

MAT_PATH = SCRATCH / 'qmax_matrix.npz'
if MAT_PATH.exists():
    Q = np.load(MAT_PATH)['Q']
else:
    ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
    csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')
    Q = np.full((len(eval_idx), N), np.inf)
    t0 = time.time()
    for k, i in enumerate(eval_idx):
        for j in range(N):
            if j == i: continue
            try:
                _, d = csm(ccs(chromas[i], chromas[j]))
                Q[k, j] = d
            except Exception:
                pass
        print(f'qmax row {k+1}/{len(eval_idx)} ({time.time()-t0:.0f}s)', flush=True)
    np.savez_compressed(MAT_PATH, Q=Q, eval_idx=np.array(eval_idx))

L2 = np.zeros((len(eval_idx), N))
A = np.stack(l2s)
for k, i in enumerate(eval_idx):
    L2[k] = np.linalg.norm(A - A[i], axis=1)
    L2[k, i] = np.inf

def evaluate(D, name):
    t1 = t5 = 0
    for k, i in enumerate(eval_idx):
        order = np.argsort(D[k])
        ranked = [works[j] for j in order[:5]]
        t1 += ranked[0] == works[i]
        t5 += works[i] in ranked
    ne = len(eval_idx)
    print(f'{name:28s} top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%}', flush=True)

evaluate(Q, 'Qmax alone')
evaluate(L2, 'L2 alone')
# rank fusion
def ranks(D):
    R = np.empty_like(D)
    for k in range(D.shape[0]):
        R[k, np.argsort(D[k])] = np.arange(D.shape[1])
    return R
RQ, RL = ranks(Q), ranks(L2)
for w in (0.2, 0.3, 0.5):
    evaluate(RQ * (1 - w) + RL * w, f'rank fusion w_L2={w}')
