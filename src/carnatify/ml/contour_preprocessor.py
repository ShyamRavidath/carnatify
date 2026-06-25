"""Pre-processing of normalized pitch contours before DTW matching.

Contours are sequences of cents relative to the tonic, with unvoiced frames
encoded as 0 (see :mod:`carnatify.audio.feature_extractor`). Raw contours are
noisy: they carry gamaka micro-variation, silent gaps, and far more frames than
DTW needs. These steps reduce that noise and length so alignment is both more
robust and faster.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class ContourPreprocessor:
    """Clean and reduce a pitch contour ahead of DTW alignment."""

    def remove_unvoiced(self, contour: NDArray[np.float32]) -> NDArray[np.float32]:
        """Drop unvoiced frames (value == 0), compacting the voiced frames.

        This discards the timing of silences entirely. Use it when silence
        position is irrelevant and only the sung pitch trajectory matters.
        """
        contour = np.asarray(contour, dtype=np.float32)
        return contour[contour != 0.0]

    def interpolate_unvoiced(
        self, contour: NDArray[np.float32]
    ) -> NDArray[np.float32]:
        """Linearly interpolate across unvoiced gaps, preserving length.

        Leading/trailing unvoiced frames are filled with the nearest voiced
        value. Better than :meth:`remove_unvoiced` for short gaps where the
        surrounding melody implies a smooth transition.
        """
        contour = np.asarray(contour, dtype=np.float32).copy()
        voiced = contour != 0.0
        if not np.any(voiced):
            return contour
        if np.all(voiced):
            return contour

        idx = np.arange(contour.size)
        contour[~voiced] = np.interp(
            idx[~voiced], idx[voiced], contour[voiced]
        )
        return contour

    def smooth(
        self, contour: NDArray[np.float32], window_size: int = 5
    ) -> NDArray[np.float32]:
        """Moving-average smoothing to suppress noise and gamaka jitter.

        A centered window is used; edges are handled with ``np.convolve`` in
        ``same`` mode after edge-padding so the output length is unchanged.
        """
        contour = np.asarray(contour, dtype=np.float32)
        if window_size <= 1 or contour.size == 0:
            return contour
        window_size = min(window_size, contour.size)

        pad = window_size // 2
        padded = np.pad(contour, pad, mode="edge")
        kernel = np.ones(window_size, dtype=np.float32) / window_size
        smoothed = np.convolve(padded, kernel, mode="valid")
        # 'valid' over a length-(n+2*pad) signal yields n+2*pad-window_size+1
        # samples; trim symmetrically back to the original length.
        return smoothed[: contour.size].astype(np.float32)

    def downsample(
        self, contour: NDArray[np.float32], factor: int = 4
    ) -> NDArray[np.float32]:
        """Reduce resolution by average pooling over non-overlapping windows.

        A trailing partial window (when the length is not divisible by
        ``factor``) is averaged on its own so no frames are dropped.
        """
        contour = np.asarray(contour, dtype=np.float32)
        if factor <= 1 or contour.size == 0:
            return contour

        n = contour.size
        full = n - (n % factor)
        pooled = []
        if full > 0:
            pooled.append(contour[:full].reshape(-1, factor).mean(axis=1))
        if n > full:
            pooled.append(np.array([contour[full:].mean()], dtype=np.float32))
        return np.concatenate(pooled).astype(np.float32)

    def preprocess(
        self,
        contour: NDArray[np.float32],
        remove_silence: bool = True,
        smooth_window: int = 5,
        downsample_factor: int = 4,
    ) -> NDArray[np.float32]:
        """Full pipeline: silence handling -> smoothing -> downsampling.

        When ``remove_silence`` is True unvoiced frames are dropped outright;
        otherwise they are interpolated so length and timing are preserved.
        """
        contour = np.asarray(contour, dtype=np.float32)

        if remove_silence:
            contour = self.remove_unvoiced(contour)
        else:
            contour = self.interpolate_unvoiced(contour)

        if smooth_window > 1:
            contour = self.smooth(contour, smooth_window)
        if downsample_factor > 1:
            contour = self.downsample(contour, downsample_factor)

        return contour.astype(np.float32)
