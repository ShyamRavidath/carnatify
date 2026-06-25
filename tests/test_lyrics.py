"""Tests for the lyrics catalog pipeline."""

from __future__ import annotations

import json

import pytest

from carnatify.lyrics.database import LyricsDatabase, slugify
from carnatify.lyrics.meaning_generator import MeaningGenerator
from carnatify.lyrics.scraper import LyricsScraper
from carnatify.schemas import LyricsEntry, MeaningEntry


@pytest.fixture
def entry() -> LyricsEntry:
    return LyricsEntry(
        composition_id=slugify("Vatapi Ganapatim", "Muthuswami Dikshitar"),
        composition_name="Vatapi Ganapatim",
        composer="Muthuswami Dikshitar",
        raga="Hamsadhwani",
        tala="Adi",
        language="Sanskrit",
        pallavi="vAtApi gaNapatiM bhajE haM",
        anupallavi="bhUtAdi saMsEvita caraNaM",
        charanam=["puraNa cidAnanda...", "vIra vighnESvara..."],
        source="https://www.karnatik.com/c2001.shtml",
    )


@pytest.fixture
def db() -> LyricsDatabase:
    database = LyricsDatabase(db_path=":memory:")
    yield database
    database.close()


def test_slugify_is_stable_and_ascii():
    slug = slugify("Vātāpi Gaṇapatim", "Muthuswami Dikshitar")
    assert slug == "vatapi-ganapatim-muthuswami-dikshitar"
    assert slugify("A B", "C") == slugify("A B", "C")


def test_insert_and_get_by_id(db: LyricsDatabase, entry: LyricsEntry):
    db.insert(entry)
    fetched = db.get_by_id(entry.composition_id)
    assert fetched == entry


def test_charanam_roundtrips_as_list(db: LyricsDatabase, entry: LyricsEntry):
    db.insert(entry)
    fetched = db.get_by_id(entry.composition_id)
    assert fetched.charanam == entry.charanam
    assert isinstance(fetched.charanam, list)


def test_insert_is_idempotent(db: LyricsDatabase, entry: LyricsEntry):
    db.insert(entry)
    db.insert(entry)
    assert len(db.list_all()) == 1


def test_search_by_name(db: LyricsDatabase, entry: LyricsEntry):
    db.insert(entry)
    assert db.search_by_name("Vatapi")[0].composition_id == entry.composition_id
    assert db.search_by_name("nonexistent") == []


def test_search_by_raga(db: LyricsDatabase, entry: LyricsEntry):
    db.insert(entry)
    assert db.search_by_raga("Hamsadhwani")[0].composition_id == entry.composition_id


def test_search_by_composer(db: LyricsDatabase, entry: LyricsEntry):
    db.insert(entry)
    assert db.search_by_composer("Dikshitar")[0].composition_id == entry.composition_id


def test_get_missing_returns_none(db: LyricsDatabase):
    assert db.get_by_id("does-not-exist") is None


def test_list_all_empty(db: LyricsDatabase):
    assert db.list_all() == []


def test_meaning_cache_avoids_regeneration(tmp_path, entry: LyricsEntry):
    cache_path = tmp_path / "meanings.json"

    class _FakeBlock:
        type = "text"
        text = "A devotional invocation of Ganapati."

    class _FakeResponse:
        content = [_FakeBlock()]

    class _FakeMessages:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return _FakeResponse()

    class _FakeClient:
        def __init__(self):
            self.messages = _FakeMessages()

    fake_client = _FakeClient()
    gen = MeaningGenerator(cache_path=cache_path, client=fake_client)

    first = gen.generate(entry)
    assert isinstance(first, MeaningEntry)
    assert first.meaning == "A devotional invocation of Ganapati."
    assert fake_client.messages.calls == 1

    # Second call hits cache — no new API call.
    second = gen.generate(entry)
    assert second.meaning == first.meaning
    assert fake_client.messages.calls == 1

    # Cache persists across instances.
    gen2 = MeaningGenerator(cache_path=cache_path, client=fake_client)
    third = gen2.generate(entry)
    assert third.meaning == first.meaning
    assert fake_client.messages.calls == 1


def test_meaning_cache_file_keyed_by_composition_id(tmp_path, entry: LyricsEntry):
    cache_path = tmp_path / "meanings.json"

    class _FakeBlock:
        type = "text"
        text = "meaning text"

    class _FakeMessages:
        def create(self, **kwargs):
            class _R:
                content = [_FakeBlock()]

            return _R()

    class _FakeClient:
        messages = _FakeMessages()

    gen = MeaningGenerator(cache_path=cache_path, client=_FakeClient())
    gen.generate(entry)

    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    assert entry.composition_id in cached


def test_parse_sections_splits_structure():
    scraper = LyricsScraper()
    lines = [
        "pallavi",
        "vatapi ganapatim bhaje",
        "anupallavi",
        "bhutadi samsevita",
        "charanam",
        "purana chidananda",
        "charanam",
        "vira vighnesvara",
    ]
    pallavi, anupallavi, charanam = scraper._parse_sections(lines)
    assert pallavi == "vatapi ganapatim bhaje"
    assert anupallavi == "bhutadi samsevita"
    assert charanam == ["purana chidananda", "vira vighnesvara"]


def test_detect_language():
    scraper = LyricsScraper()
    assert scraper._detect_language("Language: Sanskrit") == "Sanskrit"
    assert scraper._detect_language("This is in telugu") == "Telugu"
    assert scraper._detect_language("no marker here") == "Unknown"
