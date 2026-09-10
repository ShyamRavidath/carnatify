"""Versioned, tonic-relative melody features for newly trained models.

Existing pickles use the historical implementation and MUST NOT consume these
features. Unlike that implementation, delays use elapsed time, all intervening
frames must be voiced, and repeated transitions accumulate with np.add.at.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

FEATURE_VERSION = "melody_v1_elapsed_contiguous"
FEATURE_VERSIONS = {'elapsed':FEATURE_VERSION,'voiced':'melody_v1_voiced_compressed',
                    'legacy_fused':'melody_v1_legacy_fused',
                    'multiscale_voiced':'melody_v2_six_voiced_scales'}
TAUS = (0.1, 0.15, 0.25)
MULTISCALE_TAUS = (*TAUS,0.5,1.0,2.0)
NB = 40


def melody_features(frequencies, tonic: float, hop_s: float, *, legacy=False,taus=TAUS):
    """Return histogram (480) and TDMS (4800), or None for insufficient melody.

    legacy=True is only the paired TDMS ablation: voiced-time compression and
    historical histogram semantics. It never changes a deployed artifact.
    """
    f = np.asarray(frequencies, dtype=np.float64)
    if f.ndim != 1:
        raise ValueError("pitch must be a 1-D Hz contour")
    if not np.isfinite(tonic) or tonic <= 0 or not np.isfinite(hop_s) or hop_s <= 0:
        raise ValueError("tonic and hop_s must be finite and positive")
    voiced = np.isfinite(f) & (f > 0)
    if voiced.sum() < 10:
        return None
    if legacy:
        f = f[voiced]
        voiced = np.ones(f.size, dtype=bool)
    cents = np.zeros(f.size)
    cents[voiced] = np.mod(1200 * np.log2(f[voiced] / tonic), 1200)
    # Stabilize values within floating point roundoff of a bin edge.
    cents = np.round(cents, 8) % 1200
    invalid_prefix = np.r_[0, np.cumsum(~voiced)]

    def valid_span(lag):
        return invalid_prefix[lag + 1:] == invalid_prefix[:-(lag + 1)]

    hist = np.histogram(cents[voiced], bins=120, range=(0, 1200))[0].astype(float)
    hist /= hist.sum()
    p12 = np.floor(cents / 100).astype(int) % 12
    p6 = np.floor(cents / 200).astype(int) % 6
    bg, tg = np.zeros((12, 12)), np.zeros((6, 6, 6))
    for mat, ix in (
        (bg, (p12[:-1][valid_span(1)], p12[1:][valid_span(1)])),
        (tg, (p6[:-2][valid_span(2)], p6[1:-1][valid_span(2)], p6[2:][valid_span(2)])),
    ):
        if legacy:
            mat[ix] += 1
        else:
            np.add.at(mat, ix, 1)
        if mat.sum():
            mat /= mat.sum()
    bins = np.floor(cents / (1200 / NB)).astype(int) % NB
    surfaces = []
    for tau in taus:
        if not np.isfinite(tau) or tau<=0:raise ValueError('Delays must be positive')
        lag = max(1, round(tau / hop_s))
        if f.size <= lag:
            return None
        valid = valid_span(lag)
        if not valid.any():
            return None
        surface = np.zeros((NB, NB))
        np.add.at(surface, (bins[:-lag][valid], bins[lag:][valid]), 1)
        surface = gaussian_filter(surface, sigma=1, mode="wrap") ** 0.75
        surfaces.append((surface / surface.sum()).ravel())
    return np.r_[hist, bg.ravel(), tg.ravel()], np.concatenate(surfaces)


def feature_vector(frequencies,tonic,hop_s,representation='elapsed'):
    if representation not in FEATURE_VERSIONS:
        raise ValueError('Unknown melody representation')
    value=melody_features(frequencies,tonic,hop_s,
        legacy=representation in {'voiced','legacy_fused','multiscale_voiced'},
        taus=MULTISCALE_TAUS if representation=='multiscale_voiced' else TAUS)
    if value is None:return None
    return value[1] if representation in {'voiced','multiscale_voiced'} else np.r_[value[0],value[1]]
