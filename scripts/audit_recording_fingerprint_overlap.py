"""Flag possible re-encoded/excerpt copies; never automatically change labels.

Exact 32-bit landmark votes propose offsets; continuous 20s bit-error windows
verify candidates. This heuristic is a screening audit, not proof of absence.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json

POLICY=dict(max_code_occurrences=128,min_votes=8,offsets_per_pair=8,
            window_frames=160,min_unique_codes=32,max_bit_error=.1,
            action='flag only; independent audio verification required')


def make_index(queries):
    index=defaultdict(list);suppressed=set()
    for qi,values in enumerate(queries):
        for position,code in enumerate(values):
            code=int(code)
            if code in suppressed:continue
            index[code].append((qi,position))
            if len(index[code])>POLICY['max_code_occurrences']:
                del index[code];suppressed.add(code)
    return index


def scan(reference,queries,index):
    votes=Counter()
    for position,code in enumerate(reference):
        for qi,qp in index.get(int(code),()):
            votes[qi,position-qp]+=1
    offsets=defaultdict(list)
    for (qi,offset),count in votes.items():
        if count>=POLICY['min_votes']:offsets[qi].append((count,offset))
    flags=[];window=POLICY['window_frames']
    for qi,candidates in offsets.items():
        query=queries[qi];best=None
        for count,offset in sorted(candidates,key=lambda x:(-x[0],abs(x[1]),x[1]))[:POLICY['offsets_per_pair']]:
            q0,r0=max(0,-offset),max(0,offset)
            n=min(len(query)-q0,len(reference)-r0)
            if n<window:continue
            xor=np.bitwise_xor(query[q0:q0+n],reference[r0:r0+n])
            errors=np.unpackbits(xor.view(np.uint8)).reshape(n,32).mean(axis=1)
            sums=np.r_[0,np.cumsum(errors)]
            means=(sums[window:]-sums[:-window])/window
            for start in np.flatnonzero(means<=POLICY['max_bit_error']):
                q=query[q0+start:q0+start+window];r=reference[r0+start:r0+start+window]
                if min(len(np.unique(q)),len(np.unique(r)))<POLICY['min_unique_codes']:continue
                candidate=(float(means[start]),int(q0+start),int(r0+start),count,offset)
                if best is None or candidate<best:best=candidate
        if best:
            flags.append(dict(query_index=qi,bit_error=best[0],query_frame=best[1],reference_frame=best[2],
                              landmark_votes=best[3],offset_frames=best[4],window_frames=window))
    return flags


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features',type=Path,default=ROOT/'data/overhaul/recording_fingerprints/result.json')
    parser.add_argument('--out',type=Path,default=ROOT/'data/overhaul/recording_fingerprints/overlap.json')
    args=parser.parse_args()
    source=json.loads(args.features.read_text())
    if source['completed']!=source['expected'] or len(source['rows'])!=source['expected']:
        raise ValueError('Full fingerprint inventory is not complete')
    failures=[r for r in source['rows'] if r.get('status')=='decode_failed']
    queries=[r for r in source['rows'] if r['role']=='evaluation' and r not in failures]
    references=[r for r in source['rows'] if r['role']=='train' and r not in failures]
    def load(row):
        path=ROOT/row['cache']
        if sha(path)!=row['cache_sha256']:raise ValueError('Fingerprint cache changed')
        with np.load(path) as z:return z['values'].copy()
    query_values=[load(r) for r in queries];index=make_index(query_values)
    report=dict(input_sha256=sha(args.features),policy=POLICY,n_queries=len(queries),
                decode_failures=failures,
                expected_references=len(references),completed_references=0,flags=[],
                limitation='Screening only; zero flags would not prove recording or artist independence')
    for row in references:
        values=load(row)
        for flag in scan(values,query_values,index):
            query=queries[flag.pop('query_index')]
            report['flags'].append(dict(**flag,query=query['track'],reference=row['track'],
                                        query_audio_sha256=query['sha256'],reference_audio_sha256=row['sha256']))
        report['completed_references']+=1
        write_json(args.out,report)
        if report['completed_references']%50==0:
            print(f'{report["completed_references"]}/{len(references)}; flags {len(report["flags"])}',flush=True)
    print(f'Complete: {len(report["flags"])} candidate overlap pairs',flush=True)


if __name__=='__main__':main()
