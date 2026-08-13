"""PRIMARY ARM: the harness that actually produced 72.8% / 84.7%, at four levels
of disjointness.

`scratch_archive_0711/raga_final_eval.py` (commit `c1fca59`) is the harness. Run
verbatim it prints `min>=25 ragas=18 top1=72.8% top3=84.7%` and
`min>=20 ragas=32 top1=67.6% top3=79.4%` — both recorded tiers, both metrics,
exact. It is **multi-tau TDMS alone**, one feature row per track, no histogram
fusion; the `cv_note` on the *fused* exported model quotes it anyway, which is a
labelling error recorded in `data/RAGA_CONTAMINATION_AUDIT.md`.

This module is that harness with exactly one thing changed: the `groups=`
argument handed to `cv.split`. Everything else — the feature code, the tier
(`min_tracks >= 25` on level-(a) track counts, frozen), the forest
(`RandomForestClassifier(800, 'sqrt', random_state=42)`), the splitter
(`StratifiedGroupKFold(5, shuffle=True, random_state=42)`) and the read-out
(per-track posterior, `clf.classes_[argsort]`) — is byte-faithful to the
original.

  (a) groups = track_id            -> must print 72.8 / 84.7 or the rebuild fails
  (b) groups = contour sha1        (archive; Saraga keeps track_id)
  (c) groups = archive item / Saraga concert, artist-merged
  (c') groups = (c) with identifiers collapsed into fuzzy families

Read-only. Fits in memory; nothing under `models/` is written.
Writes `data/raga_audit/levels.json`.

Usage: venv/bin/python scripts/raga_audit_levels.py

2026-08-13 (`WORKHORSE_RAGA_COVERAGE_BRIEF.md`): the tier constant `MIN` is now
reachable from the command line as `--min-tracks`, which accepts a comma list so
several tiers can be scored off **one** feature matrix and **one** group vector
build. `MIN = 25` remains the default and bare
`venv/bin/python scripts/raga_audit_levels.py` is byte-identical in behaviour to
the version that produced `data/raga_audit/levels.json`. Nothing else moved: not
the features, not the taus, not the forest, not the splitter, not the seed, not
the level-(c) group construction.

Usage (coverage sweep):
  venv/bin/python scripts/raga_audit_levels.py --min-tracks 25,20,15,10 \
      --levels a,c --out-dir data/raga_coverage --per-track
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import raga_audit_protocol as P  # noqa: E402  — group vectors and level stats

ROOT = HERE.parent
CACHE_DIR = ROOT / 'data' / 'raga_v2_cache'
MEL_DIR = CACHE_DIR / 'melodia_full'
OUT_DIR = ROOT / 'data' / 'raga_audit'
MEL_HOP_S = 128 / 44100
SARAGA_HOP_S = 0.0029024943310657597
MIN = 25
N_SPLITS = 5
SEED = 42


# --- verbatim from scratch_archive_0711/raga_final_eval.py ------------------
def _fold(name):
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


_seen = {}
def canon(r): return _seen.setdefault(_fold(r), r)


def tdms(cents_bins_cache, key, v, hop_s, tau_s, nb, sigma, alpha):
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


def collect():
    """`raga_final_eval.py`'s `tracks` list, plus the npz stem and source dir
    (which it discards) so provenance can be joined for levels (b) and (c)."""
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
            tracks.append((1200.0 * np.log2(v / tonic), hop, raga, tid, p.stem, subdir))
    return tracks, concert, artists


def build(tracks, tau_list=(0.1, 0.15, 0.25), nb=40, sigma=1.0, alpha=0.75):
    """`raga_final_eval.build()`, carrying stem/source through the ok-mask."""
    F, okm = [], []
    for cents, hop, raga, tid, stem, src in tracks:
        parts, ok = [], True
        for tau_s in tau_list:
            f = tdms(None, None, cents, hop, tau_s, nb, sigma, alpha)
            if f is None: ok = False; break
            parts.append(f)
        F.append(np.concatenate(parts) if ok else None)
        okm.append(ok)
    okm = np.array(okm)
    X = np.stack([f for f in F if f is not None])
    y = np.array([t[2] for t in tracks])[okm]
    g = np.array([t[3] for t in tracks])[okm]
    stem = np.array([t[4] for t in tracks])[okm]
    src = np.array([t[5] for t in tracks])[okm]
    return X, y, g, stem, src


def run_cv(X, y, g_track, g_split, keep):
    """`raga_final_eval.run_cv`'s inner pass, with `groups=` swapped for a level.

    The tier `keep` is passed in, frozen on LEVEL-(a) track counts, so coarser
    grouping cannot re-tune it. Aggregation stays keyed on the TRACK, so the
    read-out is unchanged; only the fold assignment moves.
    """
    m = np.isin(y, keep)
    Xk, yk, gk, gs = X[m], y[m], g_track[m], g_split[m]
    le = LabelEncoder(); yi = le.fit_transform(yk)
    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    t1 = t3 = ntot = 0
    correct1, correct3, fold_of = {}, {}, {}
    for k, (tr, te) in enumerate(cv.split(Xk, yi, groups=gs)):
        clf = RandomForestClassifier(n_estimators=800, max_features='sqrt',
                                     random_state=SEED, n_jobs=-1)
        clf.fit(Xk[tr], yi[tr])
        proba = clf.predict_proba(Xk[te])
        agg = defaultdict(list)
        for i, idx in enumerate(te): agg[gk[idx]].append(proba[i])
        for tid, ps in agg.items():
            mean = np.mean(ps, 0); true = yi[gk == tid][0]
            order = np.argsort(-mean); cs = clf.classes_
            h1 = bool(cs[order[0]] == true); h3 = bool(true in cs[order[:3]])
            t1 += h1; t3 += h3; ntot += 1
            correct1[tid] = h1; correct3[tid] = h3; fold_of[tid] = k
    cnt = Counter(yk); tot = sum(cnt.values())
    prior = np.array([c / tot for c in cnt.values()])
    label_of = {tid: yk[gk == tid][0] for tid in correct1}
    group_of = {tid: gs[gk == tid][0] for tid in correct1}
    return dict(
        n_ragas=len(le.classes_), n_tracks=ntot, n_groups=int(len(set(gs))),
        n_folds=len(set(fold_of.values())),
        top1=int(t1), top3=int(t3),
        top1_rate=t1 / ntot, top3_rate=t3 / ntot,
        majority_class_rate=float(prior.max()),
        class_prior_expectation=float((prior ** 2).sum()),
        correct1=correct1, correct3=correct3, label_of=label_of, group_of=group_of,
    )


def inventory(y, g, groups, keep, levels):
    """Everything derivable from set membership alone — no fold is scored here.

    Exists so a preregistration can state n, the floors and the per-class group
    counts of a tier *before* that tier's first `RandomForestClassifier` is fit.
    """
    m = np.isin(y, keep)
    yk = y[m]
    cnt = Counter(yk)
    tot = sum(cnt.values())
    prior = np.array([c / tot for c in cnt.values()])
    inv = dict(
        n_ragas=len(keep), n_tracks=int(len(set(g[m]))), n_rows=int(m.sum()),
        majority_class_rate=float(prior.max()),
        class_prior_expectation=float((prior ** 2).sum()),
        track_counts={r: int(cnt[r]) for r in keep},
        levels={},
    )
    for lv in levels:
        gl = groups[lv][m]
        per_raga = {r: int(len(set(gl[yk == r]))) for r in keep}
        inv['levels'][lv] = dict(
            n_groups=int(len(set(gl))),
            groups_per_raga=per_raga,
            min_groups_per_raga=int(min(per_raga.values())),
            ragas_below_n_splits=sorted(r for r, k in per_raga.items() if k < N_SPLITS),
        )
    return inv


def score_tier(X, y, g, groups, keep, min_tracks, ntr, notes, levels, per_track):
    """One tier, scored at each requested level. Returns (out, res)."""
    print(f'\n===== min>={min_tracks}: {len(keep)} ragas, '
          f'{len(set(g[np.isin(y, keep)]))} tracks =====', flush=True)

    out = {'tier': {'min_tracks': min_tracks, 'ragas': keep,
                    'track_counts': {r: ntr[r] for r in keep}},
           'notes': notes, 'levels': {}}
    res = {}
    for lv in levels:
        r = run_cv(X, y, g, groups[lv], keep)
        res[lv] = r
        print(f"({lv}) {P.LEVEL_NAMES[lv]}", flush=True)
        print(f"     n: tracks {r['n_tracks']}  groups {r['n_groups']}  "
              f"ragas {r['n_ragas']}  folds {r['n_folds']}", flush=True)
        print(f"     floors: majority {r['majority_class_rate']:.4f}  "
              f"class-prior {r['class_prior_expectation']:.4f}", flush=True)
        print(f"     top1={r['top1']}/{r['n_tracks']} = {r['top1_rate']:.1%}   "
              f"top3={r['top3']}/{r['n_tracks']} = {r['top3_rate']:.1%}", flush=True)

    # --- the reproduction gate, checked explicitly -------------------------
    # Only the recorded tier has a recorded number to reproduce. At any other
    # tier there is nothing to gate on and claiming a gate would be a lie.
    gate = None
    if min_tracks == 25 and 'a' in res:
        a = res['a']
        gate = (abs(a['top1_rate'] * 100 - 72.8) < 0.05
                and abs(a['top3_rate'] * 100 - 84.7) < 0.05)
        print(f"\nREPRODUCTION GATE: level (a) = {a['top1_rate']:.1%} / {a['top3_rate']:.1%} "
              f"vs recorded 72.8% / 84.7%  ->  {'EXACT' if gate else 'MISMATCH'}", flush=True)
        print(f"                   {a['top1']}/{a['n_tracks']} = {a['top1_rate']:.3%}"
              f"      {a['top3']}/{a['n_tracks']} = {a['top3_rate']:.3%}", flush=True)
        if 'c' in res:
            cc = res['c']
            cgate = (abs(cc['top1_rate'] * 100 - 72.2) < 0.05
                     and abs(cc['top3_rate'] * 100 - 84.0) < 0.05)
            print(f"REPRODUCTION GATE: level (c) = {cc['top1_rate']:.1%} / "
                  f"{cc['top3_rate']:.1%} vs recorded 72.2% / 84.0%  ->  "
                  f"{'EXACT' if cgate else 'MISMATCH'}", flush=True)
            print(f"                   {cc['top1']}/{cc['n_tracks']} = {cc['top1_rate']:.3%}"
                  f"      {cc['top3']}/{cc['n_tracks']} = {cc['top3_rate']:.3%}", flush=True)
            gate = bool(gate and cgate)

    # --- per-raga at level (c), and the a->c flip table --------------------
    c = res['c']
    per_raga = {}
    for r in keep:
        ts = [t for t, lab in c['label_of'].items() if lab == r]
        if not ts:
            continue
        d = dict(n_tracks=len(ts))
        if 'a' in res:
            d['top1_a'] = float(np.mean([res['a']['correct1'][t] for t in ts]))
        d['top1_c'] = float(np.mean([c['correct1'][t] for t in ts]))
        d['top3_c'] = float(np.mean([c['correct3'][t] for t in ts]))
        per_raga[r] = d

    # exposure: does a track share its level-(c) source with a SAME-RAGA sibling?
    m = np.isin(y, keep)
    gk, gc, yk = g[m], groups['c'][m], y[m]
    by_src = defaultdict(list)
    for t, s, lab in zip(gk, gc, yk):
        by_src[s].append((t, lab))
    clustered = set()
    for s, members in by_src.items():
        lc = Counter(lab for _, lab in members)
        for t, lab in members:
            if lc[lab] > 1:
                clustered.add(t)
    expo = {}
    if 'a' in res:
        for name, sel in (('clustered', clustered),
                          ('solo', set(c['correct1']) - clustered)):
            if not sel:
                continue
            expo[name] = dict(
                n=len(sel),
                top1_a=float(np.mean([res['a']['correct1'][t] for t in sel])),
                top1_c=float(np.mean([c['correct1'][t] for t in sel])),
            )
        print('\nsame-raga-in-one-source exposure (the mechanism the brief flagged):')
        for k, v in expo.items():
            print(f"  {k:10s} n={v['n']:3d}   (a) {v['top1_a']:.1%}  ->  (c) {v['top1_c']:.1%}"
                  f"   delta {100 * (v['top1_c'] - v['top1_a']):+.1f}pp")

    for lv, r in res.items():
        out['levels'][lv] = {k: v for k, v in r.items()
                             if k not in ('correct1', 'correct3', 'label_of', 'group_of')}
    out['gate_exact'] = bool(gate)
    out['per_raga_level_c'] = per_raga
    out['exposure'] = expo
    if 'a' in res:
        out['flips_a_to_c'] = sorted(t for t in res['a']['correct1']
                                     if res['a']['correct1'][t] and not c['correct1'][t])
        out['gains_a_to_c'] = sorted(t for t in res['a']['correct1']
                                     if not res['a']['correct1'][t] and c['correct1'][t])
    if per_track:
        out['per_track'] = {lv: dict(correct1={k: bool(v) for k, v in r['correct1'].items()},
                                     correct3={k: bool(v) for k, v in r['correct3'].items()},
                                     label_of={k: str(v) for k, v in r['label_of'].items()},
                                     group_of={k: str(v) for k, v in r['group_of'].items()})
                            for lv, r in res.items()}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--min-tracks', default=str(MIN),
                    help='comma-separated tier thresholds on LEVEL-(a) track '
                         f'counts; default {MIN} = the frozen historical tier')
    ap.add_argument('--levels', default=','.join(P.LEVELS),
                    help='comma-separated disjointness levels to score')
    ap.add_argument('--out-dir', default=str(OUT_DIR))
    ap.add_argument('--out-name', default=None,
                    help="output filename; default 'levels.json' for a single "
                         "tier, 'levels_min<N>.json' when several are swept")
    ap.add_argument('--per-track', action='store_true',
                    help='carry per-track correctness into the json (needed to '
                         'pair tiers at the track level)')
    ap.add_argument('--inventory-only', action='store_true',
                    help='n, floors and group counts per tier; fits nothing')
    args = ap.parse_args()

    mins = [int(s) for s in args.min_tracks.split(',') if s.strip()]
    levels = [s.strip() for s in args.levels.split(',') if s.strip()]
    for lv in levels:
        if lv not in P.LEVELS:
            raise SystemExit(f'unknown level {lv!r}; known: {P.LEVELS}')
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    # ---- built ONCE, shared by every tier --------------------------------
    tracks, concert, artists = collect()
    print(f'{len(tracks)} tracks with full melody', flush=True)
    X, y, g, stem, src = build(tracks)

    Mt = dict(tid=g, src=src, stem=stem, saraga_concert=concert, saraga_artists=artists)
    groups, notes = P.build_groups(Mt)

    ntr = {r: len(set(g[y == r])) for r in set(y)}

    if args.inventory_only:
        inv = {'notes': notes, 'n_tracks_total': int(len(set(g))),
               'n_ragas_total': int(len(set(y))), 'tiers': {}}
        for mt in mins:
            keep = sorted(r for r, n in ntr.items() if n >= mt)
            st = inventory(y, g, groups, keep, levels)
            st['ragas'] = keep
            inv['tiers'][str(mt)] = st
            print(f"\nmin>={mt}: {st['n_ragas']} ragas, {st['n_tracks']} tracks", flush=True)
            print(f"  floors: majority {st['majority_class_rate']:.4f}  "
                  f"class-prior {st['class_prior_expectation']:.4f}", flush=True)
            for lv in levels:
                L = st['levels'][lv]
                print(f"  ({lv}) groups {L['n_groups']}   min groups/raga "
                      f"{L['min_groups_per_raga']}   ragas with <{N_SPLITS} groups "
                      f"{len(L['ragas_below_n_splits'])}", flush=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / (args.out_name or 'inventory.json')
        p.write_text(json.dumps(inv, ensure_ascii=False, indent=1))
        print(f'\nwrote {p}')
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    for mt in mins:
        keep = sorted(r for r, n in ntr.items() if n >= mt)   # FROZEN on level (a)
        out = score_tier(X, y, g, groups, keep, mt, ntr, notes, levels, args.per_track)
        if args.out_name:
            name = args.out_name if len(mins) == 1 else f'{Path(args.out_name).stem}_min{mt}.json'
        else:
            name = 'levels.json' if len(mins) == 1 and mt == MIN else f'levels_min{mt}.json'
        p = out_dir / name
        # written after EVERY tier, never at the end, so a session limit is survivable
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(f'\nwrote {p}', flush=True)


if __name__ == '__main__':
    main()
