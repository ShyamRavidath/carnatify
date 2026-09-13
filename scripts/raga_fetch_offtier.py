"""Off-tier fetch check: would reachable audio bring any raga over the admission line?

August handoff §6-E: 185 reachable (raga, title) pairs attach to ragas below
the tier. This recomputes reachability for EVERY raga the fetchers can resolve,
then joins it to the reference candidate's actual 69-class support and the
overhaul's admission threshold. Entirely offline against the cached archive.org
metadata; no download, no audio, no model.

Usage: venv/bin/python scripts/raga_fetch_offtier.py
"""
from __future__ import annotations
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from normalize_ragas import fold
import download_title_join as TJ
from download_targeted_deficits import build_matchers, norm, vfold
from scripts.raga_fetch_recount import (META_DIR, DASH_SPLIT_RE, NUM_SEG_RE, EXCLUDE_FOLDS,
                                        on_disk_pairs)

ADMISSION_MIN_TRACKS = 5   # the overhaul's broader admission rule
TALA_WORDS = {'adi', 'aadi', 'adhi', 'rupakam', 'rupaka', 'misrachapu', 'khandachapu', 'chapu', 'tisra', 'khanda', 'misra'}
REFERENCE = ROOT / 'data/overhaul/context180_recovered_experiment/training/raga.json'
OUT = ROOT / 'data/raga_tier/fetch_recount_offtier.json'


def main():
    a_norm, a_fold, a_vfold = build_matchers()
    title_map = TJ.build_title_raga_map()
    per_title = on_disk_pairs()
    display = {}

    def match_raga(seg):
        # The fetchers' vowel-folded matcher maps the tala word 'Adi' onto the
        # raga Pāḍi (93 false hits in the cached metadata). Tala words are not
        # raga evidence; they are excluded here and the bug is noted in the
        # report. The August in-tier recount was unaffected (Pāḍi is off-tier).
        if fold(seg) in TALA_WORDS:
            return None
        c = a_norm.get(norm(seg)) or a_fold.get(fold(seg)) or a_vfold.get(vfold(seg))
        if c is None or '/' in c or fold(c) in EXCLUDE_FOLDS:
            return None
        display.setdefault(fold(c), c)
        return fold(c)

    def own_label(fobj):
        title = fobj.get('title') or ''
        name = fobj.get('name', '')
        parts = [p for p in DASH_SPLIT_RE.split(title) if p]
        if len(parts) >= 2:
            r = match_raga(parts[1])
            if r: return r, parts[0]
        for text in (Path(name).stem, title):
            segs = [s for s in re.split(r'[-_]', text) if s and not NUM_SEG_RE.match(s)]
            for s in reversed(segs[1:]):
                r = match_raga(s)
                if r: return r, segs[0]
        return None, None

    new = Counter(); new_pairs = defaultdict(set); files = 0
    for mp in sorted(META_DIR.glob('*.json')):
        try: objs = json.loads(mp.read_text())
        except Exception: continue
        if not isinstance(objs, list): continue
        for f in objs:
            name = f.get('name', '')
            if not name.lower().endswith('.mp3'): continue
            files += 1
            rf, comp = own_label(f)
            if rf is None:
                raw = f.get('title') or Path(name).stem
                comp = DASH_SPLIT_RE.split(raw)[0]
                tf0 = TJ.tfold(comp)
                if len(tf0) >= TJ.MIN_TITLE_FOLD_LEN and tf0 in title_map:
                    canon = title_map[tf0]
                    if '/' not in canon and fold(canon) not in EXCLUDE_FOLDS:
                        rf = fold(canon); display.setdefault(rf, canon)
            if rf is None: continue
            tf = TJ.tfold(comp or Path(name).stem)
            if per_title.get((rf, tf), 0) > 0 or tf in new_pairs[rf]: continue
            new_pairs[rf].add(tf); new[rf] += 1

    on_disk = Counter()
    for (r, _), c in per_title.items(): on_disk[r] += c
    ref = json.loads(REFERENCE.read_text())
    support = {fold(k): v['n_tracks'] for k, v in ref['class_support'].items()}
    ref_display = {fold(k): k for k in ref['class_support']}
    rows = []
    for rf in sorted(set(new) | set(on_disk) | set(support)):
        rows.append(dict(raga=ref_display.get(rf) or display.get(rf) or rf,
                         in_reference_vocabulary=rf in support,
                         reference_training_tracks=support.get(rf, 0),
                         on_disk_recordings=on_disk.get(rf, 0),
                         reachable_new=new.get(rf, 0)))
    off = [r for r in rows if not r['in_reference_vocabulary']]
    crossing = [r for r in off if r['on_disk_recordings'] + r['reachable_new'] >= ADMISSION_MIN_TRACKS]
    thin = [r for r in rows if r['in_reference_vocabulary'] and r['reference_training_tracks'] < 10]
    thin_gain = [r for r in thin if r['reachable_new'] > 0]
    out = dict(status='offline reachability arithmetic; upper bound on candidate recordings, not trained tracks',
               matcher_bug_noted='download_targeted_deficits vowel-folded matcher maps the tala word Adi to raga Pāḍi; excluded here',
               mp3_files_in_cached_metadata=files, admission_min_tracks=ADMISSION_MIN_TRACKS,
               reference_classes=len(support),
               off_vocabulary_ragas_with_reachable_audio=sum(1 for r in off if r['reachable_new']),
               off_vocabulary_reachable_pairs=sum(r['reachable_new'] for r in off),
               off_vocabulary_ragas_that_would_cross_admission=len(crossing),
               crossing=sorted(crossing, key=lambda r: -(r['on_disk_recordings'] + r['reachable_new'])),
               thin_in_vocabulary_classes=len(thin), thin_classes_with_reachable_audio=len(thin_gain),
               thin=sorted(thin, key=lambda r: -r['reachable_new']),
               per_raga=sorted(rows, key=lambda r: -r['reachable_new']))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k not in ('per_raga', 'thin', 'crossing')}, indent=1))
    print('\nwould cross admission (on disk + reachable >= %d):' % ADMISSION_MIN_TRACKS)
    for r in out['crossing']: print(f"  {r['raga']:24s} disk {r['on_disk_recordings']:3d} reachable {r['reachable_new']:3d}")
    print('\nthin in-vocabulary classes (<10 training tracks) with reachable audio:')
    for r in thin_gain: print(f"  {r['raga']:24s} train {r['reference_training_tracks']:3d} disk {r['on_disk_recordings']:3d} reachable {r['reachable_new']:3d}")


if __name__ == '__main__':
    main()
