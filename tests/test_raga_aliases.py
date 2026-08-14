"""Regression tests for the eight live wrong merges in `data/raga_aliases.json`.

`data/RAGA_MERGE_DECISIONS.md` §"What needs no ruling and should be fixed
anyway" lists eight aliases that map a raga onto a **different** raga. They are
not equivalence questions — they are mistakes, and 17 scraped programme items
ride them.

The repair needs no musical adjudication, and these tests are why: for every one
of the eight, **the alias map already contains the right answer under a
different spelling of the same name**. `'AbhEri'`, `'Abheri'` and `'abheri'` all
map to `None`; only `'AbEri'` maps to `'Sāvēri'`. So the fix is not a judgment
about what Ābhēri is, it is making one key agree with its own siblings.

That is the invariant these tests encode: a raga-name family in the alias map
must not contain both a `None` and a canonical value. A future scrape, a fuzzy
match at the 0.6 difflib cutoff, or a hand edit that re-introduces any of these
will fail here rather than silently mislabelling concert items.

Run with the three named suites (`handoff.md` §2f):
    venv_train/bin/python -m pytest tests/test_clip_policy.py \
        tests/test_registry_junk.py tests/test_negative_arm.py \
        tests/test_raga_aliases.py -q
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ALIASES = ROOT / 'data' / 'raga_aliases.json'


def fold(name: str) -> str:
    d = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


@pytest.fixture(scope='module')
def aliases() -> dict:
    return json.loads(ALIASES.read_text())


# The eight documented wrong merges, and what each was wrongly merged INTO.
# `garuDwani`/`garudwani` are the same alias in two cases, and `navarasas
# kannaDa`/`navasrasa kannaDA` are two typos of one name — both pairs carried the
# same wrong value. So the eight documented aliases are TEN keys. The tenth,
# `navasrasa kannaDA`, was found by the repair itself rather than by the audit:
# it sits two lines below its twin in the file and carries the identical wrong
# target, with the same unanimous null siblings.
WRONG_MERGES = {
    'AbEri': 'Sāvēri',
    'garuDwani': 'Kāmavardani',
    'garudwani': 'Kāmavardani',
    'sunAdavinOdhini': 'Jaganmōhini',
    'navarasas kannaDa': 'Bṛndāvana sāranga',
    'navasrasa kannaDA': 'Bṛndāvana sāranga',
    'gaulipantu': 'Gauḷa',
    'jayantasri': 'Dhanaśrī',
    'nalainakAnti': 'Kalāvati',
    'veera vasanatam': 'Vasanta',
}

# Each repaired key, with the sibling spellings that already agree it is
# unresolved. The sibling list is the *evidence* the repair needed no ruling.
FAMILIES = {
    'AbEri': ['AbhEri', 'Abheri', 'abheri'],
    'garuDwani': ['garuDadwani'],
    'garudwani': ['garuDadwani'],
    'sunAdavinOdhini': ['sunAda vinOdini', 'sunAdavinOdini', 'sunAdavonOdini',
                        'sunadavonodini'],
    'navarasas kannaDa': ['navarasa kannaDA', 'navarasakannaDA',
                          'navasrasa kannaDA'],
    'navasrasa kannaDA': ['navarasa kannaDA', 'navarasakannaDA',
                          'navarasas kannaDa'],
    'jayantasri': ['jayantasree'],
    'nalainakAnti': ['naLinakAnti', 'naliNakAnti', 'nalinakAnti'],
    'veera vasanatam': ['veera vasantam', 'veeravasantam', 'Veera Vasantham',
                        'veera vasantam (diff concert ?)'],
    # `gaulipantu` has no sibling spelling in the map. It is repaired on the
    # plain musical fact that Gaulipantu is not Gauḷa, which is the one entry
    # here that rests on a name rather than on the map's own testimony.
    'gaulipantu': [],
}


@pytest.mark.parametrize('key', sorted(WRONG_MERGES))
def test_wrong_merge_is_repaired(aliases, key):
    """The eight documented aliases (ten keys) must resolve to None."""
    assert key in aliases, f'{key!r} vanished from the alias map entirely'
    assert aliases[key] is None, (
        f'{key!r} maps to {aliases[key]!r}; it was wrongly merged into '
        f'{WRONG_MERGES[key]!r} and must be unresolved (None) instead. '
        f'See data/RAGA_MERGE_DECISIONS.md.'
    )


@pytest.mark.parametrize('key,siblings', sorted(FAMILIES.items()))
def test_family_is_internally_consistent(aliases, key, siblings):
    """No raga-name family may hold both a None and a canonical value.

    This is the invariant that makes the repair self-evident rather than a
    ruling: every sibling spelling already said None.
    """
    present = [s for s in siblings if s in aliases]
    disagreeing = {s: aliases[s] for s in present if aliases[s] is not None}
    assert not disagreeing, (
        f'{key!r} is unresolved but its sibling spellings disagree: '
        f'{disagreeing}. A raga-name family must be internally consistent.'
    )


def test_no_key_reintroduces_a_documented_wrong_target(aliases):
    """Catch the mistake coming back under a spelling nobody has seen yet.

    Any *new* key that folds to one of the repaired names must not acquire the
    wrong canonical value. This is the test that survives the next scrape.
    """
    repaired_folds = {fold(k) for k in WRONG_MERGES}
    # the fold of a family member is the fold of the family name
    for fam, sibs in FAMILIES.items():
        repaired_folds.update(fold(s) for s in sibs)

    offenders = {
        k: v for k, v in aliases.items()
        if v is not None and fold(k) in repaired_folds
    }
    assert not offenders, (
        f'these keys fold to a repaired raga name but carry a canonical '
        f'value: {offenders}'
    )


def test_the_repair_did_not_touch_anything_else(aliases):
    """Exactly ten keys changed. Guards against a bulk edit riding along."""
    n_null = sum(1 for v in aliases.values() if v is None)
    assert len(aliases) == 958, (
        f'alias map has {len(aliases)} keys, expected 958 — the repair must not '
        f'add or remove keys, only change ten values'
    )
    assert n_null == 274 + 10, (
        f'{n_null} null values, expected {274 + 10} (274 before the repair, plus '
        f'the ten repaired keys). A different count means something else moved.'
    )


def test_flagged_but_not_repaired_is_still_flagged(aliases):
    """`garuDadhwani -> Śuddadhanyāsi` looks like a further instance.

    It is NOT repaired, and unlike `navasrasa kannaDA` it is not a typo of a
    name the map already resolves to None — it asserts a specific and different
    raga, so repairing it is a musical claim rather than a bookkeeping one. It is
    outside the eight the verifier seat verified, and
    scope creep in an alias map is how wrong merges got here. This test pins the
    current value so the open question cannot be silently closed in either
    direction — see data/RAGA_MERGE_DECISIONS.md.
    """
    assert aliases.get('garuDadhwani') == 'Śuddadhanyāsi', (
        'garuDadhwani changed value. If it was deliberately repaired, move it '
        'into WRONG_MERGES and update data/RAGA_MERGE_DECISIONS.md; do not just '
        'edit this test.'
    )
