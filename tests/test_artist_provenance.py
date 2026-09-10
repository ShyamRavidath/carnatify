from scripts.merge_raga_training import artist_key, known_artist


def test_missing_manifest_artist_uses_existing_provenance():
    assert known_artist({'track': 'a'}, {'a': {'artist': 'K V Narayanaswamy'}}) == 'K V Narayanaswamy'
    assert artist_key('K V Narayanaswamy') == artist_key('K V Narayanaswami')
    assert known_artist({'track': 'a'}, {}) is None
    assert known_artist({'track': 'a', 'artist': '78 RPM recordings part 1'}, {}) is None
