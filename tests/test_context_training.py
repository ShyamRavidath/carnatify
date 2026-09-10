import numpy as np
import pytest
from scripts.extract_context_training import window_starts,extract_track


def test_decode_audit_requires_matching_evidence_and_excludes_failures():
    from scripts.extract_context_training import filter_decode_audit
    row=dict(track='a',corpus='archive',audio='a.mp3',audio_sha256='hash')
    record=dict(row,status='clean')
    assert filter_decode_audit([row],dict(rows=[record]))==([row],[])
    bad=dict(record,status='decoder_error')
    assert filter_decode_audit([row],dict(rows=[bad]))==([],[bad])
    for records in ([],[dict(record,audio_sha256='changed')],[record,record]):
        with pytest.raises(ValueError):filter_decode_audit([row],dict(rows=records))


def test_archive_window_decode_error_is_recorded_not_silently_reused(tmp_path,monkeypatch):
    import json
    import soundfile as sf
    from scripts import extract_context_training as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'sha',lambda p:'fixed')
    np.save(tmp_path/'pitch.npy',np.ones(2000)*220)
    def broken(*args,**kwargs):raise sf.LibsndfileError(1)
    monkeypatch.setattr(module,'extract_query',broken)
    row=dict(track='archive',corpus='archive',contour='pitch.npy',contour_sha256='fixed',
        audio='audio.mp3',audio_sha256='fixed',hop_s=.01,tonic=220)
    target=extract_track((row,str(tmp_path/'out'),'plan',180))
    with np.load(target,allow_pickle=False) as z:
        assert z['X'].shape==(0,5280)
        assert json.loads(str(z['metadata']))['rejected'][0]['reason']=='libsndfile_window_decode_error'


def test_bundle_window_tracks_context_protocol_without_changing_legacy_default():
    from scripts.train_raga_svc import training_window_seconds
    assert training_window_seconds({})==60
    assert training_window_seconds(dict(context_plan_sha256='hash',protocol=dict(window_s=180)))==180
    with pytest.raises(ValueError,match='window metadata'):
        training_window_seconds(dict(context_plan_sha256='hash'))


def test_context_window_grid_is_bounded_and_deduplicates_short_tracks():
    assert window_starts(1000,.01,180)==[0]
    assert window_starts(24000,.01,180)==[1200,3000,4800]
    with pytest.raises(ValueError):window_starts(0,.01,180)


def test_reference_pitch_context_features_and_resume(tmp_path,monkeypatch):
    from scripts import extract_context_training as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'sha',lambda p:'fixed')
    t=np.arange(2000)*.01;f=220*2**(.15*np.sin(t))
    np.savetxt(tmp_path/'pitch.txt',np.c_[t,f])
    row=dict(track='reference',corpus='compmusic',contour='pitch.txt',contour_sha256='fixed',hop_s=.01,tonic=220)
    target=extract_track((row,str(tmp_path/'out'),'plan',180))
    with np.load(target,allow_pickle=False) as z:
        assert z['X'].shape==(1,5280) and z['legacy'].shape==(1,4800)
        assert np.isfinite(z['X']).all()
    assert extract_track((row,str(tmp_path/'out'),'plan',180))==target
    with pytest.raises(ValueError,match='plan changed'):extract_track((row,str(tmp_path/'out'),'other',180))
    monkeypatch.setattr(module,'sha',lambda p:'changed')
    with pytest.raises(ValueError,match='contour changed'):extract_track((row,str(tmp_path/'out'),'plan',180))
