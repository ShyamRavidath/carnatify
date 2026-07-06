"""Prepare local audio + tonic manifest for the CNN Colab run.

Cuts 65s FLAC segments (mixed audio, pre-Demucs) for the two sources whose
audio is NOT already on Google Drive (Saraga, carnatic_varnam), and collects
per-track tonics for all three sources into one manifest. Archive audio is
already on Drive (carnatify_concert_audio.zip) — the Colab notebook cuts its
segments itself using the tonics shipped here.

Tonic sources (no estimation anywhere — all known):
- saraga:  annotated tonic, from data/raga_v2_cache/saraga_v3/*.npz
- archive: essentia tonic already computed, from data/raga_v2_cache/archive_v3/*.npz
- varnam:  annotated tonics.yaml (keyed by artist name in the filename)

Output: data/cnn_extra_audio/{saraga,varnam}/*.flac + manifest.json.
Zip and upload:  cd data && zip -r ~/cnn_extra_audio.zip cnn_extra_audio
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

ROOT = Path(__file__).parent
OUT = ROOT / "data" / "cnn_extra_audio"
SEG_LEN_S = 65.0
SEGS_PER_TRACK = 3
SR = 44100


def cut_segments(audio_path: str, dest_dir: Path, stem: str) -> list[str]:
    """Cut up to SEGS_PER_TRACK non-overlapping 65s segments, evenly placed."""
    try:
        dur = librosa.get_duration(path=audio_path)
    except Exception:
        return []
    if dur < 50:
        return []
    n = min(SEGS_PER_TRACK, max(1, int((dur - 30) // SEG_LEN_S)))
    # even placement between 30s intro-skip and the end
    usable = dur - 30 - SEG_LEN_S
    starts = [30 + usable * i / max(1, n - 1) for i in range(n)] if n > 1 else [min(30, max(0, dur - SEG_LEN_S))]
    written = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(starts):
        out = dest_dir / f"{stem}__{i}.flac"
        if out.exists():
            written.append(out.name)
            continue
        y, _ = librosa.load(audio_path, sr=SR, mono=True, offset=max(0, s), duration=SEG_LEN_S)
        if len(y) < SR * 50:
            continue
        sf.write(out, y, SR)
        written.append(out.name)
    return written


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"segments": [], "archive_tonics": {}}

    # ── archive: tonics only (audio already on Drive) ────────────────────────
    for p in (ROOT / "data" / "raga_v2_cache" / "archive_v3").glob("*.npz"):
        d = np.load(p, allow_pickle=True)
        manifest["archive_tonics"][str(d["track_id"])] = {
            "tonic": float(d["tonics"][0]),
            "raga": str(d["raga"]),
        }
    print(f"archive tonics: {len(manifest['archive_tonics'])}")

    # ── saraga: cut segments, annotated tonic from v3 cache ─────────────────
    import mirdata

    ds = mirdata.initialize("saraga_carnatic", data_home=str(ROOT))
    tracks = ds.load_tracks()
    n_seg = 0
    for p in sorted((ROOT / "data" / "raga_v2_cache" / "saraga_v3").glob("*.npz")):
        d = np.load(p, allow_pickle=True)
        tid, raga, tonic = str(d["track_id"]), str(d["raga"]), float(d["tonics"][0])
        tr = tracks.get(tid)
        if tr is None or not tr.audio_path or not Path(tr.audio_path).exists():
            continue
        safe = re.sub(r"[^\w\-]", "_", tid)
        for name in cut_segments(tr.audio_path, OUT / "saraga", safe):
            manifest["segments"].append(
                {"file": f"saraga/{name}", "source": "saraga", "track_id": tid,
                 "raga": raga, "tonic": tonic}
            )
            n_seg += 1
        print(f"  saraga {tid} ok", flush=True)
    print(f"saraga segments: {n_seg}")

    # ── varnam: filename carries artist + raga; tonic from tonics.yaml ──────
    import yaml

    vroot = ROOT / "carnatic_varnam_1.1"
    tonics = yaml.safe_load((vroot / "Notations_Annotations" / "annotations" / "tonics.yaml").read_text())
    n_seg = 0
    for mp3 in sorted((vroot / "Audio").glob("*.mp3")):
        m = re.search(r"by-(\w+)-in-([\w\-]+)-raaga", mp3.stem)
        if not m:
            print(f"  varnam SKIP (unparsable): {mp3.name}")
            continue
        artist, raga = m.group(1), m.group(2)
        tonic = tonics.get(artist)
        if tonic is None:
            print(f"  varnam SKIP (no tonic): {artist}")
            continue
        tid = f"varnam__{artist}__{raga}"
        for name in cut_segments(str(mp3), OUT / "varnam", f"{artist}__{raga}"):
            manifest["segments"].append(
                {"file": f"varnam/{name}", "source": "varnam", "track_id": tid,
                 "raga": raga, "tonic": float(tonic)}
            )
            n_seg += 1
        print(f"  varnam {tid} ok", flush=True)
    print(f"varnam segments: {n_seg}")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"\nmanifest: {len(manifest['segments'])} local segments, "
          f"{len(manifest['archive_tonics'])} archive tonics")
    print("Next: cd data && zip -r ~/cnn_extra_audio.zip cnn_extra_audio && upload to Drive")


if __name__ == "__main__":
    main()
