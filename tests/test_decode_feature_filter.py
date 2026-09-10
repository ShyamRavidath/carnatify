import json
import sys
import numpy as np
from scripts import filter_strict_decode_features as module
from scripts.raga_pipeline import sha,write_json,load_features
from carnatify.ml.melody_features import FEATURE_VERSION


def test_filter_preserves_reference_features_and_fold_assignments(tmp_path,monkeypatch):
    source=tmp_path/'source';out=tmp_path/'out'
    manifest=source/'manifest.json'
    write_json(manifest,dict(rows=[dict(track='reference',corpus='compmusic',label='r',group='g')]))
    np.savez(source/'features.npz',X=np.ones((2,5280)),legacy=np.ones((2,4800)),
        y=np.array(['r','r']),track=np.array(['reference','reference']),group=np.array(['g','g']),
        version=FEATURE_VERSION,manifest_sha256=sha(manifest))
    write_json(source/'folds.json',dict(feature_sha256=sha(source/'features.npz'),folds=dict(reference=3)))
    identity=tmp_path/'identity.json';audit=tmp_path/'audit.json'
    write_json(identity,dict(rows=[]));write_json(audit,dict(rows=[]))
    original=sha(source/'features.npz')
    monkeypatch.setattr(sys,'argv',['filter','--run',str(source),'--out',str(out),
        '--identity',str(identity),'--decode-audit',str(audit)])
    module.main()
    z=load_features(out)
    assert np.array_equal(z['X'],np.ones((2,5280)))
    assert json.loads((out/'folds.json').read_text())['folds']==dict(reference=3)
    assert sha(source/'features.npz')==original
