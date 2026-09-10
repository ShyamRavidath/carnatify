"""Bounded-memory full-recording fingerprints for training/evaluation copy checks."""
import argparse
import json
from pathlib import Path
import sys
import time
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import soundfile as sf
from carnatify.audio.recording_fingerprint import RecordingFingerprinter
from carnatify.audio.utils import phase_safe_mono
from carnatify.audio.cache_io import atomic_npz
from scripts.raga_pipeline import sha, write_json


def ffmpeg_blocks(path, sr, channels):
    """Independent decoder fallback preserving native channels/rate."""
    with tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-i',str(path),
                                  '-map','0:a:0','-ac',str(channels),'-ar',str(sr),
                                  '-f','f32le','pipe:1'],stdout=subprocess.PIPE,stderr=errors)
        try:
            while True:
                raw=process.stdout.read(sr*30*channels*4)
                if not raw:break
                if len(raw)%(channels*4):raise RuntimeError('Partial PCM frame from fallback decoder')
                yield np.frombuffer(raw,dtype='<f4').reshape(-1,channels)
            code=process.wait(timeout=10)
            errors.seek(0);message=errors.read(4096).decode(errors='replace')
            if code or message:
                raise RuntimeError(f'FFmpeg decode not clean ({code}): {message}')
        finally:
            if process.poll() is None:
                process.kill();process.wait(timeout=10)
            process.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--field-only',action='store_true',help='Use frozen long concerts instead of Saraga as evaluation audio')
    args = parser.parse_args()
    lib = ROOT / 'data/overhaul/chromaprint/build/src/libchromaprint.1.5.1.dylib'
    manifest = ROOT / 'data/overhaul/broader_audio_deduplicated/manifest.json'
    identity = ROOT / 'data/overhaul/archive_audio_identity_refreshed.json'
    corpus = ROOT / 'data/overhaul/annotated_corpus_v2.json'
    queries = ROOT / 'data/overhaul/saraga_audio_results.json'
    identities = {r['track']:r for r in json.loads(identity.read_text())['rows']}
    query_hashes = {r['track']:r['metadata']['audio_sha256'] for r in json.loads(queries.read_text())['rows']}
    rows = [dict(track=r['track'], role='train', audio=r['audio'], sha256=identities[r['track']]['sha256'])
            for r in json.loads(manifest.read_text())['rows'] if r.get('corpus') == 'archive']
    rows += [dict(track=r['track'], role='evaluation', audio=r['audio'], sha256=query_hashes[r['track']])
             for r in json.loads(corpus.read_text())['rows'] if r['track'] in query_hashes]
    frozen=None
    if args.field_only:
        frozen=ROOT/'data/long_concerts/FROZEN_CONCERTS.json'
        rows=[r for r in rows if r['role']=='train']
        for r in json.loads(frozen.read_text())['concerts']:
            if Path(r['file']).name!=r['file']:raise ValueError('Invalid frozen concert filename')
            rows.append(dict(track='field:'+r['file'],role='evaluation',
                audio='data/long_concerts/audio/'+r['file'],sha256=r['sha256']))
    rows.sort(key=lambda r:(r['sha256'],r['track']))
    if args.limit:
        rows = rows[:args.limit]
    policy = dict(version='chromaprint_1.5.1_test2_native_mono_blocks30_v1', library_sha256=sha(lib),
                  block_s=30, clipping='clip normalized mono to [-1,1], count affected samples',
                  downmix='shared phase_safe_mono per native-rate block')
    plan = dict(inputs={str(p.relative_to(ROOT)):sha(p) for p in (manifest,identity,corpus,queries)},
                policy=policy, rows=rows)
    if frozen:plan['inputs'][str(frozen.relative_to(ROOT))]=sha(frozen)
    args.out.mkdir(parents=True,exist_ok=True)
    pp=args.out/'plan.json'
    if pp.exists() and json.loads(pp.read_text()) != plan:
        raise ValueError('Fingerprint extraction plan differs')
    write_json(pp,plan)
    cache=ROOT/'data/overhaul/recording_fingerprints/cache'
    cache.mkdir(parents=True,exist_ok=True)
    printer=RecordingFingerprinter(lib,policy['library_sha256'])
    results=[];started=time.monotonic()
    for row in rows:
        path=ROOT/row['audio']
        if sha(path)!=row['sha256']:
            raise ValueError('Recording bytes changed')
        target=cache/(row['sha256']+'_'+policy['library_sha256'][:16]+'.npz')
        if target.exists():
            with np.load(target) as z:
                metadata=json.loads(str(z['metadata']))
                if metadata['policy']!=policy:raise ValueError('Cached fingerprint policy changed')
        else:
            info=sf.info(path)
            stats=dict(blocks=0,clipped_samples=0,strongest_channel_blocks=0)
            def blocks(fallback=False):
                stream=(ffmpeg_blocks(path,info.samplerate,info.channels) if fallback else
                        sf.blocks(path,blocksize=info.samplerate*30,dtype='float32',always_2d=True))
                for block in stream:
                    mono,diagnostic=phase_safe_mono(block)
                    stats['blocks']+=1
                    stats['clipped_samples']+=int(np.sum(np.abs(mono)>1))
                    stats['strongest_channel_blocks']+=diagnostic['downmix']=='strongest_channel'
                    yield np.clip(mono,-1,1)
            decoder='soundfile';decoder_error=None
            try:
                try:
                    values,meta=printer.fingerprint(blocks(),int(info.samplerate))
                except sf.LibsndfileError as exc:
                    decoder_error=str(exc);decoder='ffmpeg_fallback'
                    stats=dict(blocks=0,clipped_samples=0,strongest_channel_blocks=0)
                    values,meta=printer.fingerprint(blocks(True),int(info.samplerate))
            except (RuntimeError,ValueError,sf.LibsndfileError) as exc:
                results.append(dict(**row,status='decode_failed',error=f'{type(exc).__name__}: {exc}'))
                write_json(args.out/'result.json',dict(plan_sha256=sha(pp),rows=results,
                           completed=len(results),expected=len(rows),elapsed_s=time.monotonic()-started))
                print(f'{len(results)}/{len(rows)} DECODE FAILED {row["track"]}',flush=True)
                continue
            metadata=dict(policy=policy,stream=meta,diagnostics=stats,audio_sha256=row['sha256'],
                          duration_s=info.duration,unique_codes=len(np.unique(values)),
                          decoder=decoder,primary_decoder_error=decoder_error)
            atomic_npz(target,values=values,metadata=json.dumps(metadata))
        results.append(dict(**row,cache=str(target.relative_to(ROOT)),cache_sha256=sha(target),metadata=metadata))
        write_json(args.out/'result.json',dict(plan_sha256=sha(pp),rows=results,
                   completed=len(results),expected=len(rows),elapsed_s=time.monotonic()-started))
        print(f'{len(results)}/{len(rows)} {row["role"]} {metadata["duration_s"]:.1f}s; elapsed {time.monotonic()-started:.1f}s',flush=True)


if __name__=='__main__':main()
