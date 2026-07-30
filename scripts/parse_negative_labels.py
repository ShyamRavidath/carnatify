#!/usr/bin/env python3
"""Turn the filled-in labeling sheet into negative-arm strata.

Rewritten 2026-07-28. The previous parser was rejected on three counts
(`CODEX_NEGATIVE_ARM_REVIEW.md` §§2-4) and all three are structural, not
tuning:

1. **It inferred OOC from a failed filename lookup.** `title_from_filename`
   held strings like `4830 aswinsainarain`, so "no registry row" meant nothing,
   and at least 3 of the 12 nominal OOC items were in-catalog works. Here an
   item is OOC only if it appears in `data/duration_probe/verified_ooc.json`, a
   reviewed identity file. Otherwise it is `sung_unidentified` — real audio, a
   real negative-ish case, reported separately and never gating.
2. **It called items no-sahitya on partial or `unusable` evidence.** `certain`
   only meant each supplied token was unambiguous, so items with one label out
   of three, or with an `unusable` excerpt that could conceal singing, were
   retained. Here anything short of an unambiguous `no-sahitya` on the whole
   sweep is `unknown` and drops out.
3. **The labels described audio that was never scored.** Fixed upstream: the
   sweep is cut from the scored 300s window itself
   (`scripts/build_negative_arm.py`).

Amended 2026-07-29 after `CODEX_NEGATIVE_ARM_REVIEW_R2.md` P0-1: sheet 1's
sweep is a 50% duty cycle, so it left fifteen unheard 10s stretches per window
and could not support "no sung words anywhere in it". **Gating now requires
`no-sahitya` on both sweeps** — sheet 1 and the complementary
`LABELING_SHEET_2.md` from `scripts/build_negative_complement.py`, which
together tile the window exactly. Hearing singing once is conclusive, so
`sahitya` on *either* sheet settles the item; everything else short of a clean
double negative is `unknown`.

**If sheet 2 is missing entirely this script exits non-zero** rather than
reproducing the old single-sweep gating stratum. That is the chosen failure
mode of the two the brief allowed: a loud stop cannot be mistaken for a result,
whereas a silently-stamped run of 51 `unknown`s looks like a labeling problem
rather than a missing input. `--allow-single-sweep` is available for
inspection; it stamps `sweeps_applied: 1`, which the scorer's validity gate
rejects, so it still cannot print a safety conclusion.

Strata are stamped back into `truth_negatives.json` so the scorer has one
source of truth to validate against, rather than joining two files that can
disagree.

Run:
  venv_train/bin/python scripts/parse_negative_labels.py
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from duration_probe_titles import (candidates, registry_index,  # noqa: E402
                                   resolve_exact, resolve_relaxed)

OUT_ROOT = ROOT / 'data' / 'duration_probe'
ARM = OUT_ROOT / 'negative_arm'
SHEET = ARM / 'LABELING_SHEET.md'
MAPPING = ARM / '_mapping.json'
COMP = ARM / 'complement'
SHEET2 = COMP / 'LABELING_SHEET_2.md'
SIDECAR = OUT_ROOT / 'truth_negatives.json'
VERIFIED_OOC = OUT_ROOT / 'verified_ooc.json'
OUT = ARM / 'negative_labels.json'

# How many independent sweeps of the scored window must agree before an item is
# allowed into the gating stratum. Sheet 1 alone covers 50% of the window.
SWEEPS_REQUIRED = 2

VALID = {'no-sahitya', 'sahitya', 'unusable'}
# Accepted spellings of the v1 vocabulary, so a sheet filled in from muscle
# memory still parses instead of silently dropping rows.
SYNONYM = {'nosahitya': 'no-sahitya', 'no sahitya': 'no-sahitya',
           'sahityam': 'sahitya', 'lyrics': 'sahitya', 'singing': 'sahitya',
           'in-catalog': 'sahitya', 'ooc': 'sahitya', 'unclear': 'unusable'}

GATING = 'no-sahitya'
NON_GATING = ('sung_unidentified', 'ooc')


def parse_sheet(path: Path) -> tuple[dict, list]:
    """item -> set of labels given for it. Unrecognised tokens are reported.

    An item absent from the returned dict was never offered on this sheet; an
    item present with an empty set was offered and left blank. The two are
    different and the caller must keep them apart.
    """
    per_item, problems = {}, []
    for line in path.read_text().splitlines():
        cells = [c.strip().strip('`') for c in line.strip().split('|')]
        if len(cells) < 5:
            continue
        m = re.search(r'(neg\d+)', cells[2] or '')
        if not m:
            continue
        opts = set()
        for token in (t.strip().lower() for t in re.split(r'[,/]', cells[3])):
            if not token:
                continue
            token = SYNONYM.get(token, token)
            if token in VALID:
                opts.add(token)
            else:
                problems.append((m.group(1), token))
        per_item[m.group(1)] = opts
    return per_item, problems


def collapse(opts: set) -> str:
    """One sweep -> one verdict, with abstention as a first-class outcome.

    `no-sahitya` requires that to be the ONLY thing she wrote. A blank row, an
    `unusable`, or a `no-sahitya/sahitya` coin-toss all land in `unknown`: a
    false negative in the bluff denominator flatters the pipeline, which is the
    direction this project has repeatedly been wrong in.
    """
    if opts == {'no-sahitya'}:
        return 'no-sahitya'
    if opts == {'sahitya'}:
        return 'sahitya'
    return 'unknown'


def combine_sweeps(v1: str, v2: str | None) -> str:
    """Two sweep verdicts -> the item's audio verdict.

    The two sweeps tile the scored window exactly, so:

    * `sahitya` on either sweep is conclusive — singing heard is singing heard,
      and the other half cannot un-hear it;
    * `no-sahitya` requires BOTH sweeps to say so, because each alone leaves
      half the window unplayed;
    * anything else — a blank, an `unusable`, a coin-toss, or a sweep that was
      never offered (`v2 is None`) — is `unknown` and drops out.
    """
    if 'sahitya' in (v1, v2):
        return 'sahitya'
    if v1 == 'no-sahitya' and v2 == 'no-sahitya':
        return 'no-sahitya'
    return 'unknown'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--allow-single-sweep', action='store_true',
                    help='parse without sheet 2. Stamps sweeps_applied=1, '
                         'which the scorer rejects — for inspection only.')
    args = ap.parse_args()

    if not SHEET.exists() or not MAPPING.exists():
        sys.exit(f'{SHEET} / {MAPPING} missing — run build_negative_arm.py')
    per_item, problems = parse_sheet(SHEET)

    # Sheet 1 covers half of each window. Gating on it alone is the defect
    # CODEX_NEGATIVE_ARM_REVIEW_R2.md P0-1 identified, so its absence is fatal
    # rather than degraded.
    if SHEET2.exists():
        per_item2, problems2 = parse_sheet(SHEET2)
        sweeps_applied = 2
    elif args.allow_single_sweep:
        per_item2, problems2 = {}, []
        sweeps_applied = 1
        print('!! --allow-single-sweep: sheet 2 absent, every item that would '
              'gate becomes unknown and the scorer will suppress the safety '
              'conclusion.')
    else:
        sys.exit(
            f'{SHEET2} missing. Sheet 1 plays only half of each scored window, '
            f'so it cannot establish "no sung words anywhere in it" on its '
            f'own.\nRun: venv_train/bin/python '
            f'scripts/build_negative_complement.py\n'
            f'(--allow-single-sweep parses anyway, for inspection; it cannot '
            f'produce a safety verdict.)')
    problems += problems2

    mapping = json.loads(MAPPING.read_text())
    verified = json.loads(VERIFIED_OOC.read_text()) \
        if VERIFIED_OOC.exists() else {}
    by_key, by_skel = registry_index()

    if problems:
        print('!! unrecognised label tokens (item, token):')
        for p in problems:
            print('  ', p)

    out, strata, by_source = {}, Counter(), defaultdict(Counter)
    sweep_cross = Counter()
    for item, meta in sorted(mapping.items()):
        opts = per_item.get(item, set())
        opts2 = per_item2.get(item)
        v1 = collapse(opts)
        v2 = collapse(opts2) if opts2 is not None else None
        verdict = combine_sweeps(v1, v2)
        sweep_cross[(v1, v2 if v2 is not None else 'not-offered')] += 1

        if verdict == 'no-sahitya':
            stratum = 'no-sahitya'
        elif verdict == 'unknown':
            stratum = 'unknown'
        elif meta['source'] in verified:
            stratum = 'ooc'
        else:
            # Someone is singing. Whether the work is in the catalog is a join,
            # never an inference from a filename that failed to resolve.
            cands = candidates(Path(meta['source']).stem,
                               meta.get('file_title_raw'))
            if resolve_exact(cands, by_key):
                stratum = 'in-catalog'
            elif resolve_relaxed(cands, by_skel):
                stratum = 'in-catalog_probable'
            else:
                stratum = 'sung_unidentified'

        strata[stratum] += 1
        by_source[meta['candidate_kind']][stratum] += 1
        out[item] = {
            'stratum': stratum,
            # Kept apart on purpose: collapsing them loses which half of the
            # window the evidence came from, and the review's whole point is
            # that the halves are not interchangeable.
            'labels_given_1': sorted(opts),
            'labels_given_2': (sorted(opts2) if opts2 is not None else None),
            'sweep_verdicts': [v1, v2],
            'labeled': bool(opts),
            'candidate_kind': meta['candidate_kind'],
            'cluster': meta.get('cluster'),
            'source': meta['source'],
            'title': meta.get('title'),
            'anchor_seconds': meta.get('anchor_seconds'),
        }

    print(f'\nsheet rows with a label: {sum(1 for v in out.values() if v["labeled"])}'
          f'/{len(mapping)}')
    print('\n=== per-item strata ===')
    for k, v in strata.most_common():
        print(f'  {k:22s} {v}')

    print('\n=== stratum vs why it was sampled (blinding held while labeling) '
          '===')
    for kind, c in sorted(by_source.items()):
        print(f'  {kind:24s} ' + '  '.join(f'{k}={v}'
                                           for k, v in sorted(c.items())))

    # The cost of the second sweep, made visible: every item here that reads
    # (no-sahitya, sahitya) is a window sheet 1 would have gated on and that
    # actually contains singing.
    print('\n=== sweep 1 vs sweep 2 (the second sheet is what this buys) ===')
    for (a, b), v in sorted(sweep_cross.items(), key=lambda kv: -kv[1]):
        flag = '   <-- sheet 1 alone would have gated this' \
            if (a, b) == ('no-sahitya', 'sahitya') else ''
        print(f'  sweep1={a:<12} sweep2={b:<12} {v:>3}{flag}')

    gate = [i for i, d in out.items() if d['stratum'] == GATING]
    clusters = {out[i]['cluster'] for i in gate}
    print(f'\nGATING STRATUM (no-sahitya): {len(gate)} items over '
          f'{len(clusters)} clusters')
    extra = [i for i, d in out.items() if d['stratum'] in NON_GATING]
    print(f'NON-GATING (sensitivity): {len(extra)} items '
          f'({", ".join(sorted({out[i]["stratum"] for i in extra})) or "none"})')
    if not verified:
        print('OOC stratum is empty by construction — no verified '
              'out-of-catalog work identities exist on disk '
              '(data/duration_probe/verified_ooc.json).')

    # What the GPU actually has to transcribe. `in-catalog` items feed no
    # registered readout, so they are excluded; the unknowns are KEPT, because
    # transcribing them is what lets the scorer report T5's worst case as an
    # observation rather than an assumption.
    if SIDECAR.exists():
        durations = json.loads(SIDECAR.read_text()).get('durations', [])
        billed = {i for i, d in out.items()
                  if d['stratum'] in (GATING,) + NON_GATING + ('unknown',)}
        skipped = sorted(set(out) - billed)
        secs = len(billed) * sum(durations)
        print(f'\n=== REALIZED GPU BILL (items feeding a registered readout) '
              f'===')
        print(f'  {len(billed)} items x {sum(durations)}s = {secs / 3600:.1f} h '
              f'unique audio ~= {secs * 7 / 3600:.0f} whisper-hours at the '
              f'7-pass config')
        print(f'  excluded: {len(skipped)} in-catalog item(s), which feed no '
              f'registered readout')
        # ... but they still have to be TRANSCRIBED. `validate_negatives`
        # demands an exact bijection between the sidecar and the result rows,
        # so a run that skips them is invalid, not cheaper. Quote both numbers
        # or the GPU bill reads ~6 whisper-hours low.
        all_secs = len(out) * sum(durations)
        print(f'  but the run still transcribes all {len(out)} items '
              f'({all_secs / 3600:.1f} h, ~{all_secs * 7 / 3600:.0f} '
              f'whisper-hours): the validity gate requires a result row for '
              f'every sidecar window.')

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f'\nwrote {OUT}')

    # Stamp strata into the sidecar so the scorer validates against one file.
    if SIDECAR.exists():
        side = json.loads(SIDECAR.read_text())
        unmatched = 0
        for stem, win in side['windows'].items():
            rec = out.get(win.get('item'))
            if rec is None:
                unmatched += 1
                continue
            win['stratum'] = rec['stratum']
        side['labels_applied'] = True
        side['stratum_counts'] = dict(strata)
        # Rule A (pre-registration §6b) is a conjunction over the gating
        # sources, so which sources exist at gating size is part of the
        # registered design, not an incidental property of the results. Stamped
        # here and checked by the scorer, so a source that later vanishes
        # suppresses instead of dropping quietly out of the conjunction.
        side['gating_source_counts'] = {
            kind: c[GATING] for kind, c in sorted(by_source.items())
            if c[GATING]}
        # The scorer refuses a safety verdict when applied < required, so a
        # single-sweep arm cannot reach a conclusion by accident.
        side['sweeps_required'] = SWEEPS_REQUIRED
        side['sweeps_applied'] = sweeps_applied
        SIDECAR.write_text(json.dumps(side, ensure_ascii=False, indent=1))
        print(f'stamped strata into {SIDECAR}'
              + (f' ({unmatched} windows had no label record)'
                 if unmatched else ''))


if __name__ == '__main__':
    main()
