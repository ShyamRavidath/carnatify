"""Device calibration for the duration probe (pre-registration §5b / §5b.1).

Re-transcribes a small set of already-cached probe windows on THIS machine
against a TEMPORARY cache path, then compares the four `source: 'mix'`
hypotheses verbatim on `raw` against what the GPU run produced. The mix passes
do not involve Demucs, so they isolate device-dependence of the transcriber
from device-dependence of the separator; the three `source: 'stem'` hypotheses
are reported alongside as information only, because a laptop re-run takes the
unpatched CPU-Demucs path and would differ for that reason rather than for the
reason being tested.

The production cache `data/asr_cache_v2.json` is never written: the registered
builder is driven with `identify_clip.CACHE2` and `_BACKEND_CACHES['whisper']`
patched to the temporary path, and the production file's sha256 is asserted
unchanged on the way out.

    # step 1 (slow, unattended)
    venv_train/bin/python scripts/duration_probe_device_cal.py transcribe
    # step 2 (instant)
    venv_train/bin/python scripts/duration_probe_device_cal.py compare

Windows default to the §5b.1 selection: the shortest windows of the two
straddler candidates, so that no clean title's data is consulted whatever the
device map turns out to be.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import identify_clip as ic  # noqa: E402

# §5b.1(2): drawn from probe0016 and probe0051, shortest windows available.
DEFAULT_WINDOWS = ('probe0016d030a.wav',
                   'probe0051d030a.wav',
                   'probe0016d060a.wav')
DEVICE_CAL_N = 3

ARM = ROOT / 'data' / 'duration_probe' / 'anchored'
CAL_DIR = ROOT / 'data' / 'duration_probe' / 'device_cal'
CAL_CACHE = CAL_DIR / 'asr_cache_v2_laptop.json'
STAGE = CAL_DIR / 'stage'
REPORT = ROOT / 'data' / 'duration_probe' / 'DEVICE_CALIBRATION.md'


def _prod_sha() -> str:
    import hashlib
    return hashlib.sha256(ic.CACHE2_REAL.read_bytes()).hexdigest()


# keep a handle on the real path before anything is patched
ic.CACHE2_REAL = ic.CACHE2


def _entry(cache: dict, name: str) -> dict:
    hits = [v for v in cache['entries'].values() if v.get('file') == name]
    if len(hits) != 1:
        sys.exit(f'{name}: expected exactly 1 cache entry, found {len(hits)}')
    return hits[0]


def _by_source(entry: dict, source: str) -> list[dict]:
    """Hypotheses of one source, in stored order. `hypotheses` is a real JSON
    list of dicts (not a repr string), so this is a structural read."""
    hyps = entry['hypotheses']
    if not isinstance(hyps, list):
        sys.exit(f'unexpected hypotheses type {type(hyps).__name__}')
    return [h for h in hyps if h.get('source') == source]


def transcribe(windows: list[str]) -> None:
    for name in windows:
        if not (ARM / name).exists():
            sys.exit(f'missing window {name}')
    prod_before = _prod_sha()

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    for name in windows:
        (STAGE / name).symlink_to(ARM / name)

    # drive the REGISTERED builder against a temporary cache path
    ic.CACHE2 = CAL_CACHE
    ic._BACKEND_CACHES['whisper'] = (CAL_CACHE, ic.ASR_CONFIG_V2)
    sys.path.insert(0, str(ROOT / 'scripts'))
    import build_asr_cache_v2 as builder
    builder.build(STAGE)

    if _prod_sha() != prod_before:
        sys.exit('FATAL: data/asr_cache_v2.json changed during calibration')
    print(f'production cache unchanged (sha256 {prod_before[:16]}…)')
    print(f'laptop cache written to {CAL_CACHE}')


def compare(windows: list[str]) -> int:
    gpu = json.loads(ic.CACHE2_REAL.read_text())
    if not CAL_CACHE.exists():
        sys.exit(f'{CAL_CACHE} does not exist — run `transcribe` first')
    cpu = json.loads(CAL_CACHE.read_text())

    if gpu['config'] != cpu['config']:
        sys.exit('cache configs differ — the comparison is not like-for-like')

    lines: list[str] = []
    mix_verdicts: list[bool] = []
    stem_verdicts: list[bool] = []

    for name in windows:
        g, c = _entry(gpu, name), _entry(cpu, name)
        if g['audio_sha256'] != c['audio_sha256']:
            sys.exit(f'{name}: audio sha differs — not the same bytes')
        if g['config_id'] != c['config_id']:
            sys.exit(f'{name}: config_id differs — cache key semantics changed')
        lines.append(f'\n### `{name}`\n')
        lines.append(f'- `audio_sha256` `{g["audio_sha256"][:24]}` — identical '
                     f'on both sides\n')
        for source, bucket in (('mix', mix_verdicts), ('stem', stem_verdicts)):
            gh, ch = _by_source(g, source), _by_source(c, source)
            lines.append(f'\n**`source: {source}`** — GPU {len(gh)} passes, '
                         f'laptop {len(ch)} passes\n\n')
            if len(gh) != len(ch):
                bucket.append(False)
                lines.append(f'PASS COUNT DIFFERS ({len(gh)} vs {len(ch)}) — '
                             f'treated as *differs*.\n')
                continue
            lines.append('| # | lang | status | verdict | GPU `raw` | '
                         'laptop `raw` |\n|---|---|---|---|---|---|\n')
            for i, (a, b) in enumerate(zip(gh, ch)):
                same = (a.get('raw') == b.get('raw')
                        and a.get('lang') == b.get('lang')
                        and a.get('status') == b.get('status'))
                bucket.append(same)
                lines.append(
                    f'| {i} | {a.get("lang")} | `{a.get("status")}` | '
                    f'{"identical" if same else "**DIFFERS**"} | '
                    f'{_cell(a.get("raw"))} | {_cell(b.get("raw"))} |\n')

    mix_ok = bool(mix_verdicts) and all(mix_verdicts)
    n_windows = len(windows)
    if n_windows != DEVICE_CAL_N:
        lines.append(f'\n**Note:** {n_windows} windows compared, '
                     f'DEVICE_CAL_N is {DEVICE_CAL_N}.\n')

    header = [
        '# Duration probe — device calibration\n\n',
        'Executed under `DURATION_PROBE_PREREGISTRATION.md` §5b / §5b.1. The\n',
        'branch this selects was frozen before the calibration ran.\n\n',
        f'- windows: {", ".join(f"`{w}`" for w in windows)} '
        f'(`DEVICE_CAL_N = {DEVICE_CAL_N}`)\n',
        '- drawn from `probe0016` and `probe0051`, the two straddler '
        'candidates, so no clean title\'s data is consulted\n',
        f'- GPU side: `data/asr_cache_v2.json` (the run under test)\n',
        f'- laptop side: `{CAL_CACHE.relative_to(ROOT)}`, produced by the '
        'registered `scripts/build_asr_cache_v2.py` against a temporary cache '
        'path\n',
        '- comparison is verbatim on `raw`, plus `lang` and `status`\n\n',
        '## Verdict\n\n',
        f'**mix passes: {"ALL IDENTICAL" if mix_ok else "DIFFER"}** '
        f'({sum(mix_verdicts)}/{len(mix_verdicts)} pass-comparisons identical)'
        '\n\n',
        f'stem passes (information only, do not decide the branch): '
        f'{sum(stem_verdicts)}/{len(stem_verdicts)} identical\n\n',
        '§5b branch selected: '
        + ('**device-invariant — score both arms as-is at the registered n**\n'
           if mix_ok else
           '**device-dependent — establish the map, exclude every straddler, '
           'score at reduced n** (§5b.1(3), and §5b.1(4) if no record '
           'establishes the map)\n'),
        '\n## Per-window comparison\n',
    ]
    REPORT.write_text(''.join(header + lines))
    print(''.join(header))
    print(f'written: {REPORT}')
    return 0 if mix_ok else 1


def _cell(s) -> str:
    if s is None:
        return '—'
    s = str(s).replace('|', '\\|').replace('\n', ' ⏎ ')
    return f'`{s}`' if s else '*(empty)*'


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=('transcribe', 'compare'))
    ap.add_argument('--windows', nargs='+', default=list(DEFAULT_WINDOWS))
    a = ap.parse_args()
    CAL_DIR.mkdir(parents=True, exist_ok=True)
    if a.mode == 'transcribe':
        transcribe(a.windows)
    else:
        sys.exit(compare(a.windows))


if __name__ == '__main__':
    main()
