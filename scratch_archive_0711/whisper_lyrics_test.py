"""Deepti's idea: transcribe sung lyrics -> match composition by text.

Whisper (small) on each sung clip; fuzzy n-gram match of the transcript
against (a) composition titles in the catalog+blog records, (b) lyrics_original
from lyrics.db. Scores like the melody path for direct comparison.
"""
import json, re, sqlite3, unicodedata
from pathlib import Path
from collections import defaultdict

import whisper

ROOT = Path('/Users/shyamravidath/carnatify')

def fold(s):
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 ]', '', t.lower())

def ngrams(text, n=3):
    toks = re.sub(r'\s+', ' ', text).strip()
    toks = toks.replace(' ', '')
    return {toks[i:i+n] for i in range(len(toks) - n + 1)} if len(toks) >= n else set()

# targets: catalog titles + lyrics db
targets = {}  # key -> (display title, raga, source)
meta = json.loads((ROOT / 'models' / 'qmax_catalog_meta.json').read_text())
for m in meta:
    k = fold(m['title'])
    if len(k) >= 6:
        targets.setdefault(k, (m['title'], m['raga'], 'catalog'))
con = sqlite3.connect(ROOT / 'data' / 'lyrics.db')
lyrics_rows = con.execute('select title, raga, lyrics_original from lyrics_catalog').fetchall()
for title, raga, _ in lyrics_rows:
    k = fold(title)
    if len(k) >= 6:
        targets.setdefault(k, (title, raga or '?', 'lyrics_db'))
lyrics_text = {fold(t): fold(ly or '') for t, _, ly in lyrics_rows}
print(f'{len(targets)} target compositions ({sum(1 for v in targets.values() if v[2]=="catalog")} catalog)')

tgt_grams = {k: ngrams(k) | ngrams(lyrics_text.get(k, ''))[:] if False else ngrams(k) for k in targets}
# include first 400 chars of lyrics text in the gram set
for k in targets:
    lt = lyrics_text.get(k, '')
    if lt:
        tgt_grams[k] = tgt_grams[k] | ngrams(lt[:400])

model = whisper.load_model('small')
folder = Path('/Users/shyamravidath/sung_tests')
hits1 = hits5 = n = 0
for path in sorted(folder.glob('*.m4a')):
    if path.stem.startswith('alapana'):
        continue
    gt = fold(path.stem.split('__', 1)[0])
    n += 1
    best_text = ''
    grams = set()
    for lang in (None, 'ta', 'te'):  # auto, tamil, telugu
        try:
            r = model.transcribe(str(path), language=lang, fp16=False)
            txt = fold(r['text'])
            grams |= ngrams(txt)
            if len(txt) > len(best_text): best_text = txt
        except Exception as e:
            print('  whisper fail', lang, e)
    print(f'\n{path.name}\n  transcript(best): {best_text[:120]}')
    if not grams:
        print('  no transcript'); continue
    scored = []
    for k, g in tgt_grams.items():
        if not g: continue
        ov = len(grams & g) / max(4, min(len(grams), len(g)))
        scored.append((ov, k))
    scored.sort(reverse=True)
    top5 = scored[:5]
    print('  text-match top-5: ' + ' | '.join(f'{targets[k][0][:22]}({s:.2f})' for s, k in top5))
    h1 = top5 and top5[0][1] == gt
    h5 = any(k == gt for _, k in top5)
    hits1 += h1; hits5 += h5
    print(f'  TRUTH {gt}: top1 {"OK" if h1 else "--"} top5 {"OK" if h5 else "--"}')
print(f'\nLYRICS PATH SCORE: top1 {hits1}/{n} top5 {hits5}/{n}')
