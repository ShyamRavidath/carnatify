#!/usr/bin/env python3
"""Title extraction and registry resolution for the duration probe.

Split out of `duration_probe_cut.py` on 2026-07-28 because the negative-arm
review (`CODEX_NEGATIVE_ARM_REVIEW.md` §2) proved the old one-line extractor
manufactured false negatives:

* `NUM_PREFIX` stripped only **1-3** leading digits, so seven-digit Jamendo ids
  survived into the title (`1224830 aswinsainarain` -> `4830 aswinsainarain`).
  A registry lookup on that string fails for reasons that have nothing to do
  with the recording, and the old negative arm then called the item OOC.
* The filename is not the authoritative title. `data/concert_audio/
  download_manifest.json` carries `file_title_raw`, and for exactly the mangled
  files it holds the real one (`04_khamas_santanagopalakrishnam`).

Two rules govern everything here, and they are not symmetric:

1. **Resolution that feeds TRUTH is exact only.** `resolve_exact()` matches on
   `skey`, the same key the live matcher uses, plus a hand-reviewed alias table
   (`data/duration_probe/title_aliases.json`). No fuzzy matching may ever create
   a truth id; a false merge would silently relabel one work as another.
2. **Resolution that feeds EXCLUSION may be relaxed.** `resolve_relaxed()`
   matches a consonant-skeleton key with a small edit-distance budget. Its only
   sanctioned use is to *disqualify* an item from the OOC stratum. Over-matching
   there costs sample size, never validity, so the error direction is safe.
   `audit_relaxed_collisions()` publishes what that key over-merges.

The three contaminated items from the review are the calibration set: all three
fail exact `skey` on transliteration variance alone
(`krishnam`/`krSNam` is a vowel insertion, `payuthey`/`pAyudE` is t/d plus a
trailing glide, `chinnan`/`chinnam` is a nasal), and all three are caught by
`resolve_relaxed`.
"""
import json
import re
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identify_clip import fold, skey  # noqa: E402

REGISTRY = ROOT / 'data' / 'composition_registry.json'
RAGA_ALIASES = ROOT / 'data' / 'raga_aliases.json'
MANIFEST = ROOT / 'data' / 'concert_audio' / 'download_manifest.json'
ALIAS_TABLE = ROOT / 'data' / 'duration_probe' / 'title_aliases.json'

# Any number of leading digits, and the track-range forms the archive uses
# ("29-30 72_...", "15-16_...", "27-28 -72_...").
NUM_PREFIX = re.compile(r'^[\d]+(?:\s*[-–]\s*\d+)*[\s._\-]*')
REND_SUFFIX = re.compile(r'_r\d+$')
AUDIO_EXT = re.compile(r'\.(?:mp3|MP3|flac|wav|m4a|ogg)$')
SEGMENT_SPLIT = re.compile(r'\s+[-–]\s+|_|\s*\|\s*')

# Genuinely free-form / percussion items: no fixed composition to identify.
# mangalam, tillana, viruttam and sloka are deliberately NOT here -- they carry
# fixed text and go through normal registry resolution.
NON_COMP = {'alapana', 'rtp', 'thani', 'thaniavarthanam', 'ragamtanampallavi',
            'tanam', 'raga', 'ragam', 'pallavi', 'niraval', 'swaram',
            'kalpanaswaram'}

# Filename stems that name a slot in an archive, not a work. When the filename
# is one of these the manifest title is used instead.
GENERIC_STEM = re.compile(
    r'^(?:track|concert|disc|side|part|cd|vol|volume|untitled|audio|file)\b'
    r'|^[a-z]{1,2}$|^x+$', re.I)

# Structural / instrumental words that are never a composition title on their
# own. Used only to reject a *segment* as a title candidate.
SEGMENT_STOPWORDS = NON_COMP | {
    'melakartha', 'melakartachakkaram', 'melakarthachakkaram', 'chakkaram',
    'chakram', 'lecdem', 'lecturedemonstration', 'vocal', 'veena', 'veenai',
    'violin', 'flute', 'mandolin', 'whistle', 'nadaswaram', 'applause',
    'tuning', 'announcement', 'intro', 'introduction', 'presents', 'live',
    'concert', 'track', 'adi', 'rupakam', 'misrachapu', 'khandachapu',
    'chapu', 'tisram', 'ata', 'atatala', 'talam', 'tala',
    # forms, not titles: `01_varnam_vasantha` names a raga and a genre and no
    # work at all, and must not become the "title" `varnam`
    'varnam', 'varnams', 'kriti', 'krithi', 'keerthanam', 'kirtanam',
    'geetham', 'ragamalika', 'slokam', 'sloka', 'viruttam',
}

MIN_SEGMENT_CHARS = 5      # below this a segment is not evidence of a title


# --------------------------------------------------------------------------
# keys
# --------------------------------------------------------------------------

def cskel(s: str) -> str:
    """Consonant-skeleton key. EXCLUSION USE ONLY -- never builds a truth id.

    Absorbs the three transliteration axes the review's counterexamples turn
    on, in this order: inherent-vowel insertion (`krishnam`/`krSNam`), voicing
    (`payuthey`/`pAyudE`), and nasal place (`chinnan`/`chinnam`). Gemination is
    collapsed last because the earlier steps can create new doubles.
    """
    k = re.sub(r'[aeiou]', '', skey(s))
    k = k.translate(str.maketrans('dbgjmz', 'tpkcns'))
    return re.sub(r'(.)\1+', r'\1', k)


def edit_distance(a: str, b: str, cap: int = 2) -> int:
    """Levenshtein, short-circuited at `cap` (returns cap + 1 when over)."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


# --------------------------------------------------------------------------
# vocabularies
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def raga_vocab() -> frozenset:
    """skey of every raga name we know, from the reviewed alias file.

    Junk keys (dates, years) map to null in `raga_aliases.json` and are
    dropped -- `HANDOFF_CLIP_ID.md` §8 is explicit that registry raga metadata
    is not trustworthy on its own.
    """
    out = set()
    if RAGA_ALIASES.exists():
        for alias, canon in json.loads(RAGA_ALIASES.read_text()).items():
            if not canon:
                continue
            for name in (alias, canon):
                k = skey(name)
                if len(k) >= 3:
                    out.add(k)
    return frozenset(out)


@lru_cache(maxsize=1)
def composer_vocab() -> frozenset:
    out = set()
    for row in json.loads(REGISTRY.read_text()):
        for c in row.get('composers') or []:
            for token in re.split(r'[\s,/]+', c or ''):
                k = skey(token)
                if len(k) >= 4:
                    out.add(k)
    return frozenset(out)


@lru_cache(maxsize=1)
def manifest_rows() -> dict:
    """relative file path -> manifest row."""
    if not MANIFEST.exists():
        return {}
    return {r['file_path']: r
            for r in json.loads(MANIFEST.read_text()) if r.get('file_path')}


@lru_cache(maxsize=1)
def reviewed_aliases() -> dict:
    """skey(title) -> registry id, hand-reviewed. Truth-bearing, so explicit.

    Empty until someone reviews a proposed row; `--propose-aliases` writes the
    candidate list. Nothing here is generated automatically.
    """
    if not ALIAS_TABLE.exists():
        return {}
    raw = json.loads(ALIAS_TABLE.read_text())
    return {skey(k): v['registry_id'] for k, v in raw.items()
            if isinstance(v, dict) and v.get('status') == 'accepted'
            and v.get('registry_id')}


# --------------------------------------------------------------------------
# title candidates
# --------------------------------------------------------------------------

def clean(s: str) -> str:
    s = AUDIO_EXT.sub('', REND_SUFFIX.sub('', (s or '').strip()))
    return NUM_PREFIX.sub('', s.replace('_', ' ')).strip(' .-_')


def _segment_ok(seg: str) -> bool:
    k = skey(seg)
    return (len(k) >= MIN_SEGMENT_CHARS
            and not k.isdigit()
            and k not in SEGMENT_STOPWORDS
            and k not in raga_vocab()
            and k not in composer_vocab())


def candidates(stem: str, raw_title: str | None) -> list[dict]:
    """Every string that could be this recording's composition title.

    Ordered: filename first (the corpus's own cleaned title, right ~99% of the
    time), then the manifest raw title whole, then its segments. Provenance is
    carried so callers can prefer the conservative sources.
    """
    out, seen = [], set()

    def add(text, source):
        t = clean(text)
        k = skey(t)
        # A section name is never a work. Without this, `Alapana.mp3` resolves
        # to comp00196 (canonical "Alapana", 19 ragas, no lyrics — already on
        # the reviewed junk blocklist) and `rAgam tAnam pallavi.mp3` to
        # comp06030, and free-form files would be reported as in-catalog.
        if not t or len(k) < 3 or k in seen or k in NON_COMP:
            return
        seen.add(k)
        out.append({'title': t, 'key': k, 'source': source})

    add(stem, 'filename')
    if raw_title:
        add(raw_title, 'manifest_raw')
        for seg in SEGMENT_SPLIT.split(AUDIO_EXT.sub('', raw_title)):
            seg = clean(seg)
            if seg and _segment_ok(seg):
                add(seg, 'manifest_segment')
    return out


def primary_title(stem: str, raw_title: str | None) -> tuple[str, str]:
    """The one title the POOL builder resolves. Conservative by construction.

    The filename wins unless it is demonstrably not a title: still numeric
    after prefix stripping (the Jamendo/lecdem id case), a generic archive slot
    name (`Track 02`, `Concert 163`, `A`, `B`, `xxxx`), or too short to carry
    one. Only then does the manifest supply it, and then only through the
    longest surviving segment -- the whole raw string usually carries the raga
    and composer as well, which no registry title contains.

    Returns (title, provenance).
    """
    stem_title = clean(stem)
    # A free-form marker (`RTP`, `Alapana`) IS the filename's answer and must
    # survive: these files have no composition to identify, and letting the
    # manifest overwrite `RTP` with `RTP - dwijAvanti` would quietly delete the
    # whole no-sahitya candidate source.
    if skey(stem_title) in NON_COMP:
        return stem_title, 'filename'
    # A stripped four-plus-digit prefix means the filename was an archive/upload
    # id, not a curated title. What follows it is then usually an uploader or
    # channel name (`1224830 aswinsainarain`), which resolves or fails for
    # reasons having nothing to do with the recording — the exact defect that
    # produced the invalid OOC arm. Distrust the whole stem in that case.
    long_id = re.match(r'^\d{4,}', stem.strip())
    mangled = (not stem_title
               or long_id
               or re.match(r'^\d', stem_title)
               or GENERIC_STEM.match(stem_title)
               or len(skey(stem_title)) < 4)
    if not mangled:
        return stem_title, 'filename'

    segs = [c for c in candidates(stem, raw_title)
            if c['source'] == 'manifest_segment']
    if segs:
        best = max(segs, key=lambda c: len(c['key']))
        return best['title'], 'manifest_segment'
    whole = clean(raw_title or '')
    if whole and not GENERIC_STEM.match(whole):
        return whole, 'manifest_raw'
    return stem_title, 'filename_unrecoverable'


# --------------------------------------------------------------------------
# resolution
# --------------------------------------------------------------------------

def registry_index() -> tuple[dict, dict]:
    """(rows_by_skey, rows_by_cskel), both id-deduped.

    Deduping by id is the fix from the previous round: a row whose canonical
    and alias fold to the same key used to appear twice and be called
    ambiguous.
    """
    by_key: dict[str, dict[str, dict]] = defaultdict(dict)
    by_skel: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in json.loads(REGISTRY.read_text()):
        for name in [row['canonical']] + list(row.get('aliases') or []):
            if not name:
                continue
            by_key[skey(name)][row['id']] = row
            by_skel[cskel(name)][row['id']] = row
    return by_key, by_skel


def resolve_exact(cands, by_key, alias_table=None) -> dict:
    """cand key -> registry rows, exact `skey` plus the reviewed alias table."""
    alias_table = reviewed_aliases() if alias_table is None else alias_table
    hits = {}
    for c in cands:
        rows = dict(by_key.get(c['key'], {}))
        aliased = alias_table.get(c['key'])
        if aliased:
            for rid, row in ((rid, row) for d in by_key.values()
                             for rid, row in d.items() if rid == aliased):
                rows[rid] = row
        if rows:
            hits[c['key']] = rows
    return hits


def resolve_relaxed(cands, by_skel, budget: int = 1) -> dict:
    """cand key -> near registry rows. EXCLUSION ONLY -- never a truth id.

    Exact skeleton hits first; then a bounded edit-distance sweep over the
    skeleton space, which is what catches `alaipayuthey` -> `alai pAyudE`.
    """
    hits = {}
    skels = list(by_skel)
    for c in cands:
        cs = cskel(c['title'])
        if len(cs) < 4:
            continue
        rows = dict(by_skel.get(cs, {}))
        if not rows and budget:
            for s in skels:
                if abs(len(s) - len(cs)) <= budget and \
                        edit_distance(s, cs, budget) <= budget:
                    rows.update(by_skel[s])
        if rows:
            hits[c['key']] = rows
    return hits


def audit_relaxed_collisions(by_key, by_skel) -> dict:
    """What `cskel` over-merges, published because §7.2 requires it.

    Counts registry *works* (ids) that share a skeleton with a different id.
    Every collision makes the OOC filter stricter, never looser, so this is a
    cost-of-recall report rather than a validity threat -- but it has to be on
    the record before the key is used.
    """
    # Skeletons shorter than 4 are never consulted (see resolve_relaxed), so
    # counting their collisions would overstate the cost by an order of
    # magnitude -- they are the ones where a 5-letter title loses everything.
    usable = {s: d for s, d in by_skel.items() if len(s) >= 4}
    multi = {s: sorted(d) for s, d in usable.items() if len(d) > 1}
    exact_multi = {k: sorted(d) for k, d in by_key.items() if len(d) > 1}
    return {
        'registry_names_indexed': len(by_key),
        'distinct_skeletons': len(by_skel),
        'skeletons_consulted (len >= 4)': len(usable),
        'skeletons_covering_multiple_ids': len(multi),
        'ids_touched_by_a_collision': len({i for v in multi.values()
                                           for i in v}),
        'short_skeletons_never_consulted': len(by_skel) - len(usable),
        'exact_skey_already_multi_id': len(exact_multi),
        'examples': dict(sorted(multi.items(),
                                key=lambda kv: -len(kv[1]))[:10]),
    }


def main() -> None:
    """`python scripts/duration_probe_titles.py` prints the audit."""
    by_key, by_skel = registry_index()
    audit = audit_relaxed_collisions(by_key, by_skel)
    print('=== relaxed-key (cskel) false-merge audit ===')
    for k, v in audit.items():
        if k != 'examples':
            print(f'  {k:38s} {v}')
    print('\n  worst skeleton collisions (ids sharing one skeleton):')
    for s, ids in audit['examples'].items():
        print(f'    {s:24s} {len(ids)} ids  {ids[:6]}')

    print('\n=== calibration set from CODEX_NEGATIVE_ARM_REVIEW §2 ===')
    for probe, want in (('santanagopalakrishnam', 'santAna gOpAlakrSNam'),
                        ('alaipayuthey', 'alai pAyudE'),
                        ('chinnanchiru kiliye', 'chinnam ciru kiLiyE')):
        cands = [{'title': probe, 'key': skey(probe), 'source': 'probe'}]
        ex = resolve_exact(cands, by_key)
        rel = resolve_relaxed(cands, by_skel)
        ids = sorted({i for d in rel.values() for i in d})
        print(f'  {probe:24s} exact={"HIT" if ex else "miss":4s} '
              f'relaxed={"HIT" if rel else "MISS"} -> {ids[:4]} '
              f'(want a row like {want!r})')


if __name__ == '__main__':
    main()
