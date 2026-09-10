"""Summarize completed experiments with paired artist-cluster uncertainty."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from normalize_ragas import fold
from scripts.raga_pipeline import sha,write_json


def paired_interval(delta,groups,seed=42,n_boot=5000):
    delta=np.asarray(delta,dtype=float);groups=np.asarray(groups)
    keys=np.unique(groups)
    if not len(keys):return None
    sums=np.array([delta[groups==g].sum() for g in keys])
    counts=np.array([np.sum(groups==g) for g in keys])
    idx=np.random.default_rng(seed).integers(0,len(keys),size=(n_boot,len(keys)))
    reps=sums[idx].sum(1)/counts[idx].sum(1)
    return dict(mean=float(delta.mean()),ci95=np.percentile(reps,[2.5,97.5]).tolist(),
                n=len(delta),n_clusters=len(keys),bootstrap=n_boot)


def main():
    base=ROOT/'data/overhaul'
    specs=[('saraga_audio_results.json','ridge'),('saraga_admitted_results.json','ridge'),
           ('saraga_compmusic_results.json','compmusic'),('saraga_combined_results.json','combined')]
    baseline_path=base/'saraga_forest800_results.json'
    baseline=json.loads(baseline_path.read_text())
    br={r['track']:r for r in baseline['rows']}
    corpus={r['track']:r for r in json.loads((base/'annotated_corpus.json').read_text())['rows']}
    out=dict(status='repeated development validation; not final untouched test or SOTA evidence',
             baseline_sha256=sha(baseline_path),comparisons={})
    for filename,name in specs:
        path=base/filename
        if not path.exists():continue
        report=json.loads(path.read_text())
        if len(report['rows'])!=report['n_selected']:continue
        matched=[]
        for r in report['rows']:
            b=br[r['track']]
            if r['metadata']!=b['metadata']:raise ValueError('Different audio query/extraction metadata')
            a=r['predictions'][name+'_estimated'];old=b['predictions']['forest800_estimated']
            if a['in_vocabulary'] and old['in_vocabulary']:
                # Saraga primary-artist groups coalesce that artist's concerts.
                artists=corpus[r['track']]['artists']
                group='|'.join(sorted(fold(s) for s in artists)) or corpus[r['track']]['group']
                matched.append((int(a['correct'])-int(old['correct']),group,int(a['correct']),int(old['correct'])))
        ci=paired_interval([r[0] for r in matched],[r[1] for r in matched])
        ci.update(candidate_correct=sum(r[2] for r in matched),baseline_correct=sum(r[3] for r in matched))
        out['comparisons'][filename]=dict(result_sha256=sha(path),
            external_summary=report['summary'][name+'_estimated'],
            matched_vocabulary_paired_difference=ci)
    write_json(base/'evidence_summary.json',out)
    for name,r in out['comparisons'].items():print(name,r['matched_vocabulary_paired_difference'])


if __name__=='__main__':main()
