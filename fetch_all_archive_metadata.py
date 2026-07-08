"""Enumerate ALL archive.org identifiers referenced by shankarkrish blog pages
(source_urls from data/scraped_compositions.json) and fetch file metadata for
every one into data/raga_v2_cache/archive_metadata/ (same format as
download_concerts.py: list of original-source MP3 file dicts). Resume-safe.

Usage: python fetch_all_archive_metadata.py
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent
COMPOSITIONS_PATH = ROOT / "data" / "scraped_compositions.json"
METADATA_CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "archive_metadata"
IDENTIFIERS_PATH = ROOT / "data" / "raga_v2_cache" / "archive_identifiers.json"

USER_AGENT = (
    "CarnatifyResearchBot/1.0 (+https://carnatify.vercel.app; "
    "educational raga-classification research; contact: dpti0904@gmail.com)"
)
EMBED_RE = re.compile(r"archive\.org/(?:embed|details|download)/([A-Za-z0-9_.\-]+)")
METADATA_SLEEP_S = 0.5


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    compositions = json.loads(COMPOSITIONS_PATH.read_text())
    source_urls = sorted({c["source_url"] for c in compositions})
    print(f"Blog pages: {len(source_urls)}")

    # Page -> identifiers (cached so reruns skip page fetches)
    if IDENTIFIERS_PATH.exists():
        page_idents = json.loads(IDENTIFIERS_PATH.read_text())
    else:
        page_idents = {}
    for i, url in enumerate(source_urls, 1):
        if url in page_idents:
            continue
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            page_idents[url] = sorted(set(EMBED_RE.findall(r.text)))
            print(f"[{i}/{len(source_urls)}] {url} -> {len(page_idents[url])} identifiers")
        except Exception as exc:
            print(f"[{i}/{len(source_urls)}] FAILED {url}: {exc}")
        IDENTIFIERS_PATH.write_text(json.dumps(page_idents, indent=1))
        time.sleep(1.0)

    all_idents = sorted({i for lst in page_idents.values() for i in lst})
    print(f"Total unique identifiers: {len(all_idents)}")

    METADATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = {p.stem for p in METADATA_CACHE_DIR.glob("*.json")}
    todo = [i for i in all_idents if i not in cached]
    print(f"Already cached: {len(cached)}; to fetch: {len(todo)}")

    n_ok = n_fail = 0
    for k, ident in enumerate(todo, 1):
        try:
            r = session.get(f"https://archive.org/metadata/{ident}", timeout=30)
            r.raise_for_status()
            data = r.json()
            files = [
                f for f in data.get("files", [])
                if f.get("source") == "original" and "MP3" in f.get("format", "")
            ]
            (METADATA_CACHE_DIR / f"{ident}.json").write_text(json.dumps(files))
            n_ok += 1
            if k % 25 == 0:
                print(f"  [{k}/{len(todo)}] fetched {ident} ({len(files)} mp3s)", flush=True)
        except Exception as exc:
            n_fail += 1
            print(f"  [{k}/{len(todo)}] FAILED {ident}: {exc}", flush=True)
        time.sleep(METADATA_SLEEP_S)

    print(f"Done: {n_ok} fetched, {n_fail} failed, cache total "
          f"{len(list(METADATA_CACHE_DIR.glob('*.json')))}")


if __name__ == "__main__":
    main()
