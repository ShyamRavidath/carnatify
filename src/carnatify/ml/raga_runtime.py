"""The one raga scoring contract: candidate registry, gate, and identify_raga.

Every measurement and every product path that scores a raga goes through
`score_contour` (already-extracted melody) or `identify_raga` (bounded audio
query). Both return the same `RagaResult` dict, so a number produced anywhere
in the repo records which model, which feature contract, which gate and which
signals produced it.

Candidates are named in `configs/raga_candidates.json`; a bundle is loaded
only if its SHA256 matches the registry. Gates are registered JSON files with
a signal name, a threshold and a status; a gate is never invented at runtime.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.special import softmax

from carnatify.ml.melody_features import FEATURE_VERSIONS, feature_vector
from carnatify.ml.inference_runtime import serial_forest_prediction

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / 'configs/raga_candidates.json'
SIGNALS = ('max_score', 'margin', 'softmax_max')
MIN_VOICED_S = 10.0
TOP_K = 5


def sha256_of(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load_registry(path=REGISTRY):
    return json.loads(Path(path).read_text())


class RagaGate:
    """A registered selective-answer rule. `None` threshold means always abstain."""

    def __init__(self, signal, threshold, name, status, source=None):
        if signal not in SIGNALS:
            raise ValueError(f'Unknown gate signal {signal!r}')
        if threshold is not None and (not np.isfinite(threshold)):
            raise ValueError('Gate threshold must be finite or None')
        self.signal, self.threshold, self.name, self.status, self.source = signal, threshold, name, status, source

    @classmethod
    def load(cls, path):
        path = Path(path)
        doc = json.loads(path.read_text())
        return cls(doc['signal'], doc.get('threshold'), doc['name'], doc['status'], str(path))

    def accepts(self, signals):
        if self.threshold is None:
            return False
        return bool(signals[self.signal] >= self.threshold)

    def describe(self):
        return dict(name=self.name, signal=self.signal, threshold=self.threshold,
                    status=self.status, source=self.source)


class RagaCandidate:
    """A fitted raga model plus the metadata every score must carry."""

    def __init__(self, bundle, sha256, name, path):
        self.model = serial_forest_prediction(bundle['model'])
        self.classes = [str(c) for c in self.model.classes_]
        self.representation = bundle.get('representation', 'elapsed')
        self.feature_version = bundle.get('feature_version')
        if FEATURE_VERSIONS.get(self.representation) != self.feature_version:
            raise ValueError('Bundle representation and feature version disagree')
        self.window_s = bundle.get('window_s')
        self.temperature = float(bundle.get('calibration', {}).get('temperature', 1.0))
        self.sha256, self.name, self.path = sha256, name, str(path)
        self.bundle = bundle

    @classmethod
    def load(cls, ref, registry=REGISTRY):
        """`ref` is a registry name or a bundle path. Registry names verify SHA256."""
        reg = load_registry(registry) if Path(registry).exists() else {}
        if ref in reg.get('candidates', {}):
            entry = reg['candidates'][ref]
            path = ROOT / entry['bundle']
            digest = sha256_of(path)
            if digest != entry['sha256']:
                raise ValueError(f'Registry SHA256 mismatch for candidate {ref!r}: {digest}')
            name = ref
        else:
            path = Path(ref)
            if not path.exists():
                raise ValueError(f'Unknown candidate {ref!r}: not a registry name or a bundle path')
            digest = sha256_of(path)
            name = path.stem
        import joblib
        return cls(joblib.load(path), digest, name, path)

    def default_gate(self, registry=REGISTRY):
        reg = load_registry(registry) if Path(registry).exists() else {}
        entry = reg.get('candidates', {}).get(self.name, {})
        return RagaGate.load(ROOT / entry['gate']) if entry.get('gate') else None

    def raw_scores(self, vector):
        X = np.asarray(vector, dtype=float)[None]
        if hasattr(self.model, 'decision_function'):
            return np.asarray(self.model.decision_function(X), dtype=float)[0], 'decision'
        return np.asarray(self.model.predict_proba(X), dtype=float)[0], 'probability'

    def describe(self):
        return dict(name=self.name, sha256=self.sha256, path=self.path,
                    feature_version=self.feature_version, representation=self.representation,
                    window_s=self.window_s, n_classes=len(self.classes))


def signals_from(scores, kind, temperature):
    top = np.sort(scores)[::-1]
    prob = softmax(scores / temperature) if kind == 'decision' else scores
    return dict(max_score=float(top[0]), margin=float(top[0] - top[1]) if len(top) > 1 else float(top[0]),
                softmax_max=float(prob.max())), prob


def abstain(reason, candidate, gate, voiced_s):
    return dict(answered=False, reason=reason, top1=None, ranked=[], signals=None,
                accepted=False, gate=gate.describe() if gate else None, voiced_s=voiced_s,
                model=candidate.describe())


def score_contour(candidate, f0, tonic_hz, hop_s, gate=None, top_k=TOP_K):
    """Score one melody contour. Never guesses a tonic; never invents a gate."""
    f0 = np.asarray(f0, dtype=float)
    voiced_s = float(np.sum(np.isfinite(f0) & (f0 > 0)) * hop_s)
    if tonic_hz is None or not np.isfinite(tonic_hz) or tonic_hz <= 0:
        return abstain('missing_tonic', candidate, gate, voiced_s)
    if voiced_s < MIN_VOICED_S:
        return abstain('insufficient_melody', candidate, gate, voiced_s)
    vector = feature_vector(f0, float(tonic_hz), float(hop_s), candidate.representation)
    if vector is None:
        return abstain('insufficient_transitions', candidate, gate, voiced_s)
    scores, kind = candidate.raw_scores(vector)
    signals, prob = signals_from(scores, kind, candidate.temperature)
    order = np.argsort(-scores)[:top_k]
    ranked = [dict(raga=candidate.classes[i], score=float(scores[i]), probability=float(prob[i])) for i in order]
    return dict(answered=True, reason=None, top1=ranked[0]['raga'], ranked=ranked, signals=signals,
                accepted=gate.accepts(signals) if gate else False,
                gate=gate.describe() if gate else None, voiced_s=voiced_s,
                model=candidate.describe())


def identify_raga(candidate, audio_path, audio_sha256, start_s, duration_s, cache_dir,
                  gate=None, profile='default', top_k=TOP_K):
    """Bounded audio query through the shared melody frontend, then score_contour."""
    from carnatify.audio.melody_frontend import extract_query, HOP_S
    f0, meta = extract_query(audio_path, audio_sha256, start_s, duration_s, cache_dir, profile)
    result = score_contour(candidate, f0, meta['tonic_hz'], HOP_S, gate, top_k)
    result['query'] = dict(audio_sha256=audio_sha256, start_s=float(start_s), duration_s=float(duration_s),
                           profile=profile, frontend=meta['contract']['version'],
                           tonic_hz=meta['tonic_hz'], extraction_failure=meta['extraction_failure'])
    return result
