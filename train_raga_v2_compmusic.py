"""Feature extraction for Model B: CompMusic pitch-based reference.

This is NOT the pipeline the user asked for (it uses track.pitch, CompMusic's
own pre-extracted pitch, not our Demucs+pyin pipeline over raw audio) -- it
exists purely as a size/coverage reference point, per the hybrid approach:
compmusic_raga's audio was never downloaded locally and isn't available via
mirdata's automated .download() (CompMusic gates audio access behind a
manual request to the Dunya team), so the literal "run 477 tracks through
librosa.pyin on raw audio" instruction can't be executed. See
train_raga_v2_saraga.py for the real audio-pipeline model (Model A), built
on a smaller substitute dataset (Saraga Carnatic) that does have local audio.

Model B reuses the original train_raga.py's data source (track.pitch) across
the full 477-track / 40-raga compmusic_raga set, but adds the same style of
augmentation as Model A so the two are at least comparable on "does
augmentation help" -- NOT on "does matching the inference pipeline help",
since Model B's underlying pitch source is still CompMusic's, not ours.

Augmentation here operates on the frequency contour directly (there's no
waveform to run librosa.effects.pitch_shift or true SNR-based noise on):
  - "pitch shift" proxy: multiply all frequencies by 2**(+-1/12)
  - "noise" proxy: multiply each frequency by a small per-sample Gaussian
    jitter (relative std matched to roughly the pitch-tracking error range
    a light 20dB-SNR noise floor would introduce)

Usage:
    venv_train/bin/python train_raga_v2_compmusic.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import mirdata
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "src"))
from carnatify.ml.raga_features import extract_features  # noqa: E402

ROOT = Path(__file__).parent
OUT_PATH = ROOT / "data" / "raga_v2_cache" / "compmusic_features.joblib"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

JITTER_REL_STD = 0.01  # ~1% relative frequency jitter, proxy for a light noise floor


def augmented_variants(frequencies: np.ndarray, tonic: float, rng: np.random.Generator):
    variants = [("orig", frequencies, tonic)]

    shift_semitones = 1 if rng.integers(0, 2) == 0 else -1
    ratio = 2 ** (shift_semitones / 12)
    variants.append(("pitch_shift", frequencies * ratio, tonic * ratio))

    jitter = rng.normal(1.0, JITTER_REL_STD, size=frequencies.shape)
    variants.append(("noise", frequencies * jitter, tonic))

    return variants


def main() -> None:
    ds = mirdata.initialize("compmusic_raga", data_home=str(ROOT))
    tracks = ds.load_tracks()

    X, y_labels, kinds, track_ids = [], [], [], []
    skipped = 0
    rng = np.random.default_rng(42)

    print(f"Loading tracks... (total in dataset: {len(tracks)})")
    for track_id, track in tracks.items():
        if track.tradition != "carnatic":
            continue
        if not track.raga or not track.pitch:
            skipped += 1
            continue
        tonic = float(track.tonic) if track.tonic else 220.0

        for kind, freqs, ton in augmented_variants(track.pitch.frequencies, tonic, rng):
            feat = extract_features(freqs, ton)
            if feat is None:
                continue
            X.append(feat)
            y_labels.append(track.raga)
            kinds.append(kind)
            track_ids.append(track_id)

    X = np.array(X)
    print(f"Tracks loaded: {len(set(track_ids))}  |  Skipped: {skipped}  |  "
          f"Ragas: {len(set(y_labels))}  |  Total samples (with augmentation): {len(X)}")

    joblib.dump(
        {"X": X, "y_labels": y_labels, "kinds": kinds, "track_ids": track_ids},
        OUT_PATH,
    )
    print(f"Saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
