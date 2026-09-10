import json
import numpy as np
import pytest
from scripts.benchmark_melody_retrieval import load_query


def save(cache,window,meta):
    np.savez(cache/f'{"a"*32}_center{window}_v1.npz',f0=np.array([220.]),meta=json.dumps(meta))


def test_long_query_uses_its_own_tonic_and_exact_cache(tmp_path):
    original=dict(audio_sha256='a'*64,start_s=100.,end_s=160.,tonic_estimated=110.)
    expanded=dict(original,start_s=40.,end_s=220.,tonic_estimated=220.)
    save(tmp_path,180,expanded)
    f,meta=load_query(tmp_path,original,180)
    assert meta==expanded and f[0]==220.


@pytest.mark.parametrize('changes',[dict(audio_sha256='b'*64),dict(start_s=41.),
                                    dict(extraction_profile='harmonic'),dict(end_s=221.),
                                    dict(start_s=70.,end_s=190.)])
def test_shifted_or_wrong_recording_cache_rejected(tmp_path,changes):
    original=dict(audio_sha256='a'*64,start_s=100.,end_s=160.,tonic_estimated=110.)
    expanded=dict(original,start_s=40.,end_s=220.);expanded.update(changes)
    save(tmp_path,180,expanded)
    with pytest.raises(ValueError,match='provenance'):load_query(tmp_path,original,180)


def test_original_query_cannot_change_tonic_silently(tmp_path):
    original=dict(audio_sha256='a'*64,start_s=100.,end_s=160.,tonic_estimated=110.)
    save(tmp_path,60,dict(original,tonic_estimated=220.))
    with pytest.raises(ValueError,match='metadata changed'):load_query(tmp_path,original)
