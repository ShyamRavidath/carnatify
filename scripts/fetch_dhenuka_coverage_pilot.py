"""Acquire one documented coverage candidate; no training admission or relabeling."""
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.raga_pipeline import sha,write_json


def validate_bytes(path,entry):
    if path.stat().st_size!=int(entry['size']):raise ValueError('Published size mismatch')
    hashes={name:hashlib.new(name) for name in ('md5','sha1','sha256')}
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            for h in hashes.values():h.update(block)
    result={name:h.hexdigest() for name,h in hashes.items()}
    if any(result[k]!=entry[k] for k in ('md5','sha1')):raise ValueError('Published audio checksum mismatch')
    return result


def main():
    identifier='01.VarnamNatakurinji'
    filename='03. Teliyaleru Rama - Denuka - Thyagayya.mp3'
    metadata=ROOT/'data/overhaul/all_archive_metadata/c98a70a1d7b4b39607b89ab72b097bf6774246f6d2f7990c8e889978ee1d872f.raw.json'
    if sha(metadata)!='04bda87296ed61002fa49a5b8ebf4c1c05dc3a702c581d6ba00932bac44506c3':
        raise ValueError('Publisher metadata changed')
    raw=json.loads(metadata.read_text())
    if raw['metadata']['identifier']!=identifier:raise ValueError('Source identifier changed')
    matches=[f for f in raw['files'] if f['name']==filename]
    if len(matches)!=1:raise ValueError('Publisher file ambiguous')
    entry=matches[0]
    if int(entry['size'])>8*1024*1024:raise ValueError('Bounded coverage pilot exceeded')
    out=ROOT/'data/overhaul/dhenuka_coverage_pilot';target=out/'candidate.mp3'
    url='https://archive.org/download/'+urllib.parse.quote(identifier,safe='')+'/'+urllib.parse.quote(filename,safe='')
    plan=dict(identifier=identifier,file=entry,url=url,metadata_sha256=sha(metadata),
        canonical_raga_candidate='Dhenuka',work_raga_corroboration='https://www.karnatik.com/c31447.shtml',
        label_evidence='publisher Denuka token plus independent Teliyaleru Rama work/raga catalog; acoustic identity not verified',
        purpose='missing-vocabulary coverage candidate; requires decode, copy and group checks before any admission',
        max_download_bytes=8*1024*1024,script_sha256=sha(Path(__file__)))
    pp=out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Acquisition plan changed')
    write_json(pp,plan);attempts=[]
    if not target.exists():
        partial=out/'candidate.mp3.part'
        for attempt in range(1,4):
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'CarnatifyResearch/0.1 (bounded public metadata/audio integrity pilot)'})
                with urllib.request.urlopen(request,timeout=30) as response,partial.open('wb') as stream:
                    size=0
                    while True:
                        block=response.read(1024*1024)
                        if not block:break
                        size+=len(block)
                        if size>int(entry['size']):raise ValueError('Response exceeds published size')
                        stream.write(block)
                validate_bytes(partial,entry);partial.replace(target)
                attempts.append(dict(attempt=attempt,status='ok'));break
            except Exception as exc:
                attempts.append(dict(attempt=attempt,status='failed',error=str(exc)))
                write_json(out/'progress.json',dict(attempts=attempts))
                if attempt==3:raise
                time.sleep(1)
    hashes=validate_bytes(target,entry)
    result=dict(plan_sha256=sha(pp),audio=str(target.relative_to(ROOT)),hashes=hashes,
        bytes=target.stat().st_size,attempts=attempts,status='downloaded candidate only; not admitted or trained')
    write_json(out/'result.json',result);print(json.dumps(result))


if __name__=='__main__':main()
