"""Resolve existing CompMusic recording IDs through public MusicBrainz relations.

At most one request per 1.1 seconds; bounded responses, resumable local receipts,
single-process lock, no title search or guessed work identity. No audio fetched.
"""
import argparse,datetime,fcntl,json,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import requests
from scripts.raga_pipeline import sha,write_json


def work_links(recording,expected_id):
    if recording.get('id')!=expected_id:raise ValueError('Recording ID changed; explicit merge review required')
    works={}
    for relation in recording.get('relations',[]):
        if relation.get('target-type')!='work' or relation.get('type')!='performance':continue
        work=relation['work'];key=str(uuid.UUID(work['id']))
        works[key]=dict(work_id=key,title=work.get('title',''))
    return list(works.values())


def fetch_receipt(url,recording_id):
    with requests.get(url,params={'inc':'work-rels','fmt':'json'},
        headers={'User-Agent':'CarnatifyResearch/0.1 (https://github.com/ShyamRavidath/carnatify)'},
        timeout=25,stream=True) as response:
        if response.status_code not in (200,404):return dict(status=response.status_code)
        body=bytearray()
        for block in response.iter_content(65536):
            body.extend(block)
            if len(body)>2*1024*1024:raise ValueError('Oversized metadata response')
        payload=json.loads(body) if response.status_code==200 else None
        if payload is not None:work_links(payload,recording_id)
        return dict(url=url,status=response.status_code,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),recording=payload)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--limit',type=int,default=3)
    args=ap.parse_args()
    if args.limit<1:ap.error('--limit must be positive')
    import mirdata
    base=ROOT/'data/overhaul/compmusic_work_links';base.mkdir(parents=True,exist_ok=True)
    dataset=mirdata.initialize('compmusic_raga',data_home=str(ROOT));rows=[]
    for track in dataset.load_tracks().values():
        if track.tradition!='carnatic' or not Path(track.pitch_path).exists():continue
        rows.append(dict(track=track.track_id,recording_id=str(uuid.UUID(track.mbid)),
            title=track.recording,artist=track.artist,raga=track.raga,
            pitch=str(Path(track.pitch_path).relative_to(ROOT)),pitch_sha256=sha(track.pitch_path)))
    rows.sort(key=lambda r:r['recording_id']);plan=base/'plan.json'
    protocol=dict(source='local CompMusic distributed recording IDs',rows=rows)
    if plan.exists() and json.loads(plan.read_text())!=protocol:raise ValueError('Local reference plan changed')
    if not plan.exists():write_json(plan,protocol)
    results=[];next_request=0.;attempted=0;unavailable_status=None;unavailable_error=None
    def checkpoint():
        write_json(base/'result.json',dict(plan_sha256=sha(plan),n_planned=len(rows),n_checked=len(results),
            complete=len(results)==len(rows),rows=results,network_attempts=attempted,
            unavailable_http_status=unavailable_status,unavailable_error=unavailable_error,
            status='public recording relations only; not yet integrated into a song catalog'))
    with (base/'fetch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for row in rows:
            path=base/(row['recording_id']+'.json')
            if not path.exists():
                if attempted>=args.limit:break
                url='https://musicbrainz.org/ws/2/recording/'+row['recording_id']
                fetched=None
                for attempt in range(3):
                    if attempted>=args.limit:break
                    time.sleep(max(0.,next_request-time.monotonic()));attempted+=1
                    unavailable_status=None;unavailable_error=None
                    try:
                        fetched=fetch_receipt(url,row['recording_id'])
                        if fetched['status'] in (200,404):break
                        unavailable_status=fetched['status']
                    except requests.RequestException as exc:
                        unavailable_error=type(exc).__name__
                    finally:
                        next_request=time.monotonic()+3.
                    if unavailable_status not in (None,408,429,500,502,503,504):break
                    if attempt<2 and attempted<args.limit:
                        delay=10*(attempt+1)
                        print(f'Transient metadata failure; retrying this recording after {delay}s.',flush=True)
                        next_request=time.monotonic()+delay
                if unavailable_status is not None or unavailable_error is not None:
                    print(f'Public metadata unavailable: {unavailable_error or unavailable_status}; completed receipts retained.',flush=True)
                    break
                write_json(path,fetched)
            receipt=json.loads(path.read_text())
            if receipt['status'] not in (200,404):raise ValueError('Invalid cached receipt')
            links=work_links(receipt['recording'],row['recording_id']) if receipt['status']==200 else []
            results.append(dict(**row,works=links,receipt_sha256=sha(path),
                status='single_explicit_work' if len(links)==1 else ('multiple_works_quarantined' if links else 'no_work_link')))
            checkpoint()
            print(f'{len(results)}/{len(rows)} references checked; {row["title"]}: {len(links)} work links',flush=True)
    checkpoint()
    if unavailable_status is not None or unavailable_error is not None:raise SystemExit(2)


if __name__=='__main__':main()
