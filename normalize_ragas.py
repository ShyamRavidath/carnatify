"""Collapse the raw scraped raga spellings onto canonical dataset labels.

The scraped corpus (data/scraped_compositions.json) uses informal ASCII
transliterations — ``tODi``, ``kalyANi``, ``shankarabharanam`` — with ~958
distinct spellings. This maps each onto the canonical, diacritical raga names
the classifier was actually trained on:

  * compmusic_raga (Carnatic) — 40 ragas, == the raga_label_encoder classes
  * saraga_carnatic            — the raaga vocabulary in its track metadata

Matching strategy, per spelling:
  1. a hand-coded alias dict for common variants (highest priority), then
  2. difflib.get_close_matches (cutoff 0.6) on a diacritic-stripped "fold" of
     both the spelling and every canonical name.
Unmatched spellings map to None.

Outputs (no models retrained, lyrics DB untouched):
  * data/scraped_compositions.json — each record gains a ``raga_canonical`` field
  * data/raga_aliases.json         — {raw_spelling: canonical_or_null}, hand-editable
"""

from __future__ import annotations

import difflib
import json
import sys
import unicodedata
from pathlib import Path

_ROOT = Path(__file__).parent
_SCRAPED = _ROOT / "data" / "scraped_compositions.json"
_ALIASES_OUT = _ROOT / "data" / "raga_aliases.json"
_COMPMUSIC_MAP = _ROOT / "RagaDataset" / "Carnatic" / "_info_" / "ragaId_to_ragaName_mapping.json"
_COMPMUSIC_PMR = _ROOT / "RagaDataset" / "Carnatic" / "_info_" / "path_mbid_ragaid.json"

FUZZY_CUTOFF = 0.6

# Hand-curated aliases, keyed by folded ASCII -> canonical display name.
# Difflib alone is unreliable for Carnatic raga transliterations: genuine
# spelling variants and *different* ragas overlap across the whole 0.6–0.9
# similarity band (e.g. "saraswati"~"saramati"=0.82, "hamsanadam"~"hamsanandi"
# =0.80 are both wrong). So every spelling occurring >= 4 times in the corpus is
# pinned here by hand. Canonical names use the compmusic/label-encoder spelling
# where one exists. Less-frequent spellings fall back to fuzzy matching.
_CANONICAL_ALIASES: dict[str, str] = {
    "todi": "Tōḍi",
    "kalyani": "Kalyāṇi",
    "shankarabharanam": "Śankarābharaṇaṁ",
    "sankarabaranam": "Śankarābharaṇaṁ",
    "sankarabharanam": "Śankarābharaṇaṁ",
    "kambhoji": "Kāṁbhōji",
    "kamboji": "Kāṁbhōji",
    "kaambhoji": "Kāṁbhōji",
    "pantuvarali": "Kāmavardani",
    "subhapantuvarali": "Kāmavardani",
    "subapantuvarali": "Kāmavardani",
    "kamavardani": "Kāmavardani",
    "hamsadwani": "Hamsadhvāni",
    "hamsadhwani": "Hamsadhvāni",
    "hamsdwani": "Hamsadhvāni",
    "mohanam": "Mōhanaṁ",
    "abhogi": "Ābhōgī",
    "abogi": "Ābhōgī",
    "begada": "Bēgaḍa",
    "reetigowla": "Rītigauḷa",
    "reethigowla": "Rītigauḷa",
    "ritigaula": "Rītigauḷa",
    "reetigaula": "Rītigauḷa",
    "atana": "Aṭāna",
    "athana": "Aṭāna",
    "saveri": "Sāvēri",
    "kapi": "Kāpi",
    "nata": "Nāṭa",
    "natta": "Nāṭa",
    "nattai": "Nāṭa",
    "natakurinji": "Nāṭakurinji",
    "natakurunji": "Nāṭakurinji",
    "natakuranji": "Nāṭakurinji",
    "kurunji": "Nāṭakurinji",
    "kurinji": "Nāṭakurinji",
    "varali": "Varāḷi",
    "dhanyasi": "Dhanyāsi",
    "sri": "Śrī",
    "sree": "Śrī",
    "sriranjani": "Śrīranjani",
    "sreeranjani": "Śrīranjani",
    "srrianjani": "Śrīranjani",
    "shanmukapriya": "Ṣanmukhapriya",
    "shanmukhapriya": "Ṣanmukhapriya",
    "shanmugapriya": "Ṣanmukhapriya",
    "shanmughapriya": "Ṣanmukhapriya",
    "anandabhairavi": "Ānandabhairavi",
    "harikambhoji": "Harikāmbhōji",
    "harikambodi": "Harikāmbhōji",
    "harikambhodi": "Harikāmbhōji",
    "karaharapriya": "Karaharapriya",
    "mayamalavagowla": "Māyāmāḷavagauḷa",
    "poorvikalyani": "Pūrvīkaḷyāṇi",
    "purvikalyani": "Pūrvīkaḷyāṇi",
    "poorvaikalyani": "Pūrvīkaḷyāṇi",
    "neelambari": "Nīlāṁbari",
    "suruti": "Suraṭi",
    "chakravagam": "Cakravākaṁ",
    "chakravakam": "Cakravākaṁ",
    "poornachandrika": "Pūrṇacandrika",
    "purnachandrika": "Pūrṇacandrika",
    "kedaragowla": "Kēdāragauḷa",
    "kedaragaula": "Kēdāragauḷa",
    "senjuruti": "Sencuruṭṭi",
    "cenjuruti": "Sencuruṭṭi",
    "senjurutti": "Sencuruṭṭi",
    "senchuruti": "Sencuruṭṭi",
    "dwijavanti": "Dvijāvanti",
    "dvijavanti": "Dvijāvanti",
    "hindolam": "Hindōḷaṁ",
    "madhyamavati": "Madhyamāvati",
    "madyamavati": "Madhyamāvati",
    "mukhari": "Mukhāri",
    "kanada": "Kānaḍa",
    "kannada": "Kānaḍa",
    "bilahari": "Bilahari",
    "kamas": "Kamās",
    "khamas": "Kamās",
    "gaula": "Gauḷa",
    "gowla": "Gauḷa",
    "des": "Dēś",
    "desh": "Dēś",
    "devagandhari": "Dēvagāndhāri",
    "kathanakutuhalam": "Kathanakutūhalaṁ",
    "kadanakutoohalam": "Kathanakutūhalaṁ",
    "behag": "Behāg",
    "saurashtram": "Saurāṣtraṁ",
    "sowrashtram": "Saurāṣtraṁ",
    "hameerkalyani": "Hamīr kaḷyaṇi",
    "hamirkalyani": "Hamīr kaḷyaṇi",
    "bageswari": "Bāgēśrī",
    "bagesri": "Bāgēśrī",
    "simhendramadyam": "Simhēndra madhyamaṁ",
    "simhendramadhyamam": "Simhēndra madhyamaṁ",
    "gambeeranata": "Gaṁbhīra nāṭa",
    "gambheeranata": "Gaṁbhīra nāṭa",
    "gambeeranattai": "Gaṁbhīra nāṭa",
    "kuntalavarali": "Kuntalavarāḷi",
    "ragamalika": "Rāgamālika",
    "navaragamalika": "Rāgamālika",
}

# Spellings that fuzzy-match a canonical name but are actually *distinct* ragas
# with no entry in the compmusic/saraga vocabulary — forced to None so they are
# not silently mislabelled.
_FORCE_NONE: set[str] = {
    "arabhi", "aarabhi", "arabi", "darbar", "darbari", "keeravani", "keeravaani",
    "kiravani", "abheri", "paras", "nayaki", "revati", "valaji", "manji",
    "hamsanadam", "jayamanohari", "eesamanohari", "gowrimanohari",
    "kamalamanohari", "mohanakalyani", "navarasakannada", "bhairavam",
    "bhavapriya", "dharmavati", "malavi", "saraswati", "sivaranjani",
    "veeravasantam", "veeravasantham", "kalyanavasantam", "natabhairavi",
    "kannadagowla", "kannadagaula", "devamanohari", "ramapriya", "sivapriya",
    "sindhunamakriya",
}

HAND_ALIASES: dict[str, str | None] = {
    **_CANONICAL_ALIASES,
    **{k: None for k in _FORCE_NONE},
}


def fold(name: str) -> str:
    """Diacritic-stripped, lowercase, alphanumeric-only key for matching."""
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return "".join(c for c in stripped.lower() if c.isalnum())


def load_compmusic_carnatic() -> list[str]:
    """The 40 Carnatic ragas in compmusic_raga (== classifier label set)."""
    id2name = json.loads(_COMPMUSIC_MAP.read_text())
    pmr = json.loads(_COMPMUSIC_PMR.read_text())
    carnatic_ids = {v["ragaid"] for v in pmr.values()}
    return sorted({id2name[i] for i in carnatic_ids if i in id2name})


def load_saraga_ragas() -> list[str]:
    """Unique raga names from the local saraga_carnatic metadata."""
    import mirdata

    saraga = mirdata.initialize("saraga_carnatic", data_home=str(_ROOT))
    names: set[str] = set()
    for tid in saraga.track_ids:
        meta = saraga.track(tid).metadata or {}
        for r in meta.get("raaga") or []:
            n = r.get("name") or r.get("common_name")
            if n:
                names.add(n.strip())
    return sorted(names)


def build_fold_index(canonicals: list[str]) -> dict[str, str]:
    """Map folded-key -> canonical display name.

    compmusic names are inserted first so they win ties (keeping canonical
    output aligned with the classifier's labels). Slash compounds like
    ``Kāmavardani/Pantuvarāḷi`` also register each part as its own key.
    """
    index: dict[str, str] = {}
    for name in canonicals:
        keys = [name]
        if "/" in name:
            keys += [p.strip() for p in name.split("/")]
        for k in keys:
            fk = fold(k)
            if fk and fk not in index:
                index[fk] = name
    return index


def resolve(spelling: str, fold_index: dict[str, str], fold_keys: list[str]) -> str | None:
    """Canonical name for one raw spelling, or None."""
    fk = fold(spelling)
    if not fk:
        return None
    # 1. hand alias
    if fk in HAND_ALIASES:
        return HAND_ALIASES[fk]
    # 2. exact fold hit against the canonical vocabulary
    if fk in fold_index:
        return fold_index[fk]
    # 3. fuzzy match on folded keys
    match = difflib.get_close_matches(fk, fold_keys, n=1, cutoff=FUZZY_CUTOFF)
    return fold_index[match[0]] if match else None


def main() -> None:
    if not _SCRAPED.exists():
        sys.exit(f"Missing {_SCRAPED} — run scrape_concerts.py first.")

    records = json.loads(_SCRAPED.read_text())

    compmusic = load_compmusic_carnatic()
    saraga = load_saraga_ragas()
    # compmusic first → its spellings win ties in the fold index.
    canonicals: list[str] = compmusic + [r for r in saraga if r not in compmusic]
    fold_index = build_fold_index(canonicals)
    fold_keys = list(fold_index.keys())

    print(f"Canonical vocabulary: {len(compmusic)} compmusic + "
          f"{len(saraga)} saraga -> {len(set(canonicals))} unique names\n")

    # One entry per distinct raw spelling.
    raw_spellings = sorted({(r.get("raga") or "").strip() for r in records if r.get("raga")})
    alias_map: dict[str, str | None] = {}
    for sp in raw_spellings:
        alias_map[sp] = resolve(sp, fold_index, fold_keys)

    # Enrich records.
    for r in records:
        raga = (r.get("raga") or "").strip()
        r["raga_canonical"] = alias_map.get(raga)

    _SCRAPED.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    _ALIASES_OUT.write_text(json.dumps(alias_map, ensure_ascii=False, indent=2, sort_keys=True))

    mapped_spellings = sum(1 for v in alias_map.values() if v)
    records_with_canon = sum(1 for r in records if r.get("raga_canonical"))
    unique_canon = len({v for v in alias_map.values() if v})

    print("── Summary ─────────────────────────────")
    print(f"  raw spellings mapped     : {mapped_spellings}/{len(raw_spellings)}"
          f"  ({100 * mapped_spellings / len(raw_spellings):.1f}%)")
    print(f"  records with canonical   : {records_with_canon}/{len(records)}"
          f"  ({100 * records_with_canon / len(records):.1f}%)")
    print(f"  unique canonical ragas   : {unique_canon}")
    print(f"  saved -> {_SCRAPED.name}, {_ALIASES_OUT.name}")


if __name__ == "__main__":
    main()
