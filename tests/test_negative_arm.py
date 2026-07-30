"""Contract tests for the negative arm's two-sweep labeling and validity gate.

The negative arm is the only thing standing between a duration PROMOTE and a
safety claim nobody measured, so its failure modes are all silent ones: a
half-heard window that gates anyway, a sidecar that validates while describing
a different experiment, a missing field read as an answer. Each test below
pins one of those.

Run: venv_train/bin/python -m pytest tests/test_negative_arm.py -q
(pure logic over fixtures; no audio, no ASR, no registry)
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import identify_clip as ic  # noqa: E402
import build_negative_complement as bnc  # noqa: E402
import duration_probe_score as dps  # noqa: E402
import parse_negative_labels as pnl  # noqa: E402


# ------------------------------------------------------- sweep coverage (T1)

def test_the_two_sweeps_tile_the_window_exactly():
    """The whole justification for sheet 2: together they leave nothing."""
    s1, s2 = bnc.assert_tiles(300)
    assert s1 == list(range(0, 290, 20))
    assert s2 == list(range(10, 300, 20))
    assert len(s1) == len(s2) == 15


def test_sheet_one_alone_leaves_half_the_window_unheard():
    """Characterization of the defect sheet 2 exists to fix."""
    heard = sum(e - s for s, e in bnc.intervals(bnc.sweep_starts(300), 300))
    assert heard == 150


def test_tiling_assertion_actually_fires_on_a_bad_period(monkeypatch):
    """The assertion must be load-bearing, not decorative."""
    monkeypatch.setattr(bnc, 'SCAN_EVERY', 30)
    with pytest.raises(AssertionError):
        bnc.assert_tiles(300)


# --------------------------------------------------- label combination (T1)

@pytest.mark.parametrize('v1,v2,expected', [
    ('no-sahitya', 'no-sahitya', 'no-sahitya'),   # the only way to gate
    ('no-sahitya', 'sahitya', 'sahitya'),         # sheet 2 overrides sheet 1
    ('sahitya', 'no-sahitya', 'sahitya'),         # singing heard is conclusive
    ('no-sahitya', 'unknown', 'unknown'),         # blank/unusable on sheet 2
    ('unknown', 'no-sahitya', 'unknown'),
    ('no-sahitya', None, 'unknown'),              # sheet-2 row never offered
    ('sahitya', None, 'sahitya'),
    ('unknown', None, 'unknown'),
])
def test_combine_sweeps(v1, v2, expected):
    assert pnl.combine_sweeps(v1, v2) == expected


@pytest.mark.parametrize('opts,expected', [
    ({'no-sahitya'}, 'no-sahitya'),
    ({'sahitya'}, 'sahitya'),
    ({'unusable'}, 'unknown'),
    (set(), 'unknown'),
    ({'no-sahitya', 'sahitya'}, 'unknown'),   # coin toss is not evidence
])
def test_collapse(opts, expected):
    assert pnl.collapse(opts) == expected


def _sheet(path: Path, rows, suffix):
    lines = ['| # | listen | label | notes |', '|---:|---|---|---|']
    lines += [f'| {i} | `{item}{suffix}.wav` | {label} |  |'
              for i, (item, label) in enumerate(rows, 1)]
    path.write_text('\n'.join(lines) + '\n')


def test_parser_round_trips_a_hand_made_two_sheet_fixture(tmp_path):
    """All four combinations survive parse -> collapse -> combine intact."""
    s1 = tmp_path / 'LABELING_SHEET.md'
    s2 = tmp_path / 'LABELING_SHEET_2.md'
    _sheet(s1, [('neg001', 'no-sahitya'), ('neg002', 'no-sahitya'),
                ('neg003', 'no-sahitya'), ('neg004', 'sahitya'),
                ('neg005', 'unusable'), ('neg006', 'no-sahitya')], '_scan')
    _sheet(s2, [('neg001', 'no-sahitya'), ('neg002', 'sahitya'),
                ('neg003', ''), ('neg004', 'no-sahitya'),
                ('neg005', 'no-sahitya')], '_scan2')

    p1, probs1 = pnl.parse_sheet(s1)
    p2, probs2 = pnl.parse_sheet(s2)
    assert not probs1 and not probs2

    def verdict(item):
        o2 = p2.get(item)
        return pnl.combine_sweeps(
            pnl.collapse(p1.get(item, set())),
            pnl.collapse(o2) if o2 is not None else None)

    assert verdict('neg001') == 'no-sahitya'   # clean double negative
    assert verdict('neg002') == 'sahitya'      # sheet 2 caught singing
    assert verdict('neg003') == 'unknown'      # sheet 2 left blank
    assert verdict('neg004') == 'sahitya'      # sheet 1 conclusive
    assert verdict('neg005') == 'unknown'      # unusable on sheet 1
    assert verdict('neg006') == 'unknown'      # never offered on sheet 2


def test_parse_sheet_separates_never_offered_from_left_blank(tmp_path):
    """`absent` and `blank` are different facts and must not merge."""
    s = tmp_path / 'sheet.md'
    _sheet(s, [('neg001', '')], '_scan')
    per_item, _ = pnl.parse_sheet(s)
    assert per_item['neg001'] == set()      # offered, left blank
    assert 'neg002' not in per_item         # never offered


# --------------------------------------------------- negative validity gate

def _sidecar(audio_dir: Path, items=('neg001', 'neg002'), **over):
    """A minimally valid negative sidecar, with real audio behind the SHAs."""
    windows = {}
    for item in items:
        for dur in (30, 300):
            stem = f'{item}d{dur:03d}'
            wav = audio_dir / f'{stem}.wav'
            wav.write_bytes(f'pretend-audio-{stem}'.encode())
            windows[stem] = {
                'item': item, 'window_seconds': dur, 'stratum': 'no-sahitya',
                'cluster': f'c-{item}', 'candidate_kind': 'free_form_candidate',
                'audio_sha256': ic.audio_sha256(wav)}
    side = {'durations': [30, 300], 'n_items': len(items),
            'expected_windows': 2 * len(items), 'labels_applied': True,
            'sweeps_required': 2, 'sweeps_applied': 2, 'seed': 1,
            'stratum_counts': {'no-sahitya': len(items)}, 'windows': windows}
    side.update(over)
    return side


def _results(side, **over):
    rows = []
    for stem in side['windows']:
        row = {'file': f'{stem}.wav', 'cache_v2': 'hit',
               'composition_confidence': 'none', 'compositions': []}
        row.update(over)
        rows.append(row)
    return rows


def _errs(side, audio_dir, results=None):
    return dps.validate_negatives(results if results is not None
                                  else _results(side), side, audio_dir)


def test_valid_negative_arm_produces_no_errors(tmp_path):
    side = _sidecar(tmp_path)
    assert _errs(side, tmp_path) == []


def test_single_sweep_sidecar_is_rejected(tmp_path):
    """The T1 gate: half-heard windows cannot reach a safety verdict."""
    side = _sidecar(tmp_path, sweeps_applied=1)
    assert any('sweep' in e for e in _errs(side, tmp_path))


def test_sidecar_predating_the_two_sweep_rule_is_rejected(tmp_path):
    side = _sidecar(tmp_path)
    del side['sweeps_applied'], side['sweeps_required']
    assert any('sweep' in e for e in _errs(side, tmp_path))


# ------------------------------------- T3: one test per named validator hole

def test_hole1_sidecar_without_the_frozen_contrast_is_rejected(tmp_path):
    """A 300s-only sidecar gave short == long, b == 0, and printed SAFE."""
    side = _sidecar(tmp_path)
    side['durations'] = [300]
    for stem in [s for s, m in side['windows'].items()
                 if m['window_seconds'] == 30]:
        side['windows'].pop(stem)
    side['expected_windows'] = len(side['windows'])
    assert any('frozen design' in e for e in _errs(side, tmp_path))


def test_hole2_duplicate_item_duration_metadata_is_rejected(tmp_path):
    side = _sidecar(tmp_path)
    stem = 'neg001d030'
    clone = dict(side['windows'][stem])
    side['windows']['neg001d030_copy'] = clone
    (tmp_path / 'neg001d030_copy.wav').write_bytes(
        (tmp_path / f'{stem}.wav').read_bytes())
    side['expected_windows'] = len(side['windows'])
    assert any('appear more than once' in e for e in _errs(side, tmp_path))


def test_hole3_item_with_different_strata_at_its_endpoints_is_rejected(
        tmp_path):
    side = _sidecar(tmp_path)
    side['windows']['neg001d030']['stratum'] = 'sung_unidentified'
    side['stratum_counts'] = {'no-sahitya': 2}
    assert any('different strata' in e for e in _errs(side, tmp_path))


@pytest.mark.parametrize('field,value,needle', [
    ('n_items', 99, 'n_items'),
    ('seed', None, 'seed'),
    ('stratum_counts', {'no-sahitya': 99}, 'stratum_counts'),
])
def test_hole4_sidecar_bookkeeping_is_checked(tmp_path, field, value, needle):
    side = _sidecar(tmp_path)
    side[field] = value
    assert any(needle in e for e in _errs(side, tmp_path))


def test_hole4_gating_stratum_reusing_a_cluster_is_rejected(tmp_path):
    """The cluster cap existed but nothing verified it survived to scoring."""
    side = _sidecar(tmp_path)
    for meta in side['windows'].values():
        meta['cluster'] = 'one-lecdem-upload'
    assert any('cluster' in e for e in _errs(side, tmp_path))


@pytest.mark.parametrize('over', [{'cache_v2': None}, {}])
def test_hole5_missing_or_malformed_cache_field_is_rejected(tmp_path, over):
    side = _sidecar(tmp_path)
    rows = _results(side)
    for r in rows:
        r.pop('cache_v2', None)
        r.update(over)
    assert any('cache_v2' in e for e in _errs(side, tmp_path, rows))


def test_hole6_missing_confidence_field_is_rejected(tmp_path):
    """`!= 'none'` read a missing field as an answer, so b=0 meant nothing."""
    side = _sidecar(tmp_path)
    rows = _results(side)
    for r in rows:
        r.pop('composition_confidence')
    assert any('composition_confidence' in e for e in _errs(side, tmp_path,
                                                            rows))


def test_hole6_a_run_that_produced_nothing_cannot_read_as_zero_bluffs(
        tmp_path):
    """The failure this hole enabled, end to end."""
    side = _sidecar(tmp_path)
    rows = _results(side)
    for r in rows:
        r.pop('composition_confidence')
    _items, b, _r, _ = dps.negative_transitions(
        rows, side['windows'], 'no-sahitya', 30, 300)
    assert b == 0                                    # looks perfectly safe ...
    assert _errs(side, tmp_path, rows)               # ... and is now refused


def test_hole7_unstamped_sidecar_is_rejected(tmp_path):
    side = _sidecar(tmp_path)
    for meta in side['windows'].values():
        meta.pop('audio_sha256')
    assert any('audio_sha256' in e for e in _errs(side, tmp_path))


def test_hole7_swapped_audio_behind_a_correct_filename_is_rejected(tmp_path):
    side = _sidecar(tmp_path)
    (tmp_path / 'neg001d300.wav').write_bytes(b'a different recording')
    assert any('different files' in e for e in _errs(side, tmp_path))


def test_hole7_absent_audio_is_rejected(tmp_path):
    side = _sidecar(tmp_path)
    (tmp_path / 'neg001d300.wav').unlink()
    assert any('no audio on disk' in e for e in _errs(side, tmp_path))


# ----------------------------------------- T2: per-source readout and gate

def test_per_source_split_separates_what_the_pool_hides():
    """The review's worked example: 3 bluffs in one source, pooled says SAFE."""
    assert round(100 * dps.clopper_pearson_upper(3, 51), 1) == 14.5
    assert round(100 * dps.clopper_pearson_upper(3, 26), 1) == 27.2
    assert round(100 * dps.clopper_pearson_upper(3, 21), 1) == 32.9


def test_source_gate_requires_every_major_source_to_clear_alone():
    per_source = [('free_form_candidate', 26, 3, 0,
                   100 * dps.clopper_pearson_upper(3, 26)),
                  ('opening_candidate', 21, 0, 0,
                   100 * dps.clopper_pearson_upper(0, 21))]
    safe, why = dps.source_gate_verdict(per_source, 15.0)
    assert not safe and 'free_form_candidate' in why


def test_source_gate_passes_only_on_zero_bluffs_at_these_sizes():
    per_source = [('free_form_candidate', 26, 0, 0,
                   100 * dps.clopper_pearson_upper(0, 26)),
                  ('opening_candidate', 21, 0, 0,
                   100 * dps.clopper_pearson_upper(0, 21))]
    assert dps.source_gate_verdict(per_source, 15.0)[0]
    one_bluff = [('free_form_candidate', 26, 1, 0,
                  100 * dps.clopper_pearson_upper(1, 26))] + per_source[1:]
    assert not dps.source_gate_verdict(one_bluff, 15.0)[0]


def test_a_source_too_small_to_carry_a_claim_cannot_grant_one():
    """4 unidentified items bound nothing; they must not read as 'safe'."""
    small = [('unidentified_candidate', 4, 0, 0,
              100 * dps.clopper_pearson_upper(0, 4))]
    safe, why = dps.source_gate_verdict(small, 15.0)
    assert not safe and str(dps.SOURCE_MIN_N) in why


def test_gating_source_counts_are_checked_against_the_windows(tmp_path):
    side = _sidecar(tmp_path)
    side['gating_source_counts'] = {'free_form_candidate': 99}
    assert any('gating_source_counts' in e for e in _errs(side, tmp_path))


# --------------------------------------------- L1: rule A is the applied gate

def _rule_a_sidecar(tmp_path, n_free=25, n_open=20):
    """A sidecar at the realized gating sizes: 25 free-form + 20 opening."""
    kinds = ([('free_form_candidate', i) for i in range(n_free)]
             + [('opening_candidate', i) for i in range(n_open)])
    items = [f'neg{k[:1]}{i:03d}' for k, i in kinds]
    side = _sidecar(tmp_path, items=tuple(items))
    for (kind, _i), item in zip(kinds, items):
        for dur in (30, 300):
            side['windows'][f'{item}d{dur:03d}']['candidate_kind'] = kind
    side['stratum_counts'] = {'no-sahitya': len(items)}
    side['gating_source_counts'] = {'free_form_candidate': n_free,
                                    'opening_candidate': n_open}
    return side


def _rule_a_results(side, bluffs=()):
    """All items abstain at both endpoints, except `bluffs`: none -> low."""
    rows = []
    for stem, meta in side['windows'].items():
        answered = meta['item'] in bluffs and meta['window_seconds'] == 300
        rows.append({'file': f'{stem}.wav', 'cache_v2': 'hit',
                     'compositions': [],
                     'composition_confidence': 'low' if answered else 'none'})
    return rows


def _run_negatives(tmp_path, side, rows):
    import argparse
    (tmp_path / 'side.json').write_text(json.dumps(side))
    (tmp_path / 'res.json').write_text(json.dumps(rows))
    args = argparse.Namespace(
        negative_results=str(tmp_path / 'res.json'),
        negative_truth=str(tmp_path / 'side.json'))
    return dps.report_negatives(args, 15.0, audio_dir=tmp_path)


def test_rule_a_fails_on_one_planted_bluff_that_the_pooled_bound_would_pass(
        tmp_path, capsys):
    """The whole point of the flip: 1/45 pooled looks safe, 1/25 does not."""
    side = _rule_a_sidecar(tmp_path)
    bluff = next(m['item'] for m in side['windows'].values()
                 if m['candidate_kind'] == 'free_form_candidate')
    safe, why = _run_negatives(tmp_path, side, _rule_a_results(side, {bluff}))
    out = capsys.readouterr().out
    assert 100 * dps.clopper_pearson_upper(1, 45) < 15.0    # pooled: SAFE
    assert 100 * dps.clopper_pearson_upper(1, 25) >= 15.0   # free-form: not
    assert not safe and 'free_form_candidate' in why
    assert 'APPLIED (rule A): NOT SAFE' in out
    assert 'THE POOLED BOUND WOULD HAVE PASSED THIS RUN' in out


def test_rule_a_passes_only_when_both_gating_sources_are_clean(tmp_path,
                                                               capsys):
    side = _rule_a_sidecar(tmp_path)
    safe, why = _run_negatives(tmp_path, side, _rule_a_results(side))
    assert safe and 'rule A' in why
    assert 'APPLIED (rule A): SAFE' in capsys.readouterr().out
    opening = next(m['item'] for m in side['windows'].values()
                   if m['candidate_kind'] == 'opening_candidate')
    safe2, why2 = _run_negatives(tmp_path, side,
                                 _rule_a_results(side, {opening}))
    assert not safe2 and 'opening_candidate' in why2


def test_a_gating_source_missing_from_the_results_suppresses(tmp_path):
    """Losing a source must not hand rule A a pass on what is left."""
    side = _rule_a_sidecar(tmp_path)
    rows = [r for r in _rule_a_results(side)
            if side['windows'][Path(r['file']).stem]['candidate_kind']
            != 'opening_candidate']
    errs = dps.validate_negatives(rows, side, tmp_path)
    assert any('opening_candidate' in e and 'gating source' in e
               for e in errs)
    safe, why = _run_negatives(tmp_path, side, rows)
    assert not safe and why == 'negative arm invalid'


def test_a_gating_source_missing_from_the_sidecar_suppresses(tmp_path):
    side = _rule_a_sidecar(tmp_path)
    for stem in [s for s, m in list(side['windows'].items())
                 if m['candidate_kind'] == 'opening_candidate']:
        side['windows'].pop(stem)
    side['n_items'] = len({m['item'] for m in side['windows'].values()})
    side['expected_windows'] = len(side['windows'])
    side['stratum_counts'] = {'no-sahitya': side['n_items']}
    errs = dps.validate_negatives(_rule_a_results(side), side, tmp_path)
    assert any('opening_candidate' in e and 'absent from the sidecar' in e
               for e in errs)


# ------------------------- L2: the recall arm gets the same artifact binding

def _recall_sidecar(audio_dir: Path, stamp=True):
    """A minimally valid recall sidecar: 2 titles x the 5 registered windows."""
    windows = {}
    for t in range(2):
        for dur in (30, 60, 90, 180, 300):
            stem = f'probe{t:04d}d{dur:03d}a'
            wav = audio_dir / f'{stem}.wav'
            wav.write_bytes(f'pretend-audio-{stem}'.encode())
            windows[stem] = {'key': f'title{t}', 'window_seconds': dur,
                             'truth_ids': ['comp00001'], 'n_lyric_lines': 7,
                             'arm': 'anchored'}
            if stamp:
                windows[stem]['audio_sha256'] = ic.audio_sha256(wav)
    return {'arm': 'anchored', 'seed': 1, 'n_titles': 2,
            'durations': [30, 60, 90, 180, 300], 'expected_windows': 10,
            'windows': windows}


def _recall_results(side):
    return [{'file': f'{stem}.wav', 'cache_v2': 'hit',
             'composition_confidence': 'none', 'compositions': []}
            for stem in side['windows']]


def test_a_stamped_recall_arm_validates(tmp_path):
    side = _recall_sidecar(tmp_path)
    assert dps.validate(_recall_results(side), side['windows'], side,
                        tmp_path) == []


def test_an_unstamped_recall_arm_is_rejected(tmp_path):
    """§6b hole 7 applied to §5: filenames are not identity in either arm."""
    side = _recall_sidecar(tmp_path, stamp=False)
    errs = dps.validate(_recall_results(side), side['windows'], side, tmp_path)
    assert any('audio_sha256' in e for e in errs)


def test_a_recut_recall_window_is_rejected(tmp_path):
    """A re-cut window keeps its filename, and the cache serves the old ASR."""
    side = _recall_sidecar(tmp_path)
    (tmp_path / 'probe0000d300a.wav').write_bytes(b'cut from a new anchor')
    errs = dps.validate(_recall_results(side), side['windows'], side, tmp_path)
    assert any('different files' in e for e in errs)


def test_transitions_can_be_restricted_to_one_source(tmp_path):
    side = _sidecar(tmp_path, items=('neg001', 'neg002'))
    side['windows']['neg002d030']['candidate_kind'] = 'opening_candidate'
    side['windows']['neg002d300']['candidate_kind'] = 'opening_candidate'
    rows = _results(side)
    items, _b, _r, _ = dps.negative_transitions(
        rows, side['windows'], 'no-sahitya', 30, 300,
        kind='free_form_candidate')
    assert items == ['neg001']


# ------------- C2: §5b straddler exclusion (built before the calibration ran)

def test_excluding_a_recall_title_reduces_n_and_reconciles_the_sidecar(
        tmp_path):
    """A dropped title leaves every readout, and the bookkeeping follows it."""
    side = _recall_sidecar(tmp_path)
    results = _recall_results(side)
    out, new_side, errs = dps.apply_exclusions(results, side, {'title0'},
                                               'key', 'recall title')
    assert errs == []
    assert new_side['n_titles'] == 1 and new_side['expected_windows'] == 5
    assert len(new_side['windows']) == 5 and len(out) == 5
    assert {m['key'] for m in new_side['windows'].values()} == {'title1'}
    # the reduced sidecar must still validate against its recomputed counts
    assert dps.validate(out, new_side['windows'], new_side, tmp_path) == []


def test_excluding_a_title_that_is_not_in_the_sidecar_is_an_error(tmp_path):
    side = _recall_sidecar(tmp_path)
    _o, _s, errs = dps.apply_exclusions(_recall_results(side), side,
                                        {'title9'}, 'key', 'recall title')
    assert any('not in the sidecar' in e for e in errs)


def test_an_exclusion_cannot_hide_a_window_that_was_missing_anyway(tmp_path):
    """Excluding an absent unit is still an invalid run: the full arm is
    validated before anything is dropped, so the missing window is fatal."""
    side = _recall_sidecar(tmp_path)
    results = [r for r in _recall_results(side)
               if r['file'] != 'probe0000d300a.wav']
    full = dps.validate(results, side['windows'], side, tmp_path)
    assert any('no result' in e for e in full)


def test_excluding_a_negative_item_moves_its_source_count_and_the_bound(
        tmp_path):
    side = _rule_a_sidecar(tmp_path)
    rows = _rule_a_results(side)
    victim = next(m['item'] for m in side['windows'].values()
                  if m['candidate_kind'] == 'free_form_candidate')
    out, new_side, errs = dps.apply_exclusions(rows, side, {victim}, 'item',
                                               'negative item')
    assert errs == []
    assert new_side['gating_source_counts']['free_form_candidate'] == 24
    assert new_side['n_items'] == 44 and new_side['expected_windows'] == 88
    assert new_side['stratum_counts']['no-sahitya'] == 44
    assert dps.validate_negatives(out, new_side, tmp_path) == []
    items, _b, _r, _ = dps.negative_transitions(
        out, new_side['windows'], 'no-sahitya', 30, 300,
        kind='free_form_candidate')
    assert len(items) == 24 and victim not in items
    # the bound is the one the reduced n earns, not the registered one
    assert (100 * dps.clopper_pearson_upper(0, 24)
            > 100 * dps.clopper_pearson_upper(0, 25))


def test_an_exclusion_that_shrinks_a_gating_source_below_20_suppresses(
        tmp_path, capsys):
    """Rule A is quantified over the REGISTERED sources. An exclusion that
    pushes one below SOURCE_MIN_N must suppress, not gate on the survivors."""
    side = _rule_a_sidecar(tmp_path)
    rows = _rule_a_results(side)
    opening = sorted({m['item'] for m in side['windows'].values()
                      if m['candidate_kind'] == 'opening_candidate'})[:2]
    out, new_side, errs = dps.apply_exclusions(rows, side, set(opening),
                                               'item', 'negative item')
    assert errs == [] and new_side['gating_source_counts'][
        'opening_candidate'] == 18
    per_source = dps.report_by_source(out, new_side['windows'], 30, 300, 15.0)
    capsys.readouterr()
    safe, why = dps.source_gate_verdict(per_source, 15.0,
                                        side['gating_source_counts'])
    assert not safe and 'opening_candidate 20->18' in why
    # without the registered census it would have quietly gated on free-form
    safe_blind, _ = dps.source_gate_verdict(per_source, 15.0)
    assert safe_blind


def test_a_straddler_can_be_named_by_window_id_or_by_title_key(tmp_path):
    """DEVICE_MAP.md names `probe0051`; the sidecar is keyed `title0`. Making
    the operator translate by hand is how the wrong title gets excluded."""
    side = _recall_sidecar(tmp_path)
    w = side['windows']
    assert dps.resolve_recall_units(['probe0000'], w) == ({'title0'}, [])
    assert dps.resolve_recall_units(['title1'], w) == ({'title1'}, [])
    got, errs = dps.resolve_recall_units(['probe0009'], w)
    assert got == set() and any('neither a title key' in e for e in errs)


def test_a_window_id_spanning_two_titles_is_an_error_not_a_guess(tmp_path):
    side = _recall_sidecar(tmp_path)
    side['windows']['probe0000d030a']['key'] = 'title9'
    got, errs = dps.resolve_recall_units(['probe0000'], side['windows'])
    assert got == set() and any('spans 2 title keys' in e for e in errs)


def test_exclusion_block_prints_the_set_the_reason_and_the_realized_n(capsys):
    dps.exclusion_block('recall arm', {'title0'}, 'straddles two GPUs', 60, 59)
    out = capsys.readouterr().out
    assert 'title0' in out and 'straddles two GPUs' in out
    assert 'realized n: 59 of 60 registered' in out
