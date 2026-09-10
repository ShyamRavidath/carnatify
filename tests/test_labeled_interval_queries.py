import pytest
from scripts.evaluate_labeled_intervals import plan_queries


def test_longest_interval_once_per_item_and_no_new_labels():
    base=dict(item_id='one',concert='c1',raga='A',primary=True,confidence='high')
    labels={'intervals':[{**base,'start_s':2,'end_s':755},
                         {**base,'start_s':1440,'end_s':1503},
                         {**base,'item_id':'weak','start_s':1600,'end_s':2000,'primary':False}]}
    queries=plan_queries(labels)
    assert len(queries)==1
    assert queries[0]['start_s']==288.5
    assert queries[0]['duration_s']==180
    labels['intervals'][1]['raga']='B'
    with pytest.raises(ValueError):
        plan_queries(labels)
