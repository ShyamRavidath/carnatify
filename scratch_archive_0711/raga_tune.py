"""RF tuning + train-side noise filtering on the doubled corpus (min>=20 tier)."""
import unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np
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

X, y_labels, track_ids = [], [], []
for subdir in ('saraga_v3', 'archive_v3'):
    for p in sorted((CACHE_DIR / subdir).glob('*.npz')):
        d = np.load(p, allow_pickle=True)
        raga = canon(str(d['raga']))
        if raga == 'Rāgamālika': continue
        for row in d['X']:
            X.append(row); y_labels.append(raga); track_ids.append(str(d['track_id']))
X = np.array(X); y_labels = np.array(y_labels); track_ids = np.array(track_ids)

MIN = 20
ntr = {r: len(set(track_ids[y_labels == r])) for r in set(y_labels)}
keep = {r for r, n in ntr.items() if n >= MIN}
m = np.isin(y_labels, list(keep))
Xk, yk, gk = X[m], y_labels[m], track_ids[m]
le = LabelEncoder(); yi = le.fit_transform(yk)
print(f'min>={MIN}: {len(keep)} ragas, {len(set(gk))} tracks', flush=True)

def run_cv(params, train_filter_probs=None, filter_q=0.0, tag=''):
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    t1 = t3 = ntot = 0
    oof = {}
    for tr, te in cv.split(Xk, yi, groups=gk):
        tr_use = tr
        if train_filter_probs is not None and filter_q > 0:
            thr = np.quantile([train_filter_probs[t] for t in set(gk[tr])], filter_q)
            bad_tracks = {t for t in set(gk[tr]) if train_filter_probs[t] < thr}
            tr_use = tr[~np.isin(gk[tr], list(bad_tracks))]
        clf = RandomForestClassifier(random_state=42, n_jobs=-1, **params)
        clf.fit(Xk[tr_use], yi[tr_use])
        proba = clf.predict_proba(Xk[te])
        agg = defaultdict(list)
        for i, idx in enumerate(te): agg[gk[idx]].append(proba[i])
        for tid, ps in agg.items():
            mean = np.mean(ps, 0); true = yi[gk == tid][0]
            order = np.argsort(-mean); cs = clf.classes_
            t1 += cs[order[0]] == true; t3 += true in cs[order[:3]]; ntot += 1
            ci = np.where(cs == true)[0]
            oof[tid] = float(mean[ci[0]]) if ci.size else 0.0
    print(f'{tag:48s} top1={t1/ntot:.1%} top3={t3/ntot:.1%}', flush=True)
    return oof

base = dict(n_estimators=300, max_features='sqrt')
oof = run_cv(base, tag='base rf300')
run_cv(dict(n_estimators=800, max_features='sqrt'), tag='rf800')
run_cv(dict(n_estimators=800, max_features='sqrt', class_weight='balanced_subsample'), tag='rf800 balanced')
run_cv(dict(n_estimators=800, max_features=0.2), tag='rf800 mf=0.2')
run_cv(dict(n_estimators=800, max_features='sqrt', min_samples_leaf=2), tag='rf800 leaf2')
# noise filter: drop lowest-q OOF-true-prob tracks from TRAIN only
for q in (0.05, 0.10, 0.15):
    run_cv(dict(n_estimators=800, max_features='sqrt'), train_filter_probs=oof, filter_q=q,
           tag=f'rf800 + train noise filter q={q}')
