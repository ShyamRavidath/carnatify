"""Round 4: essentia Qmax cover-song similarity on pitch-derived chroma.

Chroma built from raw pitch contour (Hz), octave-folded, NO tonic dependence:
ChromaCrossSimilarity's OTI handles transposition between renditions.
"""
import json, time, sys
from pathlib import Path
from collections import Counter
import numpy as np
import essentia.standard as es

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
meta = json.load(open(CACHE / 'meta.json'))

DT = 0.0029024943310657597  # saraga pitch hop
DEC = 80                     # -> ~4.3 Hz chroma frames

def chroma_from_pitch(f):
    """One-hot 12-bin chroma per decimated frame from raw Hz (octave-folded)."""
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
        # small spread to neighbors for gamaka tolerance
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
N = len(meta)
works = [m['work_mbid'] for m in meta]
wc = Counter(works)
eval_idx = [i for i in range(N) if wc[works[i]] >= 2]
lens = np.array([c.shape[0] for c in chromas])
print(f'{N} tracks, eval {len(eval_idx)}, chroma len median {np.median(lens):.0f} max {lens.max()}', flush=True)

# cap length to keep O(n*m) sane: use first 1500 frames (~6 min melody)
CAP = 1500
chromas = [c[:CAP] for c in chromas]

ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')

def score(i, j):
    sim = ccs(chromas[i], chromas[j])
    _, d = csm(sim)
    return -d  # lower distance = better

t1 = t5 = 0
t0 = time.time()
for k, i in enumerate(eval_idx):
    s = np.array([score(i, j) if j != i else -np.inf for j in range(N)])
    order = np.argsort(-s)
    ranked = [works[j] for j in order[:5]]
    hit1 = ranked[0] == works[i]; hit5 = works[i] in ranked
    t1 += hit1; t5 += hit5
    print(f'[{k+1}/{len(eval_idx)}] {meta[i]["tid"][:34]:34s} top1={"OK" if hit1 else "--"} top5={"OK" if hit5 else "--"} best={meta[order[0]]["title"][:24]}', flush=True)
ne = len(eval_idx)
print(f'F: Qmax cover-song (serra09, OTI)  top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%} ({time.time()-t0:.0f}s)', flush=True)
