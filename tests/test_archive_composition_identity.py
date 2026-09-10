from scripts.build_composition_catalog import specific_title,reference_work_id
from normalize_ragas import fold


def test_generic_improvisation_names_do_not_become_compositions():
    for title in ['Alapana','Ragam Tanam Pallavi','Kalyani RTP','Thillana','']:
        assert not specific_title(title)
    assert specific_title('sarOjadhalanEtri')


def test_work_join_is_exact_unambiguous_and_otherwise_provisional():
    known={(fold('Example'),fold('Raga')):{'annotated-id'}}
    assert reference_work_id('Example','Raga',known)=='annotated-id'
    assert reference_work_id('Unseen','Raga',known).startswith('weak-title:')
    known[(fold('Example'),fold('Raga'))].add('conflicting-id')
    assert reference_work_id('Example','Raga',known).startswith('weak-title:')
