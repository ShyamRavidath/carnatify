"""Late fusion: RF(hist) + RF(bigram) probability averaging, weighted."""
import unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.ndimage import median_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

CACHE_DIR = Path('/Users/shyamravidath/carnatify/data/raga_v2_cache')

def _fold(name):
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())

_seen = {}
def canon(r): return _seen.setdefault(_fold(r), r)

NB = 24
def bigram_feat(freqs, tonic):
    f = np.asarray(freqs, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 60 or tonic <= 0: return np.zeros(NB * NB)
    c = 1200.0 * np.log2(v / tonic)
    c = median_filter(c, size=7, mode='nearest')
    q = np.mod(np.round(c / (1200.0 / NB)).astype(int), NB)
    keep = np.ones(q.size, bool); keep[1:] = q[1:] != q[:-1]
    seq = q[keep]
    M = np.zeros((NB, NB))
    if seq.size >= 2:
        np.add.at(M, (seq[:-1], seq[1:]), 1.0)
        M /= M.sum()
    return M.ravel()

X, Xb, y_labels, track_ids = [], [], [], []
for subdir in ('saraga_v3', 'archive_v3'):
    for p in sorted((CACHE_DIR / subdir).glob('*.npz')):
        d = np.load(p, allow_pickle=True)
        raga = canon(str(d['raga']))
        if raga == 'Rāgamālika': continue
        bg = bigram_feat(d['frequencies'], float(d['tonics'][0]))
        for row in d['X']:
            X.append(row); Xb.append(bg); y_labels.append(raga); track_ids.append(str(d['track_id']))
X = np.array(X); Xb = np.array(Xb); y_labels = np.array(y_labels); track_ids = np.array(track_ids)

for MIN in (5, 10, 15):
    ntr = {r: len(set(track_ids[y_labels == r])) for r in set(y_labels)}
    keep = {r for r, n in ntr.items() if n >= MIN}
    m = np.isin(y_labels, list(keep))
    Xk, Xbk, yk, gk = X[m], Xb[m], y_labels[m], track_ids[m]
    le = LabelEncoder(); yi = le.fit_transform(yk)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    res = {w: [0, 0, 0] for w in (0.0, 0.2, 0.3, 0.5)}
    for tr, te in cv.split(Xk, yi, groups=gk):
        c1 = RandomForestClassifier(n_estimators=300, max_features='sqrt', random_state=42, n_jobs=-1).fit(Xk[tr], yi[tr])
        c2 = RandomForestClassifier(n_estimators=300, max_features='sqrt', random_state=42, n_jobs=-1).fit(Xbk[tr], yi[tr])
        p1 = c1.predict_proba(Xk[te]); p2 = c2.predict_proba(Xbk[te])
        agg = defaultdict(list)
        for i, idx in enumerate(te): agg[gk[idx]].append((p1[i], p2[i]))
        for w in res:
            for tid, ps in agg.items():
                m1 = np.mean([a for a, b in ps], 0); m2 = np.mean([b for a, b in ps], 0)
                mean = (1 - w) * m1 + w * m2
                true = yi[gk == tid][0]
                order = np.argsort(-mean); cs = c1.classes_
                res[w][0] += cs[order[0]] == true
                res[w][1] += true in cs[order[:3]]
                res[w][2] += 1
    for w, (t1, t3, ntot) in res.items():
        print(f'min>={MIN:2d} w_bigram={w}: top1={t1/ntot:.1%} top3={t3/ntot:.1%}', flush=True)
