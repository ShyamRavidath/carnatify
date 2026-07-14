#!/usr/bin/env python3
"""Scrape karnatik.com lyrics catalog (8k songs, robots.txt: allow all).

Phase 1 (fetch): download each cNNNN.shtml song page into
  data/karnatik_html/ (gitignored raw cache). Resume-safe: existing
  non-empty files are skipped, so re-running only fills gaps.
Phase 2 (parse): extract title/raga/tala/composer/language/lyrics/meaning
  into data/karnatik_lyrics.json.

Usage:
  python scrape_karnatik.py fetch   # ~1h at the polite rate below
  python scrape_karnatik.py parse
  python scrape_karnatik.py all

Song list comes from the lyrics.shtml dropdown; regenerate with:
  curl -sL https://www.karnatik.com/lyrics.shtml | <extract OPTION VALUE>
(kept in data/karnatik_songs.json).
"""
import html
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SONGS = ROOT / 'data' / 'karnatik_songs.json'
HTML_DIR = ROOT / 'data' / 'karnatik_html'
OUT = ROOT / 'data' / 'karnatik_lyrics.json'
BASE = 'https://www.karnatik.com/'
UA = ('carnatify-research/0.1 (personal Carnatic music project; '
      'contact: dpti0904@gmail.com)')
WORKERS = 2
DELAY = 0.3          # per-worker sleep between requests


def fetch_one(page: str) -> str:
    dest = HTML_DIR / page.replace('.shtml', '.html')
    if dest.exists() and dest.stat().st_size > 500:
        return 'cached'
    req = urllib.request.Request(BASE + page, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        dest.write_bytes(data)
        time.sleep(DELAY)
        return 'ok'
    except Exception as e:            # noqa: BLE001 — log and move on
        time.sleep(DELAY * 3)
        return f'ERR {e}'


def fetch() -> None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    songs = json.loads(SONGS.read_text())
    pages = [s['page'] for s in songs]
    done = errs = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, res in enumerate(ex.map(fetch_one, pages), 1):
            done += 1
            if res.startswith('ERR'):
                errs += 1
                print(f'{pages[i-1]}: {res}', flush=True)
            if i % 250 == 0:
                rate = i / (time.time() - t0)
                print(f'{i}/{len(pages)} ({errs} errors, '
                      f'{rate:.1f} pages/s)', flush=True)
    print(f'fetch done: {done} pages, {errs} errors', flush=True)


SECTION = re.compile(r'^(pallavi|anupallavi|caraNam(\s*\d*)|caranam(\s*\d*)|'
                     r'charanam(\s*\d*)|samashTi caraNam|madhyamakAla '
                     r'sAhityam|citta svaram|swaram|pallavi\s*:)\s*$', re.I)
STOP = re.compile(r'^(Meaning:|Other information:|Notation:|first\s*$)', re.I)


def text_lines(raw: str) -> list[str]:
    t = re.sub(r'<script.*?</script>', '', raw, flags=re.S | re.I)
    t = re.sub(r'<style.*?</style>', '', t, flags=re.S | re.I)
    t = re.sub(r'<[^>]+>', '\n', t)
    t = html.unescape(t)
    return [l.strip() for l in t.split('\n') if l.strip()]


def parse_one(page: str, lines: list[str]) -> dict:
    def field(label):
        for j, l in enumerate(lines):
            if l.lower().startswith(label):
                rest = l[len(label):].strip(' :')
                if rest:
                    return rest
                if j + 1 < len(lines):
                    return lines[j + 1].strip()
        return ''

    rec = {'page': page,
           'raga': field('raagam'),
           'tala': field('taalam'),
           'composer': field('composer'),
           'language': field('language')}

    # lyrics: from the first section header to Meaning/Other information
    start = next((j for j, l in enumerate(lines) if SECTION.match(l)), None)
    lyr, meaning, mode = [], [], None
    if start is not None:
        for l in lines[start:]:
            if STOP.match(l):
                mode = 'meaning' if l.lower().startswith('meaning') else 'end'
                if mode == 'end':
                    break
                continue
            if mode == 'meaning':
                if re.match(r'^(first|previous|next|Contact us|updated on)',
                            l, re.I):
                    break
                meaning.append(l)
            else:
                lyr.append(l)
    rec['lyrics'] = '\n'.join(lyr).strip()
    rec['meaning'] = ' '.join(meaning).strip()
    return rec


def parse() -> None:
    songs = json.loads(SONGS.read_text())
    out = []
    missing = empty = 0
    for s in songs:
        f = HTML_DIR / s['page'].replace('.shtml', '.html')
        if not f.exists():
            missing += 1
            continue
        rec = parse_one(s['page'],
                        text_lines(f.read_text(encoding='utf-8',
                                               errors='replace')))
        rec['title'] = s['title']
        rec['raga_index'] = s['raga']       # raga per the index dropdown
        rec['composer_index'] = s['composer']
        if not rec['lyrics']:
            empty += 1
        out.append(rec)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    with_lyr = sum(1 for r in out if r['lyrics'])
    with_mean = sum(1 for r in out if r['meaning'])
    print(f'parsed {len(out)} (missing html {missing}); '
          f'lyrics {with_lyr}, empty {empty}, meanings {with_mean}')


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if arg in ('fetch', 'all'):
        fetch()
    if arg in ('parse', 'all'):
        parse()
