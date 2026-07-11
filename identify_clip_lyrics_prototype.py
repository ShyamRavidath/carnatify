"""Lyrics path v3: whisper transcripts (cached) + phonetic fuzzy matching."""
import json, re, sqlite3, unicodedata
from pathlib import Path

import numpy as np

ROOT = Path('/Users/shyamravidath/carnatify')
S = Path(__file__).parent
TCACHE = S / 'whisper_transcripts.json'

def fold(s):
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 ]', '', t.lower())

def phon(s):
    """Aggressive phonetic squash for transliteration/ASR noise."""
    t = fold(s).replace(' ', '')
    for a, b in [('aa','a'),('ee','i'),('ii','i'),('oo','u'),('uu','u'),
                 ('bh','b'),('ch','c'),('dh','d'),('gh','g'),('jh','j'),
                 ('kh','k'),('ph','p'),('sh','s'),('th','t'),('w','v'),
                 ('z','s')]:
        t = t.replace(a, b)
    # drop vowels except leading
    return t[:1] + re.sub(r'[aeiou]', '', t[1:])

# transcripts (cache across runs)
if TCACHE.exists():
    transcripts = json.loads(TCACHE.read_text())
else:
    transcripts = {}
import whisper, librosa
folder = Path('/Users/shyamravidath/sung_tests')
files = [p for p in sorted(folder.glob('*.m4a')) if not p.stem.startswith('alapana')]
model_small = whisper.load_model('small')
model_medium = None
for p in files:
    if p.name in transcripts: continue
    audio, _ = librosa.load(str(p), sr=16000, mono=True)
    audio = audio.astype('float32')
    texts = []
    for lang in (None, 'ta', 'te', 'hi'):
        try:
            r = model_small.transcribe(audio, language=lang, fp16=False)
            texts.append(fold(r['text']))
        except Exception:
            pass
    best = max(texts, key=len) if texts else ''
    if len(best.replace(' ', '')) < 12:
        if model_medium is None:
            model_medium = whisper.load_model('medium')
        for lang in (None, 'ta'):
            try:
                r = model_medium.transcribe(audio, language=lang, fp16=False)
                t = fold(r['text'])
                if len(t) > len(best): best = t
            except Exception:
                pass
    transcripts[p.name] = best
    TCACHE.write_text(json.dumps(transcripts, ensure_ascii=False, indent=1))
    print(f'{p.name}: {best[:100]}', flush=True)

# targets
from rapidfuzz import fuzz
targets = {}
meta = json.loads((ROOT / 'models' / 'qmax_catalog_meta.json').read_text())
for m in meta:
    k = fold(m['title'])
    if len(k) >= 6:
        targets.setdefault(k, m['title'])
con = sqlite3.connect(ROOT / 'data' / 'lyrics.db')
rows = con.execute('select title, lyrics_original from lyrics_catalog').fetchall()
lyr = {}
for title, ly in rows:
    k = fold(title)
    if len(k) >= 6:
        targets.setdefault(k, title)
        lyr[k] = fold(ly or '')[:600]

print(f'\n{len(targets)} targets')
h1 = h5 = n = 0
for p in files:
    txt = transcripts.get(p.name, '')
    gt = fold(p.stem.split('__', 1)[0])
    n += 1
    print(f'\n{p.name}\n  transcript: {txt[:90]}')
    if len(txt.replace(' ', '')) < 8:
        print('  (no usable transcript)'); continue
    ptxt = phon(txt)
    scored = []
    for k, disp in targets.items():
        s_title = fuzz.partial_ratio(phon(k), ptxt)
        s_lyr = fuzz.partial_ratio(phon(lyr[k])[:200], ptxt) if k in lyr and lyr[k] else 0
        scored.append((max(s_title, 0.9 * s_lyr), k, disp))
    scored.sort(reverse=True)
    top5 = scored[:5]
    print('  top-5: ' + ' | '.join(f'{d[:24]}({s:.0f})' for s, k, d in top5))
    hit1 = top5 and top5[0][1] == gt
    hit5 = any(k == gt for _, k, _ in top5)
    h1 += hit1; h5 += hit5
    print(f'  TRUTH {gt}: top1 {"OK" if hit1 else "--"} top5 {"OK" if hit5 else "--"}')
print(f'\nLYRICS v3 SCORE: top1 {h1}/{n} top5 {h5}/{n}')
