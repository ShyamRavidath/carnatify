"""Resumable exact-query archival DSP plus explicit reference-pitch CompMusic.

Preserves the audited cohort/labels/groups. Does not admit new recordings.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.melody_frontend import extract_query,HOP_S,VERSION
from carnatify.audio.cache_io import atomic_npz
from carnatify.ml.melody_features import melody_features,FEATURE_VERSION


def window_starts(n_frames,hop_s,window_s):
    if n_frames<1 or hop_s<=0 or window_s not in (60,180):raise ValueError('Invalid training grid')
    width=round(window_s/hop_s)
    return sorted({round(max(0,n_frames-width)*q) for q in (.2,.5,.8)})


def extract_track(task):
    row,out,plan_sha,window_s=task;out=Path(out)
    key=hashlib.sha256(row['track'].encode()).hexdigest();target=out/'tracks'/(key+'.npz')
    if target.exists():
        with np.load(target,allow_pickle=False) as z:
            if str(z['plan_sha256'])!=plan_sha:raise ValueError('Track cache plan changed')
        return str(target)
    began=time.monotonic();path=ROOT/row['contour']
    if sha(path)!=row['contour_sha256']:raise ValueError('Source contour changed')
    if row['corpus']=='archive':
        if sha(ROOT/row['audio'])!=row['audio_sha256']:raise ValueError('Raw training audio changed')
        original=np.load(path)
    elif row['corpus']=='compmusic':
        raw=np.loadtxt(path);original=raw[:,1]
    else:raise ValueError('Unsupported training corpus')
    modern=[];old=[];receipts=[];rejected=[];hop=row['hop_s'];width=round(window_s/hop)
    for start in window_starts(len(original),hop,window_s):
        clip=original[start:start+width];duration=min(window_s,len(clip)*hop)
        if row['corpus']=='archive':
            f,meta=extract_query(ROOT/row['audio'],row['audio_sha256'],start*hop,duration,
                ROOT/'data/overhaul/cache/context_training')
            tonic=meta['tonic_hz'];query_hop=HOP_S
        else:
            f=clip;tonic=row['tonic'];query_hop=hop
            meta=dict(frontend='distributed reference pitch, not raw-audio inference',
                      start_s=start*hop,duration_s=duration,tonic_hz=tonic)
        reason=None
        if not tonic:reason='missing_query_tonic'
        elif np.sum(np.isfinite(f)&(f>0))*query_hop<10:reason='less_than_10s_voiced'
        if reason:
            rejected.append(dict(start_s=start*hop,reason=reason,metadata=meta));continue
        a=melody_features(f,tonic,query_hop);b=melody_features(f,tonic,query_hop,legacy=True)
        if a is None or b is None:
            rejected.append(dict(start_s=start*hop,reason='no_valid_transitions',metadata=meta));continue
        modern.append(np.r_[a[0],a[1]]);old.append(b[1]);receipts.append(meta)
    atomic_npz(target,X=np.asarray(modern).reshape(-1,5280),legacy=np.asarray(old).reshape(-1,4800),
        plan_sha256=plan_sha,metadata=json.dumps(dict(track=row['track'],windows=receipts,rejected=rejected,
            elapsed_s=time.monotonic()-began),allow_nan=False))
    return str(target)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'data/overhaul/file_tag_guarded')
    parser.add_argument('--identity',type=Path,default=ROOT/'data/overhaul/repro_audio_identity/audio_identity.json')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--window-s',type=int,choices=[60,180],default=180)
    parser.add_argument('--workers',type=int,choices=[1,2,4],default=4)
    parser.add_argument('--limit',type=int,default=0)
    args=parser.parse_args()
    if args.limit<0 or args.out.resolve()==args.source.resolve() or not args.out.resolve().is_relative_to(ROOT):
        raise ValueError('Use a separate repository run and nonnegative limit')
    manifest=args.source/'manifest.json';source=json.loads(manifest.read_text())
    identities={r['track']:r for r in json.loads(args.identity.read_text())['rows']}
    rows=sorted(source['rows'],key=lambda r:hashlib.sha256(r['track'].encode()).hexdigest())
    if args.limit:rows=rows[:args.limit]
    rows=[dict(r,audio_sha256=identities[r['track']]['sha256']) if r['corpus']=='archive' else dict(r) for r in rows]
    plan=dict(inputs={str(p.resolve().relative_to(ROOT)):sha(p) for p in (manifest,args.identity,Path(__file__))},
        rows=rows,window_s=args.window_s,offsets=[.2,.5,.8],frontend=VERSION,
        policy='exact query DSP and query tonic for archive; reference-pitch/annotated tonic for CompMusic',
        limit=args.limit,feature_version=FEATURE_VERSION)
    pp=args.out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Frozen extraction plan changed')
    write_json(pp,plan);plan_sha=sha(pp);X=[];legacy=[];labels=[];tracks=[];groups=[];kept=[];audits=[]
    began=time.monotonic();tasks=[(r,str(args.out),plan_sha,args.window_s) for r in rows]
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        for row,path in zip(rows,pool.map(extract_track,tasks)):
            with np.load(path,allow_pickle=False) as z:
                a=z['X'];b=z['legacy'];meta=json.loads(str(z['metadata']))
            if a.shape!=(len(b),5280) or b.shape[1:]!=(4800,) or not np.isfinite(a).all() or not np.isfinite(b).all():
                raise ValueError('Invalid context features')
            audits.append(meta);n=len(a)
            if n:
                X.extend(a);legacy.extend(b);labels.extend([row['label']]*n);tracks.extend([row['track']]*n);groups.extend([row['group']]*n)
                kept.append(dict(row,query_windows=meta['windows'],training_frontend=plan['policy']))
            write_json(args.out/'progress.json',dict(plan_sha256=plan_sha,completed=len(audits),expected=len(rows),
                windows=len(X),elapsed_s=time.monotonic()-began))
            print(f'{len(audits)}/{len(rows)} {n} windows; {time.monotonic()-began:.1f}s',flush=True)
    if not X:raise ValueError('No valid training features')
    write_json(args.out/'manifest.json',dict(source,rows=kept,context_plan_sha256=plan_sha,
        protocol=dict(window_s=args.window_s,offsets=[.2,.5,.8],frontend=plan['policy'])))
    atomic_npz(args.out/'features.npz',X=np.array(X),legacy=np.array(legacy),y=np.array(labels),
        track=np.array(tracks),group=np.array(groups),version=FEATURE_VERSION,
        manifest_sha256=sha(args.out/'manifest.json'))
    write_json(args.out/'extraction.json',dict(plan_sha256=plan_sha,tracks=len(kept),windows=len(X),rows=audits,
        elapsed_s=time.monotonic()-began))


if __name__=='__main__':main()
