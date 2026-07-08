"""Enumerate Carnatic concert items on archive.org BEYOND the shankarkrish blog.

Queries the archive.org advancedsearch API for audio items likely to be
Carnatic concerts, then fetches per-item file metadata into the same cache dir
used by the downloaders (data/raga_v2_cache/archive_metadata/, one JSON per
identifier, list of original-source MP3 file dicts). The downloaders
(download_targeted_deficits.py / download_title_join.py) then label files from
titles/tracklists exactly as before — no new labeling logic here.

Resume-safe: identifiers already in the cache dir are skipped.

Usage: python fetch_archive_search_metadata.py [--max-items N]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent
METADATA_CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "archive_metadata"
SEARCH_IDS_PATH = ROOT / "data" / "raga_v2_cache" / "archive_search_identifiers.json"

USER_AGENT = (
    "CarnatifyResearchBot/1.0 (+https://carnatify.vercel.app; "
    "educational raga-classification research; contact: dpti0904@gmail.com)"
)
SEARCH_SLEEP_S = 1.0
METADATA_SLEEP_S = 0.75

# Conservative queries: Carnatic vocal concert uploads are commonly titled with
# artist + "carnatic"; kutcheri is the concert word itself.
QUERIES = [
    'carnatic AND mediatype:audio',
    'kutcheri AND mediatype:audio',
    'kriti AND carnatic AND mediatype:audio',
]
ROWS = 500


def search_identifiers(session: requests.Session, max_items: int) -> list[str]:
    if SEARCH_IDS_PATH.exists():
        idents = json.loads(SEARCH_IDS_PATH.read_text())
        print(f"Loaded {len(idents)} identifiers from cache")
        return idents[:max_items]
    seen: list[str] = []
    seen_set: set[str] = set()
    for q in QUERIES:
        page = 1
        while True:
            try:
                r = session.get(
                    "https://archive.org/advancedsearch.php",
                    params={"q": q, "fl[]": "identifier", "rows": ROWS,
                            "page": page, "output": "json"},
                    timeout=60,
                )
                r.raise_for_status()
                docs = r.json()["response"]["docs"]
            except Exception as exc:
                print(f"  search failed q={q!r} page={page}: {exc}")
                break
            if not docs:
                break
            for d in docs:
                ident = d["identifier"]
                if ident not in seen_set:
                    seen_set.add(ident); seen.append(ident)
            print(f"  q={q!r} page={page}: total {len(seen)}", flush=True)
            page += 1
            if len(seen) >= max_items or page > 40:
                break
            time.sleep(SEARCH_SLEEP_S)
        if len(seen) >= max_items:
            break
    SEARCH_IDS_PATH.write_text(json.dumps(seen))
    return seen[:max_items]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=8000)
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    METADATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    idents = search_identifiers(session, args.max_items)
    cached = {p.stem for p in METADATA_CACHE_DIR.glob("*.json")}
    todo = [i for i in idents if i not in cached]
    print(f"{len(idents)} identifiers, {len(todo)} need metadata fetch")

    n_ok = n_empty = n_fail = 0
    for k, ident in enumerate(todo, 1):
        try:
            r = session.get(f"https://archive.org/metadata/{ident}", timeout=60)
            r.raise_for_status()
            md = r.json()
        except Exception as exc:
            n_fail += 1
            print(f"  FAILED {ident}: {exc}", flush=True)
            time.sleep(METADATA_SLEEP_S)
            continue
        files = [
            {"name": f.get("name"), "title": f.get("title"),
             "size": f.get("size"), "source": f.get("source")}
            for f in md.get("files", [])
            if (f.get("name", "").lower().endswith(".mp3")
                and f.get("source") == "original")
        ]
        if files:
            (METADATA_CACHE_DIR / f"{ident}.json").write_text(
                json.dumps(files, ensure_ascii=False))
            n_ok += 1
        else:
            n_empty += 1
        if k % 100 == 0:
            print(f"  [{k}/{len(todo)}] ok={n_ok} empty={n_empty} fail={n_fail}", flush=True)
        time.sleep(METADATA_SLEEP_S)

    print(f"Done: {n_ok} items with mp3s, {n_empty} empty, {n_fail} failed")


if __name__ == "__main__":
    main()
