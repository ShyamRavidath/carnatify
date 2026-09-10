import hashlib
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from carnatify.audio.recording_fingerprint import RecordingFingerprinter
from scripts.extract_recording_fingerprints import ffmpeg_blocks

LIB = Path(__file__).resolve().parents[1] / 'data/overhaul/chromaprint/build/src/libchromaprint.1.5.1.dylib'


@pytest.fixture
def printer():
    if not LIB.exists():
        pytest.skip('Optional locally built audit library unavailable')
    return RecordingFingerprinter(LIB, hashlib.sha256(LIB.read_bytes()).hexdigest())


def test_library_hash_is_checked_before_loading(tmp_path):
    p = tmp_path / 'library'
    p.write_bytes(b'not a library')
    with pytest.raises(ValueError, match='checksum'):
        RecordingFingerprinter(p, 'wrong')


def test_streaming_partition_does_not_change_fingerprint(printer):
    sr = 11025
    t = np.arange(sr * 20) / sr
    y = (.3 * np.sin(2 * np.pi * (220 * t + 15 * t * t))).astype(np.float32)
    before = y.copy()
    a, ma = printer.fingerprint([y], sr)
    b, mb = printer.fingerprint(np.array_split(y, 20), sr)
    assert np.array_equal(a, b) and ma == mb
    assert len(a) > 50 and a.dtype == np.uint32
    assert np.array_equal(y, before)


def test_invalid_stream_fails_without_native_crash(printer):
    for y in [np.zeros((10, 2)), np.array([np.nan]), np.array([2.]), np.zeros(100)]:
        with pytest.raises(ValueError):
            printer.fingerprint([y])


def test_fallback_decoder_preserves_native_channels_and_samples(tmp_path):
    sr=11025
    t=np.arange(sr*2)/sr
    y=.3*np.sin(2*np.pi*220*t)
    path=tmp_path/'stereo.wav'
    sf.write(path,np.column_stack([y,-y]),sr,subtype='PCM_16')
    expected,_=sf.read(path,dtype='float32',always_2d=True)
    decoded=np.concatenate(list(ffmpeg_blocks(path,sr,2)))
    np.testing.assert_array_equal(decoded,expected)


def test_fallback_decode_error_is_not_silently_accepted(tmp_path):
    with pytest.raises(RuntimeError,match='not clean'):
        list(ffmpeg_blocks(tmp_path/'missing.mp3',11025,1))
