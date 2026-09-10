import pytest
from scripts.benchmark_concert_transitions import score_windows, score_timeline


def test_mixed_contexts_are_not_silently_given_dominant_gold():
    truth = [dict(start_s=0., end_s=90., kind='music', raga='Todi'),
             dict(start_s=90., end_s=100., kind='silence'),
             dict(start_s=100., end_s=190., kind='music', raga='Bhairavi')]
    def window(a,b,p):
        return dict(start_s=a,end_s=b,status='candidate',probabilities=p)
    result = score_windows([window(0,60,{'Todi':1}), window(60,120,{'Todi':1}),
                            window(100,160,{}), window(90,100,{})], truth)
    assert result['n_pure']==2 and result['n_pure_correct']==1
    assert result['pure_accuracy']==.5 and result['n_mixed']==1
    assert result['rows'][1]['correct'] is None
    assert result['rows'][3]['correct'] is None


def test_incomplete_truth_is_rejected():
    with pytest.raises(ValueError, match='cover'):
        score_windows([dict(start_s=0,end_s=60,status='candidate')], [])


def test_timeline_scores_all_music_not_only_answered_regions():
    truth = [dict(start_s=0, end_s=90, kind='music', raga='Todi'),
             dict(start_s=90, end_s=100, kind='silence'),
             dict(start_s=100, end_s=190, kind='music', raga='Bhairavi')]
    segments = [dict(start_s=0,end_s=120,status='unverified_candidate',
                     candidates=[dict(raga='Todi')]),
                dict(start_s=120,end_s=190,status='uncertain',candidates=[])]
    result = score_timeline(segments, truth)
    assert result['musical_s'] == 180
    assert result['candidate_correct_s'] == 90
    assert result['candidate_accuracy'] == .5
    assert result['candidate_coverage_s'] == 110
    assert result['asserted_identity_s'] == 0


def test_context_cap_uses_silence_not_raga_or_percussion_predictions():
    from scripts.concert_pipeline import silence_bounded_end
    events = [dict(start_s=40,end_s=50,state='percussion'),
              dict(start_s=90,end_s=100,state='silence'),
              dict(start_s=190,end_s=200,state='silence')]
    assert silence_bounded_end(0,180,events) == 90
    assert silence_bounded_end(90,270,events) == 100
    assert silence_bounded_end(100,280,events) == 190
    assert silence_bounded_end(200,290,events) == 290
    assert silence_bounded_end(0,60,events) == 60


def test_silence_energy_ignores_only_short_edge_transients():
    import numpy as np
    from scripts.concert_pipeline import interior_silence
    y=np.zeros(160000);y[:160]=.01;y[-160:]=.01
    assert interior_silence(y,16000)
    y[50000:50160]=.01
    assert not interior_silence(y,16000)
    assert not interior_silence(np.full(160000,.0001),16000)
    assert not interior_silence(np.zeros(10),16000)
    assert not interior_silence(np.full(16000,np.nan),16000)


def test_silence_end_anchors_close_grid_coverage_gaps():
    from scripts.concert_pipeline import context_query_starts
    events=[dict(state='silence',end_s=100),dict(state='silence',end_s=200),
            dict(state='silence',end_s=290)]
    ordinary=context_query_starts(290,events)
    bounded=context_query_starts(290,events,True)
    assert set(bounded)-set(ordinary)=={100.,200.}
    assert 290 not in bounded and len(bounded)==len(set(bounded))
