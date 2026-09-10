import pytest
from carnatify.ml.evaluation_integrity import assert_unseen_tracks,assert_unseen_audio,training_support


def test_renamed_audio_bytes_and_legacy_admitted_ids_are_rejected():
    with pytest.raises(ValueError,match='audio bytes'):
        assert_unseen_audio({'training_audio_sha256':['hash']},'hash')
    assert assert_unseen_audio({'training_audio_sha256':['hash']},'other')
    assert not assert_unseen_audio({},'other')
    with pytest.raises(ValueError,match='training tracks'):
        assert_unseen_tracks({'admitted_tracks':['a']},[{'track':'a'}])


def test_training_audio_cannot_be_reported_as_independent():
    with pytest.raises(ValueError,match='training tracks'):
        assert_unseen_tracks({'training_track_ids':['a','b']},[{'track':'a'}])
    assert_unseen_tracks({'training_track_ids':['a','b']},[{'track':'c'}])


def test_overlapping_windows_do_not_inflate_class_support():
    result=training_support(['A']*3,['t1']*3,['concert1']*3)
    assert result['A']==dict(n_tracks=1,n_groups=1,limited_support=True)
    with pytest.raises(ValueError):training_support(['A'],[],[])
