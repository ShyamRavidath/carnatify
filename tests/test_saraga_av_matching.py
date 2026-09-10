import pytest
from scripts.saraga_av_matching import mixture_lookup,match_mixture,recording_identity


def test_case_normalization_and_corroborated_artist_join():
    paths=['metadata/Shruthi Bhat/Tamasa miga/x.json',
           'metadata/Hari Krishan/Eti Janmamidhi/x.json',
           'metadata/Hari Krishan/Raga Ratnamalikache/x.json']
    rows=[{'path':'saraga audio/Shruthi Bhat/Tamasa Miga/Tamasa Miga.wav'},
          {'path':'saraga audio/Hari Kishan/Eti Janmamidhi/Eti Janmamidhi.wav'},
          {'path':'saraga audio/Hari Kishan/Raga Ratnamalikache/Raga Ratnamalikache.wav'}]
    lookup,aliases,evidence=mixture_lookup(rows,paths)
    assert match_mixture(paths[0],lookup,aliases)==rows[0]
    assert match_mixture(paths[1],lookup,aliases)==rows[1]
    assert len(evidence['Hari Krishan']['exact_shared_titles'])==2
    with pytest.raises(ValueError):
        mixture_lookup(rows[:2],paths)


def test_ambiguous_folded_mixture_rejected():
    with pytest.raises(ValueError):
        mixture_lookup([{'path':'root/A/Title/Title.wav'},
                        {'path':'root/A/title/title.wav'}],[])


def test_recording_key_does_not_use_repeated_artist_mbid():
    a=recording_identity({'path':'root/Artist/Song A/Song A.wav'})
    b=recording_identity({'path':'root/Artist/Song B/Song B.wav'})
    assert a!=b
    assert a==recording_identity({'path':'root/Artist/Song A/Song A.wav'})
