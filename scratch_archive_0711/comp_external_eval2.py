"""EXTERNAL composition eval: archive.org concert kritis, cross-artist renditions.

Works = (folded composition title, raga dir). Multi-rendition works give LOO
queries; catalog = every archive track with a melodia contour (~1200).
Windowed Qmax on melodia chroma (production-representative: mix audio, no
annotations of any kind).
"""
import json, re, time, unicodedata
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import essentia.standard as es

ROOT = Path('/Users/shyamravidath/carnatify')
MEL_DIR = ROOT / 'data' / 'raga_v2_cache' / 'melodia_full'
DEC = 80
W_REF = 1000
MAX_QUERIES = 60

def fold(s):
    d = unicodedata.normalize('NFKD', s)
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())

NUM_PREFIX = re.compile(r'^\d{1,3}[\s._-]*')
REND_SUFFIX = re.compile(r'_r\d+$')

def work_key(path):
    # archive__<raga>__<title stem>.npy
    parts = path.stem.split('__', 2)
    if len(parts) != 3: return None
    raga, stem = parts[1], parts[2]
    stem = REND_SUFFIX.sub('', stem)
    t = fold(NUM_PREFIX.sub('', stem))
    if len(t) < 6: return None
    return (t, fold(raga))

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
    return out if out.shape[0] >= 200 else None

def windows(c):
    n = c.shape[0]
    if n <= W_REF: return [c]
    starts = sorted({0, (n - W_REF) // 2, n - W_REF})
    return [c[s:s + W_REF] for s in starts]

paths = sorted(MEL_DIR.glob('*.npy'))
keys = [work_key(p) for p in paths]
ok = [i for i, k in enumerate(keys) if k is not None]
paths = [paths[i] for i in ok]; keys = [keys[i] for i in ok]
kc = Counter(keys)
multi = {k for k, n in kc.items() if n >= 2}
print(f'{len(paths)} tracks, {len(kc)} works, {len(multi)} multi-rendition works '
      f'({sum(kc[k] for k in multi)} tracks)', flush=True)

print('loading chroma...', flush=True)
chromas = []
for p in paths:
    chromas.append(chroma_from_pitch(np.load(p)))
usable = [i for i, c in enumerate(chromas) if c is not None]
paths = [paths[i] for i in usable]; keys = [keys[i] for i in usable]
chromas = [chromas[i] for i in usable]
N = len(paths)
kc = Counter(keys)
eval_idx = [i for i in range(N) if kc[keys[i]] >= 2]
rng = np.random.default_rng(0)
if len(eval_idx) > MAX_QUERIES:
    eval_idx = list(rng.choice(eval_idx, MAX_QUERIES, replace=False))
wins = [windows(c) for c in chromas]
print(f'{N} usable tracks, {len(eval_idx)} queries', flush=True)

ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')

import multiprocessing as _mp
_mp.set_start_method("fork", force=True)
from multiprocessing import Pool

def eval_query(i):
    import essentia.standard as es2
    ccs2 = es2.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
    csm2 = es2.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')
    s = np.full(N, np.inf)
    for j in range(N):
        if j == i: continue
        best = np.inf
        for qa in wins[i][:2]:
            for rb in wins[j]:
                try:
                    _, d = csm2(ccs2(qa, rb))
                    if d < best: best = d
                except Exception:
                    pass
        s[j] = best
    order = np.argsort(s)
    ranked = [keys[j] for j in order[:5]]
    return i, ranked[0] == keys[i], keys[i] in ranked

t1 = t5 = done = 0
t0 = time.time()
with Pool(6) as pool:
    for i, hit1, hit5 in pool.imap_unordered(eval_query, eval_idx):
        t1 += hit1; t5 += hit5; done += 1
        print(f'[{done}/{len(eval_idx)}] {paths[i].stem[:50]:50s} {"OK" if hit1 else "--"}/{"OK" if hit5 else "--"} ({time.time()-t0:.0f}s)', flush=True)
ne = len(eval_idx)
print(f'EXTERNAL: top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%}', flush=True)
