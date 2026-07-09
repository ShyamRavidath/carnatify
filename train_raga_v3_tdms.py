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

Exports (candidate only — does NOT overwrite models/raga_classifier.pkl):
  models/raga_v3_tdms_rf.pkl, models/raga_v3_hist_rf.pkl,
  models/raga_v3_label_encoder.pkl, models/raga_v3_meta.json

Usage: venv/bin/python train_raga_v3_tdms.py [--min-tracks 20]
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
    args = ap.parse_args()

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
    joblib.dump(rf_t, MODELS / 'raga_v3_tdms_rf.pkl')
    joblib.dump(rf_h, MODELS / 'raga_v3_hist_rf.pkl')
    joblib.dump(le, MODELS / 'raga_v3_label_encoder.pkl')
    (MODELS / 'raga_v3_meta.json').write_text(json.dumps({
        'taus_s': TAUS, 'n_bins': NB, 'sigma': 1.0, 'alpha': 0.75,
        'fusion_w_hist': FUSION_W_HIST, 'min_tracks': args.min_tracks,
        'ragas': list(le.classes_),
        'cv_note': 'grouped 5-fold track-level 2026-07-08: min>=25 72.8/84.7, min>=20 67.6/79.4',
    }, ensure_ascii=False, indent=2))
    print('exported models/raga_v3_* (candidate; production pkl untouched)')


if __name__ == '__main__':
    main()
