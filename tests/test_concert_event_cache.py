"""Default activity blocks must not redundantly extract discarded pitch."""
import json
from types import SimpleNamespace
import numpy as np
import pytest
from scripts import concert_pipeline as module


def test_exact_frontend_uses_events_only_cache_and_resumes(tmp_path,monkeypatch):
    model=SimpleNamespace(classes_=np.array(['A','B']),n_jobs=4,
                          predict_proba=lambda x:np.array([[.8,.2]]))
    bundle=dict(model=model,representation='voiced',
                feature_version=module.FEATURE_VERSIONS['voiced'],
                calibration=dict(gate=dict(threshold=.5),status='development'))
    monkeypatch.setattr(module.joblib,'load',lambda p:bundle)
    monkeypatch.setattr(module.sf,'info',lambda p:SimpleNamespace(duration=10.))
    monkeypatch.setattr(module,'sha',lambda p:'a'*64)
    monkeypatch.setattr(module,'load_audio_window',lambda *a:
                        (np.ones(441000,dtype=np.float32)*.1,44100,dict(rms=.1)))
    import essentia.standard as es
    monkeypatch.setattr(es,'PredominantPitchMelodia',
                        lambda **kw:pytest.fail('Discarded block pitch extraction'))
    monkeypatch.setattr(es,'TonicIndianArtMusic',
                        lambda **kw:pytest.fail('Discarded block tonic extraction'))
    calls=[]
    class Events:
        def __init__(self,*args):pass
        def predict(self,clip):
            calls.append(len(clip))
            return dict(state='music',music=.9,speech=0,applause=0,
                        percussion=0,melodic=.9,top_events=[])
    monkeypatch.setattr(module,'AudioEventClassifier',Events)
    import carnatify.ml.composition_catalog as catalogs
    from carnatify.audio.melody_frontend import query_contract
    prior_calls=[]
    class Catalog:
        def __init__(self,*args):pass
        def rank(self,*args,**kwargs):
            prior_calls.append(kwargs['raga_probabilities'])
            return []
    monkeypatch.setattr(catalogs,'CompositionCatalog',Catalog)
    monkeypatch.setattr(module,'extract_query',lambda *a:
                        (np.full(4000,220.),dict(tonic_hz=110.,extraction_failure=None,
                            contract=query_contract('a'*64,0,10))))
    monkeypatch.setattr(module,'feature_vector',lambda *a:np.ones(2))
    output=tmp_path/'report.json';cache=tmp_path/'cache'
    monkeypatch.setattr(module.sys,'argv',['concert_pipeline','audio.wav',
                        '--output',str(output),'--cache',str(cache),
                        '--composition-catalog','catalog.npz','--composition-raga-prior',
                        '--composition-window-s','180'])
    module.main()
    assert model.n_jobs==1
    first=json.loads(output.read_text())
    assert first['block_frontend']==module.EVENTS_VERSION
    assert first['query_frontend']==module.QUERY_FRONTEND_VERSION
    paths=list(cache.rglob('*.npz'))
    assert len(paths)==1
    with np.load(paths[0]) as saved:
        assert saved.files==['meta']
    monkeypatch.setattr(module,'load_audio_window',lambda *a:pytest.fail('Cache not reused'))
    module.main()
    second=json.loads(output.read_text())
    assert first['events']==second['events'] and first['windows']==second['windows']
    assert len(calls)==1
    assert prior_calls==[{'A':.8,'B':.2}]*2
    assert first['composition_raga_prior_weight']==.1
    assert first['windows'][0]['composition_query']['end_s']==10
    assert module.EVENTS_VERSION!=module.EXTRACTION_VERSION
