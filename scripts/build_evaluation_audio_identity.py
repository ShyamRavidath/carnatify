"""Build evaluation audio hash receipts before training; no predictions needed."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.raga_pipeline import sha,write_json


def build(corpus,root):
    rows=[];seen=set()
    for row in corpus['rows']:
        if row['track'] in seen:raise ValueError('Duplicate evaluation track identifier')
        seen.add(row['track'])
        path=(root/row['audio']).resolve()
        if not path.is_relative_to(root.resolve()):raise ValueError('Evaluation audio escapes repository')
        rows.append(dict(track=row['track'],audio=row['audio'],metadata=dict(audio_sha256=sha(path))))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    rows=build(json.loads(args.corpus.read_text()),ROOT)
    write_json(args.out,dict(corpus_sha256=sha(args.corpus),rows=rows,
               policy='Reserve all supplied evaluation audio before training; no label/prediction filtering'))
    print(f'Pinned {len(rows)} evaluation audio files')


if __name__=='__main__':main()
