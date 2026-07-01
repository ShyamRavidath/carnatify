"""Train + 5-fold CV both retrain candidates and report results side by side.

Reads the caches built by train_raga_v2_saraga.py + train_raga_v2_archive.py
(Model A: real audio, Demucs+pyin, matches inference exactly -- combined
across both real-audio sources) and train_raga_v2_compmusic.py (Model B:
CompMusic's own pitch extraction, reference/comparison only -- see that
script's docstring for why it isn't a true pipeline-matched candidate).

Does NOT overwrite models/raga_classifier.pkl (the production model) --
saves each candidate to models/raga_classifier_<name>.pkl instead so the
choice of what ships is a separate, explicit step.

Usage:
    venv_train/bin/python train_raga_v2_evaluate.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).parent
CACHE_DIR = ROOT / "data" / "raga_v2_cache"
MODELS_DIR = ROOT / "models"


def load_realaudio_cache() -> tuple[np.ndarray, list[str], list[str]]:
    """Combines both real-audio sources (Saraga Carnatic + archive.org downloads) --
    both went through the identical Demucs+pyin pipeline via raga_v2_pipeline.py, so
    they're directly poolable into one dataset."""
    X, y_labels, track_ids = [], [], []
    for subdir in ("saraga", "archive"):
        for npz_path in sorted((CACHE_DIR / subdir).glob("*.npz")):
            d = np.load(npz_path, allow_pickle=True)
            raga = str(d["raga"])
            tid = str(d["track_id"])
            for row in d["X"]:
                X.append(row)
                y_labels.append(raga)
                track_ids.append(tid)
    return np.array(X), y_labels, track_ids


def load_compmusic_cache() -> tuple[np.ndarray, list[str], list[str]]:
    d = joblib.load(CACHE_DIR / "compmusic_features.joblib")
    return np.array(d["X"]), d["y_labels"], d["track_ids"]


def evaluate(name: str, X: np.ndarray, y_labels: list[str], track_ids: list[str]) -> dict:
    le = LabelEncoder()
    y = le.fit_transform(y_labels)

    # Group by track_id: augmented variants of the same track are near-duplicates
    # (same recording, same singer, same session), so a plain StratifiedKFold lets
    # them leak across train/test and inflates accuracy. StratifiedGroupKFold keeps
    # every variant of a track on the same side of the split, so the reported score
    # reflects generalization to genuinely unseen recordings.
    tracks_per_class = Counter(
        {label: len(set(t for t, lbl in zip(track_ids, y_labels) if lbl == label))
         for label in set(y_labels)}
    )
    min_tracks_per_class = min(tracks_per_class.values())
    n_splits = max(2, min(5, min_tracks_per_class))

    clf = RandomForestClassifier(
        n_estimators=300, max_features="sqrt", random_state=42, n_jobs=-1
    )
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores = cross_val_score(clf, X, y, cv=cv, groups=track_ids, n_jobs=-1)

    n_tracks = len(set(track_ids))
    print(f"\n── {name} ──────────────────────────────────────────────")
    print(f"  samples (incl. augmentation): {len(y)}   source tracks: {n_tracks}")
    print(f"  ragas: {len(le.classes_)}   min source-tracks/raga: {min_tracks_per_class}   "
          f"folds used: {n_splits} (grouped by track_id)")
    print(f"  Grouped CV accuracy (no track leakage): {scores.mean():.3f} +/- {scores.std():.3f}")

    clf.fit(X, y)
    metadata = {
        "name": name,
        "cv_accuracy": float(scores.mean()),
        "cv_std": float(scores.std()),
        "n_folds": n_splits,
        "feature_dim": X.shape[1],
        "n_ragas": len(le.classes_),
        "n_source_tracks": n_tracks,
        "n_samples": len(y),
        "ragas": le.classes_.tolist(),
    }
    model_path = MODELS_DIR / f"raga_classifier_{name}.pkl"
    encoder_path = MODELS_DIR / f"raga_label_encoder_{name}.pkl"
    joblib.dump({"model": clf, "metadata": metadata}, model_path)
    joblib.dump(le, encoder_path)
    print(f"  saved -> {model_path}")

    return metadata


def main() -> None:
    existing_path = MODELS_DIR / "raga_classifier.pkl"
    if existing_path.exists():
        existing = joblib.load(existing_path)["metadata"]
        print("── Current production model (baseline, before) ──────────────")
        print(f"  cv_accuracy: {existing.get('cv_accuracy'):.3f}   "
              f"ragas: {existing.get('n_ragas')}   "
              f"pitch_source: {existing.get('pitch_source')} (CompMusic's own extraction)")

    results = []

    Xa, ya, tida = load_realaudio_cache()
    if len(Xa):
        results.append(evaluate("realaudio_v2", Xa, ya, tida))
    else:
        print("\nNo real-audio cache found yet -- run train_raga_v2_saraga.py "
              "and/or train_raga_v2_archive.py first.")

    Xb, yb, tidb = load_compmusic_cache()
    if len(Xb):
        results.append(evaluate("compmusic_v2_reference", Xb, yb, tidb))
    else:
        print("\nNo CompMusic cache found yet -- run train_raga_v2_compmusic.py first.")

    print("\n── Summary ────────────────────────────────────────────────")
    for r in results:
        print(f"  {r['name']:<28} acc={r['cv_accuracy']:.3f}  "
              f"ragas={r['n_ragas']:<3} tracks={r['n_source_tracks']:<4} "
              f"samples={r['n_samples']}")


if __name__ == "__main__":
    main()
