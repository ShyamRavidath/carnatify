import hashlib
import json
import sys
import numpy as np
import pytest
from scripts import merge_context_decode_recovery as module
from scripts.raga_pipeline import sha,write_json,load_features
from carnatify.audio.cache_io import atomic_npz
from carnatify.ml.melody_features import FEATURE_VERSION


def fixture(tmp_path):
    run=tmp_path/'run';recovery=tmp_path/'recovery';out=tmp_path/'out'
    audio=tmp_path/'raw';audio.write_bytes(b'unchanged')
    row=dict(track='r',corpus='archive',audio=str(audio),audio_sha256=sha(audio),label='Kamas',group='artist:a')
    write_json(run/'plan.json',dict(rows=[row],policy='parent frontend'))
    window=dict(start_s=0.,duration_s=15.,reason='libsndfile_window_decode_error')
    track=run/'tracks'/(hashlib.sha256(b'r').hexdigest()+'.npz')
    atomic_npz(track,plan_sha256=sha(run/'plan.json'),metadata=json.dumps(dict(rejected=[window],windows=[])))
    write_json(recovery/'plan.json',dict(row=row,windows=[window],inputs={str((run/'plan.json').resolve()):sha(run/'plan.json'),str(track.resolve()):sha(track)}))
    receipt=dict(track='r',start_s=0.,duration_s=15.)
    atomic_npz(recovery/'window_0.npz',X=np.ones(5280),legacy=np.ones(4800),f0=np.ones(100)*220,
        plan_sha256=sha(recovery/'plan.json'),metadata=json.dumps(receipt))
    write_json(recovery/'result.json',dict(plan_sha256=sha(recovery/'plan.json'),windows=[receipt]))
    write_json(run/'manifest.json',dict(rows=[],context_plan_sha256=sha(run/'plan.json'),protocol=dict(window_s=180)))
    atomic_npz(run/'features.npz',X=np.zeros((0,5280)),legacy=np.zeros((0,4800)),
        y=np.array([],dtype=str),track=np.array([],dtype=str),group=np.array([],dtype=str),
        version=FEATURE_VERSION,manifest_sha256=sha(run/'manifest.json'))
    write_json(run/'extraction.json',dict(plan_sha256=sha(run/'plan.json'),rows=[dict(track='r')],tracks=0,windows=0))
    folds=tmp_path/'folds.json';write_json(folds,dict(folds=dict(r=2)))
    return run,recovery,out,folds


def test_merge_preserves_parent_and_adds_only_rejected_window(tmp_path,monkeypatch):
    run,recovery,out,folds=fixture(tmp_path);before=sha(run/'features.npz')
    monkeypatch.setattr(sys,'argv',['merge','--run',str(run),'--recovery',str(recovery),
        '--folds',str(folds),'--out',str(out)])
    module.main();z=load_features(out)
    assert z['X'].shape==(1,5280) and z['track'].tolist()==['r']
    assert z['y'].tolist()==['Kamas'] and z['group'].tolist()==['artist:a']
    assert sha(run/'features.npz')==before
    assert json.loads((out/'folds.json').read_text())['folds']==dict(r=2)


def test_merge_refuses_incomplete_parent(tmp_path,monkeypatch):
    run,recovery,out,folds=fixture(tmp_path)
    write_json(run/'extraction.json',dict(plan_sha256=sha(run/'plan.json'),rows=[],tracks=0,windows=0))
    monkeypatch.setattr(sys,'argv',['merge','--run',str(run),'--recovery',str(recovery),
        '--folds',str(folds),'--out',str(out)])
    with pytest.raises(ValueError,match='incomplete'):module.main()
    assert not out.exists()


def test_merge_rejects_stale_raw_identity(tmp_path):
    run,recovery,out,folds=fixture(tmp_path)
    (tmp_path/'raw').write_bytes(b'changed')
    with pytest.raises(ValueError,match='raw audio changed'):module.checked_recovery(run,recovery)
