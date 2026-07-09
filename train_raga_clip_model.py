"""Train + export the clip-domain raga classifier used for sung-clip gating.

TDMS features from 60s clips (8 random clips per track) of full-track melody.
Clip-trained matters: the full-track-trained model drops from 77% to 56% top-8
on 60s clips (measured 2026-07-09, evaluate_composition_shortclip.py).

Exports: models/raga_clip_rf.pkl, models/raga_clip_meta.json
Usage: venv/bin/python train_raga_clip_model.py [--min-tracks 10]
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

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'src'))
CACHE_DIR = ROOT / 'data' / 'raga_v2_cache'
MEL_DIR = CACHE_DIR / 'melodia_full'
MODELS = ROOT / 'models'
MEL_HOP_S = 128 / 44100
SARAGA_HOP_S = 0.0029024943310657597
TAUS = (0.1, 0.15, 0.25)
NB = 40
Q_SECS = 60.0
CLIPS_PER_TRACK = 8


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
    if v.size < 300 or tonic <= 0:
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
    ap.add_argument('--min-tracks', type=int, default=10)
    args = ap.parse_args()

    import mirdata
    saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
    saraga_pitch = {}
    for tid in saraga.track_ids:
        t = saraga.track(tid)
        p = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
        if p is not None:
            saraga_pitch[tid] = p.frequencies

    tracks = []  # (f0, hop, tonic, raga)
    for subdir in ('saraga_v3', 'archive_v3'):
        for p in sorted((CACHE_DIR / subdir).glob('*.npz')):
            d = np.load(p, allow_pickle=True)
            raga = canon(str(d['raga']))
            if raga == 'Rāgamālika':
                continue
            tonic = float(d['tonics'][0])
            if subdir == 'archive_v3':
                mp = MEL_DIR / f'{p.stem}.npy'
                if not mp.exists():
                    continue
                tracks.append((np.load(mp), MEL_HOP_S, tonic, raga))
            else:
                tid = str(d['track_id']).replace('saraga__', '')
                full = saraga_pitch.get(tid)
                if full is None:
                    continue
                tracks.append((full, SARAGA_HOP_S, tonic, raga))

    from collections import Counter
    rc = Counter(r for _, _, _, r in tracks)
    keep = {r for r, n in rc.items() if n >= args.min_tracks}
    tracks = [t for t in tracks if t[3] in keep]
    print(f'{len(tracks)} tracks, {len(keep)} ragas (min {args.min_tracks})')

    X, y = [], []
    for k, (f0, hop, tonic, raga) in enumerate(tracks):
        qf = int(Q_SECS / hop)
        rng = np.random.default_rng(k)
        for _ in range(CLIPS_PER_TRACK):
            if f0.size <= qf:
                clip = f0
            else:
                s0 = int(rng.uniform(0.02, 0.75) * (f0.size - qf))
                clip = f0[s0:s0 + qf]
            td = tdms_multi(clip, tonic, hop)
            if td is not None:
                X.append(td)
                y.append(raga)
    X = np.stack(X)
    print(f'{X.shape[0]} clip samples')

    clf = RandomForestClassifier(n_estimators=600, max_features='sqrt',
                                 random_state=42, n_jobs=-1)
    clf.fit(X, np.array(y))
    joblib.dump(clf, MODELS / 'raga_clip_rf.pkl')
    (MODELS / 'raga_clip_meta.json').write_text(json.dumps({
        'taus_s': TAUS, 'n_bins': NB, 'sigma': 1.0, 'alpha': 0.75,
        'clip_secs': Q_SECS, 'clips_per_track': CLIPS_PER_TRACK,
        'min_tracks': args.min_tracks, 'ragas': sorted(keep),
        'cv_note': '60s-clip top-8 gate 77.4% (grouped CV 2026-07-09)',
    }, ensure_ascii=False, indent=2))
    print('exported models/raga_clip_rf.pkl')


if __name__ == '__main__':
    main()
