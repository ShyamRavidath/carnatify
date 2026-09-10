"""Replay frozen raga evidence with an optional development activity annotator.

Only activity/segment proposals change. No human labels are consumed, and no
new raga accuracy or production calibration is claimed.
"""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.pitch_activity import PitchActivityAnnotator
from carnatify.ml.concert_segments import decode_concert,candidate_only_segments


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--activity-model',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    started=time.monotonic()
    if args.input.resolve()==args.out.resolve():raise ValueError('Preserve the original concert report')
    source=json.loads(args.input.read_text());audio=Path(source['audio'])
    if not audio.is_absolute():audio=ROOT/audio
    if sha(audio)!=source['audio_sha256']:raise ValueError('Source audio changed')
    events=PitchActivityAnnotator(args.activity_model).annotate(audio,source['audio_sha256'],
        source['events'],ROOT/'data/overhaul/cache/activity_pitch')
    classes=list(next(w['probabilities'] for w in source['windows'] if w.get('probabilities')))
    segments=decode_concert(events,source['windows'],classes,threshold=source['threshold'],
                            overlap_factor=source.get('raga_context_s',60)/10)
    report={**source,'events':events,'segments':candidate_only_segments(segments),
            'source_prediction_report_sha256':sha(args.input),'pitch_activity_model_sha256':sha(args.activity_model),
            'activity_refinement_status':'development candidate; raga evidence unchanged',
            'raga_evidence_scope':'copied unchanged from source report; not rerun with current frontend',
            'source_timing':source.get('timing'),
            'timing':dict(elapsed_s=time.monotonic()-started,scope='activity-only replay; source raga compute excluded')}
    write_json(args.out,report)
    print([(s['start_s'],s['end_s'],s['kind']) for s in report['segments']])


if __name__=='__main__':main()
