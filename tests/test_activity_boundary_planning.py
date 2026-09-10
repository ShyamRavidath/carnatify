import pytest
from scripts.benchmark_activity_boundaries import explicit_truth,segments_from_states


def test_unknown_gaps_remain_unlabeled_and_tanam_is_music():
    sections=[dict(start_s=0,end_s=12,kind='tanam'),dict(start_s=15,end_s=25,kind='tani')]
    assert explicit_truth(sections,5,20)==[dict(start_s=5,end_s=12,truth='music'),dict(start_s=15,end_s=20,truth='percussion')]


def test_same_class_overlap_is_unioned_but_conflicts_rejected():
    sections=[dict(start_s=0,end_s=15,kind='pallavi'),dict(start_s=10,end_s=20,kind='charanam')]
    assert explicit_truth(sections,0,20)==[dict(start_s=0,end_s=20,truth='music')]
    sections[-1]['kind']='tani'
    with pytest.raises(ValueError,match='Conflicting'):explicit_truth(sections,0,20)


def test_segment_merging_preserves_gaps():
    assert segments_from_states([0,10,30],[0,0,0])==[
        dict(start_s=0,end_s=20,kind='melodic_music'),dict(start_s=30,end_s=40,kind='melodic_music')]
