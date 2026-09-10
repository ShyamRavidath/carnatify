import hashlib
import json
import sys
import numpy as np
import pytest
from scripts import recover_context_decode_windows as module
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.cache_io import atomic_npz


def test_recovery_is_separate_resumable_and_rechecks_raw_identity(tmp_path,monkeypatch):
    audio=tmp_path/'audio.bin';audio.write_bytes(b'fixture source')
    run=tmp_path/'run';out=tmp_path/'recovery';track='a'
    row=dict(track=track,corpus='archive',audio=str(audio),audio_sha256=sha(audio))
    write_json(run/'plan.json',dict(rows=[row]))
    cache=run/'tracks'/(hashlib.sha256(track.encode()).hexdigest()+'.npz')
    atomic_npz(cache,plan_sha256=sha(run/'plan.json'),metadata=json.dumps(dict(rejected=[
        dict(reason='libsndfile_window_decode_error',start_s=0,duration_s=15)])))
    original=sha(cache)
    monkeypatch.setattr(module,'decode_native_window',lambda *a:(np.ones((44100*15,1),dtype='float32')*.1,44100,{}))
    f=220*2**(.1*np.sin(np.arange(5168)*.01))
    monkeypatch.setattr(module,'extract_waveform',lambda *a:(f,220))
    monkeypatch.setattr(sys,'argv',['recover','--run',str(run),'--out',str(out),'--track',track])
    module.main()
    with np.load(out/'window_0.npz',allow_pickle=False) as z:
        assert z['X'].shape==(5280,) and z['legacy'].shape==(4800,)
        assert np.isfinite(z['X']).all()
    monkeypatch.setattr(module,'decode_native_window',lambda *a:pytest.fail('Resume decoded again'))
    module.main()
    assert sha(cache)==original
    audio.write_bytes(b'changed')
    with pytest.raises(ValueError,match='Raw audio changed'):module.main()
