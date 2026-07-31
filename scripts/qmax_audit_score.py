"""Read the Qmax distance matrix out at each registered level of disjointness.

One matrix, four read-outs, no re-computation: see
`data/qmax_audit/PREREGISTRATION.md`, written before the first row of
`D_rows.npz` existed.

  (a)  as-originally-run  — `if j == i: continue`, nothing else
  (b)  recording-disjoint — + byte-identical melodia contours
  (c)  source-disjoint    — + same `archive_identifier`, + same artist
  (c') registered sensitivity on (c) — identifiers folded into families by
       `rapidfuzz.fuzz.ratio >= 85`, because one upload can carry two spellings

Ranking is verbatim from `evaluate_composition_external.py`: the top five
*tracks* by distance, and a hit is that the query's `work_key` appears among
their keys — not the top five distinct works.

Read-only. Writes `data/qmax_audit/external.json`.

Usage: venv_train/bin/python -u scripts/qmax_audit_score.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qmax_audit_protocol import build_protocol, fold  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'data' / 'qmax_audit'
FAMILY_RATIO = 85


def identifier_families(idents: set[str]) -> dict[str, str]:
    """Union spellings of one upload: 78RPM-Chittor-V-Nagaiah ~ 78RPM-ChittoorVNagaiah."""
    canon = sorted(idents)
    folded = {i: fold(i) for i in canon}
    parent = {i: i for i in canon}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a in range(len(canon)):
        for b in range(a + 1, len(canon)):
            ia, ib = canon[a], canon[b]
            if fuzz.ratio(folded[ia], folded[ib]) >= FAMILY_RATIO:
                ra, rb = find(ia), find(ib)
                if ra != rb:
                    parent[rb] = ra
    return {i: find(i) for i in canon}


def build_masks(P, prov):
    paths, keys, N, ev = P['paths'], P['keys'], P['N'], P['eval_idx']
    stems = [p.stem for p in paths]
    contour = [prov[s]['contour_sha1'] for s in stems]
    ident = [(prov[s]['archive_identifier'] or '') or None for s in stems]
    artist = [prov[s]['artist'] for s in stems]
    fam_of = identifier_families({i for i in ident if i})
    family = [fam_of.get(i) if i else None for i in ident]

    out = {}
    for lv in ('a', 'b', 'c', "c'"):
        M = np.ones((len(ev), N), dtype=bool)
        for k, i in enumerate(ev):
            M[k, i] = False
            for j in range(N):
                if lv != 'a' and contour[j] == contour[i]:
                    M[k, j] = False
                if lv in ('c', "c'"):
                    if ident[i] and ident[j] == ident[i]:
                        M[k, j] = False
                    if artist[i] and artist[j] == artist[i]:
                        M[k, j] = False
                if lv == "c'" and family[i] and family[j] == family[i]:
                    M[k, j] = False
        out[lv] = M
    n_fam = len(set(fam_of.values()))
    return out, dict(identifiers=len(fam_of), families=n_fam)


def score(P, D, masks):
    keys, N, ev = P['keys'], P['N'], P['eval_idx']
    res = {}
    for lv, M in masks.items():
        t1 = t5 = 0
        evaluable = []
        per_clip = []
        for k, i in enumerate(ev):
            cand = [j for j in range(N) if M[k, j] and np.isfinite(D[k, j])]
            npos = sum(1 for j in cand if keys[j] == keys[i])
            if npos == 0:
                continue
            evaluable.append(k)
            per_clip.append(npos / len(cand))
            order = sorted(cand, key=lambda j: D[k, j])
            ranked = [keys[j] for j in order[:5]]
            t1 += ranked[0] == keys[i]
            t5 += keys[i] in ranked
        n = len(evaluable)
        res[lv] = dict(
            n_evaluable=n, n_queries=len(ev),
            top1=int(t1), top5=int(t5),
            top1_pct=t1 / n if n else 0.0,
            top5_pct=t5 / n if n else 0.0,
            top1_pct_all60=t1 / len(ev),
            top5_pct_all60=t5 / len(ev),
            mean_refs=float(np.mean([int(masks[lv][k].sum()) for k in evaluable])) if n else 0.0,
            chance_top1=float(np.mean(per_clip)) if per_clip else 0.0,
        )
    return res


def main():
    prov = {r['stem']: r for r in json.loads((OUT_DIR / 'provenance.json').read_text())}
    P = build_protocol()
    D = np.load(OUT_DIR / 'D_rows.npz')['D']
    incomplete = [k for k in range(D.shape[0]) if np.isnan(D[k]).all()]
    if incomplete:
        raise SystemExit(f'matrix incomplete: {len(incomplete)} rows missing {incomplete}')

    masks, fam = build_masks(P, prov)
    res = score(P, D, masks)

    names = {'a': 'as-originally-run  (self index only)',
             'b': 'recording-disjoint (+byte-identical contour)',
             'c': 'source-disjoint    (+archive item, +artist)',
             "c'": "sensitivity        (+identifier family, ratio>=85)"}
    print(f"archive identifiers {fam['identifiers']} -> {fam['families']} families")
    print('\n=== EXTERNAL Qmax (archive concerts, melodia mix, W_REF=800) ===')
    for lv in ('a', 'b', 'c', "c'"):
        r = res[lv]
        print(f"  ({lv}) {names[lv]}")
        print(f"        n={r['n_evaluable']}/{r['n_queries']} evaluable, "
              f"mean refs {r['mean_refs']:.0f}, chance top-1 {r['chance_top1']:.4f}")
        print(f"        top1 {r['top1']}/{r['n_evaluable']} = {r['top1_pct']:.1%}"
              f"   (over all 60: {r['top1_pct_all60']:.1%})")
        print(f"        top5 {r['top5']}/{r['n_evaluable']} = {r['top5_pct']:.1%}"
              f"   (over all 60: {r['top5_pct_all60']:.1%})")

    (OUT_DIR / 'external.json').write_text(json.dumps(
        dict(families=fam, levels=res), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
