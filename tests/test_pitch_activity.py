import numpy as np
import pytest
from carnatify.audio.pitch_activity import activity_features,refine_event


def test_activity_features_are_finite_and_octave_invariant():
    f=np.r_[np.linspace(220,330,400),np.zeros(200),np.linspace(330,220,400)]
    a=activity_features(f,.01);b=activity_features(f*2,.01)
    np.testing.assert_allclose(a,b,atol=1e-6)
    assert a.shape==(10,) and np.isfinite(a).all()
    assert a[0]==np.float32(.8)
    assert np.all(activity_features(np.zeros(1000),.01)==0)


def test_silence_gap_is_not_a_pitch_jump():
    f=np.r_[np.full(400,220.),np.zeros(200),np.full(400,880.)]
    a=activity_features(f,.01)
    assert a[6]==0 and a[7]==0 and a[8]==0


def test_refinement_preserves_nonmusic_and_unknown_states():
    assert refine_event({'state':'music'},.9)['state']=='percussion'
    assert refine_event({'state':'percussion'},.1)['state']=='music'
    for state in ['speech','applause','silence','uncertain']:
        assert refine_event({'state':state},.9)['state']==state


def test_activity_artifact_requires_matching_training_report(tmp_path):
    import hashlib,joblib
    from types import SimpleNamespace
    from carnatify.audio.pitch_activity import PitchActivityAnnotator,VERSION
    report=tmp_path/'result.json';report.write_text('{}')
    bundle=dict(version=VERSION,training_report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                threshold=.5,model=SimpleNamespace(classes_=np.array([0,1])))
    path=tmp_path/'model.joblib';joblib.dump(bundle,path)
    assert PitchActivityAnnotator(path).threshold==.5
    report.write_text('{"changed": true}')
    with pytest.raises(ValueError,match='mismatch'):PitchActivityAnnotator(path)


def test_optional_activity_skips_nonmusic_and_partial_windows(monkeypatch):
    import carnatify.audio.pitch_activity as module
    from types import SimpleNamespace
    annotator=object.__new__(module.PitchActivityAnnotator)
    annotator.threshold=.5
    annotator.model=SimpleNamespace(predict_proba=lambda x:np.array([[.1,.9]]))
    calls=[]
    monkeypatch.setattr(module,'extract_activity_query',lambda *args:calls.append(args) or np.zeros(10))
    events=[dict(start_s=0,end_s=10,state='music'),dict(start_s=10,end_s=20,state='speech'),
            dict(start_s=20,end_s=25,state='music')]
    result=annotator.annotate('audio','hash',events,'cache')
    assert len(calls)==1 and result[0]['state']=='percussion'
    assert result[1:]==events[1:]
    assert events[0]['state']=='music'
