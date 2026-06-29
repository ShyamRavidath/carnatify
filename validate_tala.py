"""Validate detect_tala() against saraga_carnatic ground-truth annotations.

Filters tracks that have both sama beat annotations and a tempo dict with a
populated beats_per_cycle value, then compares detect_tala() predictions
against the ground truth.

Run from project root:
    python validate_tala.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import mirdata

from carnatify.ml.tala_detector import detect_tala

_DATA_HOME = "/Users/shyamravidath/carnatify"


def _gt_beats_per_cycle(track) -> int | None:
    """Extract ground-truth beats_per_cycle from a saraga track.

    Tries track.tempo['beats_per_cycle'] first; falls back to estimating
    from sama timestamps and bpm if that key is absent or zero.
    """
    tempo = getattr(track, "tempo", None)
    if tempo and "beats_per_cycle" in tempo:
        bpc = tempo["beats_per_cycle"]
        if bpc and float(bpc) > 0:
            return int(round(float(bpc)))

    # Fallback: derive from sama interval × bpm
    sama = getattr(track, "sama", None)
    if sama is not None and tempo and "bpm" in tempo and "sama_interval" in tempo:
        try:
            bpm = float(tempo["bpm"])
            sama_interval = float(tempo["sama_interval"])
            if bpm > 0 and sama_interval > 0:
                return int(round(bpm * sama_interval / 60.0))
        except (TypeError, ValueError):
            pass

    return None


def main() -> None:
    saraga = mirdata.initialize("saraga_carnatic", data_home=_DATA_HOME)
    tracks = saraga.load_tracks()

    print(f"Total saraga tracks: {len(tracks)}")
    print()

    correct = 0
    total = 0
    errors = 0
    skipped = 0

    header = f"{'Track ID':<45} {'GT':>3}  {'Pred':>4}  {'Conf':>5}  {'Tala':<15}  Result"
    print(header)
    print("-" * len(header))

    for track_id, track in sorted(tracks.items()):
        sama = getattr(track, "sama", None)
        gt_bpc = _gt_beats_per_cycle(track)

        if sama is None or gt_bpc is None:
            skipped += 1
            continue

        audio_path = getattr(track, "audio_path", None)
        if audio_path is None or not Path(audio_path).exists():
            skipped += 1
            continue

        try:
            result = detect_tala(audio_path)
            pred_bpc = result["beats_per_cycle"]
            conf = result["confidence"]
            tala = result["tala"]
            match = pred_bpc == gt_bpc
            correct += int(match)
            total += 1
            status = "OK  " if match else "MISS"
            print(
                f"{track_id:<45} {gt_bpc:>3}  {pred_bpc:>4}  {conf:>5.2f}  {tala:<15}  {status}"
            )
        except Exception as exc:
            errors += 1
            print(f"{track_id:<45} {'?':>3}  {'?':>4}  {'?':>5}  {'ERROR':<15}  {exc}")

    print()
    print(f"Evaluated : {total}")
    print(f"Skipped   : {skipped}  (no sama / tempo / audio)")
    print(f"Errors    : {errors}")
    if total > 0:
        print(f"Accuracy  : {correct}/{total} = {correct / total:.1%}")
    else:
        print("Accuracy  : N/A — no evaluable tracks found")


if __name__ == "__main__":
    main()
