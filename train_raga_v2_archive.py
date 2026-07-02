"""Feature extraction for Model A (part 2): shankarkrish.blog/archive.org
real-audio training pipeline.

Runs the same Demucs+pyin pipeline as train_raga_v2_saraga.py (via
raga_v2_pipeline.process_track), but over data/concert_audio/ -- the tracks
downloaded by download_concerts.py to grow the real, locally-available
raga-labeled audio pool beyond Saraga Carnatic's ~3 tracks/raga.

Must run under venv_train (isolated Python 3.11 env with demucs + pinned
torch==2.5.1/torchaudio==2.5.1 CPU wheels).

Per-track results are cached as individual .npz files under
data/raga_v2_cache/archive/ so a long run can be safely interrupted and
resumed (already-cached track_ids are skipped).

Usage:
    venv_train/bin/python train_raga_v2_archive.py [--limit N]
"""

from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

from raga_v2_pipeline import process_track

ROOT = Path(__file__).parent
AUDIO_DIR = ROOT / "data" / "concert_audio"
CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "archive"

# Forms, not ragas — a ragamalika moves through several ragas in one piece,
# so its tracks carry no single-raga label and would poison training.
EXCLUDED_LABELS = {"Rāgamālika"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    candidates = []
    counts = Counter()
    for raga_dir in sorted(AUDIO_DIR.iterdir()):
        if not raga_dir.is_dir() or raga_dir.name in EXCLUDED_LABELS:
            continue
        raga = raga_dir.name
        for mp3_path in sorted(raga_dir.glob("*.mp3")):
            track_id = f"archive__{raga}__{mp3_path.stem}"
            candidates.append((track_id, raga, str(mp3_path)))
            counts[raga] += 1

    print(f"Tracks found: {len(candidates)} across {len(counts)} ragas")

    if args.limit:
        candidates = candidates[: args.limit]

    n_ok, n_skip, n_cached = 0, 0, 0
    t_start = time.time()
    for i, (tid, raga, audio_path) in enumerate(candidates, 1):
        try:
            result = process_track(tid, raga, audio_path, CACHE_DIR)
        except Exception as exc:
            print(f"[{i}/{len(candidates)}] {tid} FAILED: {exc}")
            n_skip += 1
            continue
        if result is None:
            print(f"[{i}/{len(candidates)}] {tid} skipped (too short / unvoiced)")
            n_skip += 1
        elif result["status"] == "cached":
            n_cached += 1
        else:
            n_ok += 1
            elapsed = time.time() - t_start
            print(f"[{i}/{len(candidates)}] {tid} ({raga}) ok, "
                  f"{result['n_variants']} variants, {elapsed:.0f}s elapsed")

    print(f"\nDone. ok={n_ok} cached={n_cached} skipped={n_skip} "
          f"total_time={time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
