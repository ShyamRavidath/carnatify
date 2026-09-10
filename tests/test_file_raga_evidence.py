from scripts.audit_file_raga_evidence import explicit_tokens
from normalize_ragas import build_fold_index


def test_delimited_raga_with_track_number_and_extension():
    vocab=build_fold_index(['Todi','Bhairavi'])
    assert explicit_tokens('03 Alapana - Todi.mp3',vocab)==[dict(token='Todi',label='Todi')]
    assert explicit_tokens('01_Title_Bhairavi_Adi.mp3',vocab)==[dict(token='Bhairavi',label='Bhairavi')]


def test_no_substring_or_fuzzy_guessing():
    vocab=build_fold_index(['Todi','Bhairavi'])
    assert explicit_tokens('Hanumatodi-song.mp3',vocab)==[]
    assert explicit_tokens('song-Bhairav.mp3',vocab)==[]
    assert explicit_tokens(None,vocab)==[]


def test_longest_explicit_compound_prevents_parent_name_false_positive():
    vocab=build_fold_index(['Anandabhairavi','Bhairavi','Todi'])
    assert explicit_tokens('song-Ananda-bhairavi.mp3',vocab)==[dict(token='Ananda bhairavi',label='Anandabhairavi')]
    assert {r['label'] for r in explicit_tokens('lecture-Todi-Bhairavi.mp3',vocab)}=={'Todi','Bhairavi'}
