#!/usr/bin/env python3
"""Convert Deepti's `LABELS.tsv` into the explicit interval manifest scoring reads.

`scripts/evaluate_labeled_intervals.py` refuses to run unless
`data/architecture_audit/label_intervals.json` pins the SHA256 of the current
`LABELS.tsv`. Until now that manifest was written by hand. This script derives
it deterministically and fails loudly on anything it cannot interpret, so a
human never has to guess what an agent did with a free-text note.

Rows (parsed with `long_concert_labels.parse_row`, so tab and space-run columns
both work):
  * blank-raga rows are ignored; `ragamalika` / `unsure` / thani-type rows are
    not intervals (recorded under `unscored`);
  * a row ends at the next labelled row's start, or the concert's frozen end.

Notes are free text. Only these phrasings are interpreted:
  * ``song ends [at|around] T`` or ``at T, song ends``  -> the row ends at T;
    ``around`` marks the end approximate (not primary);
  * ``at T, thani ... until T2``                         -> exclusion `tani`,
    the row is split around it into two intervals with one item ID;
  * ``ignore rest of (clip|recording)`` after a song end  -> exclusion
    `after_song` from the end to the next row / concert end;
  * ``muted``                                            -> not primary.
Any other `m:ss` time in a note is an error: extend the rules or reword the
note, never let a time be silently dropped.

Primary = confidence `high`, end not approximate, not muted.

Raga spelling is resolved against the model and corpus vocabularies: exact
fold first, then a loose key (`sh`->`s`, repeated letters collapsed) only when
that key is unique in the vocabulary. Every non-exact resolution is printed.
Global aliases are deliberately not used (kalAnidhi -> Kalyani would change
the raga's identity).

Default is a dry run that prints the intervals and the diff against the
existing manifest. `--write` replaces the manifest.

Usage:
    venv_train/bin/python scripts/labels_to_intervals.py            # dry run
    venv_train/bin/python scripts/labels_to_intervals.py --write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

from scripts.long_concert_labels import parse_row, parse_time, _fold  # noqa: E402

LABELS = ROOT / 'data' / 'long_concerts' / 'LABELS.tsv'
FROZEN = ROOT / 'data' / 'long_concerts' / 'FROZEN_CONCERTS.json'
OUT = ROOT / 'data' / 'architecture_audit' / 'label_intervals.json'

UNSCORED = {'ragamalika', 'unsure', 'unknown', 'na', 'thani', 'tani',
            'taniavarthanam', 'taniavartanam', 'speech', 'applause', 'tuning',
            'silence', 'noise'}
TIME = r'(\d{1,2}:\d{2}(?::\d{2})?)'
SONG_END = [re.compile(r'song\s+ends,?\s*(at\s+|around\s+|~\s*)?' + TIME, re.I),
            re.compile(r'at\s+' + TIME + r',?\s+song\s+ends', re.I)]
TANI = re.compile(r'at\s+' + TIME + r',?\s+th?ani\b[^.;]*?until\s+' + TIME, re.I)
IGNORE_REST = re.compile(r'ignore\s+(the\s+)?rest\s+of\s+(the\s+)?(clip|recording)(?!\s+until)', re.I)


class LabelError(ValueError):
    pass


def loose_key(name: str) -> str:
    k = _fold(name).replace('sh', 's')
    return re.sub(r'(.)\1+', r'\1', k)


def build_resolver(vocab: list[str]):
    exact = {_fold(v): v for v in vocab}
    loose: dict[str, set[str]] = {}
    for v in vocab:
        loose.setdefault(loose_key(v), set()).add(v)

    def resolve(raw: str) -> tuple[str, str]:
        if _fold(raw) in exact:
            return exact[_fold(raw)], 'exact'
        hits = loose.get(loose_key(raw), set())
        if len(hits) == 1:
            return next(iter(hits)), 'loose'
        return raw, 'unresolved' if not hits else 'ambiguous'
    return resolve


def default_vocabulary() -> list[str]:
    from carnatify.ml.raga_runtime import RagaCandidate
    from scripts.long_concert_labels import corpus_vocabulary
    model = [str(c) for c in RagaCandidate.load('context180').classes]
    return model + sorted(set(corpus_vocabulary().values()) - set(model))


def interpret_notes(notes: str, start: float, end: float, line: int) -> dict:
    """Return {'end', 'approximate', 'muted', 'exclusions'} or raise LabelError."""
    consumed: list[tuple[int, int]] = []
    out = dict(end=end, approximate=False, muted=bool(re.search(r'\bmuted\b', notes, re.I)),
               exclusions=[])
    for m in TANI.finditer(notes):
        a, b = parse_time(m.group(1)), parse_time(m.group(2))
        if not (start < a < b <= end):
            raise LabelError(f'line {line}: thani {m.group(1)}-{m.group(2)} outside the row')
        out['exclusions'].append(dict(kind='tani', start_s=a, end_s=b))
        consumed.append(m.span())
    song_end = None
    for pat in SONG_END:
        for m in pat.finditer(notes):
            if any(s <= m.start() < e for s, e in consumed):
                continue
            t = parse_time(m.group(m.lastindex))
            if song_end is not None and t != song_end:
                raise LabelError(f'line {line}: two different song ends in notes')
            song_end = t
            out['approximate'] |= bool(m.lastindex == 2 and (m.group(1) or '').strip().lower() in ('around', '~'))
            consumed.append(m.span())
    if song_end is not None:
        if not start < song_end <= end:
            raise LabelError(f'line {line}: song end {song_end:.0f}s outside the row ({start:.0f}-{end:.0f}s)')
        if any(x['end_s'] > song_end for x in out['exclusions']):
            raise LabelError(f'line {line}: thani runs past the song end')
        if IGNORE_REST.search(notes) and song_end < end:
            out['exclusions'].append(dict(kind='after_song', start_s=song_end, end_s=end))
        out['end'] = song_end
    for m in re.finditer(TIME, notes):
        if not any(s <= m.start() < e for s, e in consumed):
            raise LabelError(f'line {line}: note time {m.group(1)} is not covered by any rule: {notes!r}')
    return out


def convert(labels_path: Path, frozen: dict, resolve) -> dict:
    dur = {Path(c['file']).stem: c['duration_s'] for c in frozen['concerts']}
    rows = []
    for ln, raw in enumerate(labels_path.read_text().splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith('#') or raw.split('\t')[0].strip() == 'concert':
            continue
        r = parse_row(raw)
        if r['concert'] not in dur:
            raise LabelError(f'line {ln}: unknown concert {r["concert"]!r}')
        if not r['raga']:
            continue
        r['line'], r['start_s'] = ln, parse_time(r['start'])
        if r['start_s'] is None:
            raise LabelError(f'line {ln}: {r["raga"]!r} has no valid start time')
        rows.append(r)

    intervals, exclusions, unscored, resolutions = [], [], [], []
    by_concert: dict[str, list[dict]] = {}
    for r in rows:
        by_concert.setdefault(r['concert'], []).append(r)
    for concert in sorted(by_concert, key=lambda c: int(c.rsplit('_', 1)[1])):
        rs = by_concert[concert]
        starts = [r['start_s'] for r in rs]
        if starts != sorted(starts) or len(set(starts)) != len(starts):
            raise LabelError(f'{concert}: start times must strictly increase')
        n = int(concert.rsplit('_', 1)[1])
        k = 0
        for i, r in enumerate(rs):
            end = rs[i + 1]['start_s'] if i + 1 < len(rs) else dur[concert]
            if not r['start_s'] < end <= dur[concert]:
                raise LabelError(f'line {r["line"]}: row does not fit the concert')
            if _fold(r['raga']) in UNSCORED:
                unscored.append(dict(concert=concert, start_s=r['start_s'], end_s=end,
                                     raga_raw=r['raga'], source_line=r['line']))
                continue
            k += 1
            item_id = f'c{n}_{k}'
            info = interpret_notes(r['notes'], r['start_s'], end, r['line'])
            raga, how = resolve(r['raga'])
            if how != 'exact':
                resolutions.append(dict(line=r['line'], raw=r['raga'], resolved=raga, how=how))
            conf = r['confidence'].lower()
            primary = conf == 'high' and not info['approximate'] and not info['muted']
            reasons = [x for x, on in (('approximate end', info['approximate']),
                                       ('partly muted', info['muted']),
                                       ('confidence not high', conf != 'high')) if on]
            cuts = sorted(x for x in info['exclusions'] if x['kind'] == 'tani')
            pieces, a = [], r['start_s']
            for x in cuts:
                pieces.append((a, x['start_s']))
                a = x['end_s']
            pieces.append((a, info['end']))
            for a, b in pieces:
                if b <= a:
                    continue
                row = dict(concert=concert, item_id=item_id, source_line=r['line'],
                           start_s=a, end_s=b, raga_raw=r['raga'], raga=raga,
                           item=r['item'], confidence=conf, primary=primary)
                if reasons:
                    row['note'] = '; '.join(reasons)
                intervals.append(row)
            for x in info['exclusions']:
                exclusions.append(dict(concert=concert, start_s=x['start_s'], end_s=x['end_s'],
                                       kind=x['kind'], source_line=r['line']))
    return dict(
        schema=1, role='held_out_evaluation_only',
        source=str(labels_path.relative_to(ROOT)) if labels_path.is_relative_to(ROOT) else str(labels_path),
        source_sha256=hashlib.sha256(labels_path.read_bytes()).hexdigest(),
        generator='scripts/labels_to_intervals.py',
        notes=('Derived deterministically from LABELS.tsv; notes interpreted only by the rules in '
               'the generator docstring. Unlabeled gaps remain unknown. Non-exact raga '
               'resolutions are listed under raga_resolutions.'),
        intervals=intervals, exclusions=exclusions, unscored=unscored,
        raga_resolutions=resolutions)


def diff(old: dict, new: dict) -> list[str]:
    key = lambda r: (r['concert'], round(r['start_s'], 3))  # noqa: E731
    o, n = {key(r): r for r in old['intervals']}, {key(r): r for r in new['intervals']}
    lines = []
    for k in sorted(o.keys() | n.keys()):
        a, b = o.get(k), n.get(k)
        if a is None:
            lines.append(f'+ {k[0]} {b["start_s"]:.0f}-{b["end_s"]:.0f}s {b["raga"]} primary={b["primary"]}')
        elif b is None:
            lines.append(f'- {k[0]} {a["start_s"]:.0f}-{a["end_s"]:.0f}s {a["raga"]}')
        else:
            ch = [f'{f}: {a.get(f)!r} -> {b.get(f)!r}' for f in ('end_s', 'raga', 'confidence', 'primary', 'item_id')
                  if (round(a.get(f), 3) if f == 'end_s' else a.get(f)) !=
                     (round(b.get(f), 3) if f == 'end_s' else b.get(f))]
            if ch:
                lines.append(f'~ {k[0]} {a["start_s"]:.0f}s ' + '; '.join(ch))
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--labels', type=Path, default=LABELS)
    ap.add_argument('--out', type=Path, default=OUT)
    ap.add_argument('--write', action='store_true', help='replace the manifest (default: dry run)')
    args = ap.parse_args()
    from scripts.long_concert_score import validate_intervals
    frozen = json.loads(FROZEN.read_text())
    try:
        manifest = convert(args.labels, frozen, build_resolver(default_vocabulary()))
        validate_intervals(manifest, frozen)
    except (LabelError, ValueError) as exc:
        sys.exit(f'ERROR {exc}')
    for r in manifest['intervals']:
        print(f'{r["item_id"]:6} {r["concert"]:15} {r["start_s"]:7.0f}-{r["end_s"]:7.0f}s '
              f'{r["raga"]:22} {r["confidence"] or "-":6} primary={r["primary"]}'
              + (f'  ({r["note"]})' if 'note' in r else ''))
    for x in manifest['raga_resolutions']:
        print(f'raga   line {x["line"]}: {x["raw"]!r} -> {x["resolved"]!r} ({x["how"]})')
    print(f'{len(manifest["intervals"])} intervals, {len(manifest["exclusions"])} exclusions, '
          f'{len(manifest["unscored"])} unscored rows, '
          f'{sum(r["primary"] for r in manifest["intervals"])} primary intervals')
    if args.out.exists():
        d = diff(json.loads(args.out.read_text()), manifest)
        print('\nchanges vs existing manifest:' if d else '\nno interval changes vs existing manifest')
        print('\n'.join(d))
    if args.write:
        args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        print(f'\nwrote {args.out}')
    else:
        print('\ndry run; pass --write to replace the manifest')


if __name__ == '__main__':
    main()
