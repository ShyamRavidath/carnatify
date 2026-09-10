"""Conservatively union training groups using checksum-bound file artist tags.

No person-name guessing or musical relabeling. Unknown aliases/ensemble strings
remain unresolved; this is not proof of complete performer independence.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json,load_features
from scripts.raga_audit_protocol import DSU
from scripts.merge_raga_training import artist_key
from carnatify.audio.cache_io import atomic_npz


def artist_tags(value):
    values=[value] if isinstance(value,str) else value
    if not isinstance(values,list):return []
    ignored={'unknown','various','variousartists','carnaticmusic','unknownartist','na'}
    return sorted({v.strip() for v in values if isinstance(v,str) and v.strip() and artist_key(v) not in ignored})


def union_groups(rows,tags):
    dsu=DSU()
    for row in rows:
        dsu.find(row['group'])
        if row.get('artist'):dsu.union(row['group'],'artist:'+artist_key(row['artist']))
        for artist in tags.get(row['track'],[]):dsu.union(row['group'],'artist:'+artist_key(artist))
    members={}
    for row in rows:members.setdefault(dsu.find(row['group']),set()).add(row['group'])
    return {r['track']:min(members[dsu.find(r['group'])]) for r in rows}


def reserved_groups(rows,tags,groups,reserved):
    return {groups[r['track']] for r in rows if
            ({artist_key(a) for a in tags.get(r['track'],[])} |
             ({artist_key(r['artist'])} if r.get('artist') else set())) & reserved}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--identity',type=Path,default=ROOT/'data/overhaul/all_archive_audio_identity_refreshed.json')
    parser.add_argument('--metadata',type=Path,default=ROOT/'data/overhaul/all_archive_metadata')
    parser.add_argument('--reserved-corpus',type=Path,help='Exclude connected groups matching exact reserved artist names')
    args=parser.parse_args()
    if args.run.resolve()==args.out.resolve() or (args.out/'manifest.json').exists():raise ValueError('Use a new separate run')
    source=args.run/'manifest.json';manifest=json.loads(source.read_text());rows=manifest['rows']
    identities={r['track']:r for r in json.loads(args.identity.read_text())['rows']}
    receipt=args.metadata/'result.json';report=json.loads(receipt.read_text())
    if report['completed']!=report['expected']:raise ValueError('Metadata incomplete')
    metadata={};digests={}
    for r in report['rows']:
        if r['status']!='ok':continue
        path=args.metadata/r['raw_file']
        if not path.resolve().is_relative_to(args.metadata.resolve()) or sha(path)!=r['raw_sha256']:
            raise ValueError('Publisher metadata changed')
        raw=json.loads(path.read_text())
        if raw['metadata']['identifier']!=r['identifier']:raise ValueError('Publisher identity changed')
        metadata[r['identifier']]=raw;digests[r['identifier']]=r['raw_sha256']
    tags={};evidence={}
    for row in rows:
        if row.get('corpus')!='archive':continue
        ident=identities[row['track']]
        if row['audio']!=ident['audio']:raise ValueError('Training audio path changed')
        names={c['name'] for c in ident['candidates'] if c['identifier']==row['source']}
        files=[f for f in metadata[row['source']]['files'] if f['name'] in names]
        if not files:raise ValueError('Exact publisher file missing')
        names_found=[]
        for f in files:
            if int(f['size'])!=ident['size'] or f.get('md5')!=ident['md5'] or f.get('sha1')!=ident['sha1']:
                raise ValueError('Publisher audio identity changed')
            names_found.extend(artist_tags(f.get('artist')))
        tags[row['track']]=sorted(set(names_found))
        evidence[row['track']]=dict(artists=tags[row['track']],audio_sha256=ident['sha256'],
                                  publisher_metadata_sha256=digests[row['source']])
    groups=union_groups(rows,tags)
    reserved=set()
    if args.reserved_corpus:
        reserved={artist_key(a) for r in json.loads(args.reserved_corpus.read_text())['rows'] for a in r['artists']}
    denied=reserved_groups(rows,tags,groups,reserved)
    newrows=[dict(r,group=groups[r['track']],publisher_file_artists=tags.get(r['track'],[]))
             for r in rows if groups[r['track']] not in denied]
    audit=dict(n_tracks=len(rows),n_groups_before=len({r['group'] for r in rows}),n_groups_after=len(set(groups.values())),
        n_archival_with_file_artist=sum(bool(v) for v in tags.values()),n_archival_without_file_artist=sum(not v for v in tags.values()),
        retained_tracks=len(newrows),excluded_reserved_artist_groups=sorted(denied),
        removed_tracks=[r['track'] for r in rows if groups[r['track']] in denied],
        evidence=evidence,limitation='Exact known names only; unresolved aliases, ensemble strings and incorrect publisher tags remain possible')
    inputs={str(p.resolve().relative_to(ROOT)):sha(p) for p in (source,args.run/'features.npz',args.identity,receipt,Path(__file__))}
    if args.reserved_corpus:inputs[str(args.reserved_corpus.resolve().relative_to(ROOT))]=sha(args.reserved_corpus)
    write_json(args.out/'manifest.json',dict(manifest,rows=newrows,file_artist_grouping=audit,regrouping_inputs=inputs))
    z=load_features(args.run);arrays={k:z[k] for k in z.files}
    mask=np.isin(z['track'],[r['track'] for r in newrows])
    for key in ('X','legacy','y','track','group'):arrays[key]=arrays[key][mask]
    arrays['group']=np.array([groups[str(t)] for t in arrays['track']]);arrays['manifest_sha256']=np.array(sha(args.out/'manifest.json'))
    atomic_npz(args.out/'features.npz',**arrays);write_json(args.out/'grouping.json',audit)
    print(json.dumps({k:v for k,v in audit.items() if k!='evidence'}))


if __name__=='__main__':main()
