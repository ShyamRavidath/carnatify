"""Recover per-track provenance for the Qmax external-eval corpus.

The 60-67% Qmax claim was measured over `data/raga_v2_cache/melodia_full/`,
whose filenames (`archive__<raga>__<title stem>.npy`) carry no provenance at
all. This script rebuilds it so that the audit can ask whether a query was
ever scored against its own recording, its own archive upload, or its own
artist.

Three joins, in decreasing order of reliability:

1. `data/concert_audio/download_manifest.json` — 741 rows written by the
   download scripts, each carrying `archive_identifier` directly.
2. Exact file-size join against `data/raga_v2_cache/archive_metadata/*.json`
   (1,857 cached archive.org item listings). Validated against join 1: on the
   741 manifest rows the size join agrees on every row it resolves.
3. MD5 of the local mp3 against the archive `md5` field, used only to break
   ties when several archive items contain a file of the same size.

Artist comes from `data/raga_v2_cache/archive_identifiers.json`
(source page URL -> archive identifiers) joined to `scraped_compositions.json`
(source page URL -> artist), plus identifiers that spell the artist out.

Read-only. Writes `data/qmax_audit/provenance.json`.

Usage: venv_train/bin/python scripts/qmax_provenance.py
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEL_DIR = ROOT / 'data' / 'raga_v2_cache' / 'melodia_full'
AUDIO = ROOT / 'data' / 'concert_audio'
MANIFEST = AUDIO / 'download_manifest.json'
META_DIR = ROOT / 'data' / 'raga_v2_cache' / 'archive_metadata'
IDENTS = ROOT / 'data' / 'raga_v2_cache' / 'archive_identifiers.json'
SCRAPED = ROOT / 'data' / 'scraped_compositions.json'
OUT_DIR = ROOT / 'data' / 'qmax_audit'

AUDIO_EXT = ('.mp3', '.m4a', '.ogg', '.wav', '.flac')


def nfc(s: str) -> str:
    return unicodedata.normalize('NFC', s or '')


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_archive_index() -> tuple[dict, dict]:
    """(size -> {(ident, name)}, md5 -> {(ident, name)}) over cached listings."""
    by_size: dict[int, set] = defaultdict(set)
    by_md5: dict[str, set] = defaultdict(set)
    for p in sorted(META_DIR.glob('*.json')):
        ident = p.stem
        try:
            files = json.loads(p.read_text())
        except Exception:
            continue
        if not isinstance(files, list):
            continue
        for e in files:
            if not isinstance(e, dict):
                continue
            name = e.get('name')
            if e.get('size'):
                try:
                    by_size[int(e['size'])].add((ident, name))
                except (TypeError, ValueError):
                    pass
            if e.get('md5'):
                by_md5[str(e['md5']).lower()].add((ident, name))
    return by_size, by_md5


def load_artist_map() -> dict[str, str]:
    """archive identifier (lowercased) -> artist, where recoverable."""
    url_artist: dict[str, set] = defaultdict(set)
    for row in json.loads(SCRAPED.read_text()):
        if row.get('source_url') and row.get('artist'):
            url_artist[row['source_url']].add(row['artist'])
    out: dict[str, str] = {}
    for url, idents in json.loads(IDENTS.read_text()).items():
        arts = url_artist.get(url)
        if not arts or len(arts) != 1:
            continue
        artist = next(iter(arts))
        for ident in idents:
            out[ident.lower()] = artist
    return out


def local_audio_for(raga: str, title: str) -> Path | None:
    d = AUDIO / raga
    if not d.is_dir():
        # APFS stores NFD; a NFC lookup misses. Scan by folded name.
        for cand in AUDIO.iterdir():
            if cand.is_dir() and nfc(cand.name) == nfc(raga):
                d = cand
                break
        else:
            return None
    for f in d.iterdir():
        if f.suffix.lower() in AUDIO_EXT and nfc(f.stem) == nfc(title):
            return f
    return None


def main() -> None:
    by_size, by_md5 = load_archive_index()
    artist_of = load_artist_map()

    manifest_ident: dict[tuple[str, str], str] = {}
    if MANIFEST.exists():
        for row in json.loads(MANIFEST.read_text()):
            fp = row.get('file_path')
            if not fp:
                continue
            p = Path(fp)
            manifest_ident[(nfc(p.parent.name), nfc(p.stem))] = row.get('archive_identifier')

    records = []
    agree = disagree = 0
    for p in sorted(MEL_DIR.glob('*.npy')):
        parts = p.stem.split('__', 2)
        if len(parts) != 3:
            continue
        _, raga, title = parts
        rec = {
            'stem': p.stem,
            'raga_dir': raga,
            'title_stem': title,
            'audio_path': None,
            'audio_size': None,
            'audio_md5': None,
            'archive_identifier': None,
            'ident_source': None,
            'ident_candidates': [],
            'artist': None,
        }
        mid = manifest_ident.get((nfc(raga), nfc(title)))
        audio = local_audio_for(raga, title)
        if audio is not None:
            rec['audio_path'] = str(audio.relative_to(ROOT))
            rec['audio_size'] = audio.stat().st_size
            cands = {i for i, _ in by_size.get(rec['audio_size'], ())}
            if len(cands) > 1:
                digest = md5(audio)
                rec['audio_md5'] = digest
                tight = {i for i, _ in by_md5.get(digest, ())}
                if tight:
                    cands = tight
            rec['ident_candidates'] = sorted(cands)
            if mid and mid.lower() in {c.lower() for c in cands}:
                agree += 1
            elif mid and cands:
                disagree += 1
            if mid:
                rec['archive_identifier'] = mid
                rec['ident_source'] = 'manifest'
            elif len(cands) == 1:
                rec['archive_identifier'] = next(iter(cands))
                rec['ident_source'] = 'size_md5_join'
        elif mid:
            rec['archive_identifier'] = mid
            rec['ident_source'] = 'manifest_no_audio'
        if rec['archive_identifier']:
            rec['artist'] = artist_of.get(rec['archive_identifier'].lower())
        records.append(rec)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'provenance.json').write_text(
        json.dumps(records, ensure_ascii=False, indent=1))

    resolved = sum(1 for r in records if r['archive_identifier'])
    ambiguous = sum(1 for r in records
                    if not r['archive_identifier'] and len(r['ident_candidates']) > 1)
    with_artist = sum(1 for r in records if r['artist'])
    idents = {r['archive_identifier'] for r in records if r['archive_identifier']}
    print(f'{len(records)} melodia tracks')
    print(f'  archive_identifier resolved : {resolved} '
          f'({resolved / len(records):.1%})')
    print(f'    from download_manifest    : '
          f"{sum(1 for r in records if r['ident_source'] and r['ident_source'].startswith('manifest'))}")
    print(f'    from size/md5 join        : '
          f"{sum(1 for r in records if r['ident_source'] == 'size_md5_join')}")
    print(f'  unresolved, ambiguous size  : {ambiguous}')
    print(f'  distinct archive items      : {len(idents)}')
    print(f'  artist recovered            : {with_artist} '
          f'({with_artist / len(records):.1%})')
    print(f'  size-join cross-check vs manifest: {agree} agree, {disagree} disagree')


if __name__ == '__main__':
    main()
