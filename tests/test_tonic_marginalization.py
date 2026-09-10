import numpy as np
import pytest
from scripts.benchmark_tonic_marginalization import mixture


def test_fixed_mixture_is_normalized_and_class_order_equivariant():
    p=np.array([[.6,.4],[.1,.9],[.2,.8]])
    np.testing.assert_allclose(mixture(p),[.51,.49])
    np.testing.assert_allclose(mixture(p[:,::-1]),mixture(p)[::-1])


@pytest.mark.parametrize('p',[np.ones((2,2)),np.full((3,2),np.nan),np.ones((3,2)),np.tile([-.1,1.1],(3,1))])
def test_invalid_probabilities_rejected(p):
    with pytest.raises(ValueError):mixture(p)
