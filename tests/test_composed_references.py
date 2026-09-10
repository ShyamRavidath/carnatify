import numpy as np
import pytest
from carnatify.ml.melody_retrieval import composed_reference_sequences


def test_composed_passages_do_not_join_across_improvisation():
    times=np.arange(3000)*.01;f=np.full(len(times),220.)
    sections=[dict(start_s=0,end_s=10,kind='pallavi'),
              dict(start_s=10,end_s=20,kind='kalpana_svaram'),
              dict(start_s=20,end_s=30,kind='charanam')]
    result=composed_reference_sequences(f,times,220,.01,sections)
    assert len(result)==2 and all(len(r)==20 for r in result)


def test_unannotated_fallback_differs_from_known_improvisation_only():
    times=np.arange(1000)*.01;f=np.full(len(times),220.)
    assert len(composed_reference_sequences(f,times,220,.01,[]))==1
    assert composed_reference_sequences(f,times,220,.01,[dict(start_s=0,end_s=10,kind='tanam')])==[]


def test_overlapping_composed_ranges_are_not_duplicated():
    times=np.arange(2000)*.01;f=np.full(len(times),220.)
    sections=[dict(start_s=0,end_s=15,kind='pallavi'),dict(start_s=10,end_s=20,kind='anupallavi')]
    result=composed_reference_sequences(f,times,220,.01,sections)
    assert len(result)==1 and len(result[0])==40


def test_invalid_time_grid_fails_closed():
    with pytest.raises(ValueError,match='time grid'):
        composed_reference_sequences([220,220],[1,0],220,.01,[])


def test_muktayi_svara_is_composed_not_kalpana_improvisation():
    times=np.arange(1000)*.01;f=np.full(len(times),220.)
    for kind in ['mukthayi_svara','mukthayi_svaram','muktayi_svara','muktayi_svaram']:
        assert len(composed_reference_sequences(f,times,220,.01,[dict(start_s=0,end_s=10,kind=kind)]))==1
