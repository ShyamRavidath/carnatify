"""Guard creator/recording overlap and exclude failed or unaudited audio decodes.

Unknown creators remain unresolved. This is not a claim of full artist-disjoint
training; no fuzzy person matching or creator-name guessing is used.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.merge_raga_training import artist_key
from scripts.raga_pipeline import sha,write_json,load_features


def matched_creators(metadata,artists):
    creator=metadata.get('creator',[])
    creator=[creator] if isinstance(creator,str) else creator
    if not isinstance(creator,list):return []
    keys={artist_key(a):a for a in artists if a}
    return sorted({keys[artist_key(c)] for c in creator if isinstance(c,str) and artist_key(c) in keys})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,default=ROOT/'data/overhaul/archive_training_metadata')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--audio-identity',type=Path,required=True)
    parser.add_argument('--decode-inventory',type=Path,default=ROOT/'data/overhaul/recording_fingerprints/result.json')
    parser.add_argument('--confirmed-overlaps',type=Path,default=ROOT/'data/overhaul/recording_fingerprints/verified_overlap.json')
    args=parser.parse_args()
    if args.run.resolve()==args.out.resolve() or (args.out/'manifest.json').exists():
        raise ValueError('Use a new separate artist-guarded run')
    source=args.metadata/'result.json';report=json.loads(source.read_text())
    if report['completed']!=report['expected']:raise ValueError('Metadata inventory incomplete')
    corpus=json.loads(args.corpus.read_text());artists={a for r in corpus['rows'] for a in r.get('artists',[])}
    metadata={};receipts={}
    for receipt in report['rows']:
        if receipt['status']!='ok':continue
        path=args.metadata/receipt['raw_file']
        if not path.resolve().is_relative_to(args.metadata.resolve()) or sha(path)!=receipt['raw_sha256']:
            raise ValueError('Publisher metadata receipt changed')
        md=json.loads(path.read_text())['metadata']
        if md['identifier'].casefold()!=receipt['identifier'].casefold():raise ValueError('Item identity mismatch')
        metadata[receipt['identifier']]=md;receipts[receipt['identifier']]=receipt['raw_sha256']
    identity={r['track']:r for r in json.loads(args.audio_identity.read_text())['rows']}
    inventory=json.loads(args.decode_inventory.read_text())
    if inventory['completed']!=inventory['expected']:raise ValueError('Decode inventory incomplete')
    decoded={r['sha256']:r.get('status','ok') for r in inventory['rows'] if r['role']=='train'}
    confirmed=json.loads(args.confirmed_overlaps.read_text())
    for path,digest in confirmed['inputs'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Confirmed copy evidence changed')
    evaluation_tracks={r['track'] for r in corpus['rows']}
    copies={r['reference_audio_sha256']:r for r in confirmed['rows']
            if r['status']=='confirmed_same_decoded_pcm' and r['query'] in evaluation_tracks}
    manifest=json.loads((args.run/'manifest.json').read_text());bad={};unknown=[];decode_excluded=[]
    for row in manifest['rows']:
        if row.get('corpus')!='archive':continue
        evidence=identity[row['track']]
        if evidence['audio']!=row['audio']:raise ValueError('Training audio identity path changed')
        digest=evidence['sha256']
        if decoded.get(digest)!='ok':decode_excluded.append(row['track'])
        if digest in copies:
            bad.setdefault(row['group'],[]).append(dict(track=row['track'],reason='confirmed_evaluation_pcm_copy',
                query=copies[digest]['query'],audio_sha256=digest))
        md=metadata.get(row['source'],{})
        matches=matched_creators(md,artists)
        if matches:
            bad.setdefault(row['group'],[]).append(dict(track=row['track'],source=row['source'],artists=matches,
                metadata_sha256=receipts[row['source']]))
        if not md.get('creator'):unknown.append(row['track'])
    denied=set(decode_excluded)
    kept=[r for r in manifest['rows'] if r['group'] not in bad and r['track'] not in denied]
    allowed={r['track'] for r in kept};z=load_features(args.run);mask=np.isin(z['track'],list(allowed))
    audit=dict(policy='whole connected group exclusion for exact normalized publisher creator/evaluation artist match or confirmed evaluation PCM copy; individual exclusion for failed or unaudited decode',
               matched_groups=bad,removed_tracks=[r['track'] for r in manifest['rows'] if r['group'] in bad or r['track'] in denied],
               decode_failed_or_unaudited_tracks=decode_excluded,
               unknown_creator_tracks=unknown,
               unknown_creator_tracks_scope='input cohort before exclusions; publisher creator field only',
               limitation='Creators may be absent or incomplete; performer aliases and unknown artists are not resolved')
    inputs={str(p.resolve().relative_to(ROOT)):sha(p) for p in (args.run/'manifest.json',args.run/'features.npz',args.corpus,
        source,args.audio_identity,args.decode_inventory,args.confirmed_overlaps)}
    write_json(args.out/'manifest.json',dict(manifest,rows=kept,inputs=inputs,artist_guard=audit))
    arrays={k:(z[k][mask] if z[k].ndim and len(z[k])==len(mask) else z[k]) for k in z.files}
    arrays['manifest_sha256']=np.array(sha(args.out/'manifest.json'))
    np.savez_compressed(args.out/'features.npz',**arrays)
    write_json(args.out/'artist_guard.json',audit)
    print(json.dumps(dict(retained_tracks=len(kept),removed_tracks=len(audit['removed_tracks']),
                          excluded_groups=len(bad),unknown_creator_tracks=len(unknown))))


if __name__=='__main__':main()
