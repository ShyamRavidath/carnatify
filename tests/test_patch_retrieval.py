import numpy as np
import pytest
from carnatify.ml.melody_retrieval import subsequence_distance


def test_patch_alignment_handles_reordered_reference_passages():
    q=np.eye(24,dtype=np.float32)[np.repeat([0,8,16],12)]
    r=np.concatenate([q[24:],q[:12],q[12:24]])
    assert subsequence_distance(q,r,query_patches=3)<1e-6
    assert subsequence_distance(q,r)>0.1


def test_patch_alignment_does_not_choose_separate_transpositions():
    q=np.eye(24,dtype=np.float32)[np.repeat([0,8,16],12)]
    r=np.eye(24,dtype=np.float32)[np.repeat([0],36)]
    assert subsequence_distance(q,r,True,3)>.5


def test_short_patch_queries_do_not_silently_change_protocol():
    q=np.eye(24,dtype=np.float32)[:12]
    assert np.isinf(subsequence_distance(q,q,query_patches=3))
    with pytest.raises(ValueError):subsequence_distance(q,q,query_patches=2)
