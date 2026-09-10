"""Read-only byte identity audit; never treats title/size agreement as proof.

Cached archive MD5 identifies a candidate; size and any published SHA1 must
also agree. Local SHA256 pins every audited file. This does NOT authenticate
raga labels, performer identity, or correspondence with cached pitch contours.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digests(path):
    hashes = {name: hashlib.new(name) for name in ('md5', 'sha1', 'sha256')}
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            for h in hashes.values():
                h.update(block)
    return {name: h.hexdigest() for name, h in hashes.items()}


def matches(entry, size, hashes):
    try:
        return (int(entry.get('size', -1)) == size
                and str(entry.get('md5', '')).lower() == hashes['md5']
                and (not entry.get('sha1')
                     or str(entry['sha1']).lower() == hashes['sha1']))
    except (TypeError, ValueError):
        return False


def source_status(source, candidates):
    ids = {c['identifier'].casefold() for c in candidates}
    if not ids:
        return 'no_exact_cached_match'
    if str(source).casefold() not in ids:
        return 'assigned_source_mismatch'
    return 'assigned_source_confirmed' if len(ids) == 1 else 'shared_across_items'


def refreshed_entries(directory):
    """Read only checksum-pinned successful receipts; fail on modified caches."""
    report = json.loads((directory / 'result.json').read_text())
    if report['completed'] != report['expected']:
        raise ValueError('Metadata refresh is incomplete')
    entries, hashes = [], {}
    for receipt in report['rows']:
        if receipt['status'] != 'ok':
            continue
        path = directory / receipt['raw_file']
        if path.parent.resolve() != directory.resolve():
            raise ValueError('Metadata receipt path escapes cache')
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != receipt['raw_sha256']:
            raise ValueError('Stale refreshed metadata receipt')
        metadata = json.loads(raw)
        identifier = receipt['identifier']
        if metadata['metadata']['identifier'].casefold() != identifier.casefold():
            raise ValueError('Refreshed identifier mismatch')
        entries.extend(dict(e, identifier=identifier) for e in metadata['files'] if isinstance(e, dict))
        hashes[path.name] = digest
    return entries, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'data/overhaul/broader/train/manifest.json')
    parser.add_argument('--metadata', type=Path, default=ROOT / 'data/raga_v2_cache/archive_metadata')
    parser.add_argument('--out', type=Path, default=ROOT / 'data/overhaul/archive_audio_identity.json')
    parser.add_argument('--refreshed-metadata', type=Path)
    parser.add_argument('--include-unmarked-archive',action='store_true',
                        help='Audit legacy archive__ rows lacking a corpus field; no training admission')
    args = parser.parse_args()
    index = defaultdict(list)
    metadata_hashes = {}
    for path in sorted(args.metadata.glob('*.json')):
        raw = path.read_bytes()
        metadata_hashes[path.name] = hashlib.sha256(raw).hexdigest()
        entries = json.loads(raw)
        if not isinstance(entries, list):
            raise ValueError(f'Unexpected metadata structure: {path}')
        for e in entries:
            if isinstance(e, dict) and e.get('md5'):
                index[str(e['md5']).lower()].append(dict(e, identifier=path.stem))
    refreshed_hashes = {}
    if args.refreshed_metadata:
        entries, refreshed_hashes = refreshed_entries(args.refreshed_metadata)
        for e in entries:
            if e.get('md5'):
                index[str(e['md5']).lower()].append(e)
    raw_manifest = args.manifest.read_bytes()
    rows = []
    duplicates = defaultdict(list)
    for r in json.loads(raw_manifest)['rows']:
        if r.get('corpus') != 'archive' and not (
                args.include_unmarked_archive and 'corpus' not in r and r['track'].startswith('archive__')):
            continue
        path = ROOT / r['audio']
        hashes = digests(path)
        size = path.stat().st_size
        candidates = [dict(identifier=e['identifier'], name=e.get('name'),
                           sha1_verified=bool(e.get('sha1')))
                      for e in index[hashes['md5']] if matches(e, size, hashes)]
        rows.append(dict(track=r['track'], label=r['label'], group=r['group'],
                         source=r['source'], audio=r['audio'], size=size, **hashes,
                         status=source_status(r['source'], candidates), candidates=candidates))
        duplicates[hashes['sha256']].append(r['track'])
        if len(rows) % 100 == 0:
            print(f'Hashed {len(rows)} archival files', flush=True)
    result = dict(schema=1, manifest_sha256=hashlib.sha256(raw_manifest).hexdigest(),
                  include_unmarked_archive=args.include_unmarked_archive,
                  metadata_sha256=metadata_hashes, refreshed_metadata_sha256=refreshed_hashes, rows=rows,
                  counts=dict(Counter(r['status'] for r in rows)),
                  duplicate_audio_groups=[v for v in duplicates.values() if len(v) > 1],
                  limitation='Byte identity only. Labels, artists, and pitch/audio correspondence remain separate checks.')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(args.out)
    print(json.dumps(dict(rows=len(rows), counts=result['counts'],
                          duplicate_groups=len(result['duplicate_audio_groups'])), indent=2))


if __name__ == '__main__':
    main()
