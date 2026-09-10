import json
import numpy as np
import pytest
import joblib

from carnatify.ml.raga_runtime import (RagaCandidate, RagaGate, score_contour, signals_from,
                                       sha256_of, SIGNALS)
from carnatify.ml.distribution_classifier import DistributionKernelRidge
from carnatify.ml.melody_features import FEATURE_VERSIONS, feature_vector

HOP = 128 / 44100


def synthetic_contour(pattern, seconds=30, tonic=150.0):
    """A stepwise contour cycling over pitch-class offsets (cents) above Sa."""
    n = int(seconds / HOP)
    steps = np.repeat(np.array(pattern, dtype=float), max(1, n // len(pattern)))[:n]
    return tonic * 2 ** (steps / 1200)


@pytest.fixture
def candidate(tmp_path):
    rng = np.random.default_rng(0)
    X, y = [], []
    for label, pattern in (('A', [0, 200, 400, 700, 900]), ('B', [0, 100, 300, 700, 800]), ('C', [0, 200, 500, 700, 1100])):
        for _ in range(4):
            jitter = rng.normal(0, 15, size=len(pattern))
            v = feature_vector(synthetic_contour(np.array(pattern) + jitter), 150.0, HOP, 'voiced')
            X.append(v); y.append(label)
    model = DistributionKernelRidge(alpha=.1, gamma=2, mode='tdms').fit(np.stack(X), np.array(y))
    bundle = dict(model=model, representation='voiced', feature_version=FEATURE_VERSIONS['voiced'],
                  window_s=30, calibration=dict(temperature=.1))
    path = tmp_path / 'raga.joblib'
    joblib.dump(bundle, path)
    return RagaCandidate.load(str(path)), path


def test_score_contour_carries_model_signals_and_ranking(candidate):
    cand, _ = candidate
    f0 = synthetic_contour([0, 200, 400, 700, 900])
    r = score_contour(cand, f0, 150.0, HOP)
    assert r['answered'] and r['reason'] is None
    assert r['top1'] == 'A' and r['ranked'][0]['raga'] == 'A'
    assert set(r['signals']) == set(SIGNALS)
    assert r['model']['sha256'] == cand.sha256 and r['model']['feature_version'] == FEATURE_VERSIONS['voiced']
    scores = np.array([x['score'] for x in r['ranked']])
    assert np.all(np.diff(scores) <= 0)
    assert r['signals']['margin'] == pytest.approx(scores[0] - scores[1])
    assert r['accepted'] is False and r['gate'] is None


def test_abstains_without_tonic_or_melody(candidate):
    cand, _ = candidate
    f0 = synthetic_contour([0, 200, 400, 700, 900])
    assert score_contour(cand, f0, None, HOP)['reason'] == 'missing_tonic'
    assert score_contour(cand, f0, float('nan'), HOP)['reason'] == 'missing_tonic'
    short = score_contour(cand, f0[:int(5 / HOP)], 150.0, HOP)
    assert short['reason'] == 'insufficient_melody' and short['voiced_s'] < 10
    for r in (score_contour(cand, f0, None, HOP), short):
        assert not r['answered'] and not r['accepted'] and r['ranked'] == []


def test_gate_is_registered_never_invented(candidate, tmp_path):
    cand, _ = candidate
    f0 = synthetic_contour([0, 200, 400, 700, 900])
    open_result = score_contour(cand, f0, 150.0, HOP)
    margin = open_result['signals']['margin']
    gate_path = tmp_path / 'gate.json'
    gate_path.write_text(json.dumps(dict(name='t', signal='margin', threshold=margin / 2, status='test')))
    gate = RagaGate.load(gate_path)
    accepted = score_contour(cand, f0, 150.0, HOP, gate)
    assert accepted['accepted'] is True and accepted['gate']['threshold'] == margin / 2
    strict = RagaGate('margin', margin * 2, 'strict', 'test')
    assert score_contour(cand, f0, 150.0, HOP, strict)['accepted'] is False
    closed = RagaGate('margin', None, 'closed', 'always abstain')
    assert score_contour(cand, f0, 150.0, HOP, closed)['accepted'] is False
    with pytest.raises(ValueError):
        RagaGate('confidence', .5, 'bad', 'unknown signal')


def test_registry_refuses_sha_mismatch(candidate, tmp_path):
    cand, path = candidate
    reg = tmp_path / 'registry.json'
    reg.write_text(json.dumps(dict(candidates=dict(
        good=dict(bundle=str(path), sha256=sha256_of(path)),
        bad=dict(bundle=str(path), sha256='0' * 64)))))
    # Registry bundle paths are ROOT-relative in production; absolute paths resolve the same way.
    loaded = RagaCandidate.load('good', registry=reg)
    assert loaded.sha256 == cand.sha256 and loaded.name == 'good'
    with pytest.raises(ValueError, match='SHA256 mismatch'):
        RagaCandidate.load('bad', registry=reg)
    with pytest.raises(ValueError, match='Unknown candidate'):
        RagaCandidate.load('nope', registry=reg)


def test_signals_from_probability_models():
    p = np.array([.6, .3, .1])
    s, prob = signals_from(p, 'probability', 1.0)
    assert s['max_score'] == pytest.approx(.6) and s['margin'] == pytest.approx(.3)
    assert s['softmax_max'] == pytest.approx(.6) and np.allclose(prob, p)
    d = np.array([1.0, .5, 0.])
    s, prob = signals_from(d, 'decision', .5)
    assert s['margin'] == pytest.approx(.5) and prob.sum() == pytest.approx(1.0)


def test_committed_registry_and_gate_are_consistent():
    from carnatify.ml.raga_runtime import load_registry, ROOT
    reg = load_registry()
    assert reg['reference'] in reg['candidates']
    ref = reg['candidates'][reg['reference']]
    gate = RagaGate.load(ROOT / ref['gate'])
    assert gate.signal in SIGNALS and gate.threshold is not None
    assert 'off in the product' in gate.status
