"""Identifier families for the raga contamination audit's registered (c') sensitivity.

`data/qmax_audit/provenance.json` resolved an `archive_identifier` for all 1,232
melodia contours, but two identifiers can still be one upload under two
spellings — `78RPM-Chittor-V-Nagaiah` / `78RPM-ChittoorVNagaiah` is the case
found by the Qmax audit. The brief registers a *sensitivity*, non-gating:
two identifiers are one family when their folded forms score
`rapidfuzz.fuzz.ratio >= 85`.

`rapidfuzz` lives only in `venv_train` (py3.11), so the family map is computed
here once and written to disk for `raga_audit_protocol.py` to consume. Nothing
in this file reads a feature or produces a score.

Read-only. Writes `data/raga_audit/ident_families.json`.

Usage: venv_train/bin/python scripts/raga_audit_families.py
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
PROVENANCE = ROOT / 'data' / 'qmax_audit' / 'provenance.json'
OUT_DIR = ROOT / 'data' / 'raga_audit'
THRESHOLD = 85


def fold(s: str) -> str:
    d = unicodedata.normalize('NFKD', s)
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in t.lower() if c.isalnum())


class DSU:
    def __init__(self):
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def main() -> None:
    prov = json.loads(PROVENANCE.read_text())
    idents = sorted({r['archive_identifier'] for r in prov if r['archive_identifier']})
    folded = {i: fold(i) for i in idents}

    dsu = DSU()
    for i in idents:
        dsu.find(i)
    pairs = []
    for a in range(len(idents)):
        for b in range(a + 1, len(idents)):
            ia, ib = idents[a], idents[b]
            r = fuzz.ratio(folded[ia], folded[ib])
            if r >= THRESHOLD:
                dsu.union(ia, ib)
                pairs.append([ia, ib, round(float(r), 2)])

    fam = {i: dsu.find(i) for i in idents}
    n_fam = len(set(fam.values()))
    print(f'{len(idents)} identifiers -> {n_fam} families '
          f'({len(pairs)} pairs at fuzz.ratio >= {THRESHOLD})')
    for a, b, r in sorted(pairs, key=lambda x: -x[2]):
        print(f'  {r:6.2f}  {a}  ~  {b}')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'ident_families.json').write_text(json.dumps(
        {'threshold': THRESHOLD, 'n_identifiers': len(idents), 'n_families': n_fam,
         'pairs': pairs, 'family_of': fam}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
