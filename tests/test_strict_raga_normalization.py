from normalize_ragas import build_fold_index, resolve


def test_distinct_names_never_fuzzy_merge():
    index = build_fold_index(['Aṭāna', 'Bilahari', 'Kalyāṇi', 'Dvijāvanti',
                              'Kāmavardani', 'Nāṭakurinji', 'Kānaḍa'])
    for raw in ['jayantasEna', 'malahari', 'kalAnidhi', 'vijayasri',
                'subhapantuvarali', 'kurinji', 'kannada']:
        assert resolve(raw, index, list(index)) is None


def test_exact_and_explicit_transliteration():
    index = build_fold_index(['Kalyāṇi', 'Hamsadhvāni', 'Ārabhi'])
    assert resolve('kalyANi', index, []) == 'Kalyāṇi'
    assert resolve('hamsadwani', index, []) == 'Hamsadhvāni'
    assert resolve('arabhi', index, []) == 'Ārabhi'
    assert resolve('todi', index, []) is None  # target not in supplied taxonomy
