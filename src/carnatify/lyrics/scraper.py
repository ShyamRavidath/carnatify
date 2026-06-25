"""Scraper for Carnatic composition lyrics (sahityam) from karnatik.com.

Collects only the original-language lyric text (public domain) plus metadata.
Translations are never scraped; English meanings are generated fresh via the
Claude API in meaning_generator.py.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from carnatify.lyrics.database import slugify
from carnatify.schemas import LyricsEntry

BASE_URL = "https://www.karnatik.com"
USER_AGENT = "CarnatifyLyricsBot/0.1 (Carnatic music education; respectful crawler)"
REQUEST_DELAY_SECONDS = 2.0

# Section headers as they appear in karnatik.com lyric pages, mapped to a
# canonical structural label. Order matters: longer/more specific keys first.
_SECTION_PATTERNS: list[tuple[str, str]] = [
    ("anupallavi", "anupallavi"),
    ("pallavi", "pallavi"),
    ("charanam", "charanam"),
    ("caraNam", "charanam"),
    ("samashti charanam", "charanam"),
]

_LANGUAGE_KEYWORDS = {
    "telugu": "Telugu",
    "sanskrit": "Sanskrit",
    "tamil": "Tamil",
    "kannada": "Kannada",
    "malayalam": "Malayalam",
}


@dataclass
class ParsedComposition:
    """Raw fields extracted from a single lyric page, pre-LyricsEntry."""

    composition_name: str
    composer: str
    raga: str
    tala: str
    language: str
    pallavi: str
    anupallavi: str
    charanam: list[str]
    source_url: str


class LyricsScraper:
    """Polite HTTP scraper for karnatik.com sahityam pages."""

    def __init__(self, delay_seconds: float = REQUEST_DELAY_SECONDS):
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _get(self, url: str) -> str:
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        time.sleep(self.delay_seconds)
        return resp.text

    @staticmethod
    def _detect_language(text: str) -> str:
        lowered = text.lower()
        for keyword, label in _LANGUAGE_KEYWORDS.items():
            if keyword in lowered:
                return label
        return "Unknown"

    @staticmethod
    def _extract_metadata_field(text: str, field: str) -> str:
        """Pull a 'Field: value' line out of the page header block."""
        match = re.search(rf"{field}\s*:\s*(.+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_sections(lyric_lines: list[str]) -> tuple[str, str, list[str]]:
        """Split raw lyric lines into pallavi / anupallavi / charanam blocks."""
        sections: dict[str, list[str]] = {
            "pallavi": [],
            "anupallavi": [],
            "charanam": [],
        }
        current: str | None = None
        charanam_blocks: list[list[str]] = []

        for line in lyric_lines:
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            matched_section = None
            for header, canonical in _SECTION_PATTERNS:
                if lowered.startswith(header.lower()):
                    matched_section = canonical
                    break
            if matched_section:
                current = matched_section
                if current == "charanam":
                    charanam_blocks.append([])
                continue
            if current == "charanam":
                charanam_blocks[-1].append(stripped)
            elif current in ("pallavi", "anupallavi"):
                sections[current].append(stripped)

        pallavi = "\n".join(sections["pallavi"])
        anupallavi = "\n".join(sections["anupallavi"])
        charanam = ["\n".join(block) for block in charanam_blocks if block]
        return pallavi, anupallavi, charanam

    def parse_composition_page(self, html: str, source_url: str) -> ParsedComposition:
        """Parse a single karnatik.com lyric page into structured fields."""
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find("div", class_="dynamic") or soup.body or soup
        text = content.get_text("\n")

        name = self._extract_metadata_field(text, "songtitle")
        if not name:
            heading = soup.find(["h1", "h2"])
            name = heading.get_text(strip=True) if heading else "Unknown"

        composer = self._extract_metadata_field(text, "composer")
        raga = self._extract_metadata_field(text, "raagam") or self._extract_metadata_field(
            text, "raga"
        )
        tala = self._extract_metadata_field(text, "taalam") or self._extract_metadata_field(
            text, "tala"
        )
        language = self._extract_metadata_field(text, "language")
        if language:
            language = self._detect_language(language) if self._detect_language(
                language
            ) != "Unknown" else language
        else:
            language = self._detect_language(text)

        lyric_lines = text.splitlines()
        pallavi, anupallavi, charanam = self._parse_sections(lyric_lines)

        return ParsedComposition(
            composition_name=name,
            composer=composer,
            raga=raga,
            tala=tala,
            language=language,
            pallavi=pallavi,
            anupallavi=anupallavi,
            charanam=charanam,
            source_url=source_url,
        )

    def scrape_composition(self, page_path: str) -> LyricsEntry:
        """Fetch and parse one composition page, returning a LyricsEntry."""
        url = page_path if page_path.startswith("http") else f"{BASE_URL}/{page_path.lstrip('/')}"
        html = self._get(url)
        parsed = self.parse_composition_page(html, url)
        return LyricsEntry(
            composition_id=slugify(parsed.composition_name, parsed.composer),
            composition_name=parsed.composition_name,
            composer=parsed.composer,
            raga=parsed.raga,
            tala=parsed.tala,
            language=parsed.language,
            pallavi=parsed.pallavi,
            anupallavi=parsed.anupallavi,
            charanam=parsed.charanam,
            source=parsed.source_url,
        )

    def discover_composition_links(self, index_path: str) -> list[str]:
        """Collect composition-page links from a karnatik.com index page."""
        url = (
            index_path
            if index_path.startswith("http")
            else f"{BASE_URL}/{index_path.lstrip('/')}"
        )
        html = self._get(url)
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if re.search(r"c\d+\.shtml", href) or "/lyrics/" in href:
                links.append(href)
        return links

    def scrape_catalog(self, page_paths: list[str]) -> list[LyricsEntry]:
        """Scrape many composition pages, skipping ones that fail."""
        entries: list[LyricsEntry] = []
        for path in page_paths:
            try:
                entries.append(self.scrape_composition(path))
            except (requests.RequestException, ValueError):
                continue
        return entries


# Seed list of standard compositions across major vaggeyakaras. Each entry is a
# karnatik.com lyric-page path. The catalog builder scrapes these plus any links
# discovered from composer/raga index pages to reach 200+ compositions.
SEED_COMPOSITION_PATHS: list[str] = [
    # Tyagaraja
    "c1001.shtml",
    "c1002.shtml",
    "c1003.shtml",
    # Muthuswami Dikshitar
    "c2001.shtml",
    "c2002.shtml",
    # Syama Sastri
    "c3001.shtml",
    # Purandaradasa
    "c4001.shtml",
]

# karnatik.com index pages to crawl for additional composition links.
SEED_INDEX_PATHS: list[str] = [
    "lyrics/byc_tyagaraja.shtml",
    "lyrics/byc_dikshitar.shtml",
    "lyrics/byc_syamasastri.shtml",
    "lyrics/byc_purandaradasa.shtml",
]
