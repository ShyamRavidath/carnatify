#!/usr/bin/env python3
"""Generate review-only work-family duplicate candidates for wild truths.

This script never edits the registry or truth manifest. It compares every
registry ID named by the 78 in-catalog wild-manifest entries with all other
registry rows and writes an evidence-ranked review packet:

  data/workfamily_candidates.json

Evidence, strongest first:
  1. an identical effective karnatik page link;
  2. identical/near-identical first pallavi lines;
  3. matching composer+raga with a highly similar title.

A deliberately low-confidence fallback catches lyrics-less/truncated stubs
whose composer is absent but whose raga and title strongly match a fuller row.
Rows with clearly different available pallavis are rejected even when their
titles rhyme. Nothing emitted here is safe to merge without human review.

Run:
  venv_train/bin/python scripts/detect_workfamily_dupes.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data" / "composition_registry.json"
MANIFEST = ROOT / "data" / "wild_truth_manifest.json"
KARNATIK = ROOT / "data" / "karnatik_lyrics.json"
LINK_OVERRIDES = ROOT / "data" / "karnatik_link_overrides.json"
OUTPUT = ROOT / "data" / "workfamily_candidates.json"

PALLAVI_HIGH = 92.0
PALLAVI_REVIEW = 88.0
PALLAVI_DIFFERENT = 85.0
TITLE_MEDIUM = 88.0
TITLE_STUB = 90.0

SECTION_RE = re.compile(
    r"^\s*(pallavi|anupallavi|cara[nṇ]am|charanam|caranam|"
    r"samash?ti.*|madhyamak.*|citta\s?svaram?|chittaswaram?|swaram?)"
    r"\s*\d*\s*:?\s*$",
    re.I,
)
PALLAVI_PREFIX_RE = re.compile(r"^\s*p\s*:\s*", re.I)
REFRAIN_RE = re.compile(r"^\s*(\(|\||\*|note\b)", re.I)

# Only spelling-equivalent raga names belong here. This is not a musical
# similarity map: related/different ragas must remain different.
RAGA_ALIASES = {
    "dwijavanti": "dvijavanti",
    "dvijavanti": "dvijavanti",
    "jujavanti": "dvijavanti",
    "nilambari": "nilambari",
    "nilambri": "nilambari",
    "neelambari": "nilambari",
    "kamavardani": "pantuvarali",
    "kamavardhani": "pantuvarali",
    "pantuvarali": "pantuvarali",
    "pantuvarali": "pantuvarali",
    "sri": "sri",
    "shri": "sri",
    "todi": "todi",
    "kambhoji": "kambhoji",
    "kamboji": "kambhoji",
    "kambodi": "kambhoji",
    "harikambhoji": "harikambhoji",
    "harikamboji": "harikambhoji",
    "harikambodi": "harikambhoji",
    "yadukulakambhoji": "yadukulakambhoji",
    "yadukulakamboji": "yadukulakambhoji",
    "yadukulakambodi": "yadukulakambhoji",
    "mayamalavagaula": "mayamalavagaula",
    "mayamalavagowla": "mayamalavagaula",
    "sindubhairavi": "sindhubhairavi",
    "sindhubhairavi": "sindhubhairavi",
    "anandabairavi": "anandabhairavi",
    "anandhabairavi": "anandabhairavi",
    "anandabhairavi": "anandabhairavi",
    "kadanakutoohalam": "katanakutuhalam",
    "kadanakutuhala": "katanakutuhalam",
    "katanakutoohalam": "katanakutuhalam",
    "katanakutuhalam": "katanakutuhalam",
    "katanakutuhala": "katanakutuhalam",
}


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", plain.lower())


def soft(text: str) -> str:
    text = re.sub(r"\s+", " ", fold(text)).strip()
    for source, target in (
        ("aa", "a"),
        ("ee", "i"),
        ("ii", "i"),
        ("oo", "u"),
        ("uu", "u"),
        ("bh", "b"),
        ("ch", "c"),
        ("dh", "d"),
        ("gh", "g"),
        ("jh", "j"),
        ("kh", "k"),
        ("ph", "p"),
        ("sh", "s"),
        ("th", "t"),
        ("w", "v"),
        ("z", "s"),
    ):
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def compact(text: str) -> str:
    return soft(text).replace(" ", "")


def composer_keys(row: dict) -> set[str]:
    keys = set()
    for composer in row.get("composers", []):
        key = compact(composer)
        if key:
            keys.add(key)
    return keys


def raga_key(value: str) -> str:
    value = re.sub(r"\([^)]*\)", " ", value or "")
    key = compact(value)
    return RAGA_ALIASES.get(key, key)


def raga_keys(row: dict) -> set[str]:
    keys = set()
    for value in row.get("ragas", []):
        for part in re.split(r"[/,;+]", value):
            key = raga_key(part)
            if key:
                keys.add(key)
    return keys


def first_pallavi(lyrics: str) -> str:
    """Return the first real pallavi line, falling back to first lyric line."""
    fallback = ""
    section = ""
    for raw in (lyrics or "").splitlines():
        line = raw.strip()
        if not line or REFRAIN_RE.match(line):
            continue
        prefix = PALLAVI_PREFIX_RE.match(line)
        if prefix:
            line = line[prefix.end() :].strip()
            if line:
                return line
            section = "pallavi"
            continue
        heading = SECTION_RE.match(line)
        if heading:
            section = heading.group(1).lower()
            continue
        if not fallback and len(compact(line)) >= 6:
            fallback = line
        if section == "pallavi" and len(compact(line)) >= 6:
            return line
    return fallback


def title_similarity(left: dict, right: dict) -> tuple[float, str, str, bool]:
    """Best strict similarity; containment is explicit, not token-set fuzzy."""
    best = (0.0, left["canonical"], right["canonical"], False)
    left_titles = [left["canonical"], *left.get("aliases", [])]
    right_titles = [right["canonical"], *right.get("aliases", [])]
    for a in left_titles:
        ak = soft(a)
        if not ak:
            continue
        for b in right_titles:
            bk = soft(b)
            if not bk:
                continue
            ac, bc = ak.replace(" ", ""), bk.replace(" ", "")
            shorter, longer = sorted((ac, bc), key=len)
            containment = len(shorter) >= 8 and shorter in longer
            score = 100.0 if containment else float(fuzz.ratio(ak, bk))
            if score > best[0]:
                best = (float(score), a, b, containment)
    return best


def best_pallavi(
    left_pages: set[str],
    right_pages: set[str],
    page_pallavi: dict[str, str],
) -> tuple[float | None, str, str]:
    best: tuple[float | None, str, str] = (None, "", "")
    for left_page in sorted(left_pages):
        left = page_pallavi.get(left_page, "")
        if not left:
            continue
        for right_page in sorted(right_pages):
            right = page_pallavi.get(right_page, "")
            if not right:
                continue
            score = float(fuzz.ratio(soft(left), soft(right)))
            if best[0] is None or score > best[0]:
                best = (score, left, right)
    return best


def is_stub(row: dict, effective_pages: set[str]) -> bool:
    return not effective_pages or not row.get("has_lyrics")


def candidate_for(
    truth: dict,
    candidate: dict,
    truth_pages: set[str],
    candidate_pages: set[str],
    page_pallavi: dict[str, str],
    expected_ragas: set[str],
    already_in_truth_set: bool,
) -> dict | None:
    shared_pages = sorted(truth_pages & candidate_pages)
    pallavi_ratio, truth_pal, candidate_pal = best_pallavi(
        truth_pages, candidate_pages, page_pallavi
    )
    title_ratio, truth_title, candidate_title, title_containment = (
        title_similarity(truth, candidate)
    )
    composers = composer_keys(truth) & composer_keys(candidate)
    ragas = raga_keys(truth) & raga_keys(candidate)
    candidate_expected_raga = bool(raga_keys(candidate) & expected_ragas)
    stub_pair = is_stub(truth, truth_pages) or is_stub(candidate, candidate_pages)

    # A clearly different available pallavi vetoes title-family guesses. An
    # identical explicit page remains conclusive even if parsing found a noisy
    # fallback line.
    different_pallavi = (
        not shared_pages
        and pallavi_ratio is not None
        and pallavi_ratio < PALLAVI_DIFFERENT
    )

    evidence: list[str] = []
    confidence = ""
    if shared_pages:
        evidence.append("shared_page:" + ",".join(shared_pages))
        confidence = "high"

    if (
        pallavi_ratio is not None
        and pallavi_ratio >= PALLAVI_REVIEW
        and (candidate_expected_raga or already_in_truth_set)
    ):
        evidence.append(f"pallavi_ratio:{pallavi_ratio:.1f}")
        if pallavi_ratio >= PALLAVI_HIGH:
            confidence = "high"
        elif not confidence:
            confidence = "medium"

    if (
        composers
        and ragas
        and candidate_expected_raga
        and title_ratio >= TITLE_MEDIUM
        and title_containment
        and not different_pallavi
    ):
        evidence.append(
            "title+composer+raga:"
            f"title={title_ratio:.1f};"
            f"composer={','.join(sorted(composers))};"
            f"raga={','.join(sorted(ragas))}"
        )
        if not confidence:
            confidence = "medium"

    # Lyrics-less stubs often lack composer metadata, so the requested medium
    # rule cannot see them. Retain only a narrow, explicitly low-confidence
    # fallback: same raga, very high title similarity, at least one stub, and
    # no contradictory pallavi.
    if (
        stub_pair
        and ragas
        and candidate_expected_raga
        and title_ratio >= TITLE_STUB
        and title_containment
        and not different_pallavi
        and not any(item.startswith("title+composer+raga:") for item in evidence)
    ):
        evidence.append(
            "title+raga_stub:"
            f"title={title_ratio:.1f};raga={','.join(sorted(ragas))}"
        )
        if not confidence:
            confidence = "low"

    if not evidence:
        return None

    snippet = ""
    if truth_pal or candidate_pal:
        snippet = f"truth: {truth_pal[:90]} | candidate: {candidate_pal[:90]}"
    title_note = ""
    if title_ratio:
        title_note = (
            f"title_pair:{title_ratio:.1f}:"
            f"{truth_title[:60]} <> {candidate_title[:60]}"
        )
        evidence.append(title_note)

    return {
        "candidate_id": candidate["id"],
        "canonical": candidate["canonical"],
        "raga": candidate.get("ragas", []),
        "composer": candidate.get("composers", []),
        "evidence": evidence,
        "confidence": confidence,
        "pallavi_snippet": snippet,
    }


def confidence_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}[value]


def main() -> None:
    registry = json.loads(REGISTRY.read_text())
    manifest = json.loads(MANIFEST.read_text())
    karnatik = json.loads(KARNATIK.read_text())
    overrides_doc = (
        json.loads(LINK_OVERRIDES.read_text()) if LINK_OVERRIDES.exists() else {}
    )
    link_overrides = overrides_doc.get("links", overrides_doc)

    by_id = {row["id"]: row for row in registry}
    page_records = {row["page"]: row for row in karnatik if row.get("page")}
    page_pallavi = {
        page: first_pallavi(row.get("lyrics", ""))
        for page, row in page_records.items()
    }

    effective_pages: dict[str, set[str]] = {}
    for row in registry:
        pages = set(row.get("karnatik_pages", []))
        pages.update(link_overrides.get(row["id"], []))
        effective_pages[row["id"]] = pages

    truth_clips: dict[str, list[str]] = defaultdict(list)
    truth_expected_ragas: dict[str, set[str]] = defaultdict(set)
    family_members: dict[str, set[str]] = defaultdict(set)
    empty_truth_clips = []
    in_catalog_entries = 0
    for clip, entry in manifest.items():
        if entry.get("ooc"):
            continue
        in_catalog_entries += 1
        truth_ids = entry.get("truth_ids", [])
        if not truth_ids:
            empty_truth_clips.append(clip)
            continue
        family = set(truth_ids)
        clip_raga = raga_key(clip.rsplit("__", 1)[-1])
        for truth_id in truth_ids:
            truth_clips[truth_id].append(clip)
            family_members[truth_id].update(family)
            if clip_raga:
                truth_expected_ragas[truth_id].add(clip_raga)

    unknown = sorted(set(truth_clips) - set(by_id))
    if unknown:
        raise SystemExit(f"unknown truth ids: {unknown}")

    candidates_by_truth: dict[str, list[dict]] = {}
    pair_rows: dict[tuple[str, str], dict] = {}
    counts = {"high": 0, "medium": 0, "low": 0}
    new_high_truth_ids = set()

    for truth_id in sorted(truth_clips):
        truth = by_id[truth_id]
        rows = []
        for candidate in registry:
            if candidate["id"] == truth_id:
                continue
            already_known = candidate["id"] in family_members[truth_id]
            result = candidate_for(
                truth,
                candidate,
                effective_pages[truth_id],
                effective_pages[candidate["id"]],
                page_pallavi,
                truth_expected_ragas[truth_id],
                already_known,
            )
            if result is None:
                continue
            result["already_in_truth_set"] = already_known
            rows.append(result)

            pair = tuple(sorted((truth_id, candidate["id"])))
            existing = pair_rows.get(pair)
            display = {
                "truth_id": truth_id,
                "truth": truth["canonical"],
                **result,
            }
            if (
                existing is None
                or confidence_rank(result["confidence"])
                < confidence_rank(existing["confidence"])
            ):
                pair_rows[pair] = display

        rows.sort(
            key=lambda row: (
                confidence_rank(row["confidence"]),
                row["already_in_truth_set"],
                row["candidate_id"],
            )
        )
        candidates_by_truth[truth_id] = rows

    for row in pair_rows.values():
        counts[row["confidence"]] += 1
        if row["confidence"] == "high" and not row["already_in_truth_set"]:
            new_high_truth_ids.add(row["truth_id"])

    output = {
        "meta": {
            "scope": "wild truth registry IDs only; review candidates, never auto-merge",
            "in_catalog_manifest_entries": in_catalog_entries,
            "empty_truth_clips": sorted(empty_truth_clips),
            "unique_truth_ids_scanned": len(truth_clips),
            "thresholds": {
                "pallavi_high": PALLAVI_HIGH,
                "pallavi_review": PALLAVI_REVIEW,
                "different_pallavi_veto_below": PALLAVI_DIFFERENT,
                "title_composer_raga": TITLE_MEDIUM,
                "title_raga_stub_low": TITLE_STUB,
            },
            "unique_pair_counts": counts,
            "new_high_confidence_truth_ids": sorted(new_high_truth_ids),
        },
        "candidates_by_truth_id": candidates_by_truth,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")

    table = sorted(
        pair_rows.values(),
        key=lambda row: (
            confidence_rank(row["confidence"]),
            row["already_in_truth_set"],
            row["truth_id"],
            row["candidate_id"],
        ),
    )
    print(
        "confidence  truth id   truth                         candidate  "
        "candidate work                  known  evidence"
    )
    print("-" * 132)
    for row in table:
        evidence = "; ".join(
            item for item in row["evidence"] if not item.startswith("title_pair:")
        )
        print(
            f"{row['confidence']:<10}  {row['truth_id']:<10} "
            f"{row['truth'][:29]:<29}  {row['candidate_id']:<10} "
            f"{row['canonical'][:30]:<30}  "
            f"{'yes' if row['already_in_truth_set'] else 'no ':<5}  "
            f"{evidence}"
        )
    print()
    print(
        f"unique pairs: high={counts['high']} medium={counts['medium']} "
        f"low={counts['low']} | truth ids scanned={len(truth_clips)} | "
        f"wrote {OUTPUT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
