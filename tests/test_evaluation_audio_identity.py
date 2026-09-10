import hashlib
import pytest
from scripts.build_evaluation_audio_identity import build
from scripts.quarantine_audio_overlap import quarantined_groups


def test_audio_reserved_without_any_model_or_labels(tmp_path):
    p=tmp_path/'recording.mp3';p.write_bytes(b'example bytes')
    row=dict(track='recording',audio=p.name)
    result=build(dict(rows=[row]),tmp_path)
    assert result[0]['metadata']['audio_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='Duplicate'):
        build(dict(rows=[row,row]),tmp_path)
    with pytest.raises(ValueError,match='escapes'):
        build(dict(rows=[dict(row,audio='../outside.mp3')]),tmp_path)


def test_unverified_sources_cannot_enter_strict_pipeline():
    row=dict(track='a',audio='a.mp3',group='g',corpus='archive')
    evidence=dict(audio='a.mp3',sha256='hash',status='no_exact_cached_match')
    assert 'g' in quarantined_groups([row],{'a':evidence},set(),True)
    evidence['status']='shared_across_items'
    assert not quarantined_groups([row],{'a':evidence},set(),True)
