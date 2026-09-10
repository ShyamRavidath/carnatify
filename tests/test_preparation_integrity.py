"""Rare labels must not hide contradictory labels on identical recordings."""
import json
from argparse import Namespace
import numpy as np
from scripts import raga_pipeline


def test_duplicate_conflicts_are_quarantined_before_minimum_class_filter(tmp_path,monkeypatch):
    monkeypatch.setattr(raga_pipeline,'ROOT',tmp_path)
    data=tmp_path/'data'
    for directory in ['raga_coverage','qmax_audit','raga_v2_cache/archive_v3','raga_v2_cache/melodia_full']:
        (data/directory).mkdir(parents=True)
    ids=['common_copy','common_unique','rare_copy']
    np.savez(data/'raga_coverage/matrix.npz',g=ids,y=['A','A','B'],gc=['x','y','z'])
    provenance=[]
    for i,tid in enumerate(ids):
        np.savez(data/f'raga_v2_cache/archive_v3/{tid}.npz',track_id=tid,tonics=[138.])
        np.save(data/f'raga_v2_cache/melodia_full/{tid}.npy',np.full(100,220. if i!=1 else 330.))
        provenance.append(dict(stem=tid,archive_identifier=tid,audio_path=f'{tid}.wav'))
    (data/'qmax_audit/provenance.json').write_text(json.dumps(provenance))
    run=tmp_path/'run'
    raga_pipeline.prepare(Namespace(run=run,min_tracks=2,max_classes=0))
    result=json.loads((run/'manifest.json').read_text())
    assert result['skipped']['conflicting_recording_labels']==2
    assert result['rows']==[]  # A has only one valid track after quarantine.
