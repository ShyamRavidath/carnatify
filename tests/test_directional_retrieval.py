import numpy as np
import pytest
from carnatify.ml.melody_retrieval import directional_cost,directional_distances,subsequence_distance


def test_forward_computation_preserves_original_distance():
    rng=np.random.default_rng(42)
    q=np.eye(24,dtype=np.float32)[rng.integers(0,24,24)]
    r=np.roll(np.repeat(q,2,axis=0),10,axis=1)
    for invariant in (False,True):
        forward,reverse=directional_distances(q,r,invariant)
        assert forward==pytest.approx(subsequence_distance(q,r,invariant),abs=1e-12)
    assert reverse>forward
    assert directional_cost(forward,reverse)<.1


def test_stationary_pitch_has_no_directional_evidence():
    q=np.eye(24,dtype=np.float32)[[0]*30]
    a,b=directional_distances(q,q,True)
    assert a==b==0 and directional_cost(a,b)==.5


def test_unequal_costs_and_invalid_inputs():
    assert directional_cost(.2,.6)==pytest.approx(.25)
    assert directional_cost(.6,.2)==pytest.approx(.75)
    with pytest.raises(ValueError):directional_cost(float('inf'),1.)
    with pytest.raises(ValueError):directional_cost(-1.,1.)
    assert directional_distances(np.zeros((7,24)),np.zeros((20,24)))==(float('inf'),float('inf'))
