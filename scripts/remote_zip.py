"""Read selected public ZIP members with bounded, verified HTTP range reads.

Never silently fall back to downloading an entire archive when a server ignores
Range. This is for public dataset GETs only, not authenticated private resources.
"""
from __future__ import annotations
import io
import time
import hashlib
import os
import tempfile
from pathlib import Path
from collections import OrderedDict
import requests


class TransientRangeError(RuntimeError):
    pass


class RangeReader(io.RawIOBase):
    def __init__(self,url,size,block_size=4*1024*1024,max_cached_blocks=8,retry_attempts=3,
                 cache_dir=None,archive_checksum=''):
        if size<=0 or not 0<block_size<=32*1024*1024 or max_cached_blocks<1 or not 1<=retry_attempts<=5:
            raise ValueError('Invalid bounded range-reader configuration')
        self.url=url;self.size=int(size);self.position=0;self.block_size=block_size
        self.max_cached_blocks=max_cached_blocks;self.blocks=OrderedDict();self.downloaded=0
        self.session=requests.Session()
        self.retry_attempts=retry_attempts
        self.cache_hits=0;self.disk_cache=None
        if cache_dir is not None:
            namespace=hashlib.sha256(f'{url}|{size}|{block_size}|{archive_checksum}'.encode()).hexdigest()
            self.disk_cache=Path(cache_dir)/namespace
            self.disk_cache.mkdir(parents=True,exist_ok=True)

    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.position

    def seek(self,offset,whence=0):
        pos=offset if whence==0 else self.position+offset if whence==1 else self.size+offset if whence==2 else -1
        if pos<0:raise ValueError('Invalid seek')
        self.position=pos;return pos

    def _block(self,index):
        if index in self.blocks:
            self.blocks.move_to_end(index);return self.blocks[index]
        start=index*self.block_size;end=min(start+self.block_size,self.size)-1
        body=self._cached_block(index,end-start+1)
        if body is not None:
            self.cache_hits+=1
            self.blocks[index]=body
            while len(self.blocks)>self.max_cached_blocks:self.blocks.popitem(last=False)
            return body
        for attempt in range(self.retry_attempts):
            try:
                body=self._request_block(start,end)
                break
            except (TransientRangeError,requests.RequestException) as exc:
                if attempt+1==self.retry_attempts:
                    raise TransientRangeError(f'Bounded range request failed after {self.retry_attempts} attempts: {exc}') from exc
                time.sleep(2**attempt)
        self._store_block(index,body)
        self.downloaded+=len(body);self.blocks[index]=body
        while len(self.blocks)>self.max_cached_blocks:self.blocks.popitem(last=False)
        return body

    def _cached_block(self,index,expected_size):
        if self.disk_cache is None:return None
        path=self.disk_cache/f'{index}.block'
        if not path.exists():return None
        with path.open('rb') as stream:stored=stream.read(expected_size+66)
        if len(stored)!=expected_size+65 or stored[64:65]!=b'\n':return None
        body=stored[65:]
        if hashlib.sha256(body).hexdigest().encode()!=stored[:64]:return None
        return body

    def _store_block(self,index,body):
        if self.disk_cache is None:return
        target=self.disk_cache/f'{index}.block'
        fd,temporary=tempfile.mkstemp(prefix=f'.{index}.',suffix='.tmp',dir=self.disk_cache)
        try:
            with os.fdopen(fd,'wb') as stream:
                stream.write(hashlib.sha256(body).hexdigest().encode()+b'\n')
                stream.write(body)
            os.replace(temporary,target)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)

    def _request_block(self,start,end):
        with self.session.get(self.url,headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'},
                              timeout=60,stream=True) as response:
            if response.status_code in (408,429,500,502,503,504):
                raise TransientRangeError(f'Transient HTTP status {response.status_code}')
            if response.status_code!=206:raise IOError(f'Server does not honor bounded ranges: {response.status_code}')
            expected=f'bytes {start}-{end}/{self.size}'
            if response.headers.get('Content-Range')!=expected:raise IOError('Range response mismatch')
            # Bound the body too, even if a server falsely advertises a valid
            # Content-Range but sends more data than requested.
            body=response.raw.read(end-start+2)
        if len(body)!=end-start+1:raise IOError('Truncated range response')
        return body

    def read(self,size=-1):
        size=min(self.size-self.position,size if size>=0 else self.size-self.position)
        if size<=0:return b''
        if size>32*1024*1024:raise IOError('Use bounded streaming reads for large ZIP members')
        parts=[]
        while size:
            index,offset=divmod(self.position,self.block_size)
            block=self._block(index);n=min(size,len(block)-offset)
            if n<=0:raise IOError('Invalid range block')
            parts.append(block[offset:offset+n]);self.position+=n;size-=n
        return b''.join(parts)

    def close(self):
        self.session.close();super().close()
