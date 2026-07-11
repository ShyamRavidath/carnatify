"""Single entry point for clip identification (SoundHound-for-Carnatic v1).

Audio in -> {composition top-5, raga top-5, confidence flags}.

Pipeline (wild-clip validated, 2026-07-11 scoreboard):
  1. ASR, two variants per clip: whisper large-v3-turbo on the original audio
     AND on the demucs vocal stem (stem pass rescues clips where violin/
     mridangam drown the sahitya; original pass rescues clips demucs mangles).
  2. Lyrics matcher per variant: token coverage + repetition bonus + order
     bonus over catalog titles + lyrics.db first lines, variant dedup.
  3. Variant selection: best usable transcript by match score, preferring the
     vocal-stem variant when within 0.15 (its transcripts are cleaner when
     both work). Usable = repeated tokens present (sung kritis repeat pallavi;
     ASR garbage doesn't) after whisper-hallucination-loop stoplist.
     CPU stack measured: comp top-1 3/10, top-5 6/10, zero alapana bluffs.
  4. Raga: melodia (voice-band) -> tonic (drone + 12-rotation vote) -> TDMS
     -> clip RF. Weak on wild clips (honest confidence: always "low") but the
     only answer available for alapana / no-transcript clips.
  Melody/Qmax composition matching is deliberately absent: 0% on wild clips.
  Prompted whisper variants are deliberately absent: on CPU turbo they
  hallucinate fluent repetitive junk that defeats the repetition gate.

Run in venv_train (whisper, demucs, essentia, rapidfuzz):
  venv_train/bin/python identify_clip.py <audio-file-or-folder> [--json]
  --fast skips the demucs+stem ASR pass (halves latency, loses stem rescues)

Filenames "<title>__<raga>.<ext>" get automatic truth scoring
(soft-phonetic fold >= 90, never exact string).
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
MODELS = ROOT / 'models'
TCACHE = ROOT / 'data' / 'whisper_transcripts_turbo.json'
SCACHE = ROOT / 'data' / 'whisper_transcripts_turbo_stems.json'
MEL_HOP_S = 128 / 44100
TAUS = (0.1, 0.15, 0.25)
NB = 40
MIN_TRANSCRIPT_CHARS = 8
# whisper decode-loop artifacts seen on silence/instrumental input
HALLUC = re.compile(r'thank you|subtitles|amaraorg|copyright'
                    r'|like and subscribe|satsang with mooji')
VARIANT_CLOSE = 0.15
MIN_ANSWER_SCORE = 0.35

# ---------------------------------------------------------------- text utils

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


def tokens(s: str, minlen: int = 4) -> list[str]:
    return [soft(w) for w in fold(s).split() if len(w) >= minlen]


# ------------------------------------------------------------------- catalog

def load_targets():
    """Folded-title -> display title, plus folded-title -> folded lyrics head."""
    targets: dict[str, str] = {}
    meta = json.loads((MODELS / 'qmax_catalog_meta.json').read_text())
    for m in meta:
        k = fold(m['title'])
        if len(k) >= 6:
            targets.setdefault(k, m['title'])
    lyr: dict[str, str] = {}
    con = sqlite3.connect(ROOT / 'data' / 'lyrics.db')
    for title, ly in con.execute(
            'select title, lyrics_original from lyrics_catalog'):
        k = fold(title)
        if len(k) >= 6:
            targets.setdefault(k, title)
            lyr[k] = fold(ly or '')[:400]
    con.close()
    return targets, lyr


# ------------------------------------------------------------- lyrics scorer

def lyr_score(k: str, lyr: dict[str, str], tl: list[str],
              tfreq: Counter) -> float:
    """Token coverage + repetition bonus + order bonus (the 6/8 top-5 scorer)."""
    ktoks = tokens(k)
    kt_title = list(dict.fromkeys(ktoks))
    if k in lyr and lyr[k]:
        ktoks = ktoks + tokens(lyr[k])[:6]
    ktoks = list(dict.fromkeys(ktoks))[:9]
    if not ktoks:
        return 0.0
    hits = 0.0
    freq_bonus = 0.0
    for kt in ktoks:
        best = 0
        btok = None
        for tt in tfreq:
            r = _ratio(kt, tt)
            if r > best:
                best = r
                btok = tt
        if best >= 75:
            hits += 1
            if kt in kt_title:
                freq_bonus += min(tfreq[btok], 6) * 0.05
        elif best >= 65:
            hits += 0.5
    order = 0.0
    if len(kt_title) >= 2 and _partial(' '.join(kt_title[:3]),
                                       ' '.join(tl)) >= 80:
        order = 0.15
    return (hits / len(ktoks)) * min(1.0, 0.4 + 0.2 * hits) + freq_bonus + order


def _ratio(a, b):
    from rapidfuzz import fuzz
    return fuzz.ratio(a, b)


def _partial(a, b):
    from rapidfuzz import fuzz
    return fuzz.partial_ratio(a, b)


def match_lyrics(transcript: str, targets: dict[str, str],
                 lyr: dict[str, str], topn: int = 5):
    """Score every target, dedup spelling variants, return top-n."""
    tl = tokens(transcript)
    if not tl:
        return [], 0
    tfreq = Counter(tl)
    scored = sorted(((lyr_score(k, lyr, tl, tfreq), k) for k in targets),
                    reverse=True)
    seen: set[str] = set()
    out = []
    for s, k in scored:
        sk = skey(targets[k])
        if any(_ratio(sk, x) >= 88 for x in seen):
            continue
        seen.add(sk)
        out.append({'title': targets[k], 'score': round(float(s), 3)})
        if len(out) == topn:
            break
    return out, (max(tfreq.values()) if tfreq else 0)


# ---------------------------------------------------------------------- ASR

def _whisper_multi(audio, langs=(None, 'ta', 'te', 'hi')) -> str:
    import whisper
    if not hasattr(_whisper_multi, '_model'):
        _whisper_multi._model = whisper.load_model('large-v3-turbo')
    best = ''
    for lang in langs:
        try:
            r = _whisper_multi._model.transcribe(audio, language=lang,
                                                 fp16=False)
            t = fold(r['text'])
            if len(t) > len(best):
                best = t
        except Exception:
            pass
    return best


def transcribe(path: Path, cache: dict) -> str:
    """Whisper large-v3-turbo on the original audio (cached by filename)."""
    if path.name in cache:
        return cache[path.name]
    import librosa
    audio, _ = librosa.load(str(path), sr=16000, mono=True)
    best = _whisper_multi(audio.astype('float32'))
    cache[path.name] = best
    TCACHE.parent.mkdir(exist_ok=True)
    TCACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return best


def transcribe_stem(path: Path, cache: dict) -> str:
    """Demucs vocal stem -> whisper turbo (cached by filename)."""
    if path.name in cache and 'stem_turbo' in cache[path.name]:
        return cache[path.name]['stem_turbo']
    import librosa
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    if not hasattr(transcribe_stem, '_dem'):
        transcribe_stem._dem = get_model('htdemucs')
        transcribe_stem._dem.eval()
    dem = transcribe_stem._dem
    y, _ = librosa.load(str(path), sr=44100, mono=True)
    wav = torch.tensor(y, dtype=torch.float32)[None].repeat(2, 1)[None]
    with torch.no_grad():
        stems = apply_model(dem, wav, device='cpu', progress=False)[0]
    vocals = stems[dem.sources.index('vocals')].mean(0).numpy()
    v16 = librosa.resample(vocals, orig_sr=44100,
                           target_sr=16000).astype('float32')
    best = _whisper_multi(v16, langs=(None, 'ta', 'te'))
    cache.setdefault(path.name, {})['stem_turbo'] = best
    SCACHE.parent.mkdir(exist_ok=True)
    SCACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return best


# --------------------------------------------------------------------- raga

def tdms_multi(freqs, tonic, hop_s):
    from scipy.ndimage import gaussian_filter
    f = np.asarray(freqs, dtype=np.float64)
    v = f[(f > 0) & np.isfinite(f)]
    if v.size < 300 or tonic <= 0:
        return None
    cents = 1200.0 * np.log2(v / tonic)
    b = np.floor(np.mod(cents, 1200.0) / (1200.0 / NB)).astype(int) % NB
    parts = []
    for tau_s in TAUS:
        tau = max(1, int(round(tau_s / hop_s)))
        if b.size <= tau:
            return None
        M = np.zeros((NB, NB))
        np.add.at(M, (b[:-tau], b[tau:]), 1.0)
        M = gaussian_filter(M, sigma=1.0, mode='wrap')
        M = M ** 0.75
        s = M.sum()
        if s <= 0:
            return None
        parts.append((M / s).ravel())
    return np.concatenate(parts)


def raga_top5(path: Path):
    """Clip RF over TDMS; tonic = drone estimate + 12-rotation vote.

    Wild-clip accuracy is weak (0/10 top-1 measured); confidence is always
    reported "low" so the UI never bluffs.
    """
    import essentia.standard as es
    import joblib
    if not hasattr(raga_top5, '_clf'):
        raga_top5._clf = joblib.load(MODELS / 'raga_clip_rf.pkl')
    clf = raga_top5._clf
    melodia = es.PredominantPitchMelodia(
        frameSize=2048, hopSize=128,
        minFrequency=90, maxFrequency=900, voicingTolerance=0.6)
    y = es.MonoLoader(filename=str(path), sampleRate=44100)()
    f0, _ = melodia(es.EqualLoudness()(y))
    if (f0 > 0).sum() * MEL_HOP_S < 10:
        return [], 'too little melody detected'
    tonic0 = None
    try:
        t_est = float(es.TonicIndianArtMusic()(y))
        if 80.0 <= t_est <= 400.0:
            tonic0 = t_est
    except Exception:
        pass
    base = tonic0 if tonic0 else 146.83
    cands = []
    for k in range(12):
        t_k = base * (2.0 ** (k / 12.0))
        while t_k > 400.0:
            t_k /= 2.0
        while t_k < 80.0:
            t_k *= 2.0
        td = tdms_multi(f0, t_k, MEL_HOP_S)
        if td is None:
            continue
        proba = clf.predict_proba(td[None, :])[0]
        cands.append((float(proba.max()), proba))
    if not cands:
        return [], 'TDMS failed'
    _, proba = max(cands, key=lambda x: x[0])
    order = np.argsort(-proba)
    return ([{'raga': str(clf.classes_[i]), 'p': round(float(proba[i]), 3)}
             for i in order[:5]], None)


# -------------------------------------------------------------------- driver

def identify(path: Path, targets, lyr, cache, scache,
             want_raga: bool = True, fast: bool = False) -> dict:
    variants = {'turbo': transcribe(path, cache)}
    if not fast:
        try:
            variants['stem_turbo'] = transcribe_stem(path, scache)
        except Exception as e:
            print(f'  (stem pass failed: {e})', file=sys.stderr)
    result = {
        'file': path.name,
        'transcript': '',
        'asr_variant': None,
        'compositions': [],
        'composition_confidence': 'none',
        'ragas': [],
        'raga_confidence': 'low',
        'clip_type': 'no usable lyrics (alapana / instrumental / ASR miss)',
    }
    # Score each ASR variant; keep only those with repeated tokens (sung
    # kritis repeat pallavi; hallucinated/garbage transcripts don't).
    cands = []
    for name, txt in variants.items():
        txt = HALLUC.sub(' ', txt or '')
        if len(txt.replace(' ', '')) < MIN_TRANSCRIPT_CHARS:
            continue
        comps, max_rep = match_lyrics(txt, targets, lyr)
        if not comps or max_rep < 2:
            continue
        cands.append((comps[0]['score'], name == 'stem_turbo', name,
                      txt, comps))
    pick = None
    if cands:
        best = max(c[0] for c in cands)
        strong = [c for c in cands if c[0] >= best - VARIANT_CLOSE]
        vocal = [c for c in strong if c[1]]
        pick = max(vocal or strong, key=lambda c: c[0])
    if pick and pick[0] >= MIN_ANSWER_SCORE:
        top, _, vname, txt, comps = pick
        result['transcript'] = txt[:200]
        result['asr_variant'] = vname
        result['compositions'] = comps
        result['clip_type'] = 'sung (lyrics found)'
        margin = top - (comps[1]['score'] if len(comps) > 1 else 0.0)
        if top >= 0.65 and margin >= 0.15:
            result['composition_confidence'] = 'high'
        elif top >= 0.5:
            result['composition_confidence'] = 'medium'
        else:
            result['composition_confidence'] = 'low'
    else:
        result['transcript'] = (variants.get('turbo') or '')[:200]
    if want_raga:
        ragas, err = raga_top5(path)
        result['ragas'] = ragas
        if err:
            result['raga_error'] = err
    return result


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    as_json = '--json' in sys.argv
    no_raga = '--no-raga' in sys.argv
    fast = '--fast' in sys.argv
    if not args:
        sys.exit('usage: identify_clip.py <audio-file-or-folder> '
                 '[--json] [--no-raga] [--fast]')
    target = Path(args[0]).expanduser()
    files = ([target] if target.is_file() else
             sorted(p for p in target.iterdir()
                    if p.suffix.lower() in ('.wav', '.mp3', '.m4a', '.flac')))
    if not files:
        sys.exit(f'no audio files at {target}')

    targets, lyr = load_targets()
    cache = json.loads(TCACHE.read_text()) if TCACHE.exists() else {}
    scache = json.loads(SCACHE.read_text()) if SCACHE.exists() else {}

    def truth_match(pred_title: str, gt: str) -> bool:
        a, b = skey(pred_title), skey(gt)
        return _partial(a, b) >= 90 or _partial(b, a) >= 90

    results = []
    c1 = c5 = r1 = r3 = n = 0
    for p in files:
        res = identify(p, targets, lyr, cache, scache,
                       want_raga=not no_raga, fast=fast)
        results.append(res)
        if as_json:
            continue
        print(f"\n=== {p.name} ===")
        print(f"  type: {res['clip_type']}"
              + (f"  [asr: {res['asr_variant']}]" if res['asr_variant'] else ''))
        print(f"  transcript: {res['transcript'][:90]}")
        for i, c in enumerate(res['compositions'], 1):
            print(f"  {i}. {c['title']}  ({c['score']})")
        print(f"  composition confidence: {res['composition_confidence']}")
        if res['ragas']:
            print('  raga top-5 (low confidence on clips): '
                  + ', '.join(f"{r['raga']} {r['p']}" for r in res['ragas']))
        if '__' in p.stem:
            gt_title, gt_raga = p.stem.split('__', 1)
            n += 1
            hits = [truth_match(c['title'], gt_title)
                    for c in res['compositions']]
            hit1 = bool(hits and hits[0])
            hit5 = any(hits)
            rf = fold(gt_raga).replace(' ', '')
            rhits = [fold(r['raga']).replace(' ', '') == rf
                     for r in res['ragas']]
            rhit1 = bool(rhits and rhits[0])
            rhit3 = any(rhits[:3])
            c1 += hit1; c5 += hit5; r1 += rhit1; r3 += rhit3
            print(f"  TRUTH {gt_title} [{gt_raga}]: comp top1 "
                  f"{'OK' if hit1 else '--'} top5 {'OK' if hit5 else '--'}"
                  + (f" | raga top1 {'OK' if rhit1 else '--'} "
                     f"top3 {'OK' if rhit3 else '--'}" if res['ragas'] else ''))
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    elif n:
        print(f"\n===== SCORE over {n} labeled clips =====")
        print(f"composition top-1 {c1}/{n}  top-5 {c5}/{n}")
        print(f"raga        top-1 {r1}/{n}  top-3 {r3}/{n}")


if __name__ == '__main__':
    main()
