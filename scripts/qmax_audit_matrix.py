"""Compute the Qmax query x reference distance matrix ONCE, checkpointing rows.

The three disjointness levels of the audit differ only in which references a
query is allowed to be ranked against. The distances themselves are identical,
so the expensive part is paid once here and read out three times in
`qmax_audit_score.py`. No thresholds, no protocol variants: the per-pair
distance is exactly `evaluate_composition_external.py`'s

    for qa in wins[i][:2]:
        for rb in wins[j]:
            _, d = csm2(ccs2(qa, rb))
            best = min(best, d)

Rows are appended to `data/qmax_audit/D_rows.npz` as they finish, from the
first row — a long unattended run that writes its provenance at the end
produces nothing when it crashes at 95% (see HANDOFF.md §4, the duration
probe's `run_log.json`). Re-running resumes from whatever is on disk.

Read-only with respect to the pipeline. Writes only under `data/qmax_audit/`.

Usage: caffeinate -i venv_train/bin/python -u scripts/qmax_audit_matrix.py [--workers 8]
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qmax_audit_protocol import build_protocol, windows  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'qmax_audit' / 'D_rows.npz'

_P = None
_WINS = None


def _init():
    global _P, _WINS
    _P = build_protocol()
    _WINS = [windows(c) for c in _P['chromas']]


def _row(k: int) -> tuple[int, np.ndarray]:
    import essentia.standard as es
    ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1,
                                   binarizePercentile=0.095, oti=True)
    csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5,
                                 alignmentType='serra09', distanceType='asymmetric')
    i = _P['eval_idx'][k]
    N = _P['N']
    s = np.full(N, np.inf, dtype=np.float64)
    for j in range(N):
        if j == i:
            continue
        best = np.inf
        for qa in _WINS[i][:2]:
            for rb in _WINS[j]:
                try:
                    _, d = csm(ccs(qa, rb))
                    if d < best:
                        best = d
                except Exception:
                    pass
        s[j] = best
    return k, s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()

    # Step 0: import-check the whole inference path before spending anything.
    # The duration probe lost ~27 GPU-hours by verifying inputs but never
    # verifying that its scoring imports resolved.
    import essentia.standard as es
    assert es.ChromaCrossSimilarity and es.CoverSongSimilarity

    P = build_protocol()
    nq, N = len(P['eval_idx']), P['N']
    print(f'{nq} queries x {N} references', flush=True)

    D = np.full((nq, N), np.nan)
    if OUT.exists():
        D = np.load(OUT)['D']
        assert D.shape == (nq, N), f'checkpoint shape {D.shape} != {(nq, N)}'
    todo = [k for k in range(nq) if np.isnan(D[k]).all()]
    print(f'{nq - len(todo)} rows already on disk, {len(todo)} to compute', flush=True)
    if not todo:
        return

    mp.set_start_method('fork', force=True)
    t0 = time.time()
    done = 0
    with mp.Pool(args.workers, initializer=_init) as pool:
        for k, s in pool.imap_unordered(_row, todo):
            D[k] = s
            done += 1
            np.savez_compressed(OUT, D=D)          # checkpoint every row
            el = time.time() - t0
            # el/done is throughput across the whole pool, so this is already
            # parallelism-aware. It only over-states while the first wave is in
            # flight, because those `workers` rows all land at the same instant.
            eta = el / done * (len(todo) - done)
            print(f'[{done}/{len(todo)}] row {k} '
                  f'({el/60:.1f} min elapsed, ~{eta/60:.0f} min left)', flush=True)
    print(f'wrote {OUT}', flush=True)


if __name__ == '__main__':
    main()
