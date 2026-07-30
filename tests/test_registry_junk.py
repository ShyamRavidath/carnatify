"""Contract tests for the registry junk-row detector and blocklist.

The filter removes catalog rows, so a bug here silently deletes real works from
the matcher's search space. These tests pin the two properties that matter:
the evidence gate can never fire on a real work, and the reviewed blocklist
stays in sync with what the rules actually flag.

Run: venv_train/bin/python -m pytest tests/test_registry_junk.py -q
(reads the registry + manifest JSONs; no audio, no ASR)
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# root FIRST: backend/ holds a deploy-time copy of identify_clip.py that must
# never shadow the live root module (handoff §4.13)
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import registry_junk_filter as rj  # noqa: E402

# The 24 rows hand-reviewed in data/registry_junk_blocklist_DRAFT.md.
DRAFT_DROP = [
    'comp00000', 'comp00154', 'comp00155', 'comp00639', 'comp00929',
    'comp01203', 'comp01204', 'comp01205', 'comp01206', 'comp01207',
    'comp01208', 'comp01434', 'comp01994', 'comp03347', 'comp04505',
    'comp04506', 'comp04513', 'comp08399', 'comp08602',
]
DRAFT_REVIEW = ['comp03790', 'comp04416', 'comp04821', 'comp06305',
                'comp06306']

# Real works that sit next to the junk and must survive every rule. The first
# three are the truncated-stub titles the DRAFT explicitly rules out of scope
# (they are a work-family concern, not junk); the last three are real kritis
# wearing a performer's city prefix, which an earlier leading-city rule ate.
MUST_KEEP = ['comp06166', 'comp01842', 'comp00019', 'comp06052', 'comp04571',
             'comp00744', 'comp00837', 'comp00838', 'comp01200']


@pytest.fixture(scope='module')
def registry():
    return json.loads((ROOT / 'data' / 'composition_registry.json').read_text())


@pytest.fixture(scope='module')
def by_id(registry):
    return {r['id']: r for r in registry}


@pytest.fixture(scope='module')
def flagged():
    return rj.detect()


# ------------------------------------------------------------ evidence gate

def test_evidence_gate_blocks_every_attributed_row(registry):
    """No row with a composer, a lyrics page, or stored lyrics is ever flagged.

    This is the property that makes the rules safe to loosen: a title regex
    can be wrong, but it can only be wrong about rows nothing else vouches
    for.
    """
    attributed = [r for r in registry if rj._has_evidence(r)]
    assert len(attributed) > 7000, 'registry looks wrong, not the filter'
    assert [r['id'] for r in attributed if rj.rules_for(r)] == []


def test_real_works_are_not_flagged(by_id):
    for cid in MUST_KEEP:
        assert cid in by_id, f'{cid} missing — registry was rebuilt?'
        assert rj.rules_for(by_id[cid]) == [], (
            f'{cid} {by_id[cid]["canonical"]!r} is a real work')


def test_flagged_rows_are_a_small_minority(flagged, registry):
    assert 0 < len(flagged) < len(registry) * 0.01


# ------------------------------------------------------------------- recall

def test_every_hand_reviewed_draft_row_is_detected(flagged):
    missed = [c for c in DRAFT_DROP + DRAFT_REVIEW if c not in flagged]
    assert missed == [], f'rules regressed on reviewed junk: {missed}'


@pytest.mark.parametrize('cid,rule', [
    ('comp00000', 'title_address'),      # 8th Cross, V V Mohalla, Mysore
    ('comp00154', 'title_broadcast'),    # AIR Chennai
    ('comp01205', 'title_concert'),      # Concerts with M Chandrasekaran
    ('comp03347', 'raga_is_date'),       # "raga" = Oct 19, 1985
    ('comp04506', 'raga_is_role'),       # "raga" = Vocal
    ('comp01994', 'title_tape_catalog'), # G 2437-B JM 2373 ...
    ('comp04416', 'title_perf_note'),    # Muffled RTP
])
def test_named_rule_fires_on_its_example(flagged, cid, rule):
    assert rule in flagged[cid]['rules']


# --------------------------------------------------------- blocklist wiring

def test_blocklist_covers_every_detection(flagged):
    """Detector and reviewed file must not drift apart.

    A new flag with no recorded decision would sit unfiltered and unnoticed;
    a recorded id the rules stopped flagging means a rule regressed.
    """
    reviewed = set(rj.load_blocklist()['rows'])
    assert sorted(set(flagged) - reviewed) == [], 'undecided detections'
    assert sorted(reviewed - set(flagged)) == [], 'stale blocklist rows'


def test_only_reviewed_drop_rows_are_filtered():
    drop = rj.blocklist_ids('drop')
    review = rj.blocklist_ids('review')
    assert set(DRAFT_DROP) == drop
    assert set(DRAFT_REVIEW) <= review
    assert not (drop & review)


def test_filter_targets_removes_exactly_the_drop_set():
    import identify_clip as ic
    entries, _ = ic.load_targets()
    drop = rj.blocklist_ids('drop')
    present = {e['id'] for e in entries} & drop
    kept = rj.filter_targets(entries)
    assert len(kept) == len(entries) - len(present)
    assert not ({e['id'] for e in kept} & drop)
    assert all(e in entries for e in kept), 'filter must not rebuild entries'


def test_filter_targets_is_a_noop_without_ids():
    entries = [{'id': 'comp00000'}, {'id': None}]
    assert rj.filter_targets(entries, set()) == entries


def test_legacy_entries_without_ids_survive():
    """The no-registry fallback path in load_targets() sets id=None."""
    entries = [{'id': None, 'canonical': 'x'}]
    assert rj.filter_targets(entries, {'comp00000'}) == entries


# ------------------------------------------------------------ truth safety

def test_no_blocklisted_row_is_a_wild_set_truth():
    """Filtering a truth id would make a clip unanswerable, not just cleaner."""
    wild = json.loads((ROOT / 'data' / 'wild_truth_manifest.json').read_text())
    truth = {i for v in wild.values() for i in v.get('truth_ids', [])}
    assert not (truth & set(rj.load_blocklist()['rows']))
