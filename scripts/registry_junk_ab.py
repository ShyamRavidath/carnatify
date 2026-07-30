#!/usr/bin/env python3
"""A/B the registry junk-row blocklist on the frozen wild set.

Removing rows from the catalog is behaviour-changing even when the removed
rows never win: `_vocab_idf` derives its IDF weights from the entry count and
the per-token document frequency, so dropping 19 of 8,688 rows perturbs every
score slightly.  `registry_junk_blocklist_DRAFT.md` asserts the change is
cosmetic; this script is the measurement that either backs that up or kills it.

Three passes over the same clips through the SAME policy entry point the CLI
uses (`identify_clip.assess_variants` on `variants_from_v2`), differing only in
which registry rows are in `targets`:

    baseline      full registry (what the scoreboard reports today)
    drop          minus the reviewed status=drop rows
    drop+review   minus every row the detector flags (the maximal blocklist)

Whisper backend only -- it is the product default, the cheapest pass, and the
IDF perturbation it sees is identical for every backend.

Run (~20 min, three matcher passes; see handoff §4.8/§4.9):
    caffeinate -i venv_train/bin/python -u scripts/registry_junk_ab.py \\
        ~/sung_tests > ab.txt 2>&1
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))          # root before backend/ (handoff §4.13)
sys.path.insert(0, str(ROOT / 'scripts'))

import identify_clip as ic             # noqa: E402
import registry_junk_filter as rj      # noqa: E402


def score_pass(files, targets, lyr, cache2, wild) -> dict:
    """Per-clip top-5 ids + the scoreboard aggregates for one target set."""
    per_clip = {}
    c1 = c5 = n = ooc_n = ooc_bluff = answered_in = 0
    for p in files:
        entry = cache2['entries'].get(ic.cache2_key(ic.audio_sha256(p)))
        variants = ic.variants_from_v2(entry) if entry else {}
        res = ic.assess_variants(variants, targets, lyr)
        comps = res['compositions']
        ids = [c.get('id') for c in comps]
        answered = res['composition_confidence'] != 'none' and bool(comps)

        stem = unicodedata.normalize('NFC', p.stem)
        is_ooc = stem.endswith('__OOC')
        if is_ooc:
            stem = stem[: -len('__OOC')]
        per_clip[stem + ('__OOC' if is_ooc else '')] = {
            'ids': ids, 'answered': answered,
            'tier': res['composition_confidence'],
            'top': comps[0]['score'] if comps else 0.0,
            'titles': [c['title'] for c in comps]}

        if is_ooc:
            ooc_n += 1
            ooc_bluff += answered
            continue
        n += 1
        answered_in += answered
        truth = set(wild.get(stem, {}).get('truth_ids', []))
        c1 += bool(ids) and ids[0] in truth
        c5 += any(i in truth for i in ids)

    answered_all = answered_in + ooc_bluff
    return {'per_clip': per_clip, 'n': n, 'ooc_n': ooc_n, 'c1': c1, 'c5': c5,
            'ooc_bluff': ooc_bluff, 'answered': answered_all,
            'total': n + ooc_n}


def report(label: str, s: dict) -> None:
    prec = 100.0 * s['c1'] / s['answered'] if s['answered'] else 0.0
    cov = 100.0 * s['answered'] / s['total'] if s['total'] else 0.0
    print(f"\n===== {label} =====")
    print(f"composition top-1 {s['c1']}/{s['n']}  top-5 {s['c5']}/{s['n']}")
    print(f"OOC reject  {s['ooc_n'] - s['ooc_bluff']}/{s['ooc_n']}  "
          f"(bluffs: {s['ooc_bluff']})")
    print(f"precision@coverage: {s['c1']}/{s['answered']} correct "
          f"({prec:.0f}% precision at {cov:.0f}% coverage)")


def diff(base: dict, other: dict, label: str) -> None:
    """Every clip whose answer or top-5 moved, plus a one-line verdict."""
    moved = []
    for stem, b in base['per_clip'].items():
        o = other['per_clip'][stem]
        if b['ids'] != o['ids'] or b['answered'] != o['answered']:
            moved.append((stem, b, o))
    print(f"\n--- {label}: per-clip diff vs baseline ---")
    if not moved:
        print("  no clip changed answer or top-5 ordering")
    for stem, b, o in moved:
        print(f"  {stem[:52]}")
        print(f"    base  {b['tier']:<6} {b['top']:.3f}  {b['ids']}")
        print(f"    after {o['tier']:<6} {o['top']:.3f}  {o['ids']}")
    same = all(base[k] == other[k] for k in ('c1', 'c5', 'ooc_bluff',
                                             'answered'))
    print(f"  verdict: scoreboard {'UNCHANGED' if same else 'MOVED'}; "
          f"{len(moved)} clip(s) with a top-5 change")


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1
                  else '~/sung_tests').expanduser()
    files = sorted(p for p in target.iterdir()
                   if p.suffix.lower() in ('.wav', '.mp3', '.m4a', '.flac'))
    if not files:
        sys.exit(f'no audio files at {target}')

    targets, lyr = ic.load_targets()
    cache2 = ic.load_cache_v2('whisper')
    wild = {unicodedata.normalize('NFC', k): v
            for k, v in json.loads(ic.WILD_TRUTH.read_text()).items()}

    drop = rj.blocklist_ids('drop')
    review = rj.blocklist_ids('review')
    have = {e.get('id') for e in targets}
    print(f"clips {len(files)}  |  registry entries in matcher {len(targets)}")
    print(f"blocklist: drop {len(drop)} ({len(drop & have)} present in "
          f"targets), review {len(review)} ({len(review & have)} present)")

    sets = [('baseline (full registry)', targets),
            ('drop only', rj.filter_targets(targets, drop)),
            ('drop + review', rj.filter_targets(targets, drop | review))]
    scored = []
    for label, tgt in sets:
        print(f"\nscoring: {label}  ({len(tgt)} entries) ...", flush=True)
        s = score_pass(files, tgt, lyr, cache2, wild)
        report(label, s)
        scored.append((label, s))

    # Does junk ever reach a user at all? The DRAFT claims these rows surface
    # only at score ~0.0, below MIN_ANSWER_SCORE. Count it rather than assume.
    base = scored[0][1]
    flagged = drop | review
    print("\n--- baseline occupancy of flagged rows ---")
    seen = 0
    for stem, c in base['per_clip'].items():
        hit = [(i, t) for i, t in zip(c['ids'], c['titles']) if i in flagged]
        if hit:
            seen += 1
            print(f"  {stem[:52]}  answered={c['answered']} "
                  f"tier={c['tier']} top={c['top']:.3f}")
            for i, t in hit:
                print(f"    rank {c['ids'].index(i) + 1}: {i} {t[:44]!r}")
    print(f"  {seen} clip(s) show a flagged row anywhere in top-5")

    for label, s in scored[1:]:
        diff(scored[0][1], s, label)


if __name__ == '__main__':
    main()
