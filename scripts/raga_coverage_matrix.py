"""The feature matrix and group vectors, built once and cached for both
follow-up jobs.

`raga_audit_levels.collect()` walks mirdata and 1,287 npz files and takes
~2.5 minutes; `build()` is another minute. Job A fits 75 forests and Job B fits
75 more, and neither has any reason to rebuild the matrix. This module builds it
through the **same code objects** that passed the reproduction gate — it imports
`collect` and `build` rather than reimplementing them — and caches the result.

Nothing here changes a feature, a constant or a group. The cache is keyed on
nothing because the inputs are frozen; delete the file to rebuild.

Read-only with respect to the audit: writes only
`data/raga_coverage/matrix.npz`, which is regenerable and is not committed
(~50 MB).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import raga_audit_levels as L  # noqa: E402  — the gated harness itself
import raga_audit_protocol as P  # noqa: E402

ROOT = HERE.parent
CACHE = ROOT / 'data' / 'raga_coverage' / 'matrix.npz'


def get(verbose: bool = True):
    """Returns (X, y, g_track, groups_c, ntr) with the level-(c) group vector."""
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        X, y, g, gc = z['X'], z['y'], z['g'], z['gc']
        if verbose:
            print(f'loaded cached matrix: {X.shape[0]} tracks, {X.shape[1]} features',
                  flush=True)
    else:
        tracks, concert, artists = L.collect()
        if verbose:
            print(f'{len(tracks)} tracks with full melody', flush=True)
        X, y, g, stem, src = L.build(tracks)
        Mt = dict(tid=g, src=src, stem=stem,
                  saraga_concert=concert, saraga_artists=artists)
        groups, notes = P.build_groups(Mt)
        gc = groups['c']
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(CACHE, X=X, y=y, g=g, gc=gc)
        if verbose:
            print(f'built and cached: {X.shape[0]} tracks, {X.shape[1]} features, '
                  f'provenance gaps {notes}', flush=True)
    ntr = {r: len(set(g[y == r])) for r in set(y)}
    return X, y, g, gc, ntr


def tier(ntr, min_tracks: int):
    """The frozen tier rule, on FULL level-(a) track counts. Never re-tuned."""
    return sorted(r for r, n in ntr.items() if n >= min_tracks)
