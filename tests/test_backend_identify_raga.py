"""/identify-raga: ranked candidates through the contract, never an asserted answer."""
from pathlib import Path
import numpy as np
import pytest
import joblib
from fastapi.testclient import TestClient

from carnatify.ml.raga_runtime import RagaCandidate, RagaGate
from carnatify.ml.distribution_classifier import DistributionKernelRidge
from carnatify.ml.melody_features import FEATURE_VERSIONS, feature_vector

HOP = 128 / 44100


def contour(pattern, seconds=30, tonic=150.0):
    n = int(seconds / HOP)
    steps = np.repeat(np.array(pattern, dtype=float), max(1, n // len(pattern)))[:n]
    return tonic * 2 ** (steps / 1200)


@pytest.fixture
def candidate(tmp_path):
    rng = np.random.default_rng(1)
    X, y = [], []
    for label, pattern in (('A', [0, 200, 400, 700, 900]), ('B', [0, 100, 300, 700, 800])):
        for _ in range(4):
            X.append(feature_vector(contour(np.array(pattern) + rng.normal(0, 15, len(pattern))), 150.0, HOP, 'voiced'))
            y.append(label)
    model = DistributionKernelRidge(alpha=.1, gamma=2, mode='tdms').fit(np.stack(X), np.array(y))
    path = tmp_path / 'raga.joblib'
    joblib.dump(dict(model=model, representation='voiced', feature_version=FEATURE_VERSIONS['voiced'],
                     window_s=30, calibration=dict(temperature=.1)), path)
    return RagaCandidate.load(str(path))


@pytest.fixture
def api(monkeypatch, candidate):
    from backend import main
    monkeypatch.setattr(main.limiter, 'enabled', False)
    monkeypatch.setattr(main, '_separate_vocals_sync', lambda *a: pytest.fail('No separation on this route'))
    gate = RagaGate('margin', 1e9, 'never', 'test gate that never accepts')
    monkeypatch.setattr(main, '_get_raga_candidate', lambda: (candidate, gate))
    seen = []

    def extract(path):
        assert Path(path).exists()
        seen.append(Path(path))
        return contour([0, 200, 400, 700, 900]), 150.0, HOP, 30.0
    monkeypatch.setattr(main, '_extract_melody_mix', extract)
    with TestClient(main.app) as client:
        yield client, seen


def test_identify_raga_returns_candidates_never_asserts_and_cleans_upload(api):
    client, seen = api
    r = client.post('/identify-raga', files={'file': ('clip.wav', b'x' * 2000, 'audio/wav')})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['asserted'] is False and body['answered'] is True
    assert body['candidates'][0]['raga'] == 'A'
    assert set(body['signals']) == {'max_score', 'margin', 'softmax_max'}
    assert body['gate']['would_accept'] is False and body['gate']['name'] == 'never'
    assert body['model']['feature_version'] == FEATURE_VERSIONS['voiced']
    assert seen and not seen[0].exists()


def test_identify_raga_abstains_without_tonic(api, monkeypatch):
    from backend import main
    client, _ = api
    monkeypatch.setattr(main, '_extract_melody_mix', lambda p: (contour([0, 200, 400, 700, 900]), None, HOP, 30.0))
    body = client.post('/identify-raga', files={'file': ('clip.wav', b'x', 'audio/wav')}).json()
    assert body['answered'] is False and body['reason'] == 'missing_tonic' and body['candidates'] == []


def test_identify_raga_503_when_candidate_missing(monkeypatch):
    from backend import main
    monkeypatch.setattr(main.limiter, 'enabled', False)
    monkeypatch.setattr(main, '_get_raga_candidate', lambda: (None, None))
    with TestClient(main.app) as client:
        r = client.post('/identify-raga', files={'file': ('clip.wav', b'x', 'audio/wav')})
    assert r.status_code == 503


def test_identify_raga_rejects_unknown_content_type(api):
    client, _ = api
    r = client.post('/identify-raga', files={'file': ('clip.bin', b'x', 'application/octet-stream')})
    assert r.status_code == 415


def test_committed_registry_resolves_from_backend_root():
    from backend import main
    assert main._RAGA_REGISTRY.exists()


def test_raga_candidate_load_failure_is_retried_not_cached(monkeypatch, tmp_path):
    from backend import main
    monkeypatch.setattr(main, '_RAGA_CANDIDATE', None)
    monkeypatch.setattr(main, '_RAGA_REGISTRY', tmp_path / 'missing.json')
    assert main._get_raga_candidate() == (None, None)
    assert main._RAGA_CANDIDATE is None


def test_raga_gate_failure_degrades_to_no_gate(monkeypatch, candidate):
    from backend import main
    import carnatify.ml.raga_runtime as rt
    monkeypatch.setattr(main, '_RAGA_CANDIDATE', None)
    monkeypatch.setattr(rt.RagaCandidate, 'load', classmethod(lambda cls, *a, **k: candidate))
    monkeypatch.setattr(rt.RagaCandidate, 'default_gate', lambda self, **k: (_ for _ in ()).throw(FileNotFoundError('gate.json')))
    assert main._get_raga_candidate() == (candidate, None)
    assert main._RAGA_CANDIDATE == (candidate, None)


@pytest.mark.parametrize('ct,suffix', [('audio/webm;codecs=opus', '.ogg'), ('audio/mp4', '.m4a'),
                                       ('audio/mpeg', '.mp3'), ('audio/x-wav', '.wav'),
                                       ('application/octet-stream', None), (None, None)])
def test_upload_suffix_shared_by_all_routes(ct, suffix):
    from backend import main
    assert main._upload_suffix(ct) == suffix


# ── iOS upload formats (docs/ios/BACKEND_READINESS.md, 2026-10-11) ──────────

def test_sniff_suffix_recognises_ios_containers():
    from backend.main import _sniff_suffix
    assert _sniff_suffix(b"\x00\x00\x00\x20ftypM4A \x00\x00") == ".m4a"
    assert _sniff_suffix(b"caff\x00\x01\x00\x00desc") == ".caf"
    assert _sniff_suffix(b"RIFF\x24\x00\x00\x00WAVEfmt ") == ".wav"
    assert _sniff_suffix(b"OggS\x00\x02\x00\x00\x00\x00\x00\x00") == ".ogg"
    assert _sniff_suffix(b"ID3\x04\x00\x00\x00\x00\x00\x00\x00\x00") == ".mp3"
    assert _sniff_suffix(b"\x1a\x45\xdf\xa3\x01\x00\x00\x00\x00\x00\x00\x1f") == ".webm"
    assert _sniff_suffix(b"not audio at all") is None


def test_resolve_suffix_prefers_bytes_over_declared_type():
    from backend.main import _resolve_upload_suffix
    m4a = b"\x00\x00\x00\x20ftypM4A \x00\x00"
    assert _resolve_upload_suffix("application/octet-stream", m4a) == ".m4a"
    assert _resolve_upload_suffix("audio/x-caf", b"caff\x00\x01\x00\x00") == ".caf"
    assert _resolve_upload_suffix(None, m4a) == ".m4a"
    assert _resolve_upload_suffix("audio/wav", b"garbage-bytes") == ".wav"
    assert _resolve_upload_suffix("application/octet-stream", b"garbage-bytes") is None


def test_public_identity_strips_server_paths():
    from backend.main import _public_identity
    assert _public_identity({"name": "m", "path": "/Users/x/raga.joblib"}, ("path",)) == {"name": "m"}
    assert _public_identity(None, ("path",)) is None
