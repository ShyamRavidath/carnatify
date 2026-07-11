"""Qmax param sweep. Usage: comp_sweep.py <config_name>"""
import json, time, sys
from pathlib import Path
from collections import Counter
import numpy as np
import essentia.standard as es

CFG = sys.argv[1]
CONFIGS = {
    'cap3000':   dict(dec=80, cap=3000, stack=9, binp=0.095, dison=0.5, disext=0.5, dist='asymmetric'),
    'dec40':     dict(dec=40, cap=3000, stack=9, binp=0.095, dison=0.5, disext=0.5, dist='asymmetric'),
    'binp15':    dict(dec=80, cap=1500, stack=9, binp=0.15,  dison=0.5, disext=0.5, dist='asymmetric'),
    'dis_low':   dict(dec=80, cap=1500, stack=9, binp=0.095, dison=0.3, disext=0.3, dist='asymmetric'),
    'stack15':   dict(dec=80, cap=1500, stack=15, binp=0.095, dison=0.5, disext=0.5, dist='asymmetric'),
}
C = CONFIGS[CFG]

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
meta = json.load(open(CACHE / 'meta.json'))
DEC = C['dec']

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

chromas = []
for m in meta:
    d = np.load(CACHE / m['file'])
    chromas.append(chroma_from_pitch(d['f']))
ok = [i for i, c in enumerate(chromas) if c is not None]
meta = [meta[i] for i in ok]; chromas = [chromas[i] for i in ok]
chromas = [c[:C['cap']] for c in chromas]
N = len(meta)
works = [m['work_mbid'] for m in meta]
wc = Counter(works)
eval_idx = [i for i in range(N) if wc[works[i]] >= 2]

ccs = es.ChromaCrossSimilarity(frameStackSize=C['stack'], frameStackStride=1, binarizePercentile=C['binp'], oti=True)
csm = es.CoverSongSimilarity(disOnset=C['dison'], disExtension=C['disext'], alignmentType='serra09', distanceType=C['dist'])

t1 = t5 = 0
t0 = time.time()
for i in eval_idx:
    s = np.full(N, -np.inf)
    for j in range(N):
        if j == i: continue
        try:
            _, d = csm(ccs(chromas[i], chromas[j]))
            s[j] = -d
        except Exception:
            pass
    order = np.argsort(-s)
    ranked = [works[j] for j in order[:5]]
    t1 += ranked[0] == works[i]
    t5 += works[i] in ranked
ne = len(eval_idx)
print(f'{CFG}: top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%} ({time.time()-t0:.0f}s)', flush=True)
