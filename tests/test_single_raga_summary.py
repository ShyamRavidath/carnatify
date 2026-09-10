import copy
from scripts.summarize_single_raga_evaluation import summarize


def test_mixed_recording_is_not_single_raga_oov_truth():
    pred=dict(in_vocabulary=False,correct=False,accepted=True)
    rows=[dict(track='mixed',raga='Rāgamālika',predictions={'arm':pred}),
          dict(track='single',raga='Dhenuka',predictions={'arm':pred})]
    before=copy.deepcopy(rows)
    result=summarize(rows)
    assert result['excluded_mixed_recording_tracks']==['mixed']
    assert result['summary']['arm']['n_oov_false_accepts']==1
    assert result['summary']['arm']['n']==1
    assert rows==before


def test_known_raga_counts_are_preserved():
    row=dict(track='one',raga='Todi',predictions={'arm':dict(in_vocabulary=True,correct=True,accepted=True)})
    result=summarize([row])['summary']['arm']
    assert result['n_known_correct']==1 and result['n_accepted_correct']==1
