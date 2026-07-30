#!/usr/bin/env python3
"""Duration probe — the GPU half, on Colab. Resumable, and it decides nothing.

What this produces is exactly the three files the scorer needs and nothing
else: `/tmp/probe.json`, `/tmp/neg.json` and the v2 ASR cache they were read
from. Scoring happens back on the laptop, where `duration_probe_score.py`
applies the frozen pre-registration (`DURATION_PROBE_PREREGISTRATION.md`).

Why this runs here at all: measured local throughput at `large-v3-turbo`,
mix-only 4 passes, is 30s window -> 256s wall and 300s window -> 1500s wall.
The registered 7-pass product config over both arms is ~116 whisper-hours of
audio; that is not a laptop job.

WHAT IT COSTS, honestly, so nobody is surprised at hour nine
-----------------------------------------------------------
* recall arm: 60 titles x (30+60+90+180+300)s = 11.0 h unique audio
* negative arm: **all 70 items** x (30+300)s = 6.4 h unique audio
* every second is transcribed 7 times (4 mix + 3 Demucs stem passes)
  -> 122 whisper-hours, not the 116 the brief estimated

`parse_negative_labels.py` bills 61 items (5.6 h, ~39 whisper-hours) because
the 9 `in-catalog` negatives feed no registered readout. **They still have to
be transcribed.** The frozen validity gate demands an exact bijection between
the negative sidecar and the result rows (`validate_negatives`, prereg §6b), so
a run missing 18 windows is invalid rather than cheaper. Six whisper-hours is
the price of not touching a frozen gate to save them.

`identify_clip._whisper_hyps` hard-codes `fp16=False` and the config id says
`fp16=0`, so Whisper runs **fp32 even on the GPU** — that is not a bug to fix
here. Changing it would change `asr_config_id()`, which is the cache key, which
is the whole binding. Expect roughly 10-20 h of GPU across several sessions.
That is why every step below is resumable and why the cache is checkpointed to
Drive after every chunk.

RESUMING
--------
Just run it again. It re-derives what is left from the cache itself: each
window's `audio_sha256` is hashed, `cache2_key` is looked up, and only misses
are transcribed. Interrupt it whenever; you lose at most one chunk.

INPUTS  (upload with `scripts/build_probe_colab_bundle.py`, then to Drive at
         MyDrive/carnatify/duration_probe/)
    probe_code.zip        identify_clip.py + registry/lyrics (~9 MB)
    probe_anchored.zip    300 recall windows + truth_anchored.json (~1.3 GB)
    probe_negatives.zip   140 negative windows + truth_negatives.json (~0.8 GB)

OUTPUTS (all to MyDrive/carnatify/duration_probe/out/)
    asr_cache_v2.json     the checkpoint, rewritten after every chunk
    probe_results.json    <- scorer's --results
    negative_results.json <- scorer's --negative-results
    run_log.json          devices, versions, timings, cache-miss counts
    probe_handback.zip    all four, zipped, for one download

Run (Colab, GPU runtime, ideally L4/A100):
    %run colab_duration_probe.py
"""
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

# ----------------------------------------------------------------- settings
DRIVE = Path('/content/drive/MyDrive/carnatify/duration_probe')
OUT = DRIVE / 'out'
WORK = Path('/content/carnatify')
CHUNK = 10                 # windows per Drive checkpoint

# Demucs runs on CPU inside identify_clip.py (`apply_model(..., device='cpu')`,
# identify_clip.py:644), which on a 2-vCPU Colab VM would cost more wall time
# than the GPU transcription it feeds. This runs it on the GPU instead by
# patching `demucs.apply.apply_model` — identify_clip imports that symbol
# INSIDE the function, so the patch is picked up per call and the file itself
# is untouched.
#
# This is a deviation and it is recorded as one, in `run_log.json` and in
# whatever gets quoted into AGENT_LOG.md. It changes stem numerics (fp32 CUDA
# vs fp32 CPU reduction order), not the model, the weights, the config id or
# the estimand, and it applies identically to every window of both arms and
# every duration. Set to 'cpu' if you would rather have bit-comparability with
# a local run than finish this decade.
DEMUCS_DEVICE = 'cuda'

BUNDLES = {'code': 'probe_code.zip',
           'anchored': 'probe_anchored.zip',
           'negatives': 'probe_negatives.zip'}
ARMS = {'anchored': ('data/duration_probe/anchored',
                     'data/duration_probe/truth_anchored.json'),
        'negatives': ('data/duration_probe/negatives',
                      'data/duration_probe/truth_negatives.json')}
RUN_LOG: dict = {'started': time.strftime('%Y-%m-%dT%H:%M:%S'),
                 'demucs_device_requested': DEMUCS_DEVICE, 'chunks': []}


def step(msg: str) -> None:
    print(f"\n{'=' * 68}\n== {msg}\n{'=' * 68}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def drive_retry(fn, what, tries=4):
    """Colab's Drive FUSE mount drops under IO (OSError 107). Remount, retry."""
    for i in range(1, tries + 1):
        try:
            return fn()
        except OSError as exc:
            if i == tries:
                raise
            print(f'!! {what} failed ({exc.__class__.__name__}: {exc}); '
                  f'remounting Drive ({i}/{tries - 1})', flush=True)
            from google.colab import drive          # noqa: colab-only
            time.sleep(5)
            drive.mount('/content/drive', force_remount=True)
            time.sleep(5)


# ------------------------------------------------- 1. drive, bundles, deps
step('1/6 Mount Drive, restore the bundles')
if not Path('/content/drive/MyDrive').exists():
    from google.colab import drive                  # noqa: colab-only
    drive.mount('/content/drive')
OUT.mkdir(parents=True, exist_ok=True)

for name, zname in BUNDLES.items():
    src = DRIVE / zname
    if not drive_retry(src.exists, f'stat {zname}'):
        sys.exit(f'MISSING {src}\nBuild it on the laptop with:\n'
                 f'  venv_train/bin/python scripts/build_probe_colab_bundle.py'
                 f'\nthen upload the zips to {DRIVE}/')
WORK.mkdir(parents=True, exist_ok=True)
for name, zname in BUNDLES.items():
    marker = WORK / f'.restored_{name}'
    if marker.exists():
        print(f'  {zname}: already restored')
        continue
    print(f'  unzipping {zname} ...', flush=True)
    drive_retry(lambda z=DRIVE / zname: subprocess.run(
        ['unzip', '-q', '-o', str(z), '-d', str(WORK)], check=True),
        f'unzip {zname}')
    marker.write_text('ok')

import torch                                        # noqa: E402
if not torch.cuda.is_available():
    sys.exit('No GPU on this runtime. Runtime > Change runtime type > GPU. '
             'On CPU this job takes weeks, not hours.')
print(f'  GPU: {torch.cuda.get_device_name(0)}   torch {torch.__version__}')

step('2/6 Install ASR deps')
try:
    import whisper                                  # noqa: F401,E402
    import demucs                                   # noqa: F401,E402
    print('  whisper + demucs already present')
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q',
                    'openai-whisper', 'demucs', 'librosa', 'soundfile'],
                   check=True)
    import whisper                                  # noqa: F401,E402
    import demucs                                   # noqa: F401,E402
RUN_LOG['versions'] = {'torch': torch.__version__,
                       'whisper': getattr(whisper, '__version__', '?'),
                       'demucs': getattr(demucs, '__version__', '?')}

sys.path.insert(0, str(WORK))
sys.path.insert(0, str(WORK / 'scripts'))
import identify_clip as ic                          # noqa: E402

spec = importlib.util.spec_from_file_location(
    'build_asr_cache_v2', WORK / 'scripts' / 'build_asr_cache_v2.py')
bac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bac)
print(f'  asr_config_id: {ic.asr_config_id()}')
print(f'  cache file   : {ic.CACHE2}')
RUN_LOG['asr_config_id'] = ic.asr_config_id()

# ------------------------------------------------- 3. verify before spending
step('3/6 Verify every window against its sidecar (before any GPU is spent)')
# Filenames are not identity. If the audio here is not the audio the sidecars
# describe, the cache binds transcripts to the wrong windows and — on the
# negative arm — to the wrong ear labels. That is the defect that killed the v1
# negative arm, and it is cheap to rule out. Bad audio must stop the run here,
# not surface as a strange number in three days.
todo: dict[str, list[Path]] = {}
for arm, (rel_dir, rel_side) in ARMS.items():
    audio_dir, side_path = WORK / rel_dir, WORK / rel_side
    side = json.loads(side_path.read_text())
    windows = side['windows']
    bad, absent, files = [], [], []
    for stem, meta in sorted(windows.items()):
        wav = audio_dir / f'{stem}.wav'
        if not wav.exists():
            absent.append(stem)
            continue
        if meta.get('audio_sha256') and sha256_file(wav) != meta['audio_sha256']:
            bad.append(stem)
            continue
        # Every sidecar window is transcribed, including the 9 in-catalog
        # negatives that feed no readout: the validity gate wants a bijection,
        # and a cheaper run is an invalid run.
        files.append(wav)
    if absent or bad:
        sys.exit(f'{arm}: {len(absent)} windows missing, {len(bad)} do not '
                 f'match their stamped audio_sha256 (e.g. '
                 f'{(absent + bad)[:3]}). Re-upload the bundle; do not run.')
    todo[arm] = files
    print(f'  {arm:<10} {len(windows)} windows verified, {len(files)} to '
          f'transcribe')
RUN_LOG['windows'] = {a: len(f) for a, f in todo.items()}

# ------------------------------------------------- 4. transcribe, resumably
step('4/6 Build the v2 ASR cache (resumable; checkpointed to Drive)')
cache_local, cache_drive = ic.CACHE2, OUT / 'asr_cache_v2.json'
if drive_retry(cache_drive.exists, 'stat cache') and not cache_local.exists():
    cache_local.parent.mkdir(parents=True, exist_ok=True)
    drive_retry(lambda: shutil.copy(cache_drive, cache_local), 'restore cache')
    print(f'  restored checkpoint from Drive '
          f'({cache_local.stat().st_size / 1e6:.0f} MB)')

if DEMUCS_DEVICE != 'cpu':
    import demucs.apply as _da
    _orig_apply = _da.apply_model

    def _apply_on_gpu(model, mix, **kw):
        kw['device'] = DEMUCS_DEVICE
        try:
            model.to(DEMUCS_DEVICE)
        except Exception:
            pass
        return _orig_apply(model, mix, **kw)

    _da.apply_model = _apply_on_gpu
    print(f'  Demucs patched to {DEMUCS_DEVICE} (recorded as a deviation in '
          f'run_log.json)')


def pending(files):
    """Windows with no cache entry yet — recomputed every pass, so a resumed
    run never re-transcribes and never skips a gap."""
    cache = ic.load_cache_v2()
    return [p for p in files
            if ic.cache2_key(ic.audio_sha256(p)) not in cache['entries']]


stage = Path('/content/_chunk')
t_run = time.time()
for arm, files in todo.items():
    left = pending(files)
    print(f'\n{arm}: {len(files) - len(left)}/{len(files)} already cached, '
          f'{len(left)} to go', flush=True)
    for i in range(0, len(left), CHUNK):
        batch = left[i:i + CHUNK]
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        for p in batch:
            os.symlink(p, stage / p.name)     # hashes follow the symlink
        t0 = time.time()
        bac.build(stage)                      # the registered cache builder
        drive_retry(lambda: shutil.copy(cache_local, cache_drive),
                    'checkpoint cache')
        dt = time.time() - t0
        done = i + len(batch)
        rate = dt / len(batch)
        print(f'  [{arm} {done}/{len(left)}] chunk {dt / 60:.1f} min '
              f'({rate:.0f}s/window)  ~{rate * (len(left) - done) / 3600:.1f} h '
              f'left in this arm', flush=True)
        RUN_LOG['chunks'].append({'arm': arm, 'n': len(batch),
                                  'seconds': round(dt, 1)})
    still = pending(files)
    if still:
        sys.exit(f'{arm}: {len(still)} windows still uncached after the loop '
                 f'(e.g. {[p.name for p in still[:3]]}). Something failed '
                 f'silently — read the log above before re-running.')
    print(f'{arm}: fully cached', flush=True)
RUN_LOG['transcribe_seconds'] = round(time.time() - t_run, 1)

# ------------------------------------------------- 5. inference, cache-only
step('5/6 Run identify_clip over both arms (read-only; must not transcribe)')
env = {**os.environ, 'CARNATIFY_ASR_BACKEND': 'whisper'}
results_paths = {}
for arm, out_name in (('anchored', 'probe_results.json'),
                      ('negatives', 'negative_results.json')):
    dest = OUT / out_name
    cmd = [sys.executable, '-u', 'identify_clip.py', ARMS[arm][0],
           '--json', '--no-raga', '--cache-v2']
    print(f"\n$ CARNATIFY_ASR_BACKEND=whisper {' '.join(cmd)}", flush=True)
    p = subprocess.run(cmd, cwd=WORK, env=env, capture_output=True, text=True)
    print(p.stderr[-2000:], flush=True)
    if p.returncode != 0:
        sys.exit(f'identify_clip failed on {arm} (rc={p.returncode})')
    rows = json.loads(p.stdout)
    misses = [r.get('file') for r in rows if r.get('cache_v2') == 'MISS']
    if misses:
        sys.exit(f'{len(misses)} cache MISSes on {arm} (e.g. {misses[:3]}). '
                 f'A SCORE with misses is invalid — re-run step 4.')
    drive_retry(lambda d=dest, r=rows: d.write_text(json.dumps(r, indent=1)),
                f'write {out_name}')
    results_paths[arm] = dest
    print(f'  {arm}: {len(rows)} rows, 0 cache misses -> {dest}', flush=True)
    RUN_LOG.setdefault('results', {})[arm] = {'rows': len(rows), 'misses': 0}

# ------------------------------------------------- 6. one artifact to hand back
step('6/6 Hand-back bundle')
RUN_LOG['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S')
RUN_LOG['demucs_device_used'] = DEMUCS_DEVICE
drive_retry(lambda: (OUT / 'run_log.json').write_text(
    json.dumps(RUN_LOG, indent=1)), 'write run_log')

handback = OUT / 'probe_handback.zip'
with zipfile.ZipFile(handback, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
    for p in (cache_local, OUT / 'probe_results.json',
              OUT / 'negative_results.json', OUT / 'run_log.json'):
        z.write(p, p.name)
print(f'  {handback}  ({handback.stat().st_size / 1e6:.0f} MB)')

print(f"""
Everything landed in {OUT}:
  probe_results.json     -> scorer's --results
  negative_results.json  -> scorer's --negative-results
  asr_cache_v2.json      -> the transcripts both were read from
  run_log.json           -> devices, versions, timings, deviations
  probe_handback.zip     -> all four in one download

Back on the laptop, from the repo root:

  unzip -o ~/Downloads/probe_handback.zip -d /tmp/probe_handback
  venv_train/bin/python scripts/merge_asr_cache_v2.py \\
      /tmp/probe_handback/asr_cache_v2.json
  venv_train/bin/python scripts/duration_probe_score.py \\
      --results /tmp/probe_handback/probe_results.json \\
      --truth data/duration_probe/truth_anchored.json \\
      --negative-results /tmp/probe_handback/negative_results.json \\
      --negative-truth data/duration_probe/truth_negatives.json

Quote the scorer's output verbatim into AGENT_LOG.md, with run_log.json's
demucs_device_used beside it. Nothing here decides anything: the scorer applies
the frozen rule, and a duration-probe pass is not wild-phone readiness.
""")
