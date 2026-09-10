import pytest
from scripts.build_annotated_corpus import canonical_metadata_raga,fold


def test_metadata_common_name_resolves_explicit_synonym():
    known={fold('Kāmavardani'):'Kāmavardani'}
    tag=dict(name='Kāmavardani/Pantuvarāḷi',common_name='kamavardani')
    assert canonical_metadata_raga(tag,known)=='Kāmavardani'


def test_unknown_or_conflicting_metadata_is_not_fuzzily_relabelled():
    known={fold('Kalyani'):'Kalyani',fold('Todi'):'Todi'}
    assert canonical_metadata_raga(dict(name='Kalanidhi'),known)=='Kalanidhi'
    with pytest.raises(ValueError,match='Conflicting'):
        canonical_metadata_raga(dict(name='Kalyani',common_name='todi'),known)
