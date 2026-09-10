#!/usr/bin/env python3
"""Generate the long-concert labeling template, and validate it once filled.

`--template` writes `data/long_concerts/LABELS.tsv`. **Each concert holds many
songs and therefore many rows**, so the template lays out 7-20 blank song rows
under each concert heading, scaled by that concert's length, plus a worked
four-song example in the header. The first version of this template wrote a
single row per concert; that visually contradicted its own "one row per item"
instruction and left nowhere to type, which is exactly the confusion it caused.

`--validate` is the gate. It checks only things that are checkable without any
model: monotone non-decreasing start times inside each concert, every start
inside that concert's frozen duration, no duplicate starts, item durations that
are not absurd, and — the one that matters — whether each raga name resolves
against the corpus vocabulary. A raga that does not resolve is **not an error**;
it is either a spelling this repo has not seen or a raga genuinely absent from
the corpus, and the distinction decides whether the item is in-vocabulary or
out-of-vocabulary for scoring. Both counts are reported.

Validation writes `data/long_concerts/labels_validation.json` and never edits
`LABELS.tsv`.

A row with an empty `raga` is an unused blank, not a mistake: it is skipped
silently and its missing start time is not reported. A concert whose rows are all
blank is "not yet done" and is dropped rather than guessed at.

Usage:
    venv_train/bin/python scripts/long_concert_labels.py --template [--force]
    venv_train/bin/python scripts/long_concert_labels.py --validate
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LC = ROOT / 'data' / 'long_concerts'
FROZEN = LC / 'FROZEN_CONCERTS.json'
LABELS = LC / 'LABELS.tsv'
OUT = LC / 'labels_validation.json'
CACHE = ROOT / 'data' / 'raga_v2_cache'

COLUMNS = ['concert', 'start', 'raga', 'item', 'confidence', 'notes']

HEADER = """\
# Long-concert item labels.
#
# ONE ROW PER SONG. Each concert has MANY songs, so each concert gets MANY rows
# — that is the whole point of this file. Blank rows are already laid out under
# each concert heading below; just type into them. Add more rows if a concert
# has more songs than there are blanks, delete the ones you do not use.
#
# WORKED EXAMPLE — this is what one concert with four songs looks like:
#
#   concert         start   raga          item                confidence  notes
#   long_concert_1  0:00    Nata          jagadanandakaraka   high
#   long_concert_1  9:20    Kalyani       alapana + nidhi     high        long alapana
#   long_concert_1  31:05   ragamalika    viruttam            medium      excluded
#   long_concert_1  38:40   Sindhubhairavi  thillana          low         noisy, unsure
#
# Four rows, one concert. The 2nd song runs 9:20 -> 31:05 because the next row
# starts there. You never type an end time.
#
# COLUMNS
#   concert     file stem, already filled in. Do not rename.
#   start       when the song STARTS, mm:ss or h:mm:ss. The song ends where the
#               next row starts; the last row of a concert runs to the finish.
#   raga        any spelling you like. If a song is a ragamalika, or you are not
#               sure, write `ragamalika` or `unsure` — it is then EXCLUDED
#               rather than counted wrong. That is always better than guessing.
#   item        song name if you know it, otherwise anything at all ("alapana",
#               "thani", "viruttam", "the fast one"). NEVER scored — it only
#               makes the results table readable afterwards.
#   confidence  high / medium / low. Only `high` rows go in the primary result;
#               medium and low are reported beside it and never merged in.
#   notes       anything. Applause, tuning, a false start, a mic problem.
#
# RULES
#   * Rows starting with # are ignored.
#   * Within a concert, rows must be in increasing start-time order.
#   * A row with an empty `raga` is ignored completely — leftover blanks are
#     fine and cost nothing.
#   * A concert with no ragas filled in is DROPPED, not guessed at. Doing three
#     concerts properly is worth more than eleven done vaguely.
#
# Check your work any time (it never edits this file):
#   venv_train/bin/python scripts/long_concert_labels.py --validate
"""


def _fold(name: str) -> str:
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


def parse_time(t: str) -> float | None:
    t = t.strip()
    if not t:
        return None
    parts = t.split(':')
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None
    if (not vals or any(not math.isfinite(v) or v < 0 for v in vals)
            or any(v >= 60 for v in vals[1:])):
        return None
    if len(vals) == 2:
        return vals[0] * 60 + vals[1]
    if len(vals) == 3:
        return vals[0] * 3600 + vals[1] * 60 + vals[2]
    if len(vals) == 1:
        return vals[0]
    return None


def parse_row(raw: str) -> dict[str, str]:
    """Accept TSV and the space-aligned form shown in the original example.

    Confidence is a field delimiter only when surrounded by whitespace. Missing
    confidence remains empty; it is never silently promoted to high.
    """
    fields = raw.rstrip().split('\t')
    original_fields = raw.split('\t')
    if (len(original_fields) >= 3 and not original_fields[2].strip()
            and re.fullmatch(r'long_concert_\d+', original_fields[0].strip())
            and (not original_fields[1].strip() or parse_time(original_fields[1]) is not None)):
        return dict(zip(COLUMNS, [x.strip() for x in original_fields] + [''] * len(COLUMNS)))
    if len(fields) >= 3 and fields[0].strip().startswith('long_concert_') and not re.search(r'\s', fields[0].strip()) and parse_time(fields[1]) is not None and fields[2].strip():
        return dict(zip(COLUMNS, [x.strip() for x in fields] + [''] * len(COLUMNS)))
    match = re.match(r'^\s*(long_concert_\d+)\s+(\S+)\s+(.+?)\s*$', raw)
    if not match:
        return dict(zip(COLUMNS, [x.strip() for x in fields] + [''] * len(COLUMNS)))
    concert, start, tail = match.groups()
    conf = re.search(r'\s+(high|medium|low)(?:\s+|$)', tail, re.I)
    content = tail[:conf.start()] if conf else tail
    parts = re.split(r'\t+| {2,}', content.strip(), maxsplit=2)
    if len(parts) < 2:
        raise ValueError('ambiguous row: separate raga and item with a tab or two spaces')
    return dict(concert=concert, start=start, raga=parts[0].strip(),
                item=parts[1].strip(), confidence=conf.group(1).lower() if conf else '',
                notes=tail[conf.end():].strip() if conf else (parts[2].strip() if len(parts) > 2 else ''))


def corpus_vocabulary() -> dict[str, str]:
    """Folded raga name -> canonical spelling, from the feature cache itself."""
    import numpy as np
    vocab: dict[str, str] = {}
    for subdir in ('saraga_v3', 'archive_v3'):
        for p in sorted((CACHE / subdir).glob('*.npz')):
            d = np.load(p, allow_pickle=True)
            r = str(d['raga'])
            vocab.setdefault(_fold(r), r)
    return vocab


def blank_rows_for(duration_s: float) -> int:
    """How many blank song rows to lay out under a concert heading.

    A Carnatic concert runs roughly one item per 7-8 minutes once alapana,
    thani and viruttam are counted separately, so scale with length and leave
    slack. These are only blanks — extras are ignored and more can be added.
    """
    return int(min(20, max(6, round(duration_s / 60 / 6) + 3)))


def write_template(force: bool = False) -> None:
    frozen = json.loads(FROZEN.read_text())
    if LABELS.exists() and not force:
        sys.exit(f'{LABELS} already exists — refusing to overwrite labels. '
                 f'Pass --force only if you are certain nothing is filled in.')
    lines = [HEADER, '\t'.join(COLUMNS)]
    total_blanks = 0
    for c in frozen['concerts']:
        stem = c['file'].rsplit('.', 1)[0]
        mins = c['duration_s'] / 60
        n = blank_rows_for(c['duration_s'])
        total_blanks += n
        lines.append('')
        lines.append(f'# ---- {stem}  ({mins:.1f} min) '
                     f'{"-" * max(4, 46 - len(stem))}')
        # first row pre-seeded at 0:00 because a concert almost always has
        # something at the very start; the rest are wholly blank.
        lines.append('\t'.join([stem, '0:00', '', '', '', '']))
        for _ in range(n - 1):
            lines.append('\t'.join([stem, '', '', '', '', '']))
    LABELS.write_text('\n'.join(lines) + '\n')
    print(f'wrote {LABELS}')
    print(f'  {len(frozen["concerts"])} concerts, {total_blanks} blank song rows '
          f'laid out ({blank_rows_for(frozen["concerts"][0]["duration_s"])}-'
          f'{max(blank_rows_for(c["duration_s"]) for c in frozen["concerts"])} '
          f'per concert, scaled by length)')
    print('  add more rows if a concert has more songs; leftover blanks are ignored')


def validate(labels: Path = LABELS, out: Path = OUT) -> int:
    LABELS_ = labels
    frozen = json.loads(FROZEN.read_text())
    dur = {c['file'].rsplit('.', 1)[0]: c['duration_s'] for c in frozen['concerts']}

    rows, errors, warnings = [], [], []
    n_blank = [0]
    for ln, raw in enumerate(LABELS_.read_text().splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if raw.split('\t')[0].strip() == 'concert':
            continue
        try:
            r = parse_row(raw)
        except ValueError as exc:
            errors.append(f'line {ln}: {exc}')
            continue
        r['line'] = ln
        r['start_s'] = parse_time(r['start'])
        if r['concert'] not in dur:
            errors.append(f'line {ln}: unknown concert {r["concert"]!r}')
            continue
        # A row with no raga carries no label. It is an unused blank from the
        # template, not a mistake — ignore it silently and do not complain about
        # its missing start time.
        if not r['raga']:
            n_blank[0] += 1
            continue
        if r['start_s'] is None:
            errors.append(f'line {ln}: {r["raga"]!r} has no start time — '
                          f'every labelled song needs one')
            continue
        if r['start_s'] >= dur[r['concert']]:
            errors.append(f'line {ln}: start {r["start"]} past end of '
                          f'{r["concert"]} ({dur[r["concert"]]/60:.1f} min)')
            continue
        rows.append(r)

    vocab = corpus_vocabulary()
    by_concert: dict[str, list[dict]] = {}
    for r in rows:
        by_concert.setdefault(r['concert'], []).append(r)

    items, unfilled = [], []
    for concert, rs in sorted(by_concert.items()):
        rs.sort(key=lambda x: x['line'])
        starts = [r['start_s'] for r in rs]
        if starts != sorted(starts):
            errors.append(f'{concert}: start times are not in increasing order')
        if len(set(starts)) != len(starts):
            errors.append(f'{concert}: duplicate start times')
        for i, r in enumerate(rs):
            end = rs[i + 1]['start_s'] if i + 1 < len(rs) else dur[concert]
            length = end - r['start_s']
            if length <= 0:
                errors.append(f'line {r["line"]}: non-positive item length')
                continue
            if length < 30:
                warnings.append(f'line {r["line"]}: item is only {length:.0f} s')
            fold = _fold(r['raga'])
            excluded = fold in {'', 'ragamalika', 'unsure', 'unknown', 'na',
                                'thani', 'tani', 'taniavarthanam', 'speech',
                                'applause', 'tuning', 'silence', 'noise'}
            if r['notes']:
                warnings.append(f'line {r["line"]}: notes are descriptive only; '
                                'use an explicit interval manifest before scoring song ends/exclusions')
            items.append({
                'concert': concert, 'line': r['line'],
                'start_s': round(r['start_s'], 3), 'end_s': round(end, 3),
                'duration_s': round(length, 3),
                'raga_raw': r['raga'],
                'raga_canonical': vocab.get(fold),
                'in_corpus_vocabulary': fold in vocab,
                'excluded': excluded,
                'item': r['item'], 'confidence': r['confidence'].lower(),
                'notes': r['notes'],
            })
            if r['confidence'].lower() not in ('high', 'medium', 'low', ''):
                warnings.append(f'line {r["line"]}: confidence '
                                f'{r["confidence"]!r} is not high/medium/low')

    scorable = [i for i in items if not i['excluded']]
    in_vocab = [i for i in scorable if i['in_corpus_vocabulary']]
    oov = [i for i in scorable if not i['in_corpus_vocabulary']]
    high = [i for i in in_vocab if i['confidence'] == 'high']

    unfilled = sorted(set(dur) - set(by_concert))
    report = {
        'ready_for_scoring': False,
        'boundary_contract': ('Syntax/vocabulary validation only. Ends are inferred '
                              'from the next start or file end; use a reviewed '
                              'explicit interval manifest for scoring.'),
        'n_concerts_labelled': len(by_concert),
        'n_blank_rows_ignored': n_blank[0],
        'unfilled_concerts': unfilled,
        'n_items': len(items),
        'n_excluded_ragamalika_or_unsure': len(items) - len(scorable),
        'n_scorable': len(scorable),
        'n_in_corpus_vocabulary': len(in_vocab),
        'n_out_of_vocabulary': len(oov),
        'oov_names': sorted({i['raga_raw'] for i in oov}),
        'n_high_confidence_in_vocab': len(high),
        'total_scorable_audio_s': round(sum(i['duration_s'] for i in scorable), 1),
        'errors': errors, 'warnings': warnings,
        'items': items,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

    print(f'concerts labelled     {report["n_concerts_labelled"]}/{len(dur)}'
          + (f'  (not yet done: {", ".join(unfilled)})' if unfilled else ''))
    print(f'blank rows ignored    {report["n_blank_rows_ignored"]}  '
          f'(unused template rows — harmless)')
    print(f'items                 {report["n_items"]}')
    print(f'  excluded            {report["n_excluded_ragamalika_or_unsure"]}'
          '  (ragamalika / unsure)')
    print(f'  scorable            {report["n_scorable"]}')
    print(f'    in vocabulary     {report["n_in_corpus_vocabulary"]}')
    print(f'    out of vocabulary {report["n_out_of_vocabulary"]}'
          + (f'  {report["oov_names"]}' if oov else ''))
    print(f'    high confidence   {report["n_high_confidence_in_vocab"]}')
    print(f'scorable audio        {report["total_scorable_audio_s"]/3600:.2f} h')
    for e in errors:
        print('ERROR   ' + e)
    for w in warnings:
        print('warn    ' + w)
    print(f'\nwrote {out}')
    return 1 if errors else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', action='store_true')
    ap.add_argument('--force', action='store_true',
                    help='overwrite an existing LABELS.tsv')
    ap.add_argument('--validate', action='store_true')
    ap.add_argument('--labels', type=Path, default=LABELS)
    ap.add_argument('--out', type=Path, default=OUT)
    args = ap.parse_args()
    if args.template:
        write_template(args.force)
    elif args.validate:
        sys.exit(validate(args.labels, args.out))
    else:
        ap.error('pass --template or --validate')


if __name__ == '__main__':
    main()
