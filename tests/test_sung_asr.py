from types import SimpleNamespace
import numpy as np
import pytest
from carnatify.audio.sung_asr import SungASR,DECODE


def test_untrusted_checkpoint_is_not_loaded(tmp_path):
    path=tmp_path/'wrong.pt';path.write_bytes(b'invalid')
    with pytest.raises(ValueError,match='checksum'):SungASR(path)


def test_bounded_unprompted_hypothesis_preserves_diagnostics():
    instance=object.__new__(SungASR);calls=[]
    def transcribe(y,**kwargs):
        calls.append(kwargs)
        return dict(text=' hypothesized text ',language='te',segments=[dict(start=0,end=1,text='text',avg_logprob=-.4)])
    instance.model=SimpleNamespace(transcribe=transcribe)
    result=instance.transcribe(np.ones(16000,dtype=np.float32)*.1)
    assert calls==[DECODE] and calls[0]['initial_prompt'] is None
    assert result['status']=='unverified_hypothesis' and result['segments'][0]['avg_logprob']==-.4
    assert instance.transcribe(np.zeros(16000))['status']=='silence'
    assert len(calls)==1
    with pytest.raises(ValueError):instance.transcribe(np.array([np.nan]))
    with pytest.raises(ValueError):instance.transcribe(np.ones(16000),44100)
    instance.transcribe(np.ones(16000)*.1,language='te')
    assert calls[-1]['language']=='te' and calls[-1]['initial_prompt'] is None
    with pytest.raises(ValueError):instance.transcribe(np.ones(16000),language='oracle')
