"""Orchestrates scraping, catalog storage, and meaning generation."""

from __future__ import annotations

from carnatify.lyrics.database import LyricsDatabase
from carnatify.lyrics.meaning_generator import MeaningGenerator
from carnatify.lyrics.scraper import (
    SEED_COMPOSITION_PATHS,
    SEED_INDEX_PATHS,
    LyricsScraper,
)
from carnatify.schemas import LyricsEntry, MeaningEntry


class LyricsPipeline:
    """Wires scraper -> database -> meaning generator."""

    def __init__(
        self,
        database: LyricsDatabase | None = None,
        scraper: LyricsScraper | None = None,
        meaning_generator: MeaningGenerator | None = None,
    ):
        self.database = database or LyricsDatabase()
        self.scraper = scraper or LyricsScraper()
        self.meaning_generator = meaning_generator or MeaningGenerator()

    def lookup(
        self, composition_name: str
    ) -> tuple[LyricsEntry | None, MeaningEntry | None]:
        """Find a composition by name and return its lyrics + meaning."""
        matches = self.database.search_by_name(composition_name)
        if not matches:
            return None, None
        entry = matches[0]
        meaning = self.meaning_generator.generate(entry)
        return entry, meaning

    def build_catalog(
        self,
        composition_paths: list[str] | None = None,
        index_paths: list[str] | None = None,
    ) -> int:
        """Scrape compositions (seed list + discovered links) into the database.

        Returns the number of entries written.
        """
        paths = list(composition_paths or SEED_COMPOSITION_PATHS)
        for index_path in index_paths or SEED_INDEX_PATHS:
            try:
                paths.extend(self.scraper.discover_composition_links(index_path))
            except Exception:
                continue

        seen: set[str] = set()
        deduped = [p for p in paths if not (p in seen or seen.add(p))]

        count = 0
        for entry in self.scraper.scrape_catalog(deduped):
            self.database.insert(entry)
            count += 1
        return count

    def generate_all_meanings(self, force: bool = False) -> int:
        """Generate (and cache) meanings for every catalog entry.

        Returns the number of meanings generated or already cached.
        """
        count = 0
        for entry in self.database.list_all():
            self.meaning_generator.generate(entry, force=force)
            count += 1
        return count
