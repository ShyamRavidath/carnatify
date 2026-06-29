"""Precompute a self-contained pitch bundle for the Carnatify API.

Run this ONCE locally (where the full Saraga dataset + mirdata are available).
It serializes every usable Saraga track's pitch contour + tonic into a compact
``tracks_pitch.npz`` plus a ``tracks_meta.json`` index, so the deployed
HuggingFace Space needs neither mirdata nor the multi-GB raw dataset.

Mirrors the selection logic in ``app.py`` (_get_track_index / _load_pitch):
keep tracks that have pitch data AND a tonic; prefer the vocal pitch contour.

Usage
-----
    python backend/precompute_tracks.py [--data-home /path/to/repo]

Outputs (committed into the Space repo):
    backend/data/tracks_pitch.npz   – {track_id: float32 freq array}
    backend/data/tracks_meta.json   – [{track_id, title, tonic, raga}, ...]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

# Repo root = parent of this backend/ dir. Saraga dataset lives under it.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_OUT_DIR = Path(__file__).resolve().parent / "data"


def _track_title(meta: dict, fallback: str) -> str:
    work = meta.get("work") or []
    if work:
        return work[0]["title"]
    return meta.get("title", fallback)


def _track_raga(meta: dict) -> str:
    raaga_list = meta.get("raaga") or []
    if raaga_list:
        r = raaga_list[0]
        return r.get("common_name") or r.get("name", "")
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-home",
        default=str(_REPO_ROOT),
        help="mirdata data_home containing the saraga_carnatic dataset",
    )
    args = parser.parse_args()

    import mirdata

    saraga = mirdata.initialize("saraga_carnatic", data_home=args.data_home)

    arrays: dict[str, np.ndarray] = {}
    meta_index: list[dict] = []

    total = len(saraga.track_ids)
    for i, tid in enumerate(saraga.track_ids, 1):
        t = saraga.track(tid)

        has_pitch = bool(
            (t.pitch_path and Path(t.pitch_path).exists())
            or (t.pitch_vocal_path and Path(t.pitch_vocal_path).exists())
        )
        if not has_pitch or t.tonic is None:
            continue

        pv = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
        if pv is None:
            continue

        freqs = np.asarray(pv.frequencies, dtype=np.float32)
        meta = t.metadata or {}

        # npz keys must be valid kwarg identifiers; track_ids like "0_Dorakuna"
        # are not, so store under a stable index key and record it in the meta.
        key = f"t{len(meta_index)}"
        arrays[key] = freqs
        meta_index.append(
            {
                "track_id": tid,
                "key": key,
                "title": _track_title(meta, tid),
                "tonic": float(t.tonic),
                "raga": _track_raga(meta),
            }
        )
        if i % 25 == 0 or i == total:
            print(f"  scanned {i}/{total} · kept {len(meta_index)}")

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = _OUT_DIR / "tracks_pitch.npz"
    meta_path = _OUT_DIR / "tracks_meta.json"

    # Each track stored under its own key so loading one is cheap and lazy.
    np.savez_compressed(npz_path, **arrays)
    meta_path.write_text(json.dumps(meta_index, ensure_ascii=False, indent=2))

    size_mb = npz_path.stat().st_size / 1e6
    print(f"\nWrote {len(meta_index)} tracks")
    print(f"  {npz_path}  ({size_mb:.1f} MB)")
    print(f"  {meta_path}")


if __name__ == "__main__":
    main()
