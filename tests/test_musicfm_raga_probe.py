import numpy as np
from scripts.benchmark_musicfm_raga import admit,groups_for,crossfit


def test_duplicates_and_conflicts_precede_class_support_filter():
    rows=[dict(track='a',raga='Todi'),dict(track='b',raga='Todi'),
          dict(track='c',raga='Bhairavi'),dict(track='d',raga='Ragamalika')]
    selected,conflicts=admit(rows,dict(a='same',b='same',c='other',d='third'),min_count=2)
    assert selected==[] and conflicts==[]
    selected,conflicts=admit(rows,dict(a='same',b='other',c='same',d='third'),min_count=1)
    assert [r['track'] for r in selected]==['b'] and conflicts==['same']


def test_group_connections_are_transitive():
    rows=[dict(track='a',artists=['Artist A'],source='one',audio_sha256='x'),
          dict(track='b',artists=['Artist A','Artist B'],source='two',audio_sha256='y'),
          dict(track='c',artists=['Artist B'],source='three',audio_sha256='z')]
    assert len(set(groups_for(rows)))==1


def test_crossfit_keeps_missing_queries_and_unseen_classes_in_denominator():
    X=np.eye(3);y=np.array(['A','A','B']);groups=np.array(['one','two','three'])
    result=crossfit(X,[True,False,True],y,groups)
    assert result['n']==3 and result['n_valid']==2 and result['predictions'][1] is None
    assert result['predictions'][2]=='A'  # B is not available in its training fold
    assert result['n_correct']==0
