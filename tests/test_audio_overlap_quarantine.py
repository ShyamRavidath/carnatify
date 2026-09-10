import pytest
from scripts.quarantine_audio_overlap import quarantined_groups, deduplicate_rows,exclude_documented_supervision
import hashlib


def test_duplicate_weight_removed_without_score_selection():
    rows = [dict(track=t, group='g', label='r') for t in ['b', 'a', 'c']]
    identities = {t: dict(sha256='same') for t in ['a', 'b']}
    kept, removed = deduplicate_rows(rows, identities)
    assert [r['track'] for r in kept] == ['a', 'c']
    assert removed == [dict(track='b', representative='a', audio_sha256='same')]
    rows[0]['label'] = 'other'
    with pytest.raises(ValueError, match='Conflicting labels'):
        deduplicate_rows(rows, identities)
    rows[0]['label'] = 'r'
    rows[0]['group'] = 'other'
    with pytest.raises(ValueError, match='crosses groups'):
        deduplicate_rows(rows, identities)


def test_whole_connected_groups_are_quarantined():
    rows = [dict(track=t, group=g, corpus='archive', audio=t) for t, g in
            [('a', 'g1'), ('b', 'g1'), ('c', 'g2'), ('d', 'g3')]]
    ids = {r['track']: dict(audio=r['audio'], sha256=r['track'],
                           status='assigned_source_confirmed') for r in rows}
    ids['c']['status'] = 'assigned_source_mismatch'
    reasons = quarantined_groups(rows, ids, {'a'})
    assert set(reasons) == {'g1', 'g2'}
    assert [r['track'] for r in rows if r['group'] not in reasons] == ['d']


def test_missing_or_changed_evidence_fails_closed():
    row = dict(track='a', group='g', corpus='archive', audio='a')
    with pytest.raises(ValueError, match='Missing'):
        quarantined_groups([row], {}, set())
    with pytest.raises(ValueError, match='path differs'):
        quarantined_groups([row], {'a': dict(audio='b')}, set())


def test_documented_mixed_program_exclusion_requires_pinned_evidence(tmp_path):
    p=tmp_path/'evidence.json';p.write_bytes(b'publisher metadata')
    exclusions=dict(rows=[dict(audio_sha256='bad',evidence_path=p.name,
        evidence_sha256=hashlib.sha256(p.read_bytes()).hexdigest())])
    rows=[dict(track='a'),dict(track='b')]
    kept,removed=exclude_documented_supervision(rows,{'a':dict(sha256='bad')},exclusions,tmp_path)
    assert kept==[rows[1]] and removed==['a']
    p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='evidence changed'):
        exclude_documented_supervision(rows,{},exclusions,tmp_path)
