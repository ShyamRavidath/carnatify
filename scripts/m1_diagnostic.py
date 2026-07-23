"""M1 rank/coverage diagnostic on the ASR-usable auto-fetched clips.

For every auto-fetched (fetch_manifest.tsv) in-catalog clip whose v2-cache
fold-view transcript passes the usability gates, report: which variant was
picked, the truth entry's rank in the full candidate list, the truth entry's
winning channel (title / pallavi / other), and the top-1 prediction. Summary:
truth retrieved at ranks 1/5/20/100, split by channel.

Read-only; run before/after a matcher change:
  venv_train/bin/python scripts/m1_diagnostic.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import identify_clip as ic  # noqa: E402

AUDIO_EXTS = ('.wav', '.mp3', '.m4a', '.flac')
RANKS = (1, 5, 20, 100)


def truth_match(pred_title: str, gt: str) -> bool:
    a, b = ic.skey(pred_title), ic.skey(gt)
    return ic._partial(a, b) >= 90 or ic._partial(b, a) >= 90


def usable_variants(entry) -> dict[str, str]:
    """The policy's usability gates, minus the answer-score threshold."""
    out = {}
    for name, txt in ic.variants_from_v2(entry, view=ic.fold).items():
        txt = ic.HALLUC.sub(' ', txt or '')
        if len(txt.replace(' ', '')) < ic.MIN_TRANSCRIPT_CHARS:
            continue
        if ic._max_token_run(txt) >= ic.LOOP_RUN:
            continue
        out[name] = txt
    return out


def main() -> None:
    folder = Path.home() / 'sung_tests'
    manifest = {l.split('\t')[0] for l in
                (folder / 'fetch_manifest.tsv').read_text().splitlines()}
    clips = [p for p in sorted(folder.iterdir())
             if p.suffix.lower() in AUDIO_EXTS and p.name in manifest
             and not p.stem.endswith('__OOC')]
    targets, lyr = ic.load_targets()
    cache2 = ic.load_cache_v2()
    n_dead = 0
    rows = []
    for p in clips:
        entry = cache2['entries'].get(ic.cache2_key(ic.audio_sha256(p)))
        if entry is None:
            print(f'!! v2 cache MISS {p.name}', file=sys.stderr)
            continue
        variants = usable_variants(entry)
        cands = []
        for name, txt in variants.items():
            comps, max_rep = ic.match_lyrics(txt, targets, lyr)
            if not comps or max_rep < 2:
                continue
            cands.append((comps[0]['score'], name.startswith('stem'),
                          name, txt))
        if not cands:
            n_dead += 1
            continue
        best = max(c[0] for c in cands)
        strong = [c for c in cands if c[0] >= best - ic.VARIANT_CLOSE]
        vocal = [c for c in strong if c[1]]
        _, _, vname, txt = max(vocal or strong, key=lambda c: c[0])
        gt_title = p.stem.split('__', 1)[0]
        comps, _ = ic.match_lyrics(txt, targets, lyr, topn=100, detail=True)
        rank = channel = None
        for i, c in enumerate(comps, 1):
            if truth_match(c['title'], gt_title):
                rank, channel = i, c['channel']
                break
        rows.append((p.name, vname, rank, channel,
                     comps[0]['title'], comps[0]['channel']))
    print(f'auto-fetched in-catalog: {len(clips)}  '
          f'ASR-usable: {len(rows)}  gate-dead: {n_dead}')
    print(f'\n{"clip":44s} {"var":10s} {"truth@":>7s} {"chan":8s} top-1 (chan)')
    for name, vn, rank, ch, t1, t1ch in rows:
        r = str(rank) if rank else '>100'
        print(f'{name[:44]:44s} {vn:10s} {r:>7s} {ch or "-":8s} '
              f'{t1[:30]} ({t1ch})')
    print('\ntruth retrieved (cumulative):')
    for r in RANKS:
        hit = [x for x in rows if x[2] and x[2] <= r]
        bych = {}
        for x in hit:
            bych[x[3]] = bych.get(x[3], 0) + 1
        print(f'  top-{r:<4d} {len(hit)}/{len(rows)}   by channel: '
              + (', '.join(f'{k}={v}' for k, v in sorted(bych.items()))
                 or '-'))


if __name__ == '__main__':
    main()
