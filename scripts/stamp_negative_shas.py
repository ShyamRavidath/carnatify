#!/usr/bin/env python3
"""Bind the labeled audio to the inference audio, without re-cutting anything.

`validate_negatives()` matched windows to results by filename. Correct
filenames holding swapped, truncated or regenerated audio validated cleanly —
so a re-cut that silently moved an anchor would have been invisible, and the
labels would have described audio the pipeline never heard. That is the exact
class of defect that killed the first negative arm
(`CODEX_NEGATIVE_ARM_REVIEW.md` §4); it must not be able to recur unnoticed.

It hashes the window wavs of an arm and stamps `audio_sha256` into each window
record of that arm's sidecar. **It never writes audio** — the sidecar is the
only file it touches, and re-cutting the negative arm would invalidate the 69
labels already collected.

The scorer re-verifies these hashes at read time. `--cache-v2` is itself keyed
by `audio_sha256` (`identify_clip.identify_v2`), so the label binding and the
transcript binding agree by construction rather than by convention.

Extended 2026-07-29 to the **recall** arm (`WORKHORSE_PROBE_LAUNCH_BRIEF.md`
L2). The recall arm has no labels to bind, but the second half of the defect
applies unchanged: a window silently re-cut from a different anchor keeps its
filename, so it keeps its place in the sidecar while the cache serves the
transcript of the audio it replaced. `--arm anchored` gives it the same
binding, and `duration_probe_score.validate()` enforces it exactly as §6b does
for the negatives.

Run:
  venv_train/bin/python scripts/stamp_negative_shas.py --dry-run
  venv_train/bin/python scripts/stamp_negative_shas.py
  venv_train/bin/python scripts/stamp_negative_shas.py --arm anchored
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identify_clip import audio_sha256  # noqa: E402

OUT_ROOT = ROOT / 'data' / 'duration_probe'
WINDOW_DIR = OUT_ROOT / 'negatives'
SIDECAR = OUT_ROOT / 'truth_negatives.json'

# arm -> (window directory, sidecar). `negatives` stays the default so the
# existing command in the handoff keeps working unchanged.
ARMS = {'negatives': (WINDOW_DIR, SIDECAR),
        'anchored': (OUT_ROOT / 'anchored', OUT_ROOT / 'truth_anchored.json'),
        'prefix': (OUT_ROOT / 'prefix', OUT_ROOT / 'truth_prefix.json')}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=sorted(ARMS), default='negatives',
                    help='which arm to bind (default: the negative arm)')
    ap.add_argument('--sidecar', help='override the arm default')
    ap.add_argument('--audio-dir', help='override the arm default')
    ap.add_argument('--dry-run', action='store_true',
                    help='report what would change; write nothing')
    args = ap.parse_args()

    arm_dir, arm_sidecar = ARMS[args.arm]
    sidecar = Path(args.sidecar) if args.sidecar else arm_sidecar
    audio_dir = Path(args.audio_dir) if args.audio_dir else arm_dir
    if not sidecar.exists():
        sys.exit(f'{sidecar} does not exist — cut the {args.arm} arm first.')
    print(f'arm {args.arm}: {audio_dir} -> {sidecar}')
    side = json.loads(sidecar.read_text())
    windows = side['windows']

    missing, stamped, changed, unchanged = [], 0, [], 0
    for stem, meta in sorted(windows.items()):
        wav = audio_dir / f'{stem}.wav'
        if not wav.exists():
            missing.append(stem)
            continue
        sha = audio_sha256(wav)
        prev = meta.get('audio_sha256')
        if prev is None:
            meta['audio_sha256'] = sha
            stamped += 1
        elif prev != sha:
            # Not something to paper over: the file on disk is not the file
            # that was labeled. Report every one and write nothing.
            changed.append((stem, prev[:12], sha[:12]))
        else:
            unchanged += 1

    print(f'windows in sidecar : {len(windows)}')
    print(f'newly stamped      : {stamped}')
    print(f'already correct    : {unchanged}')
    if missing:
        print(f'MISSING audio      : {len(missing)} (e.g. {missing[:5]})')
    if changed:
        print(f'\n!! {len(changed)} windows changed on disk since they were '
              f'stamped:')
        for stem, was, now in changed[:10]:
            print(f'   {stem}: {was}... -> {now}...')
        sys.exit('Refusing to write. The labeled audio and the audio on disk '
                 'are different files; re-labeling, not re-stamping, is the '
                 'fix.')
    if missing:
        sys.exit(f'Refusing to write: {len(missing)} windows have no audio.')

    if args.dry_run:
        print('\ndry run — nothing written')
        return
    if not stamped:
        print('\nnothing to do')
        return
    sidecar.write_text(json.dumps(side, ensure_ascii=False, indent=1))
    print(f'\nstamped {stamped} hashes into {sidecar}')


if __name__ == '__main__':
    main()
