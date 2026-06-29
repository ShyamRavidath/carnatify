"""Pre-generate Gemini meanings for the most common *real* scraped compositions.

Walks the most frequent titles in data/scraped_compositions.json, skips concert
form-names and scrape noise (varNam, RTP, tillAnA, slOkam, viruttam, timestamps,
"???", …), and caches an English meaning for each via LyricsCatalog. Already
cached titles are skipped, so the run is resumable.

Respects the Gemini free tier: ~7s between calls (≈8 RPM) with backoff/retry on
429s, and an early stop once the daily quota is clearly exhausted.

Usage:
    GEMINI_API_KEY=... python generate_meanings.py [N]   # N = how many titles (default 100)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

_SCRAPED = Path(__file__).parent / "data" / "scraped_compositions.json"
_PACING_SECONDS = 7
_MAX_CONSECUTIVE_FAILS = 5  # stop early when the daily quota is spent

# Concert form-names / section labels that are not actual compositions.
_FORM_NAMES = {
    "varnam", "rtp", "ragam tanam pallavi", "ragam thanam pallavi",
    "raga tanam pallavi", "tillana", "thillana", "slokam", "slokham", "sloka",
    "alapana", "alapanai", "viruttam", "virutham", "niraval", "swaram",
    "kalpanaswaram", "tani", "thani", "tani avartanam", "thani avartanam",
    "mangalam", "pallavi", "anupallavi", "charanam", "ragam", "thanam", "tanam",
    "vocal", "shlokam",
}


def is_real_composition(title: str) -> bool:
    """True if *title* looks like an actual composition, not a form-name/noise."""
    t = (title or "").strip()
    if not t:
        return False
    if re.search(r"\d{1,2}:\d{2}", t):  # embedded timestamp like "0:00 varNam"
        return False
    low = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    low = re.sub(r"\s+", " ", low).strip()
    if len(low) < 3:           # "???", stray punctuation, single syllables
        return False
    if low in _FORM_NAMES:
        return False
    return True


def real_titles_by_frequency(limit: int) -> list[str]:
    data = json.loads(_SCRAPED.read_text())
    counts = Counter(r["title"] for r in data)
    ordered = [t for t, _ in counts.most_common()]
    real = [t for t in ordered if is_real_composition(t)]
    return real[:limit]


def main() -> None:
    if "GEMINI_API_KEY" not in os.environ:
        sys.exit("Set GEMINI_API_KEY in the environment first.")

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100

    from google.api_core.exceptions import ResourceExhausted
    from carnatify.lyrics.pipeline import LyricsCatalog

    titles = real_titles_by_frequency(limit)
    print(f"{len(titles)} real compositions selected (form-names/noise filtered out)\n")

    cat = LyricsCatalog()
    success = skip = fail = 0
    consecutive_fail = 0

    for i, title in enumerate(titles, 1):
        row = cat.lookup(title)
        if row and row.get("meaning_en"):
            skip += 1
            continue

        result = None
        for attempt in range(3):
            try:
                result = cat.generate_meaning(title)
                break
            except ResourceExhausted:
                wait = 25 * (attempt + 1)
                print(f"  …rate-limited, backing off {wait}s", flush=True)
                time.sleep(wait)
            except Exception as e:  # safety block, malformed lyrics, etc.
                print(f"[{i:3d}] x  {title[:50]} ({type(e).__name__})", flush=True)
                break

        if result:
            success += 1
            consecutive_fail = 0
            print(f"[{i:3d}] ok {title[:50]}", flush=True)
        else:
            fail += 1
            consecutive_fail += 1
            print(f"[{i:3d}] -- {title[:50]} (no meaning)", flush=True)
            if consecutive_fail >= _MAX_CONSECUTIVE_FAILS:
                print("\nDaily quota appears exhausted — stopping early. "
                      "Re-run later to resume (cached titles are skipped).", flush=True)
                break

        time.sleep(_PACING_SECONDS)

    cat.close()
    print(f"\nDone: {success} generated, {skip} already cached, {fail} not generated")


if __name__ == "__main__":
    main()
