"""Fusion: lyrics token-coverage retrieves top-10 works, melody Qmax re-ranks."""
import json, re, sqlite3, unicodedata
from collections import Counter
from pathlib import Path
import numpy as np
from rapidfuzz import fuzz

ROOT = Path('/Users/shyamravidath/carnatify')
S = Path(__file__).parent
tr = json.loads((S / 'whisper_transcripts_turbo.json').read_text())

def fold(s):
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 ]', '', t.lower())
def soft(s):
    for a, b in [('aa','a'),('ee','i'),('ii','i'),('oo','u'),('uu','u'),('bh','b'),('ch','c'),('dh','d'),('gh','g'),('jh','j'),('kh','k'),('ph','p'),('sh','s'),('th','t'),('w','v'),('z','s')]:
        s = s.replace(a, b)
    return s
def skey(s): return soft(fold(s).replace(' ', ''))
def tokens(s, minlen=4):
    return [soft(w) for w in fold(s).split() if len(w) >= minlen]

meta = json.loads((ROOT / 'models' / 'qmax_catalog_meta.json').read_text())
cat = np.load(ROOT / 'models' / 'qmax_catalog.npz')
windows = cat['windows']; win_track = cat['win_track']
# map folded title -> catalog track indices
title2tracks = {}
targets = {}
for i, m in enumerate(meta):
    k = fold(m['title'])
    if len(k) >= 6:
        targets.setdefault(k, m['title'])
        title2tracks.setdefault(k, []).append(i)
con = sqlite3.connect(ROOT / 'data' / 'lyrics.db')
lyr = {}
for title, ly in con.execute('select title, lyrics_original from lyrics_catalog'):
    k = fold(title)
    if len(k) >= 6:
        targets.setdefault(k, title)
        lyr[k] = fold(ly or '')[:400]

def lyr_score(k, tl, tfreq):
    ktoks = tokens(k); kt_title = list(dict.fromkeys(ktoks))
    if k in lyr and lyr[k]: ktoks = ktoks + tokens(lyr[k])[:6]
    ktoks = list(dict.fromkeys(ktoks))[:9]
    if not ktoks: return 0.0
    hits = 0.0; freq_bonus = 0.0
    for kt in ktoks:
        best = 0; btok = None
        for tt in tfreq:
            r = fuzz.ratio(kt, tt)
            if r > best: best = r; btok = tt
        if best >= 75:
            hits += 1
            if kt in kt_title: freq_bonus += min(tfreq[btok], 6) * 0.05
        elif best >= 65: hits += 0.5
    order = 0.0
    if len(kt_title) >= 2 and fuzz.partial_ratio(' '.join(kt_title[:3]), ' '.join(tl)) >= 80:
        order = 0.15
    return (hits / len(ktoks)) * min(1.0, 0.4 + 0.2 * hits) + freq_bonus + order

import essentia.standard as es
ccs = es.ChromaCrossSimilarity(frameStackSize=9, frameStackStride=1, binarizePercentile=0.095, oti=True)
csm = es.CoverSongSimilarity(disOnset=0.5, disExtension=0.5, alignmentType='serra09', distanceType='asymmetric')
melodia = es.PredominantPitchMelodia(frameSize=2048, hopSize=128, minFrequency=90, maxFrequency=900, voicingTolerance=0.6)
eq = es.EqualLoudness()
DEC = 80
def chroma_from_pitch(f):
    f = np.asarray(f, dtype=np.float64)
    n = f.size // DEC
    if n < 30: return None
    fr = f[:n * DEC].reshape(n, DEC)
    out = np.zeros((n, 12), dtype=np.float32); valid = np.zeros(n, bool)
    for i in range(n):
        v = fr[i]; v = v[(v > 0) & np.isfinite(v)]
        if v.size < DEC // 4: continue
        pc = np.mod(12.0 * np.log2(np.median(v) / 440.0), 12.0)
        b = int(round(pc)) % 12
        out[i, b] = 1.0; out[i, (b+1)%12] = 0.3; out[i, (b-1)%12] = 0.3
        valid[i] = True
    out = out[valid]
    return out if out.shape[0] >= 30 else None

folder = Path('/Users/shyamravidath/sung_tests')
h1 = h5 = n = 0
for fname, txt in tr.items():
    gt = skey(fname.rsplit('.', 1)[0].split('__', 1)[0])
    n += 1
    tl = tokens(txt)
    if not tl:
        print(f'{fname}: no transcript'); continue
    tfreq = Counter(tl)
    scored = sorted(((lyr_score(k, tl, tfreq), k) for k in targets), reverse=True)
    # variant-dedup to top-10 candidate works
    seen = set(); cands = []
    for s, k in scored:
        sk = skey(targets[k])
        if any(fuzz.ratio(sk, x) >= 88 for x in seen): continue
        seen.add(sk); cands.append((s, k))
        if len(cands) == 10: break
    lmax = cands[0][0] if cands else 1.0
    # melody re-rank
    y = es.MonoLoader(filename=str(folder / fname), sampleRate=44100)()
    f0, _ = melodia(eq(y))
    q = chroma_from_pitch(f0)
    fused = []
    for s, k in cands:
        d_best = np.inf
        for ti in title2tracks.get(k, []):
            for wi in np.where(win_track == ti)[0]:
                try:
                    _, d = csm(ccs(q, windows[wi]))
                except Exception:
                    continue
                if d < d_best: d_best = d
        # normalize: lyrics dominant, melody tiebreak (lower dist better)
        mel = 0.0 if not np.isfinite(d_best) else max(0.0, 0.25 - d_best)
        fused.append((s / max(lmax, 1e-6) + 1.2 * mel, s, d_best, k))
    fused.sort(reverse=True)
    def m(k): return fuzz.partial_ratio(skey(targets[k]), gt) >= 90 or fuzz.partial_ratio(gt, skey(targets[k])) >= 90
    hit1 = fused and m(fused[0][3]); hit5 = any(m(k) for _, _, _, k in fused[:5])
    h1 += hit1; h5 += hit5
    print(f'{fname}: {"OK" if hit1 else ("top5" if hit5 else "--")} | ' +
          ' | '.join(f'{targets[k][:18]}(l{s:.2f}/d{d:.2f})' for _, s, d, k in fused[:3]), flush=True)
print(f'\nFUSION SCORE: top1 {h1}/{n} top5 {h5}/{n}')
