"""Separate classifier transfer from live pitch extraction on identical intervals.

Distributed pitch tracks are a reference front end, not human framewise gold.
This diagnostic must not be reported as live-audio inference accuracy.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from normalize_ragas import fold
from scripts.raga_pipeline import sha,write_json
from carnatify.ml.melody_features import feature_vector


def main():
    cp=ROOT/'data/overhaul/annotated_corpus.json';bp=ROOT/'data/overhaul/saraga_combined_results.json'
    mp=ROOT/'data/overhaul/combined/raga_ridge.joblib'
    corpus={r['track']:r for r in json.loads(cp.read_text())['rows']}
    baseline=json.loads(bp.read_text())['rows'];model=joblib.load(mp)['model']
    rows=[]
    with threadpool_limits(limits=4):
        for row in baseline:
            truth=corpus[row['track']];meta=row['metadata']
            r=dict(track=row['track'],raga=row['raga'],in_vocabulary=row['predictions']['combined_estimated']['in_vocabulary'],
                   reference_correct=False,reference_answered=False,
                   live_estimated_correct=row['predictions']['combined_estimated']['correct'],
                   live_annotated_correct=row['predictions']['combined_annotated']['correct'])
            if truth['pitch']:
                d=np.loadtxt(ROOT/truth['pitch']);hop=float(np.median(np.diff(d[:,0])))
                start,end=meta['start_s'],meta['end_s'];selection=(d[:,0]>=start)&(d[:,0]<end)
                v=feature_vector(d[selection,1],truth['tonic'],hop,'voiced')
                if v is not None:
                    p=model.predict_proba(v[None])[0];prediction=str(model.classes_[p.argmax()])
                    r.update(reference_answered=True,reference_prediction=prediction,
                             reference_correct=fold(prediction)==fold(truth['raga']))
                cache=ROOT/f'data/overhaul/cache/saraga_audio/{meta["audio_sha256"][:32]}_center60_v1.npz'
                with np.load(cache) as z:f=z['f0']
                times=start+np.arange(len(f))*128/44100
                i=np.searchsorted(d[:,0],times).clip(1,len(d)-1)
                i=np.where(abs(d[i-1,0]-times)<abs(d[i,0]-times),i-1,i)
                valid=abs(d[i,0]-times)<=hop
                reference=d[i,1];both=valid&(f>0)&(reference>0)
                if both.any():
                    cents=np.abs((1200*np.log2(f[both]/reference[both])+600)%1200-600)
                    r['octave_equivalent_agreement_50c']=float(np.mean(cents<50))
                    r['compared_voiced_frames']=int(both.sum())
                r['reference_pitch_sha256']=sha(ROOT/truth['pitch'])
            rows.append(r)
    known=[r for r in rows if r['in_vocabulary']]
    summary={key:sum(r[key] for r in known) for key in ['reference_correct','live_estimated_correct','live_annotated_correct']}
    summary['n_known']=len(known)
    report=dict(status='Reference-front-end diagnostic, not human pitch gold or deployable audio accuracy',
                corpus_sha256=sha(cp),baseline_sha256=sha(bp),model_sha256=sha(mp),summary=summary,rows=rows)
    write_json(ROOT/'data/overhaul/pitch_transfer_diagnostic.json',report);print(summary)


if __name__=='__main__':main()
