import numpy as np
import pytest
from carnatify.ml.concert_segments import decode_concert,viterbi_states,candidate_only_segments


def test_development_threshold_is_not_validated_identity():
    source=[dict(status='recognized',raga='A',score=.95),
            dict(status='uncertain',raga=None,score=.1)]
    result=candidate_only_segments(source)
    assert result[0]['status']=='unverified_candidate'
    assert result[0]['raga'] is None and result[0]['candidate_raga']=='A'
    assert result[1]==source[1]
    assert source[0]['status']=='recognized'  # No mutation of decoder evidence.


def test_temporal_decoder_recovers_changes_and_rejects_isolated_glitch():
    p=np.r_[np.tile([.97,.02,.01],(20,1)),np.tile([.02,.97,.01],(20,1))]
    p[5]=[.1,.89,.01]
    states=viterbi_states(p,switch_penalty=3)
    assert np.all(states[:20]==0) and np.all(states[20:]==1)


def test_concert_annotations_require_no_human_boundaries():
    events=[dict(start_s=i*10,end_s=(i+1)*10,state='music' if i<6 or i>=9 else 'speech') for i in range(15)]
    windows=[dict(start_s=0,end_s=60,probabilities={'A':.98,'B':.02}),
             dict(start_s=90,end_s=150,probabilities={'A':.01,'B':.99})]
    out=decode_concert(events,windows,['A','B'],threshold=.8)
    assert out[0]['start_s']==0 and out[-1]['end_s']==150
    assert out[0]['raga']=='A' and out[-1]['raga']=='B'
    assert any(s['kind']=='speech' and s['raga'] is None for s in out)
    assert all(a['end_s']==b['start_s'] for a,b in zip(out,out[1:]))
    assert all(s['label_origin']=='automatic_prediction' for s in out)


def test_invalid_decoder_input():
    for p in [np.zeros((2,3)),np.full((2,3),np.nan),np.ones((2,1))]:
        with pytest.raises(ValueError):viterbi_states(p)


def test_isolated_percussion_tag_does_not_split_accompanied_music():
    events=[dict(start_s=i*10,end_s=(i+1)*10,
                 state='percussion' if i==5 else 'music') for i in range(15)]
    windows=[dict(start_s=0,end_s=150,probabilities={'A':.95,'B':.05})]
    out=decode_concert(events,windows,['A','B'],threshold=.8)
    assert len(out)==1 and out[0]['raga']=='A'


def test_low_confidence_raga_drift_does_not_create_song_boundaries():
    events=[dict(start_s=i*10,end_s=(i+1)*10,state='music') for i in range(30)]
    windows=[dict(start_s=0,end_s=150,probabilities={'A':.55,'B':.45}),
             dict(start_s=150,end_s=300,probabilities={'A':.45,'B':.55})]
    out=decode_concert(events,windows,['A','B'],threshold=.8)
    assert len(out)==1 and out[0]['raga'] is None


def test_weak_pitch_activity_scores_do_not_become_hard_boundaries():
    events=[dict(start_s=i*10,end_s=(i+1)*10,
                 state='percussion' if 5<=i<8 else 'music',
                 pitch_percussion_probability=.51 if 5<=i<8 else .1) for i in range(20)]
    windows=[dict(start_s=0,end_s=200,probabilities={'A':.95,'B':.05})]
    out=decode_concert(events,windows,['A','B'],threshold=.8)
    assert len(out)==1 and out[0]['kind']=='melodic_music'


def test_sustained_strong_pitch_activity_evidence_creates_percussion_region():
    events=[dict(start_s=i*10,end_s=(i+1)*10,
                 state='percussion' if 5<=i<13 else 'music',
                 pitch_percussion_probability=.99 if 5<=i<13 else .01) for i in range(20)]
    windows=[dict(start_s=0,end_s=200,probabilities={'A':.95,'B':.05})]
    out=decode_concert(events,windows,['A','B'],threshold=.8)
    assert [(r['start_s'],r['end_s']) for r in out if r['kind']=='percussion']==[(50,130)]


def test_distinct_nonmusic_states_are_not_merged_into_one_majority_label():
    events=[dict(start_s=i*10,end_s=(i+1)*10,state=state)
            for i,state in enumerate(['speech']*3+['applause']*3+['silence']*3)]
    out=decode_concert(events,[],['A','B'])
    assert [(r['start_s'],r['end_s'],r['kind']) for r in out]==[
        (0,30,'speech'),(30,60,'applause'),(60,90,'silence')]
    assert all(r['raga'] is None for r in out)
