#!/usr/bin/env python3
"""Cut the duration-probe window set from data/concert_audio.

Settles P1 (HANDOFF_SESSION_0725 §7 Approach A): does listening length explain
the 30-60s collapse, with everything else held constant?

**Scope, corrected 2026-07-26 after red-team review** (`CODEX_DURATION_PROBE_
REVIEW.md`): this probe is about the **lyrics matcher only**. The 60-67%
full-recording number that motivated P1 came from *Qmax*, and `ARCHITECTURE.md:72`
records Qmax at **0%** on wild clips, while the 8-13/78 wild number is the lyrics
matcher — comparing them and attributing the gap to duration is the
matcher-identity confound already logged at `AGENT_LOG.md:2396`. Qmax cannot be
probed on this pool at all: `models/qmax_catalog.npz` is built *from*
`concert_audio` melodia, so every window would be same-recording leakage.

Design notes that cost something to establish, do not silently change them:

* **One recording per title is enough.** The lyrics channel matches transcripts
  against the TEXT registry, not against a pool of other recordings, so the
  "65 titles with 2+ renditions" constraint in the handoff was borrowed from the
  CSI setup and does not bind here.

* **Truth is resolved here, not by identify_clip.py.** The evaluator reads
  `data/wild_truth_manifest.json` keyed by clip stem, which covers ~/sung_tests
  only. Window filenames therefore deliberately contain NO `__`, so
  identify_clip.py skips truth-matching entirely (it only attempts it when
  `'__' in p.stem`). Scoring joins this script's sidecar against `--json`
  output. Nothing in the scoreboard path is edited.

* **`--cache-v2` is keyed by `audio_sha256`, not by filename** (`identify_v2`,
  ~L804). The handoff's warning about `path.name` collisions applies to the
  LEGACY `transcribe()` path (~L619) and not to the probe. Distinct basenames
  are kept anyway as cheap insurance.

* **Common random anchor, nested durations** (corrected: the first version drew
  an independent offset per duration, which estimates "an independently drawn
  random N-second excerpt" and does NOT estimate progressive listening from one
  user start — it also let the 30s and 300s windows sample different sections
  entirely). One uniform random anchor per title, then nested prefixes from that
  anchor, is what the product actually does. The objection to nesting only ever
  applied to a **zero** start, because items open with alapana, which is
  lyric-free by definition. A random anchor answers that without breaking the
  estimand. `--arm prefix` keeps the zero-start variant as a named secondary.

* **90s is a required condition**, not an optional one: the product target is
  five-minute accuracy in 90 seconds or less (HANDOFF_SESSION_0725 §1).

Windows are written as 16 kHz mono WAV so preprocessing is byte-identical
across durations and the only thing varying is length.

Run:
  venv_train/bin/python scripts/duration_probe_cut.py --n 60 --arm anchored
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

from identify_clip import fold, load_targets, skey  # noqa: E402
from duration_probe_titles import (NON_COMP, manifest_rows,  # noqa: E402
                                   primary_title, registry_index,
                                   reviewed_aliases)

AUDIO = ROOT / 'data' / 'concert_audio'
REGISTRY = ROOT / 'data' / 'composition_registry.json'
MANIFEST = AUDIO / 'download_manifest.json'
OUT_ROOT = ROOT / 'data' / 'duration_probe'
DURATIONS = (30, 60, 90, 180, 300)
SEED = 20260725
MIN_PALLAVI_CHARS = 25   # below this a shared opening is not evidence of a family

# Title extraction moved to scripts/duration_probe_titles.py on 2026-07-28.
# The old local `NUM_PREFIX = ^\d{1,3}` stripped only three digits, so
# seven-digit Jamendo ids survived into the title and their registry lookups
# failed for reasons unrelated to the audio — which is how three in-catalog
# works ended up counted as OOC negatives (`CODEX_NEGATIVE_ARM_REVIEW.md` §2).


def ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def title_key(path: Path) -> tuple[str, str, str]:
    """(title, skey, provenance) for one audio file.

    The filename is used unless it is demonstrably not a title, in which case
    `download_manifest.json`'s `file_title_raw` supplies it. See
    `duration_probe_titles.primary_title`.
    """
    rel = str(path.relative_to(ROOT))
    raw = (manifest_rows().get(rel) or {}).get('file_title_raw')
    title, prov = primary_title(path.stem, raw)
    return title, skey(title), prov


def archive_ids() -> dict[str, str]:
    """file_path -> archive_identifier, the real independent sampling unit.

    Several tracks come from one archive concert; treating them as independent
    titles would understate uncertainty in the paired analysis downstream.
    """
    if not MANIFEST.exists():
        return {}
    return {row['file_path']: row.get('archive_identifier')
            for row in json.loads(MANIFEST.read_text())
            if row.get('file_path')}


def build_pool(min_duration: float, report: dict) -> list[dict]:
    """Titles resolving to exactly one WORK (not exactly one registry row).

    Corrections applied after red-team review:
      1. `_rN` rendition suffixes are stripped (136 of 1,238 files carry one);
         previously their keys contained `r2`/`r3` and could never resolve.
      2. Candidate rows are deduplicated **by registry id**. Previously a row
         with two aliases folding to the same key appeared twice and was
         wrongly called ambiguous.
      3. Truth is a work-FAMILY id set, not one arbitrary row. This project has
         verified same-kriti duplicate rows (`AGENT_LOG.md:1948`), and the live
         matcher loads every registry row, not only lyrics-bearing ones
         (`identify_clip.py:281-296`) — so a lyrics-less truncation of the same
         kriti must count as a hit, exactly as the reviewed wild-truth manifest
         already does for `entara`.
      4. The LONGEST rendition is used, not the lexicographically first.

    A title is accepted only if all its lyrics-bearing rows agree on their
    lyrics head — that is the mechanical form of the same test used in the
    reviewed equivalences (identical pallavi). Disagreement means two genuinely
    different works share a title, which is reviewed judgment, not guessable,
    so it is dropped. Registry raga metadata is NOT used to disambiguate: the
    registry contains junk rows whose `ragas` field holds dates (`comp00000` is
    a street address with raga "Sept 13, 1997").
    """
    registry = json.loads(REGISTRY.read_text())
    entries, _ = load_targets()
    # Per-ROW lyric evidence. `lyr` alone is useless as an equivalence test:
    # load_targets looks it up by folded TITLE (`identify_clip.py:262-267`), so
    # every row sharing a title gets a byte-identical head by construction and
    # the test can never fail. `lines` comes from that row's own karnatik pages
    # and does discriminate; prefer it, fall back to `lyr`.
    # `lines` are dicts {'f','section','page','i'} (`identify_clip.py:187`).
    # Prefer the pallavi line: identical pallavi is exactly the criterion used
    # in the reviewed work-family equivalences at `AGENT_LOG.md:1948`.
    head_by_id = {}
    for e in entries:
        lines = e.get('lines') or []
        pallavi = next((ln['f'] for ln in lines
                        if ln.get('section') == 'pallavi' and ln.get('f')), '')
        first = next((ln['f'] for ln in lines if ln.get('f')), '')
        head_by_id[e['id']] = pallavi or first or fold(e.get('lyr') or '')

    # Work-family index on PALLAVI IDENTITY, across the whole registry.
    # Expanding families within a shared title key finds nothing (measured: 0
    # cases) because real families differ in title -- the verified pair at
    # `AGENT_LOG.md:1948` is comp00173 "akilAndEswari" and comp00175
    # "akhilANDEshvari rakSamAm", which fold to different keys. Identical
    # pallavi is the criterion those reviewed equivalences actually used.
    # Guards against over-merging on short or generic openings: a minimum
    # pallavi length, and composer agreement where both rows name one.
    comp_by_id = {r['id']: set(r.get('composers') or []) for r in registry}
    fam_by_pallavi: dict[str, list[str]] = defaultdict(list)
    for rid, head in head_by_id.items():
        if len(head) >= MIN_PALLAVI_CHARS:
            fam_by_pallavi[head].append(rid)

    def family(rid: str) -> list[str]:
        head = head_by_id.get(rid, '')
        sibs = fam_by_pallavi.get(head, [rid])
        mine = comp_by_id.get(rid, set())
        out = [rid]
        for s in sibs:
            if s == rid:
                continue
            theirs = comp_by_id.get(s, set())
            if mine and theirs and not (mine & theirs):
                continue          # same words, different composer: not merged
            out.append(s)
        return sorted(set(out))

    rows_by_key, _ = registry_index()          # id-deduped, shared with the
    rows_by_id = {r['id']: r for r in registry}  # negative-arm builder
    aliases = reviewed_aliases()

    titles: dict[str, list] = defaultdict(list)
    provenance = Counter()
    for p in sorted(AUDIO.rglob('*.mp3')):
        title, key, prov = title_key(p)
        provenance[prov] += 1
        if key and key not in NON_COMP:
            titles[key].append((title, p.parent.name, p, prov))
    report['distinct_title_keys'] = len(titles)
    report['title_provenance'] = dict(provenance)

    arch = archive_ids()
    pool, buckets = [], defaultdict(int)
    audit: list[dict] = []          # one row per title key, for bias analysis
    n_tracks_by_id = {r['id']: r.get('n_tracks', 0) for r in registry}
    lines_by_id = {e['id']: len(e.get('lines') or []) for e in entries}

    def note(key, bucket, items, cands=(), duration=None):
        ids = [r['id'] for r in cands]
        audit.append({
            'key': key, 'bucket': bucket,
            'n_renditions': len(items),
            'title_chars': len(key),
            'source_duration': duration,
            'n_registry_rows': len(ids),
            'n_tracks': max([n_tracks_by_id.get(i, 0) for i in ids] or [0]),
            'n_lyric_lines': max([lines_by_id.get(i, 0) for i in ids] or [0]),
            'pallavi_chars': max([len(head_by_id.get(i, '')) for i in ids]
                                 or [0]),
        })

    for key, items in titles.items():
        cands = list(rows_by_key.get(key, {}).values())
        if not cands and key in aliases:
            # hand-reviewed transliteration variant; the only non-exact route
            # into TRUTH, and every row of it is a human decision on record.
            row = rows_by_id.get(aliases[key])
            cands = [row] if row else []
        if not cands:
            buckets['no_registry_match'] += 1
            note(key, 'no_registry_match', items)
            continue
        lyric_rows = [r for r in cands if r.get('has_lyrics')]
        if not lyric_rows:
            buckets['matched_but_no_lyrics'] += 1
            note(key, 'matched_but_no_lyrics', items, cands)
            continue
        heads = {head_by_id.get(r['id'], '')[:120] for r in lyric_rows}
        heads.discard('')
        if len(heads) > 1:
            buckets['conflicting_works_same_title'] += 1
            note(key, 'conflicting_works_same_title', items, cands)
            continue
        if not heads:
            buckets['lyrics_flagged_but_absent'] += 1
            note(key, 'lyrics_flagged_but_absent', items, cands)
            continue

        # longest rendition, not items[0]
        scored = []
        for title, raga, p, prov in items:
            scored.append((ffprobe_duration(p), title, raga, p, prov))
        duration, title, raga, path, prov = max(scored, key=lambda x: x[0])
        if duration < min_duration:
            buckets['too_short'] += 1
            note(key, 'too_short', items, cands, duration)
            continue

        rel = str(path.relative_to(ROOT))
        truth_ids = sorted({i for r in cands for i in family(r['id'])}
                           | {r['id'] for r in cands})
        pool.append({
            'key': key, 'title': title, 'raga': raga,
            'title_provenance': prov,
            'truth_ids': truth_ids,
            'n_truth_ids': len(truth_ids),
            'family_expanded': len(truth_ids) > len(cands),
            'source': rel,
            'archive_identifier': arch.get(rel),
            'source_duration': round(duration, 1),
            'n_renditions': len(items),
            'lyrics_head_len': len(next(iter(heads))),
            # stratifier: works with more matchable lines give a long window
            # more chances to win the per-entry max (red-team P1)
            'n_lyric_lines': max([lines_by_id.get(i, 0) for i in truth_ids]
                                 or [0]),
        })
        buckets['RESOLVED'] += 1
        note(key, 'RESOLVED', items, cands, duration)

    report['buckets'] = dict(buckets)
    report['audit'] = audit
    pool.sort(key=lambda x: x['key'])
    return pool


def cut(src: Path, start: float, length: int, dest: Path) -> bool:
    """16 kHz mono WAV window. `-ss` before `-i` for fast seek."""
    r = subprocess.run(
        ['ffmpeg', '-nostdin', '-v', 'error', '-y',
         '-ss', f'{start:.3f}', '-i', str(src), '-t', str(length),
         '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(dest)],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f'  ffmpeg failed on {src.name}: {r.stderr.strip()[:120]}',
              file=sys.stderr)
        return False
    return True


# `cut_negatives` was removed 2026-07-28. It cut the scored windows AFTER the
# labels came back, from an anchor unrelated to the labeling excerpts, so five
# labeled items described audio the pipeline never saw
# (`CODEX_NEGATIVE_ARM_REVIEW.md` §4). The negative arm now cuts windows first
# and draws its labeling audio from inside the selected 300s window:
# scripts/build_negative_arm.py.


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=60)
    ap.add_argument('--arm', choices=('anchored', 'prefix'), default='anchored',
                    help='anchored = one random anchor per title, nested '
                         'durations (primary). prefix = zero start (secondary)')
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--durations', type=int, nargs='+', default=list(DURATIONS))
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    min_needed = max(args.durations)
    print(f'building pool (>= {min_needed}s, ffprobe over concert_audio) ...')
    report: dict = {}
    pool = build_pool(min_needed, report)

    print(f"\n=== POOL CONSTRUCTION (distinct title keys: "
          f"{report['distinct_title_keys']}) ===")
    for k, v in sorted(report['buckets'].items(), key=lambda x: -x[1]):
        print(f'  {k:32s} {v}')
    fam = sum(1 for i in pool if i['family_expanded'])
    clusters = {i['archive_identifier'] for i in pool if i['archive_identifier']}
    print(f'\nresolved pool: {len(pool)} titles')
    print(f'  {fam} carry a work-family id set (>1 registry row)')
    print(f'  {len(clusters)} distinct archive clusters '
          f"({sum(1 for i in pool if not i['archive_identifier'])} unknown)")

    rng = random.Random(args.seed)
    sample = pool if args.n >= len(pool) else rng.sample(pool, args.n)
    sample.sort(key=lambda x: x['key'])
    total = len(sample) * sum(args.durations)
    print(f'\nsampling {len(sample)} titles x {len(args.durations)} windows '
          f'= {len(sample) * len(args.durations)} clips, {total / 3600:.1f} h '
          f'unique audio ({total * 7 / 3600:.0f} whisper-hours at the '
          f'7-pass product config, plus Demucs)')
    if args.dry_run:
        # A dry run must not touch the tree. This used to regenerate
        # pool_report.json, so the red team's one ostensibly read-only command
        # mutated staged state (`CODEX_NEGATIVE_ARM_REVIEW_R2.md`, closing
        # note). Reviewers have to be able to inspect without side effects.
        print(json.dumps({'report': report, 'pool': pool}, ensure_ascii=False,
                         indent=1))
        print('\n(dry run — nothing written. Redirect stdout to keep this, or '
              'run without --dry-run to refresh pool_report.json.)',
              file=sys.stderr)
        return
    (OUT_ROOT).mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / 'pool_report.json').write_text(json.dumps(
        {'report': report, 'pool': pool}, ensure_ascii=False, indent=1))
    print(f"wrote {OUT_ROOT / 'pool_report.json'}")

    out_dir = OUT_ROOT / args.arm
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest, written, failed = {}, 0, 0

    for idx, item in enumerate(sample):
        src = ROOT / item['source']
        # ONE anchor per title; every duration nests from it.
        span = max(0.0, item['source_duration'] - max(args.durations))
        anchor = 0.0 if args.arm == 'prefix' else rng.uniform(0, span)
        for dur in args.durations:
            stem = f'probe{idx:04d}d{dur:03d}{args.arm[0]}'
            dest = out_dir / f'{stem}.wav'
            if not cut(src, anchor, dur, dest):
                failed += 1
                continue
            manifest[stem] = {**item, 'window_seconds': dur,
                              'anchor_seconds': round(anchor, 1),
                              'arm': args.arm}
            written += 1
        if (idx + 1) % 10 == 0:
            print(f'  {idx + 1}/{len(sample)} titles cut')

    sidecar = OUT_ROOT / f'truth_{args.arm}.json'
    sidecar.write_text(json.dumps(
        {'seed': args.seed, 'arm': args.arm, 'durations': args.durations,
         'n_titles': len(sample), 'expected_windows': len(sample) * len(args.durations),
         'pool_report': report, 'windows': manifest},
        ensure_ascii=False, indent=1))
    print(f'\nwrote {written} windows to {out_dir}'
          + (f' ({failed} failed)' if failed else ''))
    print(f'wrote truth sidecar {sidecar}')


if __name__ == '__main__':
    main()
