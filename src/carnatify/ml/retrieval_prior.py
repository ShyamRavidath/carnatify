"""Optional development ranking cost from estimated, not annotated, raga."""
import unicodedata
import numpy as np


def key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value).lower()
                   if c.isalnum() and not unicodedata.combining(c))


def raga_prior_cost(distance,reference_raga,estimated_probabilities,weight=.1):
    if not np.isfinite([distance,weight]).all() or distance<0 or not 0<=weight<=1:
        raise ValueError('Invalid retrieval prior configuration')
    if not estimated_probabilities:return float(distance)
    p=np.array(list(estimated_probabilities.values()),dtype=float)
    if not np.isfinite(p).all() or np.any(p<0) or not np.isclose(p.sum(),1,atol=1e-5):
        raise ValueError('Invalid estimated raga distribution')
    mass=sum(v for k,v in estimated_probabilities.items() if key(k)==key(reference_raga))
    # Unknown reference ragas remain eligible. Penalty is bounded by weight,
    # unlike a hard filter or an unbounded negative-log probability penalty.
    return float(distance+weight*(1-mass))
