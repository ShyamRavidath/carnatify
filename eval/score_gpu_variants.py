"""Score every ASR variant (GPU json + local turbo) with the shipped matcher."""
import json, sys
from pathlib import Path
sys.path.insert(0, '/Users/shyamravidath/carnatify')
from identify_clip import (load_targets, match_lyrics, skey, _partial, fold,
                           MIN_TRANSCRIPT_CHARS)

ROOT = Path('/Users/shyamravidath/carnatify')
gpu = json.loads((ROOT / 'transcripts_gpu.json').read_text())
turbo = json.loads((ROOT / 'data' / 'whisper_transcripts_turbo.json').read_text())

# GPU filenames are mojibake'd; map by folded ascii title prefix
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

def score_variant(txt, gt_title):
    if len((txt or '').replace(' ', '')) < MIN_TRANSCRIPT_CHARS:
        return None
    comps, max_rep = match_lyrics(txt, targets, lyr)
    if not comps:
        return None
    hits = [truth_match(c['title'], gt_title) for c in comps]
    return {'top': comps[0]['score'], 'rep': max_rep,
            'hit1': bool(hits[0]), 'hit5': any(hits),
            'usable': max_rep >= 2 or comps[0]['score'] >= 0.65,
            'best': comps[0]['title']}

variant_tally = {}
auto1 = auto5 = 0
print(f"{'clip':<18} {'variant':<20} top  rep hit1 hit5")
for k, real in gt_names.items():
    gt_title = real.split('__')[0]
    pool = {}
    gk = next((g for g in gpu if keyof(g) == k), None)
    if gk:
        pool.update(gpu[gk])
    tk = next((t for t in turbo if keyof(t) == k), None)
    if tk:
        pool['turbo_local'] = turbo[tk]
    rows = {}
    for v, txt in pool.items():
        r = score_variant(txt, gt_title)
        rows[v] = r
        if r:
            t = variant_tally.setdefault(v, [0, 0, 0])
            t[0] += r['hit1']; t[1] += r['hit5']; t[2] += 1
        print(f"{gt_title[:17]:<18} {v:<20} "
              + (f"{r['top']:.2f} {r['rep']:>3} {'OK' if r['hit1'] else '--':>4} "
                 f"{'OK' if r['hit5'] else '--':>4}" if r else ' unusable'))
    # auto policy: among usable variants, pick highest top score
    usable = {v: r for v, r in rows.items() if r and r['usable']}
    if usable:
        pick = max(usable.values(), key=lambda r: r['top'])
        auto1 += pick['hit1']; auto5 += pick['hit5']
        print(f"{'':18} AUTO-PICK -> {pick['best'][:30]} "
              f"hit1 {'OK' if pick['hit1'] else '--'} hit5 {'OK' if pick['hit5'] else '--'}")
    else:
        print(f"{'':18} AUTO-PICK -> abstain (no usable variant)")
    print()

print('per-variant (hit1/hit5/n-usable):')
for v, (h1, h5, n) in sorted(variant_tally.items()):
    print(f'  {v:<20} {h1}/{h5}/{n}')
print(f'\nAUTO-SELECT policy over 10 clips: top1 {auto1}/10 top5 {auto5}/10')
