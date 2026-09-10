import hashlib
import pytest
from scripts.fetch_dhenuka_coverage_pilot import validate_bytes


def test_coverage_download_requires_both_published_hashes_and_size(tmp_path):
    path=tmp_path/'blob';path.write_bytes(b'bounded audio test')
    entry=dict(size=path.stat().st_size,md5=hashlib.md5(path.read_bytes()).hexdigest(),sha1=hashlib.sha1(path.read_bytes()).hexdigest())
    assert validate_bytes(path,entry)['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='checksum'):validate_bytes(path,dict(entry,sha1='0'*40))
    with pytest.raises(ValueError,match='size'):validate_bytes(path,dict(entry,size=1))
