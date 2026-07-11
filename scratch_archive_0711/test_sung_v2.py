"""Sung-clip ID v2: voice-band melodia + tonic-hypothesis union gate + Qmax."""
import json, sys, unicodedata
from pathlib import Path
import joblib
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path('/Users/shyamravidath/carnatify')
MODELS = ROOT / 'models'
MEL_HOP_S = 128 / 44100
TAUS = (0.1, 0.15, 0.25)
NB = 40
DEC = 80
N_HYP = 3       # tonic hypotheses
GATE_K = 8      # ragas per hypothesis
PROBA_BLEND = 0.3

def fold(s):
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())

def tdms_multi(freqs, tonic):
    f = np.asarray(freqs, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 300 or tonic <= 0: return None
    cents = 1200.0 * np.log2(v / tonic)
    b = np.floor(np.mod(cents, 1200.0) / (1200.0 / NB)).astype(int) % NB
    parts = []
    for tau_s in TAUS:
        tau = max(1, int(round(tau_s / MEL_HOP_S)))
        if b.size <= tau: return None
        M = np.zeros((NB, NB))
        np.add.at(M, (b[:-tau], b[tau:]), 1.0)
        M = gaussian_filter(M, sigma=1.0, mode='wrap')
        M = M ** 0.75
        s = M.sum()
        if s <= 0: return None
        parts.append((M / s).ravel())
    return np.concatenate(parts)

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

import essentia.standard as es
clf = joblib.load(MODELS / 'raga_clip_rf.pkl')
cat = np.load(MODELS / 'qmax_catalog.npz')
windows = cat['windows']; win_track = cat['win_track']
meta = json.loads((MODELS / 'qmax_catalog_meta.json').read_text())
track_raga_f = [fold(m['raga']) for m in meta]
ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')
melodia = es.PredominantPitchMelodia(frameSize=2048, hopSize=128, minFrequency=90, maxFrequency=900, voicingTolerance=0.6)
eq = es.EqualLoudness()

TONICS = [85.0 * (2 ** (k / 36.0)) for k in range(72)]
folder = Path(sys.argv[1] if len(sys.argv) > 1 else '/Users/shyamravidath/sung_tests')
c1 = c5 = r1 = r3 = n = 0
for path in sorted(folder.glob('*.m4a')):
    print(f'\n=== {path.name} ===', flush=True)
    y = es.MonoLoader(filename=str(path), sampleRate=44100)()
    f0, _ = melodia(eq(y))
    # tonic hypotheses by RF confidence margin
    hyps = []
    for t in TONICS:
        td = tdms_multi(f0, t)
        if td is None: continue
        proba = clf.predict_proba(td[None, :])[0]
        hyps.append((float(proba.max()), t, proba))
    if not hyps:
        print('  no melody'); continue
    hyps.sort(reverse=True)
    # dedupe near-identical tonics (within 1 semitone)
    chosen = []
    for conf, t, proba in hyps:
        if all(abs(1200 * np.log2(t / tc)) > 150 for _, tc, _ in chosen):
            chosen.append((conf, t, proba))
        if len(chosen) == N_HYP: break
    gate = {}
    for conf, t, proba in chosen:
        order = np.argsort(-proba)[:GATE_K]
        for i in order:
            rf = fold(clf.classes_[i])
            gate[rf] = max(gate.get(rf, 0.0), float(proba[i]))
    print('  tonic hyps: ' + ', '.join(f'{t:.0f}Hz({c:.2f})' for c, t, _ in chosen))
    top_ragas = sorted(gate.items(), key=lambda kv: -kv[1])
    disp = {fold(c): c for c in clf.classes_}
    print('  raga union top-5: ' + ', '.join(f'{disp[r]} {p:.2f}' for r, p in top_ragas[:5]))

    q = chroma_from_pitch(f0)
    if q is None:
        print('  chroma fail'); continue
    best_per_track = {}
    for wi in range(len(win_track)):
        ti = int(win_track[wi])
        if track_raga_f[ti] not in gate: continue
        try:
            _, d = csm(ccs(q, windows[wi]))
        except Exception:
            continue
        if d < best_per_track.get(ti, np.inf):
            best_per_track[ti] = d
    scored = sorted(best_per_track.items(),
                    key=lambda kv: kv[1] - PROBA_BLEND * gate.get(track_raga_f[kv[0]], 0.0))
    seen, results = set(), []
    for ti, d in scored:
        tf = fold(meta[ti]['title'])
        if tf in seen: continue
        seen.add(tf)
        results.append((meta[ti]['title'], meta[ti]['raga'], d))
        if len(results) == 5: break
    print('  composition top-5:')
    for r, (title, raga, d) in enumerate(results, 1):
        print(f'    {r}. {title}  [{raga}]  (dist {d:.3f})')

    if '__' in path.stem:
        gt_title, gt_raga = path.stem.split('__', 1)
        n += 1
        h1 = results and fold(results[0][0]) == fold(gt_title)
        h5 = any(fold(t) == fold(gt_title) for t, _, _ in results)
        rh1 = top_ragas and top_ragas[0][0] == fold(gt_raga)
        rh3 = any(r == fold(gt_raga) for r, _ in top_ragas[:3])
        c1 += h1; c5 += h5; r1 += rh1; r3 += rh3
        print(f'  TRUTH {gt_title} [{gt_raga}]: comp {"OK" if h1 else "--"}/{"OK" if h5 else "--"} raga {"OK" if rh1 else "--"}/{"OK" if rh3 else "--"}')
if n:
    print(f'\n===== v2 SCORE over {n} =====')
    print(f'composition top-1 {c1}/{n} top-5 {c5}/{n}')
    print(f'raga union top-1 {r1}/{n} top-3 {r3}/{n}')
