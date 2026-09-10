"""Single reproducible entry point for the new candidate pipeline.

Preparation uses only existing data/annotations. No deployed artifacts, human
labels or raw audio are overwritten. Model output remains candidate-only until
independent coverage, accuracy and rejection checks pass.
"""
from __future__ import annotations
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent


def commands(args):
    run=args.run.resolve();archive=run/'archive';comp=run/'compmusic';train=run/'train'
    unfiltered=run/'train_unfiltered';identity=run/'audio_identity.json'
    artist_guarded=run/'train_integrity_guarded'
    artist_grouped=run/'train_artist_grouped'
    decode_audit=run/'strict_decode'
    decode_clean=run/'train_decode_clean'
    evaluation_identity=run/'evaluation_audio_identity.json'
    admission=run/'taxonomy_admission.json';model=run/'raga.joblib'
    corpus=run/'evaluation_corpus.json'
    if args.stage=='data-prep':
        return [('raga_pipeline.py',['--run',archive,'data-prep','--min-tracks',getattr(args,'min_tracks',10)]),
                ('audit_training_taxonomy.py',['--archive-run',archive,'--out',admission]),
                ('build_annotated_corpus.py',['--training-run',archive,'--out',corpus]),
                ('build_composition_catalog.py',['--corpus',corpus,'--out',run/'compositions.npz'])]
    if args.stage=='feature-extract':
        return [('raga_pipeline.py',['--run',archive,'feature-extract']),
                ('prepare_compmusic_features.py',['--out',comp,'--reserved-corpus',corpus]),
                ('merge_raga_training.py',['--archive-run',archive,'--compmusic-run',comp,
                                          '--admission',admission,'--out',unfiltered]),
                ('audit_archive_audio_identity.py',['--manifest',unfiltered/'manifest.json','--out',identity,
                    '--refreshed-metadata',ROOT/'data/overhaul/archive_identity_metadata']),
                ('build_evaluation_audio_identity.py',['--corpus',corpus,'--out',evaluation_identity]),
                ('quarantine_audio_overlap.py',['--run',unfiltered,'--out',train,'--identity',identity,
                    '--evaluation',evaluation_identity,'--deduplicate-audio','--require-source-match'])]
    if args.stage=='train':
        return [('guard_archive_evaluation_artists.py',['--run',train,'--corpus',corpus,'--out',artist_guarded,
                    '--audio-identity',identity]),
                ('regroup_file_artists.py',['--run',artist_guarded,'--out',artist_grouped,'--identity',identity,
                    '--reserved-corpus',corpus]),
                ('audit_strict_audio_decode.py',['--manifest',artist_grouped/'manifest.json',
                    '--identity',identity,'--out',decode_audit]),
                ('filter_strict_decode_features.py',['--run',artist_grouped,'--out',decode_clean,
                    '--identity',identity,'--decode-audit',decode_audit/'result.json']),
                ('raga_kernel_benchmark.py',['--run',decode_clean,'--out',decode_clean/'kernel_benchmark.json',
                                            '--arms','legacy_kernel_ridge']),
                ('train_raga_svc.py',['--run',decode_clean,'--family','kernel_ridge','--representation','voiced',
                                     '--oof',decode_clean/'legacy_kernel_ridge_oof.npz','--out',model,
                                     '--audio-identity',identity])]
    if args.stage=='evaluate':
        return [('evaluate_annotated_raga.py',['--model',model,'--corpus',corpus,'--name','candidate',
                                             '--window-s',getattr(args,'window_s',60),
                                             '--skip-baseline',
                                             '--out',run/'evaluation.json'])]
    if args.stage=='infer':
        if not args.audio or not args.output:raise ValueError('infer requires --audio and --output')
        activity=getattr(args,'pitch_activity_model',None)
        return [('concert_pipeline.py',[args.audio,'--model',model,'--output',args.output,
                                         '--window-s',getattr(args,'window_s',60),
                                         '--composition-catalog',getattr(args,'composition_catalog',None) or run/'compositions.npz',
                                         '--composition-window-s',getattr(args,'composition_window_s',60),
                                         *(['--composition-raga-prior'] if getattr(args,'composition_raga_prior',False) else []),
                                         *(['--silence-bounded-context'] if getattr(args,'silence_bounded_context',False) else []),
                                         *(['--pitch-activity-model',activity] if activity else [])])]
    raise ValueError('Unknown pipeline stage')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage',choices=['data-prep','feature-extract','train','evaluate','infer'])
    ap.add_argument('--run',type=Path,required=True,help='Versioned run directory inside the repository')
    ap.add_argument('--audio',type=Path);ap.add_argument('--output',type=Path)
    ap.add_argument('--min-tracks',type=int,default=10,help='Preparation minimum before taxonomy admission')
    ap.add_argument('--window-s',type=int,choices=[60,180],default=60,help='Raga evaluation/inference context')
    ap.add_argument('--pitch-activity-model',type=Path,help='Optional development activity artifact for infer only')
    ap.add_argument('--composition-catalog',type=Path,help='Explicit alternate song catalog for infer only')
    ap.add_argument('--composition-window-s',type=int,choices=[60,180],default=60)
    ap.add_argument('--composition-raga-prior',action='store_true')
    ap.add_argument('--silence-bounded-context',action='store_true',help='Experimental inference context cap at detected silence')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    if args.min_tracks<1:ap.error('--min-tracks must be positive')
    if args.pitch_activity_model and args.stage!='infer':ap.error('--pitch-activity-model applies only to infer')
    if args.silence_bounded_context and args.stage!='infer':ap.error('--silence-bounded-context applies only to infer')
    if args.stage!='infer' and (args.composition_catalog or args.composition_window_s!=60 or args.composition_raga_prior):
        ap.error('Composition settings apply only to infer')
    if not args.run.resolve().is_relative_to(ROOT):ap.error('--run must be within the repository')
    if args.run.resolve() in {ROOT,ROOT/'models'}:ap.error('Use a dedicated run directory')
    try:steps=commands(args)
    except ValueError as exc:ap.error(str(exc))
    for script,argv in steps:
        cmd=[sys.executable,str(ROOT/'scripts'/script),*[str(x) for x in argv]]
        print('Running:',script,*map(str,argv),flush=True)
        if not args.dry_run:subprocess.run(cmd,cwd=ROOT,check=True)


if __name__=='__main__':main()
