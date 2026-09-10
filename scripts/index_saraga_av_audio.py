"""Read just the Saraga AV ZIP index; do not download 65 GB of audio."""
import json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.remote_zip import RangeReader
from scripts.raga_pipeline import write_json


def main():
    base=ROOT/'data/overhaul/saraga_av';source=json.loads((base/'source.json').read_text())
    entry=next(f for f in source['files'] if f['key']=='saraga audio.zip')
    with RangeReader(entry['links']['self'],entry['size']) as reader:
        with zipfile.ZipFile(reader) as archive:
            rows=[dict(path=i.filename,size=i.file_size,compressed_size=i.compress_size,crc32=i.CRC)
                  for i in archive.infolist() if not i.is_dir() and '__MACOSX' not in i.filename
                  and not Path(i.filename).name.startswith('.')]
        write_json(base/'audio_index.json',dict(source=entry,downloaded_bytes=reader.downloaded,rows=rows))
        print(f'{len(rows)} members indexed using {reader.downloaded/1e6:.2f} MB')
        for r in rows[:15]:print(r)


if __name__=='__main__':main()
