"""End-to-end SoundHound-style eval on the archive corpus (external-ish).

Pipeline per query: 30/60s melodia clip -> TDMS -> raga RF (trained leak-free,
grouped 5-fold on full-track TDMS) -> top-3 raga gate over catalog -> Qmax
within gate -> composition ranking.

Catalog: all archive tracks with melodia (~1200), works = (title fold, raga).
Queries: multi-rendition works, clip cut from the recording (LOO).
"""
import re, time, unicodedata
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
import essentia.standard as es

ROOT = Path('/Users/shyamravidath/carnatify')
MEL_DIR = ROOT / 'data' / 'raga_v2_cache' / 'melodia_full'
CACHE_V3 = ROOT / 'data' / 'raga_v2_cache' / 'archive_v3'
MEL_HOP = 128 / 44100
DEC = 80
W_REF = 800
TAUS = (0.1, 0.15, 0.25)
NB = 40
Q_SECS = 60
MAX_QUERIES = 60

def fold(s):
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())

NUM_PREFIX = re.compile(r'^\d{1,3}[\s._-]*')
REND_SUFFIX = re.compile(r'_r\d+$')

# tonics from archive_v3 npz
tonics = {}
for p in CACHE_V3.glob('*.npz'):
    d = np.load(p, allow_pickle=True)
    tonics[p.stem] = float(d['tonics'][0])

def tdms_from_f0(f0, tonic, hop_s):
    f = np.asarray(f0, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 300 or tonic <= 0: return None
    cents = 1200.0 * np.log2(v / tonic)
    b = np.floor(np.mod(cents, 1200.0) / (1200.0 / NB)).astype(int) % NB
    parts = []
    for tau_s in TAUS:
        tau = max(1, int(round(tau_s / hop_s)))
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
        bb = int(round(pc)) % 12
        out[i, bb] = 1.0
        out[i, (bb + 1) % 12] = 0.3; out[i, (bb - 1) % 12] = 0.3
        valid[i] = True
    out = out[valid]
    return out if out.shape[0] >= 30 else None

def ref_windows(c):
    n = c.shape[0]
    if n <= W_REF: return [c]
    starts = sorted({0, (n - W_REF) // 2, n - W_REF})
    return [c[s:s + W_REF] for s in starts]

# load catalog
paths, works, ragas_f, f0s = [], [], [], []
for p in sorted(MEL_DIR.glob('*.npy')):
    parts = p.stem.split('__', 2)
    if len(parts) != 3 or p.stem not in tonics: continue
    raga, stem = parts[1], parts[2]
    t = fold(NUM_PREFIX.sub('', REND_SUFFIX.sub('', stem)))
    if len(t) < 6: continue
    paths.append(p); works.append((t, fold(raga))); ragas_f.append(fold(raga))
    f0s.append(None)  # lazy
print('catalog candidates:', len(paths), flush=True)

# features
chromas, tdms_full = [], []
for k, p in enumerate(paths):
    f0 = np.load(p)
    f0s[k] = f0
    chromas.append(chroma_from_pitch(f0))
    tdms_full.append(tdms_from_f0(f0, tonics[p.stem], MEL_HOP))
ok = [i for i in range(len(paths)) if chromas[i] is not None and tdms_full[i] is not None]
paths = [paths[i] for i in ok]; works = [works[i] for i in ok]; ragas_f = [ragas_f[i] for i in ok]
f0s = [f0s[i] for i in ok]; chromas = [chromas[i] for i in ok]; tdms_full = [tdms_full[i] for i in ok]
N = len(paths)
wc = Counter(works)
refs = [ref_windows(c) for c in chromas]
X_full = np.stack(tdms_full)
y_raga = np.array(ragas_f)
groups = np.array([p.stem for p in paths])
print(f'{N} catalog tracks, {len(set(y_raga))} ragas', flush=True)

# leak-free clip raga prediction: grouped 5-fold, train on full-track TDMS,
# predict on CLIP TDMS of held-out tracks
QF_MEL = int(Q_SECS / MEL_HOP)  # frames of raw melodia for the clip
clip_pred_top3 = {}
gkf = GroupKFold(n_splits=5)
rng = np.random.default_rng(0)
for tr, te in gkf.split(X_full, y_raga, groups=groups):
    # train on CLIP TDMS: 5 clips per training track (domain-matched)
    Xc, yc = [], []
    for ti in tr:
        f0 = f0s[ti]
        rt = np.random.default_rng(abs(hash('train'+paths[ti].stem)) % (2**32))
        for _ in range(5):
            if f0.size <= QF_MEL: clip_t = f0
            else:
                s0 = int(rt.uniform(0.02, 0.75) * (f0.size - QF_MEL))
                clip_t = f0[s0:s0 + QF_MEL]
            td = tdms_from_f0(clip_t, tonics[paths[ti].stem], MEL_HOP)
            if td is not None:
                Xc.append(td); yc.append(y_raga[ti])
    clf = RandomForestClassifier(n_estimators=400, max_features='sqrt', random_state=42, n_jobs=-1)
    clf.fit(np.stack(Xc), np.array(yc))
    for i in te:
        f0 = f0s[i]
        # clip from a random-ish position (seeded per track)
        r = np.random.default_rng(abs(hash(paths[i].stem)) % (2**32))
        if f0.size <= QF_MEL: clip = f0
        else:
            s0 = int(r.uniform(0.05, 0.6) * (f0.size - QF_MEL))
            clip = f0[s0:s0 + QF_MEL]
        td = tdms_from_f0(clip, tonics[paths[i].stem], MEL_HOP)
        if td is None:
            clip_pred_top3[i] = None; continue
        proba = clf.predict_proba(td[None, :])[0]
        top3 = clf.classes_[np.argsort(-proba)[:5]]
        clip_pred_top3[i] = (set(top3), clip)
raga_top3_hits = sum(1 for i, v in clip_pred_top3.items() if v and y_raga[i] in v[0])
n_pred = sum(1 for v in clip_pred_top3.values() if v)
print(f'clip({Q_SECS}s) raga top-5 accuracy (clip-trained): {raga_top3_hits}/{n_pred}={raga_top3_hits/n_pred:.1%}', flush=True)

# end-to-end composition
eval_idx = [i for i in range(N) if wc[works[i]] >= 2 and clip_pred_top3.get(i)]
if len(eval_idx) > MAX_QUERIES:
    eval_idx = list(int(x) for x in rng.choice(eval_idx, MAX_QUERIES, replace=False))
ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')

t1 = t5 = n_eval = 0
t0 = time.time()
for k, i in enumerate(eval_idx):
    top3, clip = clip_pred_top3[i]
    q = chroma_from_pitch(clip)
    if q is None: continue
    cand = [j for j in range(N) if j != i and ragas_f[j] in top3]
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
    hit1 = rw[0] == works[i]; hit5 = works[i] in rw
    t1 += hit1; t5 += hit5; n_eval += 1
    print(f'[{n_eval}] {paths[i].stem[:46]:46s} cand={len(cand):3d} {"OK" if hit1 else "--"}/{"OK" if hit5 else "--"} ({time.time()-t0:.0f}s)', flush=True)
print(f'E2E {Q_SECS}s clip, clip-trained top-5 raga gate: top1={t1}/{n_eval}={t1/n_eval:.1%} top5={t5}/{n_eval}={t5/n_eval:.1%}', flush=True)
