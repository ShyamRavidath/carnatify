"""Fetch immutable upstream source for the local-only recording-copy audit."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '5c3be6803856f25b11d1d704bac56e733b4fc997'  # upstream v1.5.1
ARCHIVE_SHA256 = 'b134542bf50af0106c73b701a9b0cd876b15de3fba8e064f8fe36bedfb3a8351'
OUT = ROOT / 'data/overhaul/chromaprint'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    url = f'https://codeload.github.com/acoustid/chromaprint/tar.gz/{COMMIT}'
    archive = OUT / 'source.tar.gz'
    if not archive.exists():
        with urlopen(Request(url, headers={'User-Agent': 'Carnatify-research-audit'}), timeout=60) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('Source archive exceeds expected bound')
        archive.write_bytes(raw)
    raw = archive.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Pinned source archive checksum mismatch')
    receipt = dict(commit=COMMIT, release='v1.5.1', url=url,
                   sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                   scope='local audit tool only; no binary distribution or model promotion')
    receipt_path = OUT / 'source_receipt.json'
    if receipt_path.exists() and json.loads(receipt_path.read_text()) != receipt:
        raise ValueError('Source archive changed')
    destination = OUT / 'source'
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if not parts or parts[0] != 'chromaprint-' + COMMIT or '..' in parts:
                raise ValueError('Unexpected source archive path')
            target = destination.joinpath(*parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                payload = tar.extractfile(member).read()
                if target.exists() and target.read_bytes() != payload:
                    raise ValueError('Existing source differs from pinned archive')
                target.write_bytes(payload)
            elif (member.issym() and parts[1:] == ('src', 'include', 'chromaprint.h')
                  and member.linkname == '../chromaprint.h'):
                # Materialize the one audited internal header alias. Never
                # create archive-controlled symlinks in the workspace.
                header = tar.getmember(parts[0] + '/src/chromaprint.h')
                if not header.isfile():
                    raise ValueError('Header alias target is not a regular file')
                payload = tar.extractfile(header).read()
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_bytes() != payload:
                    raise ValueError('Existing header alias differs')
                target.write_bytes(payload)
            else:
                raise ValueError('Non-regular source archive entry')
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
