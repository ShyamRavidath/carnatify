"""Does Qmax hold up with Melodia-on-mix contours instead of saraga vocal pyin?

Subset: all multi-rendition eval tracks + 40 distractors. Extract
PredominantPitchMelodia from the MIX audio, build chroma, run windowed Qmax
eval-vs-all-subset. Compare to the pyin-based result on the same subset.
"""
import json, time, sys
from pathlib import Path
from collections import Counter
import numpy as np
import essentia.standard as es

sys.path.insert(0, '/Users/shyamravidath/carnatify/src')
import mirdata

SCRATCH = Path(__file__).parent
CACHE = SCRATCH / 'comp_pitch_cache'
MEL_CACHE = SCRATCH / 'melodia_cache'; MEL_CACHE.mkdir(exist_ok=True)
meta = json.load(open(CACHE / 'meta.json'))
works_all = [m['work_mbid'] for m in meta]
wc = Counter(works_all)
eval_tids = [m['tid'] for m in meta if wc[m['work_mbid']] >= 2]
rng = np.random.default_rng(0)
distractors = [m['tid'] for m in meta if wc[m['work_mbid']] == 1]
sub_tids = eval_tids + distractors
by_tid = {m['tid']: m for m in meta}
print(f'subset: {len(sub_tids)} tracks ({len(eval_tids)} eval)', flush=True)

saraga = mirdata.initialize('saraga_carnatic', data_home='/Users/shyamravidath/carnatify')

eq = es.EqualLoudness()
melodia = es.PredominantPitchMelodia(frameSize=2048, hopSize=128)

def melodia_pitch(tid):
    p = MEL_CACHE / f"{tid.replace('/','_')}.npy"
    if p.exists(): return np.load(p)
    t = saraga.track(tid)
    audio_path = t.audio_path
    y = es.MonoLoader(filename=audio_path, sampleRate=44100)()
    f0, _ = melodia(eq(y))
    np.save(p, f0.astype(np.float32))
    return f0

DEC = 155  # 44100/128 hop = 344.5 Hz; /155 ≈ 2.2 Hz... match pyin DEC80@344Hz -> 4.3Hz: use 80
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

def ref_windows(c):
    n = c.shape[0]
    if n <= W_REF: return [c]
    starts = sorted({0, (n - W_REF) // 2, n - W_REF})
    return [c[s:s + W_REF] for s in starts]

chromas = {}
t0 = time.time()
for k, tid in enumerate(sub_tids):
    try:
        f0 = melodia_pitch(tid)
        chromas[tid] = chroma_from_pitch(f0)
    except Exception as e:
        print(f'  {tid}: FAIL {e}', flush=True)
        chromas[tid] = None
    if (k + 1) % 10 == 0:
        print(f'  melodia {k+1}/{len(sub_tids)} ({(time.time()-t0)/60:.0f} min)', flush=True)

sub = [t for t in sub_tids if chromas.get(t) is not None]
wins = {t: ref_windows(chromas[t]) for t in sub}
works = {t: by_tid[t]['work_mbid'] for t in sub}
ev = [t for t in sub if t in set(eval_tids)]
print(f'{len(sub)} usable, {len(ev)} eval', flush=True)

ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')

t1 = t5 = 0
for k, ti in enumerate(ev):
    s = {}
    for tj in sub:
        if tj == ti: continue
        best = np.inf
        for qa in wins[ti]:
            for rb in wins[tj]:
                try:
                    _, d = csm(ccs(qa, rb))
                    if d < best: best = d
                except Exception:
                    pass
        s[tj] = best
    ranked = sorted(s, key=s.get)
    rw = [works[t] for t in ranked[:5]]
    t1 += rw[0] == works[ti]
    t5 += works[ti] in rw
    print(f'[{k+1}/{len(ev)}] {ti[:32]:32s} {"OK" if rw[0]==works[ti] else "--"}/{"OK" if works[ti] in rw else "--"}', flush=True)
ne = len(ev)
print(f'J: melodia-mix FULL windowed Qmax: top1={t1}/{ne}={t1/ne:.1%} top5={t5}/{ne}={t5/ne:.1%}', flush=True)
