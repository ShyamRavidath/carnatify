#!/usr/bin/env python3
"""Duration probe — the GPU half, on an EC2 GPU box. Resumable, decides nothing.

Sibling of `colab_duration_probe.py`, same loop and same guarantees, with the
Colab-only parts removed: no Drive mount, no FUSE remount dance, checkpoints go
to local disk and optionally to S3. Produces exactly what the scorer needs:
`probe_results.json`, `negative_results.json`, and the v2 ASR cache they were
read from. Scoring happens on the laptop under the frozen pre-registration.

Migration from a Colab run is supported and is the expected case: drop the
Drive checkpoint at `<root>/data/asr_cache_v2.json` and this resumes from it.
Cache keys are `sha256(audio)[:24] + ':' + asr_config_id()`, which contain
nothing machine-specific, so a half-finished run travels.

**Mixed hardware is recorded, not hidden.** Whisper is fp32 and near
deterministic, but a window transcribed on a T4 and one on an L4 are not
guaranteed bit-identical, and a paired 30s -> 300s contrast is exactly where a
systematic device difference would hide. So: `--prior-hardware` names what the
inherited cache entries came off, every window this run touches is stamped with
this box's GPU in `run_log.json`, and the log is rewritten after every chunk so
an interrupted session still leaves a truthful record. Keep whole titles on one
device where you can — resume on a chunk boundary and this happens by itself
(CHUNK=5 and 5 windows per title line up).

Setup on a Deep Learning AMI (see the runbook in the workhorse handoff):
    sudo apt-get update && sudo apt-get install -y ffmpeg unzip
    pip install -q openai-whisper demucs librosa soundfile
    mkdir -p ~/probe && cd ~/probe        # put the three zips here

Run under tmux, always — an SSH drop must not kill 12 h of GPU:
    tmux new -s probe
    python aws_duration_probe.py --root ~/probe --bundles ~/probe \\
        --prior-hardware 'Tesla T4 (Colab), windows 1-80' \\
        --s3-checkpoint s3://YOUR-BUCKET/duration_probe
    # detach with ctrl-b d, reattach with: tmux attach -t probe
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

BUNDLES = ('probe_code.zip', 'probe_anchored.zip', 'probe_negatives.zip')
ARMS = {'anchored': ('data/duration_probe/anchored',
                     'data/duration_probe/truth_anchored.json'),
        'negatives': ('data/duration_probe/negatives',
                      'data/duration_probe/truth_negatives.json')}


def step(msg: str) -> None:
    print(f"\n{'=' * 68}\n== {msg}\n{'=' * 68}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def s3_cp(src, dst) -> None:
    subprocess.run(['aws', 's3', 'cp', str(src), str(dst), '--only-show-errors'],
                   check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='~/probe',
                    help='working tree; the bundles unzip into it')
    ap.add_argument('--bundles', default='~/probe',
                    help='directory holding the three probe_*.zip files')
    ap.add_argument('--out', default=None,
                    help='where results land (default <root>/out)')
    ap.add_argument('--chunk', type=int, default=5,
                    help='windows per checkpoint. A session death costs at '
                         'most one chunk; 5 windows is one recall title')
    ap.add_argument('--demucs-device', default='cuda', choices=('cuda', 'cpu'),
                    help="identify_clip pins Demucs to CPU (identify_clip.py:"
                         "644); on a 4-vCPU box that costs more wall time than "
                         "the GPU work it feeds. 'cuda' patches "
                         "demucs.apply.apply_model without editing the file")
    ap.add_argument('--arms', nargs='+', default=list(ARMS), choices=list(ARMS))
    ap.add_argument('--s3-checkpoint', default=None,
                    help='s3://bucket/prefix — cache + results copied there '
                         'after every chunk. MANDATORY on spot instances; the '
                         'root EBS volume dies with the instance')
    ap.add_argument('--prior-hardware', default=None,
                    help='what the inherited cache entries were produced on, '
                         'e.g. "Tesla T4 (Colab), windows 1-80"')
    args = ap.parse_args()

    root = Path(args.root).expanduser()
    bundles = Path(args.bundles).expanduser()
    out = Path(args.out).expanduser() if args.out else root / 'out'
    out.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------- 1. restore the bundles
    step('1/6 Restore the bundles')
    for zname in BUNDLES:
        src = bundles / zname
        if not src.exists():
            sys.exit(f'MISSING {src}\nBuild on the laptop with:\n  venv_train/'
                     f'bin/python scripts/build_probe_colab_bundle.py\nthen '
                     f'copy the zips here (scp, or aws s3 cp).')
    for zname in BUNDLES:
        marker = root / f'.restored_{zname}'
        if marker.exists():
            print(f'  {zname}: already restored')
            continue
        print(f'  unzipping {zname} ...', flush=True)
        with zipfile.ZipFile(bundles / zname) as z:
            z.extractall(root)
        marker.write_text('ok')

    import torch
    if not torch.cuda.is_available():
        sys.exit('No CUDA device. Wrong AMI, wrong instance type, or the '
                 'driver did not come up (check `nvidia-smi`). On CPU this job '
                 'takes weeks.')
    gpu = torch.cuda.get_device_name(0)
    print(f'  GPU: {gpu}   torch {torch.__version__}')

    step('2/6 Imports')
    import whisper
    import demucs
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / 'scripts'))
    import identify_clip as ic
    spec = importlib.util.spec_from_file_location(
        'build_asr_cache_v2', root / 'scripts' / 'build_asr_cache_v2.py')
    bac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bac)
    print(f'  asr_config_id: {ic.asr_config_id()}')
    print(f'  cache file   : {ic.CACHE2}')

    run_log = {
        'started': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'host': 'ec2', 'gpu': gpu,
        'versions': {'torch': torch.__version__,
                     'whisper': getattr(whisper, '__version__', '?'),
                     'demucs': getattr(demucs, '__version__', '?')},
        'asr_config_id': ic.asr_config_id(),
        'demucs_device': args.demucs_device,
        'prior_hardware': args.prior_hardware,
        'chunk': args.chunk,
        'windows_by_gpu': {},        # gpu -> [window stems produced HERE]
        'chunks': [],
    }
    log_path = out / 'run_log.json'

    def save_log():
        """Written after every chunk, not at the end: a run that dies at hour
        nine must still leave a truthful record of what came off which GPU."""
        log_path.write_text(json.dumps(run_log, indent=1))
        if args.s3_checkpoint:
            s3_cp(log_path, f'{args.s3_checkpoint}/run_log.json')

    # ------------------------------------------------- 3. verify before spending
    step('3/6 Verify every window against its sidecar (before any GPU is spent)')
    # Filenames are not identity. If this audio is not the audio the sidecars
    # describe, the cache binds transcripts to the wrong windows and, on the
    # negative arm, to the wrong ear labels — the defect that killed the v1
    # negative arm. Cheap to rule out, so it is ruled out here rather than
    # discovered as a strange number in three days.
    todo: dict[str, list[Path]] = {}
    for arm in args.arms:
        rel_dir, rel_side = ARMS[arm]
        audio_dir, side_path = root / rel_dir, root / rel_side
        side = json.loads(side_path.read_text())
        windows = side['windows']
        bad, absent, files = [], [], []
        for stem, meta in sorted(windows.items()):
            wav = audio_dir / f'{stem}.wav'
            if not wav.exists():
                absent.append(stem)
            elif (meta.get('audio_sha256')
                  and sha256_file(wav) != meta['audio_sha256']):
                bad.append(stem)
            else:
                # Every sidecar window is transcribed, including the 9
                # in-catalog negatives that feed no readout: validate_negatives
                # wants a bijection, and a cheaper run is an invalid one.
                files.append(wav)
        if absent or bad:
            sys.exit(f'{arm}: {len(absent)} windows missing, {len(bad)} do not '
                     f'match their stamped audio_sha256 (e.g. '
                     f'{(absent + bad)[:3]}). Re-copy the bundle; do not run.')
        todo[arm] = files
        print(f'  {arm:<10} {len(windows)} windows verified, {len(files)} in '
              f'scope')
    run_log['windows_in_scope'] = {a: len(f) for a, f in todo.items()}

    # ------------------------------------------------- 4. transcribe, resumably
    step('4/6 Build the v2 ASR cache (resumable; checkpointed every chunk)')
    cache_local = ic.CACHE2
    cache_local.parent.mkdir(parents=True, exist_ok=True)
    if not cache_local.exists() and args.s3_checkpoint:
        try:
            s3_cp(f'{args.s3_checkpoint}/asr_cache_v2.json', cache_local)
            print('  restored checkpoint from S3')
        except subprocess.CalledProcessError:
            print('  no checkpoint on S3 yet — starting fresh')
    if cache_local.exists():
        n = len(json.loads(cache_local.read_text()).get('entries', {}))
        print(f'  inherited cache: {n} entries '
              f'({cache_local.stat().st_size / 1e6:.0f} MB)'
              + (f' from {args.prior_hardware}' if args.prior_hardware else ''))
        run_log['inherited_entries'] = n

    if args.demucs_device != 'cpu':
        # identify_clip does `from demucs.apply import apply_model` INSIDE
        # _vocal_stem_16k, so patching the module attribute is picked up per
        # call and identify_clip.py itself stays byte-unchanged.
        import demucs.apply as _da
        _orig_apply = _da.apply_model

        def _apply_on_device(model, mix, **kw):
            kw['device'] = args.demucs_device
            try:
                model.to(args.demucs_device)
            except Exception:
                pass
            return _orig_apply(model, mix, **kw)

        _da.apply_model = _apply_on_device
        print(f'  Demucs patched to {args.demucs_device} (recorded as a '
              f'deviation in run_log.json)')

    def pending(files):
        """Windows with no cache entry yet, recomputed every pass: a resumed
        run never re-transcribes and never skips a gap."""
        cache = ic.load_cache_v2()
        return [p for p in files
                if ic.cache2_key(ic.audio_sha256(p)) not in cache['entries']]

    stage = root / '_chunk'
    for arm in args.arms:
        files = todo[arm]
        left = pending(files)
        print(f'\n{arm}: {len(files) - len(left)}/{len(files)} already cached, '
              f'{len(left)} to go', flush=True)
        for i in range(0, len(left), args.chunk):
            batch = left[i:i + args.chunk]
            if stage.exists():
                shutil.rmtree(stage)
            stage.mkdir(parents=True)
            for p in batch:
                os.symlink(p, stage / p.name)   # hashes follow the symlink
            t0 = time.time()
            bac.build(stage)                    # the registered cache builder
            dt = time.time() - t0
            run_log['windows_by_gpu'].setdefault(gpu, []).extend(
                p.stem for p in batch)
            run_log['chunks'].append({'arm': arm, 'n': len(batch),
                                      'seconds': round(dt, 1), 'gpu': gpu})
            save_log()
            if args.s3_checkpoint:
                s3_cp(cache_local, f'{args.s3_checkpoint}/asr_cache_v2.json')
            done, rate = i + len(batch), dt / len(batch)
            print(f'  [{arm} {done}/{len(left)}] {dt / 60:.1f} min '
                  f'({rate:.0f}s/window)  ~{rate * (len(left) - done) / 3600:.1f}'
                  f' h left in this arm', flush=True)
        still = pending(files)
        if still:
            sys.exit(f'{arm}: {len(still)} windows still uncached after the '
                     f'loop (e.g. {[p.name for p in still[:3]]}). Something '
                     f'failed silently — read the log before re-running.')
        print(f'{arm}: fully cached', flush=True)

    # ------------------------------------------------- 5. inference, cache-only
    step('5/6 Run identify_clip over both arms (read-only; must not transcribe)')
    if set(args.arms) != set(ARMS):
        print('  SKIPPED — inference needs both arms cached; re-run without '
              '--arms once the other arm is done.')
        return
    env = {**os.environ, 'CARNATIFY_ASR_BACKEND': 'whisper'}
    for arm, out_name in (('anchored', 'probe_results.json'),
                          ('negatives', 'negative_results.json')):
        cmd = [sys.executable, '-u', 'identify_clip.py', ARMS[arm][0],
               '--json', '--no-raga', '--cache-v2']
        print(f"\n$ CARNATIFY_ASR_BACKEND=whisper {' '.join(cmd)}", flush=True)
        p = subprocess.run(cmd, cwd=root, env=env, capture_output=True,
                           text=True)
        print(p.stderr[-2000:], flush=True)
        if p.returncode != 0:
            sys.exit(f'identify_clip failed on {arm} (rc={p.returncode})')
        rows = json.loads(p.stdout)
        misses = [r.get('file') for r in rows if r.get('cache_v2') == 'MISS']
        if misses:
            sys.exit(f'{len(misses)} cache MISSes on {arm} (e.g. {misses[:3]}). '
                     f'A SCORE with misses is invalid — re-run step 4.')
        (out / out_name).write_text(json.dumps(rows, indent=1))
        run_log.setdefault('results', {})[arm] = {'rows': len(rows),
                                                  'misses': 0}
        print(f'  {arm}: {len(rows)} rows, 0 cache misses -> '
              f'{out / out_name}', flush=True)

    # ------------------------------------------------- 6. hand back
    step('6/6 Hand-back bundle')
    run_log['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    save_log()
    handback = out / 'probe_handback.zip'
    with zipfile.ZipFile(handback, 'w', zipfile.ZIP_DEFLATED,
                         allowZip64=True) as z:
        for p in (cache_local, out / 'probe_results.json',
                  out / 'negative_results.json', log_path):
            z.write(p, p.name)
    if args.s3_checkpoint:
        s3_cp(handback, f'{args.s3_checkpoint}/probe_handback.zip')
    print(f'  {handback}  ({handback.stat().st_size / 1e6:.0f} MB)')
    print(f"""
Pull it to the laptop, then from the repo root:

  scp -i <key.pem> ubuntu@<ip>:{handback} /tmp/
  unzip -o /tmp/probe_handback.zip -d /tmp/probe_handback
  venv_train/bin/python scripts/merge_asr_cache_v2.py \\
      /tmp/probe_handback/asr_cache_v2.json
  venv_train/bin/python scripts/duration_probe_score.py \\
      --results /tmp/probe_handback/probe_results.json \\
      --truth data/duration_probe/truth_anchored.json \\
      --negative-results /tmp/probe_handback/negative_results.json \\
      --negative-truth data/duration_probe/truth_negatives.json

Then TERMINATE the instance. Quote the scorer output verbatim into
AGENT_LOG.md, with run_log.json's gpu / prior_hardware / demucs_device beside
it. Nothing here decides anything: the scorer applies the frozen rule, and a
duration-probe pass is not wild-phone readiness.
""")


if __name__ == '__main__':
    main()
