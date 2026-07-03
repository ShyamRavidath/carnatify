"""Feature extraction for Model A (part 1): Saraga real-audio training pipeline.

Runs the ACTUAL production inference pipeline (Demucs vocal separation ->
librosa.pyin, via raga_v2_pipeline.process_track) over real Saraga Carnatic
audio, instead of using any pre-extracted pitch source. This closes the
train/inference domain mismatch that the original train_raga.py had (it
used CompMusic's own pitch extraction via mirdata's compmusic_raga.track.pitch).

CompMusic's raga-labeled 477-track dataset (compmusic_raga) does NOT have
its raw audio available locally or via mirdata's automated .download() --
audio access there requires an out-of-band request to the CompMusic/Dunya
team (pending). Saraga Carnatic is one of two real-audio sources used here
as a substitute -- see train_raga_v2_archive.py for the other (a
shankarkrish.blog/archive.org download pass), and train_raga_v2_evaluate.py
for how the two are combined. Saraga alone is smaller and sparser per-class
(184 labeled tracks over 96 ragas, most with 1-2 tracks) than compmusic_raga's
477 tracks over 40 ragas -- see train_raga_v2_compmusic.py for a
same-augmentation reference point built on the larger (but
pipeline-mismatched) CompMusic pitch data.

Must run under venv_train (isolated Python 3.11 env with demucs + pinned
torch==2.5.1/torchaudio==2.5.1 CPU wheels -- the project's main venv is
Python 3.14, which has no compatible torch/demucs wheels).

Per-track results are cached as individual .npz files under
data/raga_v2_cache/saraga/ so a long run can be safely interrupted and
resumed (already-cached track_ids are skipped).

Usage:
    venv_train/bin/python train_raga_v2_saraga.py [--limit N]
"""

from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

import mirdata

from raga_v2_pipeline import process_track

ROOT = Path(__file__).parent
# v3: correct tonic handling (annotated where available, essentia drone
# estimation otherwise). The old saraga/ cache used median-F0 tonics, which
# were within ±50 cents of true Sa only 10% of the time.
CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "saraga_v3"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--min-tracks-per-raga", type=int, default=2)
    args = parser.parse_args()

    ds = mirdata.initialize("saraga_carnatic", data_home=str(ROOT))
    tracks = ds.load_tracks()

    counts = Counter()
    candidates = []
    for tid, t in tracks.items():
        raagas = t.metadata.get("raaga", []) if t.metadata else []
        if not raagas or not t.audio_path:
            continue
        if not Path(t.audio_path).exists():
            continue
        name = raagas[0]["name"]
        counts[name] += 1
        tonic = None
        try:
            tonic = t.tonic  # annotated ground truth where the dataset has it
        except Exception:
            pass
        candidates.append((tid, name, t.audio_path, tonic))

    keep_ragas = {r for r, n in counts.items() if n >= args.min_tracks_per_raga}
    candidates = [c for c in candidates if c[1] in keep_ragas]
    print(f"Tracks with usable audio+raga: {sum(counts.values())}")
    print(f"Ragas with >= {args.min_tracks_per_raga} tracks: {len(keep_ragas)}  "
          f"({len(candidates)} tracks kept)")

    if args.limit:
        candidates = candidates[: args.limit]

    n_ok, n_skip, n_cached = 0, 0, 0
    t_start = time.time()
    for i, (tid, raga, audio_path, tonic) in enumerate(candidates, 1):
        try:
            result = process_track(tid, raga, audio_path, CACHE_DIR, tonic_hz=tonic)
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
