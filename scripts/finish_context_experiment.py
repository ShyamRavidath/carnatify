"""Wait for a specific extractor, then recover, fit and evaluate its candidate.

No deployment, network, model promotion or raw-audio mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.raga_pipeline import sha,write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--pid',type=int,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--folds',type=Path,required=True)
    p.add_argument('--identity',type=Path,required=True)
    p.add_argument('--corpus',type=Path,required=True)
    p.add_argument('--recovery',type=Path,nargs='*',default=[])
    args=p.parse_args()
    if args.pid<=1 or args.out.resolve()==args.run.resolve():raise ValueError('Invalid process/output')
    scripts=['recover_context_decode_windows.py','merge_context_decode_recovery.py',
        'raga_kernel_benchmark.py','train_raga_svc.py','evaluate_annotated_raga.py']
    inputs=[args.run/'plan.json',args.folds,args.identity,args.corpus,Path(__file__)]+[ROOT/'scripts'/s for s in scripts]
    plan=dict(inputs={str(f.resolve()):sha(f) for f in inputs},parent_pid=args.pid,
        policy='wait for exact parent; frozen local candidate recovery, fixed-fold benchmark, fit, matched development evaluation; no promotion')
    pp=args.out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Supervisor plan changed')
    write_json(pp,plan);began=time.monotonic()
    while not (args.run/'extraction.json').exists():
        probe=subprocess.run(['ps','-p',str(args.pid),'-o','command='],capture_output=True,text=True,check=False)
        if probe.returncode or 'extract_context_training.py' not in probe.stdout or str(args.run) not in probe.stdout:
            raise RuntimeError('Specific parent is no longer running and no completion result exists')
        if time.monotonic()-began>4*3600:raise TimeoutError('Parent exceeded four-hour observation bound')
        write_json(args.out/'progress.json',dict(stage='waiting_for_parent',elapsed_s=time.monotonic()-began,pid=args.pid))
        time.sleep(30)
    def execute(script,argv):
        for path,digest in plan['inputs'].items():
            if sha(Path(path))!=digest:raise ValueError('Frozen experiment dependency changed: '+path)
        command=[sys.executable,str(ROOT/'scripts'/script),*map(str,argv)]
        print('Executing '+script,flush=True)
        write_json(args.out/'progress.json',dict(stage=script,command=command,elapsed_s=time.monotonic()-began))
        with (args.out/(script+'.log')).open('a') as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    completed=json.loads((args.run/'extraction.json').read_text())
    if completed['plan_sha256']!=sha(args.run/'plan.json'):raise ValueError('Completed parent plan changed')
    needed={r['track'] for r in completed['rows'] if any(w['reason']=='libsndfile_window_decode_error' for w in r['rejected'])}
    existing={json.loads((r/'plan.json').read_text())['row']['track']:r for r in args.recovery}
    recoveries=[]
    for track in sorted(needed):
        target=existing.get(track)
        if target is None:
            target=args.out/'recoveries'/hashlib.sha256(track.encode()).hexdigest()
            execute('recover_context_decode_windows.py',['--run',args.run,'--out',target,'--track',track])
        recoveries.append(target)
    if not recoveries:raise ValueError('This recovery experiment requires at least one rejected query')
    training=args.out/'training'
    execute('merge_context_decode_recovery.py',['--run',args.run,'--recovery',*recoveries,
        '--folds',args.folds,'--out',training])
    execute('raga_kernel_benchmark.py',['--run',training,'--out',training/'kernel_benchmark.json','--arms','legacy_kernel_ridge'])
    execute('train_raga_svc.py',['--run',training,'--family','kernel_ridge','--representation','voiced',
        '--oof',training/'legacy_kernel_ridge_oof.npz','--out',training/'raga.joblib','--audio-identity',args.identity])
    execute('evaluate_annotated_raga.py',['--model',training/'raga.joblib','--corpus',args.corpus,
        '--name','context180_recovered','--window-s',180,'--skip-baseline','--out',training/'evaluation180.json'])
    write_json(args.out/'result.json',dict(plan_sha256=sha(pp),elapsed_s=time.monotonic()-began,
        status='development experiment completed; no promotion',training=str(training)))


if __name__=='__main__':main()
