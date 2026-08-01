"""Wild raga measurement, stage 2 — features for every (clip, window, arm).

Per `data/raga_wild/PREREGISTRATION.md` §2-§5. One row per (clip, window, arm);
resumable at that granularity — a completed row is loaded from
`data/raga_wild/rows/<key>.npz` and never recomputed, so a session limit costs
at most the row in flight.

For one (clip, window):

  1. decode the window natively at **44100 Hz** mono, the rate the melodia cache
     was built at (prereg §4 — the domain job's 22050 round trip existed only
     because `augment_wild.SR` is 22050 and there is no augmentation here);
  2. **tonic**: `TonicIndianArtMusic()` on that MIX window, accepted in
     [80, 400] Hz else `identify_clip.py`'s own 146.83 fallback. Estimated on
     the mix in BOTH arms because `raga_v2_pipeline.py:56` records that the
     drone estimator must run before separation. The tonic on the separated
     vocal is recorded as a diagnostic and used for nothing;
  3. **`mix` arm**: `PredominantPitchMelodia(frameSize=2048, hopSize=128)` on
     `EqualLoudness()` — `extract_melodia_full.py` verbatim — then the frozen
     multi-tau TDMS;
  4. **`mix_voiceband` arm** (non-gating diagnostic): the same, with
     `identify_clip.py`'s wild-clip constraint `minFrequency=90,
     maxFrequency=900, voicingTolerance=0.6`;
  5. **`demucs` arm**: `htdemucs --two-stems=vocals` on the window, then 3;
  6. **histogram half of the fused model**: `librosa.pyin` at 22050 Hz on that
     same htdemucs vocal, then `carnatify.ml.raga_features.extract_features`
     with the mix tonic. This is `raga_v2_pipeline.py`'s production feature and
     it is Demucs-derived in BOTH arms by construction (prereg §4).

Trap 2 is inherited unrepaired: `tdms()` is verbatim from
`scripts/raga_domain_cells.py`, itself verbatim from
`scripts/raga_duration_windows.py` and the archived harness. Per-window voicing
density is recorded so the confound can be reported.

macOS + essentia needs **fork**, not spawn (`HANDOFF_CLIP_ID.md` §5). Demucs
times out under CPU contention (same section), so it runs sequentially in the
parent and no worker pool is used.

Read-only. Nothing under `models/` is written; no model is loaded here.

Usage: venv_train/bin/python scripts/raga_wild_features.py [--only <substr>]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# librosa's audioread fallback pulls in macOS ObjC audio frameworks; once the
# ObjC runtime is initialised any fork() child aborts. Must precede any import.
os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')

import numpy as np
from scipy.ndimage import gaussian_filter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import essentia.standard as _es          # noqa: E402
import librosa as _lb                    # noqa: E402
import soundfile as _sf                  # noqa: E402
from carnatify.ml.raga_features import extract_features  # noqa: E402

OUT_DIR = ROOT / 'data' / 'raga_wild'
ROW_DIR = OUT_DIR / 'rows'
CLIPS_DIR = Path.home() / 'sung_tests'
FFMPEG = '/opt/homebrew/bin/ffmpeg'

SR_MEL = 44100                # extract_melodia_full.py's rate
SR_PYIN = 22050               # raga_v2_pipeline.TARGET_SR
MEL_HOP_S = 128 / 44100
TAUS = (0.1, 0.15, 0.25)
NB = 40
SIGMA = 1.0
ALPHA = 0.75
MIN_VOICED = 500              # the frozen harness's own guard, verbatim
TONIC_MIN_HZ, TONIC_MAX_HZ = 80.0, 400.0     # identify_clip.py's own range
TONIC_FALLBACK = 146.83                      # identify_clip.py's own default
PYIN_FMIN, PYIN_FMAX = 60, 1000              # raga_v2_pipeline.py's own range

ARMS = ('mix', 'mix_voiceband', 'demucs')


# --- verbatim from scripts/raga_domain_cells.py (itself verbatim from the
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
    if voiced.size == 0 or not np.isfinite(tonic) or tonic <= 0:
        return None
    return tdms_multi(1200.0 * np.log2(np.asarray(voiced, np.float64) / tonic), hop_s)


# ------------------------------------------------------------------- engines --
_E = {}


def engines():
    if not _E:
        _E['mel'] = _es.PredominantPitchMelodia(frameSize=2048, hopSize=128)
        _E['mel_vb'] = _es.PredominantPitchMelodia(
            frameSize=2048, hopSize=128,
            minFrequency=90, maxFrequency=900, voicingTolerance=0.6)
        _E['eq'] = _es.EqualLoudness()
        _E['tonic'] = _es.TonicIndianArtMusic()
    # **Not optional.** These are composite algorithms wrapping a streaming
    # network and they carry state across compute() calls: without the reset the
    # tonic estimator answers on the FIRST call and throws on every one after it
    # (`scripts/raga_domain_cells.py:engines`). Silently, that would look like a
    # total tonic failure on every clip but the first.
    for a in _E.values():
        a.reset()
    return _E


def load_window(path: Path, start_s: float, dur_s: float, sr: int) -> np.ndarray | None:
    """Decode [start_s, start_s+dur_s) at `sr`, mono. librosa first; ffmpeg is a
    DECODE fallback for the damaged mp3s libmpg123 gives up on midway."""
    need = int(round(dur_s * sr))
    try:
        y, _ = _lb.load(str(path), sr=sr, mono=True, offset=start_s, duration=dur_s)
        if y.size >= 0.98 * need:
            return y.astype(np.float32)
    except Exception:
        pass
    r = subprocess.run([FFMPEG, '-v', 'error', '-ss', f'{start_s:.6f}',
                        '-t', f'{dur_s:.6f}', '-i', str(path),
                        '-f', 'f32le', '-ac', '1', '-ar', str(sr), '-'],
                       capture_output=True)
    z = np.frombuffer(r.stdout, dtype=np.float32)
    return z.copy() if z.size >= 0.98 * need else None


def demucs_vocals(y44: np.ndarray, key: str, tmpdir: Path) -> np.ndarray:
    """htdemucs two-stem vocal separation, matching backend/main.py's production
    call (`raga_v2_pipeline._separate_vocals`). Written as real 2-channel audio:
    Demucs's own mono->stereo upmix aliases memory and crashes torch>=2."""
    d = tmpdir / key
    d.mkdir(parents=True, exist_ok=True)
    wav = d / 'in.wav'
    _sf.write(wav, np.repeat(y44[:, None], 2, axis=1), SR_MEL)
    r = subprocess.run([sys.executable, '-m', 'demucs', '--two-stems=vocals',
                        '-n', 'htdemucs', '-o', str(d), str(wav)],
                       capture_output=True, text=True, timeout=1800)
    voc = d / 'htdemucs' / 'in' / 'vocals.wav'
    if r.returncode != 0 or not voc.exists():
        raise RuntimeError(f'demucs rc={r.returncode}: {r.stderr[-300:]}')
    out, _ = _lb.load(str(voc), sr=SR_MEL, mono=True)
    for p in sorted(d.rglob('*'), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    d.rmdir()
    return out.astype(np.float32)


def melodia_tdms(y44: np.ndarray, tonic: float, engine_key: str) -> tuple[dict, np.ndarray | None]:
    """One melodia pass -> the registered outcome taxonomy + the TDMS vector."""
    E = engines()
    seg, _ = E[engine_key](E['eq'](y44))
    seg = np.asarray(seg, dtype=np.float64)
    v = seg[(seg > 0) & np.isfinite(seg)]
    row = dict(n_raw=int(seg.size), n_voiced=int(v.size),
               density=float(v.size / max(1, seg.size)),
               voiced_s=float(v.size * MEL_HOP_S))
    if v.size == 0:
        row['outcome'] = 'no_contour'
        return row, None
    if v.size < MIN_VOICED:
        row['outcome'] = 'min_voiced'
        return row, None
    feat = feature_from_voiced(v, tonic)
    if feat is None:
        row['outcome'] = 'tdms_none'
        return row, None
    row['outcome'] = 'scored'
    return row, np.asarray(feat, np.float32)


def run_window(clip: dict, win: dict, tmpdir: Path) -> dict:
    """Everything for one (clip, window): the three arms and the hist feature."""
    path = CLIPS_DIR / clip['file']
    key = f"{clip['stem_key']}__{win['kind']}"
    out = ROW_DIR / f'{key}.npz'
    if out.exists():
        return dict(key=key, cached=True)

    rec = dict(key=key, file=clip['file'], raga_canonical=clip['raga_canonical'],
               window=win['kind'], start_s=win['start_s'], dur_s=win['dur_s'],
               arms={}, hist=dict(outcome='pending'))
    t0 = time.time()
    feats = {}

    y44 = load_window(path, win['start_s'], win['dur_s'], SR_MEL)
    if y44 is None:
        rec['audio'] = dict(outcome='audio_unavailable')
        for a in ARMS:
            rec['arms'][a] = dict(outcome='audio_unavailable')
        rec['hist'] = dict(outcome='audio_unavailable')
        np.savez_compressed(out, meta=np.array(json.dumps(rec, ensure_ascii=False)))
        return rec
    rec['audio'] = dict(outcome='ok', real_s=float(y44.size / SR_MEL),
                        rms=float(np.sqrt(np.mean(y44.astype(np.float64) ** 2))))

    # --- tonic, on the MIX, once, shared by every arm (prereg §4) -------------
    E = engines()
    try:
        t = float(E['tonic'](y44))
    except Exception:
        t = float('nan')
    ok = np.isfinite(t) and TONIC_MIN_HZ <= t <= TONIC_MAX_HZ
    rec['tonic'] = dict(raw=None if not np.isfinite(t) else float(t),
                        used=float(t) if ok else TONIC_FALLBACK,
                        fallback=bool(not ok))
    tonic = rec['tonic']['used']

    # --- mix arms -------------------------------------------------------------
    for arm, ek in (('mix', 'mel'), ('mix_voiceband', 'mel_vb')):
        r, f = melodia_tdms(y44, tonic, ek)
        rec['arms'][arm] = r
        if f is not None:
            feats[f'tdms_{arm}'] = f

    # --- demucs, once: feeds the demucs TDMS arm AND the histogram half -------
    try:
        yv = demucs_vocals(y44, key, tmpdir)
    except Exception as e:
        rec['arms']['demucs'] = dict(outcome='demucs_fail', error=f'{type(e).__name__}: {e}')
        rec['hist'] = dict(outcome='demucs_fail')
    else:
        r, f = melodia_tdms(yv, tonic, 'mel')
        rec['arms']['demucs'] = r
        if f is not None:
            feats['tdms_demucs'] = f
        try:
            tv = float(E['tonic'](yv))
            rec['tonic']['on_vocal_diagnostic'] = None if not np.isfinite(tv) else float(tv)
        except Exception:
            rec['tonic']['on_vocal_diagnostic'] = None
        # histogram half: pyin on the vocal at 22050, production convention
        y22 = _lb.resample(yv, orig_sr=SR_MEL, target_sr=SR_PYIN)
        f0, voiced_flag, _ = _lb.pyin(y22, fmin=PYIN_FMIN, fmax=PYIN_FMAX, sr=SR_PYIN)
        freqs = f0[voiced_flag].astype(np.float64)
        h = extract_features(freqs, tonic) if freqs.size >= 10 else None
        rec['hist'] = dict(outcome='scored' if h is not None else 'hist_none',
                           n_voiced=int(freqs.size))
        if h is not None:
            feats['hist'] = np.asarray(h, np.float32)

    rec['secs'] = round(time.time() - t0, 1)
    np.savez_compressed(out, meta=np.array(json.dumps(rec, ensure_ascii=False)), **feats)
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None, help='substring filter on the filename')
    ap.add_argument('--tmpdir', default=str(OUT_DIR / 'tmp'))
    args = ap.parse_args()

    proto = json.loads((OUT_DIR / 'protocol.json').read_text())
    frozen = json.loads((OUT_DIR / 'FROZEN_CLIPS.json').read_text())
    if proto['n_hash_bad']:
        raise SystemExit('BLOCKER: hash gate failed; refusing to score')

    clips = []
    for c in frozen['clips']:
        stem_key = ''.join(ch if ch.isalnum() else '_' for ch in Path(c['file']).stem)
        clips.append(dict(file=c['file'], raga_canonical=c['raga_canonical'],
                          stem_key=stem_key))
    if args.only:
        clips = [c for c in clips if args.only.lower() in c['file'].lower()]

    tmpdir = Path(args.tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    ROW_DIR.mkdir(parents=True, exist_ok=True)

    jobs = [(c, w) for c in clips for w in proto['window_plan'][c['file']]]
    print(f'{len(clips)} clips, {len(jobs)} (clip, window) rows, arms {ARMS}', flush=True)
    t0 = time.time()
    for n, (c, w) in enumerate(jobs, 1):
        r = run_window(c, w, tmpdir)
        if r.get('cached'):
            print(f"  [{n:3d}/{len(jobs)}] {r['key']}: cached", flush=True)
            continue
        arms = ' '.join(f"{a}={r['arms'][a]['outcome']}" for a in ARMS)
        print(f"  [{n:3d}/{len(jobs)}] {r['key']}  {w['dur_s']:.1f}s  "
              f"tonic={r.get('tonic', {}).get('used', 0):.1f}"
              f"{'(fallback)' if r.get('tonic', {}).get('fallback') else ''}  "
              f"{arms}  hist={r['hist']['outcome']}  {r.get('secs', 0)}s "
              f"[elapsed {time.time() - t0:.0f}s]", flush=True)
    print(f'done in {time.time() - t0:.0f}s; rows in {ROW_DIR}')


if __name__ == '__main__':
    main()
