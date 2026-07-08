"""Build data/pending_extraction.json for the Colab GPU extraction notebook.

Lists every local mp3 in data/concert_audio/ that has no feature npz in
data/raga_v2_cache/archive_v3/, with a re-downloadable archive.org URL
(reconstructed by joining the download manifest back to the metadata cache).
The JSON is small and committed to git so Colab can clone and fetch audio
directly from archive.org — no multi-GB Drive upload needed.

Usage: python build_pending_extraction.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "data" / "concert_audio"
ARCHIVE_V3 = ROOT / "data" / "raga_v2_cache" / "archive_v3"
METADATA_CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "archive_metadata"
MANIFEST_PATH = OUT_DIR / "download_manifest.json"
PENDING_PATH = ROOT / "data" / "pending_extraction.json"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    by_path = {r["file_path"]: r for r in manifest}

    # identifier -> files metadata (lazy cache)
    meta_cache: dict[str, list[dict]] = {}

    def find_url(rec: dict) -> str | None:
        ident = rec["archive_identifier"]
        if ident not in meta_cache:
            p = METADATA_CACHE_DIR / f"{ident}.json"
            meta_cache[ident] = json.loads(p.read_text()) if p.exists() else []
        want = norm(rec["file_title_raw"])
        for f in meta_cache[ident]:
            if norm(f.get("title") or "") == want or norm(Path(f.get("name", "")).stem) == want:
                return f"https://archive.org/download/{ident}/{quote(f['name'])}"
        # fallback: unique file whose name contains the composition title fold
        cands = [f for f in meta_cache[ident]
                 if norm(rec["composition_title"]) in norm(f.get("name", ""))]
        if len(cands) == 1:
            return f"https://archive.org/download/{ident}/{quote(cands[0]['name'])}"
        return None

    extracted = {p.stem for p in ARCHIVE_V3.glob("*.npz")}
    pending, no_url = [], 0
    for raga_dir in sorted(OUT_DIR.iterdir()):
        if not raga_dir.is_dir():
            continue
        for mp3 in sorted(raga_dir.glob("*.mp3")):
            track_id = f"archive__{raga_dir.name}__{mp3.stem}"
            if track_id in extracted:
                continue
            rel = str(mp3.relative_to(ROOT))
            rec = by_path.get(rel)
            url = find_url(rec) if rec else None
            if url is None:
                no_url += 1
                continue
            pending.append({"track_id": track_id, "raga": raga_dir.name, "url": url})

    PENDING_PATH.write_text(json.dumps(pending, ensure_ascii=False, indent=1))
    print(f"pending: {len(pending)}  (skipped, no URL: {no_url})")
    print(f"-> {PENDING_PATH}")


if __name__ == "__main__":
    main()
