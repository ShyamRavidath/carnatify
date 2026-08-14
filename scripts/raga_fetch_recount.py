"""How much audio is ACTUALLY reachable? — the precondition for `handoff.md` §5.3

`handoff.md` §2e records 1,712 identified programme items as unfetched and says
in the same breath to **treat it as an optimistic ceiling, not a promised
corpus**. §5.3 then says: *"Recount reachable audio first — 1,712 is an
optimistic ceiling."* This is that recount, done **entirely offline** against
the 1,857 already-cached archive.org metadata files in
`data/raga_v2_cache/archive_metadata/`. No network, no downloads, no audio.

`data/RAGA_COVERAGE_CURVE.md` §10 is why the answer matters: the within-class
learning curve rises **+18.4 pp from 10 to 30 tracks per class with no
saturation anywhere**, every class in the corpus is capped at 30, and nobody has
seen where it bends. So the fetch is the best-value job on the board *if* the
audio exists. This counts whether it exists, per class.

## What "reachable" means, stated before any count

A cached mp3 is **reachable** if it can be attributed to a raga by one of the
two mechanisms the committed fetchers use, and **new** if no recording of that
(raga, title) pair is already on disk under `data/concert_audio/`.

  own-label   — the raga is in the file's own `title` or filename, resolved
                strictly through `data/raga_aliases.json`, never guessed from
                audio. Mirrors `download_targeted_deficits.py:parse_file`'s
                three label sources, using that module's own `norm`/`fold`/
                `vfold` matchers.
  title-join  — the filename matches a composition title that maps to exactly
                one canonical raga across every blog record. Uses
                `download_title_join.py`'s own `build_title_raga_map` and
                `tfold`, imported rather than reimplemented.

**This counts candidate recordings, not finished training tracks.** A fetched
file still has to survive download, Demucs, melodia, and the frozen
`v.size < 500` / `tonic <= 0` drops. The count below is therefore itself an
upper bound — a tighter one than 1,712, but an upper bound.

**Calibration check, reported before the headline:** the same pass counts how
many cached files resolve to a (raga, title) pair that IS already on disk. The
fetchers have put 1,238 files in `data/concert_audio`, so that number should
land in the same neighbourhood. If it does not, the attribution logic has
drifted from the fetchers' and the reachable count cannot be trusted either.

Read-only. Writes `data/raga_tier/fetch_recount.json`.

Usage: venv/bin/python scripts/raga_fetch_recount.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from normalize_ragas import fold  # noqa: E402
import download_title_join as TJ  # noqa: E402
from download_targeted_deficits import (  # noqa: E402  — the fetcher's matchers
    build_matchers, norm, vfold,
)

META_DIR = ROOT / 'data' / 'raga_v2_cache' / 'archive_metadata'
AUDIO_DIR = ROOT / 'data' / 'concert_audio'
CURVE = ROOT / 'data' / 'raga_coverage' / 'curve.json'
OUT = ROOT / 'data' / 'raga_tier' / 'fetch_recount.json'

DASH_SPLIT_RE = re.compile(r"\s+[–—-]\s+")
NUM_SEG_RE = re.compile(r"^\d{1,3}$")
EXCLUDE_FOLDS = {fold('Rāgamālika')}


def on_disk_pairs():
    """(raga_fold, title_fold) -> count, from data/concert_audio."""
    per = Counter()
    for d in sorted(AUDIO_DIR.iterdir()) if AUDIO_DIR.exists() else []:
        if d.is_dir():
            for mp3 in d.glob('*.mp3'):
                per[(fold(d.name), TJ.tfold(mp3.stem))] += 1
    return per


def main() -> None:
    a_norm, a_fold, a_vfold = build_matchers()
    title_map = TJ.build_title_raga_map()
    per_title = on_disk_pairs()
    tier54 = [r['raga'] for r in json.loads(CURVE.read_text())['per_class_min10']]
    tier_folds = {fold(r): r for r in tier54}

    def match_raga(seg: str):
        c = (a_norm.get(norm(seg)) or a_fold.get(fold(seg))
             or a_vfold.get(vfold(seg)))
        if c is None or '/' in c or fold(c) in EXCLUDE_FOLDS:
            return None
        return fold(c)

    def own_label(fobj):
        """`download_targeted_deficits.parse_file`'s three label sources."""
        title = fobj.get('title') or ''
        name = fobj.get('name', '')
        parts = [p for p in DASH_SPLIT_RE.split(title) if p]
        if len(parts) >= 2:
            r = match_raga(parts[1])
            if r:
                return r, parts[0]
        for text in (Path(name).stem, title):
            segs = [s for s in re.split(r'[-_]', text) if s and not NUM_SEG_RE.match(s)]
            for s in reversed(segs[1:]):
                r = match_raga(s)
                if r:
                    return r, segs[0]
        return None, None

    files = 0
    already = 0
    new_own, new_join = Counter(), Counter()
    new_pairs = defaultdict(set)

    for mp in sorted(META_DIR.glob('*.json')):
        try:
            objs = json.loads(mp.read_text())
        except Exception:
            continue
        if not isinstance(objs, list):
            continue
        for f in objs:
            name = f.get('name', '')
            if not name.lower().endswith('.mp3'):
                continue
            files += 1

            rf, comp = own_label(f)
            how = 'own_label' if rf else None
            if rf is None:
                raw = f.get('title') or Path(name).stem
                comp = DASH_SPLIT_RE.split(raw)[0]
                tf0 = TJ.tfold(comp)
                if len(tf0) >= TJ.MIN_TITLE_FOLD_LEN and tf0 in title_map:
                    canon = title_map[tf0]
                    if '/' not in canon and fold(canon) not in EXCLUDE_FOLDS:
                        rf, how = fold(canon), 'title_join'
            if rf is None:
                continue

            tf = TJ.tfold(comp or Path(name).stem)
            if per_title.get((rf, tf), 0) > 0:
                already += 1
                continue
            if tf in new_pairs[rf]:
                continue                      # same (raga,title) seen already
            new_pairs[rf].add(tf)
            (new_own if how == 'own_label' else new_join)[rf] += 1

    rows = []
    for rf, disp in tier_folds.items():
        n = new_own[rf] + new_join[rf]
        have = sum(c for (r, _), c in per_title.items() if r == rf)
        rows.append(dict(raga=disp, on_disk_recordings=have, reachable_new=n,
                         via_own_label=new_own[rf], via_title_join=new_join[rf]))
    rows.sort(key=lambda r: -r['reachable_new'])

    in_tier = sum(r['reachable_new'] for r in rows)
    off_tier = sum(v for k, v in (new_own + new_join).items() if k not in tier_folds)
    n_zero = sum(1 for r in rows if r['reachable_new'] == 0)
    n_thin = sum(1 for r in rows if r['reachable_new'] < 5)

    out = dict(
        mp3_files_in_cached_metadata=files,
        calibration_resolved_to_a_pair_already_on_disk=already,
        calibration_files_actually_on_disk=int(sum(per_title.values())),
        reachable_new_distinct_pairs_total=in_tier + off_tier,
        reachable_new_in_54_tier=in_tier,
        reachable_new_off_tier=off_tier,
        classes_with_zero_reachable=n_zero,
        classes_with_under_5_reachable=n_thin,
        optimistic_ceiling_in_handoff=1712,
        per_class=rows,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')

    print(f"mp3 files in cached archive.org metadata      {files:6d}")
    print(f"CALIBRATION: resolve to a pair already on disk {already:6d}")
    print(f"             files actually in concert_audio   "
          f"{out['calibration_files_actually_on_disk']:6d}")
    print(f"\nreachable NEW distinct (raga, title) pairs    "
          f"{out['reachable_new_distinct_pairs_total']:6d}")
    print(f"  in the 54-class tier                        {in_tier:6d}")
    print(f"  off-tier (would add new classes)            {off_tier:6d}")
    print(f"  handoff's optimistic ceiling                  1712")
    print(f"\nclasses with 0 reachable: {n_zero}/54   with <5: {n_thin}/54")
    print(f"\n{'raga':24s} {'disk':>5s} {'new':>5s} {'own':>5s} {'join':>5s}")
    for r in rows[:15]:
        print(f"{r['raga']:24s} {r['on_disk_recordings']:5d} {r['reachable_new']:5d} "
              f"{r['via_own_label']:5d} {r['via_title_join']:5d}")
    print('  ...')
    for r in rows[-10:]:
        print(f"{r['raga']:24s} {r['on_disk_recordings']:5d} {r['reachable_new']:5d} "
              f"{r['via_own_label']:5d} {r['via_title_join']:5d}")
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
