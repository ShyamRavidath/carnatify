"""Evaluate the production TalaAnalyzer against Saraga ground truth.

Walks ``saraga1.5_carnatic/`` for tracks that carry a ``taala`` label and an
mp3, beat-tracks a 90s excerpt from each, runs :class:`TalaAnalyzer`, and
scores the predicted name against the (diacritics-folded) ground truth.
Tracks with ``.sama-manual.txt`` cycle annotations also get a cycle-duration
sanity check (estimated vs median inter-sama interval).

Run from the repo root: ``./venv/bin/python evaluate_tala.py``

Measured 2026-07-01 over 170 tracks (adi 122, rupaka 25, misra chapu 16,
khanda chapu 7): 16.5% overall — the inter-beat-interval autocorrelation
finds sub-periods (median estimated cycle = 0.51x the true sama cycle).
An onset-envelope variant with octave-folded classes reached 32.9%. Both are
far below the 70% deploy bar and below the 72% majority-class baseline, so
tala stays out of the API. See HANDOFF.md section 2.2.
"""
from __future__ import annotations

import json
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
warnings.filterwarnings("ignore")

import librosa  # noqa: E402

from carnatify.ml.tala_analyzer import TalaAnalyzer  # noqa: E402
from carnatify.ml.tala_validator import normalize_tala_name  # noqa: E402

TARGET_TALAS = {"adi", "rupaka", "misra chapu", "khanda chapu"}
SARAGA_ROOT = Path(__file__).resolve().parent / "saraga1.5_carnatic"


def collect_tracks() -> list[tuple[Path, str, Path | None]]:
    """(mp3, canonical ground-truth tala, sama annotation path or None)."""
    tracks = []
    for meta_path in SARAGA_ROOT.rglob("*.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        taala = meta.get("taala")
        if isinstance(taala, list) and taala:
            name = taala[0].get("name") if isinstance(taala[0], dict) else taala[0]
        elif isinstance(taala, dict):
            name = taala.get("name")
        else:
            name = taala
        if not name:
            continue
        mp3s = list(meta_path.parent.glob("*.mp3"))
        if not mp3s:
            continue
        samas = list(meta_path.parent.glob("*.sama-manual.txt"))
        tracks.append((mp3s[0], normalize_tala_name(name), samas[0] if samas else None))
    return tracks


def main() -> None:
    tracks = [t for t in collect_tracks() if t[1] in TARGET_TALAS]
    print(f"{len(tracks)} tracks with a target tala label + audio")
    analyzer = TalaAnalyzer()

    results = []
    for i, (mp3, gt, sama_path) in enumerate(tracks, 1):
        try:
            y, sr = librosa.load(mp3, sr=22050, mono=True, offset=90.0, duration=90.0)
            if len(y) < sr * 30:  # short track: fall back to the start
                y, sr = librosa.load(mp3, sr=22050, mono=True, duration=90.0)
            _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            cycle = analyzer.estimate_cycle_length(beat_times)
            bpc = analyzer.estimate_beats_per_cycle(beat_times, cycle)
            name, _ = analyzer.classify_tala(bpc, cycle, analyzer.estimate_tempo(beat_times))
        except Exception as exc:
            results.append({"mp3": str(mp3), "gt": gt, "error": str(exc)})
            continue

        true_cycle = None
        if sama_path is not None:
            samas = np.loadtxt(sama_path, usecols=0, ndmin=1)
            if len(samas) > 2:
                true_cycle = float(np.median(np.diff(samas)))

        results.append({
            "mp3": str(mp3), "gt": gt,
            "pred": normalize_tala_name(name), "bpc": bpc,
            "cycle_est": round(cycle, 2),
            "cycle_true": round(true_cycle, 2) if true_cycle else None,
            "correct": normalize_tala_name(name) == gt,
        })
        if i % 40 == 0:
            print(f"...{i}/{len(tracks)}", flush=True)

    out = Path("tala_eval_results.json")
    out.write_text(json.dumps(results, indent=1))

    scored = [r for r in results if "error" not in r]
    print(f"\nevaluated {len(scored)} tracks, {len(results) - len(scored)} errors")
    print(f"overall accuracy: {np.mean([r['correct'] for r in scored]):.1%}")
    by_class = defaultdict(list)
    for r in scored:
        by_class[r["gt"]].append(r["correct"])
    for tala, hits in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tala:14s} n={len(hits):3d}  acc={np.mean(hits):.1%}")
    print("predicted distribution:", Counter(r["pred"] for r in scored))

    with_sama = [r for r in scored if r["cycle_true"]]
    if with_sama:
        ratios = [r["cycle_est"] / r["cycle_true"] for r in with_sama]
        print(f"cycle est/true (n={len(ratios)}): median={np.median(ratios):.2f}, "
              f"within ±20%: {np.mean([0.8 < x < 1.2 for x in ratios]):.1%}")
    print(f"\nper-track detail: {out}")


if __name__ == "__main__":
    main()
