import numpy as np
import pytest

from carnatify.audio import melody_frontend as frontend


def test_query_contract_distinguishes_context_and_offset():
    a = frontend.query_contract('a'*64, 0, 60)
    assert a != frontend.query_contract('a'*64, 0, 180)
    assert a != frontend.query_contract('a'*64, 30, 60)
    assert a != frontend.query_contract('a'*64, 0, 60, 'harmonic')
    for start, duration in [(-1, 60), (0, 181), (0, 0), (np.nan, 60)]:
        with pytest.raises(ValueError):
            frontend.query_contract('a'*64, start, duration)


def test_query_cache_uses_exact_window(tmp_path, monkeypatch):
    from carnatify.audio import utils
    calls = []
    def load(path, start, duration, sr):
        calls.append((start, duration))
        return np.ones(sr*10, dtype=np.float32), sr, {'rms': 1.}
    monkeypatch.setattr(utils, 'load_audio_window', load)
    monkeypatch.setattr(frontend, 'extract_waveform', lambda *a: (np.ones(100)*220, 110.))
    f0, meta = frontend.extract_query('unused', 'a'*64, 30, 180, tmp_path)
    assert meta['tonic_hz'] == 110
    again, _ = frontend.extract_query('unused', 'a'*64, 30, 180, tmp_path)
    np.testing.assert_array_equal(again, f0)
    assert calls == [(30, 180)]
    frontend.extract_query('unused', 'a'*64, 30, 60, tmp_path)
    assert calls == [(30, 180), (30, 60)]


def test_ten_second_waveform_matches_evaluation_algorithm():
    import essentia.standard as es
    sr=44100
    audio=(.2*np.sin(2*np.pi*220*np.arange(sr*10)/sr)).astype(np.float32)
    f0, tonic=frontend.extract_waveform(audio)
    direct,_=es.PredominantPitchMelodia(**frontend.melodia_parameters())(
        es.EqualLoudness(sampleRate=sr)(audio))
    np.testing.assert_array_equal(f0,direct)
    assert tonic == float(es.TonicIndianArtMusic(sampleRate=sr)(audio))
