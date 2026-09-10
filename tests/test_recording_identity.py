import pytest
from scripts.saraga_recording_identity import recording_from_metadata,same_recording

RID='662dbd9a-6858-4899-9369-8079c6c22935'
WID='11d3ea14-7cb2-4a8e-b77b-232e7fb86af0'


def test_recording_identity_does_not_depend_on_artist_spelling():
    assert same_recording({'recording_id':RID,'artist':'alias a'},{'recording_id':RID,'artist':'alias b'})
    assert not same_recording({}, {})


def test_artist_id_is_not_accepted_as_recording_id():
    with pytest.raises(ValueError,match='Artist ID'):
        recording_from_metadata({'work_id':WID},{'mbid':RID,'album_artists':[{'mbid':RID}]})


def test_frozen_work_identity_must_match_source_metadata():
    md={'mbid':RID,'work':[{'mbid':WID}]}
    assert recording_from_metadata({'work_id':WID},md)==RID
    with pytest.raises(ValueError,match='annotation changed'):recording_from_metadata({'work_id':'different'},md)
