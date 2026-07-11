"""v2 voice-band melodia oracle-tonic diagnostic on Deepti's sung clips.

For each clip: melodia -> try 36 tonic hypotheses (85-340 Hz, 1/3-semitone
steps) -> TDMS -> raga RF -> rank of TRUE raga. Reports the best tonic per
clip and whether a consistent shruti fixes the gate.
"""
import sys, unicodedata
from pathlib import Path
import joblib
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path('/Users/shyamravidath/carnatify')
MODELS = ROOT / 'models'
MEL_HOP_S = 128 / 44100
TAUS = (0.1, 0.15, 0.25)
NB = 40

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

import essentia.standard as es
clf = joblib.load(MODELS / 'raga_clip_rf.pkl')
classes_f = [fold(c) for c in clf.classes_]
melodia = es.PredominantPitchMelodia(frameSize=2048, hopSize=128, minFrequency=90, maxFrequency=900, voicingTolerance=0.6)
eq = es.EqualLoudness()

folder = Path('/Users/shyamravidath/sung_tests')
TONICS = [85.0 * (2 ** (k / 36.0)) for k in range(72)]  # 85..340 Hz, 1/3 semitone
best_per_clip = []
for path in sorted(folder.glob('*.m4a')):
    gt_raga = fold(path.stem.split('__', 1)[1])
    y = es.MonoLoader(filename=str(path), sampleRate=44100)()
    f0, _ = melodia(eq(y))
    v = f0[f0 > 0]
    print(f'\n{path.name}: voiced median {np.median(v):.0f} Hz, p5-p95 {np.percentile(v,5):.0f}-{np.percentile(v,95):.0f}')
    if gt_raga not in classes_f:
        print(f'  TRUE raga not in model classes — skip rank scan')
        continue
    gi = classes_f.index(gt_raga)
    rows = []
    for t in TONICS:
        td = tdms_multi(f0, t)
        if td is None: continue
        proba = clf.predict_proba(td[None, :])[0]
        rank = int((proba > proba[gi]).sum()) + 1
        rows.append((rank, proba[gi], t, proba.max(), clf.classes_[proba.argmax()]))
    rows.sort()
    r0 = rows[0]
    print(f'  BEST: true-raga rank {r0[0]} (p={r0[1]:.2f}) at tonic {r0[2]:.1f} Hz (argmax {r0[4]} {r0[3]:.2f})')
    good = [r for r in rows if r[0] <= 8]
    print(f'  tonics putting true raga in top-8: {len(good)}/{len(rows)}: ' +
          ', '.join(f'{r[2]:.0f}' for r in good[:10]))
    if good:
        best_per_clip.append((path.name, [r[2] for r in good]))

# consistency: is there one tonic in every clip's good set?
print('\n=== cross-clip shruti consistency ===')
from collections import Counter
c = Counter()
for name, ts in best_per_clip:
    for t in ts:
        c[round(12 * np.log2(t / 130.81)) % 12] += 1  # semitone class rel C3
for pc, n in c.most_common(5):
    print(f'pitch-class {pc} (~{130.81 * 2**(pc/12):.0f} Hz family): good in {n} clip-tonics')
