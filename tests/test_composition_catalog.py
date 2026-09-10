import json
import numpy as np
import pytest
from carnatify.ml.composition_catalog import CompositionCatalog,CATALOG_VERSION
from carnatify.ml.melody_retrieval import melody_sequence


def test_catalog_ranks_without_pickle_and_can_exclude_recording(tmp_path):
    f=np.repeat(220*2**(np.array([0,2,4,7,9,7,4,2,0,2,4,0])/12),50)
    q=melody_sequence(f,220,.01);other=np.eye(24,dtype=np.float32)[[23]*len(q)]
    meta=[dict(work_id='one',title='One',raga='A',track='a',audio_sha256='first'),
          dict(work_id='two',title='Two',raga='B',track='b',audio_sha256='second')]
    path=tmp_path/'catalog.npz'
    np.savez_compressed(path,version=CATALOG_VERSION,frames=np.r_[q,other],
                        offsets=np.array([0,len(q),2*len(q)]),metadata=json.dumps(meta))
    catalog=CompositionCatalog(path)
    assert catalog.rank(f,220,.01)[0]['work_id']=='one'
    result=catalog.rank(f,220,.01,exclude_audio_hashes=['first'])
    assert all(r['work_id']!='one' and r['status']=='unverified_candidate' for r in result)


def test_catalog_version_checked(tmp_path):
    path=tmp_path/'bad.npz';np.savez(path,version='unknown')
    with pytest.raises(ValueError,match='version'):CompositionCatalog(path)


def test_prior_is_applied_before_work_deduplication(tmp_path,monkeypatch):
    import carnatify.ml.composition_catalog as module
    metadata=[dict(work_id=w,title=w,raga=r,track=str(i))
              for i,(w,r) in enumerate([('one','A'),('one','B'),('two','A'),('short','B')])]
    path=tmp_path/'catalog.npz'
    np.savez(path,version=CATALOG_VERSION,frames=np.zeros((32,24),np.float32),
             offsets=np.arange(0,33,8),metadata=json.dumps(metadata))
    monkeypatch.setattr(module,'melody_sequence',lambda *a:np.zeros((8,24)))
    costs=iter([.2,.21,.19,float('inf')])
    monkeypatch.setattr(module,'subsequence_distance',lambda *a,**kw:next(costs))
    ranked=CompositionCatalog(path).rank([],110,.01,raga_probabilities={'B':1.})
    assert ranked[0]['work_id']=='one' and ranked[0]['reference_track']=='1'
    assert ranked[0]['distance']==ranked[0]['ranking_cost']==.21
    assert ranked[1]['distance']==.19 and ranked[1]['ranking_cost']==pytest.approx(.29)
    assert all(r['status']=='unverified_candidate' for r in ranked)
