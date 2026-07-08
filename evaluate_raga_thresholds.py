"""RF accuracy vs min-tracks-per-raga threshold, track-level top1/top3, grouped CV."""
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

CACHE_DIR = Path('/Users/shyamravidath/carnatify/data/raga_v2_cache')


def _fold(name: str) -> str:
    d = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in d if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


def canonical_label(raga: str, _seen: dict = {}) -> str:
    """Merge diacritic spelling dupes (e.g. Ābhōgi/Ābhōgī) onto first-seen form."""
    return _seen.setdefault(_fold(raga), raga)


X, y_labels, track_ids = [], [], []
for subdir in ("saraga_v3", "archive_v3"):
    for p in sorted((CACHE_DIR / subdir).glob("*.npz")):
        d = np.load(p, allow_pickle=True)
        raga = canonical_label(str(d["raga"]))
        if raga == "Rāgamālika":
            continue
        for row in d["X"]:
            X.append(row); y_labels.append(raga); track_ids.append(str(d["track_id"]))
X = np.array(X); y_labels = np.array(y_labels); track_ids = np.array(track_ids)
total_tracks = len(set(track_ids))
print(f"all: {len(X)} samples, {total_tracks} tracks, {len(set(y_labels))} ragas")

for MIN in (5, 8, 10, 15, 20):
    ntr = {r: len(set(track_ids[y_labels == r])) for r in set(y_labels)}
    keep = {r for r, n in ntr.items() if n >= MIN}
    m = np.isin(y_labels, list(keep))
    Xk, yk, gk = X[m], y_labels[m], track_ids[m]
    le = LabelEncoder(); yi = le.fit_transform(yk)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    t1 = t3 = ntot = 0
    for tr, te in cv.split(Xk, yi, groups=gk):
        clf = RandomForestClassifier(n_estimators=300, max_features="sqrt",
                                     random_state=42, n_jobs=-1)
        clf.fit(Xk[tr], yi[tr])
        proba = clf.predict_proba(Xk[te])
        agg = defaultdict(list)
        for i, idx in enumerate(te):
            agg[gk[idx]].append(proba[i])
        for tid, ps in agg.items():
            mean = np.mean(ps, 0)
            true = yi[gk == tid][0]
            order = np.argsort(-mean)
            classes_seen = clf.classes_
            t1 += classes_seen[order[0]] == true
            t3 += true in classes_seen[order[:3]]
            ntot += 1
    cov = len(set(gk)) / total_tracks
    print(f"min_tracks>={MIN:2d}: ragas={len(keep):2d} tracks={len(set(gk)):3d} "
          f"coverage={cov:.0%}  track top1={t1/ntot:.1%} top3={t3/ntot:.1%}")
