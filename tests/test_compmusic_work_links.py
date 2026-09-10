import pytest
from scripts.fetch_compmusic_work_links import work_links

RID='9aa2770a-c170-4db9-9657-14a74024bc31'
WID='11d3ea14-7cb2-4a8e-b77b-232e7fb86af0'


def test_only_explicit_performance_relations_supply_identity():
    relation={'target-type':'work','type':'performance','work':{'id':WID,'title':'Known work'}}
    result=work_links({'id':RID,'relations':[relation,relation,{'target-type':'artist','type':'performance'}]},RID)
    assert result==[{'work_id':WID,'title':'Known work'}]


def test_titles_and_changed_recording_ids_are_not_identity_evidence():
    assert work_links({'id':RID,'title':'Known work'},RID)==[]
    with pytest.raises(ValueError,match='Recording ID changed'):work_links({'id':WID},RID)


def test_temporary_outage_is_not_cached_as_absent_work(tmp_path,monkeypatch):
    import json,sys,mirdata
    from types import SimpleNamespace
    import scripts.fetch_compmusic_work_links as module
    pitch=tmp_path/'pitch.txt';pitch.write_text('0 220\n')
    track=SimpleNamespace(tradition='carnatic',pitch_path=str(pitch),track_id='track',
        mbid=RID,recording='title',artist='artist',raga='raga')
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(mirdata,'initialize',lambda *a,**k:SimpleNamespace(load_tracks=lambda:{'track':track}))
    class Unavailable:
        status_code=503
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setattr(module.requests,'get',lambda *a,**k:Unavailable())
    monkeypatch.setattr(sys,'argv',['fetch_compmusic_work_links.py','--limit','1'])
    with pytest.raises(SystemExit) as exc:module.main()
    assert exc.value.code==2
    base=tmp_path/'data/overhaul/compmusic_work_links'
    assert not (base/(RID+'.json')).exists()
    report=json.loads((base/'result.json').read_text())
    assert report['unavailable_http_status']==503 and report['n_checked']==0 and not report['complete']


def test_timeout_preserves_completed_lookup_in_progress_report(tmp_path,monkeypatch):
    import json,sys,mirdata,requests
    from types import SimpleNamespace
    import scripts.fetch_compmusic_work_links as module
    pitch=tmp_path/'pitch.txt';pitch.write_text('0 220\n')
    ids=['00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002']
    tracks={rid:SimpleNamespace(tradition='carnatic',pitch_path=str(pitch),track_id=rid,
        mbid=rid,recording='title',artist='artist',raga='raga') for rid in ids}
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(mirdata,'initialize',lambda *a,**k:SimpleNamespace(load_tracks=lambda:tracks))
    monkeypatch.setattr(module.time,'sleep',lambda _:None)
    def fetch(url,rid):
        if rid==ids[1]:raise requests.ReadTimeout('simulated')
        return dict(url=url,status=200,recording={'id':rid,'relations':[]})
    monkeypatch.setattr(module,'fetch_receipt',fetch)
    monkeypatch.setattr(sys,'argv',['fetch_compmusic_work_links.py','--limit','2'])
    with pytest.raises(SystemExit) as exc:module.main()
    assert exc.value.code==2
    base=tmp_path/'data/overhaul/compmusic_work_links'
    report=json.loads((base/'result.json').read_text())
    assert report['n_checked']==1 and report['unavailable_error']=='ReadTimeout'
    assert (base/(ids[0]+'.json')).exists() and not (base/(ids[1]+'.json')).exists()
