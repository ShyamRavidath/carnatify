#!/usr/bin/env python3
"""Freeze the 11 long-form concert recordings — inventory only, no prediction.

Writes `data/long_concerts/FROZEN_CONCERTS.json`: per file sha256, byte length,
ffprobe duration/codec/rate/channels, and the sha256 of the copy still sitting in
`~/Downloads` so the copy can be shown to be byte-identical to the source.

This is the same discipline `data/raga_wild/FROZEN_CLIPS.json` used: the record
is written and committed **before any prediction exists**, so a later score
cannot be quietly computed on a different or re-encoded file. Re-running this
script after the freeze is committed re-verifies rather than rewrites — pass
`--verify` and it exits non-zero on any mismatch without touching the file.

Usage:
    venv_train/bin/python scripts/long_concert_freeze.py            # write
    venv_train/bin/python scripts/long_concert_freeze.py --verify   # re-check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / 'data' / 'long_concerts' / 'audio'
FROZEN = ROOT / 'data' / 'long_concerts' / 'FROZEN_CONCERTS.json'
DOWNLOADS = Path.home() / 'Downloads'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def probe(path: Path) -> dict:
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-print_format', 'json',
         '-show_format', '-show_streams', str(path)],
        capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    a = next(s for s in d['streams'] if s['codec_type'] == 'audio')
    return {
        'duration_s': round(float(d['format']['duration']), 3),
        'codec': a['codec_name'],
        'sample_rate_hz': int(a['sample_rate']),
        'channels': int(a['channels']),
        'bit_rate_bps': int(d['format'].get('bit_rate', 0)),
    }


def build() -> dict:
    rows = []
    for p in sorted(AUDIO.glob('long_concert_*.mp3'),
                    key=lambda q: int(q.stem.split('_')[-1])):
        row = {'file': p.name, 'bytes': p.stat().st_size, 'sha256': sha256(p)}
        row.update(probe(p))
        src = DOWNLOADS / p.name
        row['source_copy'] = str(src) if src.exists() else None
        row['source_sha256'] = sha256(src) if src.exists() else None
        row['source_identical'] = (row['source_sha256'] == row['sha256']
                                   if src.exists() else None)
        rows.append(row)
    total_s = sum(r['duration_s'] for r in rows)
    return {
        'frozen_utc': None,          # filled at write time only
        'n_concerts': len(rows),
        'total_duration_s': round(total_s, 3),
        'total_duration_h': round(total_s / 3600.0, 3),
        'total_bytes': sum(r['bytes'] for r in rows),
        'provenance': ("Deepti's own recordings of live Carnatic concerts, "
                       "converted to mp3 2026-08-13 by scripts/convert_long_concerts.sh "
                       "(44.1 kHz stereo 192 kbps). Sources are .mp4/.MOV in ~/Downloads."),
        'concerts': rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()

    built = build()
    for r in built['concerts']:
        print(f"{r['file']:22s} {r['duration_s']/60:7.1f} min  {r['bytes']/1e6:7.1f} MB  "
              f"{r['codec']} {r['sample_rate_hz']} {r['channels']}ch  "
              f"src_identical={r['source_identical']}  {r['sha256'][:16]}")
    print(f"\n{built['n_concerts']} concerts, {built['total_duration_h']:.2f} h, "
          f"{built['total_bytes']/1e6:.0f} MB")

    if args.verify:
        if not FROZEN.exists():
            sys.exit('FROZEN_CONCERTS.json does not exist — nothing to verify')
        old = json.loads(FROZEN.read_text())
        bad = []
        oldmap = {r['file']: r for r in old['concerts']}
        if set(oldmap) != {r['file'] for r in built['concerts']}:
            bad.append(f"file set differs: frozen={sorted(oldmap)} "
                       f"disk={sorted(r['file'] for r in built['concerts'])}")
        for r in built['concerts']:
            o = oldmap.get(r['file'])
            if o is None:
                continue
            for k in ('sha256', 'bytes', 'duration_s'):
                if o[k] != r[k]:
                    bad.append(f"{r['file']}: {k} frozen={o[k]} disk={r[k]}")
        if bad:
            print('\nGATE FAIL')
            for b in bad:
                print('  ' + b)
            sys.exit(1)
        print('\nGATE PASS — every frozen sha256, byte length and duration matches disk')
        return

    if FROZEN.exists():
        sys.exit(f'{FROZEN} already exists — refusing to overwrite a freeze. '
                 f'Use --verify.')
    from datetime import datetime, timezone
    built['frozen_utc'] = datetime.now(timezone.utc).isoformat()
    FROZEN.write_text(json.dumps(built, ensure_ascii=False, indent=2) + '\n')
    print(f'\nwrote {FROZEN}')


if __name__ == '__main__':
    main()
