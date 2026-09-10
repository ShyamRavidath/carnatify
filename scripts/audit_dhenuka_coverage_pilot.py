"""Decode and copy-screen the new coverage candidate; no training admission."""
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import soundfile as sf
from scripts.raga_pipeline import sha,write_json
from scripts.audit_strict_audio_decode import check
from scripts.extract_recording_fingerprints import ffmpeg_blocks
from scripts.audit_recording_fingerprint_overlap import make_index,scan,POLICY
from carnatify.audio.recording_fingerprint import RecordingFingerprinter
from carnatify.audio.utils import phase_safe_mono
from carnatify.audio.cache_io import atomic_npz


def main():
    out=ROOT/'data/overhaul/dhenuka_coverage_pilot'
    download=json.loads((out/'result.json').read_text());audio=ROOT/download['audio']
    if sha(audio)!=download['hashes']['sha256']:raise ValueError('Downloaded bytes changed')
    sources=[ROOT/'data/overhaul/recording_fingerprints/result.json',
             ROOT/'data/overhaul/recording_fingerprints_field/result.json']
    lib=ROOT/'data/overhaul/chromaprint/build/src/libchromaprint.1.5.1.dylib'
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise RuntimeError('FFmpeg unavailable')
    plan=dict(inputs={str(p.relative_to(ROOT)):sha(p) for p in [out/'result.json',*sources,Path(__file__)]},
        library_sha256=sha(lib),ffmpeg_sha256=sha(Path(ffmpeg)),screening_policy=POLICY,
        policy='strict full-file decode; bounded 128-recording index batches; no model or label changes')
    pp=out/'audit_plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Frozen audit plan changed')
    write_json(pp,plan)
    row=dict(track='coverage__Dhenuka__Teliyaleru_Rama_SKR',audio=download['audio'],audio_sha256=download['hashes']['sha256'])
    decode=check((row,str(out/'decode'),ffmpeg,sha(pp)))
    if decode['status']!='clean':raise ValueError('Coverage candidate requires decoder diagnosis')
    printer=RecordingFingerprinter(lib,plan['library_sha256']);info=sf.info(audio)
    def blocks():
        for chunk in ffmpeg_blocks(audio,info.samplerate,info.channels):
            mono,_=phase_safe_mono(chunk);yield np.clip(mono,-1,1)
    values,meta=printer.fingerprint(blocks(),int(info.samplerate))
    atomic_npz(out/'fingerprint.npz',values=values,metadata=json.dumps(meta))
    records={}
    for path in sources:
        report=json.loads(path.read_text())
        if report['completed']!=report['expected']:raise ValueError('Comparison inventory incomplete')
        for r in report['rows']:
            if r.get('status','ok')=='ok':records.setdefault(r['sha256'],r)
    entries=list(records.values());flags=[]
    for start in range(0,len(entries),128):
        batch=entries[start:start+128];arrays=[]
        for r in batch:
            path=ROOT/r['cache']
            if sha(path)!=r['cache_sha256']:raise ValueError('Comparison fingerprint changed')
            with np.load(path,allow_pickle=False) as z:arrays.append(z['values'].copy())
        for hit in scan(values,arrays,make_index(arrays)):
            reference=batch[hit.pop('query_index')]
            flags.append(dict(hit,compared_track=reference['track'],compared_audio_sha256=reference['sha256'],role=reference['role']))
    write_json(out/'audit_result.json',dict(plan_sha256=sha(pp),decode=decode,n_compared=len(entries),flags=flags,
        fingerprint_sha256=sha(out/'fingerprint.npz'),fingerprint_metadata=meta,
        status='screened coverage candidate; no admission, performer-independence or raga accuracy claim',
        limitation='Zero flags cannot prove absence of all transformations, alternate microphones or artist overlap'))
    print(json.dumps(dict(n_compared=len(entries),flags=flags,decode=decode['status'])))


if __name__=='__main__':main()
