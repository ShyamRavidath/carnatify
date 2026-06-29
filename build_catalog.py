"""Build the composition reference catalog from saraga_carnatic.

Run from project root:
    python build_catalog.py [--extra-dir PATH]

The catalog is written to:
    models/composition_catalog.npz       (numpy contour array)
    models/composition_catalog_meta.json (titles, track IDs)

Adding new concert data later requires no code changes:
    1. Save pitch files as JSON ({"title": str, "tonic": float, "frequencies": [...]})
    2. Drop them in a folder
    3. python build_catalog.py --extra-dir /path/to/folder
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import mirdata
import numpy as np

from carnatify.ml.composition_matcher import build_catalog

_DATA_HOME = "/Users/shyamravidath/carnatify"


def _saraga_iter():
    """Yield (track_id, title, frequencies, tonic) for all usable saraga tracks."""
    saraga = mirdata.initialize("saraga_carnatic", data_home=_DATA_HOME)
    ids = saraga.track_ids
    total = len(ids)
    yielded = 0
    skipped = 0

    for i, tid in enumerate(ids, 1):
        print(f"\r  Loading [{i:>3}/{total}] {tid:<50}", end="", flush=True)
        t = saraga.track(tid)

        # prefer vocal pitch; fall back to overall mixed-source pitch
        pitch_obj = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
        tonic = t.tonic

        if pitch_obj is None or tonic is None:
            skipped += 1
            continue

        meta = t.metadata or {}
        work = meta.get("work") or []
        title = work[0]["title"] if work else meta.get("title", "")
        if not title:
            skipped += 1
            continue

        yielded += 1
        yield tid, title, pitch_obj.frequencies, float(tonic)

    print(f"\r  Saraga: {yielded} usable / {total} total ({skipped} skipped){' ' * 20}")


def _extra_dir_iter(extra_dir: Path):
    """Yield (track_id, title, frequencies, tonic) from JSON pitch files."""
    json_files = sorted(extra_dir.glob("*.json"))
    loaded = 0
    for p in json_files:
        try:
            with open(p) as f:
                obj = json.load(f)
            yield p.stem, str(obj["title"]), np.array(obj["frequencies"]), float(obj["tonic"])
            loaded += 1
        except Exception as exc:
            print(f"  [WARN] skipping {p.name}: {exc}")
    print(f"  Extra dir: {loaded}/{len(json_files)} files loaded")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Carnatify composition catalog")
    parser.add_argument(
        "--extra-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Folder of JSON pitch files ({title, tonic, frequencies}) to append",
    )
    args = parser.parse_args()

    print("Building composition catalog from saraga_carnatic …")

    def tracks_iter():
        yield from _saraga_iter()
        if args.extra_dir is not None:
            if not args.extra_dir.is_dir():
                print(f"[WARN] --extra-dir {args.extra_dir} is not a directory; skipping")
                return
            print(f"Loading extra pitch files from {args.extra_dir} …")
            yield from _extra_dir_iter(args.extra_dir)

    n = build_catalog(tracks_iter())

    print(f"\nDone. Indexed {n} tracks.")
    print("  → models/composition_catalog.npz")
    print("  → models/composition_catalog_meta.json")


if __name__ == "__main__":
    main()
