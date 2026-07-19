#!/usr/bin/env python
"""prepare_coverhunter_data.py — package synth_train clips for CSI training.

Converts the augmentation manifest (data/synth_train/manifest.jsonl, produced
by augment_wild.py --pairs) plus the real multi-rendition concert recordings
into the dataset layout cover-song-ID trainers (CoverHunter / ByteCover-class)
consume:

  data/coverhunter_data/
    wav16k/<utt>.wav          16 kHz mono
    full.jsonl                one JSON line per clip:
                                {utt, wav, dur_s, song_id, version}
    train.jsonl / val.jsonl   split by song_id — val compositions are fully
                              held out (retrieval eval must be cross-song,
                              same-corpus leakage is how this project got
                              burned before)
    song_id_map.json          song_id -> comp_id

"version" groups clips from the same source rendition; the trainer treats
same song_id / different version as positives. Real renditions of the 68
multi-rendition compositions are added as extra versions (random 60 s crop,
un-augmented) — those are the scarce genuine cross-artist positives.

Zero-cost, local. GPU training itself happens on Colab Pro: upload
data/coverhunter_data/ + clone the CoverHunter repo there, then adapt
full.jsonl to its exact data_process schema if field names drifted.

Usage:
    venv_train/bin/python prepare_coverhunter_data.py [--val-frac 0.15]
"""

import argparse
import json
import os
import random
import re
import sys
import unicodedata

import numpy as np
import librosa
import soundfile as sf

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "data", "synth_train", "manifest.jsonl")
CONCERT_DIR = os.path.join(ROOT, "data", "concert_audio")
OUT = os.path.join(ROOT, "data", "coverhunter_data")
WAV_DIR = os.path.join(OUT, "wav16k")
SR = 16000


def load_16k(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    return y


def write_wav(utt, y):
    out = os.path.join(WAV_DIR, f"{utt}.wav")
    sf.write(out, y, SR)
    return os.path.relpath(out, ROOT), len(y) / SR


def real_rendition_rows(rng):
    """Un-augmented 60 s crops of every rendition in multi-rendition groups."""
    sys.path.insert(0, ROOT)
    from augment_wild import collect_groups   # same grouping/casefold logic
    groups, titles = collect_groups()
    rows = []
    for (raga, tkey), files in sorted(groups.items()):
        if len(files) < 2:
            continue
        comp_id = f"{_slug(raga)}::{_slug(titles[(raga, tkey)])}"
        for i, f in enumerate(sorted(files)):
            rows.append({"comp_id": comp_id, "source": f,
                         "version": f"real{i}"})
    return rows


def _slug(s, maxlen=60):
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[^\w\- ]+", "", s).strip().replace(" ", "_")
    return s[:maxlen] or "untitled"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    if not os.path.exists(MANIFEST):
        sys.exit(f"missing {MANIFEST} — run augment_wild.py --pairs first")
    os.makedirs(WAV_DIR, exist_ok=True)

    song_ids: dict[str, int] = {}
    rows = []

    # synthetic augmented clips (already 20-60 s, 22.05 kHz)
    for n, line in enumerate(open(MANIFEST)):
        m = json.loads(line)
        comp = m["comp_id"]
        sid = song_ids.setdefault(comp, len(song_ids))
        utt = f"synth_{n:06d}"
        y = load_16k(os.path.join(ROOT, m["clip"]))
        wav, dur = write_wav(utt, y)
        rows.append({"utt": utt, "wav": wav, "dur_s": round(dur, 1),
                     "song_id": sid, "version": f"aug_{m['source']}"})
        if (n + 1) % 50 == 0:
            print(f"  synth {n + 1}")

    # real cross-rendition versions (the genuine positives)
    for k, r in enumerate(real_rendition_rows(rng)):
        sid = song_ids.setdefault(r["comp_id"], len(song_ids))
        utt = f"real_{k:04d}"
        y = load_16k(r["source"])
        if len(y) < 20 * SR:
            continue
        n60 = min(len(y), 60 * SR)
        start = rng.randint(0, len(y) - n60)
        wav, dur = write_wav(utt, y[start:start + n60])
        rows.append({"utt": utt, "wav": wav, "dur_s": round(dur, 1),
                     "song_id": sid, "version": r["version"]})
        if (k + 1) % 25 == 0:
            print(f"  real {k + 1}")

    # split by song_id; make sure val contains some multi-version songs so
    # retrieval eval is meaningful
    versions_per_song = {}
    for r in rows:
        versions_per_song.setdefault(r["song_id"], set()).add(r["version"])
    sids = sorted(song_ids.values())
    rng.shuffle(sids)
    n_val = max(1, int(len(sids) * args.val_frac))
    multi = [s for s in sids if len(versions_per_song.get(s, ())) >= 2]
    rng.shuffle(multi)
    val = set(multi[: max(1, n_val // 2)])
    for s in sids:
        if len(val) >= n_val:
            break
        val.add(s)

    with open(os.path.join(OUT, "full.jsonl"), "w") as ff, \
         open(os.path.join(OUT, "train.jsonl"), "w") as tf, \
         open(os.path.join(OUT, "val.jsonl"), "w") as vf:
        for r in rows:
            line = json.dumps(r, ensure_ascii=False) + "\n"
            ff.write(line)
            (vf if r["song_id"] in val else tf).write(line)

    with open(os.path.join(OUT, "song_id_map.json"), "w") as f:
        json.dump({v: k for k, v in song_ids.items()}, f,
                  ensure_ascii=False, indent=0)

    n_train = sum(r["song_id"] not in val for r in rows)
    print(f"done: {len(rows)} clips, {len(song_ids)} songs "
          f"({len(multi)} with >=2 versions); train {n_train} / "
          f"val {len(rows) - n_train} (songs disjoint) -> {OUT}")


if __name__ == "__main__":
    main()
