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


# ------------------------------------------- Rung 1: wild-truth manifest

@pytest.fixture(scope='module')
def _wild():
    import json
    reg = json.loads(ic.REGISTRY.read_text())
    manifest = json.loads(ic.WILD_TRUTH.read_text())
    return reg, {r['id'] for r in reg}, manifest


def test_manifest_ids_all_exist_in_registry(_wild):
    _, ids, manifest = _wild
    for stem, m in manifest.items():
        for tid in m.get('truth_ids', []):
            assert tid in ids, f'{stem}: unknown truth id {tid}'


def test_manifest_covers_every_in_catalog_clip(_wild):
    # every non-OOC entry is either a real truth set or an explicit
    # empty/non-sahitya row -- there is no silent fallback.
    _, _, manifest = _wild
    for stem, m in manifest.items():
        if m.get('ooc'):
            continue
        assert 'truth_ids' in m, f'{stem}: no truth_ids and not OOC'


def test_rama_nee_truth_is_one_to_one(_wild):
    """The flagship flattery case: fuzzy `partial_ratio >= 90` matched ~67
    registry rows for the generic short title 'rAma nee'. The reviewed
    manifest resolves it to exactly the real work and rejects the rest."""
    reg, _, manifest = _wild
    truth = set(manifest['rAma nee__Karaharapriya']['truth_ids'])
    assert truth == {'comp06177'}  # rAma nee samAnam evaru (Tyagaraja)

    # characterize the old behavior we removed: the fuzzy rule was loose
    a = ic.skey('rAma nee')
    fuzzy = {r['id'] for r in reg
             if ic._partial(a, ic.skey(r['canonical'])) >= 90
             or ic._partial(ic.skey(r['canonical']), a) >= 90}
    assert len(fuzzy) > 40, 'expected the old fuzzy rule to over-match'

    # id comparison accepts only the real work; the stub and unrelated
    # short-title neighbours that fuzzy accepted are now rejected.
    assert 'comp06177' in truth
    for wrong in ('comp06166', 'comp06168', 'comp06180'):
        assert wrong in fuzzy      # fuzzy wrongly accepted these
        assert wrong not in truth  # id comparison correctly rejects them


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


# ------------------------------------------------------- Rung 3: indic cache

def test_indic_backend_is_isolated(monkeypatch):
    """The indic cache must carry its own file + config identity; the
    default whisper path must be byte-identical with the env unset."""
    monkeypatch.delenv('CARNATIFY_ASR_BACKEND', raising=False)
    assert ic.asr_backend() == 'whisper'
    whisper_id = ic.asr_config_id()
    assert whisper_id.startswith('whisper-turbo')
    whisper_key = ic.cache2_key('a' * 64)
    monkeypatch.setenv('CARNATIFY_ASR_BACKEND', 'indic')
    assert ic.asr_backend() == 'indic'
    assert ic.asr_config_id() == ic.INDIC_CONFIG_ID
    assert ic.asr_config_id() != whisper_id
    # keys can never collide across backends for the same audio
    assert ic.cache2_key('a' * 64) != whisper_key
    assert ic.INDIC_CACHE != ic.CACHE2
    assert ic.INDIC_CACHE.name == 'asr_cache_indic.json'


def test_indic_variants_per_lane_translit():
    """Indic entries: one variant per language lane, translit view always
    (the model emits native script only — fold() would erase everything);
    error and empty lanes never become variants."""
    entry = {'config_id': ic.INDIC_CONFIG_ID, 'hypotheses': [
        {'source': 'mix', 'lang': 'te', 'raw': 'వాతాపి గణపతిం భజే',
         'status': 'ok'},
        {'source': 'mix', 'lang': 'ta', 'raw': 'வாதாபி கணபதிம்',
         'status': 'ok'},
        {'source': 'mix', 'lang': 'kn', 'raw': '', 'status': 'empty'},
        {'source': 'mix', 'lang': 'hi', 'raw': 'x',
         'status': 'error: boom'},
    ]}
    v = ic.variants_from_v2(entry)
    assert set(v) == {'indic_te', 'indic_ta'}
    assert v['indic_te'] == 'vatapi ganapatim bhaje'
    assert not any(k.startswith('stem') for k in v)  # mix only


def test_whisper_v2_entries_unaffected_by_indic_code():
    """A whisper v2 entry (no indic config_id) keeps the legacy
    longest-per-source selection and the fold default view."""
    entry = {'config_id': 'whisper-turbo|fp16=0|x', 'hypotheses': [
        {'source': 'mix', 'lang': 'auto', 'raw': 'plain latin text',
         'status': 'ok'},
        {'source': 'mix', 'lang': 'te', 'raw': 'వాతాపి', 'status': 'ok'},
    ]}
    v = ic.variants_from_v2(entry)
    assert set(v) == {'turbo', 'stem_turbo'}
    assert v['turbo'] == 'plain latin text'  # fold erases native by default


# ------------------------------------------- Rung 4: hybrid arbitration

def _res(answered, q_cov=None, ordered=None, top_id=None, score=1.3,
         conf='medium'):
    """Synthetic assess_variants-shaped result for arbitration tests."""
    if not answered:
        return {'transcript': '', 'asr_variant': None, 'compositions': [],
                'composition_confidence': 'none',
                'clip_type': 'no usable lyrics (alapana / instrumental / '
                'ASR miss)'}
    return {'transcript': f'txt-{top_id}', 'asr_variant': 'indic_te',
            'compositions': [{'id': top_id, 'title': top_id, 'score': score,
                              'align': {'q_cov': q_cov, 'ordered': ordered}}],
            'composition_confidence': conf,
            'clip_type': 'sung (lyrics found)',
            'raga_from_catalog': ['someRaga']}


def test_detail_leaves_scores_and_selection_identical(targets):
    """detail=True is additive (adds `align`); it must not change work IDs,
    scores, ordering, selected variant, or confidence."""
    entries, lyr = targets
    variants = {'turbo': 'vatapi ganapatim bhaje vatapi ganapatim',
                'stem_turbo': 'vatapi ganapatim bhajeham'}
    plain = ic.assess_variants(dict(variants), entries, lyr, detail=False)
    det = ic.assess_variants(dict(variants), entries, lyr, detail=True)
    for k in ('composition_confidence', 'asr_variant', 'transcript'):
        assert plain[k] == det[k]
    # compositions identical once align (the only addition) is stripped
    stripped = [{k: v for k, v in c.items() if k != 'align'}
                for c in det['compositions']]
    assert stripped == plain['compositions']
    assert all('align' in c for c in det['compositions'])  # detail present


def test_hybrid_gate_boundary():
    assert ic._passes_gate({'answered': True, 'q_cov': 0.250, 'ordered': True})
    assert not ic._passes_gate({'answered': True, 'q_cov': 0.249,
                                'ordered': True})
    # ordered=False fails regardless of coverage
    assert not ic._passes_gate({'answered': True, 'q_cov': 0.99,
                                'ordered': False})
    # abstention never passes
    assert not ic._passes_gate({'answered': False, 'q_cov': None,
                                'ordered': None})


def test_hybrid_decision_table():
    W = _res(True, 0.30, True, 'compW')   # whisper strong
    Ww = _res(True, 0.10, True, 'compW')  # whisper weak (q_cov below gate)
    I = _res(True, 0.30, True, 'compI')   # indic eligible
    Ii = _res(True, 0.10, True, 'compI')  # indic answered, ineligible
    N = _res(False)

    # 1. indic ineligible -> whisper (even if whisper also weak)
    ch, chan, reason, _ = ic.arbitrate(Ww, Ii)
    assert ch is Ww and chan == 'whisper' and reason == 'indic_ineligible'
    # 1b. indic silent, whisper answers -> whisper_only
    ch, chan, reason, _ = ic.arbitrate(W, N)
    assert ch is W and reason == 'whisper_only'
    # 2. indic eligible, whisper abstains -> indic_fallback
    ch, chan, reason, _ = ic.arbitrate(N, I)
    assert ch is I and chan == 'indic' and reason == 'indic_fallback'
    # 3. both answer + whisper strong -> whisper wins the tie
    ch, chan, reason, _ = ic.arbitrate(W, I)
    assert ch is W and chan == 'whisper' and reason == 'whisper_strong'
    # 3b. whisper wins even with a strictly higher indic raw score
    ch, _, reason, _ = ic.arbitrate(_res(True, 0.30, True, 'compW', score=0.5),
                                    _res(True, 0.30, True, 'compI', score=2.0))
    assert ch['compositions'][0]['id'] == 'compW' and reason == 'whisper_strong'
    # 4. whisper weak + indic eligible -> indic overrides
    ch, chan, reason, _ = ic.arbitrate(Ww, I)
    assert ch is I and chan == 'indic' \
        and reason == 'indic_overrides_weak_whisper'
    # neither answered -> abstain
    ch, chan, reason, _ = ic.arbitrate(N, N)
    assert chan == 'none' and reason == 'neither_answered'


def test_hybrid_never_fuses_lists():
    """Final top-5 is exactly ONE channel's list — never a union."""
    W = _res(True, 0.30, True, 'compW')
    I = _res(True, 0.30, True, 'compI')
    for wres, ires in [(W, I), (I, W), (_res(False), I)]:
        ch, _, _, _ = ic.arbitrate(wres, ires)
        ids = {c['id'] for c in ch['compositions']}
        assert ids == {c['id'] for c in wres['compositions']} \
            or ids == {c['id'] for c in ires['compositions']}
        assert ids != ({c['id'] for c in wres['compositions']}
                       | {c['id'] for c in ires['compositions']}) \
            or not wres['compositions'] or not ires['compositions']


def test_hybrid_carries_whole_channel_row():
    """Choosing Indic carries its transcript/confidence/clip type/raga
    backfill together — no mixed-channel result."""
    W = _res(True, 0.10, True, 'compW', conf='low')   # weak
    I = _res(True, 0.40, True, 'compI', conf='high')  # eligible
    ch, chan, _, _ = ic.arbitrate(W, I)
    assert chan == 'indic'
    assert ch['transcript'] == 'txt-compI'
    assert ch['composition_confidence'] == 'high'
    assert ch['raga_from_catalog'] == ['someRaga']


def test_hybrid_explicit_config_ids_and_defaults(monkeypatch):
    """Explicit config ids address the right cache; single-backend defaults
    are byte-identical to the pre-Rung-4 behavior."""
    monkeypatch.delenv('CARNATIFY_ASR_BACKEND', raising=False)
    sha = 'b' * 64
    # explicit ids differ per backend and match the no-arg default
    assert ic.cache2_key(sha, ic.WHISPER_CONFIG_ID) == ic.cache2_key(sha)
    assert ic.cache2_key(sha, ic.INDIC_CONFIG_ID) != ic.cache2_key(sha)
    assert ic.asr_config_id('indic') == ic.INDIC_CONFIG_ID
    assert ic.asr_config_id('whisper') == ic.WHISPER_CONFIG_ID
    assert ic.load_cache_v2('indic') is not None


# --------------------------------------- Rung 5: indic stem source row

def test_stem_config_identity_distinct():
    """Three distinct config ids/caches; explicit indic_stem mapping; unknown
    backend names raise instead of silently selecting whisper."""
    ids = {ic.WHISPER_CONFIG_ID, ic.INDIC_CONFIG_ID, ic.INDIC_STEM_CONFIG_ID}
    assert len(ids) == 3
    files = {ic.CACHE2, ic.INDIC_CACHE, ic.INDIC_STEM_CACHE}
    assert len(files) == 3
    assert ic.INDIC_STEM_CACHE.name == 'asr_cache_indic_stem.json'
    sha = 'c' * 64
    keys = {ic.cache2_key(sha, cid) for cid in ids}
    assert len(keys) == 3
    assert ic.asr_config_id('indic_stem') == ic.INDIC_STEM_CONFIG_ID
    assert ic.load_cache_v2('indic_stem')['config'] \
        == ic.ASR_CONFIG_INDIC_STEM
    with pytest.raises(ValueError):
        ic.load_cache_v2('no_such_backend')
    with pytest.raises(ValueError):
        ic.asr_config_id('no_such_backend')


def test_stem_variants_source_aware():
    """Stem hypotheses become stem_indic_<lang> variants (source preserved);
    error and empty lanes excluded exactly as mix; mix naming unchanged."""
    stem_entry = {'config_id': ic.INDIC_STEM_CONFIG_ID, 'hypotheses': [
        {'source': 'stem', 'lang': 'te', 'raw': 'వాతాపి గణపతిం భజే',
         'status': 'ok'},
        {'source': 'stem', 'lang': 'kn', 'raw': '', 'status': 'empty'},
        {'source': 'stem', 'lang': 'hi', 'raw': 'x',
         'status': 'error: separation: RuntimeError: boom'},
    ]}
    v = ic.variants_from_v2(stem_entry)
    assert set(v) == {'stem_indic_te'}
    assert v['stem_indic_te'] == 'vatapi ganapatim bhaje'
    assert all(k.startswith('stem') for k in v)
    # mix entries keep their Rung-3 names byte-identical
    mix_entry = {'config_id': ic.INDIC_CONFIG_ID, 'hypotheses': [
        {'source': 'mix', 'lang': 'te', 'raw': 'వాతాపి', 'status': 'ok'}]}
    assert set(ic.variants_from_v2(mix_entry)) == {'indic_te'}


def test_stem_separation_failure_yields_no_variants():
    """A Demucs-stage failure is five per-lane errors, never five empties —
    and produces zero variants (an integration failure is not ASR-dead)."""
    entry = {'config_id': ic.INDIC_STEM_CONFIG_ID, 'hypotheses': [
        {'source': 'stem', 'lang': lang, 'raw': '', 'segments': [],
         'status': 'error: separation: RuntimeError: demucs died'}
        for lang in ('te', 'ta', 'kn', 'hi', 'ml')]}
    assert ic.variants_from_v2(entry) == {}
    assert all(h['status'] != 'empty' for h in entry['hypotheses'])


def test_indic_source_selector_decision_table():
    """Frozen effective-Indic policy: mix-eligible wins; else eligible stem;
    else mix forwarded unchanged (ineligible). Raw scores never consulted."""
    Me = _res(True, 0.30, True, 'compMix')            # mix eligible
    Mi = _res(True, 0.10, True, 'compMix')            # mix ineligible
    Se = _res(True, 0.40, True, 'compStem')           # stem eligible
    Si = _res(True, 0.10, True, 'compStem')           # stem ineligible
    N = _res(False)

    eff, reason, _, _ = ic.select_indic_source(Me, Se)
    assert eff is Me and reason == 'mix_eligible'     # mix wins even vs
    # higher-q_cov stem — no q_cov contest
    eff, reason, _, _ = ic.select_indic_source(Mi, Se)
    assert eff is Se and reason == 'stem_fallback'
    eff, reason, _, _ = ic.select_indic_source(N, Se)
    assert eff is Se and reason == 'stem_fallback'
    eff, reason, _, _ = ic.select_indic_source(Mi, Si)
    assert eff is Mi and reason == 'neither_indic_source_eligible'
    eff, reason, _, _ = ic.select_indic_source(N, N)
    assert eff is N and reason == 'neither_indic_source_eligible'
    # stem with a huge raw score but failed gate can never be selected
    eff, reason, _, _ = ic.select_indic_source(
        Mi, _res(True, 0.10, True, 'compStem', score=9.9))
    assert eff is Mi


def test_hybrid_stem_no_fusion_through_full_chain():
    """selector + arbitrate returns exactly one source row's list and carries
    that row's metadata intact."""
    W = _res(True, 0.10, True, 'compW', conf='low')   # whisper weak
    Mi = _res(True, 0.10, True, 'compMix')            # mix ineligible
    Se = _res(True, 0.40, True, 'compStem', conf='high')
    eff, sreason, _, _ = ic.select_indic_source(Mi, Se)
    chosen, chan, reason, _ = ic.arbitrate(W, eff)
    assert chosen is Se and chan == 'indic'
    assert reason == 'indic_overrides_weak_whisper'
    assert chosen['transcript'] == 'txt-compStem'
    assert chosen['composition_confidence'] == 'high'
    assert [c['id'] for c in chosen['compositions']] == ['compStem']


def test_hybrid_stem_missing_cache_marks_invalid(targets, tmp_path):
    """A missing stem entry marks the hybrid-stem result MISS and reports
    which cache missed."""
    entries, lyr = targets
    f = tmp_path / 'x.wav'
    f.write_bytes(b'not real audio')
    empty = {'schema': 'carnatify-asr-cache-v2', 'config': {}, 'entries': {}}
    sha = ic.audio_sha256(f)
    wcache = {'entries': {ic.cache2_key(sha, ic.WHISPER_CONFIG_ID): {
        'config_id': ic.WHISPER_CONFIG_ID,
        'hypotheses': [{'source': 'mix', 'lang': 'auto',
                        'raw': 'x', 'status': 'ok'}]}}}
    mcache = {'entries': {ic.cache2_key(sha, ic.INDIC_CONFIG_ID): {
        'config_id': ic.INDIC_CONFIG_ID,
        'hypotheses': [{'source': 'mix', 'lang': 'te',
                        'raw': '', 'status': 'empty'}]}}}
    res = ic.identify_v2_hybrid_stem(f, entries, lyr, wcache, mcache,
                                     dict(empty), want_raga=False)
    assert res['cache_whisper'] == 'hit'
    assert res['cache_indic'] == 'hit'
    assert res['cache_indic_stem'] == 'MISS'
    assert res['cache_v2'] == 'MISS'
    assert res['indic_source_reason'] == 'neither_indic_source_eligible'
