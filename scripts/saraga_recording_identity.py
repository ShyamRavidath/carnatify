"""Attach explicit recording IDs without rewriting frozen evaluation manifests."""
import uuid
from scripts.raga_pipeline import ROOT,sha


def recording_from_metadata(row,metadata):
    identifier=str(uuid.UUID(metadata['mbid']))
    if identifier in {a.get('mbid') for a in metadata.get('album_artists',[])}:
        raise ValueError('Artist ID supplied where recording identity is required')
    works=metadata.get('work') or []
    work_id=works[0].get('mbid') if len(works)==1 else None
    if row.get('work_id')!=work_id:raise ValueError('Work annotation changed')
    return identifier


def attach_recording_ids(rows):
    import mirdata
    dataset=mirdata.initialize('saraga_carnatic',data_home=str(ROOT))
    result=[]
    for row in rows:
        if row.get('recording_id'):
            result.append(dict(row));continue
        track=dataset.track(row['track'])
        result.append(dict(row,recording_id=recording_from_metadata(row,track.metadata),
                           recording_metadata_sha256=sha(track.metadata_path)))
    return result


def same_recording(a,b):
    return bool(a.get('recording_id') and a['recording_id']==b.get('recording_id'))
