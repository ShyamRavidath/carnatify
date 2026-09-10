from argparse import Namespace
from pathlib import Path
import pytest
from scripts.carnatify_pipeline import commands


def test_pipeline_uses_one_versioned_run_without_shell_expansion():
    root=Path('/tmp/run with spaces')
    for stage,n in [('data-prep',4),('feature-extract',6),('train',6),('evaluate',1)]:
        steps=commands(Namespace(run=root,stage=stage,audio=None,output=None))
        assert len(steps)==n
        assert any('run with spaces' in str(a) for _,argv in steps for a in argv)
        if stage in {'data-prep','feature-extract'}:
            assert steps[0][1][0]=='--run'  # argparse global option precedes subcommand


def test_byte_identity_and_deduplication_are_standard_not_opt_in():
    args=Namespace(run=Path('/tmp/run'),stage='feature-extract',audio=None,output=None)
    steps=commands(args)
    assert steps[-1][0]=='quarantine_audio_overlap.py'
    assert '--deduplicate-audio' in steps[-1][1] and '--require-source-match' in steps[-1][1]
    assert steps[-2][0]=='build_evaluation_audio_identity.py'
    args.stage='train'
    assert commands(args)[0][0]=='guard_archive_evaluation_artists.py'
    assert commands(args)[1][0]=='regroup_file_artists.py'
    assert '--reserved-corpus' in commands(args)[1][1]
    assert commands(args)[2][0]=='audit_strict_audio_decode.py'
    assert commands(args)[3][0]=='filter_strict_decode_features.py'
    assert Path('/tmp/run/train_decode_clean').resolve() in commands(args)[-1][1]
    assert '--audio-identity' in commands(args)[-1][1]
    args.stage='evaluate'
    assert '--skip-baseline' in commands(args)[0][1]


def test_infer_requires_explicit_input_and_output():
    with pytest.raises(ValueError):
        commands(Namespace(run=Path('/tmp/run'),stage='infer',audio=None,output=None))


def test_evaluation_and_references_use_run_scoped_metadata():
    args=Namespace(run=Path('/tmp/run'),stage='data-prep',audio=None,output=None,min_tracks=5)
    steps=commands(args)
    assert steps[0][1][-1]==5
    assert steps[-1][1][1]==Path('/tmp/run/evaluation_corpus.json').resolve()
    args.stage='evaluate'
    assert Path('/tmp/run/evaluation_corpus.json').resolve() in commands(args)[0][1]


def test_pitch_activity_is_explicit_opt_in():
    args=Namespace(run=Path('/tmp/run'),stage='infer',audio=Path('concert.wav'),output=Path('result.json'))
    assert '--pitch-activity-model' not in commands(args)[0][1]
    args.pitch_activity_model=Path('/tmp/activity/model.joblib')
    assert commands(args)[0][1][-2:]==['--pitch-activity-model',args.pitch_activity_model]


def test_expanded_song_experiment_is_forwarded_explicitly():
    args=Namespace(run=Path('/tmp/run'),stage='infer',audio=Path('concert.wav'),output=Path('result.json'),
                   composition_catalog=Path('/tmp/full.npz'),composition_window_s=180,composition_raga_prior=True)
    argv=commands(args)[0][1]
    assert argv[argv.index('--composition-catalog')+1]==args.composition_catalog
    assert argv[argv.index('--composition-window-s')+1]==180
    assert '--composition-raga-prior' in argv


def test_silence_boundary_policy_is_explicit_opt_in():
    args=Namespace(run=Path('/tmp/run'),stage='infer',audio=Path('concert.wav'),output=Path('result.json'))
    assert '--silence-bounded-context' not in commands(args)[0][1]
    args.silence_bounded_context=True
    assert '--silence-bounded-context' in commands(args)[0][1]
