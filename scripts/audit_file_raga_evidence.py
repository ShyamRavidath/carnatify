"""Audit explicit delimited publisher filename/title raga tokens; no relabeling."""
import json
import argparse
import re
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from normalize_ragas import build_fold_index,resolve,fold
from scripts.raga_pipeline import sha,write_json


def explicit_tokens(text,vocab):
    if not isinstance(text,str):return []
    # No arbitrary substring scan: e.g. Todi must not match Hanumatodi.
    parts=re.split(r'[-_–—|()]',re.sub(r'\.(mp3|flac|wav|ogg|m4a)$','',text,flags=re.I))
    results=[]
    parts=[re.sub(r'^\s*\d+[.\s]*','',part).strip() for part in parts]
    index=0
    while index<len(parts):
        # Longest explicit compound first: Ananda-bhairavi is not Bhairavi.
        for width in range(min(3,len(parts)-index),0,-1):
            token=' '.join(parts[index:index+width])
            label=resolve(token,vocab,list(vocab))
            if label:
                results.append(dict(token=token,label=label));index+=width;break
        else:index+=1
    return results


def main():
    run=ROOT/'data/overhaul/repro_audio_identity'
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=run/'train_integrity_guarded/manifest.json')
    parser.add_argument('--identity',type=Path,default=run/'audio_identity.json')
    parser.add_argument('--metadata',type=Path,default=ROOT/'data/overhaul/archive_training_metadata')
    parser.add_argument('--out',type=Path,default=run/'file_raga_evidence.json')
    parser.add_argument('--include-unmarked-archive',action='store_true')
    args=parser.parse_args()
    manifest=args.manifest;identity=args.identity;metadata=args.metadata;receipt=metadata/'result.json'
    rows=json.loads(manifest.read_text())['rows'];vocab=build_fold_index(sorted({r['label'] for r in rows}))
    identities={r['track']:r for r in json.loads(identity.read_text())['rows']}
    publishers={}
    for entry in json.loads(receipt.read_text())['rows']:
        if entry['status']!='ok':continue
        path=metadata/entry['raw_file']
        if not path.resolve().is_relative_to(metadata.resolve()) or sha(path)!=entry['raw_sha256']:
            raise ValueError('Publisher receipt changed')
        raw=json.loads(path.read_text())
        if raw['metadata']['identifier']!=entry['identifier']:raise ValueError('Publisher identifier changed')
        publishers[entry['identifier']]=(raw,entry['raw_sha256'])
    results=[]
    for row in rows:
        if row.get('corpus')!='archive' and not (
                args.include_unmarked_archive and 'corpus' not in row and row['track'].startswith('archive__')):continue
        ident=identities[row['track']];raw,receipt_sha=publishers[row['source']]
        if ident['audio']!=row['audio']:raise ValueError('Audio path changed')
        names={c['name'] for c in ident['candidates'] if c['identifier']==row['source']}
        files=[f for f in raw['files'] if f['name'] in names]
        if not files:
            results.append(dict(track=row['track'],label=row['label'],source=row['source'],
                status='unresolved_publisher_file_identity',audio_sha256=ident['sha256'],evidence=[]))
            continue
        evidence=[]
        for f in files:
            if int(f['size'])!=ident['size'] or f.get('md5')!=ident['md5'] or f.get('sha1')!=ident['sha1']:
                raise ValueError('Published audio identity changed')
            for field in ('name','title'):
                for token in explicit_tokens(f.get(field),vocab):
                    evidence.append(dict(field=field,text=f[field],**token))
        labels={fold(e['label']) for e in evidence};expected=fold(row['label'])
        status=('no_explicit_file_tag' if not labels else 'file_tag_consistent' if labels=={expected}
                else 'file_tag_conflict_or_ambiguous')
        results.append(dict(track=row['track'],label=row['label'],source=row['source'],status=status,
            audio_sha256=ident['sha256'],publisher_metadata_sha256=receipt_sha,evidence=evidence))
    report=dict(policy='exact vocabulary/explicit alias on delimited file name and title fields; no label changes',
        inputs={str(p.resolve().relative_to(ROOT)):sha(p) for p in (manifest,identity,receipt,Path(__file__),ROOT/'normalize_ragas.py')},
        counts=dict(Counter(r['status'] for r in results)),rows=results,
        limitation='Publisher tags are weak supervision; title words may resemble ragas. Conflicts require diagnosis, not automatic relabeling.')
    report['include_unmarked_archive']=args.include_unmarked_archive
    write_json(args.out,report);print(json.dumps(report['counts']))


if __name__=='__main__':main()
