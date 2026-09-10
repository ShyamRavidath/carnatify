"""Fetch public archive file checksums into a separate, resumable audit cache.

No audio downloads, no mutation of legacy metadata or training manifests.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.raga_pipeline import sha, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', type=Path, default=ROOT / 'data/overhaul/archive_audio_identity.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'data/overhaul/archive_identity_metadata')
    parser.add_argument('--sources', nargs='+', help='Explicit subset of source IDs already present in the audit')
    parser.add_argument('--training-manifest',type=Path,help='Fetch sources used by this archival training cohort')
    parser.add_argument('--reuse-cache',type=Path,help='Reuse verified full-metadata receipts without network requests')
    args = parser.parse_args()
    audit = json.loads(args.identity.read_text())
    identifiers = sorted({r['source'] for r in audit['rows'] if r['status'] == 'no_exact_cached_match'})
    if args.sources:
        if not set(args.sources) <= {r['source'] for r in audit['rows']}:
            raise ValueError('Explicit source is outside the audited corpus')
        identifiers = sorted(set(args.sources))
    if args.training_manifest:
        if args.sources:raise ValueError('Choose explicit sources or a training manifest, not both')
        identifiers=sorted({r['source'] for r in json.loads(args.training_manifest.read_text())['rows']
                            if r.get('corpus')=='archive'})
        if not set(identifiers)<={r['source'] for r in audit['rows']}:
            raise ValueError('Training source is outside identity audit')
    plan = dict(identity_sha256=sha(args.identity), identifiers=identifiers,
                endpoint='https://archive.org/metadata/', purpose='public file checksums only')
    if args.training_manifest:plan['training_manifest_sha256']=sha(args.training_manifest)
    args.out.mkdir(parents=True, exist_ok=True)
    plan_path = args.out / 'plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError('Existing fetch plan differs')
    write_json(plan_path, plan)
    results = []
    for identifier in identifiers:
        key = hashlib.sha256(identifier.encode()).hexdigest()
        receipt_path = args.out / (key + '.json')
        if not receipt_path.exists() and args.reuse_cache:
            prior_path=args.reuse_cache/(key+'.json')
            if prior_path.exists():
                prior=json.loads(prior_path.read_text())
                if prior.get('status')=='ok':
                    if prior['identifier']!=identifier or prior['raw_file']!=key+'.raw.json':
                        raise ValueError('Reusable metadata identity mismatch')
                    raw_path=args.reuse_cache/prior['raw_file']
                    if sha(raw_path)!=prior['raw_sha256']:raise ValueError('Reusable metadata changed')
                    (args.out/prior['raw_file']).write_bytes(raw_path.read_bytes())
                    write_json(receipt_path,prior)
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if receipt['identifier'] != identifier:
                raise ValueError('Cached identifier mismatch')
            if receipt.get('status') == 'ok' and sha(args.out / receipt['raw_file']) == receipt['raw_sha256']:
                results.append(receipt)
                continue
        url = 'https://archive.org/metadata/' + quote(identifier, safe='')
        receipt = dict(identifier=identifier, url=url, status='error')
        for attempt in range(3):
            try:
                request = Request(url, headers={'User-Agent': 'Carnatify-research-provenance-audit/1.0'})
                with urlopen(request, timeout=30) as response:
                    raw = response.read(16 * 1024 * 1024 + 1)
                if len(raw) > 16 * 1024 * 1024:
                    raise ValueError('Metadata exceeds bounded response size')
                metadata = json.loads(raw)
                if not isinstance(metadata.get('files'), list) or not metadata['files']:
                    raise ValueError('No public file listing')
                if metadata.get('metadata', {}).get('identifier', '').casefold() != identifier.casefold():
                    raise ValueError('Returned item identifier mismatch')
                raw_path = args.out / (key + '.raw.json')
                temporary = raw_path.with_suffix('.tmp')
                temporary.write_bytes(raw)
                temporary.replace(raw_path)
                receipt.update(status='ok', raw_file=raw_path.name, raw_sha256=sha(raw_path),
                               files=len(metadata['files']), attempt=attempt + 1)
                break
            except Exception as exc:
                receipt['error'] = f'{type(exc).__name__}: {exc}'
                if attempt < 2:
                    time.sleep(1 + attempt)
        write_json(receipt_path, receipt)
        results.append(receipt)
        write_json(args.out / 'result.json', dict(plan_sha256=sha(plan_path), rows=results,
                   completed=len(results), expected=len(identifiers)))
        print(f'{len(results)}/{len(identifiers)} {identifier}: {receipt["status"]}', flush=True)
        time.sleep(.3)
    write_json(args.out / 'result.json', dict(plan_sha256=sha(plan_path), rows=results,
               completed=len(results), expected=len(identifiers)))


if __name__ == '__main__':
    main()
