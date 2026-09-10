"""Merge verified decoder recovery only after the parent extraction completes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json,load_features
from carnatify.audio.cache_io import atomic_npz


def checked_recovery(run,recovery):
    parent=run/'plan.json';plan=json.loads(parent.read_text())
    rp=recovery/'plan.json';rplan=json.loads(rp.read_text())
    result=json.loads((recovery/'result.json').read_text())
    if result['plan_sha256']!=sha(rp) or rplan['inputs'].get(str(parent.resolve()))!=sha(parent):
        raise ValueError('Recovery parent/result plan mismatch')
    row=rplan['row'];source={r['track']:r for r in plan['rows']}
    if source.get(row['track'])!=row:raise ValueError('Recovery row not in parent cohort')
    if sha(ROOT/row['audio'])!=row['audio_sha256']:raise ValueError('Recovery raw audio changed')
    track=run/'tracks'/(hashlib.sha256(row['track'].encode()).hexdigest()+'.npz')
    if rplan['inputs'].get(str(track.resolve()))!=sha(track):raise ValueError('Parent track cache changed')
    with np.load(track,allow_pickle=False) as z:
        if str(z['plan_sha256'])!=sha(parent):raise ValueError('Parent track plan mismatch')
        meta=json.loads(str(z['metadata']))
    rejected=[r for r in meta['rejected'] if r['reason']=='libsndfile_window_decode_error']
    if rejected!=rplan['windows'] or len(result['windows'])!=len(rejected):
        raise ValueError('Recovery does not cover the recorded decoder rejections')
    windows=[]
    for i,(expected,receipt) in enumerate(zip(rejected,result['windows'])):
        path=recovery/f'window_{i}.npz'
        with np.load(path,allow_pickle=False) as z:
            if str(z['plan_sha256'])!=sha(rp) or json.loads(str(z['metadata']))!=receipt:
                raise ValueError('Recovery window receipt mismatch')
            a=z['X'];b=z['legacy'];f=z['f0']
        if a.shape!=(5280,) or b.shape!=(4800,) or f.ndim!=1 or not all(np.isfinite(v).all() for v in (a,b,f)):
            raise ValueError('Invalid recovered feature layout')
        if receipt['track']!=row['track'] or any(receipt[k]!=expected[k] for k in ('start_s','duration_s')):
            raise ValueError('Recovered query boundary mismatch')
        if any(w['contract']['start_s']==receipt['start_s'] for w in meta['windows']):
            raise ValueError('Recovery duplicates an accepted query')
        windows.append((a,b,dict(receipt,recovery_plan_sha256=sha(rp)),path))
    return row,windows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--recovery',type=Path,nargs='+',required=True)
    p.add_argument('--folds',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.resolve()==args.run.resolve() or any(args.out.resolve()==r.resolve() for r in args.recovery):
        raise ValueError('Use a separate merged output')
    # A progress file or partial track cache is never a completion certificate.
    completion=json.loads((args.run/'extraction.json').read_text())
    parent=json.loads((args.run/'plan.json').read_text())
    if (completion['plan_sha256']!=sha(args.run/'plan.json') or
            [r['track'] for r in completion['rows']]!=[r['track'] for r in parent['rows']]):
        raise ValueError('Parent extraction is incomplete or stale')
    manifest=json.loads((args.run/'manifest.json').read_text());z=load_features(args.run)
    if completion['windows']!=len(z['track']) or completion['tracks']!=len(manifest['rows']):
        raise ValueError('Parent completion counts disagree')
    arrays={k:list(z[k]) for k in ('X','legacy','y','track','group')}
    rows={r['track']:dict(r) for r in manifest['rows']};seen=set();added=[]
    inputs=[args.run/f for f in ('plan.json','extraction.json','manifest.json','features.npz')]+[args.folds,Path(__file__)]
    for recovery in args.recovery:
        row,windows=checked_recovery(args.run,recovery)
        if row['track'] in seen:raise ValueError('Duplicate recovery track')
        seen.add(row['track']);inputs.extend([recovery/'plan.json',recovery/'result.json'])
        updated=rows.setdefault(row['track'],dict(row,query_windows=[],training_frontend=parent['policy']))
        updated['recovered_query_windows']=[]
        for a,b,receipt,path in windows:
            for key,value in [('X',a),('legacy',b),('y',row['label']),('track',row['track']),('group',row['group'])]:
                arrays[key].append(value)
            updated['recovered_query_windows'].append(receipt);inputs.append(path);added.append(receipt)
    folds=json.loads(args.folds.read_text())
    if not set(arrays['track'])<=set(folds['folds']):raise ValueError('Missing fixed development fold')
    group_folds={}
    for track,group in zip(arrays['track'],arrays['group']):
        group_folds.setdefault(group,set()).add(folds['folds'][track])
    if any(len(v)!=1 for v in group_folds.values()):raise ValueError('Fixed folds split a source/artist group')
    plan=dict(inputs={str(f.resolve()):sha(f) for f in inputs},added=added,
        policy='append only verified decoder-rejected windows; preserve labels/groups and fixed development folds')
    target=args.out/'plan.json'
    if target.exists() and json.loads(target.read_text())!=plan:raise ValueError('Frozen merge plan changed')
    write_json(target,plan)
    write_json(args.out/'manifest.json',dict(manifest,rows=list(rows.values()),decoder_recovery_plan_sha256=sha(target)))
    atomic_npz(args.out/'features.npz',**{k:np.asarray(v) for k,v in arrays.items()},
        version=z['version'],manifest_sha256=sha(args.out/'manifest.json'))
    write_json(args.out/'folds.json',dict(folds,feature_sha256=sha(args.out/'features.npz'),
        parent_folds_sha256=sha(args.folds),folds={t:folds['folds'][t] for t in set(arrays['track'])}))
    write_json(args.out/'merge.json',dict(plan_sha256=sha(target),tracks=len(rows),windows=len(arrays['track']),recovered=len(added)))
    print(json.dumps(dict(tracks=len(rows),windows=len(arrays['track']),recovered=len(added))))


if __name__=='__main__':main()
