import numpy as np
from carnatify.ml.melody_retrieval import melody_sequence,subsequence_distance


def test_retrieval_tonic_invariance_and_sa_preservation():
    f=np.repeat(220*2**(np.array([0,2,4,7,9,7,4,2])/12),100)
    a=melody_sequence(f,220,.01)
    b=melody_sequence(f*1.31,220*1.31,.01)
    np.testing.assert_allclose(a,b)
    assert len(a)==16 and a[0,0]>0
    assert subsequence_distance(a,b)<1e-6


def test_subsequence_and_tempo():
    q=np.eye(24,dtype=np.float32)[[0,4,8,14,18,14,8,4,0,4,8,0]]
    r=np.r_[np.eye(24)[[21]*10],np.repeat(q,2,axis=0),np.eye(24)[[22]*10]]
    assert subsequence_distance(q,r)<.06
    assert subsequence_distance(q,np.eye(24)[[23]*60])>.9


def test_song_alignment_handles_global_tonic_error_without_changing_raga_labels():
    q=np.eye(24,dtype=np.float32)[[0,4,8,14,18,14,8,4,0,4,8,0]]
    r=np.roll(q,10,axis=1)
    assert subsequence_distance(q,r,transposition_invariant=True)<1e-6
    assert subsequence_distance(q,r)>.1
