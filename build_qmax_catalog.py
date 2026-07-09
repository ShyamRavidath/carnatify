"""Build the Qmax composition catalog for sung-clip matching.

One entry per track that has a full-track melodia contour (archive) or
annotated vocal pitch (saraga). Stores per-track chroma windows (up to 3 x 800
frames) + metadata (work title, raga, source track id).

Output:
  models/qmax_catalog.npz         (windows: float32 [n_windows, 800, 12];
                                   win_track: int32 index into meta per window)
  models/qmax_catalog_meta.json   (per-track: track_id, title, raga)

Usage: venv/bin/python build_qmax_catalog.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'src'))
MEL_DIR = ROOT / 'data' / 'raga_v2_cache' / 'melodia_full'
MODELS = ROOT / 'models'
DEC = 80
W_REF = 800
MIN_CHROMA = 200

NUM_PREFIX = re.compile(r'^\d{1,3}[\s._-]*')
REND_SUFFIX = re.compile(r'_r\d+$')


def fold(s: str) -> str:
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())


def chroma_from_pitch(f: np.ndarray) -> np.ndarray | None:
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
    return out if out.shape[0] >= MIN_CHROMA else None


def pad_windows(c: np.ndarray) -> list[np.ndarray]:
    n = c.shape[0]
    if n <= W_REF:
        w = np.zeros((W_REF, 12), dtype=np.float32)
        w[:n] = c
        return [w]
    starts = sorted({0, (n - W_REF) // 2, n - W_REF})
    return [c[s:s + W_REF] for s in starts]


def main() -> None:
    windows, win_track, meta = [], [], []

    # archive tracks
    for p in sorted(MEL_DIR.glob('*.npy')):
        parts = p.stem.split('__', 2)
        if len(parts) != 3:
            continue
        raga, stem = parts[1], parts[2]
        title = NUM_PREFIX.sub('', REND_SUFFIX.sub('', stem)).strip()
        c = chroma_from_pitch(np.load(p))
        if c is None:
            continue
        ti = len(meta)
        meta.append({'track_id': p.stem, 'title': title, 'raga': raga})
        for w in pad_windows(c):
            windows.append(w)
            win_track.append(ti)

    # saraga tracks
    import mirdata
    saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
    for tid in saraga.track_ids:
        t = saraga.track(tid)
        pv = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
        if pv is None:
            continue
        m = t.metadata or {}
        work = m.get('work') or []
        title = work[0]['title'] if work else (m.get('title') or '')
        raaga = m.get('raaga') or []
        rname = raaga[0]['name'] if raaga else ''
        if not title:
            continue
        c = chroma_from_pitch(pv.frequencies)
        if c is None:
            continue
        ti = len(meta)
        meta.append({'track_id': f'saraga__{tid}', 'title': title, 'raga': rname})
        for w in pad_windows(c):
            windows.append(w)
            win_track.append(ti)

    W = np.stack(windows).astype(np.float32)
    np.savez_compressed(MODELS / 'qmax_catalog.npz',
                        windows=W, win_track=np.array(win_track, dtype=np.int32))
    (MODELS / 'qmax_catalog_meta.json').write_text(
        json.dumps(meta, ensure_ascii=False, indent=1))
    print(f'{len(meta)} tracks, {len(windows)} windows -> models/qmax_catalog.npz '
          f'({W.nbytes / 1e6:.0f} MB raw)')


if __name__ == '__main__':
    main()
