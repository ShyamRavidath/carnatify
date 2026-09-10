"""Fetch the small, CC-BY-4.0 Saraga AV metadata archive only (not 65 GB audio)."""
import hashlib,json,sys,zipfile
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.raga_pipeline import write_json,sha


def main():
    out=ROOT/'data/overhaul/saraga_av';out.mkdir(parents=True,exist_ok=True)
    record=requests.get('https://zenodo.org/api/records/15102483',timeout=30)
    record.raise_for_status();metadata=record.json()
    entry=next(f for f in metadata['files'] if f['key']=='saraga metadata.zip')
    if entry['size']>1000000:raise ValueError('Unexpected metadata archive size')
    archive=out/'metadata.zip'
    if not archive.exists():
        response=requests.get(entry['links']['self'],timeout=60);response.raise_for_status()
        if len(response.content)!=entry['size']:raise ValueError('Incomplete metadata download')
        if hashlib.md5(response.content).hexdigest()!=entry['checksum'].split(':')[1]:
            raise ValueError('Metadata checksum mismatch')
        archive.write_bytes(response.content)
    if hashlib.md5(archive.read_bytes()).hexdigest()!=entry['checksum'].split(':')[1]:
        raise ValueError('Cached metadata checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist())>20000000:raise ValueError('Unexpected inflated size')
        for info in z.infolist():
            target=(out/'metadata'/info.filename).resolve()
            if not target.is_relative_to((out/'metadata').resolve()):raise ValueError('Unsafe ZIP member path')
            if info.is_dir():continue
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info))
    write_json(out/'source.json',dict(record='https://zenodo.org/records/15102483',
        license=metadata['metadata'].get('license'),files=metadata['files'],
        downloaded='metadata only',metadata_sha256=sha(archive),
        attribution='Shankar A, Plaja-Roglans G, Nuttall T, Rocamora M, Serra X. Saraga Audiovisual, ISMIR 2024.'))
    print(f'Metadata verified and extracted to {out}')


if __name__=='__main__':main()
