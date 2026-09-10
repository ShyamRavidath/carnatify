"""Separate recording-level Ragamalika diagnostics without changing predictions."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from normalize_ragas import fold


def summarize(rows):
    excluded=[r['track'] for r in rows if fold(r['raga'])=='ragamalika']
    eligible=[r for r in rows if fold(r['raga'])!='ragamalika']
    arms=sorted({key for row in rows for key in row['predictions']})
    result={}
    for arm in arms:
        preds=[r['predictions'][arm] for r in eligible]
        known=[p for p in preds if p['in_vocabulary']]
        unknown=[p for p in preds if not p['in_vocabulary']]
        accepted=[p for p in preds if p['accepted']]
        result[arm]=dict(n=len(preds),n_correct=sum(p['correct'] for p in preds),
            n_known=len(known),n_known_correct=sum(p['correct'] for p in known),
            n_oov=len(unknown),n_oov_false_accepts=sum(p['accepted'] for p in unknown),
            n_accepted=len(accepted),n_accepted_correct=sum(p['correct'] for p in accepted))
    return dict(policy='recording label Ragamalika has no single-raga window truth; excluded from this separate summary only',
        excluded_mixed_recording_tracks=excluded,summary=result,
        limitation='Other labels remain recording-level, not time-aligned ground truth. Changed denominator is not a model gain.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    report=json.loads(args.report.read_text());corpus=json.loads(args.corpus.read_text())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(args.corpus)!=report['corpus_sha256']:raise ValueError('Source corpus changed')
    source={r['track']:r for r in corpus['rows']}
    seen=set()
    for row in report['rows']:
        if row['track'] in seen or source[row['track']]['raga']!=row['raga']:
            raise ValueError('Duplicate query or altered source label')
        seen.add(row['track'])
    result=summarize(report['rows'])
    result['inputs']={str(p):digest(p) for p in (args.report,args.corpus)}
    if args.out.resolve() in {args.report.resolve(),args.corpus.resolve()}:
        raise ValueError('Do not overwrite source artifacts')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
