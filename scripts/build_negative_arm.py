#!/usr/bin/env python3
"""Build the duration probe's negative arm, rebuilt 2026-07-28.

The first version was rejected in full (`CODEX_NEGATIVE_ARM_REVIEW.md`). Four
of its defects are structural, and this rewrite is organised around them.

**1. Windows are cut BEFORE labels are collected.** The old order cut labeling
excerpts at fixed 15/50/85% positions and cut the scored windows later, from an
independent random anchor — so 2/23 no-sahitya and 3/12 OOC items were labeled
on audio that overlapped the scored window nowhere at all. Here the 30s/300s
windows are cut first and the labeling audio is drawn *from inside the selected
300s window*, so the label is about exactly the audio the pipeline will hear.
Only the 300s window needs a label: the 30s window nests at its start, so a
lyric-free 300s window is lyric-free at 30s by construction.

**2. Labeling is a scan of the whole window, not three sparse samples.** Three
20s excerpts covered 20% of a 300s window and could not support "no sahitya
anywhere in it". Each item now gets one concatenated scan — 10s every 20s,
50% duty cycle, maximum unheard gap 10s — cut from the window wav itself.

**3. The ear is asked only what an ear can answer.** Catalog membership is a
lookup over 8,688 registry rows; the old sheet asked for `ooc` by ear. The
label is now binary (sahitya / no-sahitya), and every catalog question is a
join. `unusable` and missing labels become **unknown**, never no-sahitya.

**4. OOC truth needs a verified work identity, not a failed filename lookup.**
Candidates whose title is unresolvable are `sung_unidentified`, a non-gating
sensitivity stratum. An item becomes OOC only by appearing in
`data/duration_probe/verified_ooc.json`, which is a reviewed file.

Endpoints only (30s and 300s): that is the contrast the gate reads, and it buys
roughly 2.5x the items for the same GPU (`CODEX_NEGATIVE_ARM_REVIEW.md` §5.5).

Run:
  venv_train/bin/python scripts/build_negative_arm.py --dry-run   # supply only
  venv_train/bin/python scripts/build_negative_arm.py             # cut it
"""
import argparse
import json
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from identify_clip import skey  # noqa: E402
from duration_probe_titles import (NON_COMP, candidates,  # noqa: E402
                                   manifest_rows, primary_title,
                                   registry_index, resolve_exact,
                                   resolve_relaxed)
from duration_probe_cut import AUDIO, cut, ffprobe_duration  # noqa: E402
from duration_probe_score import power_table  # noqa: E402  (one definition)

OUT_ROOT = ROOT / 'data' / 'duration_probe'
WINDOW_DIR = OUT_ROOT / 'negatives'
LABEL_DIR = OUT_ROOT / 'negative_arm'
VERIFIED_OOC = OUT_ROOT / 'verified_ooc.json'

DURATIONS = (30, 300)
SEED = 20260728

# Second no-sahitya source. `data/concert_audio` holds only 36 free-form files,
# so a census of them caps the gating stratum at ~34 items — enough to rule out
# a +15pp bluff rise only if at most ONE item bluffs, which is too brittle to
# stake the roadmap on. Long in-catalog recordings open with alapana, and their
# first 300s is both plentiful (227 files over 177 clusters at >= 900s) and the
# most product-relevant negative there is: it is exactly what Jon hears if he
# opens the app before the kriti starts.
#
# Anchor selection cannot bias this arm the way it would bias the recall arm.
# Eligibility here is decided by adjudicating **the very window that is
# scored**, so where the window came from changes which items land in the
# stratum — the composition of the negative population, which is described —
# and never whether a given item's label is right.
OPENING_MIN_DURATION = 900
OPENING_ANCHOR = 0.0

SCAN_EVERY = 20      # start a snippet every 20s of the window ...
SCAN_LEN = 10        # ... and play 10s of it: 50% duty, max unheard gap 10s
BOUNDARY_PP = 15.0   # the pre-registered effect size the negative arm polices


# --------------------------------------------------------------------------
# candidate generation
# --------------------------------------------------------------------------

def survey() -> list[dict]:
    """Every concert_audio file, with its title, resolution status and cluster.

    Resolution is asymmetric on purpose (`duration_probe_titles`): exact `skey`
    decides in-catalog, and the relaxed consonant-skeleton key is allowed to
    *disqualify* an OOC candidate but never to create one.
    """
    by_key, by_skel = registry_index()
    man = manifest_rows()
    rows = []
    for p in sorted(AUDIO.rglob('*.mp3')):
        rel = str(p.relative_to(ROOT))
        meta = man.get(rel) or {}
        raw = meta.get('file_title_raw')
        title, prov = primary_title(p.stem, raw)
        cands = candidates(p.stem, raw)
        exact = resolve_exact(cands, by_key)
        relaxed = resolve_relaxed(cands, by_skel)
        rows.append({
            'source': rel,
            'title': title,
            'title_provenance': prov,
            'file_title_raw': raw,
            'archive_identifier': meta.get('archive_identifier'),
            'free_form': skey(title) in NON_COMP,
            'resolves_exact': sorted({i for d in exact.values() for i in d}),
            'resolves_relaxed': sorted({i for d in relaxed.values()
                                        for i in d})[:8],
        })
    return rows


def classify(row: dict) -> str:
    """Why this file is a negative CANDIDATE. Not a stratum — the ear decides.

    * `free_form_candidate` — the filename names a section (alapana, RTP,
      thani), so there is no fixed composition in it. The no-sahitya supply.
    * `unidentified_candidate` — a real recording whose title resolves to
      nothing, even under the relaxed key. NOT evidence of OOC: seven-digit
      upload ids, shellac catalogue numbers and `Concert 163` all land here.
    * `opening_candidate` — the first 300s of a long in-catalog recording,
      where the alapana lives. Also just a candidate: the ear decides.
    * `in_catalog` / `in_catalog_probable` — resolves; not a negative.
    """
    if row.get('opening'):
        return 'opening_candidate'
    if row['free_form']:
        return 'free_form_candidate'
    if row['resolves_exact']:
        return 'in_catalog'
    if row['resolves_relaxed']:
        return 'in_catalog_probable'
    return 'unidentified_candidate'


def pick(rows: list[dict], min_duration: int, per_cluster: int,
         rng: random.Random) -> tuple[list[dict], dict]:
    """Cap items per archive cluster, then take a census of what remains.

    Sampling by file treated 7 tracks off one lecture-demonstration upload as 7
    independent works. The cap is the fix. Files with no manifest row have no
    known cluster; each is treated as its own, which is an assumption the
    report states rather than hides.
    """
    report = {'classified': Counter(), 'dropped_short': Counter(),
              'dropped_cluster_cap': Counter()}
    eligible = defaultdict(list)
    for row in rows:
        kind = classify(row)
        report['classified'][kind] += 1
        if kind not in ('free_form_candidate', 'unidentified_candidate'):
            continue
        dur = ffprobe_duration(ROOT / row['source'])
        row['source_duration'] = round(dur, 1)
        if dur < min_duration:
            report['dropped_short'][kind] += 1
            continue
        cluster = row['archive_identifier'] or f"solo:{row['source']}"
        row['cluster'] = cluster
        eligible[(kind, cluster)].append(row)

    out = []
    for (kind, _cluster), group in sorted(eligible.items()):
        group.sort(key=lambda r: r['source'])
        keep = group if len(group) <= per_cluster else rng.sample(group,
                                                                  per_cluster)
        report['dropped_cluster_cap'][kind] += len(group) - len(keep)
        out.extend(keep)
    out.sort(key=lambda r: r['source'])
    return out, report


def pick_openings(rows: list[dict], n: int, used_clusters: set,
                  rng: random.Random) -> list[dict]:
    """Opening windows of long in-catalog recordings, one per fresh cluster.

    These are CANDIDATES only. A recording resolving to a catalog work says
    nothing about whether its first five minutes contain any sung words, and
    the ear settles that per window, as everywhere else in this arm.
    """
    pool = []
    for row in rows:
        if classify(row) != 'in_catalog':
            continue
        cluster = row['archive_identifier'] or f"solo:{row['source']}"
        if cluster in used_clusters:
            continue
        dur = ffprobe_duration(ROOT / row['source'])
        if dur < OPENING_MIN_DURATION:
            continue
        pool.append({**row, 'source_duration': round(dur, 1),
                     'cluster': cluster, 'opening': True})
    by_cluster: dict[str, list] = defaultdict(list)
    for r in pool:
        by_cluster[r['cluster']].append(r)
    one_each = [sorted(g, key=lambda r: r['source'])[0]
                for g in by_cluster.values()]
    one_each.sort(key=lambda r: r['source'])
    return one_each if n >= len(one_each) else rng.sample(one_each, n)


# --------------------------------------------------------------------------
# cutting
# --------------------------------------------------------------------------

def scan_file(window: Path, dest: Path, length: int) -> int:
    """Concatenate 10s every 20s of `window` into one file. Returns snippets.

    Built from the window wav, not the source mp3, so the labeler hears
    literally the audio that will be transcribed.
    """
    starts = list(range(0, max(1, length - SCAN_LEN + 1), SCAN_EVERY))
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


def write_sheet(items: list[str], mapping: dict, longest: int) -> None:
    n = len(items)
    lines = [
        '# Negative-arm labeling sheet — duration probe (rebuilt 2026-07-28)',
        '',
        f'**{n} rows, one label each. One file to listen to per row.**',
        '',
        f'Each `_scan.wav` is a {SCAN_LEN}s-every-{SCAN_EVERY}s sweep of the '
        f'exact {longest}s window the pipeline will be given — about '
        f'{(longest // SCAN_EVERY) * SCAN_LEN}s of listening, covering half of '
        'it with no unheard gap longer than '
        f'{SCAN_EVERY - SCAN_LEN}s. Last time you were given three 20s '
        'excerpts from elsewhere in the recording; five of them turned out not '
        'to overlap the scored window at all, which is why this is a sweep of '
        'the window itself.',
        '',
        '**The only question is whether anyone sings words.** Not which '
        'composition, not whether we have it — those are lookups, and asking '
        'your ear for them was my mistake last round.',
        '',
        '**Stop as soon as you hear singing.** The moment anyone sings words, '
        'write `sahitya` and go to the next row — you do not have to finish '
        'the sweep. Most rows should end in a few seconds; only the genuinely '
        'lyric-free ones cost you the full sweep.',
        '',
        '**You can stop anywhere in the sheet.** Rows you leave blank are '
        'treated as unknown and excluded, and the order is random, so a '
        'partial sheet is a valid smaller experiment rather than a broken one. '
        'More labeled rows buys tolerance for a bad item: ~40 confirmed '
        'no-sahitya rows survive one surprise answer, ~55 survive two.',
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
        f'If a row is borderline, the full {longest}s window is on disk as '
        '`../negatives/<id>d300.wav` — but only open it if the sweep is '
        'genuinely ambiguous.',
        '',
        'Ids are blind and the order is shuffled, so the filenames tell you '
        'nothing (`METRIC_CONTRACT.md:30`).',
        '',
        '| # | listen | label | notes |',
        '|---:|---|---|---|',
    ]
    lines += [f'| {i} | `{item}_scan.wav` |  |  |'
              for i, item in enumerate(items, 1)]
    (LABEL_DIR / 'LABELING_SHEET.md').write_text('\n'.join(lines) + '\n')
    (LABEL_DIR / '_mapping.json').write_text(
        json.dumps(mapping, ensure_ascii=False, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--durations', type=int, nargs='+', default=list(DURATIONS))
    ap.add_argument('--per-cluster', type=int, default=1,
                    help='max items from one archive upload (pseudo-replication '
                         'cap; the old arm took 7 tracks off one lecdem)')
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--opening', type=int, default=30,
                    help='opening windows of long in-catalog recordings added '
                         'to the no-sahitya CANDIDATE set (the 36 free-form '
                         'files alone cap the gating stratum at ~34)')
    ap.add_argument('--dry-run', action='store_true',
                    help='print the supply and power report, cut nothing')
    args = ap.parse_args()

    longest = max(args.durations)
    rng = random.Random(args.seed)
    rows = survey()
    picked, report = pick(rows, longest, args.per_cluster, rng)
    if args.opening:
        used = {r['cluster'] for r in picked}
        picked += pick_openings(rows, args.opening, used, rng)

    print('=== CANDIDATE SUPPLY (data/concert_audio) ===')
    for k, v in report['classified'].most_common():
        print(f'  {k:26s} {v}')
    print(f"\n  dropped, shorter than {longest}s: "
          f"{dict(report['dropped_short'])}")
    print(f"  dropped, archive-cluster cap {args.per_cluster}: "
          f"{dict(report['dropped_cluster_cap'])}")

    by_kind = defaultdict(list)
    for r in picked:
        by_kind[classify(r)].append(r)
    print('\n=== ITEMS TO CUT ===')
    for kind, group in sorted(by_kind.items()):
        clusters = len({r['cluster'] for r in group})
        print(f'  {kind:26s} {len(group):>3} items over {clusters} clusters')

    n_gate = (len(by_kind.get('free_form_candidate', []))
              + len(by_kind.get('opening_candidate', [])))
    print(f'\n=== WHAT THE GATING STRATUM CAN SUPPORT ===')
    print(f'  {n_gate} no-sahitya CANDIDATES; realized n is whatever her ear '
          f'confirms and')
    print(f'  whatever she gets through — unlabeled rows are unknown, not '
          f'no-sahitya.')
    print('  new bluffs (30s abstains, 300s answers) -> one-sided exact 95% '
          'upper bound')
    for n in sorted({max(1, n_gate // 2), max(1, int(n_gate * 0.75)), n_gate}):
        row = '  '.join(f'b={b}: {ub:4.1f}pp{"" if ok else "*"}'
                        for b, ub, ok in power_table(n))
        print(f'    if n={n:<3} {row}')
    print('    (* = does NOT rule out +15pp)')
    print('  This arm is powered to RULE OUT a +15pp bluff rise, not to '
          'detect one;')
    print('  detection at +15pp needs ~44 items that FLIP, which no corpus '
          'here can promise.')

    verified = json.loads(VERIFIED_OOC.read_text()) if VERIFIED_OOC.exists() \
        else {}
    print(f'\n=== OOC STRATUM ===')
    print(f'  verified OOC works on file: {len(verified)}')
    if not verified:
        print('  EMPTY. Not a sampling failure — no recording in '
              'data/concert_audio has')
        print('  a verified out-of-catalog work identity. Every unresolvable '
              'title here is')
        print('  an upload id, a shellac catalogue number or a slot name '
              '(`Concert 163`),')
        print('  and the registry itself was built from these filenames. OOC '
              'abstention')
        print('  at length is UNMEASURABLE from assets on disk and needs '
              'prospective audio.')

    total = len(picked) * sum(args.durations)
    print(f'\n=== COST ===')
    print(f'  {len(picked)} items x {len(args.durations)} windows = '
          f'{len(picked) * len(args.durations)} clips, '
          f'{total / 3600:.1f} h unique audio '
          f'({total * 7 / 3600:.0f} whisper-hours at the 7-pass config)')
    print(f'  labeling: {len(picked)} sweeps x '
          f'{(longest // SCAN_EVERY) * SCAN_LEN}s = '
          f'{len(picked) * (longest // SCAN_EVERY) * SCAN_LEN / 60:.0f} min')

    if args.dry_run:
        return

    WINDOW_DIR.mkdir(parents=True, exist_ok=True)
    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    windows, mapping, sheet = {}, {}, []
    for idx, row in enumerate(picked):
        item = f'neg{idx:03d}'
        src = ROOT / row['source']
        anchor = (OPENING_ANCHOR if row.get('opening')
                  else rng.uniform(0, max(0.0,
                                          row['source_duration'] - longest)))
        ok = True
        for dur in args.durations:
            stem = f'{item}d{dur:03d}'
            if not cut(src, anchor, dur, WINDOW_DIR / f'{stem}.wav'):
                ok = False
                continue
            windows[stem] = {**row, 'item': item, 'window_seconds': dur,
                             'anchor_seconds': round(anchor, 1),
                             'candidate_kind': classify(row)}
        if not ok:
            continue
        n_snip = scan_file(WINDOW_DIR / f'{item}d{longest:03d}.wav',
                           LABEL_DIR / f'{item}_scan.wav', longest)
        mapping[item] = {**row, 'anchor_seconds': round(anchor, 1),
                         'candidate_kind': classify(row),
                         'scan_snippets': n_snip}
        sheet.append(item)
        if (idx + 1) % 10 == 0:
            print(f'  {idx + 1}/{len(picked)} items cut')

    rng.shuffle(sheet)
    write_sheet(sheet, mapping, longest)

    (OUT_ROOT / 'truth_negatives.json').write_text(json.dumps({
        'seed': args.seed, 'durations': args.durations,
        'per_cluster_cap': args.per_cluster,
        'n_items': len(sheet),
        'expected_windows': len(sheet) * len(args.durations),
        'labels_applied': False,      # parse_negative_labels.py flips this
        'supply_report': {k: dict(v) for k, v in report.items()},
        'windows': windows,
    }, ensure_ascii=False, indent=1))

    print(f'\nwrote {len(windows)} windows to {WINDOW_DIR}')
    print(f"sheet {LABEL_DIR / 'LABELING_SHEET.md'} ({len(sheet)} rows)")
    print(f"sidecar {OUT_ROOT / 'truth_negatives.json'} — strata are UNSET "
          f'until scripts/parse_negative_labels.py runs')


if __name__ == '__main__':
    main()
