#!/usr/bin/env python3
"""Junk-row detector + filter for `data/composition_registry.json`.

The scraper that built the registry parsed some *concert-page* lines as if they
were compositions: postal addresses, broadcast dates, venue names, tape catalog
numbers, and the artist-index headings of the source pages.  They carry no
composer, no karnatik lyrics page, and their `ragas` slot holds a date or a
performance role instead of a raga (memory `registry-junk-entries`; handoff
§4.19).  `data/registry_junk_blocklist_DRAFT.md` is the human review of the
first 24 such rows.

This module is the machine-readable half of that review:

  * `detect()`  -- re-derives junk candidates from the registry with named,
                   auditable rules.  Nothing is hard-coded to an id, so the
                   detector keeps working if the registry is ever rebuilt
                   (which reshuffles every `comp#####` -- handoff §4.18).
  * `blocklist_ids()` -- the *reviewed* drop set, read from
                   `data/registry_junk_blocklist.json`.  Only rows a human
                   marked `drop` are in it; `review` rows are reported and
                   never filtered.
  * `filter_targets()` -- drops those ids from `identify_clip.load_targets()`
                   output.

Nothing here is wired into `identify_clip.py`.  Applying the blocklist is
behaviour-changing (it also shifts the IDF denominator) and therefore needs its
own SCORE block on the frozen wild set before it can graduate -- see
`scripts/registry_junk_ab.py` for the measurement.

CLI
    python scripts/registry_junk_filter.py            # audit the registry
    python scripts/registry_junk_filter.py --verbose  # + every flagged row
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / 'data' / 'composition_registry.json'
BLOCKLIST = ROOT / 'data' / 'registry_junk_blocklist.json'

# --------------------------------------------------------------- rule corpus

_MONTH = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*'
_CITY = (r'(?:Mysore|Chennai|Madras|Delhi|Bangalore|Bengaluru|Mumbai|Bombay|'
         r'Boston|Hyderabad|Pune|Kolkata|Calcutta|Trivandrum|Coimbatore|'
         r'Cleveland|New\s+York|London|Toronto)')

# A raga slot holding one of these is not a raga at all.
_DATE_PATTERNS = (
    re.compile(rf'^\s*{_MONTH}\s+\d{{1,2}}\s*,?\s*(?:19|20)\d{{2}}\s*$', re.I),
    re.compile(rf'^\s*\d{{1,2}}\s+{_MONTH}\s*,?\s*(?:19|20)\d{{2}}\s*$', re.I),
    re.compile(r'^\s*(?:19|20)\d{2}\s*$'),
    re.compile(r'^\s*\d{1,2}[-/]\d{1,2}[-/](?:19|20)\d{2}\s*$'),
)
_ROLE = re.compile(
    r'^\s*(?:Vocal|Violin|Mridangam|Mrudangam|Ghatam|Flute|Veena|Vina|'
    r'Gottuvadyam|Nagaswaram|Nadaswaram|Dance\s+Music|Instrumental|Konnakol|'
    r'Morsing|Tabla|Kanjira)\b[\s\-–]*$', re.I)

_TITLE_RULES = {
    # 8th Cross, V V Mohalla, Mysore
    'title_address': re.compile(
        rf'\b\d+(?:st|nd|rd|th)\s+(?:Cross|Main|Street|Ave)\b|\bMohalla\b'
        rf'|,\s*{_CITY}\s*$', re.I),
    # AIR Chennai / AIR National Program
    'title_broadcast': re.compile(
        r'^\s*AIR\b|\bAIR\s+(?:Chennai|Madras|National|Sangeeth)', re.I),
    # Concerts with M Chandrasekaran / Wedding concert
    'title_concert': re.compile(r'\bconcerts?\b', re.I),
    # Karnataka Sangeeta Sabha, Delhi / At MIT, Boston / Kapali Koil / Mysore
    # The bare-city arm is anchored at BOTH ends on purpose: 'Bangalore Thaye
    # Dharini' and 'Coimbatore Thaye' are real kritis wearing a performer's
    # city prefix, and a leading-city-only rule swallowed them.
    'title_venue': re.compile(
        rf'\b(?:Sabha|Auditorium|Gurukulam|Koil|Kovil|Temple|Hall)\b'
        rf'|^\s*At\s+\w+|^\s*{_CITY}\s*(?:\(|$)', re.I),
    # G 2437-B JM 2373 ... / VOL MSG AIR oct 20004 RTP
    'title_tape_catalog': re.compile(r'\b[A-Z]{1,4}\s?\d{3,5}(?:-[A-Z])?\b'),
    # Long Alapana (lead up to RTP) / Muffled RTP / DKP DKJ RTP / Unidentified
    'title_perf_note': re.compile(
        r'^\s*(?:Long\s+)?Alapana\b|^\s*Muffled\b|^\s*RTP\b|\bRTP\s*$'
        r'|^\s*Unidentified\s*$|^\s*Thani\b|^\s*Tanam\b', re.I),
    # "Below are the recordings in no particular order"
    'title_prose': re.compile(
        r'^\s*(?:Below|Above|Click|Please|Note)\b|\bare\s+the\b', re.I),
}


def _norm(s: str) -> str:
    """NFC + collapsed whitespace -- APFS hands us NFD (handoff §4.6)."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', s)).strip()


def _has_evidence(row: dict) -> bool:
    """True when something other than the scraper's title vouches for the row.

    A composer attribution, a karnatik lyrics page, or stored lyrics all mean a
    second source treated this as a work.  Junk rows have none of the three,
    so this is the hard gate every rule sits behind -- no row with real
    evidence can ever be flagged, whatever its title looks like.
    """
    return bool(row.get('composers') or row.get('karnatik_pages')
                or row.get('has_lyrics'))


def rules_for(row: dict) -> list[str]:
    """Names of the junk rules a registry row trips (empty == looks real)."""
    if _has_evidence(row):
        return []
    fired = []
    ragas = [_norm(g) for g in row.get('ragas', []) if _norm(g)]
    if ragas and all(any(p.match(g) for p in _DATE_PATTERNS) for g in ragas):
        fired.append('raga_is_date')
    if ragas and all(_ROLE.match(g) for g in ragas):
        fired.append('raga_is_role')
    canonical = _norm(row.get('canonical', ''))
    fired += [name for name, pat in _TITLE_RULES.items()
              if pat.search(canonical)]
    return fired


def detect(registry: list[dict] | None = None) -> dict[str, dict]:
    """id -> {canonical, ragas, rules} for every row the rules flag."""
    if registry is None:
        registry = json.loads(REGISTRY.read_text())
    out = {}
    for row in registry:
        fired = rules_for(row)
        if fired:
            out[row['id']] = {'canonical': row['canonical'],
                              'ragas': row.get('ragas', []),
                              'rules': fired}
    return out


# ------------------------------------------------------------ reviewed list

def load_blocklist() -> dict:
    """The reviewed blocklist file, or an empty shell when it is absent."""
    if not BLOCKLIST.exists():
        return {'rows': {}}
    return json.loads(BLOCKLIST.read_text())


def blocklist_ids(status: str = 'drop') -> set[str]:
    """Registry ids a human reviewed and marked with `status`.

    Only `drop` is filtered.  `review` rows (RTP items, alapana descriptions --
    things that are performance items rather than catalogable works) stay in
    the catalog until Deepti rules on them.
    """
    return {i for i, r in load_blocklist().get('rows', {}).items()
            if r.get('status') == status}


def filter_targets(entries: list[dict], ids: set[str] | None = None
                   ) -> list[dict]:
    """Drop blocklisted rows from `identify_clip.load_targets()` entries.

    Entries carry the registry `id`; the legacy no-registry fallback path sets
    it to None and is therefore left untouched.
    """
    drop = blocklist_ids() if ids is None else ids
    return [e for e in entries if e.get('id') not in drop]


# --------------------------------------------------------------------- CLI

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--verbose', action='store_true',
                    help='print every flagged row, grouped by review status')
    args = ap.parse_args()

    registry = json.loads(REGISTRY.read_text())
    found = detect(registry)
    reviewed = load_blocklist().get('rows', {})

    by_status: dict[str, list[str]] = {}
    for cid in sorted(found):
        status = reviewed.get(cid, {}).get('status', 'UNREVIEWED')
        by_status.setdefault(status, []).append(cid)

    print(f'registry rows      {len(registry)}')
    print(f'no-evidence rows   '
          f'{sum(1 for r in registry if not _has_evidence(r))}')
    print(f'flagged by rules   {len(found)}')
    for status in sorted(by_status):
        print(f'  {status:<12} {len(by_status[status])}')

    stale = sorted(set(reviewed) - set(found))
    if stale:
        print(f'\nreviewed ids the rules no longer flag ({len(stale)}): '
              f'{", ".join(stale)}')

    if args.verbose:
        for status in sorted(by_status):
            print(f'\n--- {status} ---')
            for cid in by_status[status]:
                row = found[cid]
                print(f'  {cid} | {row["canonical"][:58]!r} | '
                      f'ragas={row["ragas"][:2]} | {",".join(row["rules"])}')

    if 'UNREVIEWED' in by_status:
        print('\nUNREVIEWED rows are NOT filtered. Add them to '
              f'{BLOCKLIST.name} with a status before they take effect.')
        sys.exit(1)


if __name__ == '__main__':
    main()
