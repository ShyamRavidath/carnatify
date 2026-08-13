#!/usr/bin/env python3
"""Generate the long-concert labeling template, and validate it once filled.

`--template` writes `data/long_concerts/LABELS.tsv` with one seed row per frozen
concert. Deepti fills it in; every other row is added by her.

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

Usage:
    venv_train/bin/python scripts/long_concert_labels.py --template
    venv_train/bin/python scripts/long_concert_labels.py --validate
"""
from __future__ import annotations

import argparse
import json
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
# Long-concert item labels — Deepti fills this in. One row per ITEM.
#
#   concert     file stem, e.g. long_concert_3   (do not rename)
#   start       when the item STARTS, mm:ss or h:mm:ss. The item ends where the
#               next one starts, so you never type an end time. Use the last row
#               of a concert for whatever runs to the finish.
#   raga        raga name, any spelling you like. If an item is a ragamalika or
#               you are not sure, write ragamalika / unsure and it is excluded
#               rather than counted wrong.
#   item        composition name if you know it, otherwise anything ("alapana",
#               "thani", "viruttam"). Never scored — it is for reading the
#               results table afterwards.
#   confidence  high / medium / low. Only `high` rows are in the primary
#               read-out; the rest are reported beside it and never merged in.
#   notes       anything. Applause, tuning, a false start, a mic problem.
#
# Rows starting with # are ignored. Order within a concert must be by start time.
# Leave a concert's seed row alone and add rows under it if you have not done
# that concert yet — an unfilled concert is dropped, not guessed at.
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
    if len(vals) == 2:
        return vals[0] * 60 + vals[1]
    if len(vals) == 3:
        return vals[0] * 3600 + vals[1] * 60 + vals[2]
    if len(vals) == 1:
        return vals[0]
    return None


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


def write_template() -> None:
    frozen = json.loads(FROZEN.read_text())
    if LABELS.exists():
        sys.exit(f'{LABELS} already exists — refusing to overwrite labels.')
    lines = [HEADER, '\t'.join(COLUMNS)]
    for c in frozen['concerts']:
        stem = c['file'].rsplit('.', 1)[0]
        lines.append(f"# {stem}: {c['duration_s']/60:.1f} min total")
        lines.append('\t'.join([stem, '0:00', '', '', '', '']))
    LABELS.write_text('\n'.join(lines) + '\n')
    print(f'wrote {LABELS} — {len(frozen["concerts"])} seed rows')


def validate(labels: Path = LABELS, out: Path = OUT) -> int:
    LABELS_ = labels
    frozen = json.loads(FROZEN.read_text())
    dur = {c['file'].rsplit('.', 1)[0]: c['duration_s'] for c in frozen['concerts']}

    rows, errors, warnings = [], [], []
    for ln, raw in enumerate(LABELS_.read_text().splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        f = raw.split('\t')
        if f[0].strip() == 'concert':
            continue
        f += [''] * (len(COLUMNS) - len(f))
        r = dict(zip(COLUMNS, (x.strip() for x in f)))
        r['line'] = ln
        r['start_s'] = parse_time(r['start'])
        if r['concert'] not in dur:
            errors.append(f'line {ln}: unknown concert {r["concert"]!r}')
            continue
        if r['start_s'] is None:
            errors.append(f'line {ln}: unparseable start {r["start"]!r}')
            continue
        if r['start_s'] > dur[r['concert']]:
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
        if all(not r['raga'] for r in rs):
            unfilled.append(concert)
            continue
        for i, r in enumerate(rs):
            end = rs[i + 1]['start_s'] if i + 1 < len(rs) else dur[concert]
            length = end - r['start_s']
            if length <= 0:
                errors.append(f'line {r["line"]}: non-positive item length')
                continue
            if length < 30:
                warnings.append(f'line {r["line"]}: item is only {length:.0f} s')
            fold = _fold(r['raga'])
            excluded = fold in {'', 'ragamalika', 'unsure', 'unknown', 'na'}
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

    report = {
        'n_concerts_labelled': len(by_concert) - len(unfilled),
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
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    print(f'concerts labelled     {report["n_concerts_labelled"]}/11'
          + (f'  (unfilled: {", ".join(unfilled)})' if unfilled else ''))
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
    ap.add_argument('--validate', action='store_true')
    ap.add_argument('--labels', type=Path, default=LABELS)
    ap.add_argument('--out', type=Path, default=OUT)
    args = ap.parse_args()
    if args.template:
        write_template()
    elif args.validate:
        sys.exit(validate(args.labels, args.out))
    else:
        ap.error('pass --template or --validate')


if __name__ == '__main__':
    main()
