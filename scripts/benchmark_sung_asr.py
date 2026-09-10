"""Deterministic, bounded offline ASR pilot on existing Saraga recordings."""
import argparse,hashlib,importlib.metadata,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.sung_asr import SungASR,VERSION,CHECKPOINT_SHA256,DECODE
from carnatify.audio.utils import load_audio_window


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path,required=True)
    ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--window-s',type=int,choices=[10,30,60,180],default=10)
    ap.add_argument('--limit',type=int,default=1)
    ap.add_argument('--languages',nargs='+',choices=['auto','ta','te','hi'],
                    help='Fixed global lanes applied to every query, never selected from query metadata')
    args=ap.parse_args()
    if args.limit<1:ap.error('--limit must be positive')
    if args.languages and len(args.languages)!=len(set(args.languages)):ap.error('Duplicate language lanes')
    corpus=ROOT/'data/overhaul/annotated_corpus.json'
    source=ROOT/'data/overhaul/saraga_audio_results.json'
    audio=json.loads(source.read_text())
    if audio['corpus_sha256']!=sha(corpus):raise ValueError('Query/corpus provenance mismatch')
    rows={r['track']:r for r in json.loads(corpus.read_text())['rows']}
    selected=sorted(audio['rows'],key=lambda r:hashlib.sha256(r['track'].encode()).hexdigest())[:args.limit]
    plan=dict(corpus_sha256=sha(corpus),source_sha256=sha(source),version=VERSION,
        checkpoint_sha256=CHECKPOINT_SHA256,decode=DECODE,window_s=args.window_s,
        whisper_version=importlib.metadata.version('openai-whisper'),
        torch_version=importlib.metadata.version('torch'),
        selection='fixed track-hash-sorted prefix; no truth-based selection',queries=[])
    if args.languages:plan['language_lanes']=args.languages
    for row in selected:
        meta=row['metadata'];length=meta['start_s']+meta['end_s']
        duration=min(args.window_s,length);start=(length-duration)/2
        path=ROOT/rows[row['track']]['audio']
        if sha(path)!=meta['audio_sha256']:raise ValueError('Source audio changed')
        plan['queries'].append(dict(track=row['track'],audio=str(path.relative_to(ROOT)),
            audio_sha256=meta['audio_sha256'],start_s=start,duration_s=duration))
    args.run.mkdir(parents=True,exist_ok=True);pp=args.run/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Use a new run for a changed ASR plan')
    if not pp.exists():write_json(pp,plan)
    import torch
    torch.set_num_threads(4)
    model=None;results=[];started=time.monotonic()
    for query in plan['queries']:
        target=args.run/(hashlib.sha256(json.dumps(query,sort_keys=True).encode()).hexdigest()+'.json')
        if target.exists():
            result=json.loads(target.read_text())
            if result['plan_sha256']!=sha(pp) or result['query']!=query:raise ValueError('ASR receipt provenance mismatch')
        else:
            if model is None:model=SungASR(args.checkpoint)
            y,sr,diagnostics=load_audio_window(ROOT/query['audio'],query['start_s'],query['duration_s'],16000)
            begin=time.monotonic()
            if args.languages:
                hypotheses={lane:model.transcribe(y,sr,language=None if lane=='auto' else lane)
                            for lane in args.languages}
            else:hypothesis=model.transcribe(y,sr)
            result=dict(plan_sha256=sha(pp),query=query,audio=diagnostics,
                waveform_sha256=hashlib.sha256(y.tobytes()).hexdigest(),
                transcription_s=time.monotonic()-begin)
            result.update(hypotheses=hypotheses) if args.languages else result.update(hypothesis=hypothesis)
            write_json(target,result)
        results.append(result)
        write_json(args.run/'result.json',dict(plan_sha256=sha(pp),rows=results,
            complete=len(results)==len(selected),elapsed_s=time.monotonic()-started,
            status='unverified ASR pilot; no word-accuracy or identity claim'))
        status={k:v['status'] for k,v in result['hypotheses'].items()} if args.languages else result['hypothesis']['status']
        print(f'{len(results)}/{len(selected)} {query["track"]}: {status}; {result["transcription_s"]:.1f}s',flush=True)


if __name__=='__main__':main()
