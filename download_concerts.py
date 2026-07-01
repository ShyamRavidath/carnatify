"""Download concert audio from archive.org, paired with raga labels from
data/scraped_compositions.json, for ragas in the current 40-raga vocabulary
(models/raga_label_encoder.pkl).

This grows the pool of real, locally-available raga-labeled audio beyond
Saraga Carnatic (only ~3 tracks/raga after filtering -- see
train_raga_v2_saraga.py and HANDOFF.md for why that wasn't enough to
retrain the raga classifier on the actual Demucs+pyin inference pipeline).
Purely a download script: no training, no model changes. The retrain
happens once this completes or CompMusic audio access is granted,
whichever comes first.

How the matching works
-----------------------
shankarkrish.blog artist pages embed whole-concert archive.org items via
<iframe src="https://archive.org/embed/{identifier}">, each following a
<ul> of "{title} - {raga}" (or "{title} - {raga} - {tala}") <li> entries
for that concert. archive.org's own file metadata
(https://archive.org/metadata/{identifier}) carries a matching `title`
field per original-source mp3 in the exact same "{title} - {raga}[ -
{tala}]" text -- so blog HTML is only used to discover which archive.org
identifiers exist on a given artist page; the actual title/raga match is
done against archive.org's file metadata directly (more reliable than
re-parsing the blog's <ul>/<li> structure and depending on list-position
alignment).

Usage:
    python download_concerts.py
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

import joblib
import requests

ROOT = Path(__file__).parent
COMPOSITIONS_PATH = ROOT / "data" / "scraped_compositions.json"
LABEL_ENCODER_PATH = ROOT / "models" / "raga_label_encoder.pkl"
OUT_DIR = ROOT / "data" / "concert_audio"
METADATA_CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "archive_metadata"

USER_AGENT = (
    "CarnatifyResearchBot/1.0 (+https://carnatify.vercel.app; "
    "educational raga-classification research; contact: dpti0904@gmail.com)"
)
MAX_PER_RAGA = 10
MAX_TOTAL = 400
DOWNLOAD_SLEEP_S = 2.0
METADATA_SLEEP_S = 0.5

EMBED_RE = re.compile(r"archive\.org/embed/([A-Za-z0-9_.\-]+)")
DASH_SPLIT_RE = re.compile(r"\s+[–—-]\s+")


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def parse_title_raga(file_title: str) -> tuple[str, str] | None:
    """"title - raga" -> (title, raga); "title - raga - tala" -> (title, raga)."""
    parts = [p for p in DASH_SPLIT_RE.split(file_title) if p]
    if len(parts) == 2:
        return norm(parts[0]), norm(parts[1])
    if len(parts) >= 3:
        return norm(parts[0]), norm(parts[1])  # raga is the middle segment
    return None


def get_page_identifiers(source_url: str, session: requests.Session) -> list[str]:
    r = session.get(source_url, timeout=30)
    r.raise_for_status()
    return sorted(set(EMBED_RE.findall(r.text)))


def get_item_files(identifier: str, session: requests.Session) -> list[dict]:
    cache_path = METADATA_CACHE_DIR / f"{identifier}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    r = session.get(f"https://archive.org/metadata/{identifier}", timeout=30)
    r.raise_for_status()
    data = r.json()
    files = [
        f for f in data.get("files", [])
        if f.get("source") == "original" and "MP3" in f.get("format", "")
    ]
    METADATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(files))
    return files


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    le = joblib.load(LABEL_ENCODER_PATH)
    target_ragas = set(le.classes_.tolist())

    compositions = json.loads(COMPOSITIONS_PATH.read_text())
    matching = [c for c in compositions if c.get("raga_canonical") in target_ragas]
    print(f"Compositions in 40-raga vocabulary: {len(matching)} / {len(compositions)}")

    by_source_url: dict[str, list[dict]] = defaultdict(list)
    for c in matching:
        by_source_url[c["source_url"]].append(c)
    print(f"Unique blog pages to scan: {len(by_source_url)}")

    per_raga_count: Counter[str] = Counter()
    total_downloaded = 0
    downloaded_bytes = 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for page_i, (source_url, records) in enumerate(by_source_url.items(), 1):
        if total_downloaded >= MAX_TOTAL:
            print("Reached MAX_TOTAL, stopping.")
            break
        try:
            identifiers = get_page_identifiers(source_url, session)
        except Exception as exc:
            print(f"[page {page_i}] FAILED {source_url}: {exc}")
            continue
        time.sleep(DOWNLOAD_SLEEP_S)

        title_raga_map: dict[tuple[str, str], tuple[str, str]] = {}
        for ident in identifiers:
            try:
                files = get_item_files(ident, session)
            except Exception as exc:
                print(f"  [metadata] {ident} FAILED: {exc}")
                continue
            for f in files:
                key = parse_title_raga(f.get("title") or f.get("name", ""))
                if key:
                    title_raga_map[key] = (ident, f["name"])
            time.sleep(METADATA_SLEEP_S)

        print(f"[page {page_i}/{len(by_source_url)}] {source_url} -> "
              f"{len(identifiers)} concerts, {len(title_raga_map)} tracks indexed")

        for rec in records:
            if total_downloaded >= MAX_TOTAL:
                break
            raga_canon = rec["raga_canonical"]
            if per_raga_count[raga_canon] >= MAX_PER_RAGA:
                continue
            key = (norm(rec["title"]), norm(rec["raga"]))
            hit = title_raga_map.get(key)
            if hit is None:
                continue
            ident, filename = hit

            dest_dir = OUT_DIR / raga_canon
            dest_dir.mkdir(parents=True, exist_ok=True)
            safe_title = re.sub(r"[^\w \-]", "", rec["title"]).strip() or filename
            dest_path = dest_dir / f"{safe_title}.mp3"
            if dest_path.exists():
                per_raga_count[raga_canon] += 1
                total_downloaded += 1
                downloaded_bytes += dest_path.stat().st_size
                continue

            download_url = f"https://archive.org/download/{ident}/{quote(filename)}"
            try:
                resp = session.get(download_url, timeout=120)
                resp.raise_for_status()
                dest_path.write_bytes(resp.content)
            except Exception as exc:
                print(f"  [download] {download_url} FAILED: {exc}")
                continue

            per_raga_count[raga_canon] += 1
            total_downloaded += 1
            downloaded_bytes += dest_path.stat().st_size
            print(f"  [{total_downloaded}/{MAX_TOTAL}] {raga_canon}: "
                  f"{rec['title']} <- {ident}/{filename}")
            time.sleep(DOWNLOAD_SLEEP_S)

    print("\n── Summary ─────────────────────────────────────────────")
    print(f"Ragas covered: {len(per_raga_count)} / {len(target_ragas)}")
    print(f"Tracks downloaded: {total_downloaded}")
    print(f"Estimated total size: {downloaded_bytes / 1e6:.1f} MB")
    for raga, n in per_raga_count.most_common():
        print(f"  {raga:<25} {n}")
    missing = target_ragas - set(per_raga_count)
    if missing:
        print(f"\nRagas with zero downloads ({len(missing)}): {sorted(missing)}")


if __name__ == "__main__":
    main()
