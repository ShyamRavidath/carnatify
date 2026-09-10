import numpy as np
import pytest
from carnatify.audio import cache_io


def test_atomic_feature_write_and_failed_replacement(tmp_path,monkeypatch):
    target=tmp_path/'features.npz'
    cache_io.atomic_npz(target,f0=np.array([220.,0.]))
    with np.load(target) as z:np.testing.assert_array_equal(z['f0'],[220.,0.])
    original=target.read_bytes()
    def fail(stream,**arrays):
        stream.write(b'partial output')
        raise RuntimeError('simulated interruption')
    monkeypatch.setattr(cache_io.np,'savez_compressed',fail)
    with pytest.raises(RuntimeError):cache_io.atomic_npz(target,f0=np.array([330.]))
    assert target.read_bytes()==original
    assert list(tmp_path.iterdir())==[target]
