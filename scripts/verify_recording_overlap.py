"""Confirm fingerprint flags with complete decoded PCM hashes, without audio export."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.raga_pipeline import sha,write_json


def pcm_hash(path):
    with tempfile.TemporaryFile() as errors:
        result=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(path),'-map','0:a:0',
            '-ar','44100','-ac','2','-c:a','pcm_s16le','-f','hash','-hash','sha256','-'],
            stdout=subprocess.PIPE,stderr=errors,text=True,timeout=120)
        errors.seek(0);message=errors.read(4096).decode(errors='replace')
    if result.returncode or message:raise RuntimeError(f'Decode verification failed: {message}')
    prefix='SHA256='
    value=result.stdout.strip()
    if not value.startswith(prefix) or len(value[len(prefix):])!=64:
        raise ValueError('Unexpected PCM hash output')
    return value[len(prefix):]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',type=Path,default=ROOT/'data/overhaul/recording_fingerprints/result.json')
    parser.add_argument('--flags',type=Path,default=ROOT/'data/overhaul/recording_fingerprints/overlap.json')
    parser.add_argument('--out',type=Path,default=ROOT/'data/overhaul/recording_fingerprints/verified_overlap.json')
    args=parser.parse_args()
    flags=json.loads(args.flags.read_text());inventory=json.loads(args.inventory.read_text())
    if flags['input_sha256']!=sha(args.inventory):raise ValueError('Fingerprint inventory changed')
    if flags['completed_references']!=flags['expected_references']:raise ValueError('Overlap screening incomplete')
    rows={r['track']:r for r in inventory['rows']};verified=[]
    for flag in flags['flags']:
        hashes={}
        for role in ['query','reference']:
            row=rows[flag[role]];path=ROOT/row['audio']
            if sha(path)!=flag[role+'_audio_sha256']:raise ValueError('Flagged audio changed')
            hashes[role]=pcm_hash(path)
        verified.append(dict(flag,status='confirmed_same_decoded_pcm' if hashes['query']==hashes['reference']
                             else 'not_confirmed_by_exact_pcm',decoded_pcm_sha256=hashes))
    write_json(args.out,dict(inputs={str(p.relative_to(ROOT)):sha(p) for p in [args.inventory,args.flags]},
        ffmpeg_sha256=sha(Path(shutil.which('ffmpeg')).resolve()),
        method='Complete first audio stream decoded as 44100Hz stereo PCM16LE; clean decoder output required',
        rows=verified,limitation='Different PCM hashes do not disprove a performance copy; positive equality confirms decoded audio identity'))
    print(json.dumps(verified,indent=2))


if __name__=='__main__':main()
