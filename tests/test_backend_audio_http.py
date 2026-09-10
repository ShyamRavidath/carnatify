"""Local HTTP wiring tests: no model downloads, feedback writes, or deployment."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api(monkeypatch):
    from backend import main
    monkeypatch.setattr(main.limiter,'enabled',False)
    monkeypatch.setattr(main,'_estimate_tonic_mix',lambda path:None)
    monkeypatch.setattr(main,'_separate_vocals_sync',
                        lambda *a:pytest.fail('Separation must not run in this test'))
    monkeypatch.setattr(main,'predict_raga',
                        lambda *a,**kw:pytest.fail('Raga must not run without tonic'))
    paths=[]
    def decode(path,sr,duration):
        assert Path(path).exists()
        paths.append(Path(path))
        return np.full(15*sr,.1,dtype=np.float32),sr
    monkeypatch.setattr(main,'load_upload_audio',decode)
    with TestClient(main.app) as client:
        yield client,paths


def test_audio_http_rejects_missing_tonic_before_separation_and_cleans_upload(api):
    client,paths=api
    response=client.post('/predict-audio',files={'file':('clip.webm',b'fixture','audio/webm')})
    assert response.status_code==422 and 'tonic Sa' in response.json()['detail']
    assert paths and all(not p.exists() for p in paths)


def test_lyrics_http_keeps_independent_result_without_tonic(api,monkeypatch):
    import librosa
    client,paths=api
    monkeypatch.setitem(sys.modules,'clip_identify',SimpleNamespace(
        transcribe_multi=lambda *a,**kw:'unverified text',
        identify_from_variants=lambda variants:dict(matches=[],status='unverified'),
        log_query=lambda *a,**kw:'offline-test'))
    monkeypatch.setattr(librosa,'pyin',lambda *a,**kw:
                        (np.full(20,220.),np.ones(20,dtype=bool),np.ones(20)))
    response=client.post('/identify?fast=true',files={'file':('clip.webm',b'fixture','audio/webm')})
    assert response.status_code==200
    assert response.json()['raga']==[] and response.json()['query_id']=='offline-test'
    assert response.json()['status']=='unverified'
    assert paths and all(not p.exists() for p in paths)


def test_space_assembly_includes_matcher_registry_dependency():
    script=(Path(__file__).resolve().parents[1]/'backend/build_space.sh').read_text()
    assert 'cp "$ROOT/registry_hygiene.py" "$HERE/registry_hygiene.py"' in script
