#!/usr/bin/env python3
"""Selection-bias check on the duration-probe pool.

Red-team finding (`CODEX_DURATION_PROBE_REVIEW.md`, P1 "the surviving pool is
selected for exactly the property that can amplify a duration curve"): exact
lyric resolution selects well-documented works with local text, and the >=300s
constraint selects long performances. Works with many matchable sections give a
long window more chances to capture one distinctive line, while short or
repetitive works saturate early -- so pool selection can change the SHAPE of the
duration curve, not merely its intercept.

This compares the surviving pool against every exclusion bucket on the features
that could drive that interaction. It cannot prove the pool is unbiased; it can
show whether the bias is large enough to worry about, before any GPU is spent.

Run (after `duration_probe_cut.py --dry-run` has written pool_report.json):
  venv_train/bin/python scripts/duration_probe_bias.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / 'data' / 'duration_probe' / 'pool_report.json'
OUT = ROOT / 'data' / 'duration_probe' / 'BIAS_REPORT.md'

FEATURES = [('n_lyric_lines', 'lyric lines'),
            ('pallavi_chars', 'pallavi chars'),
            ('n_tracks', 'registry n_tracks'),
            ('n_renditions', 'renditions'),
            ('title_chars', 'title chars'),
            ('source_duration', 'duration s')]


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    return xs[len(xs) // 2] if xs else None


def fmt(v):
    return '   -  ' if v is None else f'{v:6.0f}'


def main() -> None:
    data = json.loads(REPORT.read_text())
    audit = data['report']['audit']
    pool = data['pool']

    by_bucket = defaultdict(list)
    for row in audit:
        by_bucket[row['bucket']].append(row)

    lines = ['# Duration-probe pool — selection-bias report', '',
             f'Title keys audited: {len(audit)}. '
             f'Surviving pool: {len(pool)}.', '',
             '## Median feature by bucket', '',
             '| bucket | n | ' + ' | '.join(n for _, n in FEATURES) + ' |',
             '|---|---:|' + '---:|' * len(FEATURES)]

    order = ['RESOLVED'] + sorted(k for k in by_bucket if k != 'RESOLVED')
    for bucket in order:
        rows = by_bucket[bucket]
        meds = [median([r[f] for r in rows]) for f, _ in FEATURES]
        lines.append(f'| {bucket} | {len(rows)} | '
                     + ' | '.join(fmt(m).strip() for m in meds) + ' |')

    # the interaction that matters: does lyric length vary within the pool
    # enough that the curve should be reported stratified by it?
    lyr = sorted(r['n_lyric_lines'] for r in by_bucket['RESOLVED'])
    if lyr:
        q1, q2, q3 = lyr[len(lyr) // 4], lyr[len(lyr) // 2], lyr[3 * len(lyr) // 4]
        lines += ['', '## Lyric length inside the surviving pool', '',
                  f'- quartiles: {q1} / {q2} / {q3} lyric lines '
                  f'(min {lyr[0]}, max {lyr[-1]})',
                  '- The scorer must publish the duration curve **stratified '
                  'by this**, since works with more matchable lines give a '
                  'long window more chances to win the per-entry max.']

    clusters = Counter(i['archive_identifier'] for i in pool)
    known = {k: v for k, v in clusters.items() if k}
    big = sorted(known.items(), key=lambda x: -x[1])[:5]
    lines += ['', '## Source clustering (independence of sampling units)', '',
              f'- {len(known)} known archive concerts cover '
              f'{sum(known.values())} of {len(pool)} pool titles; '
              f"{clusters.get(None, 0)} have no archive_identifier.",
              f'- largest clusters: '
              + ', '.join(f'{k} ({v} titles)' for k, v in big),
              '- Titles from one concert share artist, hall, mic and era. The '
              'paired analysis must resample **clusters**, not titles, or the '
              'interval will be too narrow.']

    OUT.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
