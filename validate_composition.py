"""Leave-one-out validation of the composition matcher against saraga_carnatic.

Uses only the compositions that have 2+ renditions in the built catalog.
For each such track, temporarily excludes it from the catalog (leave-one-out)
and checks whether the correct composition title appears in the top-1 and top-5
results. Reports accuracy for both.

Run from project root (after running build_catalog.py):
    python validate_composition.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np

_CATALOG_NPZ = Path("models/composition_catalog.npz")
_CATALOG_META = Path("models/composition_catalog_meta.json")
_N_POINTS = 500  # must match composition_matcher._N_POINTS


def main() -> None:
    if not _CATALOG_NPZ.exists() or not _CATALOG_META.exists():
        print("ERROR: Catalog not found. Run build_catalog.py first.")
        sys.exit(1)

    data = np.load(str(_CATALOG_NPZ))
    contours = data["contours"].astype(np.float32)
    with open(_CATALOG_META) as f:
        meta = json.load(f)

    N = len(meta)
    assert contours.shape[0] == N, (
        f"Catalog shape mismatch: {contours.shape[0]} contours vs {N} meta entries"
    )
    print(f"Catalog: {N} tracks total")

    title_counts = Counter(m["title"] for m in meta)
    multi_titles = {t for t, c in title_counts.items() if c >= 2}
    print(f"Compositions with 2+ renditions in catalog: {len(multi_titles)}")

    multi_idx = [i for i, m in enumerate(meta) if m["title"] in multi_titles]
    print(f"Tracks to evaluate (leave-one-out): {len(multi_idx)}")
    print()

    if not multi_idx:
        print("No multi-rendition compositions found. Rebuild the catalog and retry.")
        sys.exit(1)

    col_title = 28
    col_id = 38
    header = (
        f"{'Title':<{col_title}} {'Track ID':<{col_id}}"
        f" {'Top1':>4}  {'Top5':>4}  {'Rank':>4}  Best match"
    )
    print(header)
    print("-" * (len(header) + 10))

    top1_hits = top5_hits = 0
    all_contig = contours.astype(np.float64)  # avoid repeated casting in loop

    for i in multi_idx:
        query = all_contig[i]
        target_title = meta[i]["title"]

        # Leave-one-out: compare against every other track
        mask = np.ones(N, dtype=bool)
        mask[i] = False
        others = all_contig[mask]
        others_meta = [meta[j] for j in range(N) if j != i]

        dists = np.linalg.norm(others - query, axis=1)
        sims = 1.0 / (1.0 + dists / _N_POINTS)
        ranked_idx = np.argsort(sims)[::-1]
        ranked_titles = [others_meta[r]["title"] for r in ranked_idx]

        top1_ok = ranked_titles[0] == target_title
        top5_ok = target_title in ranked_titles[:5]
        try:
            rank = ranked_titles.index(target_title) + 1
        except ValueError:
            rank = -1

        top1_hits += int(top1_ok)
        top5_hits += int(top5_ok)

        short_title = target_title[:col_title - 1]
        short_id = meta[i]["track_id"][:col_id - 1]
        best = ranked_titles[0][:22] if ranked_titles else "?"
        print(
            f"{short_title:<{col_title}} {short_id:<{col_id}}"
            f" {'OK' if top1_ok else '--':>4}"
            f"  {'OK' if top5_ok else '--':>4}"
            f"  {rank:>4}"
            f"  {best}"
        )

    total = len(multi_idx)
    print()
    print(f"Evaluated  : {total} tracks across {len(multi_titles)} compositions")
    print(f"Top-1 accuracy : {top1_hits}/{total} = {top1_hits / total:.1%}")
    print(f"Top-5 accuracy : {top5_hits}/{total} = {top5_hits / total:.1%}")


if __name__ == "__main__":
    main()
