"""Seed the lyrics catalog with composition titles from saraga_carnatic.

Run from project root:
    python seed_catalog.py

Writes stubs (title + raga, no lyrics, no meaning) to data/lyrics.db.
Existing titles are left unchanged. The Anthropic API is never called here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from carnatify.lyrics.pipeline import LyricsCatalog


def main() -> None:
    print("Seeding lyrics catalog from saraga_carnatic …")
    with LyricsCatalog() as catalog:
        n = catalog.seed_from_saraga()
        total = catalog._conn.execute(
            "SELECT COUNT(*) FROM lyrics_catalog"
        ).fetchone()[0]
    print(f"Done. {n} new titles seeded  ({total} total in catalog).")
    print(f"  → {Path('data/lyrics.db').resolve()}")


if __name__ == "__main__":
    main()
