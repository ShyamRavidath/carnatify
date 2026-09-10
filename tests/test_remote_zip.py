import io,zipfile
import pytest
from scripts.remote_zip import RangeReader


class Response:
    def __init__(self,data,start,end,status=206):
        self.status_code=status;self.headers={'Content-Range':f'bytes {start}-{end}/{len(data)}'}
        self.content=data[start:end+1]
        self.raw=io.BytesIO(self.content)
    def __enter__(self):return self
    def __exit__(self,*args):pass


class Session:
    def __init__(self,data,status=206):self.data=data;self.status=status;self.calls=0
    def get(self,url,headers,**kwargs):
        self.calls+=1;a,b=map(int,headers['Range'][6:].split('-'))
        return Response(self.data,a,b,self.status)
    def close(self):pass


def test_zip_reads_only_requested_ranges():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:z.writestr('one.txt','music')
    data=buf.getvalue();reader=RangeReader('https://example.invalid',len(data),block_size=32)
    reader.session=Session(data)
    with zipfile.ZipFile(reader) as z:assert z.read('one.txt')==b'music'
    assert reader.downloaded<=len(data)
    reader.seek(0);assert reader.read(3)==data[:3]


def test_ignored_range_is_rejected_without_full_archive_fallback():
    reader=RangeReader('https://example.invalid',100,block_size=32)
    reader.session=Session(b'x'*100,status=200)
    with pytest.raises(IOError,match='does not honor'):reader.read(1)
    assert reader.session.calls==1
    large=RangeReader('https://example.invalid',100*1024*1024)
    with pytest.raises(IOError,match='bounded'):large.read()


def test_transient_gateway_failure_retries_same_bounded_request(monkeypatch):
    from scripts import remote_zip
    monkeypatch.setattr(remote_zip.time,'sleep',lambda _:None)
    class RecoveringSession(Session):
        def get(self,*args,**kwargs):
            self.status=504 if self.calls==0 else 206
            return super().get(*args,**kwargs)
    reader=RangeReader('https://example.invalid',100,block_size=32)
    reader.session=RecoveringSession(b'x'*100)
    assert reader.read(1)==b'x'
    assert reader.session.calls==2
    assert reader.downloaded==32


def test_transient_failures_are_bounded(monkeypatch):
    from scripts import remote_zip
    monkeypatch.setattr(remote_zip.time,'sleep',lambda _:None)
    reader=RangeReader('https://example.invalid',100,block_size=32)
    reader.session=Session(b'x'*100,status=504)
    with pytest.raises(remote_zip.TransientRangeError,match='after 3 attempts'):
        reader.read(1)
    assert reader.session.calls==3


def test_persistent_ranges_resume_without_network_and_repair_corrupt_cache(tmp_path):
    kwargs=dict(block_size=32,cache_dir=tmp_path,archive_checksum='frozen-checksum')
    first=RangeReader('https://example.invalid',100,**kwargs);first.session=Session(b'x'*100)
    assert first.read(1)==b'x'
    resumed=RangeReader('https://example.invalid',100,**kwargs);resumed.session=Session(b'x'*100,status=504)
    assert resumed.read(1)==b'x' and resumed.session.calls==0 and resumed.cache_hits==1
    block=next(tmp_path.rglob('*.block'));block.write_bytes(b'corrupt cache fixture')
    repaired=RangeReader('https://example.invalid',100,**kwargs);repaired.session=Session(b'x'*100)
    assert repaired.read(1)==b'x' and repaired.session.calls==1
    changed=RangeReader('https://example.invalid',100,block_size=32,cache_dir=tmp_path,archive_checksum='new-checksum')
    changed.session=Session(b'y'*100)
    assert changed.read(1)==b'y' and changed.session.calls==1
