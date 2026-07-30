#!/usr/bin/env python3
"""Bundle the Saraga ASR pilot data for upload to Colab/Drive.

Produces `saraga_pilot.zip` at repo root containing:
  - saraga_asr_trainset_clean.json          (cleaned targets + flags)
  - saraga1.5_carnatic/.../*.mp3            (the 26 referenced tracks, at
                                             their original relative paths)

The Colab fine-tune script (`colab_asr_finetune.py`) unzips this and resolves
each segment's `audio_rel_path` against the unzip root, then slices windows on
the GPU box (which has ffmpeg; this laptop does not). Audio is copied, never
decoded here.

Run: venv_train/bin/python scripts/build_saraga_pilot_zip.py
Then: upload saraga_pilot.zip to MyDrive/carnatify/saraga_pilot.zip
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "saraga_asr_trainset_clean.json"
OUT = ROOT / "saraga_pilot.zip"


def main() -> None:
    segs = json.loads(CLEAN.read_text())
    audio = sorted({s["audio_rel_path"] for s in segs})
    missing = [p for p in audio if not (ROOT / p).exists()]
    if missing:
        raise SystemExit(f"missing {len(missing)} audio files, e.g. {missing[0]}")

    total = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_STORED) as z:
        z.write(CLEAN, arcname=CLEAN.name)
        for rel in audio:
            z.write(ROOT / rel, arcname=rel)
            total += (ROOT / rel).stat().st_size
    print(f"wrote {OUT.name}: {len(audio)} mp3s + {CLEAN.name} "
          f"(~{total/1e6:.0f} MB audio)")
    print("upload to: MyDrive/carnatify/saraga_pilot.zip")


if __name__ == "__main__":
    main()
