"""Coverage side of the coverage/accuracy trade: what fraction of what a
listener would actually hear can a tier even name?

Accuracy without coverage is not a product number. `raga_audit_levels.py`
measures how often the model is right *given that the raga is in the tier*; this
measures how often that condition holds. The two multiply into the only
product-relevant quantity, expected hits per 100 heard items.

Two independent priors over "what gets performed", neither of them the training
corpus:

  repertoire mass — `data/scraped_compositions.json`, the scraped concert
      programmes, restricted to the items carrying a `raga_canonical`. This is a
      prior over *items in concert programmes*, which is what a concert
      companion meets.
  wild clips     — the filename raga labels of `~/sung_tests`, folded through
      `data/raga_aliases.json`. Small, and the labels are unaudited (see
      `HANDOFF_SESSION_0731.md` §6.1), so it is reported as a secondary.

Matching is on the same NFKD-folded alphanumeric form the harness itself uses
(`raga_audit_protocol.fold`), so "Tōḍi", "Todi" and "tODi" are one class.

Read-only. Touches no audio, writes only `data/raga_coverage/coverage.json`.
`~/sung_tests` is read as a directory listing; no file in it is opened.

Usage: venv/bin/python scripts/raga_coverage_mass.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from raga_audit_protocol import fold  # noqa: E402

ROOT = HERE.parent
OUT_DIR = ROOT / 'data' / 'raga_coverage'
COMPS = ROOT / 'data' / 'scraped_compositions.json'
ALIASES = ROOT / 'data' / 'raga_aliases.json'
SUNG = Path.home() / 'sung_tests'


def repertoire_counts():
    items = json.loads(COMPS.read_text())
    c = Counter()
    n_total, n_labelled = len(items), 0
    for it in items:
        rc = it.get('raga_canonical')
        if not rc:
            continue
        n_labelled += 1
        c[fold(rc)] += 1
    return c, n_total, n_labelled


def wild_counts():
    """Filename labels only — `<title>__<raga>[__OOC].<ext>`, the convention the
    wild measurement froze on. Directory listing; no audio is read."""
    if not SUNG.is_dir():
        return Counter(), 0, 0
    alias = {fold(k): v for k, v in json.loads(ALIASES.read_text()).items()}
    c = Counter()
    n_total = n_labelled = 0
    for p in sorted(SUNG.iterdir()):
        if p.suffix.lower() not in ('.mp3', '.m4a', '.wav', '.flac', '.ogg'):
            continue
        n_total += 1
        parts = p.stem.split('__')
        if len(parts) < 2:
            continue
        raw = parts[1].strip()
        canon = alias.get(fold(raw), raw)
        if not canon:
            continue
        n_labelled += 1
        c[fold(canon)] += 1
    return c, n_total, n_labelled


def main() -> None:
    inv = json.loads((OUT_DIR / 'inventory.json').read_text())
    rep, rep_total, rep_labelled = repertoire_counts()
    wild, wild_total, wild_labelled = wild_counts()

    out = {
        'repertoire': {'file': str(COMPS.relative_to(ROOT)), 'items': rep_total,
                       'items_with_canonical_raga': rep_labelled,
                       'distinct_ragas': len(rep)},
        'wild': {'dir': str(SUNG), 'clips': wild_total, 'clips_with_label': wild_labelled,
                 'distinct_ragas': len(wild)},
        'tiers': {},
    }
    print(f'repertoire: {rep_labelled}/{rep_total} items carry a canonical raga, '
          f'{len(rep)} distinct ragas')
    print(f'wild:       {wild_labelled}/{wild_total} clips carry a filename label, '
          f'{len(wild)} distinct ragas\n')
    print(f"{'tier':>6} {'classes':>8} {'rep hits':>9} {'rep cov':>8} "
          f"{'wild hits':>10} {'wild cov':>9}")
    for mt, st in inv['tiers'].items():
        keep = {fold(r) for r in st['ragas']}
        rh = sum(v for k, v in rep.items() if k in keep)
        wh = sum(v for k, v in wild.items() if k in keep)
        rc = rh / rep_labelled if rep_labelled else 0.0
        wc = wh / wild_labelled if wild_labelled else 0.0
        out['tiers'][mt] = dict(classes=len(st['ragas']), n_tracks=st['n_tracks'],
                                repertoire_hits=rh, repertoire_coverage=rc,
                                wild_hits=wh, wild_coverage=wc,
                                ragas_absent_from_repertoire=sorted(
                                    r for r in st['ragas'] if fold(r) not in rep))
        print(f"{mt:>6} {len(st['ragas']):>8} {rh:>9} {rc:>7.1%} {wh:>10} {wc:>8.1%}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'coverage.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nwrote {OUT_DIR / 'coverage.json'}")


if __name__ == '__main__':
    main()
