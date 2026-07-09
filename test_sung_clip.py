"""Identify raga + composition from a sung/hummed clip (the SoundHound test).

For each audio file (wav/mp3/m4a) in the given folder:
  melody (essentia Melodia) -> tonic (drone estimator + 12-rotation raga
  voting fallback) -> TDMS -> clip-trained raga RF -> top-8 raga gate ->
  Qmax against models/qmax_catalog.npz -> top-5 compositions.

Name files "<title>__<raga>.wav" (double underscore) to get automatic
right/wrong scoring; any other name just prints predictions.

Usage:
  venv_train/bin/python test_sung_clip.py ~/sung_tests/
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

import joblib
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).parent
MODELS = ROOT / 'models'
MEL_HOP_S = 128 / 44100
TAUS = (0.1, 0.15, 0.25)
NB = 40
DEC = 80
GATE_K = 8
PROBA_BLEND = 0.5


def fold(s: str) -> str:
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())


def tdms_multi(freqs, tonic, hop_s):
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


def chroma_from_pitch(f):
    f = np.asarray(f, dtype=np.float64)
    n = f.size // DEC
    if n < 30:
        return None
    fr = f[:n * DEC].reshape(n, DEC)
    out = np.zeros((n, 12), dtype=np.float32)
    valid = np.zeros(n, dtype=bool)
    for i in range(n):
        v = fr[i]
        v = v[(v > 0) & np.isfinite(v)]
        if v.size < DEC // 4:
            continue
        pc = np.mod(12.0 * np.log2(np.median(v) / 440.0), 12.0)
        b = int(round(pc)) % 12
        out[i, b] = 1.0
        out[i, (b + 1) % 12] = 0.3
        out[i, (b - 1) % 12] = 0.3
        valid[i] = True
    out = out[valid]
    return out if out.shape[0] >= 30 else None


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('usage: test_sung_clip.py <folder-with-audio>')
    folder = Path(sys.argv[1]).expanduser()
    files = sorted(p for p in folder.iterdir()
                   if p.suffix.lower() in ('.wav', '.mp3', '.m4a', '.flac', '.aiff'))
    if not files:
        sys.exit(f'no audio files in {folder}')

    import essentia.standard as es
    clf = joblib.load(MODELS / 'raga_clip_rf.pkl')
    cat = np.load(MODELS / 'qmax_catalog.npz')
    windows = cat['windows']
    win_track = cat['win_track']
    meta = json.loads((MODELS / 'qmax_catalog_meta.json').read_text())
    track_raga_f = [fold(m['raga']) for m in meta]
    ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1,
                                   binarizePercentile=0.095, oti=True)
    csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5,
                                 alignmentType='serra09', distanceType='asymmetric')
    melodia = es.PredominantPitchMelodia(frameSize=2048, hopSize=128)
    eq = es.EqualLoudness()

    comp1 = comp5 = raga1 = raga3 = n_truth = 0
    for path in files:
        print(f'\n=== {path.name} ===')
        y = es.MonoLoader(filename=str(path), sampleRate=44100)()
        if y.size < 44100 * 15:
            print('  too short (<15s), skipping')
            continue
        f0, _ = melodia(eq(y))
        voiced_s = (f0 > 0).sum() * MEL_HOP_S
        print(f'  {y.size/44100:.0f}s audio, {voiced_s:.0f}s voiced melody')
        if voiced_s < 10:
            print('  too little melody detected, skipping')
            continue

        # tonic: drone estimator, then 12-rotation raga-confidence voting
        tonic0 = None
        try:
            t_est = float(es.TonicIndianArtMusic()(y))
            if 80.0 <= t_est <= 400.0:
                tonic0 = t_est
        except Exception:
            pass
        cands = []
        base = tonic0 if tonic0 else 146.83  # D3 default center
        for k in range(12):
            t_k = base * (2.0 ** (k / 12.0))
            while t_k > 400.0:
                t_k /= 2.0
            while t_k < 80.0:
                t_k *= 2.0
            td = tdms_multi(f0, t_k, MEL_HOP_S)
            if td is None:
                continue
            proba = clf.predict_proba(td[None, :])[0]
            cands.append((float(proba.max()), t_k, proba))
        if not cands:
            print('  TDMS failed, skipping')
            continue
        conf, tonic, proba = max(cands, key=lambda x: x[0])
        src = 'drone+rot' if tonic0 else 'rotation-vote'
        print(f'  tonic {tonic:.1f} Hz ({src}, raga conf {conf:.2f})')

        order = np.argsort(-proba)
        top_ragas = [(clf.classes_[i], float(proba[i])) for i in order[:GATE_K]]
        print('  raga top-5: ' + ', '.join(f'{r} {p:.2f}' for r, p in top_ragas[:5]))
        gate = {fold(r) for r, _ in top_ragas}
        pmap = {fold(r): p for r, p in top_ragas}

        q = chroma_from_pitch(f0)
        if q is None:
            print('  chroma failed, skipping')
            continue
        gated = [wi for wi in range(len(win_track))
                 if track_raga_f[win_track[wi]] in gate]
        best_per_track: dict[int, float] = {}
        for wi in gated:
            try:
                _, d = csm(ccs(q, windows[wi]))
            except Exception:
                continue
            ti = int(win_track[wi])
            if d < best_per_track.get(ti, np.inf):
                best_per_track[ti] = d
        scored = sorted(best_per_track.items(),
                        key=lambda kv: kv[1] - PROBA_BLEND * pmap.get(track_raga_f[kv[0]], 0.0))
        # aggregate to distinct titles
        seen_titles, results = set(), []
        for ti, d in scored:
            tf = fold(meta[ti]['title'])
            if tf in seen_titles:
                continue
            seen_titles.add(tf)
            results.append((meta[ti]['title'], meta[ti]['raga'], d))
            if len(results) == 5:
                break
        print('  composition top-5:')
        for r, (title, raga, d) in enumerate(results, 1):
            print(f'    {r}. {title}  [{raga}]  (dist {d:.3f})')

        # scoring if ground truth in filename: "<title>__<raga>.<ext>"
        if '__' in path.stem:
            gt_title, gt_raga = path.stem.split('__', 1)
            n_truth += 1
            tfold = fold(gt_title)
            hit1 = results and fold(results[0][0]) == tfold
            hit5 = any(fold(t) == tfold for t, _, _ in results)
            rhit1 = fold(top_ragas[0][0]) == fold(gt_raga)
            rhit3 = any(fold(r) == fold(gt_raga) for r, _ in top_ragas[:3])
            comp1 += hit1; comp5 += hit5; raga1 += rhit1; raga3 += rhit3
            print(f'  TRUTH: {gt_title} [{gt_raga}] -> comp top1 {"OK" if hit1 else "--"} '
                  f'top5 {"OK" if hit5 else "--"} | raga top1 {"OK" if rhit1 else "--"} '
                  f'top3 {"OK" if rhit3 else "--"}')

    if n_truth:
        print(f'\n===== SCORE over {n_truth} labeled clips =====')
        print(f'composition top-1 {comp1}/{n_truth}  top-5 {comp5}/{n_truth}')
        print(f'raga        top-1 {raga1}/{n_truth}  top-3 {raga3}/{n_truth}')


if __name__ == '__main__':
    main()
