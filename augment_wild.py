#!/usr/bin/env python
"""augment_wild.py — zero-cost synthetic wild-clip generator (local, no APIs).

Two outputs, two purposes — do not mix them up:

  --pairs   Training pairs for the CSI/melody embedding channel (CoverHunter/
            ByteCover fine-tune). Positive pair = same composition, different
            rendition where available (68 comps have >=2 renditions), else
            different augmented crops of the same rendition.
            Output: data/synth_train/<comp_id>/<clip>.wav + manifest.jsonl

  --suite   SYNTH robustness suite: augmented clips named <title>__<raga>.wav
            so `identify_clip.py <dir>` runs on them as a stress test.
            Output: data/synth_suite/

PROJECT RULE (do not delete): synthetic clips are same-corpus audio. The
robustness suite is a regression stress-test ONLY. It must never be merged
into ~/sung_tests (frozen wild baseline) and its SCORE block never
green-lights a change. Wild-clip eval is the only scoreboard.

No ffmpeg on this machine: codec damage is simulated with mu-law companding
and 8/16 kHz resample round-trips, not a true opus/AAC re-encode.

Usage (venv_train):
  venv_train/bin/python augment_wild.py --suite 60
  venv_train/bin/python augment_wild.py --pairs 500
  venv_train/bin/python augment_wild.py --suite 60 --pairs 500 --seed 7
"""

import argparse
import collections
import json
import os
import random
import re
import sys
import unicodedata

import numpy as np
import librosa
import soundfile as sf
from scipy import signal

SR = 22050
ROOT = os.path.dirname(os.path.abspath(__file__))
CONCERT_DIR = os.path.join(ROOT, "data", "concert_audio")
SUITE_DIR = os.path.join(ROOT, "data", "synth_suite")
PAIRS_DIR = os.path.join(ROOT, "data", "synth_train")
AUDIO_EXTS = (".mp3", ".m4a", ".wav", ".flac")


# ---------------------------------------------------------------- catalog ---

def collect_groups(root=CONCERT_DIR):
    """Group concert_audio files into (raga, composition) rendition groups.

    Filenames are <title>[_rN].<ext> inside per-raga dirs. Keys are
    NFC-normalized (macOS stores NFD; naive comparisons silently miss).
    """
    groups = collections.defaultdict(list)
    titles = {}
    for raga in sorted(os.listdir(root)):
        d = os.path.join(root, raga)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(AUDIO_EXTS):
                continue
            base = re.sub(r"_r\d+$", "", os.path.splitext(f)[0])
            # casefold so "Deenarakshaka" and "deenarakshaka" group together;
            # keep one display-cased title via the titles map
            key = (
                unicodedata.normalize("NFC", raga),
                unicodedata.normalize("NFC", base).casefold(),
            )
            groups[key].append(os.path.join(d, f))
            titles.setdefault(key, unicodedata.normalize("NFC", base))
    return groups, titles


# ---------------------------------------------------------- augmentations ---

def rand_crop(y, rng, lo=20.0, hi=60.0):
    """Random 20-60 s crop, biased away from the first/last 5% (applause,
    announcements). Structure invariance is what killed the DTW melody path —
    crops must land anywhere, not just at the pallavi."""
    dur = len(y) / SR
    want = rng.uniform(lo, min(hi, max(lo, dur)))
    n = int(want * SR)
    if n >= len(y):
        return y.copy()
    margin = int(0.05 * len(y))
    start = rng.randint(margin, max(margin + 1, len(y) - n - margin))
    return y[start:start + n].copy()


def pitch_shift(y, rng):
    """±6 semitone shruti shift. Tonic estimation is unsolved on wild clips,
    so invariance is trained in, never estimated."""
    steps = rng.uniform(-6.0, 6.0)
    return librosa.effects.pitch_shift(y, sr=SR, n_steps=steps), steps


def time_stretch(y, rng):
    rate = rng.uniform(0.8, 1.25)
    return librosa.effects.time_stretch(y, rate=rate), rate


def add_noise(y, rng):
    """Pink-ish noise at 8-25 dB SNR (crowd rumble stand-in; no crowd stems
    on disk)."""
    snr_db = rng.uniform(8.0, 25.0)
    white = np.asarray(rng_np(rng).standard_normal(len(y)), dtype=np.float32)
    b, a = signal.butter(1, 0.12)          # tilt spectrum toward low freqs
    pink = signal.lfilter(b, a, white).astype(np.float32)
    sig_p = np.mean(y ** 2) + 1e-12
    noise_p = np.mean(pink ** 2) + 1e-12
    pink *= np.sqrt(sig_p / (noise_p * 10 ** (snr_db / 10)))
    return y + pink, snr_db


def phone_mic(y, rng):
    """Phone-capture chain: bandpass + resample round-trip + mu-law
    companding (codec proxy — no ffmpeg for real opus/AAC)."""
    lo = rng.uniform(120, 350)
    hi = rng.uniform(3400, 7500)
    sos = signal.butter(4, [lo, hi], btype="band", fs=SR, output="sos")
    y = signal.sosfilt(sos, y).astype(np.float32)
    low_sr = rng.choice([8000, 11025, 16000])
    y = librosa.resample(y, orig_sr=SR, target_sr=low_sr)
    y = librosa.resample(y, orig_sr=low_sr, target_sr=SR)
    mu = 255.0
    y = np.clip(y, -1, 1)
    y = np.sign(y) * np.log1p(mu * np.abs(y)) / np.log1p(mu)
    y = np.sign(y) * (np.expm1(np.abs(y) * np.log1p(mu))) / mu
    return y.astype(np.float32), {"band": [round(lo), round(hi)], "sr": int(low_sr)}


def room_reverb(y, rng):
    """Cheap synthetic room: exponentially decaying noise IR."""
    rt = rng.uniform(0.15, 0.6)
    n = int(rt * SR)
    ir = np.asarray(rng_np(rng).standard_normal(n), dtype=np.float32)
    ir *= np.exp(-6.0 * np.arange(n) / n)
    ir[0] = 1.0
    wet = signal.fftconvolve(y, ir)[: len(y)].astype(np.float32)
    mix = rng.uniform(0.1, 0.35)
    return (1 - mix) * y + mix * wet / (np.max(np.abs(wet)) + 1e-9), rt


def agc_clip(y, rng):
    """Phone AGC: random gain then soft clip."""
    gain = rng.uniform(0.9, 2.2)
    return np.tanh(y * gain).astype(np.float32), gain


def rng_np(rng):
    return np.random.default_rng(rng.getrandbits(32))


def augment_chain(y, rng, force_pitch=True):
    """Sample an augmentation chain; return (audio, params dict)."""
    params = {}
    y = rand_crop(y, rng)
    params["crop_s"] = round(len(y) / SR, 1)
    if force_pitch or rng.random() < 0.8:
        y, params["pitch_semitones"] = pitch_shift(y, rng)
        params["pitch_semitones"] = round(params["pitch_semitones"], 2)
    if rng.random() < 0.7:
        y, params["stretch"] = time_stretch(y, rng)
        params["stretch"] = round(params["stretch"], 3)
    if rng.random() < 0.6:
        y, params["reverb_rt"] = room_reverb(y, rng)
        params["reverb_rt"] = round(params["reverb_rt"], 2)
    if rng.random() < 0.7:
        y, params["snr_db"] = add_noise(y, rng)
        params["snr_db"] = round(params["snr_db"], 1)
    if rng.random() < 0.7:
        y, params["phone"] = phone_mic(y, rng)
    if rng.random() < 0.5:
        y, params["agc_gain"] = agc_clip(y, rng)
        params["agc_gain"] = round(params["agc_gain"], 2)
    if len(y) > 60 * SR:            # slow time-stretch can push a 60 s crop
        y = y[: 60 * SR]            # to ~75 s; keep the 20-60 s clip spec
    peak = np.max(np.abs(y)) + 1e-9
    if peak > 1.0:
        y = y / peak
    return y.astype(np.float32), params


# ---------------------------------------------------------------- drivers ---

def load(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    return y


def slug(s, maxlen=60):
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[^\w\- ]+", "", s).strip().replace(" ", "_")
    return s[:maxlen] or "untitled"


def build_suite(groups, titles, n_clips, rng):
    """SYNTH robustness suite: <title>__<raga>.wav, eval-harness parseable.
    Stress test only — never the scoreboard."""
    os.makedirs(SUITE_DIR, exist_ok=True)
    keys = sorted(groups)
    rng.shuffle(keys)
    manifest = []
    made = 0
    for raga, title in keys:
        if made >= n_clips:
            break
        src = rng.choice(groups[(raga, title)])
        try:
            y = load(src)
        except Exception as e:
            print(f"  skip (load fail): {src}: {e}", file=sys.stderr)
            continue
        if len(y) < 20 * SR:
            continue
        clip, params = augment_chain(y, rng)
        # one '__' only: harness splits on it. Title must not contain '__'.
        # Rāgamālika is a form, not a raga — raga truth NA excludes it from
        # raga denominators (standing project rule).
        raga_truth = "NA" if slug(raga).casefold().startswith(
            ("rāgamālika", "ragamalika")) else slug(raga)
        name = f"{slug(titles[(raga, title)])}__{raga_truth}.wav"
        out = os.path.join(SUITE_DIR, name)
        sf.write(out, clip, SR)
        manifest.append({"file": name, "source": os.path.relpath(src, ROOT),
                         "params": params})
        made += 1
        print(f"  suite {made}/{n_clips}: {name}")
    with open(os.path.join(SUITE_DIR, "synth_manifest.json"), "w") as f:
        json.dump({"note": "SYNTH robustness suite — same-corpus, stress "
                           "test only, never merged into ~/sung_tests",
                   "clips": manifest}, f, ensure_ascii=False, indent=1)
    return made


def build_pairs(groups, titles, n_clips, rng):
    """Embedding training clips. Every clip row carries comp_id; the trainer
    forms positives = same comp_id (cross-rendition where possible) and
    negatives = different comp_id."""
    os.makedirs(PAIRS_DIR, exist_ok=True)
    keys = sorted(groups)
    # favor multi-rendition comps: real cross-artist positives are the
    # scarce, valuable class
    multi = [k for k in keys if len(groups[k]) >= 2]
    single = [k for k in keys if len(groups[k]) == 1]
    rng.shuffle(multi)
    rng.shuffle(single)
    ordered = multi * 3 + single          # oversample multi-rendition comps
    manifest_path = os.path.join(PAIRS_DIR, "manifest.jsonl")
    made = 0
    cache = {}
    with open(manifest_path, "a") as mf:
        for raga, title in ordered:
            if made >= n_clips:
                break
            disp = titles[(raga, title)]
            comp_id = f"{slug(raga)}::{slug(disp)}"
            src = rng.choice(groups[(raga, title)])
            if src not in cache:
                try:
                    cache[src] = load(src)
                except Exception as e:
                    print(f"  skip (load fail): {src}: {e}", file=sys.stderr)
                    cache[src] = None
                if len(cache) > 40:        # keep memory bounded
                    cache.pop(next(iter(cache)))
            y = cache.get(src)
            if y is None or len(y) < 20 * SR:
                continue
            clip, params = augment_chain(y, rng)
            comp_dir = os.path.join(PAIRS_DIR, slug(raga), slug(disp))
            os.makedirs(comp_dir, exist_ok=True)
            name = f"{made:06d}.wav"
            sf.write(os.path.join(comp_dir, name), clip, SR)
            mf.write(json.dumps({
                "clip": os.path.relpath(os.path.join(comp_dir, name), ROOT),
                "comp_id": comp_id,
                "raga": raga,
                "title": disp,
                "source": os.path.relpath(src, ROOT),
                "n_renditions": len(groups[(raga, title)]),
                "params": params,
            }, ensure_ascii=False) + "\n")
            made += 1
            if made % 25 == 0:
                print(f"  pairs {made}/{n_clips}")
    return made


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--suite", type=int, default=0,
                    help="N clips for SYNTH robustness suite (stress test only)")
    ap.add_argument("--pairs", type=int, default=0,
                    help="N augmented clips for embedding training")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if not (args.suite or args.pairs):
        ap.error("nothing to do: pass --suite N and/or --pairs N")
    rng = random.Random(args.seed)
    groups, titles = collect_groups()
    multi = sum(1 for v in groups.values() if len(v) >= 2)
    print(f"catalog: {sum(len(v) for v in groups.values())} files, "
          f"{len(groups)} compositions, {multi} with >=2 renditions")
    if args.suite:
        n = build_suite(groups, titles, args.suite, rng)
        print(f"suite done: {n} clips -> {SUITE_DIR}")
    if args.pairs:
        n = build_pairs(groups, titles, args.pairs, rng)
        print(f"pairs done: {n} clips -> {PAIRS_DIR}")


if __name__ == "__main__":
    main()
