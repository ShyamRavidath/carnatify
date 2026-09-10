"""Bounded full-file FFmpeg decode audit; never modifies or exports raw audio."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.raga_pipeline import sha,write_json


def decode_status(returncode,stderr_bytes,timed_out=False):
    if timed_out:return 'timeout'
    if returncode:return 'decoder_error'
    return 'decoder_diagnostic' if stderr_bytes else 'clean'


def check(task):
    row,out,ffmpeg,plan_sha=task;out=Path(out);audio=ROOT/row['audio']
    if sha(audio)!=row['audio_sha256']:raise ValueError('Raw source changed before decode audit')
    path=out/'files'/(row['audio_sha256']+'.json')
    if path.exists():
        result=json.loads(path.read_text())
        if result['plan_sha256']!=plan_sha:raise ValueError('Decode cache plan changed')
        return result
    began=time.monotonic();timed_out=False;returncode=None
    with tempfile.TemporaryFile() as errors:
        try:
            proc=subprocess.run([ffmpeg,'-nostdin','-v','error','-xerror','-threads','1',
                '-i',str(audio),'-map','0:a:0','-f','null','-'],stdout=subprocess.DEVNULL,
                stderr=errors,timeout=300,check=False)
            returncode=proc.returncode
        except subprocess.TimeoutExpired:timed_out=True
        size=errors.tell();errors.seek(0);message=errors.read(4096).decode('utf-8',errors='replace')
    result=dict(track=row['track'],audio=row['audio'],audio_sha256=row['audio_sha256'],
        plan_sha256=plan_sha,status=decode_status(returncode,size,timed_out),returncode=returncode,
        stderr_bytes=size,stderr_excerpt=message,elapsed_s=time.monotonic()-began)
    write_json(path,result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--manifest',type=Path)
    inputs.add_argument('--evaluation-corpus',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--identity',type=Path,default=ROOT/'data/overhaul/all_archive_audio_identity_refreshed.json')
    parser.add_argument('--workers',type=int,choices=[1,2],default=2)
    args=parser.parse_args()
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise RuntimeError('FFmpeg unavailable')
    manifest=args.evaluation_corpus or args.manifest
    identity_report=json.loads(args.identity.read_text())
    if args.evaluation_corpus and identity_report.get('corpus_sha256')!=sha(manifest):
        raise ValueError('Evaluation identity corpus changed')
    identity={r['track']:r for r in identity_report['rows']}
    rows=[]
    for r in json.loads(manifest.read_text())['rows']:
        if not args.evaluation_corpus and r.get('corpus')!='archive':continue
        i=identity[r['track']]
        if r['audio']!=i['audio']:raise ValueError('Audio identity path changed')
        digest=i['metadata']['audio_sha256'] if args.evaluation_corpus else i['sha256']
        rows.append(dict(track=r['track'],audio=r['audio'],audio_sha256=digest))
    if not rows:raise ValueError('No raw recordings to audit')
    if len({r['audio_sha256'] for r in rows})!=len(rows):raise ValueError('Audit a deduplicated cohort')
    plan=dict(inputs={str(p.resolve().relative_to(ROOT)):sha(p) for p in (manifest,args.identity,Path(__file__))},
        ffmpeg=ffmpeg,ffmpeg_sha256=sha(Path(ffmpeg)),rows=rows,timeout_s=300,
        policy='full first audio stream; FFmpeg -xerror; null sink; one decoder thread; no raw writes')
    pp=args.out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Frozen decode plan changed')
    write_json(pp,plan);results=[];began=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(check,[(r,str(args.out),ffmpeg,sha(pp)) for r in rows]):
            results.append(result);write_json(args.out/'progress.json',dict(completed=len(results),expected=len(rows)))
            print(f'{len(results)}/{len(rows)} {result["status"]}: {result["track"]}',flush=True)
    from collections import Counter
    report=dict(plan_sha256=sha(pp),rows=results,counts=dict(Counter(r['status'] for r in results)),
        elapsed_s=time.monotonic()-began,limitation='Clean decode is not acoustic quality, label or boundary ground truth; diagnostics are not automatically corruption')
    write_json(args.out/'result.json',report);print(json.dumps(report['counts']))


if __name__=='__main__':main()
