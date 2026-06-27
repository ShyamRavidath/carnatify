"""Raga classifier training script.

Compares SVM RBF, Random Forest, and MLP across two pitch sources
(raw pitch vs pitch_post_processed) and three feature sets
(histogram only, +bigrams, +bigrams+trigrams).

Run from project root:
    python train_raga.py

Serialises the best model to:
    models/raga_classifier.pkl
    models/raga_label_encoder.pkl
"""

import sys
from pathlib import Path

# Allow importing from src/ without installing the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

import joblib
import mirdata
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC

from carnatify.ml.raga_features import FEATURE_DIM, extract_features

# ── Data loading (unchanged) ─────────────────────────────────────────────────
raga_ds = mirdata.initialize('compmusic_raga', data_home='/Users/shyamravidath/carnatify')
tracks = raga_ds.load_tracks()

# ── Build feature matrices ────────────────────────────────────────────────────
print(f"Loading tracks … (total in dataset: {len(tracks)})")

raw_X, post_X, y_labels = [], [], []
skipped = 0

for track_id, track in tracks.items():
    if track.tradition != 'carnatic':
        continue
    if not track.raga or not track.pitch:
        skipped += 1
        continue

    tonic = float(track.tonic) if track.tonic else 220.0

    # Raw pitch features
    raw_feat = extract_features(track.pitch.frequencies, tonic)
    if raw_feat is None:
        skipped += 1
        continue

    # Post-processed pitch (silence-interpolated, noise-removed)
    # Fall back to raw if post-processed is unavailable for this track
    post_src = track.pitch_post_processed if track.pitch_post_processed is not None else track.pitch
    post_feat = extract_features(post_src.frequencies, tonic)
    if post_feat is None:
        post_feat = raw_feat.copy()

    raw_X.append(raw_feat)
    post_X.append(post_feat)
    y_labels.append(track.raga)

raw_X = np.array(raw_X)
post_X = np.array(post_X)

le = LabelEncoder()
y = le.fit_transform(y_labels)

# Histogram-only slice for ablation (first 120 dims)
raw_hist = raw_X[:, :120]
post_hist = post_X[:, :120]

print(f"Tracks loaded: {len(y)}  |  Skipped: {skipped}  |  Ragas: {len(le.classes_)}")
print(f"Feature dim (full): {raw_X.shape[1]}  |  Histogram-only: 120")
print()

# ── Cross-validation helper ───────────────────────────────────────────────────
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)


def evaluate(name: str, clf, X: np.ndarray) -> float:
    scores = cross_val_score(clf, X, y, cv=cv, n_jobs=-1)
    print(f"  {name:<55} {scores.mean():.3f} ± {scores.std():.3f}")
    return float(scores.mean())


# ── Model grid ────────────────────────────────────────────────────────────────
svm = SVC(kernel='rbf', C=10, gamma='scale', probability=True)
rf = RandomForestClassifier(n_estimators=300, max_features='sqrt', random_state=42, n_jobs=-1)
mlp = Pipeline([
    ('scale', StandardScaler()),
    ('net', MLPClassifier(hidden_layer_sizes=(256, 128), alpha=0.01,
                          max_iter=600, random_state=42)),
])

results: list[tuple[float, str, object, np.ndarray]] = []

print("── Ablation: pitch source & feature set ─────────────────────────────────")
print(f"  {'Configuration':<55} {'Acc':>5}   {'Std':>5}")
print(f"  {'-'*55}   -----   -----")

# Baseline (reproduce original)
acc = evaluate("SVM RBF  |  raw pitch  |  histogram only", svm, raw_hist)
results.append((acc, "baseline_svm", svm, raw_hist))

# Add bigrams
acc = evaluate("SVM RBF  |  raw pitch  |  hist + bigrams", svm, raw_X[:, :120 + 144])
results.append((acc, "svm_raw_bigrams", svm, raw_X[:, :120 + 144]))

# Full features: hist + bigrams + trigrams, raw pitch
acc = evaluate("SVM RBF  |  raw pitch  |  hist + bigrams + trigrams", svm, raw_X)
results.append((acc, "svm_raw_full", svm, raw_X))

# Full features, post-processed pitch  ← main hypothesis
acc = evaluate("SVM RBF  |  post pitch |  hist + bigrams + trigrams", svm, post_X)
results.append((acc, "svm_post_full", svm, post_X))

print()
print("── Model comparison (full features, post-processed pitch) ───────────────")
print(f"  {'Model':<55} {'Acc':>5}   {'Std':>5}")
print(f"  {'-'*55}   -----   -----")

acc = evaluate("SVM RBF  |  post pitch |  hist + bigrams + trigrams", svm, post_X)
results.append((acc, "svm_post_full_2", svm, post_X))

acc = evaluate("Random Forest  |  post pitch  |  full features", rf, post_X)
results.append((acc, "rf_post_full", rf, post_X))

acc = evaluate("MLP (256,128)  |  post pitch  |  full features", mlp, post_X)
results.append((acc, "mlp_post_full", mlp, post_X))

# ── Pick winner and retrain on full dataset ───────────────────────────────────
best_acc, best_name, best_clf, best_X = max(results, key=lambda r: r[0])

print()
print(f"Best configuration: {best_name}  (5-fold CV: {best_acc:.3f})")
print("Retraining on full dataset …")

# Refit on 100% of the data
best_clf.fit(best_X, y)

# ── Persist ───────────────────────────────────────────────────────────────────
MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

model_path = MODELS_DIR / "raga_classifier.pkl"
encoder_path = MODELS_DIR / "raga_label_encoder.pkl"

# If the best model used post-processed features, record that so predict_raga
# knows which pitch source to expect.
metadata = {
    "name": best_name,
    "cv_accuracy": best_acc,
    "feature_dim": best_X.shape[1],
    "pitch_source": "post" if "post" in best_name else "raw",
    "n_ragas": len(le.classes_),
    "ragas": le.classes_.tolist(),
}

joblib.dump({"model": best_clf, "metadata": metadata}, model_path)
joblib.dump(le, encoder_path)

print(f"Saved model    → {model_path}")
print(f"Saved encoder  → {encoder_path}")
print(f"CV accuracy    : {best_acc:.3f}")
print(f"Ragas covered  : {len(le.classes_)}")
