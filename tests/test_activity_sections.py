import numpy as np
import pytest
from carnatify.audio.sections import section_activity,plan_activity_queries,artist_class_weights


def test_tani_variants_not_confused_with_tanam():
    assert section_activity('tani_avartana')=='percussion'
    assert section_activity('tani_avartanam')=='percussion'
    assert section_activity('thanam')=='melodic_music'
    assert section_activity('tanam')=='melodic_music'
    assert section_activity('-') is None


def test_three_queries_stay_within_explicit_section():
    row=dict(track='one',audio='one.wav',sections=[dict(start_s=100,end_s=130,kind='tani_avartana')])
    queries=plan_activity_queries([row])
    assert [r['start_s'] for r in queries]==[104.,110.,116.]
    assert len({r['section_id'] for r in queries})==1


def test_weights_balance_artists_and_classes_without_clip_count_inflation():
    y=np.array([0,0,0,0,1,1]);groups=np.array(['A','A','A','B','C','C'])
    w=artist_class_weights(y,groups)
    np.testing.assert_allclose(w[y==0].sum(),w[y==1].sum())
    np.testing.assert_allclose(w[groups=='A'].sum(),w[groups=='B'].sum())


def test_conflicting_section_labels_fail_closed():
    row=dict(track='one',audio='one.wav',sections=[dict(start_s=0,end_s=100,kind='tani'),
        dict(start_s=0,end_s=100,kind='pallavi')])
    with pytest.raises(ValueError,match='Conflicting'):
        plan_activity_queries([row])
