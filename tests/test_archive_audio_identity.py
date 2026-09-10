import hashlib
import json
import pytest
from scripts.audit_archive_audio_identity import digests, matches, source_status, refreshed_entries


def test_refreshed_metadata_receipt_must_match_bytes(tmp_path):
    raw = json.dumps(dict(metadata=dict(identifier='item'), files=[dict(name='audio', md5='123')])).encode()
    p = tmp_path / 'raw.json'
    p.write_bytes(raw)
    receipt = dict(status='ok', identifier='item', raw_file=p.name, raw_sha256=hashlib.sha256(raw).hexdigest())
    (tmp_path / 'result.json').write_text(json.dumps(dict(completed=1, expected=1, rows=[receipt])))
    entries, hashes = refreshed_entries(tmp_path)
    assert entries[0]['identifier'] == 'item'
    assert hashes[p.name] == receipt['raw_sha256']
    p.write_bytes(b'{}')
    with pytest.raises(ValueError, match='Stale'):
        refreshed_entries(tmp_path)


def test_identity_requires_bytes_size_and_available_sha1(tmp_path):
    p = tmp_path / 'audio'
    p.write_bytes(b'concert bytes')
    h = digests(p)
    entry = dict(size=p.stat().st_size, **h)
    assert matches(entry, p.stat().st_size, h)
    assert not matches(dict(entry, md5='wrong'), p.stat().st_size, h)
    assert not matches(dict(entry, sha1='wrong'), p.stat().st_size, h)
    assert not matches(entry, 1, h)
    assert not matches(dict(size='bad', md5=h['md5']), 1, h)


def test_source_assignment_does_not_override_hash_evidence():
    assert source_status('a', []) == 'no_exact_cached_match'
    assert source_status('a', [dict(identifier='b')]) == 'assigned_source_mismatch'
    assert source_status('A', [dict(identifier='a')]) == 'assigned_source_confirmed'
    assert source_status('a', [dict(identifier='a'), dict(identifier='b')]) == 'shared_across_items'
