"""TDMS param sweep (tau/NB/alpha, multi-tau concat) + tier scan + noise filter."""
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
SARAGA_HOP_S = 0.0029024943310657597

def _fold(name):
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())

_seen = {}
def canon(r): return _seen.setdefault(_fold(r), r)

def tdms(cents_bins_cache, key, v, hop_s, tau_s, nb, sigma, alpha):
    b = np.floor(np.mod(v, 1200.0) / (1200.0 / nb)).astype(int) % nb
    tau = max(1, int(round(tau_s / hop_s)))
    if b.size <= tau: return None
    M = np.zeros((nb, nb))
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
        saraga_pitch[tid] = p.frequencies

# collect (cents_voiced, hop, raga, tid) per track
tracks = []
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
            full = saraga_pitch.get(key, saraga_pitch.get(tid))
            hop = SARAGA_HOP_S
        if full is None: continue
        f = np.asarray(full, dtype=np.float64)
        v = f[(f > 0) & np.isfinite(f)]
        if v.size < 500 or tonic <= 0: continue
        tracks.append((1200.0 * np.log2(v / tonic), hop, raga, tid))
print(f'{len(tracks)} tracks with full melody', flush=True)

y_all = np.array([t[2] for t in tracks])
g_all = np.array([t[3] for t in tracks])

def build(tau_list, nb, sigma, alpha):
    F = []
    okm = []
    for cents, hop, raga, tid in tracks:
        parts = []
        ok = True
        for tau_s in tau_list:
            f = tdms(None, None, cents, hop, tau_s, nb, sigma, alpha)
            if f is None: ok = False; break
            parts.append(f)
        F.append(np.concatenate(parts) if ok else None)
        okm.append(ok)
    okm = np.array(okm)
    return np.stack([f for f in F if f is not None]), y_all[okm], g_all[okm]

def run_cv(X, y, g, MIN, tag, filter_q=0.0):
    ntr = {r: len(set(g[y == r])) for r in set(y)}
    keep = {r for r, n in ntr.items() if n >= MIN}
    m = np.isin(y, list(keep))
    Xk, yk, gk = X[m], y[m], g[m]
    le = LabelEncoder(); yi = le.fit_transform(yk)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    def one_pass(drop_tracks=None):
        t1 = t3 = ntot = 0
        oof = {}
        for tr, te in cv.split(Xk, yi, groups=gk):
            tr_use = tr if not drop_tracks else tr[~np.isin(gk[tr], list(drop_tracks))]
            clf = RandomForestClassifier(n_estimators=800, max_features='sqrt', random_state=42, n_jobs=-1)
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
        return t1 / ntot, t3 / ntot, oof
    a1, a3, oof = one_pass()
    line = f'{tag:46s} min>={MIN:2d} ragas={len(keep):2d} top1={a1:.1%} top3={a3:.1%}'
    if filter_q > 0:
        thr = np.quantile(list(oof.values()), filter_q)
        bad = {t for t, v in oof.items() if v < thr}
        b1, b3, _ = one_pass(drop_tracks=bad)
        line += f'  | +filter q={filter_q}: top1={b1:.1%} top3={b3:.1%}'
    print(line, flush=True)

# param sweep at min>=20
for tau_list, nb, sigma, alpha in (
    ((0.3,), 40, 1.0, 0.75),
    ((0.15,), 40, 1.0, 0.75),
    ((0.5,), 40, 1.0, 0.75),
    ((0.15, 0.3, 0.6), 40, 1.0, 0.75),
    ((0.3,), 60, 1.5, 0.75),
    ((0.3,), 40, 1.0, 0.5),
    ((0.15, 0.3, 0.6), 40, 1.0, 0.5),
):
    X, y, g = build(tau_list, nb, sigma, alpha)
    run_cv(X, y, g, 20, f'tau={tau_list} nb={nb} sig={sigma} a={alpha}')

# best-guess config: tier scan + filter
X, y, g = build((0.15, 0.3, 0.6), 40, 1.0, 0.75)
for MIN in (10, 15, 20):
    run_cv(X, y, g, MIN, 'multi-tau', filter_q=0.15)
