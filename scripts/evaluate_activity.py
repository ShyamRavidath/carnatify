"""Check frozen AudioSet activity tags against existing musical/tani sections."""
import argparse,hashlib,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
os.environ.setdefault('HF_HOME',str(ROOT/'data/overhaul/cache/huggingface'))
sys.path[:0]=[str(ROOT/'data/overhaul/runtime_deps'),str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.utils import load_audio_window
from carnatify.audio.events import AudioEventClassifier
from carnatify.audio.sections import section_activity


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--corpus',type=Path,default=ROOT/'data/overhaul/annotated_corpus_v2.json')
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/activity_evaluation_v2.json')
    args=ap.parse_args()
    corpus=args.corpus;source=json.loads(corpus.read_text())['rows']
    tani=[];music=[]
    for row in source:
        for section in row['sections']:
            if section['end_s']-section['start_s']<12:continue
            kind=section['kind']
            if section_activity(kind)!='percussion' and kind not in {'pallavi','vocal_alap','violin_alap'}:continue
            q=dict(track=row['track'],audio=row['audio'],section=kind,
                   start_s=(section['start_s']+section['end_s'])/2-5,
                   truth='percussion' if kind.startswith('tani') else 'melodic_music')
            (tani if kind.startswith('tani') else music).append(q)
    # All available tani examples, plus deterministic distinct-track melody
    # examples. This is intentionally not a natural-prevalence accuracy score.
    melody=[];seen=set()
    for q in sorted(music,key=lambda q:hashlib.sha256((q['track']+q['section']).encode()).hexdigest()):
        if q['track'] not in seen:melody.append(q);seen.add(q['track'])
        if len(melody)>=12:break
    plan=tani+melody;out=args.out
    model_dir=ROOT/'data/overhaul/models/audio_events';model=AudioEventClassifier(model_dir)
    report=dict(corpus_sha256=sha(corpus),model_sha256=sha(model_dir/'model.safetensors'),
        protocol='all annotated tani >=12s plus 12 hash-selected distinct melodic tracks; center 10s',rows=[])
    start=time.monotonic()
    for q in plan:
        y,sr,diag=load_audio_window(ROOT/q['audio'],q['start_s'],10,16000)
        pred=model.predict(y,sr)
        correct=pred['state']=='percussion' if q['truth']=='percussion' else pred['state']=='music'
        report['rows'].append(dict(**q,prediction=pred,correct=correct,audio_diagnostics=diag))
        write_json(out,report);print(f'{len(report["rows"])}/{len(plan)} activity queries',flush=True)
    report['summary']={kind:dict(n=sum(r['truth']==kind for r in report['rows']),
        correct=sum(r['truth']==kind and r['correct'] for r in report['rows'])) for kind in ['percussion','melodic_music']}
    report['elapsed_s']=time.monotonic()-start;write_json(out,report)
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__':main()
