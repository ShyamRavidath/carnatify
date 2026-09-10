"""Bounded frozen-encoder feasibility probe; no raga/song accuracy claim."""
import argparse,hashlib,json,sys,time,os,importlib.metadata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['HF_HOME']=str(ROOT/'data/overhaul/cache/huggingface')
sys.path[:0]=[str(ROOT/'data/overhaul/runtime_deps'),str(ROOT),str(ROOT/'src')]
import numpy as np
import torch
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.musicfm_frontend import MusicFM,VERSION,HASHES,encoder_version
from carnatify.audio.utils import load_audio_window
from carnatify.audio.cache_io import atomic_npz


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,default=ROOT/'data/overhaul/musicfm_pilot')
    ap.add_argument('--device',choices=['cpu','mps'],default='cpu')
    ap.add_argument('--repeats',type=int,default=1)
    args=ap.parse_args()
    if not 1<=args.repeats<=5:ap.error('--repeats must be between one and five')
    torch.set_num_threads(4)
    out=args.run;out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/overhaul/sung_asr_pilot10/plan.json'
    query=json.loads(source.read_text())['queries'][0]
    audio=ROOT/query['audio']
    if sha(audio)!=query['audio_sha256']:raise ValueError('Query audio changed')
    plan=dict(version=encoder_version(args.device),source_plan_sha256=sha(source),query=query,artifacts=HASHES,
              layer=7,device=args.device,threads=4,sample_rate=24000,
              pooling='mean over time axis 0 of verified time/channel output')
    if args.repeats!=1:plan['repeats']=args.repeats
    pp=out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Pilot plan changed')
    if not pp.exists():write_json(pp,plan)
    started=time.monotonic();model=MusicFM(ROOT/'data/overhaul/models/musicfm',device=args.device)
    if args.device=='mps':torch.mps.synchronize()
    loading=time.monotonic()-started
    y,sr,diagnostics=load_audio_window(audio,query['start_s'],query['duration_s'],24000)
    begin=time.monotonic();frames=model.encode(y,sr);elapsed=time.monotonic()-begin
    times=[elapsed];differences=[]
    for _ in range(args.repeats-1):
        begin=time.monotonic();repeat=model.encode(y,sr);times.append(time.monotonic()-begin)
        differences.append(float(np.max(np.abs(frames-repeat))))
    pooled=frames.mean(axis=0)
    atomic_npz(out/'embedding.npz',frames=frames,pooled=pooled)
    report=dict(status=f'frozen encoder {args.device.upper()} feasibility only; no identity or accuracy claim',
        plan_sha256=sha(pp),waveform_sha256=hashlib.sha256(y.tobytes()).hexdigest(),audio=diagnostics,
        loading_s=loading,inference_s=elapsed,shape=list(frames.shape),pooled_shape=list(pooled.shape),
        pooled_l2=float(np.linalg.norm(pooled)),frame_std=float(frames.std()),
        embedding_sha256=sha(out/'embedding.npz'),torch_version=torch.__version__,
        runtime_versions={name:importlib.metadata.version(name) for name in ['torch','torchaudio','transformers','einops']})
    if args.repeats!=1:
        report.update(inference_times_s=times,repeat_max_abs_difference=differences)
    write_json(out/'result.json',report);print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
