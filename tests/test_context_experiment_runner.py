import sys
from types import SimpleNamespace
import pytest
from scripts import finish_context_experiment as module
from scripts.raga_pipeline import sha,write_json


def setup(tmp_path,monkeypatch):
    run=tmp_path/'run';out=tmp_path/'out';recovery=tmp_path/'recovery'
    write_json(run/'plan.json',dict(rows=[]))
    write_json(recovery/'plan.json',dict(row=dict(track='r')))
    for name in ('folds','identity','corpus'):write_json(tmp_path/(name+'.json'),{})
    monkeypatch.setattr(sys,'argv',['finish','--run',str(run),'--pid','12345','--out',str(out),
        '--folds',str(tmp_path/'folds.json'),'--identity',str(tmp_path/'identity.json'),
        '--corpus',str(tmp_path/'corpus.json'),'--recovery',str(recovery)])
    return run,out


def test_runner_stops_when_specific_parent_is_gone(tmp_path,monkeypatch):
    run,out=setup(tmp_path,monkeypatch)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1,stdout=''))
    with pytest.raises(RuntimeError,match='no longer running'):module.main()
    assert not (out/'result.json').exists()


def test_runner_orders_recovery_merge_fit_and_matched_evaluation(tmp_path,monkeypatch):
    run,out=setup(tmp_path,monkeypatch)
    write_json(run/'extraction.json',dict(plan_sha256=sha(run/'plan.json'),
        rows=[dict(track='r',rejected=[dict(reason='libsndfile_window_decode_error')])]))
    commands=[]
    def fake(command,**kwargs):commands.append(command);return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',fake)
    module.main()
    assert [module.Path(c[1]).name for c in commands]==['merge_context_decode_recovery.py',
        'raga_kernel_benchmark.py','train_raga_svc.py','evaluate_annotated_raga.py']
    assert commands[-1][commands[-1].index('--window-s')+1]=='180'
    assert '--audio-identity' in commands[-2]
    assert (out/'result.json').exists()
