"""Train + export the v3 raga classifier candidate (TDMS + histogram fusion).

Features per track:
  * TDMS (time-delayed melody surface): 40x40 octave-folded pitch-class
    transition surfaces at tau = 0.1/0.15/0.25 s, gaussian-smoothed (sigma 1,
    wrap), power-compressed (alpha 0.75), L1-normalized — computed on the
    FULL-track melody (essentia PredominantPitchMelodia on the mix for archive
    tracks; annotated vocal pitch for Saraga), tonic-normalized with the same
    tonic as the production cache (annotated / essentia TonicIndianArtMusic).
  * The production 480-dim tonic-normalized pitch histograms (65s Demucs+pyin
    slices) — fused at predict time: P = 0.6 * P_tdms + 0.4 * P_hist.

Measured (grouped 5-fold, track-level, 2026-07-08, 1287 tracks):
  min>=25 tracks/raga: 18 ragas  top1 72.8%  top3 84.7%
  min>=20 tracks/raga: 32 ragas  top1 67.6%  top3 79.4%

**Both of those are TDMS-only figures at level (a), and BOTH ARE INFLATED as a
description of this fused model.** Corrected 2026-08-13 (`handoff.md` §2c-i,
which flagged this docstring by name). The level-(a) → level-(c) source-
disjointness penalty is tier-dependent — 0.6 pp at 18 classes but 3.5 pp at 32 —
so the `min>=20` line above overstates by about that much and must not be quoted.
The honest source-disjoint numbers, fused and track-level
(`data/RAGA_TIER_GRADUATION.md`):

  min>=25  18 ragas  top1 73.6%  top3 83.6%   expected hits/100 items  28.75
  min>=20  32 ragas  top1 65.6%  top3 76.3%   expected hits/100 items  39.12
  min>=10  54 ragas  top1 59.2%  top3 72.8%   expected hits/100 items  46.86

Accuracy falls with tier width and **expected correct answers per concert rises
anyway**, because coverage of the actual repertoire more than doubles. That is
the product-relevant reading and it is why `--min-tracks 10` is the graduated
configuration.

Exports (candidate only — does NOT overwrite models/raga_classifier.pkl):
  models/<prefix>_tdms_rf.pkl, models/<prefix>_hist_rf.pkl,
  models/<prefix>_label_encoder.pkl, models/<prefix>_meta.json

Usage: venv/bin/python train_raga_v3_tdms.py [--min-tracks 20] [--out-prefix raga_v3]
       venv/bin/python train_raga_v3_tdms.py --min-tracks 10 --out-prefix raga_v4
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

import joblib
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'src'))
CACHE_DIR = ROOT / 'data' / 'raga_v2_cache'
MEL_DIR = CACHE_DIR / 'melodia_full'
MODELS = ROOT / 'models'
MEL_HOP_S = 128 / 44100
SARAGA_HOP_S = 0.0029024943310657597
TAUS = (0.1, 0.15, 0.25)
NB = 40
FUSION_W_HIST = 0.4


def _fold(name: str) -> str:
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


_seen: dict[str, str] = {}
def canon(r: str) -> str:
    return _seen.setdefault(_fold(r), r)


def tdms_multi(freqs: np.ndarray, tonic: float, hop_s: float) -> np.ndarray | None:
    f = np.asarray(freqs, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 500 or tonic <= 0:
        return None
    cents = 1200.0 * np.log2(v / tonic)
    b = np.floor(np.mod(cents, 1200.0) / (1200.0 / NB)).astype(int) % NB
    parts = []
    for tau_s in TAUS:
        tau = max(1, int(round(tau_s / hop_s)))
        if b.size <= tau:
            return None
        M = np.zeros((NB, NB))
        np.add.at(M, (b[:-tau], b[tau:]), 1.0)
        M = gaussian_filter(M, sigma=1.0, mode='wrap')
        M = M ** 0.75
        s = M.sum()
        if s <= 0:
            return None
        parts.append((M / s).ravel())
    return np.concatenate(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-tracks', type=int, default=20)
    ap.add_argument('--out-prefix', default='raga_v3',
                    help='models/<prefix>_{tdms_rf,hist_rf,label_encoder}.pkl '
                         'and models/<prefix>_meta.json. Defaults to raga_v3 so '
                         'the bare command is unchanged; the graduated wide-tier '
                         'model is exported as raga_v4 precisely so that the '
                         'measurements which scored raga_v3 keep their provenance.')
    args = ap.parse_args()
    pfx = args.out_prefix

    import mirdata
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
            if raga == 'Rāgamālika':
                continue
            tid = str(d['track_id'])
            tonic = float(d['tonics'][0])
            if subdir == 'archive_v3':
                mp = MEL_DIR / f'{p.stem}.npy'
                if not mp.exists():
                    continue
                feat = tdms_multi(np.load(mp), tonic, MEL_HOP_S)
            else:
                key = tid.replace('saraga__', '')
                full = saraga_pitch.get(key, saraga_pitch.get(tid))
                if full is None:
                    continue
                feat = tdms_multi(full, tonic, SARAGA_HOP_S)
            if feat is None:
                continue
            for row in d['X']:
                Xh.append(row); Xt.append(feat); y_labels.append(raga); track_ids.append(tid)

    Xh = np.array(Xh); Xt = np.array(Xt)
    y_labels = np.array(y_labels); track_ids = np.array(track_ids)

    ntr = {r: len(set(track_ids[y_labels == r])) for r in set(y_labels)}
    keep = sorted(r for r, n in ntr.items() if n >= args.min_tracks)
    m = np.isin(y_labels, keep)
    Xhk, Xtk, yk = Xh[m], Xt[m], y_labels[m]
    le = LabelEncoder()
    yi = le.fit_transform(yk)
    print(f'training on {len(keep)} ragas, {len(set(track_ids[m]))} tracks, {len(yk)} samples')

    rf_t = RandomForestClassifier(n_estimators=800, max_features='sqrt', random_state=42, n_jobs=-1)
    rf_t.fit(Xtk, yi)
    rf_h = RandomForestClassifier(n_estimators=800, max_features='sqrt', random_state=42, n_jobs=-1)
    rf_h.fit(Xhk, yi)

    MODELS.mkdir(exist_ok=True)
    joblib.dump(rf_t, MODELS / f'{pfx}_tdms_rf.pkl')
    joblib.dump(rf_h, MODELS / f'{pfx}_hist_rf.pkl')
    joblib.dump(le, MODELS / f'{pfx}_label_encoder.pkl')

    # The honest, source-disjoint, FUSED, track-level numbers for this tier —
    # measured by scripts/raga_tier_score.py against
    # data/raga_tier/PREREGISTRATION.md and written up in
    # data/RAGA_TIER_GRADUATION.md. Keyed by tier so a retrain at any tier on
    # the registered grid describes itself correctly and none of them can drift
    # back to a level-(a) TDMS-only figure the way raga_v3's cv_note did.
    MEASURED = {
        25: dict(classes=18, top1=0.7355, top3=0.8359, coverage=0.3910,
                 expected_hits_per_100=28.75),
        20: dict(classes=32, top1=0.6562, top3=0.7627, coverage=0.5962,
                 expected_hits_per_100=39.12),
        10: dict(classes=54, top1=0.5918, top3=0.7278, coverage=0.7920,
                 expected_hits_per_100=46.86),
    }
    m = MEASURED.get(args.min_tracks)
    (MODELS / f'{pfx}_meta.json').write_text(json.dumps({
        'taus_s': TAUS, 'n_bins': NB, 'sigma': 1.0, 'alpha': 0.75,
        'fusion_w_hist': FUSION_W_HIST, 'min_tracks': args.min_tracks,
        'ragas': list(le.classes_),
        'measured': m,
        'measurement_protocol': (
            'FUSED (P = 0.6*P_tdms + 0.4*P_hist), track-level, level (c) '
            'SOURCE-DISJOINT, StratifiedGroupKFold(5, shuffle, seed 42) over '
            'archive-item / Saraga-concert groups with the artist merge. '
            'expected_hits_per_100 = repertoire coverage x top-1, where coverage '
            'is the share of the 3,009 canonical-raga-carrying programme items in '
            'data/scraped_compositions.json whose raga this tier can emit.'
        ) if m else None,
        'cv_note': (
            f'See "measured" above. Source: data/RAGA_TIER_GRADUATION.md, '
            f'registered at data/raga_tier/PREREGISTRATION.md, harness '
            f'scripts/raga_tier_score.py. '
            f'DO NOT substitute a level-(a) or TDMS-only figure here: the '
            f'level-(a) penalty is tier-dependent (0.6 pp at 18 classes, 3.5 pp '
            f'at 32, 4.7 pp at 54) and this is a fused model, so the old '
            f'"min>=25 72.8/84.7, min>=20 67.6/79.4" line was wrong on both '
            f'counts. That error is recorded in handoff.md §2c-i.'
            if m else
            f'min_tracks={args.min_tracks} is not on the measured grid '
            f'(10 / 20 / 25). No source-disjoint figure is available for this '
            f'tier and none may be borrowed from a neighbouring one — top-1 '
            f'falls about 13.8 pp per natural-log unit of class count.'
        ),
    }, ensure_ascii=False, indent=2))
    print(f'exported models/{pfx}_* (candidate; production pkl untouched)')
    if m:
        print(f"  measured (fused, level (c), track-level): top-1 {m['top1']:.1%}  "
              f"top-3 {m['top3']:.1%}  coverage {m['coverage']:.1%}  "
              f"expected hits/100 {m['expected_hits_per_100']}")
    else:
        print(f'  WARNING: min_tracks={args.min_tracks} is off the measured grid; '
              f'meta.json carries no accuracy figure, deliberately')


if __name__ == '__main__':
    main()
