"""Ensemble: windowed Qmax distances from pyin-vocal AND melodia-mix chroma."""
import json, time
from pathlib import Path
from collections import Counter
import numpy as np
import essentia.standard as es

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
MEL_CACHE = SCRATCH / 'melodia_cache'
meta = json.load(open(CACHE / 'meta.json'))
DEC = 80
W_REF = 1000

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
    if n <= W_REF: return [c]
    starts = sorted({0, (n - W_REF) // 2, n - W_REF})
    return [c[s:s + W_REF] for s in starts]

pyin_c, mel_c = [], []
for m in meta:
    d = np.load(CACHE / m['file'])
    pyin_c.append(chroma_from_pitch(d['f']))
    mp = MEL_CACHE / f"{m['tid'].replace('/','_')}.npy"
    mel_c.append(chroma_from_pitch(np.load(mp)) if mp.exists() else None)
ok = [i for i in range(len(meta)) if pyin_c[i] is not None and mel_c[i] is not None]
meta = [meta[i] for i in ok]; pyin_c = [pyin_c[i] for i in ok]; mel_c = [mel_c[i] for i in ok]
N = len(meta)
works = [m['work_mbid'] for m in meta]
wc = Counter(works)
eval_idx = [i for i in range(N) if wc[works[i]] >= 2]
wp = [windows(c) for c in pyin_c]; wm = [windows(c) for c in mel_c]
print(f'{N} tracks, eval {len(eval_idx)}', flush=True)

ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')

def qmat(wins, path):
    p = SCRATCH / path
    if p.exists(): return np.load(p)['Q']
    Q = np.full((len(eval_idx), N), np.inf)
    t0 = time.time()
    for k, i in enumerate(eval_idx):
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
            Q[k, j] = best
        print(f'{path} row {k+1}/{len(eval_idx)} ({time.time()-t0:.0f}s)', flush=True)
    np.savez_compressed(p, Q=Q)
    return Q

Qm = qmat(wm, 'Q_melodia.npz')
Qp = qmat(wp, 'Q_pyin.npz')

def evaluate(D, name):
    t1 = t5 = 0
    for k, i in enumerate(eval_idx):
        order = np.argsort(D[k])
        ranked = [works[j] for j in order[:5]]
        t1 += ranked[0] == works[i]
        t5 += works[i] in ranked
    ne = len(eval_idx)
    print(f'{name:32s} top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%}', flush=True)

evaluate(Qp, 'pyin only')
evaluate(Qm, 'melodia only')
evaluate(np.minimum(Qp, Qm), 'min(pyin, melodia)')
evaluate((Qp + Qm) / 2, 'mean(pyin, melodia)')
def ranks(D):
    R = np.empty_like(D)
    for k in range(D.shape[0]):
        R[k, np.argsort(D[k])] = np.arange(D.shape[1])
    return R
evaluate(ranks(Qp) + ranks(Qm), 'rank sum')
