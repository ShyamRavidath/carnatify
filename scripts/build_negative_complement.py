#!/usr/bin/env python3
"""Second labeling sweep — the 150 seconds sheet 1 never played.

`build_negative_arm.py` cuts each item's `_scan.wav` as 10s every 20s of the
scored 300s window: 0-10, 20-30, ..., 280-290. That is a 50% duty cycle, so
**fifteen 10-second stretches of every scored window were never heard**,
including 290-300. `CODEX_NEGATIVE_ARM_REVIEW_R2.md` P0-1 is correct that this
does not support the claim the label is being asked to carry. "Maximum unheard
gap is 10s" is true; "the ear confirmed this window carries no sung words" is
not. One pallavi phrase inside an unheard gap is enough to make a lyrics
matcher answer, which is precisely the event the negative arm exists to bound.

This script cuts the complement — 10-20, 30-40, ..., 290-300 — for the items
currently sitting in the gating stratum, and asks the same binary question
about it. An item gates only if it comes back `no-sahitya` on **both** sweeps
(`parse_negative_labels.py`).

Two properties this deliberately preserves:

* **The audio is re-used, never re-cut.** Snippets come from the existing
  `data/duration_probe/negatives/<item>d300.wav`, so the ear still hears
  literally the samples the pipeline will be given. Re-cutting from the source
  mp3 would re-draw anchors and silently invalidate sheet 1.
* **`build_negative_arm.py` is not re-run.** It re-draws every anchor,
  re-assigns every `negNNN` id and re-shuffles the sheet, which would destroy
  the 69 labels already collected.

Coverage is asserted, not eyeballed: sweep 1 ∪ sweep 2 must tile [0, 300)
exactly, with no gap and no overlap. The script refuses to write anything if
that fails.

Run:
  venv_train/bin/python scripts/build_negative_complement.py --dry-run
  venv_train/bin/python scripts/build_negative_complement.py
"""
import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from build_negative_arm import SCAN_EVERY, SCAN_LEN  # noqa: E402  (one defn)
from parse_negative_labels import collapse  # noqa: E402

OUT_ROOT = ROOT / 'data' / 'duration_probe'
WINDOW_DIR = OUT_ROOT / 'negatives'
ARM = OUT_ROOT / 'negative_arm'
LABELS = ARM / 'negative_labels.json'
COMP_DIR = ARM / 'complement'
SIDECAR = OUT_ROOT / 'truth_negatives.json'

GATING = 'no-sahitya'
# Sheet 1 starts at 0; this sheet starts half a period later, which is exactly
# the material sheet 1 skipped.
SCAN_OFFSET = SCAN_LEN
# A fresh shuffle so sheet-1 position carries no information into sheet 2 —
# she has already heard these items once and row order should not let her
# pattern-match her own previous answers.
SEED = 20260729


def sweep1_verdict(rec: dict) -> str:
    """What sheet 1 alone said about this item.

    Selection keys off sweep 1, never off the final `stratum`: once the
    two-sweep rule is in force the parser marks these items `unknown` until
    sheet 2 comes back, so selecting on `stratum` would make this script erase
    its own input on a re-run. `labels_given` is the pre-2026-07-29 field name.
    """
    given = rec.get('labels_given_1')
    if given is None:
        given = rec.get('labels_given', [])
    return collapse(set(given))


def sweep_starts(length: int, offset: int = 0) -> list[int]:
    """Snippet start offsets for one sweep of a `length`-second window."""
    return list(range(offset, max(1, length - SCAN_LEN + 1), SCAN_EVERY))


def intervals(starts: list[int], length: int) -> list[tuple[int, int]]:
    return [(s, min(s + SCAN_LEN, length)) for s in starts]


def assert_tiles(length: int) -> tuple[list[int], list[int]]:
    """Sweep 1 ∪ sweep 2 must be exactly [0, length): no gap, no overlap.

    This is the whole point of the second sheet, so it is a hard precondition
    rather than a printed reassurance.
    """
    s1, s2 = sweep_starts(length), sweep_starts(length, SCAN_OFFSET)
    merged = sorted(intervals(s1, length) + intervals(s2, length))
    cursor = 0
    for start, end in merged:
        if start != cursor:
            raise AssertionError(
                f'sweep union is not contiguous at {cursor}s: next snippet '
                f'starts at {start}s ({"gap" if start > cursor else "overlap"})')
        cursor = end
    if cursor != length:
        raise AssertionError(f'sweep union ends at {cursor}s, not {length}s')
    return s1, s2


def scan_complement(window: Path, dest: Path, length: int,
                    starts: list[int]) -> int:
    """Concatenate the complement snippets of `window` into one file."""
    parts = ''.join(
        f'[0:a]atrim=start={s}:end={min(s + SCAN_LEN, length)},'
        f'asetpts=PTS-STARTPTS[a{i}];' for i, s in enumerate(starts))
    concat = ''.join(f'[a{i}]' for i in range(len(starts)))
    r = subprocess.run(
        ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(window),
         '-filter_complex',
         f'{parts}{concat}concat=n={len(starts)}:v=0:a=1[out]',
         '-map', '[out]', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le',
         str(dest)], capture_output=True, text=True)
    if r.returncode != 0:
        print(f'  scan failed on {window.name}: {r.stderr.strip()[:160]}',
              file=sys.stderr)
        return 0
    return len(starts)


def write_sheet(items: list[str], mapping: dict, length: int,
                starts: list[int]) -> None:
    n = len(items)
    heard = len(starts) * SCAN_LEN
    lines = [
        '# Negative-arm labeling sheet 2 — the half you have not heard',
        '',
        f'**{n} rows, one label each. One file to listen to per row.**',
        '',
        '## Why there is a second sheet',
        '',
        f'Sheet 1 played {SCAN_LEN}s every {SCAN_EVERY}s of each {length}s '
        f'window: 0-10s, 20-30s, and so on. That is half the window. The other '
        f'half — {len(starts)} stretches of {SCAN_LEN}s each, including the '
        f'final {SCAN_LEN}s — was never played to anyone.',
        '',
        'For most questions that would be fine. For this one it is not: a '
        'single sung line hiding in an unheard gap is enough to make the '
        'matcher answer, and this arm exists precisely to count how often it '
        'answers when it should not. So the rows you already called '
        '`no-sahitya` need their other half checked before they can be used.',
        '',
        f'Each `_scan2.wav` below is exactly that missing half — {heard}s, the '
        f'snippets sheet 1 skipped, in order. Together the two sheets cover '
        f'every second of the window with nothing heard twice.',
        '',
        '## The question is unchanged',
        '',
        '**Does anyone sing words?** Not which composition, not whether we '
        'have it — those are lookups.',
        '',
        '**Stop as soon as you hear singing.** Write `sahitya` and move on; '
        'you do not have to finish the sweep. Most rows should end in seconds.',
        '',
        '**You can stop anywhere in the sheet.** Blank rows are unknown and '
        'excluded, and the order is freshly shuffled, so a partial sheet is a '
        'valid smaller experiment rather than a broken one.',
        '',
        '| label | means |',
        '|---|---|',
        '| `no-sahitya` | nobody sings words anywhere in the sweep: alapana, '
        'tanam, thani, tuning, applause, speech, instrumental, or bare '
        'solfège with no composition line in it |',
        '| `sahitya` | somebody sings words somewhere in it, even one line, '
        'even briefly — **including swarakalpana**, where the solfège '
        'alternates with the sahitya line of the composition |',
        '| `unusable` | you cannot tell — too noisy, too broken, genuinely '
        'ambiguous |',
        '',
        '`unusable` and blank both count as **unknown** and are excluded; '
        'neither is treated as no-sahitya. Guessing costs us more than '
        'abstaining does.',
        '',
        'The swaram line above is a **correction** (2026-07-29): an earlier '
        'version of this sheet filed bare `swaram` under `no-sahitya` with no '
        'qualification, which is wrong for swarakalpana, because the '
        'composition line comes back between the solfège phrases. Judge what '
        'is sung, not what the section is called.',
        '',
        '**An item is used only if BOTH sheets say `no-sahitya`.** A `sahitya` '
        'here overrides sheet 1 — it means the window does contain singing, '
        'and sheet 1 simply did not play the part that held it. Expect this '
        'sheet to shrink the usable set; that is the point of running it.',
        '',
        f'If a row is borderline, the full {length}s window is on disk as '
        '`../../negatives/<id>d300.wav` — but only open it if the sweep is '
        'genuinely ambiguous.',
        '',
        'Ids are blind and the order is reshuffled with a new seed, so the '
        'row order tells you nothing about your sheet-1 answers '
        '(`METRIC_CONTRACT.md:30`).',
        '',
        '| # | listen | label | notes |',
        '|---:|---|---|---|',
    ]
    lines += [f'| {i} | `{item}_scan2.wav` |  |  |'
              for i, item in enumerate(items, 1)]
    (COMP_DIR / 'LABELING_SHEET_2.md').write_text('\n'.join(lines) + '\n')
    (COMP_DIR / '_mapping2.json').write_text(
        json.dumps(mapping, ensure_ascii=False, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--dry-run', action='store_true',
                    help='report what would be cut; write nothing')
    args = ap.parse_args()

    if not LABELS.exists():
        sys.exit(f'{LABELS} missing — run scripts/parse_negative_labels.py')
    labels = json.loads(LABELS.read_text())
    side = json.loads(SIDECAR.read_text())
    length = max(side['durations'])

    s1, s2 = assert_tiles(length)          # raises before anything is written
    print(f'sweep 1: {len(s1)} snippets starting {s1[:3]}...{s1[-1]}')
    print(f'sweep 2: {len(s2)} snippets starting {s2[:3]}...{s2[-1]}')
    print(f'union tiles [0, {length}) exactly — no gap, no overlap')

    gating = sorted(i for i, d in labels.items() if sweep1_verdict(d) == GATING)
    print(f'\nitems sheet 1 called {GATING}, needing a second sweep: '
          f'{len(gating)}')
    print(f'  listening: {len(gating)} x {len(s2) * SCAN_LEN}s = '
          f'{len(gating) * len(s2) * SCAN_LEN / 60:.0f} min worst case')

    missing = [i for i in gating
               if not (WINDOW_DIR / f'{i}d{length:03d}.wav').exists()]
    if missing:
        sys.exit(f'{len(missing)} windows missing from {WINDOW_DIR}: '
                 f'{missing[:5]} — do NOT re-run build_negative_arm.py to fix '
                 f'this; it re-draws every anchor and destroys the sheet-1 '
                 f'labels.')

    if args.dry_run:
        print('\ndry run — nothing written')
        return

    COMP_DIR.mkdir(parents=True, exist_ok=True)
    mapping, sheet = {}, []
    for idx, item in enumerate(gating, 1):
        src = WINDOW_DIR / f'{item}d{length:03d}.wav'
        n_snip = scan_complement(src, COMP_DIR / f'{item}_scan2.wav', length,
                                 s2)
        if not n_snip:
            continue
        mapping[item] = {**labels[item], 'sweep': 2,
                         'scan2_snippets': n_snip,
                         'scan2_starts': s2,
                         'sweep1_stratum': labels[item]['stratum']}
        sheet.append(item)
        if idx % 10 == 0:
            print(f'  {idx}/{len(gating)} cut')

    random.Random(args.seed).shuffle(sheet)
    write_sheet(sheet, mapping, length, s2)

    print(f'\nwrote {len(sheet)} scans to {COMP_DIR}')
    print(f"sheet {COMP_DIR / 'LABELING_SHEET_2.md'} ({len(sheet)} rows)")
    print('Gating now requires no-sahitya on BOTH sweeps — run '
          'scripts/parse_negative_labels.py when the sheet comes back.')


if __name__ == '__main__':
    main()
