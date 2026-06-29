"""Scrape composition–raga metadata from shankarkrish.blog/carnatic-vocal/.

Metadata only — NO audio is downloaded. The blog lists concert track listings
per artist, one composition per line in the form::

    siddhi vinAyakam – shanmukapriya
    vAtApi gaNapatim – hamsadwani

The left side of the dash is the composition title, the right side is the raga.
Some lines carry a trailing tala (``varNam – kalyANi – aTa``) or are
accompaniment credits (``with Lalgudi Jayaraman – Violin``); those are handled
gracefully — most non-matching lines are simply skipped.

Output:
  * data/scraped_compositions.json — [{title, raga, artist, source_url}, ...]
  * seeds new (title, raga) rows into data/lyrics.db via
    LyricsCatalog.seed_from_scrape()

Usage:
    python scrape_concerts.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent / "src"))
from carnatify.lyrics.pipeline import LyricsCatalog  # noqa: E402

INDEX_URL = "https://shankarkrish.blog/carnatic-vocal/"
USER_AGENT = "CarnatifyMetaBot/0.1 (Carnatic music education; respectful crawler)"
REQUEST_DELAY_SECONDS = 1.0
TIMEOUT = 30

_OUT_JSON = Path(__file__).parent / "data" / "scraped_compositions.json"

# Listings use a dash with spaces around it; splitting on that avoids breaking
# hyphenated words inside a title or raga name.
_DASH_SPLIT = re.compile(r"\s+[–—-]\s+")

# Lines whose "raga" side is really an accompaniment instrument / credit.
_NON_RAGA = {
    "violin", "mridangam", "kanjira", "ghatam", "morsing", "morching",
    "flute", "veena", "tambura", "tanpura", "khanjira", "konnakkol",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def fetch(sess: requests.Session, url: str) -> str | None:
    """GET *url*, returning HTML text or None on any failure."""
    try:
        r = sess.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.text
    except requests.RequestException as exc:
        print(f"  ! failed {url}: {exc}", file=sys.stderr)
        return None


def find_artist_pages(index_html: str) -> list[str]:
    """Return all distinct /carnatic-vocal/<slug>/ artist page URLs."""
    soup = BeautifulSoup(index_html, "html.parser")
    found: list[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = urljoin(INDEX_URL, a["href"].strip())
        parsed = urlparse(href)

        if "shankarkrish" not in parsed.netloc:
            continue
        if parsed.query or "#" in a["href"]:
            continue

        parts = [p for p in parsed.path.split("/") if p]
        # Expect ["carnatic-vocal", "<artist-slug>"] — exactly the subpages,
        # not the index itself (which has no slug after carnatic-vocal).
        if len(parts) != 2 or parts[0] != "carnatic-vocal":
            continue

        # Normalise host so .blog and .wordpress.com duplicates collapse.
        key = parsed.path.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        found.append(f"https://shankarkrish.blog{parsed.path}")

    return found


def artist_name(soup: BeautifulSoup, url: str) -> str:
    """Best-effort artist display name from the page heading, else the slug."""
    el = soup.find(class_="entry-title") or soup.find("h1")
    if el and el.get_text(strip=True):
        return el.get_text(strip=True)
    slug = [p for p in urlparse(url).path.split("/") if p][-1]
    return slug.replace("-", " ").title()


def parse_listings(html: str, url: str) -> list[dict]:
    """Extract (title, raga, artist, source_url) triples from one artist page."""
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(class_="entry-content") or soup
    artist = artist_name(soup, url)

    records: list[dict] = []
    for raw in content.get_text("\n").split("\n"):
        line = raw.strip()
        if not line or line.lower().startswith("with"):
            continue  # blank or accompaniment-credit line

        parts = _DASH_SPLIT.split(line)
        if len(parts) < 2:
            continue  # no dash → not a listing line

        title = parts[0].strip(" .–—-")
        raga = parts[1].strip(" .–—-")
        if not title or not raga:
            continue
        # Guard against prose and accompaniment lines.
        if len(title) > 60 or len(raga) > 40:
            continue
        if raga.lower() in _NON_RAGA:
            continue

        records.append(
            {"title": title, "raga": raga, "artist": artist, "source_url": url}
        )

    return records


def main() -> None:
    sess = _session()

    print(f"Fetching index {INDEX_URL}")
    index_html = fetch(sess, INDEX_URL)
    if index_html is None:
        sys.exit("Could not fetch the index page.")

    artist_pages = find_artist_pages(index_html)
    print(f"Found {len(artist_pages)} artist pages\n")

    all_records: list[dict] = []
    for i, url in enumerate(artist_pages, 1):
        time.sleep(REQUEST_DELAY_SECONDS)  # be polite between requests
        html = fetch(sess, url)
        if html is None:
            continue
        recs = parse_listings(html, url)
        all_records.extend(recs)
        print(f"  [{i}/{len(artist_pages)}] {len(recs):3d} listings · {url}")

    # Deduplicate by (title, raga); keep first artist/source seen.
    unique: dict[tuple[str, str], dict] = {}
    for rec in all_records:
        unique.setdefault((rec["title"], rec["raga"]), rec)
    unique_records = list(unique.values())

    _OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    _OUT_JSON.write_text(json.dumps(unique_records, ensure_ascii=False, indent=2))

    catalog = LyricsCatalog()
    try:
        new_titles = catalog.seed_from_scrape(unique_records)
    finally:
        catalog.close()

    print("\n── Summary ─────────────────────────────")
    print(f"  total records scraped : {len(all_records)}")
    print(f"  unique (title, raga)  : {len(unique_records)}")
    print(f"  new titles added to DB: {new_titles}")
    print(f"  saved -> {_OUT_JSON}")


if __name__ == "__main__":
    main()
