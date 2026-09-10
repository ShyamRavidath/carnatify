"""Extend a candidate catalog using explicit MusicBrainz work relations only.

Uses existing distributed pitch/tonic, not newly downloaded audio. A partial
metadata lookup is allowed only by explicit opt-in and remains visible.
"""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json
from scripts.fetch_compmusic_work_links import work_links
from scripts.saraga_recording_identity import attach_recording_ids
from carnatify.ml.composition_catalog import CompositionCatalog,CATALOG_VERSION
from carnatify.ml.melody_retrieval import melody_sequence
from carnatify.audio.cache_io import atomic_npz
from carnatify.ml.retrieval_prior import key


def verified_single_work(row,receipt):
    links=work_links(receipt['recording'],row['recording_id']) if receipt['status']==200 else []
    if links!=row['works']:raise ValueError('Derived work links disagree with source receipt')
    if len(links)!=1 or row['status']!='single_explicit_work':return None
    return links[0]


def duplicate_recording_reason(recording_id,work_id,recordings):
    if recording_id not in recordings:return None
    return ('duplicate_recording' if recordings[recording_id]['work_id']==work_id
            else 'conflicting_work_for_same_recording')


def improvisation_work(title,raga):
    remainder=key(title)
    if key(raga):remainder=remainder.replace(key(raga),'')
    for instrument in ('vocal','violin','instrumental'):
        remainder=remainder.replace(instrument,'')
    return remainder in {'ragam','raga','alapana','alaapana','alap','tanam','thaanam',
        'ragamtanampallavi','ragamthanampallavi','ragamthaanampallavi','rtp',
        'tani','thani','taniavartanam','taniavarthanam'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=Path,default=ROOT/'data/overhaul/repro_v2/compositions.npz')
    ap.add_argument('--links',type=Path,default=ROOT/'data/overhaul/compmusic_work_links/result.json')
    ap.add_argument('--receipt-dir',type=Path,help='Receipt/plan directory when rebuilding from a frozen lookup snapshot')
    ap.add_argument('--allow-partial',action='store_true');ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--max-recordings',type=int,help='Fixed prefix of the recording-ID-sorted lookup plan for a development checkpoint')
    args=ap.parse_args()
    if args.out.resolve()==args.base.resolve():ap.error('Preserve the original catalog')
    payload=args.links.read_bytes();links=json.loads(payload)
    receipt_dir=args.receipt_dir or args.links.parent
    if args.max_recordings is not None and (args.max_recordings<1 or len(links['rows'])<args.max_recordings):
        ap.error('--max-recordings requires that many completed lookup rows')
    if not links['complete'] and not args.allow_partial:ap.error('Metadata lookup incomplete; use a separate explicit --allow-partial experiment')
    if sha(receipt_dir/'plan.json')!=links['plan_sha256']:raise ValueError('Metadata plan changed')
    base=CompositionCatalog(args.base);sidecar=json.loads(args.base.with_suffix('.json').read_text())
    if sidecar['catalog_sha256']!=sha(args.base):raise ValueError('Base catalog/report mismatch')
    import mirdata
    tracks=mirdata.initialize('compmusic_raga',data_home=str(ROOT)).load_tracks()
    frames=[base.frames];offsets=list(base.offsets);metadata=attach_recording_ids(base.metadata);seen={r['track'] for r in metadata}
    recordings={r['recording_id']:r for r in metadata if r.get('recording_id')}
    added=[];skipped=[]
    selected=links['rows'][:args.max_recordings] if args.max_recordings is not None else links['rows']
    for row in selected:
        receipt_path=receipt_dir/(row['recording_id']+'.json')
        if sha(receipt_path)!=row['receipt_sha256']:raise ValueError('Work receipt changed')
        work=verified_single_work(row,json.loads(receipt_path.read_text()))
        if work is None:skipped.append(dict(track=row['track'],reason='no_unique_work'));continue
        if improvisation_work(work['title'],row['raga']):
            skipped.append(dict(track=row['track'],reason='generic_improvisation_work'));continue
        reason=duplicate_recording_reason(row['recording_id'],work['work_id'],recordings)
        if reason:
            original=recordings[row['recording_id']]
            skipped.append(dict(track=row['track'],reason=reason,existing_track=original['track']));continue
        t=tracks[row['track']];track='compmusic__'+t.track_id
        if track in seen:raise ValueError('Duplicate reference track')
        if t.mbid!=row['recording_id'] or sha(t.pitch_path)!=row['pitch_sha256']:
            raise ValueError('Local reference identity or contour changed')
        pitch=t.pitch;hop=float(np.median(np.diff(pitch.times)))
        seq=melody_sequence(pitch.frequencies,t.tonic,hop)
        if len(seq)<8:skipped.append(dict(track=row['track'],reason='insufficient_melody'));continue
        meta=dict(track=track,work_id=work['work_id'],title=work['title'],raga=t.raga,
            artists=[t.artist],source='CompMusic:'+t.artist+'/'+t.concert,
            audio_sha256=None,pitch_sha256=row['pitch_sha256'],tonic_sha256=sha(t.tonic_path),
            recording_id=row['recording_id'],identity_evidence='explicit_musicbrainz_performance_work_relation',
            receipt_sha256=row['receipt_sha256'],frontend='CompMusic distributed pitch and tonic')
        frames.append(seq);offsets.append(offsets[-1]+len(seq));metadata.append(meta);seen.add(track);added.append(meta)
        recordings[row['recording_id']]=meta
    if not added:raise ValueError('No verified additional references')
    atomic_npz(args.out,version=CATALOG_VERSION,frames=np.concatenate(frames),offsets=np.array(offsets),
               metadata=json.dumps(metadata,ensure_ascii=False))
    snapshot=args.out.with_suffix('.source_links.json');write_json(snapshot,links)
    write_json(args.out.with_suffix('.json'),dict(version=CATALOG_VERSION,catalog_sha256=sha(args.out),
        base_catalog_sha256=sha(args.base),source_links_sha256=hashlib.sha256(payload).hexdigest(),
        source_links_snapshot_sha256=sha(snapshot),metadata_lookup_complete=links['complete'],
        receipt_directory=str(receipt_dir.resolve()),
        n_lookup_records_used=len(selected),selection='recording-ID-sorted prefix' if args.max_recordings else 'all completed lookup rows',
        n_tracks=len(metadata),n_works=len({r['work_id'] for r in metadata}),n_added=len(added),skipped=skipped,
        status='candidate catalog; expanded-reference evaluation and rejection required; no deployment'))
    print(f'{len(added)} verified references added; {len(metadata)} total; lookup complete={links["complete"]}')


if __name__=='__main__':main()
