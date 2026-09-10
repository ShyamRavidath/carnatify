"""Frozen fresh-artist evaluation; no tuning after inspecting these predictions."""
from __future__ import annotations
import argparse,json,sys,multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from threadpoolctl import threadpool_limits
from scripts.raga_pipeline import sha,write_json
from scripts.evaluate_annotated_raga import extract
from normalize_ragas import fold
from carnatify.ml.melody_features import feature_vector
from carnatify.ml.inference_runtime import serial_forest_prediction

MODELS={'combined':ROOT/'data/overhaul/combined/raga_ridge.joblib',
        'forest800':ROOT/'data/overhaul/raga_forest800.joblib',
        'multiscale':ROOT/'data/overhaul/multiscale/raga.joblib'}


def verify_download_receipts(rows,download,plan_sha256,root=ROOT):
    if download['plan_sha256']!=plan_sha256:
        raise ValueError('Download receipt belongs to another selection')
    downloaded={r['track']:r for r in download['rows']}
    if len(downloaded)!=len(download['rows']):raise ValueError('Duplicate download receipt identity')
    for row in rows:
        receipt=downloaded.get(row['track'])
        if not receipt or sha(root/row['audio'])!=receipt['audio_sha256']:
            raise ValueError('Audio changed or lacks a frozen-download receipt')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage',choices=['freeze','extract-available','score','validate-candidate'])
    ap.add_argument('--model',type=Path)
    ap.add_argument('--out',type=Path)
    ap.add_argument('--window-s',type=int,choices=[60,180],default=60)
    ap.add_argument('--run',type=Path,default=ROOT/'data/overhaul/saraga_av')
    args=ap.parse_args();base=args.run.resolve()
    original_run=base==(ROOT/'data/overhaul/saraga_av').resolve()
    plan_path=base/'evaluation_plan.json';plan=json.loads(plan_path.read_text())
    frozen_path=base/'comparators.json'
    validation=args.stage=='validate-candidate'
    if validation:
        if not args.model or not args.out:ap.error('validate-candidate requires --model and --out')
        if args.out.resolve() in {p.resolve() for p in [plan_path,frozen_path,base/'fresh_results.json']}:
            ap.error('Post-development validation must not overwrite frozen evidence')
    elif args.out or (original_run and (args.model or args.window_s!=60)) or (args.model and args.stage!='freeze'):
        ap.error('Changed models/context require validate-candidate, not the frozen test stages')
    if args.stage=='freeze':
        if frozen_path.exists():raise ValueError('Comparator protocol already frozen')
        freeze_models={**MODELS}
        if args.model:freeze_models['broader']=args.model.resolve()
        write_json(frozen_path,dict(plan_sha256=sha(plan_path),models={name:dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
            for name,p in freeze_models.items()},query=f'deterministic center {args.window_s} seconds with estimated tonic only',
            window_s=args.window_s,
            metrics='top1 all; paired common-vocabulary top1; top3; empirical threshold precision',
            status='frozen before inspecting any fresh audio predictions'))
        print('Comparator hashes frozen');return
    protocol=json.loads(frozen_path.read_text())
    if protocol['plan_sha256']!=sha(plan_path):raise ValueError('Frozen selection changed')
    if not validation and args.window_s!=protocol.get('window_s',60):
        raise ValueError('Requested duration differs from frozen query protocol')
    if validation:
        protocol={**protocol,'models':{**protocol['models'],'candidate':dict(
            path=str(args.model.resolve().relative_to(ROOT)),sha256=sha(args.model))},
            'query':f'deterministic center {args.window_s} seconds; estimated tonic',
            'status':'post-development validation on previously inspected AV cohort; not fresh test'}
    rows=[dict(r,audio=str((base/'audio'/(r['track']+'.wav')).relative_to(ROOT))) for r in plan['rows']]
    available=[dict(r,window_s=args.window_s) for r in rows if (ROOT/r['audio']).exists()]
    if (args.stage=='score' or validation) and len(available)!=len(rows):
        raise ValueError(f'Fresh test is incomplete: {len(available)}/{len(rows)} WAVs')
    download=json.loads((base/'download.json').read_text())
    verify_download_receipts(available,download,sha(plan_path))
    for r in available:
        if sha(ROOT/r['metadata'])!=r['metadata_sha256']:raise ValueError('Metadata changed after freeze')
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        paths=list(pool.map(extract,available))
    if args.stage=='extract-available':
        print(f'{len(available)}/{len(rows)} fresh audio features cached; no predictions made');return
    import joblib
    models={}
    for name,entry in protocol['models'].items():
        if sha(ROOT/entry['path'])!=entry['sha256']:raise ValueError('Comparator changed after freeze')
        models[name]=joblib.load(ROOT/entry['path'])
        serial_forest_prediction(models[name]['model'])
    report=dict(plan_sha256=sha(plan_path),original_protocol_sha256=sha(frozen_path),protocol=protocol,
                rows=[],summary={},window_s=args.window_s,
                status=('post-development validation on previously inspected cohort; not fresh or SOTA evidence'
                        if validation else 'fresh known-raga test; not natural-prevalence, open-set or SOTA evidence'))
    with threadpool_limits(limits=4):
        for row,path in zip(available,paths):
            with np.load(path) as z:f=z['f0'];meta=json.loads(str(z['meta']))
            preds={};voiced=float(np.sum(np.isfinite(f)&(f>0))*128/44100)
            for name,bundle in models.items():
                m=bundle['model'];truth=fold(row['raga'])
                p=dict(in_vocabulary=truth in {fold(c) for c in m.classes_},answered=False,
                       correct=False,top3_correct=False,accepted=False)
                if voiced>=10 and meta['tonic_estimated']:
                    v=feature_vector(f,meta['tonic_estimated'],128/44100,bundle['representation'])
                    if v is not None:
                        probabilities=m.predict_proba(v[None])[0];order=np.argsort(-probabilities)[:3]
                        p.update(answered=True,correct=fold(m.classes_[order[0]])==truth,
                            top3_correct=truth in {fold(m.classes_[i]) for i in order},
                            top3=[str(m.classes_[i]) for i in order],confidence=float(probabilities[order[0]]),
                            accepted=bool(probabilities[order[0]]>=bundle['calibration']['gate']['threshold']))
                preds[name]=p
            report['rows'].append(dict(track=row['track'],artist=row['artist'],truth=row['raga'],
                                       metadata=meta,predictions=preds))
    for name in models:
        p=[r['predictions'][name] for r in report['rows']];accepted=[x for x in p if x['accepted']]
        report['summary'][name]=dict(n=len(p),correct=sum(x['correct'] for x in p),
            top1=float(np.mean([x['correct'] for x in p])),top3=float(np.mean([x['top3_correct'] for x in p])),
            in_vocabulary=sum(x['in_vocabulary'] for x in p),accepted=len(accepted),
            accepted_precision=float(np.mean([x['correct'] for x in accepted])) if accepted else None)
    common=[r for r in report['rows'] if all(p['in_vocabulary'] for p in r['predictions'].values())]
    report['common_vocabulary']=dict(n=len(common),correct={name:sum(r['predictions'][name]['correct'] for r in common) for name in models})
    write_json(args.out if validation else base/'fresh_results.json',report)
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__':main()
