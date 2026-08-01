"""Domain decomposition, stage 2 — build one degradation cell.

One shard per cell under `data/raga_domain/cell_<name>.npz` (gitignored).
Resumable: a shard that already exists is skipped.

Per window (518 of them, one per tier track at the duration curve's own seeded
offset-0 60 s position), per `data/raga_domain/PREREGISTRATION.md` §3:

  1. load 60.0 s of source audio at 22050 Hz mono — `augment_wild.SR`, the rate
     every registered severity is defined at;
  2. degrade by calling `augment_wild`'s own functions, IMPORTED, not copied and
     not modified, in `augment_chain`'s order;
  3. resample to 44100 Hz — the rate the melodia cache was built at;
  4. tonic: `TonicIndianArtMusic()` on that same degraded 60 s window;
  5. melody: `PredominantPitchMelodia(frameSize=2048, hopSize=128)` on
     `EqualLoudness()` of it — `extract_melodia_full.py`'s parameters verbatim,
     because the training features come from that cache;
  6. feature: voiced filter, then the frozen multi-tau TDMS of
     `1200*log2(v/tonic)`.

`clean` runs 1, 3, 4, 5, 6 — the same 22050 -> 44100 round trip, so the only
difference between `clean` and a degraded cell is the degradation.

**Seeding.** Each component draws from its own dedicated stream,
`random.Random(f"raga_domain|{component}|{stem}")`, so the `phone` parameters
for a track are bit-identical in `phone`, in `field_all` and in `all`, and no
component's draw can be displaced by another's presence or absence.

**Trap 2 is inherited unrepaired**: `tdms()` below is verbatim from
`scripts/raga_duration_windows.py`, itself verbatim from
`scripts/raga_audit_levels.py`. Per-window voicing density is recorded so the
size of the confound can be reported per cell.

The voiced contour is stored alongside the feature so the registered 2x2
(clean/degraded contour x clean/estimated tonic) is a TDMS recomputation with no
new audio work.

macOS + essentia + Pool needs **fork**, not spawn (`HANDOFF_CLIP_ID.md` §5).

Read-only. Nothing under `models/` is written; `augment_wild.py` is not touched.

Usage: venv_train/bin/python scripts/raga_domain_cells.py --cells clean,phone,...
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import random
import sys
import time
from pathlib import Path

# librosa's audioread fallback pulls in macOS ObjC audio frameworks for the mp3s
# libsndfile cannot open. Once the ObjC runtime is initialised in the parent,
# every fork() child aborts with "+[NSNumber initialize] may have been in
# progress in another thread when fork() was called". The Pool then hangs
# forever on imap. Must be set before any framework loads.
os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')

import numpy as np
from scipy.ndimage import gaussian_filter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# `import essentia.standard` instantiates and configures every registered
# algorithm, which costs minutes. Doing it lazily inside a forked worker makes
# all N workers pay it simultaneously and the run appears to hang; doing it here,
# in the PARENT, means the children inherit the loaded module for free. It is
# guarded because scripts/raga_domain_score.py imports this module from `venv`
# (py3.14), which has sklearn but no essentia.
try:
    import essentia.standard as _es
    import librosa as _lb
    import augment_wild as _AW           # IMPORTED, never modified, never copied
except Exception:                              # pragma: no cover - scorer path
    _es = _lb = _AW = None

OUT_DIR = ROOT / 'data' / 'raga_domain'
DUR_DIR = ROOT / 'data' / 'raga_duration'
MEL_DIR = ROOT / 'data' / 'raga_v2_cache' / 'melodia_full'

SR_AUG = 22050            # augment_wild.SR — the rate the severities are defined at
SR_MEL = 44100            # extract_melodia_full.py's rate
MEL_HOP_S = 128 / 44100
TAUS = (0.1, 0.15, 0.25)
NB = 40
SIGMA = 1.0
ALPHA = 0.75
MIN_VOICED = 500          # the frozen harness's own guard, reused verbatim
TONIC_MIN_HZ, TONIC_MAX_HZ = 80.0, 400.0     # identify_clip.py's own range
TONIC_FALLBACK = 146.83                      # identify_clip.py's own default
FFMPEG = '/opt/homebrew/bin/ffmpeg'          # decode fallback for damaged mp3s

# cell -> components in augment_chain order. Registered in PREREGISTRATION.md §3.
CELLS = {
    'cached':         None,                  # cached contour, reference tonic
    'clean':          [],                    # re-run melodia, estimated tonic
    # `clean_reftonic` (prereg §2) is NOT a separate audio pass: it is exactly
    # the clean contour re-normalised by the reference tonic, i.e. the `cd_tc`
    # arm of the `clean` cell, and the scorer reads it from there. Building it
    # as its own cell would re-run melodia on identical audio for no gain.
    'noise':          ['noise'],
    'reverb':         ['reverb'],
    'phone':          ['phone'],
    'field_all':      ['reverb', 'noise', 'phone'],
    'pitch':          ['pitch'],
    'stretch':        ['stretch'],
    'all':            ['pitch', 'stretch', 'reverb', 'noise', 'phone', 'agc'],
    'field_all_demucs': ['reverb', 'noise', 'phone'],   # registered tertiary
}
REF_TONIC_CELLS = {'cached', 'clean_reftonic'}


# --- verbatim from scripts/raga_duration_windows.py (itself verbatim from the
# --- archived harness). Do not modify: Trap 2 lives in here on purpose.
def tdms(v, hop_s, tau_s, nb, sigma, alpha):
    b = np.floor(np.mod(v, 1200.0) / (1200.0 / nb)).astype(int) % nb
    tau = max(1, int(round(tau_s / hop_s)))
    if b.size <= tau: return None
    M = np.zeros((nb, nb))
    np.add.at(M, (b[:-tau], b[tau:]), 1.0)
    M = gaussian_filter(M, sigma=sigma, mode='wrap')
    M = M ** alpha
    s = M.sum()
    if s <= 0: return None
    return (M / s).ravel()
# --- end verbatim -----------------------------------------------------------


def tdms_multi(cents, hop_s=MEL_HOP_S):
    parts = []
    for tau_s in TAUS:
        f = tdms(cents, hop_s, tau_s, NB, SIGMA, ALPHA)
        if f is None:
            return None
        parts.append(f)
    return np.concatenate(parts)


def feature_from_voiced(voiced, tonic, hop_s=MEL_HOP_S):
    """Voiced f0 in Hz + a tonic -> the frozen multi-tau TDMS vector."""
    if voiced.size == 0 or not np.isfinite(tonic) or tonic <= 0:
        return None
    return tdms_multi(1200.0 * np.log2(np.asarray(voiced, np.float64) / tonic), hop_s)


# ------------------------------------------------------------------ degrade --
def degrade(y, components, stem):
    """Apply `components` to a 22050 Hz mono signal using augment_wild's own
    functions. One dedicated RNG stream per (component, track) so a component's
    parameters are identical in every cell that contains it."""
    AW = _AW
    params = {}
    for comp in components:
        rng = random.Random(f'raga_domain|{comp}|{stem}')
        if comp == 'pitch':
            y, s = AW.pitch_shift(y, rng)
            params['pitch_semitones'] = round(float(s), 6)
        elif comp == 'stretch':
            y, r = AW.time_stretch(y, rng)
            params['stretch'] = round(float(r), 6)
        elif comp == 'reverb':
            y, rt = AW.room_reverb(y, rng)
            params['reverb_rt'] = round(float(rt), 4)
        elif comp == 'noise':
            y, snr = AW.add_noise(y, rng)
            params['snr_db'] = round(float(snr), 3)
        elif comp == 'phone':
            y, ph = AW.phone_mic(y, rng)
            params['phone'] = ph
        elif comp == 'agc':
            y, g = AW.agc_clip(y, rng)
            params['agc_gain'] = round(float(g), 4)
        else:
            raise ValueError(comp)
    # augment_chain's two output rules, applied in EVERY cell including clean so
    # they are not a difference between cells.
    if len(y) > 60 * SR_AUG:
        y = y[: 60 * SR_AUG]
    peak = float(np.max(np.abs(y))) + 1e-9
    if peak > 1.0:
        y = y / peak
    return np.asarray(y, dtype=np.float32), params


def demucs_vocals(y, stem, tmpdir):
    """Registered tertiary: htdemucs two-stem vocal separation before melodia,
    matching backend/main.py's production call."""
    import subprocess
    import soundfile as sf
    d = Path(tmpdir) / stem
    d.mkdir(parents=True, exist_ok=True)
    wav = d / 'in.wav'
    sf.write(wav, y, SR_AUG)
    r = subprocess.run([sys.executable, '-m', 'demucs', '--two-stems=vocals',
                        '-n', 'htdemucs', '-o', str(d), str(wav)],
                       capture_output=True, text=True, timeout=900)
    voc = d / 'htdemucs' / 'in' / 'vocals.wav'
    if r.returncode != 0 or not voc.exists():
        raise RuntimeError(f'demucs failed rc={r.returncode}: {r.stderr[-300:]}')
    out, _ = _lb.load(str(voc), sr=SR_AUG, mono=True)
    for p in sorted(d.rglob('*'), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    d.rmdir()
    return out.astype(np.float32)


# --------------------------------------------------------------- one window --
_ENGINES = {}


def engines():
    """Built per worker, but only AFTER the parent has already imported
    essentia.standard, so this is three cheap constructor calls, not a
    module import."""
    if not _ENGINES:
        _ENGINES['mel'] = _es.PredominantPitchMelodia(frameSize=2048, hopSize=128)
        _ENGINES['eq'] = _es.EqualLoudness()
        _ENGINES['tonic'] = _es.TonicIndianArtMusic()
    # **Not optional.** `TonicIndianArtMusic` and `PredominantPitchMelodia` are
    # composite algorithms wrapping a streaming network, and they carry state
    # across compute() calls: without this reset the tonic estimator returns a
    # correct value on the FIRST window of a worker and THROWS on every window
    # after it. Verified: three identical calls give 147.93 / None / None
    # without reset and 147.93 / 147.93 / 147.93 with it. Silently, that bug
    # would have made every degraded cell look like a total tonic failure.
    for a in _ENGINES.values():
        a.reset()
    return _ENGINES


def cached_contour(rec):
    """The inherited contour: melodia cache for archive, Saraga annotation for
    Saraga, sliced on the time axis exactly as raga_duration_windows does."""
    if rec['src'] == 'archive_v3':
        f = np.load(MEL_DIR / f"{rec['stem']}.npy")
    else:
        f = _SARAGA_PITCH[rec['tid'].replace('saraga__', '')]
    f = np.asarray(f, dtype=np.float64)
    return f[rec['win_start_frame']:rec['win_stop_frame']]


_SARAGA_PITCH = {}


def load_window(rec):
    """The registered 60 s window, decoded at 22050 Hz.

    Two corpus defects force a fallback and an outcome that is NOT a finding:

    * some archive mp3s are damaged (the benign `Illegal Audio-MPEG-Header ...
      resync` warnings in `HANDOFF_SESSION_0719.md` §4), libsndfile refuses
      them, and librosa's audioread fallback can return ZERO samples when asked
      to seek — so a failed seek is retried by decoding the whole file and
      slicing;
    * at least one Saraga track's audio on disk is far shorter than its pitch
      annotation, so the registered window does not exist in the audio at all.

    Returns (audio, None) or (None, 'audio_unavailable'). The window must be the
    full registered length: a partial window would be a duration cell in
    disguise. `audio_unavailable` does not depend on the degradation, so it
    removes the same tracks from every cell and the cells stay paired."""
    need = int(round(rec['win_s'] * SR_AUG))
    y, _ = _lb.load(rec['audio'], sr=SR_AUG, mono=True,
                    offset=rec['win_start_s'], duration=rec['win_s'])
    if y.size >= 0.98 * need:
        return y, None
    full, _ = _lb.load(rec['audio'], sr=SR_AUG, mono=True)
    a = int(round(rec['win_start_s'] * SR_AUG))
    yy = full[a:a + need]
    if yy.size >= 0.98 * need:
        return yy, None
    # Last resort: ffmpeg. `augment_wild.py:21` says "No ffmpeg on this machine";
    # that is stale — ffmpeg 8.1.2 is at /opt/homebrew/bin/ffmpeg — and libavcodec
    # decodes the damaged archive mp3s that libmpg123 gives up on midway. This is
    # a DECODE path only; no registered severity is touched by it.
    import subprocess
    r = subprocess.run([FFMPEG, '-v', 'error', '-ss', f"{rec['win_start_s']:.6f}",
                        '-t', f"{rec['win_s']:.6f}", '-i', rec['audio'],
                        '-f', 'f32le', '-ac', '1', '-ar', str(SR_AUG), '-'],
                       capture_output=True)
    z = np.frombuffer(r.stdout, dtype=np.float32)
    return (z.copy(), None) if z.size >= 0.98 * need else (None, 'audio_unavailable')


def run_window(job):
    rec, cell, tmpdir = job
    comps = CELLS[cell]
    stem = rec['stem']
    row = dict(stem=stem, tid=rec['tid'], src=rec['src'], raga=rec['raga'],
               group_c=rec['group_c'], cell=cell, tonic_ref=rec['tonic_ref'],
               params={}, outcome='scored', tonic_fail=False)
    t0 = time.time()
    try:
        if comps is None:                      # `cached`
            seg = cached_contour(rec)
            hop = rec['hop']
            row['real_s'] = float(seg.size * hop)
            tonic_est = None
        else:
            y, bad = load_window(rec)
            if bad:
                row['outcome'] = bad
                return row, None, None
            y, row['params'] = degrade(y, comps, stem)
            if cell.endswith('_demucs'):
                y = demucs_vocals(y, stem, tmpdir)
            row['real_s'] = float(y.size / SR_AUG)
            y44 = _lb.resample(y, orig_sr=SR_AUG, target_sr=SR_MEL).astype(np.float32)
            E = engines()
            try:
                t = float(E['tonic'](y44))
            except Exception:
                t = float('nan')
            tonic_est = t if TONIC_MIN_HZ <= t <= TONIC_MAX_HZ else None
            if tonic_est is None:
                row['tonic_fail'] = True
            row['tonic_raw'] = None if not np.isfinite(t) else float(t)
            seg, _ = E['mel'](E['eq'](y44))
            seg = np.asarray(seg, dtype=np.float64)
            hop = MEL_HOP_S
        row['hop'] = float(hop)
        row['tonic_est'] = None if tonic_est is None else float(tonic_est)
        row['n_raw'] = int(seg.size)
        v = seg[(seg > 0) & np.isfinite(seg)]
        row['n_voiced'] = int(v.size)
        row['density'] = float(v.size / max(1, seg.size))

        if cell in REF_TONIC_CELLS:
            tonic_used = rec['tonic_ref']
        elif tonic_est is not None:
            tonic_used = tonic_est
        else:
            tonic_used = TONIC_FALLBACK
        row['tonic_used'] = float(tonic_used)

        # the registered four-way taxonomy, mutually exclusive, never summed
        if v.size == 0:
            row['outcome'] = 'no_contour'
            return row, None, None
        if v.size < MIN_VOICED:
            row['outcome'] = 'min_voiced'
            return row, None, None
        feat = feature_from_voiced(v, tonic_used, hop)
        if feat is None:
            row['outcome'] = 'tdms_none'
            return row, None, None
        row['outcome'] = 'scored'
        row['secs'] = round(time.time() - t0, 2)
        return row, np.asarray(feat, np.float32), np.asarray(v, np.float32)
    except Exception as e:
        row['outcome'] = 'error'
        row['error'] = f'{type(e).__name__}: {e}'
        return row, None, None


def build_cell(recs, cell, workers, tmpdir):
    out = OUT_DIR / f'cell_{cell}.npz'
    if out.exists():
        print(f'-- {cell}: shard exists, skipping', flush=True)
        return
    jobs = [(r, cell, tmpdir) for r in recs]
    t0 = time.time()
    results = []
    if workers <= 1:
        for n, j in enumerate(jobs, 1):
            results.append(run_window(j))
            if n % 50 == 0:
                print(f'   {cell}: {n}/{len(jobs)}  {time.time() - t0:.0f}s', flush=True)
    else:
        ctx = mp.get_context('fork')      # essentia + Pool on macOS needs fork
        with ctx.Pool(workers) as pool:
            for n, r in enumerate(pool.imap(run_window, jobs), 1):
                results.append(r)
                if n % 50 == 0:
                    print(f'   {cell}: {n}/{len(jobs)}  {time.time() - t0:.0f}s', flush=True)

    feats, cont, coff, meta = [], [], [0], []
    for row, f, v in results:
        if f is not None:
            row['findex'] = len(feats)
            feats.append(f)
            cont.append(v)
            coff.append(coff[-1] + v.size)
        else:
            row['findex'] = -1
        meta.append(row)
    X = np.stack(feats) if feats else np.zeros((0, NB * NB * len(TAUS)), np.float32)
    C = np.concatenate(cont) if cont else np.zeros(0, np.float32)
    np.savez_compressed(out, X=X, contour=C, contour_off=np.array(coff, np.int64),
                        meta=np.array(json.dumps(meta, ensure_ascii=False)))
    tally = {}
    for m in meta:
        tally[m['outcome']] = tally.get(m['outcome'], 0) + 1
    tf = sum(1 for m in meta if m.get('tonic_fail'))
    print(f'   -> {out.name}: {tally}, tonic_fail {tf}, '
          f'{X.nbytes / 1e6:.0f} MB feats, {time.time() - t0:.0f}s', flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cells', default='cached,clean,phone,noise,'
                                       'reverb,field_all,all,pitch,stretch')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--tmpdir', default=str(OUT_DIR / 'tmp'))
    args = ap.parse_args()

    proto = json.loads((OUT_DIR / 'protocol.json').read_text())
    recs = proto['tracks']
    print(f"{len(recs)} windows, {proto['level_c_groups']} level-(c) groups, "
          f"offset index {proto['offset_index']}, {proto['window_s']}s", flush=True)

    names = [c.strip() for c in args.cells.split(',') if c.strip()]
    if 'cached' in names and any(r['src'] == 'saraga_v3' for r in recs):
        import mirdata
        saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
        for tid in saraga.track_ids:
            t = saraga.track(tid)
            p = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
            if p is not None:
                _SARAGA_PITCH[tid] = p.frequencies
        print(f'  saraga annotation table: {len(_SARAGA_PITCH)} tracks', flush=True)

    Path(args.tmpdir).mkdir(parents=True, exist_ok=True)
    for cell in names:
        if cell not in CELLS:
            raise SystemExit(f'unknown cell {cell}; known: {sorted(CELLS)}')
        w = 1 if cell.endswith('_demucs') else args.workers
        print(f'== building cell {cell}  ({CELLS[cell]})  workers={w}', flush=True)
        build_cell(recs, cell, w, args.tmpdir)


if __name__ == '__main__':
    main()
