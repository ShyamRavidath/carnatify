"""Short-query composition matching WITH raga gating (internal saraga eval).

Query: 60s/120s voiced melodia slice at several positions.
Gate: catalog restricted to refs whose raga matches the query's raga
(oracle = annotated; realistic gate simulated by top-3 raga hit-rate).
Score: Qmax (melodia chroma), query vs 3 ref windows, min distance.
"""
import json, time, unicodedata
from pathlib import Path
from collections import Counter
import numpy as np
import essentia.standard as es

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
MEL = SCRATCH / 'melodia_cache'
meta = json.load(open(CACHE / 'meta.json'))
DEC = 80
W_REF = 1000
MEL_HOP = 128 / 44100  # melodia hop 2.9ms -> DEC80 = 4.3Hz frames

def fold(s):
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())

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

chromas, ragas = [], []
for m in meta:
    mp = MEL / f"{m['tid'].replace('/','_')}.npy"
    chromas.append(chroma_from_pitch(np.load(mp)) if mp.exists() else None)
    ragas.append(fold(m['raga']))
ok = [i for i in range(len(meta)) if chromas[i] is not None]
meta = [meta[i] for i in ok]; chromas = [chromas[i] for i in ok]; ragas = [ragas[i] for i in ok]
N = len(meta)
works = [m['work_mbid'] for m in meta]
wc = Counter(works)
refs = [windows(c) for c in chromas]
print(f'{N} tracks; ragas known for {sum(1 for r in ragas if r)}', flush=True)

ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')

FRAMES_PER_S = 1.0 / (0.0029024943310657597 * DEC)  # pyin-rate cached melodia? melodia hop 2.9ms same

def run(q_secs, positions, gate, tag):
    QF = int(q_secs * FRAMES_PER_S)
    eval_idx = [i for i in range(N) if wc[works[i]] >= 2 and chromas[i].shape[0] >= QF + 30 and ragas[i]]
    t1 = t5 = n_eval = 0
    t0 = time.time()
    for i in eval_idx:
        c = chromas[i]
        for pos in positions:
            s0 = min(int(c.shape[0] * pos), c.shape[0] - QF)
            q = c[s0:s0 + QF]
            cand = [j for j in range(N) if j != i and (not gate or ragas[j] == ragas[i])]
            if not cand: continue
            s = {}
            for j in cand:
                best = np.inf
                for rb in refs[j]:
                    try:
                        _, d = csm(ccs(q, rb))
                        if d < best: best = d
                    except Exception:
                        pass
                s[j] = best
            ranked = sorted(s, key=s.get)
            rw = [works[j] for j in ranked[:5]]
            t1 += rw[0] == works[i]; t5 += works[i] in rw; n_eval += 1
    print(f'{tag:44s} top1={t1}/{n_eval}={t1/n_eval:.1%} top5={t5}/{n_eval}={t5/n_eval:.1%} ({time.time()-t0:.0f}s)', flush=True)

run(60, (0.05, 0.35), gate=False, tag='60s no gate (baseline)')
run(60, (0.05, 0.35), gate=True,  tag='60s ORACLE raga gate')
run(120, (0.05, 0.35), gate=True, tag='120s ORACLE raga gate')
run(30, (0.05, 0.35), gate=True,  tag='30s ORACLE raga gate')
