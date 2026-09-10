import numpy as np
import pytest
from scripts.calibrate_composition_rejection import connected_groups,signals


def test_artist_and_work_links_are_transitive():
    rows=[dict(track=str(i),work_id=w) for i,w in enumerate(['w1','w1','w2','w3'])]
    corpus={str(i):dict(work_id=r['work_id'],artists=[a]) for i,(r,a) in enumerate(zip(rows,['a','b','b','c']))}
    groups=connected_groups(rows,corpus)
    assert groups[0]==groups[1]==groups[2] and groups[3]!=groups[0]


def test_duplicate_query_rejected():
    row=dict(track='a',work_id='w');corpus={'a':dict(work_id='w',artists=['artist'])}
    with pytest.raises(ValueError):connected_groups([row,row],corpus)


def test_signals_are_bounded_and_no_candidate_is_not_confident():
    assert signals({'top5':[]})==(0.,0.)
    p,m=signals({'top5':[{'distance':.2},{'distance':.4}]})
    assert 0<p<=1 and m==.5
    assert signals({'top5':[{'distance':.2}]})[1]==0
    with pytest.raises(ValueError):signals({'top5':[{'distance':np.nan}]})


def test_joint_rank_calibration_uses_explicit_joint_cost():
    row={'top5':[{'distance':.3,'ranking_cost':.31},{'distance':.25,'ranking_cost':.35}]}
    with pytest.raises(ValueError):signals(row)
    proximity,margin=signals(row,'ranking_cost')
    assert proximity==pytest.approx(1/1.31) and margin==pytest.approx(.04/.35)
