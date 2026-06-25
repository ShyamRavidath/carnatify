"""SQLite-backed catalog of Carnatic composition lyrics."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from carnatify import config
from carnatify.schemas import LyricsEntry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS compositions (
    composition_id   TEXT PRIMARY KEY,
    composition_name TEXT NOT NULL,
    composer         TEXT NOT NULL,
    raga             TEXT NOT NULL,
    tala             TEXT NOT NULL,
    language         TEXT NOT NULL,
    pallavi          TEXT NOT NULL,
    anupallavi       TEXT NOT NULL DEFAULT '',
    charanam         TEXT NOT NULL DEFAULT '[]',
    source           TEXT NOT NULL DEFAULT ''
);
"""


def slugify(composition_name: str, composer: str) -> str:
    """Build a stable composition_id from name + composer."""
    raw = f"{composition_name}-{composer}"
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return slug


def _row_to_entry(row: sqlite3.Row) -> LyricsEntry:
    return LyricsEntry(
        composition_id=row["composition_id"],
        composition_name=row["composition_name"],
        composer=row["composer"],
        raga=row["raga"],
        tala=row["tala"],
        language=row["language"],
        pallavi=row["pallavi"],
        anupallavi=row["anupallavi"],
        charanam=json.loads(row["charanam"]),
        source=row["source"],
    )


class LyricsDatabase:
    """CRUD access to the compositions catalog."""

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            db_path = config.LYRICS_DB_PATH
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> LyricsDatabase:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def insert(self, entry: LyricsEntry) -> None:
        """Insert or replace a composition entry."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO compositions
                (composition_id, composition_name, composer, raga, tala,
                 language, pallavi, anupallavi, charanam, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.composition_id,
                entry.composition_name,
                entry.composer,
                entry.raga,
                entry.tala,
                entry.language,
                entry.pallavi,
                entry.anupallavi,
                json.dumps(entry.charanam, ensure_ascii=False),
                entry.source,
            ),
        )
        self._conn.commit()

    def get_by_id(self, composition_id: str) -> LyricsEntry | None:
        row = self._conn.execute(
            "SELECT * FROM compositions WHERE composition_id = ?",
            (composition_id,),
        ).fetchone()
        return _row_to_entry(row) if row else None

    def search_by_name(self, name: str) -> list[LyricsEntry]:
        rows = self._conn.execute(
            "SELECT * FROM compositions WHERE composition_name LIKE ? ORDER BY composition_name",
            (f"%{name}%",),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def search_by_raga(self, raga: str) -> list[LyricsEntry]:
        rows = self._conn.execute(
            "SELECT * FROM compositions WHERE raga LIKE ? ORDER BY composition_name",
            (f"%{raga}%",),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def search_by_composer(self, composer: str) -> list[LyricsEntry]:
        rows = self._conn.execute(
            "SELECT * FROM compositions WHERE composer LIKE ? ORDER BY composition_name",
            (f"%{composer}%",),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def list_all(self) -> list[LyricsEntry]:
        rows = self._conn.execute(
            "SELECT * FROM compositions ORDER BY composer, composition_name"
        ).fetchall()
        return [_row_to_entry(r) for r in rows]
