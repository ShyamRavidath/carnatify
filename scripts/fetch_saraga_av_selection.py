"""Download only the frozen selected mixture WAVs using bounded ZIP ranges."""
import argparse,hashlib,json,sys,zipfile,time,zlib
from contextlib import ExitStack
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.remote_zip import RangeReader,TransientRangeError
from scripts.raga_pipeline import write_json,sha


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,default=ROOT/'data/overhaul/saraga_av')
    args=ap.parse_args();base=args.run.resolve();plan=base/'evaluation_plan.json'
    selection=json.loads(plan.read_text());source=json.loads((ROOT/'data/overhaul/saraga_av/audio_index.json').read_text())['source']
    out=base/'audio';out.mkdir(parents=True,exist_ok=True)
    report=dict(plan_sha256=sha(plan),rows=[]);started=time.monotonic()
    with ExitStack() as stack:
        reader=None;archive=None
        for row in selection['rows']:
            member=row['archive_member']
            target=out/(row['track']+'.wav')
            if not target.exists():
                if archive is None:
                    reader=stack.enter_context(RangeReader(source['links']['self'],source['size'],
                        cache_dir=ROOT/'data/overhaul/cache/zip_ranges',archive_checksum=source['checksum']))
                    archive=stack.enter_context(zipfile.ZipFile(reader))
                info=archive.getinfo(member['path'])
                if info.file_size!=member['size'] or info.CRC!=member['crc32']:raise ValueError('Remote archive changed')
                temporary=target.with_suffix('.wav.part')
                total=0
                with archive.open(info) as inp,temporary.open('wb') as dst:
                    while block:=inp.read(4*1024*1024):
                        total+=len(block)
                        if total>member['size']:raise ValueError('Unexpected member size')
                        dst.write(block)
                if total!=member['size']:raise ValueError('Truncated ZIP member')
                temporary.replace(target)
            if target.stat().st_size!=member['size']:raise ValueError('Cached WAV size mismatch')
            digest=hashlib.sha256();crc=0
            with target.open('rb') as inp:
                while block:=inp.read(4*1024*1024):
                    digest.update(block);crc=zlib.crc32(block,crc)
            if crc!=member['crc32']:raise ValueError('Cached WAV checksum mismatch')
            # ZIP CRC validates newly decoded members; SHA records reproducible
            # local input identity for inference and subsequent resume checks.
            report['rows'].append(dict(track=row['track'],audio=str(target.relative_to(ROOT)),audio_sha256=digest.hexdigest()))
            report['downloaded_bytes']=reader.downloaded if reader else 0;report['elapsed_s']=time.monotonic()-started
            report['persistent_range_cache_hits']=reader.cache_hits if reader else 0
            write_json(base/'download.json',report)
            print(f'{len(report["rows"])}/{len(selection["rows"])} WAVs; {report["downloaded_bytes"]/1e6:.1f} MB fetched',flush=True)


if __name__=='__main__':
    try:
        main()
    except TransientRangeError as exc:
        print(f'Archive temporarily unavailable: {exc}. Cached ranges and completed WAVs are retained for resume.',file=sys.stderr)
        raise SystemExit(2)
