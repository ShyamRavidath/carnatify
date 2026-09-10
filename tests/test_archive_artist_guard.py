from scripts.guard_archive_evaluation_artists import matched_creators


def test_only_exact_creator_evidence_matches_not_description_or_substrings():
    artists=['Akkarai Sisters','S Sundar']
    assert matched_creators({'creator':'Akkarai Sisters'},artists)==['Akkarai Sisters']
    assert matched_creators({'creator':['AKKARAI SISTERS']},artists)==['Akkarai Sisters']
    assert not matched_creators({'description':'Akkarai Sisters'},artists)
    assert not matched_creators({'creator':'S Sundararajan'},artists)
    assert not matched_creators({'creator':None},artists)
