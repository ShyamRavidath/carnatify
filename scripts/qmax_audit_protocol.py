"""Replicate the original Qmax external-eval protocol exactly, then describe it.

`evaluate_composition_external.py` produced the "60.0% top-1" half of the
60-67% claim. This module rebuilds its exact state — same glob order, same
`work_key`, same chroma filter, same `np.random.default_rng(0)` draw of 500
distractors, same 60-query subsample — so that the audit measures the real
query set rather than a lookalike.

It then reports, WITHOUT running any Qmax, how many of those queries survive
each level of disjointness:

  (a) as-originally-run  — only `if j == i: continue`, i.e. index self-exclusion
  (b) recording-disjoint — also excludes any reference whose melodia contour is
      byte-identical to the query's (the corpus stores 110 redundant copies
      under `_rN` names, and `work_key` strips `_rN`, so those copies are
      counted as separate "renditions" of the same work)
  (c) source-disjoint    — also excludes any reference sharing the query's
      `archive_identifier`, and any sharing its artist where artist is known

A query is *evaluable* at a level only if at least one true positive survives
the mask; otherwise no ranking of the references can be correct and scoring it
would silently count a guaranteed miss.

Read-only. Writes `data/qmax_audit/protocol.json`.

Usage: venv_train/bin/python scripts/qmax_audit_protocol.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MEL_DIR = ROOT / 'data' / 'raga_v2_cache' / 'melodia_full'
OUT_DIR = ROOT / 'data' / 'qmax_audit'
PROVENANCE = OUT_DIR / 'provenance.json'

# --- verbatim from evaluate_composition_external.py -------------------------
DEC = 80
W_REF = 800
MAX_QUERIES = 60
NUM_PREFIX = re.compile(r'^\d{1,3}[\s._-]*')
REND_SUFFIX = re.compile(r'_r\d+$')


def fold(s):
    d = unicodedata.normalize('NFKD', s)
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())


def work_key(path):
    # archive__<raga>__<title stem>.npy
    parts = path.stem.split('__', 2)
    if len(parts) != 3:
        return None
    raga, stem = parts[1], parts[2]
    stem = REND_SUFFIX.sub('', stem)
    t = fold(NUM_PREFIX.sub('', stem))
    if len(t) < 6:
        return None
    return (t, fold(raga))


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
    return out if out.shape[0] >= 200 else None


def windows(c):
    n = c.shape[0]
    if n <= W_REF:
        return [c]
    starts = sorted({0, (n - W_REF) // 2, n - W_REF})
    return [c[s:s + W_REF] for s in starts]
# --- end verbatim -----------------------------------------------------------


def build_protocol():
    """Reproduce the original script's state up to `eval_idx`."""
    paths = sorted(MEL_DIR.glob('*.npy'))
    keys = [work_key(p) for p in paths]
    ok = [i for i, k in enumerate(keys) if k is not None]
    paths = [paths[i] for i in ok]
    keys = [keys[i] for i in ok]
    kc = Counter(keys)
    multi = {k for k, n in kc.items() if n >= 2}
    stage1 = dict(tracks=len(paths), works=len(kc), multi_works=len(multi),
                  multi_tracks=sum(kc[k] for k in multi))

    chromas = [chroma_from_pitch(np.load(p)) for p in paths]
    usable = [i for i, c in enumerate(chromas) if c is not None]
    paths = [paths[i] for i in usable]
    keys = [keys[i] for i in usable]
    chromas = [chromas[i] for i in usable]
    N = len(paths)
    kc = Counter(keys)

    rng = np.random.default_rng(0)
    multi_i = [i for i in range(N) if kc[keys[i]] >= 2]
    single_i = [i for i in range(N) if kc[keys[i]] == 1]
    keep_i = sorted(set(multi_i) | set(
        int(x) for x in rng.choice(single_i, min(500, len(single_i)), replace=False)))
    paths = [paths[i] for i in keep_i]
    keys = [keys[i] for i in keep_i]
    chromas = [chromas[i] for i in keep_i]
    N = len(paths)
    kc = Counter(keys)
    eval_idx = [i for i in range(N) if kc[keys[i]] >= 2]
    n_multi_before_subsample = len(eval_idx)
    if len(eval_idx) > MAX_QUERIES:
        eval_idx = list(int(x) for x in rng.choice(eval_idx, MAX_QUERIES, replace=False))
    return dict(paths=paths, keys=keys, chromas=chromas, N=N, kc=kc,
                eval_idx=eval_idx, stage1=stage1,
                n_multi_before_subsample=n_multi_before_subsample)


def masks(P, prov):
    """Per-level boolean reference masks: mask[level][k][j] = j is scoreable."""
    paths, keys, N, eval_idx = P['paths'], P['keys'], P['N'], P['eval_idx']
    stems = [p.stem for p in paths]
    contour = [prov[s]['contour_sha1'] for s in stems]
    ident = [(prov[s]['archive_identifier'] or '').lower() or None for s in stems]
    artist = [prov[s]['artist'] for s in stems]

    out = {}
    for level in ('a', 'b', 'c'):
        M = np.ones((len(eval_idx), N), dtype=bool)
        for k, i in enumerate(eval_idx):
            M[k, i] = False                                   # `if j == i: continue`
            if level in ('b', 'c'):
                for j in range(N):
                    if contour[j] == contour[i]:
                        M[k, j] = False
            if level == 'c':
                for j in range(N):
                    if ident[i] and ident[j] == ident[i]:
                        M[k, j] = False
                    if artist[i] and artist[j] == artist[i]:
                        M[k, j] = False
        out[level] = M
    return out


def describe(P, prov):
    keys, N, eval_idx = P['keys'], P['N'], P['eval_idx']
    M = masks(P, prov)
    rows = {}
    for level, mask in M.items():
        pos, refs, evaluable = [], [], []
        for k, i in enumerate(eval_idx):
            m = mask[k]
            npos = sum(1 for j in range(N) if m[j] and keys[j] == keys[i])
            nref = int(m.sum())
            pos.append(npos)
            refs.append(nref)
            if npos > 0:
                evaluable.append(k)
        # chance floor, the colab_coverhunter_rescore.py way: mean over CLIPS of
        # (positives available / references scored), not mean over songs.
        per_clip = [pos[k] / refs[k] for k in evaluable] if evaluable else []
        rows[level] = dict(
            queries=len(eval_idx),
            evaluable=len(evaluable),
            evaluable_idx=evaluable,
            mean_positives=float(np.mean([pos[k] for k in evaluable])) if evaluable else 0.0,
            mean_references=float(np.mean([refs[k] for k in evaluable])) if evaluable else 0.0,
            chance_top1=float(np.mean(per_clip)) if per_clip else 0.0,
        )
    return rows, M


def main():
    prov = {r['stem']: r for r in json.loads(PROVENANCE.read_text())}
    P = build_protocol()
    rows, _ = describe(P, prov)

    s = P['stage1']
    print('=== original protocol state, reproduced ===')
    print(f"  {s['tracks']} tracks, {s['works']} works, {s['multi_works']} "
          f"multi-rendition works ({s['multi_tracks']} tracks)")
    print(f"  after chroma filter + 500-distractor slim: N = {P['N']}")
    print(f"  multi-rendition tracks in kept set        : {P['n_multi_before_subsample']}")
    print(f"  queries after MAX_QUERIES subsample       : {len(P['eval_idx'])}")

    print('\n=== evaluable queries and chance floor by disjointness level ===')
    names = {'a': 'as-originally-run (self-index only)',
             'b': 'recording-disjoint (+ byte-identical contours)',
             'c': 'source-disjoint (+ archive item, + artist)'}
    for lv in 'abc':
        r = rows[lv]
        print(f"  ({lv}) {names[lv]}")
        print(f"        evaluable n = {r['evaluable']}/{r['queries']}   "
              f"mean positives {r['mean_positives']:.2f}   "
              f"mean refs {r['mean_references']:.0f}   "
              f"chance top-1 {r['chance_top1']:.4f}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {lv: {k: v for k, v in rows[lv].items() if k != 'evaluable_idx'}
               for lv in rows}
    payload['stage1'] = s
    payload['N'] = P['N']
    payload['eval_stems'] = [P['paths'][i].stem for i in P['eval_idx']]
    (OUT_DIR / 'protocol.json').write_text(json.dumps(payload, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
