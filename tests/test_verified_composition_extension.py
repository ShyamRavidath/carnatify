import pytest
from scripts.build_compmusic_compositions import verified_single_work,duplicate_recording_reason,improvisation_work

RID='9aa2770a-c170-4db9-9657-14a74024bc31'
WID='11d3ea14-7cb2-4a8e-b77b-232e7fb86af0'


def test_catalog_extension_rechecks_original_relation():
    work={'work_id':WID,'title':'Work'}
    row=dict(recording_id=RID,works=[work],status='single_explicit_work')
    receipt=dict(status=200,recording=dict(id=RID,relations=[
        {'type':'performance','target-type':'work','work':{'id':WID,'title':'Work'}}]))
    assert verified_single_work(row,receipt)==work
    row['works'][0]['title']='Fabricated'
    with pytest.raises(ValueError,match='disagree'):verified_single_work(row,receipt)


def test_missing_work_is_not_filled_from_title():
    row=dict(recording_id=RID,works=[],status='no_work_link',title='Known title')
    assert verified_single_work(row,dict(status=404,recording=None)) is None


def test_one_recording_cannot_be_counted_as_two_renditions():
    recordings={RID:{'work_id':WID}}
    assert duplicate_recording_reason(RID,WID,recordings)=='duplicate_recording'
    assert duplicate_recording_reason(RID,'different',recordings)=='conflicting_work_for_same_recording'
    assert duplicate_recording_reason('new',WID,recordings) is None


def test_generic_improvisation_entity_is_not_a_named_composition():
    assert improvisation_work('Kedaragaula Ragam','Kēdāragauḷa')
    assert improvisation_work('Kedaragaula Ragam Vocal Violin','Kēdāragauḷa')
    assert improvisation_work('Ragam Tanam Pallavi','Todi')
    assert not improvisation_work('Ragamalika Tillana','Ragamalika')
    assert not improvisation_work('Nadamadi','Kambhoji')
