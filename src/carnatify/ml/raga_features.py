"""Sklearn-compatible feature extraction for the raga classifier.

Shared between train_raga.py (training) and predict_raga() (inference) so
the feature pipeline is always identical. Three feature groups concatenated:

  - 120-bin tonic-normalized pitch histogram (baseline)
  - 12-bin pitch-class bigram matrix  (144 features) — captures melodic motion
  - 6-bin pitch-class trigram tensor  (216 features) — captures 3-note phrases

Total: 480 features per track. Bigrams and trigrams are the key improvement
over the histogram baseline: raga identity lives in characteristic melodic
movements, not just the inventory of pitches used.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

# Bin counts
_HIST_BINS = 120        # 10 bins per semitone
_BIGRAM_BINS = 12       # one bin per semitone for transitions
_TRIGRAM_BINS = 6       # coarser bins to limit sparsity (6³ = 216 cells)

FEATURE_DIM = _HIST_BINS + _BIGRAM_BINS ** 2 + _TRIGRAM_BINS ** 3  # 480


def extract_features(
    frequencies: NDArray[np.float32 | np.float64],
    tonic: float,
) -> NDArray[np.float64] | None:
    """Extract a 480-dim feature vector from a pitch contour + tonic.

    Parameters
    ----------
    frequencies:
        Raw F0 array in Hz. Unvoiced/silence frames should be 0 or NaN.
    tonic:
        Tonic frequency in Hz. Used to normalize pitch to cents relative to Sa.

    Returns
    -------
    1-D float64 array of length 480, or None if the contour has too few
    voiced frames to produce reliable statistics.
    """
    freqs = np.asarray(frequencies, dtype=np.float64)
    voiced = freqs[(freqs > 0) & np.isfinite(freqs)]

    if voiced.size < 10 or tonic <= 0:
        return None

    cents_abs = 1200.0 * np.log2(voiced / float(tonic))
    cents_mod = cents_abs % 1200.0          # fold to one octave: [0, 1200)

    # ── 120-bin histogram ────────────────────────────────────────────────────
    hist, _ = np.histogram(cents_mod, bins=_HIST_BINS, range=(0.0, 1200.0))
    hist = hist / (hist.sum() + 1e-9)

    # ── 12-bin pitch-class bigrams ───────────────────────────────────────────
    pcs12 = np.floor(cents_mod * _BIGRAM_BINS / 1200.0).astype(int).clip(0, _BIGRAM_BINS - 1)
    bigram = np.zeros((_BIGRAM_BINS, _BIGRAM_BINS), dtype=np.float64)
    if pcs12.size > 1:
        bigram[pcs12[:-1], pcs12[1:]] += 1.0
        bigram /= bigram.sum() + 1e-9

    # ── 6-bin pitch-class trigrams ───────────────────────────────────────────
    pcs6 = np.floor(cents_mod * _TRIGRAM_BINS / 1200.0).astype(int).clip(0, _TRIGRAM_BINS - 1)
    trigram = np.zeros((_TRIGRAM_BINS, _TRIGRAM_BINS, _TRIGRAM_BINS), dtype=np.float64)
    if pcs6.size > 2:
        trigram[pcs6[:-2], pcs6[1:-1], pcs6[2:]] += 1.0
        trigram /= trigram.sum() + 1e-9

    return np.concatenate([hist, bigram.ravel(), trigram.ravel()])
