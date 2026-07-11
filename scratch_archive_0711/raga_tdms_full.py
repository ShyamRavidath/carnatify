"""TDMS from FULL-track melody (melodia for archive, saraga annotated pitch),
tonic from the production cache. min>=20 tier, grouped CV, track-level."""
import sys, unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, '/Users/shyamravidath/carnatify/src')
import mirdata

ROOT = Path('/Users/shyamravidath/carnatify')
CACHE_DIR = ROOT / 'data' / 'raga_v2_cache'
MEL_DIR = CACHE_DIR / 'melodia_full'
MEL_HOP_S = 128 / 44100
PYIN_HOP_S = 512 / 22050

def _fold(name):
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())

_seen = {}
def canon(r): return _seen.setdefault(_fold(r), r)

NB = 40
def tdms(freqs, tonic, hop_s, tau_s=0.3, sigma=1.0, alpha=0.75):
    f = np.asarray(freqs, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 500 or tonic <= 0: return None
    c = np.mod(1200.0 * np.log2(v / tonic), 1200.0)
    b = np.floor(c / (1200.0 / NB)).astype(int) % NB
    tau = max(1, int(round(tau_s / hop_s)))
    if b.size <= tau: return None
    M = np.zeros((NB, NB))
    np.add.at(M, (b[:-tau], b[tau:]), 1.0)
    M = gaussian_filter(M, sigma=sigma, mode='wrap')
    M = M ** alpha
    s = M.sum()
    if s <= 0: return None
    return (M / s).ravel()

saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
saraga_pitch = {}
for tid in saraga.track_ids:
    t = saraga.track(tid)
    p = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
    if p is not None:
        saraga_pitch[tid.split('/')[-1] if '/' in tid else tid] = p.frequencies
# saraga_v3 track_ids: inspect a sample to map
X, Xt, y_labels, track_ids = [], [], [], []
n_no_full = 0
for subdir in ('saraga_v3', 'archive_v3'):
    for p in sorted((CACHE_DIR / subdir).glob('*.npz')):
        d = np.load(p, allow_pickle=True)
        raga = canon(str(d['raga']))
        if raga == 'Rāgamālika': continue
        tid = str(d['track_id'])
        tonic = float(d['tonics'][0])
        full = None; hop = MEL_HOP_S
        if subdir == 'archive_v3':
            mp = MEL_DIR / f'{p.stem}.npy'
            if mp.exists(): full = np.load(mp)
        else:
            key = tid.replace('saraga__', '')
            if key in saraga_pitch:
                full = saraga_pitch[key]; hop = 0.0029024943310657597
            elif tid in saraga_pitch:
                full = saraga_pitch[tid]; hop = 0.0029024943310657597
        if full is None:
            full = d['frequencies']; hop = PYIN_HOP_S; n_no_full += 1
        t = tdms(full, tonic, hop)
        if t is None: continue
        for row in d['X']:
            X.append(row); Xt.append(t); y_labels.append(raga); track_ids.append(tid)
X = np.array(X); Xt = np.array(Xt); y_labels = np.array(y_labels); track_ids = np.array(track_ids)
print(f'{len(set(track_ids))} tracks ({n_no_full} fell back to 65s pitch)', flush=True)

MIN = 20
ntr = {r: len(set(track_ids[y_labels == r])) for r in set(y_labels)}
keep = {r for r, n in ntr.items() if n >= MIN}
m = np.isin(y_labels, list(keep))
Xk, Xtk, yk, gk = X[m], Xt[m], y_labels[m], track_ids[m]
le = LabelEncoder(); yi = le.fit_transform(yk)
print(f'min>={MIN}: {len(keep)} ragas, {len(set(gk))} tracks', flush=True)

def run_cv(feats, tag, fuse_with=None, w=0.5):
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    t1 = t3 = ntot = 0
    for tr, te in cv.split(Xk, yi, groups=gk):
        clf = RandomForestClassifier(n_estimators=800, max_features='sqrt', random_state=42, n_jobs=-1)
        clf.fit(feats[tr], yi[tr])
        proba = clf.predict_proba(feats[te])
        if fuse_with is not None:
            c2 = RandomForestClassifier(n_estimators=800, max_features='sqrt', random_state=42, n_jobs=-1)
            c2.fit(fuse_with[tr], yi[tr])
            proba = (1 - w) * proba + w * c2.predict_proba(fuse_with[te])
        agg = defaultdict(list)
        for i, idx in enumerate(te): agg[gk[idx]].append(proba[i])
        for tid, ps in agg.items():
            mean = np.mean(ps, 0); true = yi[gk == tid][0]
            order = np.argsort(-mean); cs = clf.classes_
            t1 += cs[order[0]] == true; t3 += true in cs[order[:3]]; ntot += 1
    print(f'{tag:44s} top1={t1/ntot:.1%} top3={t3/ntot:.1%}', flush=True)

run_cv(Xtk, 'TDMS-full only')
run_cv(np.hstack([Xk, Xtk]), 'hist + TDMS-full concat')
run_cv(np.hstack([Xk, Xtk]), 'concat + fuse TDMS w=0.3', fuse_with=Xtk, w=0.3)
