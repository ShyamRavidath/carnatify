import json
import zlib
from scripts import fetch_saraga_av_selection as fetch


def test_complete_verified_selection_needs_no_network(tmp_path,monkeypatch):
    base=tmp_path/'data/overhaul/saraga_av';run=base/'test';(run/'audio').mkdir(parents=True)
    body=b'local fixture; decoder is not used during checksum verification'
    (run/'audio/one.wav').write_bytes(body)
    (base/'audio_index.json').write_text(json.dumps(dict(source=dict(size=100,checksum='frozen',links={'self':'https://example.invalid'}))))
    plan=dict(rows=[dict(track='one',archive_member=dict(path='archive/one.wav',size=len(body),crc32=zlib.crc32(body)))])
    (run/'evaluation_plan.json').write_text(json.dumps(plan))
    monkeypatch.setattr(fetch,'ROOT',tmp_path)
    monkeypatch.setattr(fetch.sys,'argv',['fetch','--run',str(run)])
    def forbidden(*args,**kwargs):raise AssertionError('Completed selection must not contact server')
    monkeypatch.setattr(fetch,'RangeReader',forbidden)
    fetch.main()
    receipt=json.loads((run/'download.json').read_text())
    assert receipt['downloaded_bytes']==0 and len(receipt['rows'])==1
