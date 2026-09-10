import pytest
from scripts.score_activity_intervals import score_segments


def test_unlabeled_time_is_excluded_and_missing_predictions_are_errors():
    result=score_segments([dict(start_s=0,end_s=15,kind='melodic_music')],
        [dict(start_s=10,end_s=20,truth='music'),dict(start_s=30,end_s=40,truth='percussion')])
    assert result['labeled_duration_s']==20
    assert result['accuracy']==.25
    assert result['recall']=={'music':.5,'percussion':0.}
    assert result['confusion_duration_s']['music']['uncovered']==5


def test_fractional_boundaries_are_scored_by_duration():
    result=score_segments([dict(start_s=0,end_s=7.5,kind='melodic_music'),
        dict(start_s=7.5,end_s=20,kind='percussion')],
        [dict(start_s=0,end_s=10,truth='music'),dict(start_s=10,end_s=20,truth='percussion')])
    assert result['accuracy']==.875


def test_overlaps_cannot_double_count_correct_seconds():
    with pytest.raises(ValueError,match='overlapping'):
        score_segments([dict(start_s=0,end_s=20,kind='melodic_music'),
            dict(start_s=10,end_s=30,kind='melodic_music')],
            [dict(start_s=0,end_s=30,truth='music')])
