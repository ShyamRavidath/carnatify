"""Build the canonical composition registry (title hygiene + alias merge).

Sources: models/qmax_catalog_meta.json titles + data/lyrics.db titles
  + data/karnatik_lyrics.json (scrape_karnatik.py — titles, ragas, full
  lyric text and meanings for ~8k songs).
Output: data/composition_registry.json —
  [{id, canonical, aliases, ragas, composers, has_lyrics, n_tracks,
    karnatik_pages}]
karnatik_pages links an entry to its lyric records in karnatik_lyrics.json
(the matcher loads lyric text from there; the registry stays title-sized).

Cleaning: strips leading track numbers / timestamps, drops uploader-junk and
too-short titles. Merging: soft-phonetic key + fuzzy >= 88 (same fold the
matcher and truth scoring use). Canonical display = longest alias that isn't
all-lowercase-mush, ties to the lyrics.db spelling (curated source).

Run: venv_train/bin/python build_composition_registry.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).parent

JUNK_PAT = re.compile(
    r'^(rtp|ssi|tani|thani( avartanam)?|mangalam)$'
    r'|imcpresents|music ncbs|in memoriam|melakartha chakkaram',
    re.I)
STRIP_PAT = re.compile(
    r'^\s*\d+(:\d+){1,2}\s*'      # leading 1:32:39 timestamps
    r'|^\s*\d{2,}\s+'             # leading track/upload numbers
    r'|\s*\((viruttham|slokam|varnam)\)\s*$', re.I)


def fold(s: str) -> str:
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 ]', '', t.lower())


def soft(s: str) -> str:
    for a, b in [('aa', 'a'), ('ee', 'i'), ('ii', 'i'), ('oo', 'u'),
                 ('uu', 'u'), ('bh', 'b'), ('ch', 'c'), ('dh', 'd'),
                 ('gh', 'g'), ('jh', 'j'), ('kh', 'k'), ('ph', 'p'),
                 ('sh', 's'), ('th', 't'), ('w', 'v'), ('z', 's')]:
        s = s.replace(a, b)
    return s


def skey(s: str) -> str:
    return soft(fold(s).replace(' ', ''))


def clean_title(raw: str) -> str | None:
    t = STRIP_PAT.sub('', raw or '').strip()
    f = fold(t)
    if len(f.replace(' ', '')) < 5:
        return None
    if JUNK_PAT.search(f):
        return None
    # uploader-handle mush: single long token, no vowel structure typical of
    # sahitya titles is hard to test; instead drop titles that are mostly
    # digits after cleaning
    digits = sum(c.isdigit() for c in f)
    if digits > len(f) * 0.3:
        return None
    return t


def main() -> None:
    # raw title -> info accumulation
    infos: dict[str, dict] = {}

    meta = json.loads((ROOT / 'models' / 'qmax_catalog_meta.json').read_text())
    for m in meta:
        t = clean_title(m['title'])
        if not t:
            continue
        d = infos.setdefault(t, {'ragas': set(), 'composers': set(),
                                 'has_lyrics': False, 'n_tracks': 0,
                                 'from_lyricsdb': False})
        d['n_tracks'] += 1
        if m.get('raga'):
            d['ragas'].add(m['raga'])

    con = sqlite3.connect(ROOT / 'data' / 'lyrics.db')
    for title, composer, raga, ly in con.execute(
            'select title, composer, raga, lyrics_original '
            'from lyrics_catalog'):
        t = clean_title(title)
        if not t:
            continue
        d = infos.setdefault(t, {'ragas': set(), 'composers': set(),
                                 'has_lyrics': False, 'n_tracks': 0,
                                 'from_lyricsdb': False})
        d['from_lyricsdb'] = True
        d['has_lyrics'] = d['has_lyrics'] or bool(ly)
        if raga:
            d['ragas'].add(raga)
        if composer:
            d['composers'].add(composer)
    con.close()

    kar_path = ROOT / 'data' / 'karnatik_lyrics.json'
    if kar_path.exists():
        for k in json.loads(kar_path.read_text()):
            t = clean_title(k['title'])
            if not t:
                continue
            d = infos.setdefault(t, {'ragas': set(), 'composers': set(),
                                     'has_lyrics': False, 'n_tracks': 0,
                                     'from_lyricsdb': False,
                                     'karnatik_pages': set()})
            d.setdefault('karnatik_pages', set())
            if k['lyrics']:
                d['karnatik_pages'].add(k['page'])
                d['has_lyrics'] = True
            if k.get('raga_index'):
                d['ragas'].add(k['raga_index'])
            if k.get('composer_index'):
                d['composers'].add(k['composer_index'])

    # merge by soft-phonetic key, then fuzzy sweep over key buckets
    by_key: dict[str, list[str]] = {}
    for t in infos:
        by_key.setdefault(skey(t), []).append(t)

    keys = sorted(by_key, key=len)
    merged_into: dict[str, str] = {}
    canon_keys: list[str] = []
    for k in keys:
        hit = None
        for ck in canon_keys:
            if abs(len(ck) - len(k)) <= 4 and fuzz.ratio(k, ck) >= 88:
                hit = ck
                break
        if hit:
            merged_into[k] = hit
        else:
            canon_keys.append(k)

    groups: dict[str, list[str]] = {}
    for k, titles in by_key.items():
        groups.setdefault(merged_into.get(k, k), []).extend(titles)

    def pick_canonical(titles: list[str]) -> str:
        # prefer curated lyrics.db spelling, then the longest title
        lyrdb = [t for t in titles if infos[t]['from_lyricsdb']]
        pool = lyrdb or titles
        return max(pool, key=lambda t: (len(fold(t)), t))

    registry = []
    for i, (ck, titles) in enumerate(sorted(groups.items())):
        canonical = pick_canonical(titles)
        ragas = sorted({r for t in titles for r in infos[t]['ragas']})
        composers = sorted({c for t in titles for c in infos[t]['composers']})
        registry.append({
            'id': f'comp{i:05d}',
            'canonical': canonical,
            'aliases': sorted(set(titles) - {canonical}),
            'ragas': ragas,
            'composers': composers,
            'has_lyrics': any(infos[t]['has_lyrics'] for t in titles),
            'n_tracks': sum(infos[t]['n_tracks'] for t in titles),
            'karnatik_pages': sorted({p for t in titles
                                      for p in infos[t].get('karnatik_pages',
                                                            ())}),
        })

    out = ROOT / 'data' / 'composition_registry.json'
    out.write_text(json.dumps(registry, ensure_ascii=False, indent=1))
    n_alias = sum(len(r['aliases']) for r in registry)
    n_multi = sum(1 for r in registry if r['aliases'])
    print(f'{len(infos)} cleaned titles -> {len(registry)} canonical '
          f'compositions ({n_multi} with aliases, {n_alias} aliases total)')
    print(f'wrote {out}')
    # show a few merges for eyeballing
    for r in registry:
        if len(r['aliases']) >= 2:
            print(f"  {r['canonical']}  <-  {r['aliases'][:4]}")


if __name__ == '__main__':
    main()
