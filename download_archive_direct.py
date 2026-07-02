"""Second-pass concert downloader: parse ragas directly from archive.org file titles.

`download_concerts.py` joins blog records to archive.org files on an exact
normalized (title, raga) pair, which yields only ~366 of the 719 archive files
whose titles carry the "{title} - {raga}[ - {tala}]" shape. This pass skips the
blog join entirely: it walks the archive.org metadata already cached in
data/raga_v2_cache/archive_metadata/, canonicalizes the raga segment via
data/raga_aliases.json, and downloads anything not already on disk.

Run after download_concerts.py (it populates the metadata cache). Idempotent.

Usage:
    python download_archive_direct.py
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).parent
ALIASES_PATH = ROOT / "data" / "raga_aliases.json"
METADATA_CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "archive_metadata"
OUT_DIR = ROOT / "data" / "concert_audio"

USER_AGENT = (
    "CarnatifyResearchBot/1.0 (+https://carnatify.vercel.app; "
    "educational raga-classification research; contact: dpti0904@gmail.com)"
)
MAX_PER_RAGA = 30
DOWNLOAD_SLEEP_S = 2.0
DASH_SPLIT_RE = re.compile(r"\s+[–—-]\s+")


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    aliases = json.loads(ALIASES_PATH.read_text())
    alias_map = {norm(k): v for k, v in aliases.items() if v}

    per_raga_count: Counter[str] = Counter()
    for raga_dir in OUT_DIR.iterdir() if OUT_DIR.exists() else []:
        if raga_dir.is_dir():
            per_raga_count[raga_dir.name] = len(list(raga_dir.glob("*.mp3")))

    n_new = n_skip = n_fail = 0
    for meta_path in sorted(METADATA_CACHE_DIR.glob("*.json")):
        ident = meta_path.stem
        for f in json.loads(meta_path.read_text()):
            file_title = f.get("title") or f.get("name", "")
            parts = [p for p in DASH_SPLIT_RE.split(file_title) if p]
            if len(parts) < 2:
                continue
            canon = alias_map.get(norm(parts[1]))
            if canon is None or per_raga_count[canon] >= MAX_PER_RAGA:
                continue

            # Same filename transform as download_concerts.py so re-downloads
            # of already-matched tracks collide and are skipped.
            safe_title = re.sub(r"[^\w \-]", "", parts[0]).strip() or Path(f["name"]).stem
            dest_dir = OUT_DIR / canon
            dest_path = dest_dir / f"{safe_title}.mp3"
            if dest_path.exists():
                n_skip += 1
                continue

            url = f"https://archive.org/download/{ident}/{quote(f['name'])}"
            try:
                resp = session.get(url, timeout=120)
                resp.raise_for_status()
            except Exception as exc:
                n_fail += 1
                print(f"  FAILED {url}: {exc}")
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(resp.content)
            per_raga_count[canon] += 1
            n_new += 1
            print(f"  [{n_new}] {canon}: {parts[0]} <- {ident}", flush=True)
            time.sleep(DOWNLOAD_SLEEP_S)

    print(f"\nDone: {n_new} new, {n_skip} already present, {n_fail} failed")
    print(f"Total on disk: {sum(per_raga_count.values())} tracks, "
          f"{len([r for r, c in per_raga_count.items() if c])} ragas")


if __name__ == "__main__":
    main()
