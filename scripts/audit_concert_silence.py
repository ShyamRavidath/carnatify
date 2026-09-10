"""Measure opt-in silence-policy activation on frozen natural recordings.

No boundary accuracy is inferred: the recordings lack exhaustive independent
item-boundary annotations. This audit consumes no human labels.
"""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import soundfile as sf
from scripts.raga_pipeline import sha,write_json
from scripts.concert_pipeline import interior_silence
from carnatify.audio.utils import load_audio_window


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,required=True)
    args=ap.parse_args()
    source=ROOT/'data/long_concerts/FROZEN_CONCERTS.json'
    manifest=json.loads(source.read_text())
    plan=dict(source_sha256=sha(source),policy='interior_rms_1e-5_trim50ms_v1',
              query_s=10,sample_rate=16000,recordings=manifest['concerts'])
    args.run.mkdir(parents=True,exist_ok=True);pp=args.run/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:
        raise ValueError('Changed natural-audio audit protocol')
    if not pp.exists():write_json(pp,plan)
    rows=[];started=time.monotonic()
    for record in plan['recordings']:
        audio=ROOT/'data/long_concerts/audio'/record['file']
        if sha(audio)!=record['sha256']:raise ValueError('Frozen audio changed')
        duration=sf.info(audio).duration
        if abs(duration-record['duration_s'])>.1:raise ValueError('Audio duration mismatch')
        receipt=args.run/(record['file']+'.json')
        if receipt.exists():
            row=json.loads(receipt.read_text())
            if row['plan_sha256']!=sha(pp):raise ValueError('Receipt provenance mismatch')
        else:
            quiet=[];rms=[];n=0
            for start in np.arange(0,duration,10.):
                length=min(10.,duration-start)
                y,sr,_=load_audio_window(audio,float(start),float(length),16000)
                n+=1
                if len(y)>=sr:
                    edge=round(.05*sr)
                    rms.append(float(np.sqrt(np.mean(y[edge:-edge].astype(float)**2))))
                if interior_silence(y,sr):
                    quiet.append(dict(start_s=float(start),end_s=float(start+length)))
                if n%100==0:print(f'{record["file"]}: {min(start+length,duration):.0f}/{duration:.0f}s',flush=True)
            row=dict(plan_sha256=sha(pp),file=record['file'],audio_sha256=record['sha256'],
                     duration_s=duration,n_windows=n,n_silent=len(quiet),silent_intervals=quiet,
                     interior_rms_percentiles=dict(zip(['min','p1','p5','p50'],np.percentile(rms,[0,1,5,50]).tolist())))
            write_json(receipt,row)
        rows.append(row)
        result=dict(status='natural-audio activation audit, not boundary accuracy',
            plan_sha256=sha(pp),complete=len(rows)==len(plan['recordings']),rows=rows,
            duration_s=sum(r['duration_s'] for r in rows),n_windows=sum(r['n_windows'] for r in rows),
            n_silent=sum(r['n_silent'] for r in rows),elapsed_s=time.monotonic()-started)
        write_json(args.run/'result.json',result)
        print(f'{record["file"]}: {row["n_silent"]}/{row["n_windows"]} silent windows',flush=True)


if __name__=='__main__':main()
