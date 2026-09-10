import numpy as np
from scripts.audit_recording_fingerprint_overlap import make_index,scan


def test_offset_and_small_bit_changes_still_flag_copy():
    rng=np.random.default_rng(123)
    q=rng.integers(0,2**32,size=250,dtype=np.uint32)
    copied=q.copy();copied[::10]^=np.uint32(1)
    r=np.r_[rng.integers(0,2**32,size=40,dtype=np.uint32),copied]
    flags=scan(r,[q],make_index([q]))
    assert len(flags)==1 and flags[0]['offset_frames']==40
    assert flags[0]['bit_error']<.01
    assert not scan(q[::-1].copy(),[q],make_index([q]))


def test_constant_fingerprints_cannot_flag_identity():
    q=np.zeros(500,dtype=np.uint32)
    assert not scan(q,[q],make_index([q]))
