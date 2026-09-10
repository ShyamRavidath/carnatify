"""Artist-held-out continuous pitch-activity diagnostic around public tani sections.

Fixed 60-second margins, 10-second queries, threshold .5 and switch penalty 6.
This is annotation-centered development evaluation, not automatic full-concert
discovery: the query regions are selected from annotations, predictions are not.
"""
import argparse,json,math,multiprocessing,sys,time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import soundfile as sf
from normalize_ragas import fold
from scripts.raga_pipeline import sha,write_json
from scripts.benchmark_pitch_activity import estimator,extract
from scripts.score_activity_intervals import score_segments
from carnatify.audio.sections import section_activity,artist_class_weights
from carnatify.ml.concert_segments import viterbi_states


def explicit_truth(sections,start,end):
    boundaries=sorted({start,end}|{max(start,min(end,r[k])) for r in sections for k in ('start_s','end_s')})
    output=[]
    for a,b in zip(boundaries,boundaries[1:]):
        kinds={section_activity(r['kind']) for r in sections if r['start_s']<(a+b)/2<r['end_s']}-{None}
        if len(kinds)>1:raise ValueError('Conflicting section activity')
        if not kinds:continue
        label='percussion' if kinds=={'percussion'} else 'music'
        if output and output[-1]['end_s']==a and output[-1]['truth']==label:output[-1]['end_s']=b
        else:output.append(dict(start_s=a,end_s=b,truth=label))
    return output


def segments_from_states(starts,states):
    out=[]
    for start,state in zip(starts,states):
        kind='percussion' if state else 'melodic_music'
        if out and out[-1]['kind']==kind and out[-1]['end_s']==start:out[-1]['end_s']=start+10
        else:out.append(dict(start_s=start,end_s=start+10,kind=kind))
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workers',type=int,default=4)
    args=ap.parse_args();started=time.monotonic()
    out=ROOT/'data/overhaul/activity_boundaries';source=ROOT/'data/overhaul/pitch_activity_expanded/query_plan.json'
    training=json.loads(source.read_text());corpus_path=ROOT/'data/overhaul/annotated_corpus.json'
    if sha(corpus_path)!=training['corpus_sha256']:raise ValueError('Corpus changed')
    corpus={r['track']:r for r in json.loads(corpus_path.read_text())['rows']}
    groups=np.array(['|'.join(sorted(fold(a) for a in corpus[r['track']]['artists'])) for r in training['rows']])
    y=np.array([r['truth']=='percussion' for r in training['rows']],dtype=int)
    plan=[]
    for track in corpus.values():
        tani=[s for s in track['sections'] if section_activity(s['kind'])=='percussion']
        if not tani:continue
        audio=ROOT/track['audio'];digest=sha(audio);duration=sf.info(audio).duration
        artist='|'.join(sorted(fold(a) for a in track['artists']))
        for section in tani:
            a=math.floor(max(0,section['start_s']-60)/10)*10
            b=math.floor(min(duration,section['end_s']+60)/10)*10
            queries=[dict(audio=track['audio'],audio_sha256=digest,start_s=s) for s in range(a,b,10)]
            plan.append(dict(track=track['track'],artist=artist,tani=section,queries=queries,
                truth=explicit_truth(track['sections'],a,b)))
    protocol=dict(training_plan_sha256=sha(source),policy='60s context margins; 10s queries; threshold .5; switch penalty 6; leave artist out',rows=plan)
    frozen=out/'plan.json'
    if frozen.exists() and json.loads(frozen.read_text())!=protocol:raise ValueError('Boundary protocol changed')
    if not frozen.exists():write_json(frozen,protocol)
    # Hash validation precedes both cached and new feature reads.
    for audio in {r['audio']:r['audio_sha256'] for r in training['rows']}:
        expected=next(r['audio_sha256'] for r in training['rows'] if r['audio']==audio)
        if sha(ROOT/audio)!=expected:raise ValueError('Training audio changed')
    X=np.stack([extract(r) for r in training['rows']]);results=[]
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        for row in plan:
            held=set(row['artist'].split('|'))
            tr=np.array([not held.intersection(g.split('|')) for g in groups])
            if not held or '' in held or len(np.unique(y[tr]))!=2:raise ValueError('Insufficient artist-held-out training')
            model=estimator(True).fit(X[tr],y[tr],logisticregression__sample_weight=artist_class_weights(y[tr],groups[tr]))
            vectors=[]
            for vector in pool.map(extract,row['queries']):
                vectors.append(vector)
                if len(vectors)%25==0:print(f'{row["track"]}: {len(vectors)}/{len(row["queries"])}',flush=True)
            p=model.predict_proba(np.stack(vectors))[:,1]
            clipped=np.clip(p,.005,.995)
            soft=viterbi_states(np.c_[1-clipped,clipped],switch_penalty=6)
            starts=[r['start_s'] for r in row['queries']]
            hard_segments=segments_from_states(starts,p>=.5);soft_segments=segments_from_states(starts,soft)
            result=dict(track=row['track'],artist=row['artist'],n_training_queries=int(tr.sum()),
                probabilities=p.tolist(),raw=score_segments(hard_segments,row['truth']),
                decoded=score_segments(soft_segments,row['truth']),decoded_segments=soft_segments)
            results.append(result)
            write_json(out/'result.json',dict(status='artist-held-out annotation-centered development diagnostic; not full-concert detection',
                complete=len(results)==len(plan),plan_sha256=sha(frozen),rows=results,elapsed_s=time.monotonic()-started))
            print(f'{row["track"]}: raw={result["raw"]["accuracy"]:.4f}; decoded={result["decoded"]["accuracy"]:.4f}',flush=True)


if __name__=='__main__':main()
