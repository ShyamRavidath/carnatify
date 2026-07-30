#!/usr/bin/env python3
"""Package the duration probe for the Colab GPU run.

Local `large-v3-turbo` throughput is 30s window -> 256s wall and 300s window ->
1500s wall at the 4-pass mix config, so the 116 whisper-hours this probe needs
cannot be spent on the laptop. This script builds the artifacts Deepti uploads
to Drive; `colab_duration_probe.py` consumes them.

Three zips, deliberately separate:

* `probe_code.zip`   — ~9 MB: `identify_clip.py`, the cache builder, and the
  registry/lyrics files `load_targets()` reads. No models, no audio.
* `probe_anchored.zip` / `probe_negatives.zip` — the window WAVs and their
  sidecars, ~1.2 GB and ~0.7 GB. Split so a dropped upload costs one arm and
  not both.

**The WAVs are shipped as bytes and not re-cut on Colab, and that is not
laziness.** `--cache-v2` is keyed by `audio_sha256` of the file, and the
sidecars carry those hashes (`scripts/stamp_negative_shas.py`), so a window
re-cut by a different ffmpeg build would hash differently, miss the cache, and
break the binding between the audio the ear labeled and the audio the pipeline
heard — the defect class that killed the v1 negative arm. WAVs are also very
nearly incompressible (measured: deflate saves ~4%), so the zips are stored,
not compressed: it is the same upload either way and packing is much faster.

Every window is re-hashed here and checked against its sidecar before anything
is written. A mismatch aborts: shipping audio the sidecar does not describe is
the one failure this whole binding exists to prevent.

Run:
  venv_train/bin/python scripts/build_probe_colab_bundle.py
  venv_train/bin/python scripts/build_probe_colab_bundle.py --out ~/probe_bundle
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identify_clip import audio_sha256  # noqa: E402

PROBE = ROOT / 'data' / 'duration_probe'
ARMS = {'anchored': (PROBE / 'anchored', PROBE / 'truth_anchored.json'),
        'negatives': (PROBE / 'negatives', PROBE / 'truth_negatives.json')}

# Everything `identify_clip.py --json --no-raga --cache-v2` touches, and
# nothing else. `models/` is not needed: the registry exists, so the
# `qmax_catalog_meta.json` fallback at identify_clip.py:300 never runs, and
# --no-raga skips `raga_clip_rf.pkl`.
CODE_FILES = [
    'identify_clip.py',
    'scripts/build_asr_cache_v2.py',
    'scripts/duration_probe_score.py',
    'data/composition_registry.json',
    'data/karnatik_lyrics.json',
    'data/karnatik_link_overrides.json',
    'data/lyrics.db',
]


def verify_arm(name: str) -> dict:
    """Re-hash every window of one arm against its sidecar. -> manifest."""
    audio_dir, sidecar_path = ARMS[name]
    if not sidecar_path.exists():
        sys.exit(f'{sidecar_path} does not exist — cut the {name} arm first.')
    side = json.loads(sidecar_path.read_text())
    windows = side['windows']
    unstamped = [s for s, m in windows.items() if not m.get('audio_sha256')]
    if unstamped:
        sys.exit(f'{len(unstamped)} {name} windows carry no audio_sha256 — run '
                 f'scripts/stamp_negative_shas.py --arm {name} first '
                 f'(e.g. {unstamped[:3]}).')
    absent, bad, total = [], [], 0
    for stem, meta in sorted(windows.items()):
        wav = audio_dir / f'{stem}.wav'
        if not wav.exists():
            absent.append(stem)
            continue
        if audio_sha256(wav) != meta['audio_sha256']:
            bad.append(stem)
        total += wav.stat().st_size
    if absent:
        sys.exit(f'{len(absent)} {name} windows have no audio on disk '
                 f'(e.g. {absent[:3]}).')
    if bad:
        sys.exit(f'{len(bad)} {name} windows do not match their stamped '
                 f'audio_sha256 (e.g. {bad[:3]}). The audio on disk is not the '
                 f'audio the sidecar describes; do not ship it.')
    print(f'  {name:<10} {len(windows):>4} windows verified, '
          f'{total / 1e9:.2f} GB')
    return {'windows': len(windows), 'bytes': total,
            'expected_windows': side.get('expected_windows'),
            'durations': side.get('durations'),
            'sha256': {s: m['audio_sha256'] for s, m in windows.items()}}


def write_zip(path: Path, members: list[tuple[Path, str]]) -> None:
    """Stored (uncompressed) — WAV deflates by ~4% and costs minutes."""
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
        for src, arc in members:
            z.write(src, arc)
    print(f'  wrote {path.name}  {path.stat().st_size / 1e9:.2f} GB')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='~/carnatify_probe_bundle',
                    help='where the zips are written (NOT inside the repo)')
    ap.add_argument('--verify-only', action='store_true',
                    help='re-hash both arms and stop; writes nothing')
    args = ap.parse_args()

    print('verifying staged audio against the sidecars ...')
    manifest = {name: verify_arm(name) for name in ARMS}
    if args.verify_only:
        print('\nverify only — nothing written')
        return

    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    print('\npacking ...')
    missing = [f for f in CODE_FILES if not (ROOT / f).exists()]
    if missing:
        sys.exit(f'code bundle is missing {missing}')
    write_zip(out / 'probe_code.zip',
              [(ROOT / f, f) for f in CODE_FILES])

    for name, (audio_dir, sidecar) in ARMS.items():
        members = [(sidecar, f'data/duration_probe/{sidecar.name}')]
        members += [(p, f'data/duration_probe/{name}/{p.name}')
                    for p in sorted(audio_dir.glob('*.wav'))]
        write_zip(out / f'probe_{name}.zip', members)

    (out / 'BUNDLE_MANIFEST.json').write_text(json.dumps(
        {'arms': {k: {kk: vv for kk, vv in v.items() if kk != 'sha256'}
                  for k, v in manifest.items()},
         'sha256': {k: v['sha256'] for k, v in manifest.items()},
         'code_files': CODE_FILES}, indent=1))
    print(f"  wrote BUNDLE_MANIFEST.json")

    total = sum(v['bytes'] for v in manifest.values())
    print(f'\nupload these to Drive at MyDrive/carnatify/duration_probe/:')
    for p in sorted(out.iterdir()):
        print(f'  {p.name:<24} {p.stat().st_size / 1e6:>8.0f} MB')
    print(f'\n({total / 1e9:.2f} GB of audio. Then run '
          f'colab_duration_probe.py in Colab on a GPU runtime.)')


if __name__ == '__main__':
    main()
