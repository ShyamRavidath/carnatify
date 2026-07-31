"""Rebuild the uncommitted CV harness behind "72.8% top-1 / 84.7% top-3", and
describe the corpus at three levels of disjointness — without scoring anything.

`train_raga_v3_tdms.py` only fits and exports; the harness that produced the
number was never committed and survives as a docstring line and a `cv_note`
dated 2026-07-08. The *features* are fully reproducible, so this module rebuilds
the matrix from the committed constants — TAUS, NB, sigma 1.0, alpha 0.75,
FUSION_W_HIST 0.4, min_tracks 25, Rāgamālika dropped — by importing
`tdms_multi` and `canon` from the training script itself rather than
re-implementing them.

It then builds four `groups` vectors over the *same* rows. The levels differ in
nothing else — not the tier, not the fusion weight, not the RF, not the seed:

  (a) as-originally-run  — groups = track_id, one value per npz file, which is
      what `StratifiedGroupKFold` was given in 2026-07
  (b) recording-disjoint — archive tracks group on `contour_sha1`, collapsing
      byte-identical melodia contours (the corpus stores redundant `_rN` copies
      of one recording under several track_ids); Saraga keeps track_id
  (c) source-disjoint    — archive tracks group on `archive_identifier` (the
      concert upload), Saraga on its concert folder, and any two such groups
      sharing a known artist are merged
  (c') registered sensitivity, non-gating — (c) with archive identifiers first
      collapsed into fuzzy families (`raga_audit_families.py`)

Read-only: no model is fitted here, nothing under `models/` is touched.
Writes `data/raga_audit/protocol.json` and a TDMS feature cache.

Usage: venv/bin/python scripts/raga_audit_protocol.py
"""
from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from train_raga_v3_tdms import (  # noqa: E402  — the committed feature code, verbatim
    CACHE_DIR, MEL_DIR, MEL_HOP_S, SARAGA_HOP_S, canon, tdms_multi,
)

OUT_DIR = ROOT / 'data' / 'raga_audit'
PROVENANCE = ROOT / 'data' / 'qmax_audit' / 'provenance.json'
FAMILIES = OUT_DIR / 'ident_families.json'
TDMS_CACHE = OUT_DIR / 'tdms_cache.npz'

MIN_TRACKS = 25          # frozen on level-(a) track counts; NOT re-tunable
N_SPLITS = 5
LEVELS = ('a', 'b', 'c', 'c2')
LEVEL_NAMES = {
    'a': 'as-originally-run (groups = track_id)',
    'b': 'recording-disjoint (archive groups = contour sha1)',
    'c': 'source-disjoint (archive item / Saraga concert, + artist merge)',
    'c2': "(c') identifier-family disjoint — registered sensitivity",
}


def fold(s: str) -> str:
    d = unicodedata.normalize('NFKD', s)
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())


class DSU:
    def __init__(self):
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


# --------------------------------------------------------------------------
# Saraga side: pitch, concert folder, album artists
# --------------------------------------------------------------------------
def saraga_tables():
    import mirdata
    saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
    pitch, concert, artists = {}, {}, {}
    for tid in saraga.track_ids:
        t = saraga.track(tid)
        p = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
        if p is not None:
            pitch[tid] = p.frequencies
        # .../saraga1.5_carnatic/<concert folder>/<item folder>/<file>.mp3
        concert[tid] = Path(t.audio_path).parent.parent.name
        md = t.metadata or {}
        artists[tid] = sorted({fold(a['name']) for a in (md.get('album_artists') or [])
                               if a.get('name')})
    return pitch, concert, artists


# --------------------------------------------------------------------------
# The feature matrix, built exactly once
# --------------------------------------------------------------------------
def build_matrix():
    """Replay `train_raga_v3_tdms.main()`'s data assembly, in its own order."""
    saraga_pitch, saraga_concert, saraga_artists = saraga_tables()

    cache = {}
    if TDMS_CACHE.exists():
        z = np.load(TDMS_CACHE, allow_pickle=True)
        cache = {k: v for k, v in zip(z['stems'], z['feats'])}

    Xh, Xt, y_labels, track_ids, sources, stems = [], [], [], [], [], []
    skipped = Counter()
    new_cache: dict[str, np.ndarray] = {}
    for subdir in ('saraga_v3', 'archive_v3'):
        for p in sorted((CACHE_DIR / subdir).glob('*.npz')):
            d = np.load(p, allow_pickle=True)
            raga = canon(str(d['raga']))
            if raga == 'Rāgamālika':
                skipped['ragamalika'] += 1
                continue
            tid = str(d['track_id'])
            tonic = float(d['tonics'][0])
            if p.stem in cache:
                feat = cache[p.stem]
                if feat.size == 0:
                    feat = None
            elif subdir == 'archive_v3':
                mp = MEL_DIR / f'{p.stem}.npy'
                if not mp.exists():
                    skipped['no_melodia'] += 1
                    continue
                feat = tdms_multi(np.load(mp), tonic, MEL_HOP_S)
            else:
                key = tid.replace('saraga__', '')
                full = saraga_pitch.get(key, saraga_pitch.get(tid))
                if full is None:
                    skipped['no_saraga_pitch'] += 1
                    continue
                feat = tdms_multi(full, tonic, SARAGA_HOP_S)
            new_cache[p.stem] = (np.zeros(0, dtype=np.float32) if feat is None
                                 else np.asarray(feat, dtype=np.float32))
            if feat is None:
                skipped['tdms_none'] += 1
                continue
            for row in d['X']:
                Xh.append(row)
                Xt.append(feat)
                y_labels.append(raga)
                track_ids.append(tid)
                sources.append(subdir)
                stems.append(p.stem)

    if new_cache:
        merged = dict(cache)
        merged.update(new_cache)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        ks = sorted(merged)
        feats = np.empty(len(ks), dtype=object)
        for i, k in enumerate(ks):
            feats[i] = merged[k]
        np.savez_compressed(TDMS_CACHE, stems=np.array(ks), feats=feats)

    return dict(
        Xh=np.array(Xh), Xt=np.array(Xt, dtype=np.float64),
        y=np.array(y_labels), tid=np.array(track_ids),
        src=np.array(sources), stem=np.array(stems), skipped=dict(skipped),
        saraga_concert=saraga_concert, saraga_artists=saraga_artists,
    )


# --------------------------------------------------------------------------
# The four group vectors
# --------------------------------------------------------------------------
def build_groups(M):
    prov = {r['stem']: r for r in json.loads(PROVENANCE.read_text())}
    fam = json.loads(FAMILIES.read_text())['family_of'] if FAMILIES.exists() else {}
    tid, src, stem = M['tid'], M['src'], M['stem']
    concert, sar_art = M['saraga_concert'], M['saraga_artists']
    n = len(tid)

    g = {'a': list(tid)}

    # (b) recording-disjoint
    gb, unresolved_b = [], 0
    for i in range(n):
        if src[i] == 'archive_v3':
            r = prov.get(stem[i])
            if r and r.get('contour_sha1'):
                gb.append('sha1:' + r['contour_sha1'])
            else:
                unresolved_b += 1
                gb.append(str(tid[i]))
        else:
            gb.append(str(tid[i]))
    g['b'] = gb

    # (c) and (c') source-disjoint: node per upload/concert, then artist merge
    def source_nodes(use_family: bool):
        nodes, artists_of = [], defaultdict(set)
        unresolved = 0
        for i in range(n):
            if src[i] == 'archive_v3':
                r = prov.get(stem[i])
                ident = (r or {}).get('archive_identifier')
                if not ident:
                    unresolved += 1
                    node = 'item?:' + str(tid[i])
                else:
                    node = 'item:' + (fam.get(ident, ident) if use_family else ident)
                if r and r.get('artist'):
                    artists_of[node].add(fold(r['artist']))
            else:
                key = str(tid[i]).replace('saraga__', '')
                node = 'concert:' + concert.get(key, str(tid[i]))
                for a in sar_art.get(key, []):
                    artists_of[node].add(a)
            nodes.append(node)
        dsu = DSU()
        for node in set(nodes):
            dsu.find(node)
        by_artist = defaultdict(list)
        for node, arts in artists_of.items():
            for a in arts:
                by_artist[a].append(node)
        merges = 0
        for a, ns in by_artist.items():
            for other in ns[1:]:
                if dsu.find(ns[0]) != dsu.find(other):
                    merges += 1
                dsu.union(ns[0], other)
        return [dsu.find(x) for x in nodes], unresolved, merges

    g['c'], unresolved_c, merges_c = source_nodes(False)
    g['c2'], _, merges_c2 = source_nodes(True)
    return ({k: np.array(v) for k, v in g.items()},
            dict(unresolved_contour=unresolved_b, unresolved_identifier=unresolved_c,
                 artist_merges_c=merges_c, artist_merges_c2=merges_c2))


# --------------------------------------------------------------------------
# The frozen tier, and per-level n
# --------------------------------------------------------------------------
def frozen_tier(y, tid):
    """min_tracks >= 25 on LEVEL-(a) track counts. Frozen; never re-tuned."""
    ntr = {r: len(set(tid[y == r])) for r in set(y)}
    return sorted(r for r, k in ntr.items() if k >= MIN_TRACKS), ntr


def level_stats(y, groups, keep_ragas, n_splits=N_SPLITS):
    """n, surviving ragas, and both chance floors — before any score exists."""
    m = np.isin(y, keep_ragas)
    yk, gk = y[m], groups[m]
    per_raga = {r: len(set(gk[yk == r])) for r in keep_ragas}
    survivors = sorted(r for r in keep_ragas if per_raga[r] >= n_splits)
    dropped = sorted(r for r in keep_ragas if per_raga[r] < n_splits)

    ms = np.isin(y, survivors)
    ys, gs = y[ms], groups[ms]
    cnt = Counter(ys)
    tot = sum(cnt.values())
    prior = np.array([c / tot for c in cnt.values()]) if tot else np.array([0.0])
    return dict(
        ragas_in_tier=len(keep_ragas),
        ragas_surviving=len(survivors),
        ragas_dropped=dropped,
        groups_per_raga={r: per_raga[r] for r in keep_ragas},
        n_groups=len(set(gs)),
        n_tracks=None,                              # filled by the caller
        n_rows=int(ms.sum()),
        majority_class_rate=float(prior.max()),
        class_prior_expectation=float((prior ** 2).sum()),
        survivors=survivors,
    )


def main() -> None:
    M = build_matrix()
    y, tid = M['y'], M['tid']
    groups, notes = build_groups(M)
    keep, ntr = frozen_tier(y, tid)

    print('=== corpus assembled from the committed constants ===')
    print(f"  rows {len(y)}   tracks {len(set(tid))}   ragas {len(set(y))}")
    print(f"  skipped: {M['skipped']}")
    print(f"  provenance gaps: {notes}")
    print(f"\n=== frozen tier: min_tracks >= {MIN_TRACKS} on level-(a) track counts ===")
    print(f"  {len(keep)} ragas, {len(set(tid[np.isin(y, keep)]))} tracks, "
          f"{int(np.isin(y, keep).sum())} rows")

    out = {'levels': {}, 'notes': notes, 'skipped': M['skipped'],
           'tier': {'min_tracks': MIN_TRACKS, 'ragas': keep,
                    'track_counts': {r: ntr[r] for r in keep}}}
    print('\n=== n before the percentage, per level (no score computed yet) ===')
    for lv in LEVELS:
        st = level_stats(y, groups[lv], keep)
        mk = np.isin(y, st['survivors'])
        st['n_tracks'] = len(set(tid[mk]))
        out['levels'][lv] = st
        print(f"  ({lv}) {LEVEL_NAMES[lv]}")
        print(f"       tracks {st['n_tracks']}  groups {st['n_groups']}  "
              f"rows {st['n_rows']}  ragas {st['ragas_surviving']}/{st['ragas_in_tier']}"
              f"  dropped {len(st['ragas_dropped'])}")
        print(f"       majority-class {st['majority_class_rate']:.4f}   "
              f"class-prior expectation {st['class_prior_expectation']:.4f}")
        if st['ragas_dropped']:
            print(f"       dropped (<{N_SPLITS} groups): {', '.join(st['ragas_dropped'])}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'protocol.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nwrote {OUT_DIR / 'protocol.json'}")


if __name__ == '__main__':
    main()
