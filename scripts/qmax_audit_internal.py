"""Audit the internal (Saraga) half of the 60-67% Qmax claim.

Commit 7e9bc7e recorded "Internal (saraga, work-mbid identity, 194-track
catalog, LOO): min(pyin-vocal, melodia-mix) windowed Qmax = 66.7% top-1 /
76.7% top-5". `evaluate_composition_qmax.py` cannot be re-run: it reads
`comp_pitch_cache/` and `melodia_cache/`, neither of which exists any more.

What CAN be scored is a reconstruction. `models/qmax_catalog.npz` is committed
and contains, for each of 189 Saraga tracks, the chroma windows built by
`build_qmax_catalog.py` from `t.pitch_vocal` — the same pyin-vocal channel that
formed one arm of the original ensemble. The reconstruction therefore differs
from the original in three named ways, and its absolute number must not be
quoted as a reproduction of 66.7%:

  * one channel (pyin-vocal), not min(pyin-vocal, melodia-mix);
  * W_REF 800 with zero-padding of short tracks, not 1000 unpadded;
  * MIN_CHROMA 200, not 30.

What it does measure faithfully is the thing the audit asks about: the shape of
the query/reference relation, and how much of the score depends on a query
being scored against its own recording, own concert, or own artist.

Levels, matching `qmax_audit_protocol.py`:
  (a) self-index exclusion only, as the original did it
  (b) + any reference whose window stack is byte-identical to the query's
  (c) + any reference from the same Saraga concert or the same album artist

Read-only. Writes `data/qmax_audit/internal.json`.

Usage: caffeinate -i venv_train/bin/python -u scripts/qmax_audit_internal.py [--workers 8]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'data' / 'qmax_audit'

_STATE = None


def build_state():
    import mirdata
    meta = json.loads((ROOT / 'models' / 'qmax_catalog_meta.json').read_text())
    d = np.load(ROOT / 'models' / 'qmax_catalog.npz')
    W, wt = d['windows'], d['win_track']

    sar = [i for i, m in enumerate(meta) if m['track_id'].startswith('saraga__')]
    tid_of = {i: meta[i]['track_id'][len('saraga__'):] for i in sar}

    s = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
    info = {}
    for tid in s.track_ids:
        m = s.track(tid).metadata or {}
        work = m.get('work') or []
        conc = m.get('concert') or []
        arts = m.get('album_artists') or []
        info[tid] = dict(
            work_mbid=work[0].get('mbid') if work else None,
            title=work[0]['title'] if work else (m.get('title') or ''),
            concert=conc[0]['title'] if conc else None,
            artist=arts[0]['name'] if arts else None,
        )

    tracks = []
    for i in sar:
        tid = tid_of[i]
        nfo = info.get(tid)
        if not nfo or not nfo['work_mbid']:
            continue                       # original grouped on work_mbid
        w = W[wt == i]
        tracks.append(dict(
            cat_idx=i, tid=tid, wins=w,
            sha=hashlib.sha1(np.ascontiguousarray(w).tobytes()).hexdigest(),
            **nfo))
    N = len(tracks)
    wc = Counter(t['work_mbid'] for t in tracks)
    eval_idx = [k for k in range(N) if wc[tracks[k]['work_mbid']] >= 2]
    return dict(tracks=tracks, N=N, eval_idx=eval_idx, wc=wc)


def _init():
    global _STATE
    _STATE = build_state()


def _row(k: int):
    import essentia.standard as es
    ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1,
                                   binarizePercentile=0.095, oti=True)
    csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5,
                                 alignmentType='serra09', distanceType='asymmetric')
    T, N = _STATE['tracks'], _STATE['N']
    i = _STATE['eval_idx'][k]
    s = np.full(N, np.inf)
    for j in range(N):
        if j == i:
            continue
        best = np.inf
        for qa in T[i]['wins']:
            for rb in T[j]['wins']:
                try:
                    _, dd = csm(ccs(qa, rb))
                    if dd < best:
                        best = dd
                except Exception:
                    pass
        s[j] = best
    return k, s


def level_masks(st):
    T, N, ev = st['tracks'], st['N'], st['eval_idx']
    out = {}
    for lv in 'abc':
        M = np.ones((len(ev), N), dtype=bool)
        for k, i in enumerate(ev):
            M[k, i] = False
            for j in range(N):
                if lv in ('b', 'c') and T[j]['sha'] == T[i]['sha']:
                    M[k, j] = False
                if lv == 'c':
                    if T[i]['concert'] and T[j]['concert'] == T[i]['concert']:
                        M[k, j] = False
                    if T[i]['artist'] and T[j]['artist'] == T[i]['artist']:
                        M[k, j] = False
        out[lv] = M
    return out


def score(st, D, M):
    T, N, ev = st['tracks'], st['N'], st['eval_idx']
    res = {}
    for lv, mask in M.items():
        t1 = t5 = n = 0
        pos_over_ref = []
        for k, i in enumerate(ev):
            m = mask[k]
            cand = [j for j in range(N) if m[j] and np.isfinite(D[k, j])]
            npos = sum(1 for j in cand if T[j]['work_mbid'] == T[i]['work_mbid'])
            if npos == 0 or not cand:
                continue
            n += 1
            pos_over_ref.append(npos / len(cand))
            order = sorted(cand, key=lambda j: D[k, j])
            ranked = [T[j]['work_mbid'] for j in order[:5]]
            t1 += ranked[0] == T[i]['work_mbid']
            t5 += T[i]['work_mbid'] in ranked
        res[lv] = dict(n=n, top1=int(t1), top5=int(t5),
                       top1_pct=t1 / n if n else 0.0,
                       top5_pct=t5 / n if n else 0.0,
                       chance_top1=float(np.mean(pos_over_ref)) if pos_over_ref else 0.0)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()
    import essentia.standard as es
    assert es.ChromaCrossSimilarity and es.CoverSongSimilarity

    st = build_state()
    nq, N = len(st['eval_idx']), st['N']
    print(f'{N} Saraga tracks with a work_mbid, {nq} multi-rendition queries',
          flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ck = OUT_DIR / 'D_internal.npz'
    D = np.full((nq, N), np.nan)
    if ck.exists():
        D = np.load(ck)['D']
        assert D.shape == (nq, N)
    todo = [k for k in range(nq) if np.isnan(D[k]).all()]
    print(f'{nq - len(todo)} rows on disk, {len(todo)} to compute', flush=True)

    if todo:
        mp.set_start_method('fork', force=True)
        t0, done = time.time(), 0
        with mp.Pool(args.workers, initializer=_init) as pool:
            for k, s in pool.imap_unordered(_row, todo):
                D[k] = s
                done += 1
                np.savez_compressed(ck, D=D)
                el = time.time() - t0
                print(f'[{done}/{len(todo)}] row {k} ({el/60:.1f} min, '
                      f'{el/done*(len(todo)-done)/60:.1f} min left)', flush=True)

    M = level_masks(st)
    res = score(st, D, M)
    names = {'a': 'as-originally-run (self only)',
             'b': 'recording-disjoint (+identical window stacks)',
             'c': 'source-disjoint (+same concert, +same artist)'}
    print('\n=== INTERNAL (Saraga, pyin-vocal reconstruction) ===')
    for lv in 'abc':
        r = res[lv]
        print(f"  ({lv}) {names[lv]}")
        print(f"        n={r['n']}  top1={r['top1']}/{r['n']}={r['top1_pct']:.1%}  "
              f"top5={r['top5']}/{r['n']}={r['top5_pct']:.1%}  "
              f"chance top-1 {r['chance_top1']:.4f}")

    (OUT_DIR / 'internal.json').write_text(json.dumps(
        dict(N=N, queries=nq, levels=res), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
