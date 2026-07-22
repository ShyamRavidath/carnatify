"""Single entry point for clip identification (SoundHound-for-Carnatic v1).

Audio in -> {composition top-5, raga top-5, confidence flags}.

Pipeline (wild-clip validated; 2026-07-13 scoreboard on 21 clips below):
  1. ASR, two variants per clip: whisper large-v3-turbo on the original audio
     AND on the demucs vocal stem (stem pass rescues clips where violin/
     mridangam drown the sahitya; original pass rescues clips demucs mangles).
  2. Lyrics matcher per variant: IDF-weighted token coverage + repetition
     bonus + order bonus over registry titles AND karnatik lyric lines (each
     line scores like a title, so mid-kriti clips are matchable). Transcript
     tokens include joined adjacent-word bigrams (whisper splits sung
     sahitya: 'vata piga na patin' -> 'vatapiga' ~ vAtApi).
  3. Variant selection: best usable transcript by match score, preferring the
     vocal-stem variant when within 0.15 (its transcripts are cleaner when
     both work). Usable = repeated tokens present (sung kritis repeat pallavi;
     ASR garbage doesn't) after whisper-hallucination-loop stoplist.
     Measured 2026-07-13, 21 wild clips, CPU: this matcher on the 2.2k v1
     registry 8/21 top-1 10/21 top-5 (old matcher 7/21, 9/21); on the 8.7k
     karnatik-expanded registry 6/21, 8/21 — the in-catalog-only test set
     cannot reward the 4x coverage, real queries can.
  4. Raga: melodia (voice-band) -> tonic (drone + 12-rotation vote) -> TDMS
     -> clip RF. Weak on wild clips (honest confidence: always "low") but the
     only answer available for alapana / no-transcript clips. A confident
     composition match backfills raga from the registry instead
     (raga_from_catalog: 7/13 correct vs RF 5/21 top-1 on the same set).
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

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
MODELS = ROOT / 'models'
TCACHE = ROOT / 'data' / 'whisper_transcripts_turbo.json'
SCACHE = ROOT / 'data' / 'whisper_transcripts_turbo_stems.json'
# v2 ASR cache: keyed by audio sha256 + full ASR config identity, stores raw
# per-language hypotheses (native script preserved) — see ASR_CONFIG_V2
CACHE2 = ROOT / 'data' / 'asr_cache_v2.json'
MEL_HOP_S = 128 / 44100
TAUS = (0.1, 0.15, 0.25)
NB = 40
MIN_TRANSCRIPT_CHARS = 8
# whisper decode-loop artifacts seen on silence/instrumental input
HALLUC = re.compile(r'thank you|subtitles|amaraorg|copyright'
                    r'|like and subscribe|satsang with mooji')
VARIANT_CLOSE = 0.15
MIN_ANSWER_SCORE = 0.35
# whisper decode loops repeat one token verbatim (satish satish satish...);
# real sung repetition is phrase-level and interleaved (brahmamayam sarvam
# brahmamayam briyere...) — max same-token run on true transcripts is 2-3
LOOP_RUN = 4


def _max_token_run(txt: str) -> int:
    best = run = 0
    prev = None
    for w in txt.split():
        run = run + 1 if w == prev else 1
        prev = w
        best = max(best, run)
    return best

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


# native Indic script blocks whisper emits for forced ta/te/hi passes;
# fold() alone would erase these to whitespace (the P0 Unicode bug)
_SCRIPTS = (
    ('devanagari', 0x0900, 0x097F),
    ('tamil', 0x0B80, 0x0BFF),
    ('telugu', 0x0C00, 0x0C7F),
    ('kannada', 0x0C80, 0x0CFF),
    ('malayalam', 0x0D00, 0x0D7F),
)


def _detect_script(s: str):
    counts = Counter()
    for ch in s:
        cp = ord(ch)
        for name, lo, hi in _SCRIPTS:
            if lo <= cp <= hi:
                counts[name] += 1
                break
    return counts.most_common(1)[0][0] if counts else None


def translit_fold(s: str) -> str:
    """Matching view for raw ASR text: native Indic script is deterministically
    transliterated (Harvard-Kyoto) before folding, so forced-language output
    survives into matching. A VIEW only — raw text stays in the cache."""
    script = _detect_script(s or '')
    if script is not None:
        from indic_transliteration import sanscript
        try:
            s = sanscript.transliterate(s, script, sanscript.HK)
        except Exception as e:
            print(f'  (transliteration {script} failed: {e})',
                  file=sys.stderr)
    return fold(s)


def tokens(s: str, minlen: int = 4) -> list[str]:
    return [soft(w) for w in fold(s).split() if len(w) >= minlen]


# ------------------------------------------------------------------- catalog

REGISTRY = ROOT / 'data' / 'composition_registry.json'
KARNATIK = ROOT / 'data' / 'karnatik_lyrics.json'
# lyric-line pseudo-variants: skip section headers and refrain markers
LINE_SKIP = re.compile(r'^(pallavi|anupallavi|cara[nN]am|charanam|caranam'
                       r'|samashTi.*|madhyamak.*|citta ?svaram?|swaram?'
                       r'|chittaswaram?)\s*\d*\s*$|^\(', re.I)
MAX_LINES_PER_ENTRY = 60


def _line_variants(pages: list[str], kar: dict[str, dict]) -> list[str]:
    """Folded lyric lines for an entry's karnatik pages (sung-unit granules).

    Each line matches like a title: a clip from any caraNam can hit its own
    line even when the pallavi/title tokens never appear in the transcript.
    """
    out, seen = [], set()
    for p in pages:
        rec = kar.get(p)
        if not rec:
            continue
        for line in rec['lyrics'].split('\n'):
            if LINE_SKIP.match(line.strip()):
                continue
            f = fold(line)
            if len(f) >= 10 and f not in seen:
                seen.add(f)
                out.append(f)
            if len(out) >= MAX_LINES_PER_ENTRY:
                return out
    return out


def _precompute(e: dict) -> None:
    """Token lists per variant/line so match-time is lookup arithmetic."""
    def prep(k: str, lyr_head: str = '', is_line: bool = False):
        ktoks = tokens(k)
        kt_title = list(dict.fromkeys(ktoks))
        if lyr_head:
            ktoks = ktoks + tokens(lyr_head)[:6]
        ktoks = list(dict.fromkeys(ktoks))[:9]
        # lines get NO repetition bonus: freq_bonus models a repeated
        # pallavi title; on 9-token lyric lines it stacks into score
        # blowups (>2.0) that bury real titles under junk-line matches
        return {'ktoks': ktoks,
                'kt_title': set() if is_line else set(kt_title),
                'head3': ' '.join(kt_title[:3]) if len(kt_title) >= 2 else ''}

    e['vtoks'] = [prep(v, e['lyr']) for v in e['variants']]
    e['ltoks'] = [prep(l, is_line=True) for l in e.get('lines', [])]


def load_targets():
    """Composition registry entries for matching.

    Returns (entries, _) where each entry is
      {'canonical', 'ragas', 'variants': [folded title strings],
       'lyr': folded lyrics head or '',
       'lines': [folded lyric lines] (karnatik full-lyrics channel),
       'vtoks'/'ltoks': precomputed token lists for the fast scorer}.
    Falls back to raw catalog+lyrics.db titles if the registry is missing
    (rebuild with build_composition_registry.py).
    """
    lyr_by_fold: dict[str, str] = {}
    con = sqlite3.connect(ROOT / 'data' / 'lyrics.db')
    for title, ly in con.execute(
            'select title, lyrics_original from lyrics_catalog'):
        if ly:
            lyr_by_fold[fold(title)] = fold(ly)[:400]
    con.close()

    kar: dict[str, dict] = {}
    if KARNATIK.exists():
        kar = {r['page']: r for r in json.loads(KARNATIK.read_text())
               if r.get('lyrics')}

    entries = []
    if REGISTRY.exists():
        for r in json.loads(REGISTRY.read_text()):
            variants = [r['canonical']] + r['aliases']
            folded = [fold(v) for v in variants]
            lyr = next((lyr_by_fold[f] for f in folded if f in lyr_by_fold),
                       '')
            entries.append({'canonical': r['canonical'],
                            'ragas': r.get('ragas', []),
                            'variants': [f for f in folded if len(f) >= 6],
                            'lyr': lyr,
                            'lines': _line_variants(
                                r.get('karnatik_pages', []), kar)})
        entries = [e for e in entries if e['variants']]
    else:
        # legacy fallback: one entry per unique folded title
        seen: dict[str, str] = {}
        meta = json.loads((MODELS / 'qmax_catalog_meta.json').read_text())
        for m in meta:
            k = fold(m['title'])
            if len(k) >= 6:
                seen.setdefault(k, m['title'])
        for k, ly in lyr_by_fold.items():
            if len(k) >= 6:
                seen.setdefault(k, k)
        entries = [{'canonical': disp, 'ragas': [], 'variants': [k],
                    'lyr': lyr_by_fold.get(k, ''), 'lines': []}
                   for k, disp in seen.items()]
    for e in entries:
        _precompute(e)
    return entries, None


# ------------------------------------------------------------- lyrics scorer

def _ratio(a, b):
    from rapidfuzz import fuzz
    return fuzz.ratio(a, b)


def _partial(a, b):
    from rapidfuzz import fuzz
    return fuzz.partial_ratio(a, b)


def _vocab_idf(entries: list[dict]):
    """Catalog token vocabulary + IDF weights, cached per entries object.

    IDF discriminates rare sahitya words from ubiquitous devotional tokens
    (rAma/pAlaya/nAma/dEva...) that would otherwise let a 8.7k-title catalog
    drown true matches in junk coincidences (measured: registry 2.2k -> 8.7k
    cost 3/21 top-1 with unweighted hits).
    """
    vc = getattr(match_lyrics, '_vc', None)
    if vc is not None and vc[0] is entries:
        return vc[1], vc[2]
    df = Counter()
    for e in entries:
        toks = {kt for vt in e['vtoks'] + e['ltoks'] for kt in vt['ktoks']}
        df.update(toks)
    n = max(1, len(entries))
    idf = {t: float(np.log2(1.0 + n / c)) for t, c in df.items()}
    vocab = sorted(idf)
    match_lyrics._vc = (entries, vocab, idf)
    return vocab, idf


def _best_map(entries: list[dict], tl_unique: list[str],
              topk: int = 3) -> dict:
    """Top-k (fuzz.ratio, transcript token) candidates per catalog token.

    One vectorized cdist over the catalog token vocabulary replaces the old
    per-variant inner loop — required now that lyric lines add ~100k
    pseudo-variants. k>1 gives the injective scorer fallback evidence when
    a transcript token is already claimed by a rarer catalog token.
    """
    from rapidfuzz import fuzz, process
    vocab, _ = _vocab_idf(entries)
    # server path must bound this (2-vCPU Space): CARNATIFY_MATCH_WORKERS=2
    workers = int(os.environ.get('CARNATIFY_MATCH_WORKERS', '-1'))
    mat = process.cdist(vocab, tl_unique, scorer=fuzz.ratio, workers=workers)
    k = min(topk, mat.shape[1])
    idx = np.argpartition(-mat, k - 1, axis=1)[:, :k]
    return {v: sorted(((float(mat[i, j]), tl_unique[int(j)])
                       for j in idx[i]), reverse=True)
            for i, v in enumerate(vocab)}


def _score_ktoks(vt: dict, best: dict, tfreq: Counter,
                 tl_joined: str, idf: dict,
                 base: dict | None = None,
                 bparts: dict | None = None) -> float:
    """IDF-weighted token coverage + repetition bonus + order bonus.

    Same shape as the pre-0713 lyr_score, fed from the _best_map lookup
    instead of an inner fuzz loop, with three changes:
    - coverage is IDF-weighted (rare sahitya words count, ubiquitous
      devotional words barely do) — required at 8.7k-title catalog scale;
    - order bonus gated on >=1 token hit (pure speed gate);
    - one-to-one evidence: each transcript token occurrence satisfies at
      most one catalog token (highest-ratio catalog tokens claim first,
      lower-ranked ones fall back to unclaimed candidates), so 'rama rama'
      cannot light up every rama-shaped token of an entry. Legacy
      many-to-one behavior: CARNATIFY_LEGACY_SCORING=1.
    """
    ktoks = vt['ktoks']
    if not ktoks:
        return 0.0
    legacy = bool(os.environ.get('CARNATIFY_LEGACY_SCORING'))
    raw_hits = 0.0
    w_hits = 0.0
    w_total = float(sum(idf.get(kt, 1.0) for kt in ktoks))
    freq_bonus = 0.0
    hit_ratios = []
    if legacy:
        assigned = [(kt, *best.get(kt, [(0.0, None)])[0]) for kt in ktoks]
    else:
        # strongest candidate first; each transcript occurrence is usable
        # once, and a joined bigram spends BOTH its parts' occurrences —
        # the same audio span never counts as two pieces of evidence
        order_i = sorted(range(len(ktoks)),
                         key=lambda i: -best.get(ktoks[i],
                                                 [(0.0, None)])[0][0])
        avail = dict(base if base is not None else tfreq)
        assigned = []
        for i in order_i:
            kt = ktoks[i]
            b, btok = 0.0, None
            for cb, ct in best.get(kt, ()):
                if cb < 65:
                    break
                parts = bparts.get(ct) if bparts else None
                if parts:
                    a1, a2 = parts
                    if avail.get(a1, 0) > 0 and (a1 != a2
                                                 or avail.get(a1, 0) > 1) \
                            and avail.get(a2, 0) > 0:
                        b, btok = cb, ct
                        avail[a1] -= 1
                        avail[a2] -= 1
                        break
                elif avail.get(ct, 0) > 0:
                    b, btok = cb, ct
                    avail[ct] -= 1
                    break
            assigned.append((kt, b, btok))
    bonus_used = set()
    for kt, b, btok in assigned:
        w = idf.get(kt, 1.0)
        # matched information is bounded by BOTH sides: a generic transcript
        # token (rama, siva...) must not inherit a rare catalog token's IDF
        # through a fuzzy hit (unseen transcript strings keep the kt weight)
        if not legacy and btok is not None and btok in idf:
            w = min(w, idf[btok])
        if b >= 75:
            raw_hits += 1
            w_hits += w
            hit_ratios.append(b)
            # repetition bonus once per distinct transcript token — a title
            # with several rama-shaped tokens must not stack it
            if kt in vt['kt_title'] and (legacy or btok not in bonus_used):
                freq_bonus += min(tfreq.get(btok, 1), 6) * 0.05
                bonus_used.add(btok)
        elif b >= 65:
            raw_hits += 0.5
            w_hits += 0.5 * w
            hit_ratios.append(b)
    order = 0.0
    if (raw_hits >= 1 and vt['head3']
            and _partial(vt['head3'], tl_joined) >= 80):
        order = 0.15
    # epsilon tie-break only: exact-matching titles beat fuzzy-junk titles
    # that reach the same coverage score (max shift 0.001, invisible in the
    # rounded display, decisive on exact ties)
    quality = (sum(hit_ratios) / len(hit_ratios) / 100_000 if hit_ratios
               else 0.0)
    return ((w_hits / w_total) * min(1.0, 0.4 + 0.2 * raw_hits)
            + freq_bonus + order + quality)


def match_lyrics(transcript: str, entries: list[dict],
                 _unused=None, topn: int = 5):
    """Score every registry entry, top-n.

    Per entry: max over title spelling variants AND karnatik lyric-line
    pseudo-variants (same scorer, same scale — a sung caraNam line counts
    like a sung title, so mid-kriti clips become matchable).
    """
    tl = tokens(transcript)
    if not tl:
        return [], 0
    tfreq = Counter(tl)
    tl_joined = ' '.join(tl)
    # joined adjacent word pairs recover whisper's syllable splits; they
    # inherit the min frequency of their parts for the repetition bonus
    raw = fold(transcript).split()
    # occurrence pool for one-to-one evidence: soft unigram counts of every
    # raw word (incl. <4-char words that the token filter drops)
    base = Counter(soft(w) for w in raw if w)
    big = Counter()
    bparts = {}
    for a, b in zip(raw, raw[1:]):
        j = soft(a + b)
        if len(j) >= 6:
            big[j] = max(big[j], min(tfreq.get(soft(a), 1),
                                     tfreq.get(soft(b), 1)))
            bparts[j] = (soft(a), soft(b))
    pool = dict(big)
    pool.update(tfreq)
    tfreq_ext = Counter(pool)
    _, idf = _vocab_idf(entries)
    best = _best_map(entries, list(tfreq_ext))
    scored = []
    for e in entries:
        s = max(_score_ktoks(vt, best, tfreq_ext, tl_joined, idf,
                             base, bparts)
                for vt in e['vtoks'])
        for vt in e['ltoks']:
            s2 = _score_ktoks(vt, best, tfreq_ext, tl_joined, idf,
                              base, bparts)
            if s2 > s:
                s = s2
        scored.append((s, e))
    scored.sort(key=lambda x: -x[0])
    out = [{'title': e['canonical'], 'score': round(float(s), 3),
            'ragas': e['ragas']}
           for s, e in scored[:topn]]
    return out, (max(tfreq.values()) if tfreq else 0)


# ---------------------------------------------------------------------- ASR

def _atomic_write_json(path: Path, obj) -> None:
    """Write via temp file + rename so an interrupted write can't corrupt
    the only scoreboard's cache."""
    path.parent.mkdir(exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _whisper_hyps(audio, langs=(None, 'ta', 'te', 'hi')) -> list[dict]:
    """One raw hypothesis per language pass, native script preserved.

    status: 'ok' | 'empty' (decode succeeded, no symbols) | 'error: ...'
    (integration failure — never conflate with an ASR-dead clip).
    """
    import whisper
    if not hasattr(_whisper_hyps, '_model'):
        _whisper_hyps._model = whisper.load_model('large-v3-turbo')
    hyps = []
    for lang in langs:
        h = {'lang': lang or 'auto', 'raw': '', 'segments': [],
             'status': 'ok'}
        try:
            r = _whisper_hyps._model.transcribe(audio, language=lang,
                                                fp16=False)
            h['raw'] = (r.get('text') or '').strip()
            h['segments'] = [
                {'start': round(float(s['start']), 2),
                 'end': round(float(s['end']), 2),
                 'text': (s.get('text') or '').strip()}
                for s in r.get('segments', [])]
            if not h['raw']:
                h['status'] = 'empty'
        except Exception as e:
            h['status'] = f'error: {type(e).__name__}: {e}'
            print(f"  (ASR pass lang={lang or 'auto'} failed: "
                  f"{h['status']})", file=sys.stderr)
        hyps.append(h)
    return hyps


def _whisper_multi(audio, langs=(None, 'ta', 'te', 'hi')) -> str:
    """Legacy selection: longest folded hypothesis across language passes."""
    best = ''
    for h in _whisper_hyps(audio, langs):
        t = fold(h['raw'])
        if len(t) > len(best):
            best = t
    return best


def transcribe(path: Path, cache: dict) -> str:
    """Whisper large-v3-turbo on the original audio (cached by filename)."""
    if path.name in cache:
        return cache[path.name]
    import librosa
    audio, _ = librosa.load(str(path), sr=16000, mono=True)
    best = _whisper_multi(audio.astype('float32'))
    cache[path.name] = best
    _atomic_write_json(TCACHE, cache)
    return best


def _vocal_stem_16k(path: Path):
    """Demucs htdemucs vocal stem, resampled to 16 kHz float32."""
    import librosa
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    if not hasattr(_vocal_stem_16k, '_dem'):
        _vocal_stem_16k._dem = get_model('htdemucs')
        _vocal_stem_16k._dem.eval()
    dem = _vocal_stem_16k._dem
    y, _ = librosa.load(str(path), sr=44100, mono=True)
    wav = torch.tensor(y, dtype=torch.float32)[None].repeat(2, 1)[None]
    with torch.no_grad():
        stems = apply_model(dem, wav, device='cpu', progress=False)[0]
    vocals = stems[dem.sources.index('vocals')].mean(0).numpy()
    return librosa.resample(vocals, orig_sr=44100,
                            target_sr=16000).astype('float32')


def transcribe_stem(path: Path, cache: dict) -> str:
    """Demucs vocal stem -> whisper turbo (cached by filename)."""
    if path.name in cache and 'stem_turbo' in cache[path.name]:
        return cache[path.name]['stem_turbo']
    best = _whisper_multi(_vocal_stem_16k(path), langs=(None, 'ta', 'te'))
    cache.setdefault(path.name, {})['stem_turbo'] = best
    _atomic_write_json(SCACHE, cache)
    return best


# ------------------------------------------------------------- ASR cache v2

# Complete ASR configuration identity. Any change here (model, languages,
# decode params, separation) MUST bump the id — stale-key reuse is how a
# scoreboard silently goes stale.
ASR_CONFIG_V2 = {
    'engine': 'openai-whisper',
    'model': 'large-v3-turbo',
    'fp16': False,
    'mix_langs': ['auto', 'ta', 'te', 'hi'],
    'stem_langs': ['auto', 'ta', 'te'],
    'separation': 'htdemucs',
}


def asr_config_id() -> str:
    return 'whisper-turbo|fp16=0|mix:auto,ta,te,hi|stem:htdemucs+auto,ta,te|v2'


def audio_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def cache2_key(sha: str) -> str:
    return f'{sha[:24]}:{asr_config_id()}'


def load_cache_v2() -> dict:
    if CACHE2.exists():
        return json.loads(CACHE2.read_text())
    return {'schema': 'carnatify-asr-cache-v2',
            'config': ASR_CONFIG_V2, 'entries': {}}


def variants_from_v2(entry: dict, view=None) -> dict[str, str]:
    """Legacy longest-wins selection per source, computed on a matching VIEW
    of the raw hypotheses.

    Default view is fold (ASCII), NOT translit_fold: measured 2026-07-22,
    the transliterated view lifts candidate recall hugely (top-5 19->29/78)
    but collapses answered precision 30%->16% because recovered native
    evidence on OOC clips bluffs through the uncalibrated thresholds
    (OOC reject 24/28 -> 2/28). It is a candidate-generation channel gated
    on Phase 4 calibration: opt in via CARNATIFY_V2_TRANSLIT=1."""
    if view is None:
        view = (translit_fold if os.environ.get('CARNATIFY_V2_TRANSLIT')
                else fold)
    best = {'mix': '', 'stem': ''}
    for h in entry['hypotheses']:
        if h['status'] != 'ok':
            continue
        t = view(h['raw'])
        if len(t) > len(best[h['source']]):
            best[h['source']] = t
    return {'turbo': best['mix'], 'stem_turbo': best['stem']}


def identify_v2(path: Path, targets, lyr, cache2: dict,
                want_raga: bool = True) -> dict:
    """identify() against the v2 cache, read-only (eval never mutates it)."""
    key = cache2_key(audio_sha256(path))
    entry = cache2['entries'].get(key)
    if entry is None:
        result = {'file': path.name, 'ragas': [], 'cache_v2': 'MISS',
                  **assess_variants({}, targets, lyr)}
    else:
        result = {'file': path.name, 'ragas': [], 'cache_v2': 'hit',
                  **assess_variants(variants_from_v2(entry), targets, lyr)}
    if want_raga:
        ragas, err = raga_top5(path)
        result['ragas'] = ragas
        if err:
            result['raga_error'] = err
    return result


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

def assess_variants(variants: dict[str, str], targets, lyr=None) -> dict:
    """THE composition policy — single source of truth for CLI and server.

    variants: name -> transcript (matching view); names starting with 'stem'
    are vocal-stem passes. Applies sanitization, usability gates (min length,
    hallucination stoplist, decode-loop run), per-variant matching, variant
    selection (best score, prefer stem within VARIANT_CLOSE), confidence
    tiers, and catalog raga backfill. Both identify() and the backend's
    identify_from_variants() MUST call this; never fork the policy.
    """
    result = {
        'transcript': '',
        'asr_variant': None,
        'compositions': [],
        'composition_confidence': 'none',
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
        if _max_token_run(txt) >= LOOP_RUN:
            continue
        comps, max_rep = match_lyrics(txt, targets, lyr)
        if not comps or max_rep < 2:
            continue
        cands.append((comps[0]['score'], name.startswith('stem'), name,
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
        # catalog backfill: a confident composition match pins the raga far
        # more reliably than the clip RF (wild-clip RF top-1 ~0)
        if (result['composition_confidence'] in ('high', 'medium')
                and comps[0].get('ragas')):
            result['raga_from_catalog'] = comps[0]['ragas']
            result['raga_confidence'] = 'medium (from composition match)'
    else:
        result['transcript'] = (variants.get('turbo')
                                or variants.get('orig') or '')[:200]
    return result


def identify(path: Path, targets, lyr, cache, scache,
             want_raga: bool = True, fast: bool = False) -> dict:
    variants = {'turbo': transcribe(path, cache)}
    if not fast:
        try:
            variants['stem_turbo'] = transcribe_stem(path, scache)
        except Exception as e:
            print(f'  (stem pass failed: {e})', file=sys.stderr)
    result = {'file': path.name, 'ragas': [],
              **assess_variants(variants, targets, lyr)}
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
    use_v2 = '--cache-v2' in sys.argv
    if not args:
        sys.exit('usage: identify_clip.py <audio-file-or-folder> '
                 '[--json] [--no-raga] [--fast] [--cache-v2]')
    target = Path(args[0]).expanduser()
    files = ([target] if target.is_file() else
             sorted(p for p in target.iterdir()
                    if p.suffix.lower() in ('.wav', '.mp3', '.m4a', '.flac')))
    if not files:
        sys.exit(f'no audio files at {target}')

    targets, lyr = load_targets()
    cache = json.loads(TCACHE.read_text()) if TCACHE.exists() else {}
    scache = json.loads(SCACHE.read_text()) if SCACHE.exists() else {}
    cache2 = load_cache_v2() if use_v2 else None
    v2_hits = v2_miss = 0

    def truth_match(pred_title: str, gt: str) -> bool:
        a, b = skey(pred_title), skey(gt)
        return _partial(a, b) >= 90 or _partial(b, a) >= 90

    results = []
    c1 = c5 = r1 = r3 = rc = rc_n = n = ooc_n = ooc_ok = rn = 0
    for p in files:
        if use_v2:
            res = identify_v2(p, targets, lyr, cache2,
                              want_raga=not no_raga)
            if res['cache_v2'] == 'MISS':
                v2_miss += 1
                print(f'  !! v2 cache MISS: {p.name}', file=sys.stderr)
            else:
                v2_hits += 1
        else:
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
            stem = p.stem
            is_ooc = stem.endswith('__OOC')
            if is_ooc:
                stem = stem[: -len('__OOC')]
            gt_title, gt_raga = stem.split('__', 1)
            rf = fold(gt_raga).replace(' ', '')
            raga_known = rf not in ('na', 'unknown')
            rhits = [fold(r['raga']).replace(' ', '') == rf
                     for r in res['ragas']]
            rhit1 = bool(rhits and rhits[0])
            rhit3 = any(rhits[:3])
            # only count raga truth when raga inference actually ran —
            # otherwise --no-raga prints a fake 0/N result
            if raga_known and not no_raga:
                rn += 1
                r1 += rhit1; r3 += rhit3
            raga_txt = (f" | raga top1 {'OK' if rhit1 else '--'} "
                        f"top3 {'OK' if rhit3 else '--'}"
                        if res['ragas'] and raga_known else '')
            if is_ooc:
                ooc_n += 1
                rejected = res['composition_confidence'] == 'none'
                ooc_ok += rejected
                print(f"  TRUTH {gt_title} [{gt_raga}] OOC: "
                      f"{'REJECT OK' if rejected else 'BLUFF'}" + raga_txt)
            else:
                n += 1
                hits = [truth_match(c['title'], gt_title)
                        for c in res['compositions']]
                hit1 = bool(hits and hits[0])
                hit5 = any(hits)
                c1 += hit1; c5 += hit5
                if res.get('raga_from_catalog'):
                    rc_n += 1
                    rc += any(skey(x) == skey(gt_raga)
                              or _partial(skey(x), skey(gt_raga)) >= 90
                              for x in res['raga_from_catalog'])
                print(f"  TRUTH {gt_title} [{gt_raga}]: comp top1 "
                      f"{'OK' if hit1 else '--'} top5 {'OK' if hit5 else '--'}"
                      + raga_txt)
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    elif n or ooc_n:
        print(f"\n===== SCORE over {n} in-catalog + {ooc_n} OOC clips =====")
        print(f"composition top-1 {c1}/{n}  top-5 {c5}/{n}")
        if ooc_n:
            print(f"OOC reject  {ooc_ok}/{ooc_n}  "
                  f"(bluffs: {ooc_n - ooc_ok})")
        if no_raga:
            print("raga        skipped (--no-raga)")
        else:
            print(f"raga        top-1 {r1}/{rn}  top-3 {r3}/{rn}"
                  f"  (clips with known raga truth)")
        if rc_n:
            print(f"raga via catalog backfill {rc}/{rc_n} "
                  f"(on clips with confident composition)")
        if use_v2:
            print(f"v2 cache: {v2_hits} hits, {v2_miss} misses"
                  + ("  ** SCORE INVALID: misses present **"
                     if v2_miss else ""))


if __name__ == '__main__':
    main()
