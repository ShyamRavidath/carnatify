import ast
from pathlib import Path
import shutil
import subprocess
import numpy as np
import pytest
import soundfile as sf
from carnatify.audio.utils import load_upload_audio, phase_safe_mono


def test_upload_decodes_channels_before_downmix_and_resample(monkeypatch):
    from carnatify.audio import utils
    y=np.sin(2*np.pi*220*np.arange(16000)/16000).astype(np.float32)*.2
    calls=[]
    def decode(path,**kwargs):
        calls.append(kwargs)
        return np.stack([y,-y]),16000
    monkeypatch.setattr(utils.librosa,'load',decode)
    result,sr=load_upload_audio('recording.webm',16000,10.)
    np.testing.assert_array_equal(result,y)
    assert sr==16000 and calls==[dict(sr=None,mono=False,duration=10.)]
    for duration in (0,-1,181,float('nan')):
        with pytest.raises(ValueError):load_upload_audio('unused',16000,duration)


def test_downmix_retains_ordinary_mean_and_rejects_bad_layout():
    y=np.array([[.1,.2],[.3,.4]],np.float32)
    mono,diagnostics=phase_safe_mono(y)
    np.testing.assert_array_equal(mono,y.mean(axis=1))
    assert diagnostics['downmix']=='mean'
    for bad in (np.ones(3),np.zeros((0,2)),np.full((4,2),np.nan)):
        with pytest.raises(ValueError):phase_safe_mono(bad)


def test_actual_browser_webm_preserves_antiphase_signal(tmp_path):
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:pytest.skip('ffmpeg required for actual WebM codec test')
    sr=48000;y=(.2*np.sin(2*np.pi*220*np.arange(10*sr)/sr)).astype(np.float32)
    wav=tmp_path/'source.wav';webm=tmp_path/'browser.webm'
    sf.write(wav,np.c_[y,-y],sr,subtype='FLOAT')
    subprocess.run([ffmpeg,'-nostdin','-v','error','-i',str(wav),'-c:a','libopus',
                    '-b:a','128k',str(webm)],check=True,capture_output=True)
    result,rate=load_upload_audio(webm,16000,5.)
    import librosa
    legacy,_=librosa.load(str(webm),sr=16000,mono=True,duration=5.)
    assert rate==16000 and len(result)==80000
    assert np.isfinite(result).all() and np.sqrt(np.mean(result**2))>.1
    assert np.sqrt(np.mean(result**2))>20*np.sqrt(np.mean(legacy**2))
    spectrum=np.abs(np.fft.rfft(result[16000:64000]))
    peak=np.fft.rfftfreq(48000,1/16000)[spectrum.argmax()]
    assert peak==pytest.approx(220,abs=1)


def test_backend_uses_only_explicitly_bounded_shared_upload_decoding():
    source=Path(__file__).resolve().parents[1]/'backend/main.py'
    tree=ast.parse(source.read_text())
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                   and isinstance(n.func.value,ast.Name) and n.func.value.id=='librosa'
                   and n.func.attr=='load' for n in ast.walk(tree))
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
           and n.func.id=='load_upload_audio']
    assert len(calls)==8
    assert all(len(n.args)==3 and isinstance(n.args[2],ast.Constant)
               and 0<n.args[2].value<=180 for n in calls)
