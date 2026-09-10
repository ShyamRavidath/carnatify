from scripts.audit_strict_audio_decode import decode_status


def test_evaluation_decode_rejects_stale_corpus_identity(tmp_path,monkeypatch):
    import json
    import sys
    import pytest
    from scripts import audit_strict_audio_decode as module
    corpus=tmp_path/'corpus.json';identity=tmp_path/'identity.json'
    corpus.write_text(json.dumps(dict(rows=[])))
    identity.write_text(json.dumps(dict(corpus_sha256='stale',rows=[])))
    monkeypatch.setattr(module.shutil,'which',lambda command:'/fake/'+command)
    monkeypatch.setattr(sys,'argv',['audit','--evaluation-corpus',str(corpus),
        '--identity',str(identity),'--out',str(tmp_path/'out')])
    with pytest.raises(ValueError,match='corpus changed'):module.main()


def test_decode_outcomes_do_not_conflate_diagnostics_timeout_and_error():
    assert decode_status(0,0)=='clean'
    assert decode_status(0,12)=='decoder_diagnostic'
    assert decode_status(1,12)=='decoder_error'
    assert decode_status(None,0,True)=='timeout'
