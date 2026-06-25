"""Generate English meanings for composition lyrics via the Claude API.

Meanings are generated fresh from the original-language (public-domain) lyric
text — never scraped from copyrighted translations. Results are cached in a JSON
file keyed by composition_id so a meaning is only generated once.
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic

from carnatify import config
from carnatify.schemas import LyricsEntry, MeaningEntry

MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096

_SYSTEM_PROMPT = (
    "You are a scholar of Carnatic music and the devotional poetry of its "
    "vaggeyakaras (composer-saints). Given the original-language lyrics of a "
    "composition, explain its meaning in clear English for a general audience. "
    "Cover the devotional and philosophical content: who is being addressed, "
    "what is being expressed or sought, and any notable imagery or references. "
    "Write the meaning yourself from the lyrics provided; do not reproduce any "
    "existing published translation. Keep it readable and concise — a few short "
    "paragraphs, no headers."
)


def _build_user_prompt(entry: LyricsEntry) -> str:
    parts = [
        f"Composition: {entry.composition_name}",
        f"Composer: {entry.composer}",
        f"Raga: {entry.raga}",
        f"Tala: {entry.tala}",
        f"Language: {entry.language}",
        "",
        "Lyrics:",
        f"Pallavi:\n{entry.pallavi}",
    ]
    if entry.anupallavi:
        parts.append(f"\nAnupallavi:\n{entry.anupallavi}")
    for i, charanam in enumerate(entry.charanam, start=1):
        parts.append(f"\nCharanam {i}:\n{charanam}")
    parts.append("\nExplain the meaning of these lyrics in English.")
    return "\n".join(parts)


class MeaningGenerator:
    """Claude-backed meaning generator with a JSON file cache."""

    def __init__(
        self,
        cache_path: Path | str | None = None,
        client: anthropic.Anthropic | None = None,
    ):
        self.cache_path = Path(cache_path or config.MEANINGS_CACHE_PATH)
        self._client = client
        self._cache: dict[str, str] = self._load_cache()

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def _load_cache(self) -> dict[str, str]:
        if self.cache_path.exists():
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_cached(self, composition_id: str) -> MeaningEntry | None:
        meaning = self._cache.get(composition_id)
        if meaning is None:
            return None
        return MeaningEntry(composition_id=composition_id, meaning=meaning)

    def generate(self, entry: LyricsEntry, force: bool = False) -> MeaningEntry:
        """Return the meaning for an entry, generating and caching if absent."""
        if not force:
            cached = self.get_cached(entry.composition_id)
            if cached is not None:
                return cached

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(entry)}],
        )
        meaning = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        self._cache[entry.composition_id] = meaning
        self._save_cache()
        return MeaningEntry(composition_id=entry.composition_id, meaning=meaning)
