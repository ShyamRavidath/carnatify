"""Duration curve, stage 2 — per-window multi-tau TDMS features.

One shard per duration under `data/raga_duration/` (gitignored). Resumable: a
shard that already exists is skipped.

**Trap 1, handled explicitly.** The raw melodia / Saraga contour is sliced on the
TIME axis first (`f[start:stop]` in original-hop frames), and the voiced filter
`(f > 0) & isfinite(f)` is applied to that slice afterwards. Each window
therefore has a known real duration and an *unknown* voiced-frame count, which
is the quantity this stage records. Taking "the first N voiced frames" instead
would give a window of unknown real duration and is exactly what is avoided.

**Trap 2, recorded and NOT repaired.** `tdms()` below is verbatim from
`scripts/raga_audit_levels.py`, which is verbatim from
`scratch_archive_0711/raga_final_eval.py`. It computes `tau` in frames of the
ORIGINAL hop and then applies it to the COMPACTED voiced array, so the nominal
0.1 / 0.15 / 0.25 s delays are only nominal — the true delay is
`tau_s / voicing_density`. Repairing this would change the frozen harness and
break comparability with `data/RAGA_CONTAMINATION_AUDIT.md`, so it is left
alone; the per-window voicing density is recorded here so the size of the
confound can be reported.

Windows per track per duration: K = 3 at random offsets (fractions drawn once in
`raga_duration_protocol.py` with `random_state=42` and reused at every duration,
so the arms are paired), plus 1 from-the-start window as a registered secondary.
Tracks shorter than the duration contribute their whole length once and are
flagged `short`.

Read-only. Nothing under `models/` is written.

Usage: venv/bin/python scripts/raga_duration_windows.py [--durations 30,60,...]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE_DIR = ROOT / 'data' / 'raga_v2_cache'
MEL_DIR = CACHE_DIR / 'melodia_full'
OUT_DIR = ROOT / 'data' / 'raga_duration'

TAUS = (0.1, 0.15, 0.25)
NB = 40
SIGMA = 1.0
ALPHA = 0.75
MIN_VOICED = 500          # the frozen harness's own track guard, reused per window
K_WINDOWS = 3


# --- verbatim from scripts/raga_audit_levels.py (itself verbatim from the
# --- archived harness). Do not modify: Trap 2 lives in here on purpose.
def tdms(v, hop_s, tau_s, nb, sigma, alpha):
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
# --- end verbatim -----------------------------------------------------------


def tdms_multi(cents, hop_s):
    parts = []
    for tau_s in TAUS:
        f = tdms(cents, hop_s, tau_s, NB, SIGMA, ALPHA)
        if f is None:
            return None
        parts.append(f)
    return np.concatenate(parts)


def load_contour(rec, saraga_pitch):
    if rec['src'] == 'archive_v3':
        return np.asarray(np.load(MEL_DIR / f"{rec['stem']}.npy"), dtype=np.float64)
    key = rec['tid'].replace('saraga__', '')
    full = saraga_pitch.get(key, saraga_pitch.get(rec['tid']))
    return np.asarray(full, dtype=np.float64)


def saraga_pitch_table():
    import mirdata
    saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
    out = {}
    for tid in saraga.track_ids:
        t = saraga.track(tid)
        p = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
        if p is not None:
            out[tid] = p.frequencies
    return out


def plan(rec, dur_s):
    """Raw-frame [start, stop) windows for one track at one duration.

    Returns (list of (kind, start, stop), short_flag). `dur_s is None` -> full.
    """
    n_raw, hop = rec['n_raw'], rec['hop']
    if dur_s is None:
        return [('full', 0, n_raw)], False
    need = int(round(dur_s / hop))
    if n_raw <= need:
        return [('short', 0, n_raw)], True
    room = n_raw - need
    wins = [('rand', int(round(u * room)), int(round(u * room)) + need)
            for u in rec['offsets'][:K_WINDOWS]]
    wins.append(('start', 0, need))
    return wins, False


def build_shard(recs, saraga_pitch, dur_s, label):
    feats, meta = [], []
    t0 = time.time()
    for n, rec in enumerate(recs):
        f = load_contour(rec, saraga_pitch)
        wins, short = plan(rec, dur_s)
        for kind, a, b in wins:
            seg = f[a:b]
            v = seg[(seg > 0) & np.isfinite(seg)]
            row = dict(stem=rec['stem'], tid=rec['tid'], raga=rec['raga'],
                       group_c=rec['group_c'], kind=kind, start=int(a), stop=int(b),
                       n_raw=int(b - a), n_voiced=int(v.size), short=bool(short),
                       real_s=float((b - a) * rec['hop']))
            if v.size < MIN_VOICED:
                row['ok'] = False
                row['drop'] = 'min_voiced'
                meta.append(row)
                continue
            feat = tdms_multi(1200.0 * np.log2(v / rec['tonic']), rec['hop'])
            if feat is None:
                row['ok'] = False
                row['drop'] = 'tdms_none'
                meta.append(row)
                continue
            row['ok'] = True
            row['drop'] = None
            row['findex'] = len(feats)
            feats.append(np.asarray(feat, dtype=np.float32))
            meta.append(row)
        if (n + 1) % 100 == 0:
            print(f'   {label}: {n + 1}/{len(recs)} tracks  {time.time() - t0:.0f}s',
                  flush=True)
    X = np.stack(feats) if feats else np.zeros((0, NB * NB * len(TAUS)), np.float32)
    return X, meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--durations', default='full,600,300,120,60,30')
    args = ap.parse_args()

    proto = json.loads((OUT_DIR / 'protocol.json').read_text())
    recs = proto['tracks']
    print(f"{len(recs)} tier tracks, {proto['level_c_groups']} level-(c) groups", flush=True)
    saraga_pitch = saraga_pitch_table()

    for tok in args.durations.split(','):
        label = tok.strip()
        out = OUT_DIR / f'tdms_{label}.npz'
        if out.exists():
            print(f'-- {label}: shard exists, skipping', flush=True)
            continue
        dur_s = None if label == 'full' else float(label)
        print(f'== building shard {label}', flush=True)
        X, meta = build_shard(recs, saraga_pitch, dur_s, label)
        np.savez_compressed(out, X=X, meta=np.array(json.dumps(meta)))
        nd = sum(1 for m in meta if not m['ok'])
        ns = sum(1 for m in meta if m['short'] and m['kind'] == 'short')
        print(f'   -> {out.name}: {X.shape[0]} scored, {nd} discarded, '
              f'{ns} short-track windows, {X.nbytes / 1e6:.0f} MB', flush=True)


if __name__ == '__main__':
    main()
