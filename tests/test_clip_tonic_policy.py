from pathlib import Path
import numpy as np
import pytest
import identify_clip


@pytest.mark.parametrize('tonic,expected_calls',[(140.,1),(float('nan'),0)])
def test_legacy_clip_does_not_search_raga_rotations(monkeypatch,tonic,expected_calls):
    import essentia.standard as es
    import carnatify.audio.utils as audio_utils
    monkeypatch.setattr(audio_utils,'load_audio_window',lambda *a:(np.ones(44100*12,dtype=np.float32),44100,{}))
    monkeypatch.setattr(es,'PredominantPitchMelodia',lambda **kw:lambda y:(np.full(6000,220.),np.ones(6000)))
    monkeypatch.setattr(es,'EqualLoudness',lambda **kw:lambda y:y)
    monkeypatch.setattr(es,'TonicIndianArtMusic',lambda **kw:lambda y:tonic)
    calls=[]
    class Model:
        classes_=np.array(['A','B'])
        def predict_proba(self,X):calls.append(X);return np.array([[.6,.4]])
    monkeypatch.setattr(identify_clip.raga_top5,'_clf',Model(),raising=False)
    result,error=identify_clip.raga_top5(Path('unused.wav'))
    assert len(calls)==expected_calls
    assert bool(result)==bool(expected_calls)
    assert (error is None)==bool(expected_calls)
