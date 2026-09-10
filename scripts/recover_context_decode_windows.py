"""Recover explicitly rejected clean-audit windows into separate candidate caches.

Never edits an active extraction run or reuses its original decoder contract.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('OMP_NUM_THREADS','1')
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import librosa
import numpy as np
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.ffmpeg_window import decode_native_window
from carnatify.audio.utils import phase_safe_mono
from carnatify.audio.melody_frontend import extract_waveform,HOP_S
from carnatify.audio.cache_io import atomic_npz
from carnatify.ml.melody_features import melody_features


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--track',required=True)
    args=parser.parse_args()
    if args.run.resolve()==args.out.resolve():raise ValueError('Separate recovery output required')
    parent=args.run/'plan.json';source=json.loads(parent.read_text())
    row=next(r for r in source['rows'] if r['track']==args.track)
    if row['corpus']!='archive':raise ValueError('Recovery requires raw archival audio')
    if sha(ROOT/row['audio'])!=row['audio_sha256']:raise ValueError('Raw audio changed')
    cache=args.run/'tracks'/(hashlib.sha256(args.track.encode()).hexdigest()+'.npz')
    with np.load(cache,allow_pickle=False) as z:
        if str(z['plan_sha256'])!=sha(parent):raise ValueError('Parent cache plan mismatch')
        meta=json.loads(str(z['metadata']))
    rejected=[r for r in meta['rejected'] if r['reason']=='libsndfile_window_decode_error']
    if not rejected:raise ValueError('No decoder-rejected windows to recover')
    files=[parent,cache,Path(__file__),ROOT/'src/carnatify/audio/ffmpeg_window.py',
        ROOT/'src/carnatify/audio/utils.py',ROOT/'src/carnatify/audio/melody_frontend.py',
        ROOT/'src/carnatify/audio/pitch_profiles.py',ROOT/'src/carnatify/ml/melody_features.py']
    plan=dict(inputs={str(p.resolve()):sha(p) for p in files},row=row,windows=rejected,
        policy='strict FFmpeg native PCM; shared phase-safe downmix, resample, estimated tonic and melody; separate recovery contract')
    target=args.out/'plan.json'
    if target.exists() and json.loads(target.read_text())!=plan:raise ValueError('Recovery plan changed')
    write_json(target,plan);receipts=[];began=time.monotonic()
    for i,window in enumerate(rejected):
        output=args.out/f'window_{i}.npz'
        if output.exists():
            with np.load(output,allow_pickle=False) as z:
                if str(z['plan_sha256'])!=sha(target):raise ValueError('Recovery cache plan mismatch')
                receipts.append(json.loads(str(z['metadata'])))
            continue
        data,sr,decoder=decode_native_window(ROOT/row['audio'],window['start_s'],window['duration_s'])
        audio,diagnostics=phase_safe_mono(data)
        if sr!=44100:audio=librosa.resample(audio,orig_sr=sr,target_sr=44100)
        f,tonic=extract_waveform(audio,44100)
        f=f[:int(np.ceil(len(audio)/44100/HOP_S))]
        if not np.isfinite(f).all() or np.any(f<0) or not np.isfinite(tonic) or tonic<=0:
            raise ValueError('Invalid recovered pitch/tonic')
        if np.sum(f>0)*HOP_S<10:raise ValueError('Recovered query has insufficient voiced audio')
        modern=melody_features(f,tonic,HOP_S);legacy=melody_features(f,tonic,HOP_S,legacy=True)
        if modern is None or legacy is None:raise ValueError('No recovered transitions')
        receipt=dict(track=args.track,start_s=window['start_s'],duration_s=window['duration_s'],
            actual_duration_s=len(audio)/44100,tonic_hz=float(tonic),voiced_s=float(np.sum(f>0)*HOP_S),
            decoder=decoder,audio=diagnostics)
        atomic_npz(output,f0=f,X=np.r_[modern[0],modern[1]],legacy=legacy[1],
            plan_sha256=sha(target),metadata=json.dumps(receipt,allow_nan=False))
        receipts.append(receipt)
    write_json(args.out/'result.json',dict(plan_sha256=sha(target),windows=receipts,
        elapsed_s=time.monotonic()-began,status='separate decoder-recovery candidate; not merged into training'))
    print(json.dumps(receipts))


if __name__=='__main__':main()
