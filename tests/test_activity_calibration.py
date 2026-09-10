from carnatify.audio.events import calibrated_event


def test_relative_activity_evidence_preserves_original_scores():
    e=dict(state='music',music=.8,percussion=.5,melodic=.05)
    c=dict(ratio_threshold=.62,min_percussion_score=.35)
    result=calibrated_event(e,c)
    assert e['state']=='music' and result['state']=='percussion'
    assert result['raw_state']=='music' and result['music']==e['music']
    assert calibrated_event(dict(e,melodic=.8),c)['state']=='music'
    assert calibrated_event(dict(e,state='speech'),c)['state']=='speech'
