import shutil
import numpy as np
import pytest
import soundfile as sf
from carnatify.audio.ffmpeg_window import decode_native_window
from carnatify.audio.utils import phase_safe_mono


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='FFmpeg unavailable')
def test_native_fallback_preserves_seek_rate_and_antiphase(tmp_path):
    sr=16000;t=np.arange(sr*10)/sr;x=(.4*np.sin(2*np.pi*220*t)).astype('float32')
    audio=np.c_[x,-x];path=tmp_path/'stereo.wav';sf.write(path,audio,sr,subtype='FLOAT')
    decoded,rate,meta=decode_native_window(path,2.125,1.5)
    assert rate==sr and decoded.shape==(24000,2)
    np.testing.assert_allclose(decoded,audio[34000:58000],atol=1e-7)
    mono,diagnostics=phase_safe_mono(decoded)
    assert diagnostics['downmix']=='strongest_channel' and np.std(mono)>.2
    assert meta['stderr_bytes']==0


@pytest.mark.parametrize('start,duration',[(-1,1),(0,0),(0,181),(float('nan'),1)])
def test_native_fallback_rejects_unbounded_queries(start,duration):
    with pytest.raises(ValueError):decode_native_window('unused',start,duration)
