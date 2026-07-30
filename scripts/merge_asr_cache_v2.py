#!/usr/bin/env python3
"""Merge a v2 ASR cache built elsewhere (Colab) into the local one.

The probe's transcripts are produced on a GPU box and come back as a whole
cache file. Overwriting `data/asr_cache_v2.json` with it would throw away the
~/sung_tests entries the scoreboard depends on, so this merges instead — and
refuses on any key that exists in both with different content, because a key
that means two things is exactly what the `sha256(audio)[:24] + ':' +
config_id` scheme exists to make impossible.

Keys are `audio_sha256[:24]:config_id`, so a collision between the two files is
either the same audio under the same config (identical, safe to skip) or a
genuine conflict worth stopping for.

Run:
  venv_train/bin/python scripts/merge_asr_cache_v2.py <incoming.json> --dry-run
  venv_train/bin/python scripts/merge_asr_cache_v2.py <incoming.json>
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import identify_clip as ic  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('incoming', help='cache file from the GPU run')
    ap.add_argument('--into', default=str(ic.CACHE2))
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    inc = json.loads(Path(args.incoming).read_text())
    dest = Path(args.into)
    cur = json.loads(dest.read_text()) if dest.exists() else {'entries': {}}
    cur.setdefault('entries', {})

    new, same, conflict = {}, 0, []
    for key, entry in inc.get('entries', {}).items():
        if key not in cur['entries']:
            new[key] = entry
        elif cur['entries'][key] == entry:
            same += 1
        else:
            conflict.append(key)

    print(f'incoming entries : {len(inc.get("entries", {}))}')
    print(f'already present  : {same} (byte-identical)')
    print(f'new              : {len(new)}')
    if conflict:
        print(f'\n!! {len(conflict)} keys differ between the two caches:')
        for k in conflict[:10]:
            print(f'   {k}')
        sys.exit('Refusing to merge. One key must mean one transcript set; '
                 'work out which file is wrong before merging either.')
    if args.dry_run:
        print('\ndry run — nothing written')
        return
    if not new:
        print('\nnothing to do')
        return
    if dest.exists():
        backup = dest.with_suffix('.json.bak')
        shutil.copy(dest, backup)
        print(f'backed up {dest.name} -> {backup.name}')
    cur['entries'].update(new)
    ic._atomic_write_json(dest, cur)
    print(f'merged {len(new)} entries into {dest} '
          f'({len(cur["entries"])} total)')


if __name__ == '__main__':
    main()
