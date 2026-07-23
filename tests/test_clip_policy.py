"""Phase 0 contract + regression tests for the clip-identification policy.

Run: venv_train/bin/python -m pytest tests/test_clip_policy.py -q
(needs the registry JSONs on disk; no whisper/demucs/audio involved)
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# root FIRST: backend/ holds a build_space.sh-time copy of identify_clip.py
# that must never shadow the live root module
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT))

os.environ.setdefault('CARNATIFY_MATCH_WORKERS', '2')

import identify_clip as ic  # noqa: E402


@pytest.fixture(scope='module')
def targets():
    entries, lyr = ic.load_targets()
    return entries, lyr


# ---------------------------------------------------------------- text views

def test_fold_erases_native_scripts():
    # characterization of the P0 bug: fold alone destroys native output
    assert ic.fold('வாதாபி கணபதிம் பஜே').strip() == ''
    assert ic.fold('వాతాపి గణపతిం భజే').strip() == ''
    assert ic.fold('वातापि गणपतिं भजे').strip() == ''


def test_translit_fold_preserves_native_scripts():
    te = ic.translit_fold('వాతాపి గణపతిం భజే')
    hi = ic.translit_fold('वातापि गणपतिं भजे')
    ta = ic.translit_fold('வாதாபி கணபதிம் பஜே')
    assert te == 'vatapi ganapatim bhaje'
    assert hi == 'vatapi ganapatim bhaje'
    assert len(ta.replace(' ', '')) > 10  # Tamil survives (voicing drift ok)
    # latin input passes through identically to fold
    assert ic.translit_fold('vAtApi gaNapatim') == ic.fold('vAtApi gaNapatim')


def test_translit_fold_is_a_view_not_storage():
    raw = 'వాతాపి గణపతిం భజే'
    ic.translit_fold(raw)
    assert raw == 'వాతాపి గణపతిం భజే'  # never mutated


# ------------------------------------------------------------------- policy

def test_loop_transcript_rejected(targets):
    entries, lyr = targets
    res = ic.assess_variants({'turbo': 'rama rama rama rama'}, entries, lyr)
    assert res['composition_confidence'] == 'none'
    assert res['compositions'] == []


def test_satish_loop_rejected(targets):
    entries, lyr = targets
    res = ic.assess_variants({'turbo': 'satish satish satish satish'},
                             entries, lyr)
    assert res['composition_confidence'] == 'none'


def test_short_transcript_rejected(targets):
    entries, lyr = targets
    res = ic.assess_variants({'turbo': 'rama'}, entries, lyr)
    assert res['composition_confidence'] == 'none'


@pytest.mark.xfail(reason='P1 many-to-one scoring exploit: generic repeated '
                          'tokens still reach answerable scores; fixed by the '
                          'one-to-one alignment behavior-changer',
                   strict=False)
def test_rama_rama_scores_below_answer_threshold(targets):
    entries, lyr = targets
    res = ic.assess_variants({'turbo': 'rama rama sita rama'}, entries, lyr)
    assert res['composition_confidence'] in ('none', 'low')


# ---------------------------------------------------- CLI/server contract

def test_backend_and_cli_same_policy(targets):
    entries, lyr = targets
    import clip_identify as backend
    backend._entries = entries  # share the loaded registry
    cases = [
        {'orig': 'vatapi ganapatim bhaje vatapi ganapatim',
         'stem': 'vatapi ganapatim bhajeham'},
        {'orig': 'rama rama rama rama'},
        {'orig': '', 'stem': ''},
        {'orig': 'nagumomu ganaleni nagumomu'},
    ]
    for variants in cases:
        cli = ic.assess_variants(dict(variants), entries, lyr)
        api = backend.identify_from_variants(dict(variants))
        assert api['composition_confidence'] == \
            cli['composition_confidence'], variants
        assert api['compositions'] == cli['compositions'], variants
        api_type = api['clip_type']
        assert (api_type == 'sung') == \
            (cli['clip_type'] == 'sung (lyrics found)'), variants


# ------------------------------------------------------------- cache v2

def test_cache2_key_includes_hash_and_config(tmp_path):
    f = tmp_path / 'x.wav'
    f.write_bytes(b'abc')
    key = ic.cache2_key(ic.audio_sha256(f))
    sha, config = key.split(':', 1)
    assert len(sha) == 24
    assert config == ic.asr_config_id()
    f.write_bytes(b'abcd')  # content change -> new key
    assert ic.cache2_key(ic.audio_sha256(f)) != key


def test_atomic_write_json(tmp_path):
    p = tmp_path / 'c.json'
    ic._atomic_write_json(p, {'a': 1})
    import json
    assert json.loads(p.read_text()) == {'a': 1}
    assert not list(tmp_path.glob('*.tmp'))


# ------------------------------------------------------------------ M1

def test_line_variants_section_tagging():
    kar = {'x.html': {'page': 'x.html', 'lyrics':
           'pallavi\nsome pallavi line goes here\n'
           'anupallavi\nthe anupallavi line text here\n'
           'caraNam 1\nfirst caranam line of the song\n'
           '(chittaswaram)\nP: prefixed pallavi content line\n'}}
    lines = ic._line_variants(['x.html'], kar)
    secs = {l['f']: l['section'] for l in lines}
    assert secs['some pallavi line goes here'] == 'pallavi'
    assert secs['the anupallavi line text here'] == 'anupallavi'
    assert secs['first caranam line of the song'] == 'caranam'
    assert secs['p prefixed pallavi content line'] == 'pallavi'
    # pallavi lines are retained first, ahead of the cap
    assert lines[0]['section'] == 'pallavi'


def test_match_lyrics_channels_and_detail(targets):
    entries, lyr = targets
    comps, _ = ic.match_lyrics('vatapi ganapatim bhaje vatapi ganapatim',
                               entries, lyr, detail=True)
    top = comps[0]
    assert set(top['channel_scores']) == {'title', 'pallavi', 'other'}
    assert top['channel'] in top['channel_scores']
    # ranking score is the plain max across channels — never a bonus
    assert top['score'] == round(max(top['channel_scores'].values()), 3)
    d = top['align']
    for k in ('pairs', 'matched_idf', 'total_idf', 'distinct_hits',
              'k_cov', 'q_cov', 'ordered', 'section'):
        assert k in d
    assert d['distinct_hits'] >= 2
    assert 0.0 <= d['k_cov'] <= 1.0 and 0.0 <= d['q_cov'] <= 1.0


def test_variants_from_v2_selects_per_source():
    entry = {'hypotheses': [
        {'source': 'mix', 'lang': 'auto', 'raw': 'short', 'status': 'ok'},
        {'source': 'mix', 'lang': 'te', 'raw': 'వాతాపి గణపతిం భజే',
         'status': 'ok'},
        {'source': 'stem', 'lang': 'ta', 'raw': 'x', 'status': 'error: boom'},
        {'source': 'stem', 'lang': 'auto', 'raw': 'stem text here',
         'status': 'ok'},
    ]}
    v = ic.variants_from_v2(entry, view=ic.translit_fold)
    assert v['turbo'] == 'vatapi ganapatim bhaje'  # native beats short latin
    assert v['stem_turbo'] == 'stem text here'     # error hyp never selected
    # fold-only diagnostic view reproduces the old ASCII behavior
    v_old = ic.variants_from_v2(entry, view=ic.fold)
    assert v_old['turbo'] == 'short'
