"""Dynamic Time Warping between normalized pitch contours.

Carnatic compositions are performed at varying tempos across renditions, so a
rigid frame-to-frame comparison (Euclidean) would penalise the same melody sung
faster or slower. DTW aligns two contours with non-linear time warping, making
the distance tempo-robust. A Sakoe-Chiba band (``window_size``) caps how far the
alignment may stray from the diagonal, bounding both cost and runtime.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from dtaidistance import dtw
from dtaidistance.subsequence.dtw import subsequence_alignment


def _drop_unvoiced(contour: NDArray[np.float32]) -> NDArray[np.float64]:
    """Return the voiced frames (value != 0) as a contiguous float64 array.

    dtaidistance expects 1-D float64 input. Unvoiced frames carry no pitch
    information and would otherwise pull the alignment toward 0 cents.
    """
    arr = np.asarray(contour, dtype=np.float64)
    return np.ascontiguousarray(arr[arr != 0.0])


class DTWMatcher:
    """Compute DTW distance and similarity between two pitch contours."""

    def __init__(
        self, window_size: int | None = None, step_pattern: str = "symmetric2"
    ):
        self.window_size = window_size
        self.step_pattern = step_pattern

    def compute_distance(
        self, query: NDArray[np.float32], reference: NDArray[np.float32]
    ) -> float:
        """DTW distance between two contours after removing unvoiced frames.

        Returns ``inf`` when either contour has no voiced frames, since no
        meaningful alignment exists.
        """
        q = _drop_unvoiced(query)
        r = _drop_unvoiced(reference)
        if q.size == 0 or r.size == 0:
            return float("inf")

        kwargs = {"use_c": False}
        if self.window_size is not None:
            kwargs["window"] = self.window_size
        return float(dtw.distance(q, r, **kwargs))

    def compute_similarity(
        self, query: NDArray[np.float32], reference: NDArray[np.float32]
    ) -> float:
        """Convert DTW distance to a similarity in ``[0, 1]``.

        The raw distance grows with contour length, so it is normalized by the
        length of the warping path before mapping through
        ``1 / (1 + normalized_distance)``. Identical contours give 1.0; the
        score decays monotonically as the contours diverge.
        """
        q = _drop_unvoiced(query)
        r = _drop_unvoiced(reference)
        if q.size == 0 or r.size == 0:
            return 0.0

        kwargs = {"use_c": False}
        if self.window_size is not None:
            kwargs["window"] = self.window_size

        distance, paths = dtw.warping_paths(q, r, **kwargs)
        if not np.isfinite(distance):
            return 0.0

        path = dtw.best_path(paths)
        path_len = len(path) if path else max(q.size, r.size)
        normalized = distance / path_len if path_len > 0 else distance
        return 1.0 / (1.0 + normalized)

    def match_subsequence(
        self, query: NDArray[np.float32], reference: NDArray[np.float32]
    ) -> float:
        """Best similarity of ``query`` against any subsequence of ``reference``.

        Uses subsequence DTW so a short query (e.g. a 30 s clip) can match the
        section of a longer reference rendition it was drawn from, without the
        unmatched remainder of the reference inflating the distance.
        """
        q = _drop_unvoiced(query)
        r = _drop_unvoiced(reference)
        if q.size == 0 or r.size == 0:
            return 0.0

        sa = subsequence_alignment(q, r)
        match = sa.best_match()
        if match is None:
            return 0.0

        distance = float(match.value)
        if not np.isfinite(distance):
            return 0.0

        # Subsequence cost accumulates over the query length; normalize by it so
        # the score is comparable to compute_similarity.
        normalized = distance / q.size if q.size > 0 else distance
        return 1.0 / (1.0 + normalized)
