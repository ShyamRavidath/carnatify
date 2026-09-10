import numpy as np
import pytest
import carnatify.audio.melody_frontend as module


def test_long_raga_context_does_not_supply_song_pitch_or_tonic(monkeypatch):
    digest='a'*64;f=np.array([110.]);calls=[]
    meta=dict(contract=module.query_contract(digest,30,180),tonic_hz=110.)
    def extract(*args):
        calls.append(args);return np.array([220.]),{'tonic_hz':220.}
    monkeypatch.setattr(module,'extract_query',extract)
    song,song_meta=module.composition_query('audio',digest,30,f,meta,'cache')
    assert calls[0][3]==60 and song_meta['tonic_hz']==220 and song[0]==220
    assert meta['tonic_hz']==110


def test_matching_short_context_is_reused(monkeypatch):
    digest='b'*64;f=np.array([220.]);meta=dict(contract=module.query_contract(digest,0,30))
    monkeypatch.setattr(module,'extract_query',lambda *args:pytest.fail('Unnecessary extraction'))
    result=module.composition_query('audio',digest,0,f,meta,'cache')
    assert result[0] is f and result[1] is meta


def test_wrong_recording_context_cannot_be_reused():
    meta=dict(contract=module.query_contract('a'*64,0,60))
    with pytest.raises(ValueError,match='context contract'):
        module.composition_query('audio','b'*64,0,np.zeros(10),meta,'cache')


def test_song_can_request_longer_context_than_raga(monkeypatch):
    digest='a'*64;f=np.array([110.]);meta=dict(contract=module.query_contract(digest,0,60))
    calls=[]
    monkeypatch.setattr(module,'extract_query',lambda *args:(calls.append(args) or (f,{})))
    module.composition_query('audio',digest,0,f,meta,'cache',duration_s=180)
    assert calls[0][3]==180


def test_matching_long_context_reused_but_invalid_duration_rejected(monkeypatch):
    digest='a'*64;f=np.array([110.]);meta=dict(contract=module.query_contract(digest,0,180))
    monkeypatch.setattr(module,'extract_query',lambda *a:pytest.fail('Exact context already available'))
    assert module.composition_query('audio',digest,0,f,meta,'cache',duration_s=180)[0] is f
    with pytest.raises(ValueError,match='bounded'):
        module.composition_query('audio',digest,0,f,meta,'cache',duration_s=181)
