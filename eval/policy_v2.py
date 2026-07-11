"""Policy v2: pick best usable variant; prefer vocal-stem variant when close."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, '/Users/shyamravidath/carnatify')
from identify_clip import load_targets, match_lyrics, skey, _partial, fold

ROOT = Path('/Users/shyamravidath/carnatify')
gpu = json.loads((ROOT / 'transcripts_gpu.json').read_text())
turbo = json.loads((ROOT / 'data' / 'whisper_transcripts_turbo.json').read_text())
HALLUC = re.compile(r'thank you|subtitles|amaraorg|copyright|like and subscribe')
DROP = {'D_prompted'}          # hallucination-prone, no unique wins
VOCAL = {'B_demucs_vocals', 'BD_vocals_prompted'}
CLOSE = 0.15
MIN_ANSWER = 0.35

def keyof(name):
    return fold(name.rsplit('.', 1)[0].split('__', 1)[0]).replace(' ', '')[:10]

gt_names = {keyof(n): n for n in
            ['Bhuvini Dasudane__Śrīranjani.m4a', 'Devadideva__Jaganmōhini.m4a',
             'Eppadi Padinaro__Karṇāṭaka dēvagāndhāri.m4a',
             'Madhava Mamava__Nīlāṁbari.m4a', 'Paripalayamam__Rītigauḷa.m4a',
             'Ramabhi Rama__Dhanyāsi.m4a', 'Tulasi Bilva__Kēdāragauḷa.m4a',
             'alapana1__Bēgaḍa.m4a', 'alapana2__Varāḷi.m4a',
             'sObillu saptaswara__Jaganmōhini.m4a']}
targets, lyr = load_targets()

def truth_match(pred, gt):
    a, b = skey(pred), skey(gt)
    return _partial(a, b) >= 90 or _partial(b, a) >= 90

h1 = h5 = abstains = bluffs = 0
for k, real in gt_names.items():
    gt_title = real.split('__')[0]
    pool = {}
    gk = next((g for g in gpu if keyof(g) == k), None)
    if gk:
        pool.update({v: t for v, t in gpu[gk].items() if v not in DROP})
    tk = next((t for t in turbo if keyof(t) == k), None)
    if tk:
        pool['turbo_local'] = turbo[tk]
    cands = []
    for v, txt in pool.items():
        txt = HALLUC.sub(' ', txt or '')
        if len(txt.replace(' ', '')) < 8:
            continue
        comps, max_rep = match_lyrics(txt, targets, lyr)
        if not comps or max_rep < 2:      # sung clips repeat; junk doesn't
            continue
        cands.append((comps[0]['score'], v in VOCAL, v, comps))
    pick = None
    if cands:
        best = max(c[0] for c in cands)
        strong = [c for c in cands if c[0] >= best - CLOSE]
        vocal = [c for c in strong if c[1]]
        pick = max(vocal or strong, key=lambda c: c[0])
    if pick is None or pick[0] < MIN_ANSWER:
        abstains += 1
        ok = 'alapana' in real or gt_title in ('Bhuvini Dasudane',)
        print(f'{gt_title[:20]:<22} ABSTAIN {"(hard clip)" if ok else "(MISSED SUNG CLIP!)"}')
        continue
    score, _, v, comps = pick
    hits = [truth_match(c['title'], gt_title) for c in comps]
    hit1, hit5 = hits[0], any(hits)
    h1 += hit1; h5 += hit5
    if 'alapana' in real:
        bluffs += 1
    print(f'{gt_title[:20]:<22} [{v:<18}] top1 {"OK" if hit1 else "--"} '
          f'top5 {"OK" if hit5 else "--"} | ' +
          ' | '.join(f"{c['title'][:18]}({c['score']:.2f})" for c in comps[:3]))
print(f'\nPOLICY V2: top1 {h1}/10 top5 {h5}/10, abstains {abstains}, '
      f'alapana-bluffs {bluffs}')
