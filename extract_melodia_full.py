"""Full-track PredominantPitchMelodia contours for every archive concert mp3.

TDMS features from full-track melody beat the 65s-segment histogram baseline
(+3.4pt already at 65s); the published TDMS results use full recordings.
Melodia runs ~2x realtime on the mix — no Demucs needed.

Output: data/raga_v2_cache/melodia_full/<track_id>.npy (float32 f0 Hz at
44100/128 hop). track_id matches archive_v3 npz stems. Resume-safe, parallel.

Usage: venv_train/bin/python extract_melodia_full.py [--workers 6]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from multiprocessing import Pool

import numpy as np

ROOT = Path(__file__).parent
AUDIO_DIR = ROOT / "data" / "concert_audio"
OUT_DIR = ROOT / "data" / "raga_v2_cache" / "melodia_full"


def process(args: tuple[str, str]) -> str:
    mp3_path, out_path = args
    try:
        import essentia.standard as es
        y = es.MonoLoader(filename=mp3_path, sampleRate=44100)()
        if y.size < 44100 * 60:
            return "short"
        f0, _ = es.PredominantPitchMelodia(frameSize=2048, hopSize=128)(es.EqualLoudness()(y))
        np.save(out_path, f0.astype(np.float32))
        return "ok"
    except Exception as e:
        return f"fail: {e}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    jobs = []
    for raga_dir in sorted(AUDIO_DIR.iterdir()):
        if not raga_dir.is_dir():
            continue
        for mp3 in sorted(raga_dir.glob("*.mp3")):
            tid = f"archive__{raga_dir.name}__{mp3.stem}"
            out = OUT_DIR / f"{tid}.npy"
            if not out.exists():
                jobs.append((str(mp3), str(out)))
    print(f"{len(jobs)} tracks to extract", flush=True)

    n = {"ok": 0, "short": 0, "fail": 0}
    with Pool(args.workers) as pool:
        for k, res in enumerate(pool.imap_unordered(process, jobs), 1):
            key = res.split(":")[0] if res.startswith("fail") else res
            n[key] = n.get(key, 0) + 1
            if k % 25 == 0 or k == len(jobs):
                print(f"[{k}/{len(jobs)}] {n}", flush=True)
    print(f"MELODIA_DONE {n}", flush=True)


if __name__ == "__main__":
    main()
