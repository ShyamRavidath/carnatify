"""Score new voiced-TDMS models on frozen historical field features.

This is diagnostic: several field sources/artists and labels remain unresolved,
and byte disjointness does not establish independent performances of excerpts.
No scope restriction to a favorable subset of model classes is applied.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from normalize_ragas import fold
from scripts.raga_pipeline import sha,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--models',nargs='+',type=Path,required=True)
    ap.add_argument('--audio-root',type=Path,default=Path('/Users/shyamravidath/sung_tests'))
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/cached_field_results.json')
    args=ap.parse_args();base=ROOT/'data/raga_wild'
    frozen=json.loads((base/'FROZEN_CLIPS.json').read_text());features={}
    protocol=json.loads((base/'protocol.json').read_text())
    plans={name:next((w for w in windows if w['kind']=='w60'),windows[0])
           for name,windows in protocol['window_plan'].items()}
    for row in frozen['clips']:
        p=args.audio_root/row['file']
        if sha(p)!=row['sha256']:raise ValueError(f'Frozen audio changed: {p}')
    for path in sorted((base/'rows').glob('*.npz')):
        with np.load(path) as z:
            md=json.loads(str(z['meta']));plan=plans.get(md['file'])
            if not plan or md['window']!=plan['kind']:continue
            if abs(md['dur_s']-plan['dur_s'])>1e-4 or abs(md['start_s']-plan['start_s'])>1e-4:
                raise ValueError(f'Feature window differs from frozen plan: {path}')
            features[md['file']]=(md,{k:z[k] for k in z.files if k!='meta'},sha(path))
    report=dict(status='historical field diagnostic; not proven source/artist/label independent',
        window_policy='registered w60 if present; otherwise registered whole <=60s clip',
        n_feature_files=len(features),frozen_sha256=sha(base/'FROZEN_CLIPS.json'),
        protocol_sha256=sha(base/'protocol.json'),models={})
    with threadpool_limits(limits=4):
        for path in args.models:
            bundle=joblib.load(path)
            if bundle['representation']!='voiced':raise ValueError('Cached contract is voiced TDMS only')
            model=bundle['model'];rows=[]
            for truth in frozen['clips']:
                item=features.get(truth['file'])
                for arm in ['mix','mix_voiceband','demucs']:
                    r=dict(file=truth['file'],truth=truth['raga_canonical'],arm=arm,correct=False,accepted=False,
                           answered=False,in_vocabulary=fold(truth['raga_canonical']) in {fold(c) for c in model.classes_})
                    if item:
                        md,feats,digest=item;r['feature_sha256']=digest
                        r['tonic_fallback']=md['tonic']['fallback']
                        key='tdms_'+arm
                        if key in feats and md['arms'][arm].get('voiced_s',0)>=10:
                            p=model.predict_proba(feats[key][None])[0];order=np.argsort(-p)[:3]
                            r.update(answered=True,top3=[str(model.classes_[i]) for i in order],
                                confidence=float(p[order[0]]),correct=fold(model.classes_[order[0]])==fold(r['truth']),
                                accepted=bool(p[order[0]]>=bundle['calibration']['gate']['threshold']))
                    rows.append(r)
            summary={}
            for arm in ['mix','mix_voiceband','demucs']:
                a=[r for r in rows if r['arm']==arm];accepted=[r for r in a if r['accepted']]
                summary[arm]=dict(n=len(a),correct=sum(r['correct'] for r in a),
                    top1=sum(r['correct'] for r in a)/len(a),n_answered=sum(r['answered'] for r in a),
                    n_accepted=len(accepted),accepted_precision=sum(r['correct'] for r in accepted)/len(accepted) if accepted else None)
            report['models'][str(path)]=dict(model_sha256=sha(path),summary=summary,rows=rows)
            write_json(args.out,report);print(str(path),json.dumps(summary),flush=True)


if __name__=='__main__':main()
