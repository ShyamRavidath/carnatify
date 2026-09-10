"""Bounded/resumable automatic long-concert activity, raga and segment inference.

No human label file is read. Public pretrained audio-event tags and a versioned
raga model produce uncertain annotations suitable for review or weak training,
never for circular evaluation of the same model.
"""
from __future__ import annotations
import argparse,json,os,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
os.environ.setdefault('HF_HOME',str(ROOT/'data/overhaul/cache/huggingface'))
os.environ.setdefault('TRANSFORMERS_CACHE',str(ROOT/'data/overhaul/cache/huggingface'))
sys.path[:0]=[str(ROOT/'data/overhaul/runtime_deps'),str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
import soundfile as sf
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.utils import load_audio_window
from carnatify.audio.events import AudioEventClassifier,calibrated_event
from carnatify.ml.melody_features import FEATURE_VERSIONS,feature_vector
from carnatify.ml.concert_segments import decode_concert,candidate_only_segments
from carnatify.ml.inference_runtime import serial_forest_prediction
from carnatify.audio.melody_frontend import extract_query,composition_query, VERSION as QUERY_FRONTEND_VERSION
from carnatify.audio.cache_io import atomic_npz

HOP=128/44100
EXTRACTION_VERSION='concert_mix_melodia_events_v1'
EVENTS_VERSION='concert_mix_events_only_v2'


def silence_bounded_end(start, end, events):
    """Cap context at a detected silence; never infer a semantic song boundary.

    Queries starting inside silence end there rather than borrowing the next
    item's tonic. This optional policy uses audio events, not reference labels.
    """
    stops = [end]
    for event in events:
        if event['state'] != 'silence':
            continue
        a, b = event['start_s'], event['end_s']
        if a <= start < b:
            stops.append(b)
        elif start < a < end:
            stops.append(a)
    return float(min(stops))


def interior_silence(audio, sr):
    """Near-digital silence excluding 50ms resampling edge transients.

    Not a speech/activity classifier: quiet rooms and applause are not assumed
    silent. Require at least one second of finite audio.
    """
    y=np.asarray(audio,dtype=float)
    if sr<=0 or y.ndim!=1 or len(y)<sr or not np.isfinite(y).all():
        return False
    edge=int(round(.05*sr));inner=y[edge:len(y)-edge]
    return bool(np.sqrt(np.mean(inner**2))<1e-5)


def context_query_starts(total, events, bounded=False):
    starts=set(float(s) for s in np.arange(0,max(1,total-29),30.))
    if bounded:
        starts.update(float(e['end_s']) for e in events
                      if e['state']=='silence' and 0<e['end_s']<total)
    return sorted(starts)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('audio',type=Path)
    ap.add_argument('--model',type=Path,default=ROOT/'data/overhaul/raga_ridge.joblib')
    ap.add_argument('--events-model',type=Path,default=ROOT/'data/overhaul/models/audio_events')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--cache',type=Path,default=ROOT/'data/overhaul/cache/concerts')
    ap.add_argument('--activity-calibration',type=Path,
                    help='Explicit experimental activity calibration; disabled by default after field regression')
    ap.add_argument('--pitch-activity-model',type=Path,
                    help='Optional development pitch-activity model; not production calibrated')
    ap.add_argument('--duration',type=float)
    ap.add_argument('--window-s',type=int,choices=[60,180],default=60,
                    help='Raga context; song context is set independently')
    ap.add_argument('--legacy-block-frontend',action='store_true',
                    help='Diagnostic only: concatenate block contours and borrow nearest block tonic')
    ap.add_argument('--silence-bounded-context',action='store_true',
                    help='Experimental: stop raga/song context at detected silence; not semantic segmentation')
    ap.add_argument('--composition-catalog',type=Path,help='Optional candidate-only melody reference index')
    ap.add_argument('--composition-window-s',type=int,choices=[60,180],default=60)
    ap.add_argument('--composition-raga-prior',action='store_true',
                    help='Experimental fixed .1 estimated-raga ranking preference; no identity acceptance gate')
    args=ap.parse_args()
    if args.silence_bounded_context and args.legacy_block_frontend:
        ap.error('Silence-bounded context requires the exact-query frontend')
    if args.activity_calibration and args.pitch_activity_model:
        ap.error('Choose one experimental activity refinement, not both')
    if args.legacy_block_frontend and (args.composition_window_s!=60 or args.composition_raga_prior):
        ap.error('Experimental song context/prior requires the exact-query frontend')
    if args.composition_raga_prior and not args.composition_catalog:
        ap.error('--composition-raga-prior requires --composition-catalog')
    bundle=joblib.load(args.model);representation=bundle.get('representation','elapsed')
    if FEATURE_VERSIONS[representation]!=bundle['feature_version']:raise ValueError('Model feature contract mismatch')
    model=serial_forest_prediction(bundle['model']);total=sf.info(str(args.audio)).duration
    composition_catalog=None
    if args.composition_catalog:
        from carnatify.ml.composition_catalog import CompositionCatalog
        composition_catalog=CompositionCatalog(args.composition_catalog)
    if args.duration is not None:
        if args.duration<=0 or not np.isfinite(args.duration):raise ValueError('Invalid duration')
        total=min(total,args.duration)
    audio_hash=sha(args.audio);event_hash=sha(args.events_model/'model.safetensors')
    activity_calibration=json.loads(args.activity_calibration.read_text()) if args.activity_calibration else None
    if activity_calibration and activity_calibration['model_sha256']!=event_hash:
        raise ValueError('Activity calibration/model mismatch')
    block_version=EXTRACTION_VERSION if args.legacy_block_frontend else EVENTS_VERSION
    key=f'{audio_hash[:24]}_{event_hash[:12]}_{block_version}'
    cache=args.cache/key;cache.mkdir(parents=True,exist_ok=True)
    event_model=None;all_events=[];all_f=[];all_times=[];tonics=[]
    started=time.monotonic()
    for start in np.arange(0,total,60.):
        length=min(60,total-start);path=cache/f'{start:.3f}_{length:.3f}.npz'
        if path.exists():
            with np.load(path) as z:
                meta=json.loads(str(z['meta']))
                if meta['version']!=block_version:raise ValueError('Block cache version mismatch')
                if args.legacy_block_frontend:f0=z['f0'];times=z['times']
        else:
            import librosa
            y,sr,diag=load_audio_window(args.audio,float(start),float(length),44100)
            y16=librosa.resample(y,orig_sr=sr,target_sr=16000)
            if event_model is None:event_model=AudioEventClassifier(args.events_model)
            events=[]
            for offset in np.arange(0,length,10.):
                a=int(round(offset*16000));b=min(len(y16),a+160000)
                clip=y16[a:b]
                if len(clip)<16000 or np.sqrt(np.mean(clip**2))<1e-5:
                    ev=dict(state='silence',music=0.,speech=0.,applause=0.,percussion=0.,melodic=0.,top_events=[])
                else:ev=event_model.predict(clip)
                ev.update(start_s=float(start+offset),end_s=float(min(start+offset+10,total)))
                events.append(ev)
            meta=dict(events=events,audio=diag,version=block_version)
            if args.legacy_block_frontend:
                import essentia.standard as es
                tonic=None
                if length>=10 and diag['rms']>=1e-5:
                    f0,_=es.PredominantPitchMelodia(sampleRate=sr,frameSize=2048,hopSize=128)(es.EqualLoudness(sampleRate=sr)(y))
                    try:tonic=float(es.TonicIndianArtMusic(sampleRate=sr)(y))
                    except RuntimeError:pass
                else:f0=np.zeros(int(length/HOP),dtype=np.float32)
                times=start+np.arange(len(f0))*HOP
                keep=times<start+length;f0=f0[keep];times=times[keep]
                meta['tonic_hz']=tonic
                atomic_npz(path,f0=f0,times=times,meta=json.dumps(meta,allow_nan=False))
            else:
                atomic_npz(path,meta=json.dumps(meta,allow_nan=False))
        all_events.extend(meta['events'])
        if args.legacy_block_frontend:
            all_f.append(f0);all_times.append(times)
            if meta['tonic_hz'] and np.isfinite(meta['tonic_hz']):
                tonics.append((start,meta['tonic_hz']))
        print(f'Audio {min(start+length,total):.0f}/{total:.0f}s; elapsed {time.monotonic()-started:.1f}s',flush=True)
    if args.legacy_block_frontend:
        frequencies=np.concatenate(all_f);times=np.concatenate(all_times)
    if args.silence_bounded_context:
        # Separate opt-in evidence; never alter the shared event-model cache.
        energy_events=[]
        for event in all_events:
            y,sr,_=load_audio_window(args.audio,event['start_s'],
                                    event['end_s']-event['start_s'],16000)
            event=dict(event)
            if interior_silence(y,sr):
                event.update(state='silence',silence_origin='interior_rms_1e-5_trim50ms_v1')
            energy_events.append(event)
        all_events=energy_events
    windows=[]
    for start in context_query_starts(total,all_events,args.silence_bounded_context):
        end=min(start+args.window_s,total)
        if args.silence_bounded_context:
            end=silence_bounded_end(start,end,all_events)
        # Retained only for explicit legacy comparison. Default queries estimate
        # tonic and melody on the full exact query, as in offline evaluation.
        if args.legacy_block_frontend:
            a,b=np.searchsorted(times,[start,end]);f=frequencies[a:b]
            tonic=min(tonics,key=lambda t:abs(t[0]-start))[1] if tonics else None
        else:
            f,query_meta=extract_query(args.audio,audio_hash,float(start),float(end-start),
                                      args.cache/'queries')
            tonic=query_meta['tonic_hz']
        row=dict(start_s=float(start),end_s=float(end),tonic_hz=tonic)
        if not args.legacy_block_frontend:
            row['query_extraction_failure']=query_meta['extraction_failure']
        voiced=float(np.sum(np.isfinite(f)&(f>0))*HOP)
        if tonic is None or voiced<10:
            row.update(status='insufficient_melody',voiced_s=voiced)
        else:
            vector=feature_vector(f,tonic,HOP,representation)
            if vector is None:row['status']='insufficient_transitions'
            else:
                p=model.predict_proba(vector[None])[0]
                row.update(status='candidate',voiced_s=voiced,
                           probabilities={str(c):float(v) for c,v in zip(model.classes_,p)})
        if composition_catalog:
            song_end=min(start+args.composition_window_s,total)
            if args.silence_bounded_context:
                song_end=silence_bounded_end(start,song_end,all_events)
            if args.legacy_block_frontend:
                song_f=f[:round(60/HOP)];song_tonic=tonic;song_failure=None
            else:
                song_f,song_meta=composition_query(args.audio,audio_hash,float(start),f,query_meta,args.cache/'queries',
                    duration_s=float(song_end-start))
                song_tonic=song_meta['tonic_hz'];song_failure=song_meta['extraction_failure']
            song_voiced=float(np.sum(np.isfinite(song_f)&(song_f>0))*HOP)
            row['composition_query']=dict(start_s=float(start),end_s=float(song_end))
            row['composition_tonic_hz']=song_tonic
            row['composition_extraction_failure']=song_failure
            row['composition_voiced_s']=song_voiced
            row['composition_candidates']=[]
            row['composition_status']='insufficient_melody'
            song_probabilities={}
            if song_tonic and song_voiced>=10:
                if args.composition_raga_prior:
                    song_vector=feature_vector(song_f,song_tonic,HOP,representation)
                    if song_vector is not None:
                        song_p=model.predict_proba(song_vector[None])[0]
                        if song_p.max()>=bundle['calibration']['gate']['threshold']:
                            song_probabilities={str(c):float(v) for c,v in zip(model.classes_,song_p)}
                row['composition_candidates']=composition_catalog.rank(song_f,song_tonic,HOP,limit=3,
                    raga_probabilities=song_probabilities)
                row['composition_status']='unverified_candidates_no_acceptance_threshold'
            row['composition_estimated_raga_probabilities']=song_probabilities
        windows.append(row)
        if not args.legacy_block_frontend:
            print(f'Query {start:.0f}-{end:.0f}s; elapsed {time.monotonic()-started:.1f}s',flush=True)
    threshold=bundle['calibration']['gate']['threshold']
    if activity_calibration:
        all_events=[calibrated_event(e,activity_calibration) for e in all_events]
    if args.pitch_activity_model:
        from carnatify.audio.pitch_activity import PitchActivityAnnotator
        all_events=PitchActivityAnnotator(args.pitch_activity_model).annotate(
            args.audio,audio_hash,all_events,args.cache.parent/'activity_pitch')
    segments=decode_concert(all_events,windows,model.classes_,threshold=threshold,overlap_factor=args.window_s/10)
    # Current bundles have development-only gates; transfer tests exposed false
    # confident answers. Retain ranking, but do not assert validated identities.
    segments=candidate_only_segments(segments)
    report=dict(audio=str(args.audio),audio_sha256=audio_hash,model_sha256=sha(args.model),
        event_model_sha256=event_hash,feature_version=bundle['feature_version'],duration_s=total,
        block_frontend=block_version,
        silence_bounded_context=args.silence_bounded_context,
        silence_boundary_policy='interior_rms_1e-5_trim50ms_anchors_v2' if args.silence_bounded_context else None,
        raga_context_s=args.window_s,composition_context_s=args.composition_window_s,
        composition_raga_prior_weight=.1 if args.composition_raga_prior else 0.,
        composition_raga_prior_model_sha256=sha(args.model) if args.composition_raga_prior else None,
        composition_frontend='legacy_block_slice' if args.legacy_block_frontend else 'independent_exact_query_v1',
        query_frontend='legacy_block_concat' if args.legacy_block_frontend else QUERY_FRONTEND_VERSION,
        requires_manual_labels=False,label_origin='automatic_prediction',
        calibration_status=bundle['calibration']['status'],threshold=threshold,
        identity_status='candidate_only; production rejection calibration not established',
        activity_calibration_sha256=sha(args.activity_calibration) if activity_calibration else None,
        activity_calibration_status=activity_calibration['status'] if activity_calibration else 'uncalibrated',
        pitch_activity_model_sha256=sha(args.pitch_activity_model) if args.pitch_activity_model else None,
        composition_catalog_sha256=sha(args.composition_catalog) if composition_catalog else None,
        timing=dict(elapsed_s=time.monotonic()-started),events=all_events,windows=windows,segments=segments)
    write_json(args.output,report)
    print(f'{len(segments)} proposed segments; {sum(s["status"]=="recognized" for s in segments)} raga answers; wrote {args.output}')


if __name__=='__main__':main()
