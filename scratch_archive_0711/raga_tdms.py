"""TDMS (time-delayed melody surface) features from cached 65s pitch, min>=20 tier."""
import unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

CACHE_DIR = Path('/Users/shyamravidath/carnatify/data/raga_v2_cache')
PYIN_HOP_S = 512 / 22050  # librosa pyin default hop at 22050

def _fold(name):
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())

_seen = {}
def canon(r): return _seen.setdefault(_fold(r), r)

NB = 40  # bins per octave-folded axis

def tdms(freqs, tonic, tau_s=0.3, sigma=1.0, alpha=0.75):
    f = np.asarray(freqs, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 100 or tonic <= 0: return None
    c = np.mod(1200.0 * np.log2(v / tonic), 1200.0)
    b = np.floor(c / (1200.0 / NB)).astype(int) % NB
    # NOTE: voiced-only sequence approximates contiguity; tau in voiced frames
    tau = max(1, int(round(tau_s / PYIN_HOP_S)))
    if b.size <= tau: return None
    M = np.zeros((NB, NB))
    np.add.at(M, (b[:-tau], b[tau:]), 1.0)
    # circular gaussian smoothing
    M = gaussian_filter(M, sigma=sigma, mode='wrap')
    M = M ** alpha
    s = M.sum()
    if s <= 0: return None
    return (M / s).ravel()

X, Xt, y_labels, track_ids = [], [], [], []
for subdir in ('saraga_v3', 'archive_v3'):
    for p in sorted((CACHE_DIR / subdir).glob('*.npz')):
        d = np.load(p, allow_pickle=True)
        raga = canon(str(d['raga']))
        if raga == 'Rāgamālika': continue
        t = tdms(d['frequencies'], float(d['tonics'][0]))
        if t is None: continue
        for row in d['X']:
            X.append(row); Xt.append(t); y_labels.append(raga); track_ids.append(str(d['track_id']))
X = np.array(X); Xt = np.array(Xt); y_labels = np.array(y_labels); track_ids = np.array(track_ids)

MIN = 20
ntr = {r: len(set(track_ids[y_labels == r])) for r in set(y_labels)}
keep = {r for r, n in ntr.items() if n >= MIN}
m = np.isin(y_labels, list(keep))
Xk, Xtk, yk, gk = X[m], Xt[m], y_labels[m], track_ids[m]
le = LabelEncoder(); yi = le.fit_transform(yk)
print(f'min>={MIN}: {len(keep)} ragas, {len(set(gk))} tracks, tdms dim {Xtk.shape[1]}', flush=True)

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
    print(f'{tag:40s} top1={t1/ntot:.1%} top3={t3/ntot:.1%}', flush=True)

run_cv(Xtk, 'TDMS only (65s)')
run_cv(np.hstack([Xk, Xtk]), 'hist+TDMS concat')
run_cv(Xk, 'TDMS late fusion w=0.4', fuse_with=Xtk, w=0.4)
