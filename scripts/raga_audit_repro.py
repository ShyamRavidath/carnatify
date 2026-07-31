"""The reproduction gate, run on the ORIGINAL harness rather than a rebuild.

`WORKHORSE_RAGA_AUDIT_BRIEF.md` states the CV harness behind "72.8% top-1 /
84.7% top-3" was never committed. **It was.** `git log -S"72.8" -- '*.py'` misses
it because the harness never contained the number: it is
`scratch_archive_0711/raga_final_push.py`, committed in `c1fca59` on 2026-07-11,
and its docstring is "Final push: multi-tau TDMS (0.1,0.15,0.25) + hist late
fusion, ExtraTrees, big forests". It hardcodes `MIN = 20` and prints a sweep,
which is where "min>=20: 67.6/79.4" came from; the min>=25 line in
`train_raga_v3_tdms.py`'s docstring came from the same code at the other tier.

This file is that harness transplanted verbatim. Everything between the two
marker comments is byte-identical to `raga_final_push.py` lines 14-102. The only
edits, both declared:

  * `MIN = 20` -> `MIN = 25`, the tier the gated number was measured at;
  * the seven `run(...)` sweep calls at the bottom reduced to the one config the
    exported model uses, `RF800 tdms + hist w=0.4`.

No feature code, no CV code, no seed, no read-out is touched. In particular the
read-out stays the original's: fold posteriors averaged over a track's three
augmented rows, one prediction per track.

Run for the audit AFTER `raga_audit_score.py` had already produced its numbers,
to answer one question the rebuild alone cannot: does the historical number
reproduce from the historical code in today's environment? Read-only; prints.

Usage: venv/bin/python scripts/raga_audit_repro.py
"""
from __future__ import annotations

import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

# --- verbatim from scratch_archive_0711/raga_final_push.py ------------------
sys.path.insert(0, '/Users/shyamravidath/carnatify/src')
import mirdata  # noqa: E402

ROOT = Path('/Users/shyamravidath/carnatify')
CACHE_DIR = ROOT / 'data' / 'raga_v2_cache'
MEL_DIR = CACHE_DIR / 'melodia_full'
MEL_HOP_S = 128 / 44100
SARAGA_HOP_S = 0.0029024943310657597
TAUS = (0.1, 0.15, 0.25)
NB = 40


def _fold(name):
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


_seen = {}
def canon(r): return _seen.setdefault(_fold(r), r)


def tdms_multi(cents, hop_s):
    parts = []
    b_all = np.floor(np.mod(cents, 1200.0) / (1200.0 / NB)).astype(int) % NB
    for tau_s in TAUS:
        tau = max(1, int(round(tau_s / hop_s)))
        if b_all.size <= tau: return None
        M = np.zeros((NB, NB))
        np.add.at(M, (b_all[:-tau], b_all[tau:]), 1.0)
        M = gaussian_filter(M, sigma=1.0, mode='wrap')
        M = M ** 0.75
        s = M.sum()
        if s <= 0: return None
        parts.append((M / s).ravel())
    return np.concatenate(parts)


saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
saraga_pitch = {}
for tid in saraga.track_ids:
    t = saraga.track(tid)
    p = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
    if p is not None:
        saraga_pitch[tid] = p.frequencies

Xh, Xt, y_labels, track_ids = [], [], [], []
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
        t = tdms_multi(1200.0 * np.log2(v / tonic), hop)
        if t is None: continue
        for row in d['X']:
            Xh.append(row); Xt.append(t); y_labels.append(raga); track_ids.append(tid)
Xh = np.array(Xh); Xt = np.array(Xt); y_labels = np.array(y_labels); track_ids = np.array(track_ids)

MIN = 25                                             # <-- declared edit (was 20)
ntr = {r: len(set(track_ids[y_labels == r])) for r in set(y_labels)}
keep = {r for r, n in ntr.items() if n >= MIN}
m = np.isin(y_labels, list(keep))
Xhk, Xtk, yk, gk = Xh[m], Xt[m], y_labels[m], track_ids[m]
le = LabelEncoder(); yi = le.fit_transform(yk)
print(f'min>={MIN}: {len(keep)} ragas, {len(set(gk))} tracks', flush=True)


def run(tag, mk_t, mk_h=None, w=0.0):
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    t1 = t3 = ntot = 0
    for tr, te in cv.split(Xtk, yi, groups=gk):
        ct = mk_t(); ct.fit(Xtk[tr], yi[tr])
        proba = ct.predict_proba(Xtk[te])
        if mk_h is not None and w > 0:
            ch = mk_h(); ch.fit(Xhk[tr], yi[tr])
            proba = (1 - w) * proba + w * ch.predict_proba(Xhk[te])
        agg = defaultdict(list)
        for i, idx in enumerate(te): agg[gk[idx]].append(proba[i])
        for tid, ps in agg.items():
            mean = np.mean(ps, 0); true = yi[gk == tid][0]
            order = np.argsort(-mean); cs = ct.classes_
            t1 += cs[order[0]] == true; t3 += true in cs[order[:3]]; ntot += 1
    print(f'{tag:44s} top1={t1/ntot:.1%} top3={t3/ntot:.1%}  (n={ntot})', flush=True)


rf = lambda n=800: (lambda: RandomForestClassifier(n_estimators=n, max_features='sqrt', random_state=42, n_jobs=-1))
# --- end verbatim -----------------------------------------------------------

run('RF800 tdms + hist w=0.4  [the exported config]', rf(), rf(), 0.4)
run('RF800 tdms only          [reference]', rf())
