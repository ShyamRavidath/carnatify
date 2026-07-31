"""Duration curve, stage 1 — the corpus, the frozen tier, the inherited level-(c)
groups, and the WINDOW INVENTORY. Nothing is scored here and no model is fitted.

Everything in this module is derivable from set membership and contour lengths
alone, so it can be (and is) run before `data/raga_duration/PREREGISTRATION.md`
is committed.

Inherited unchanged from `data/RAGA_CONTAMINATION_AUDIT.md`:

  * the corpus assembly of `scripts/raga_audit_levels.py:collect()` — the same
    npz cache, the same `Rāgamālika` drop, the same `v.size < 500` track guard;
  * the tier, `min_tracks >= 25` on level-(a) track counts (18 ragas, 518
    tracks), frozen and never re-tuned;
  * the level-(c) source-disjoint group vector from
    `scripts/raga_audit_protocol.build_groups()` — archive item / Saraga concert,
    artist-merged. Every number in this job is source-disjoint; no level-(a)
    figure is ever reported.

Trap 1 is handled here: window offsets and lengths are expressed in RAW contour
frames, so a window is a real slice of the time axis. The voiced filter is
applied *after* slicing (in `raga_duration_windows.py`), and each window keeps
however many voiced frames it happens to contain.

Writes `data/raga_duration/protocol.json` (inventory, no features, no scores).

Usage: venv/bin/python scripts/raga_duration_protocol.py
"""
from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import raga_audit_protocol as P  # noqa: E402  — inherited group vectors

ROOT = HERE.parent
CACHE_DIR = ROOT / 'data' / 'raga_v2_cache'
MEL_DIR = CACHE_DIR / 'melodia_full'
OUT_DIR = ROOT / 'data' / 'raga_duration'

MEL_HOP_S = 128 / 44100
SARAGA_HOP_S = 0.0029024943310657597
MIN = 25                       # frozen tier, inherited
N_SPLITS = 5
SEED = 42
K_WINDOWS = 3                  # random-offset windows per track per duration
DURATIONS = (30, 60, 120, 300, 600)      # seconds; 'full' is the anchor
MIN_VOICED = 500               # the frozen harness's own guard, reused verbatim


def _fold(name: str) -> str:
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


_seen: dict[str, str] = {}
def canon(r: str) -> str:
    return _seen.setdefault(_fold(r), r)


def collect_raw():
    """`raga_audit_levels.collect()` but keeping the RAW contour, not the voiced
    compaction. Same order, same drops, same guard, so the tier is identical."""
    import mirdata
    saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
    saraga_pitch, concert, artists = {}, {}, {}
    for tid in saraga.track_ids:
        t = saraga.track(tid)
        p = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
        if p is not None:
            saraga_pitch[tid] = p.frequencies
        concert[tid] = Path(t.audio_path).parent.parent.name
        md = t.metadata or {}
        artists[tid] = sorted({P.fold(a['name']) for a in (md.get('album_artists') or [])
                               if a.get('name')})

    tracks = []
    for subdir in ('saraga_v3', 'archive_v3'):
        for p in sorted((CACHE_DIR / subdir).glob('*.npz')):
            d = np.load(p, allow_pickle=True)
            raga = canon(str(d['raga']))
            if raga == 'Rāgamālika':
                continue
            tid = str(d['track_id'])
            tonic = float(d['tonics'][0])
            full = None
            hop = MEL_HOP_S
            if subdir == 'archive_v3':
                mp = MEL_DIR / f'{p.stem}.npy'
                if mp.exists():
                    full = np.load(mp)
            else:
                key = tid.replace('saraga__', '')
                full = saraga_pitch.get(key, saraga_pitch.get(tid))
                hop = SARAGA_HOP_S
            if full is None:
                continue
            f = np.asarray(full, dtype=np.float64)
            v = f[(f > 0) & np.isfinite(f)]
            if v.size < 500 or tonic <= 0:
                continue
            tracks.append(dict(stem=p.stem, tid=tid, src=subdir, raga=raga,
                               tonic=tonic, hop=hop, n_raw=int(f.size),
                               n_voiced_full=int(v.size)))
    return tracks, concert, artists


def frozen_tier(tracks):
    ntr = Counter()
    seen = defaultdict(set)
    for t in tracks:
        seen[t['raga']].add(t['tid'])
    ntr = {r: len(s) for r, s in seen.items()}
    keep = sorted(r for r, n in ntr.items() if n >= MIN)
    return keep, ntr


def level_c_groups(tracks, concert, artists):
    M = dict(tid=np.array([t['tid'] for t in tracks]),
             src=np.array([t['src'] for t in tracks]),
             stem=np.array([t['stem'] for t in tracks]),
             saraga_concert=concert, saraga_artists=artists)
    groups, notes = P.build_groups(M)
    return groups['c'], notes


def offset_fractions(tracks, seed=SEED, k=K_WINDOWS):
    """Drawn ONCE, per track, and reused at every duration and in both
    conditions, so the arms are paired: window j of track i at 30 s and at 300 s
    start at the same *fraction* through the usable range."""
    rng = np.random.default_rng(seed)
    return {t['stem']: rng.random(k) for t in sorted(tracks, key=lambda t: t['stem'])}


def window_plan(track, dur_s, fracs):
    """Raw-frame [start, stop) windows. Trap 1: the slice is on the time axis."""
    n_raw, hop = track['n_raw'], track['hop']
    need = int(round(dur_s / hop))
    if n_raw <= need:
        return [(0, n_raw)], True            # whole track once; SHORT
    room = n_raw - need
    return [(int(round(u * room)), int(round(u * room)) + need) for u in fracs], False


def main() -> None:
    tracks, concert, artists = collect_raw()
    print(f'{len(tracks)} tracks with full melody', flush=True)
    keep, ntr = frozen_tier(tracks)
    print(f'min>={MIN}: {len(keep)} ragas, '
          f'{len({t["tid"] for t in tracks if t["raga"] in keep})} tracks', flush=True)

    gc, notes = level_c_groups(tracks, concert, artists)
    tier = [i for i, t in enumerate(tracks) if t['raga'] in keep]
    print(f'level-(c) groups over the tier: {len({gc[i] for i in tier})}   {notes}',
          flush=True)

    fracs = offset_fractions(tracks)

    inv = {}
    for dur in DURATIONS:
        n_short = 0
        lens = []
        for i in tier:
            wins, short = window_plan(tracks[i], dur, fracs[tracks[i]['stem']])
            n_short += short
            lens.append(sum(b - a for a, b in wins) / max(1, len(wins)) * tracks[i]['hop'])
        inv[str(dur)] = dict(n_tracks=len(tier), n_short=int(n_short),
                             n_windows=sum(1 if s else K_WINDOWS
                                           for s in [window_plan(tracks[i], dur,
                                                                 fracs[tracks[i]['stem']])[1]
                                                     for i in tier]),
                             mean_window_s=float(np.mean(lens)))
        print(f"  d={dur:4d}s  tracks {len(tier)}  shorter-than-d {n_short:3d}  "
              f"windows {inv[str(dur)]['n_windows']:4d}  "
              f"mean window {inv[str(dur)]['mean_window_s']:.1f}s", flush=True)

    tdur = np.array([tracks[i]['n_raw'] * tracks[i]['hop'] for i in tier])
    print(f'\ntrack duration over the tier: min {tdur.min():.0f}s  '
          f'p25 {np.percentile(tdur, 25):.0f}s  median {np.median(tdur):.0f}s  '
          f'p75 {np.percentile(tdur, 75):.0f}s  max {tdur.max():.0f}s  '
          f'total {tdur.sum() / 3600:.1f}h')
    dens = np.array([tracks[i]['n_voiced_full'] / tracks[i]['n_raw'] for i in tier])
    print(f'full-track voicing density: mean {dens.mean():.3f}  '
          f'median {np.median(dens):.3f}  min {dens.min():.3f}  max {dens.max():.3f}')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = dict(
        n_tracks_all=len(tracks), tier_ragas=keep, tier_n_tracks=len(tier),
        tier_track_counts={r: ntr[r] for r in keep},
        level_c_groups=len({gc[i] for i in tier}), group_notes=notes,
        durations=list(DURATIONS), k_windows=K_WINDOWS, seed=SEED,
        min_voiced=MIN_VOICED, inventory=inv,
        track_duration_s=dict(min=float(tdur.min()), p25=float(np.percentile(tdur, 25)),
                              median=float(np.median(tdur)),
                              p75=float(np.percentile(tdur, 75)), max=float(tdur.max()),
                              total_h=float(tdur.sum() / 3600)),
        full_track_voicing_density=dict(mean=float(dens.mean()),
                                        median=float(np.median(dens)),
                                        min=float(dens.min()), max=float(dens.max())),
        tracks=[dict(stem=tracks[i]['stem'], tid=tracks[i]['tid'], src=tracks[i]['src'],
                     raga=tracks[i]['raga'], tonic=tracks[i]['tonic'],
                     hop=tracks[i]['hop'], n_raw=tracks[i]['n_raw'],
                     n_voiced_full=tracks[i]['n_voiced_full'], group_c=str(gc[i]),
                     offsets=[float(u) for u in fracs[tracks[i]['stem']]])
                for i in tier],
    )
    (OUT_DIR / 'protocol.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nwrote {OUT_DIR / 'protocol.json'}")


if __name__ == '__main__':
    main()
