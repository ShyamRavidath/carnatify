import numpy as np
import pytest
from carnatify.audio.rmvpe_frontend import log_mel,decode_salience,RMVPEOnnx


def test_ten_second_mel_contract():
    audio=(.2*np.sin(2*np.pi*220*np.arange(160000)/16000)).astype(np.float32)
    mel=log_mel(audio)
    assert mel.shape==(1,128,1001)
    assert mel.dtype==np.float32 and np.isfinite(mel).all()


def test_decoder_edges_and_silence():
    salience=np.zeros((3,360),dtype=np.float32);salience[1,0]=1;salience[2,359]=1
    f0=decode_salience(salience)
    np.testing.assert_allclose(f0,[0,10*2**(1997.3794084376191/1200),
                                 10*2**((1997.3794084376191+359*20)/1200)],rtol=1e-6)
    with pytest.raises(ValueError):decode_salience(np.full((1,360),np.nan))


def test_chunk_grid_preserves_length_and_context():
    model=object.__new__(RMVPEOnnx)
    model._chunk=lambda audio: np.full(len(audio)//160+1,220,dtype=np.float32)
    f0=model.extract(np.ones(16000*21+53,dtype=np.float32))
    assert len(f0)==2101 and np.all(f0==220)
    with pytest.raises(ValueError):model.extract(np.ones(16000),sr=44100)
