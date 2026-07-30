#!/usr/bin/env python3
"""Build weakly aligned Saraga audio/lyric segments for ASR fine-tuning.

This is a metadata-only builder. It reads Saraga track metadata and manual
section annotations, resolves exact title+raga matches in the local composition
and lyric registries, and writes:

  data/saraga_asr_trainset.json
  data/saraga_asr_trainset_report.md

It never decodes audio or modifies any source corpus.

Run:
  venv_train/bin/python scripts/build_saraga_asr_trainset.py
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent

# Running a file under scripts/ puts scripts/, rather than the repository root,
# first on sys.path. Import through the package form so this remains runnable
# exactly as documented in the brief.
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from identify_clip import skey
from scripts.detect_workfamily_dupes import (
    PALLAVI_PREFIX_RE,
    REFRAIN_RE,
    SECTION_RE,
    first_pallavi,
    raga_key,
    raga_keys,
)

SARAGA = ROOT / "saraga1.5_carnatic"
REGISTRY = ROOT / "data" / "composition_registry.json"
KARNATIK = ROOT / "data" / "karnatik_lyrics.json"
LINK_OVERRIDES = ROOT / "data" / "karnatik_link_overrides.json"
OUTPUT = ROOT / "data" / "saraga_asr_trainset.json"
REPORT = ROOT / "data" / "saraga_asr_trainset_report.md"

MAX_WINDOW_SEC = 30.0

# Saraga forms observed locally plus common spelling variants. Inclusion is
# deliberately allowlisted: an unknown form is not assumed to carry fixed text.
LYRICAL_FORM_KEYS = {
    skey(value)
    for value in (
        "Bhajan",
        "Devarnama",
        "Javali",
        "Keertana",
        "Keertana (Devara nama)",
        "Kirtana",
        "Kriti",
        "Mangalam",
        "Padam",
        "Shloka",
        "Sloka",
        "Thiruppavai",
        "Thiruppugazh",
        "Tiruppavai",
        "Tiruppugazh",
        "Varnam",
        "Varnam - Tana Varnam",
        "Virutham",
        "Viruttham",
    )
}

SHORT_SECTION_RE = re.compile(
    r"^\s*(p|a|ap|c)\s*(\d*)\s*:\s*(.*?)\s*$",
    re.IGNORECASE,
)
INLINE_SECTION_RE = re.compile(
    r"^\s*(pallavi|anupallavi|cara[nṇ]am|charanam|caranam)"
    r"\s*(\d*)\s*:\s*(.*?)\s*$",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"(\d+)")


@dataclass(frozen=True)
class LyricChoice:
    page: str
    text: str


@dataclass(frozen=True)
class Match:
    row: dict
    lyrics: LyricChoice
    matched_title: str
    resolution: str


@dataclass(frozen=True)
class MatchFailure:
    reason: str
    detail: str


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def display_form(metadata: dict) -> str:
    names = [
        item.get("name", "").strip()
        for item in metadata.get("form", [])
        if isinstance(item, dict) and item.get("name", "").strip()
    ]
    return " / ".join(names) if names else "(none)"


def is_lyrical_form(metadata: dict) -> bool:
    names = [
        item.get("name", "")
        for item in metadata.get("form", [])
        if isinstance(item, dict)
    ]
    return bool(names) and any(skey(name) in LYRICAL_FORM_KEYS for name in names)


def display_raga(metadata: dict) -> str:
    names = [
        item.get("name", "").strip()
        for item in metadata.get("raaga", [])
        if isinstance(item, dict) and item.get("name", "").strip()
    ]
    return " / ".join(names)


def track_raga_keys(metadata: dict) -> set[str]:
    keys = set()
    for item in metadata.get("raaga", []):
        if not isinstance(item, dict):
            continue
        for part in re.split(r"[/,;+]", item.get("name", "")):
            key = raga_key(part)
            if key:
                keys.add(key)
    return keys


def effective_pages(row: dict, overrides: dict[str, list[str]]) -> list[str]:
    return sorted(
        {
            *[page for page in row.get("karnatik_pages", []) if page],
            *[page for page in overrides.get(row["id"], []) if page],
        }
    )


def choose_lyrics(
    row: dict,
    title_key: str,
    overrides: dict[str, list[str]],
    pages_by_id: dict[str, dict],
) -> LyricChoice | None:
    """Choose one local lyric page without guessing across conflicting pages."""
    records = []
    for page in effective_pages(row, overrides):
        record = pages_by_id.get(page)
        if record and record.get("lyrics", "").strip():
            records.append(record)
    if not records:
        return None
    if len(records) == 1:
        record = records[0]
        return LyricChoice(record["page"], record["lyrics"].strip())

    # Prefer a unique page whose title is the title that matched the track.
    exact = [record for record in records if skey(record.get("title", "")) == title_key]
    if len(exact) == 1:
        return LyricChoice(exact[0]["page"], exact[0]["lyrics"].strip())

    # Next prefer a unique page matching any registry title for this row.
    row_keys = {
        skey(value)
        for value in [row.get("canonical", ""), *row.get("aliases", [])]
        if skey(value)
    }
    exact = [
        record for record in records if skey(record.get("title", "")) in row_keys
    ]
    if len(exact) == 1:
        return LyricChoice(exact[0]["page"], exact[0]["lyrics"].strip())

    # Duplicate pages with byte-equivalent normalized lyrics are safe; retain
    # the lexicographically first page so output is deterministic.
    normalized = {
        re.sub(r"\s+", " ", record["lyrics"]).strip(): record["lyrics"].strip()
        for record in records
    }
    if len(normalized) == 1:
        record = sorted(records, key=lambda item: item["page"])[0]
        return LyricChoice(record["page"], record["lyrics"].strip())
    return None


def registry_title_index(registry: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = defaultdict(list)
    for row in registry:
        keys = {
            skey(value)
            for value in [row.get("canonical", ""), *row.get("aliases", [])]
            if skey(value)
        }
        for key in keys:
            index[key].append(row)
    for rows in index.values():
        rows.sort(key=lambda row: row["id"])
    return index


def candidate_titles(metadata: dict) -> list[str]:
    work_titles = [
        item.get("title", "").strip()
        for item in metadata.get("work", [])
        if isinstance(item, dict) and item.get("title", "").strip()
    ]
    track_title = metadata.get("title", "").strip()
    ordered = [*work_titles, *([track_title] if track_title else [])]
    result = []
    seen = set()
    for title in ordered:
        key = skey(title)
        if key and key not in seen:
            result.append(title)
            seen.add(key)
    return result


def match_track(
    metadata: dict,
    title_index: dict[str, list[dict]],
    overrides: dict[str, list[str]],
    pages_by_id: dict[str, dict],
) -> Match | MatchFailure:
    ragas = track_raga_keys(metadata)
    if not ragas:
        return MatchFailure("missing track raga", "no raaga name in metadata")

    titles = candidate_titles(metadata)
    if not titles:
        return MatchFailure("missing track title", "no work title or track title")

    saw_title = False
    saw_raga = False
    saw_page = False
    ambiguity = ""

    for title in titles:
        title_key = skey(title)
        title_rows = title_index.get(title_key, [])
        if not title_rows:
            continue
        saw_title = True

        raga_rows = [row for row in title_rows if raga_keys(row) & ragas]
        if not raga_rows:
            continue
        saw_raga = True

        lyric_rows = []
        for row in raga_rows:
            choice = choose_lyrics(row, title_key, overrides, pages_by_id)
            if choice is not None:
                lyric_rows.append((row, choice))
        if not lyric_rows:
            continue
        saw_page = True

        # An exact canonical-key match is stronger than an alias-only match.
        best_rank = min(
            0 if skey(row.get("canonical", "")) == title_key else 1
            for row, _ in lyric_rows
        )
        best = [
            (row, choice)
            for row, choice in lyric_rows
            if (0 if skey(row.get("canonical", "")) == title_key else 1)
            == best_rank
        ]
        if len(best) == 1:
            row, choice = best[0]
            return Match(row, choice, title, "unique exact title+raga+lyrics")

        # Duplicate registry rows are still safe when they resolve to the same
        # page or exactly the same lyric payload. Choose the lowest stable ID.
        page_ids = {choice.page for _, choice in best}
        lyric_payloads = {
            re.sub(r"\s+", " ", choice.text).strip() for _, choice in best
        }
        if len(page_ids) == 1 or len(lyric_payloads) == 1:
            row, choice = sorted(best, key=lambda item: item[0]["id"])[0]
            return Match(
                row,
                choice,
                title,
                "equivalent duplicate registry rows",
            )
        ambiguity = ", ".join(row["id"] for row, _ in best)

    if ambiguity:
        return MatchFailure(
            "ambiguous lyric-bearing registry match",
            f"conflicting candidates: {ambiguity}",
        )
    if saw_page:
        # Defensive fallback; all currently reachable saw-page cases either
        # return a match or set ambiguity.
        return MatchFailure("ambiguous lyric-bearing registry match", "")
    if saw_raga:
        return MatchFailure(
            "no unambiguous linked lyrics",
            "title+raga matched, but no single usable local lyric page",
        )
    if saw_title:
        return MatchFailure(
            "raga mismatch",
            "title matched registry, but no spelling-equivalent raga matched",
        )
    return MatchFailure("no registry title match", "no exact skey title match")


def normalized_section_name(raw: str) -> str | None:
    key = skey(raw)
    if key.startswith("pallavi"):
        return "pallavi"
    if key.startswith(("anupallavi", "anupallvi")):
        return "anupallavi"
    if key.startswith(("charanam", "caranam", "caranam", "verse")):
        return "charanam"
    if key.startswith(("samashti", "samasti")):
        return "charanam"
    return None


def parse_lyric_sections(lyrics: str) -> dict[str, list[str]]:
    """Parse core sahitya sections using the detector's shared header rules."""
    blocks: dict[str, list[list[str]]] = {
        "pallavi": [],
        "anupallavi": [],
        "charanam": [],
    }
    active: str | None = None
    current: list[str] | None = None

    def start_block(section: str) -> None:
        nonlocal active, current
        active = section
        current = []
        blocks[section].append(current)

    for raw in (lyrics or "").splitlines():
        line = raw.strip()
        if not line:
            continue

        prefix = PALLAVI_PREFIX_RE.match(line)
        if prefix:
            start_block("pallavi")
            tail = line[prefix.end() :].strip()
            if tail:
                current.append(tail)
            continue

        short = SHORT_SECTION_RE.match(line)
        if short:
            token, _, tail = short.groups()
            section = {
                "p": "pallavi",
                "a": "anupallavi",
                "ap": "anupallavi",
                "c": "charanam",
            }[token.lower()]
            start_block(section)
            if tail:
                current.append(tail)
            continue

        inline = INLINE_SECTION_RE.match(line)
        if inline:
            token, _, tail = inline.groups()
            section = normalized_section_name(token)
            if section:
                start_block(section)
                if tail:
                    current.append(tail)
            continue

        heading = SECTION_RE.match(line)
        if heading:
            token = heading.group(1)
            key = skey(token)
            # Madhyamakala is usually a continuation of the current sahitya,
            # while svara headings introduce non-lyrical notation.
            if key.startswith("madhyamak"):
                continue
            if "svar" in key or "swar" in key:
                active = None
                current = None
                continue
            section = normalized_section_name(token)
            if section:
                start_block(section)
            else:
                active = None
                current = None
            continue

        if REFRAIN_RE.match(line):
            continue
        if active and current is not None:
            current.append(line)

    result = {}
    for section, section_blocks in blocks.items():
        cleaned = []
        seen = set()
        for lines in section_blocks:
            text = "\n".join(lines).strip()
            normalized = re.sub(r"\s+", " ", text)
            if text and normalized not in seen:
                cleaned.append(text)
                seen.add(normalized)
        result[section] = cleaned
    if not result["pallavi"]:
        fallback = first_pallavi(lyrics)
        if fallback:
            result["pallavi"] = [fallback.strip()]
    return result


def text_for_annotation(
    label: str, sections: dict[str, list[str]]
) -> tuple[str, str] | None:
    section = normalized_section_name(label)
    if section not in {"pallavi", "anupallavi", "charanam"}:
        return None
    blocks = sections.get(section, [])
    if not blocks:
        return None

    if section != "charanam":
        return "\n".join(blocks), "high"

    number = NUMBER_RE.search(label)
    if number:
        index = int(number.group(1)) - 1
        if 0 <= index < len(blocks):
            return blocks[index], "low"
    # A plural or unnumbered span may cover several verses; concatenation is
    # honest about the weak alignment and the output is explicitly low.
    return "\n".join(blocks), "low"


def parse_annotation_lines(path: Path) -> Iterable[tuple[float, float, str]]:
    """Yield (start, end, label) from Saraga's start/level/duration format."""
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not raw.strip():
            continue
        fields = raw.split("\t")
        if len(fields) < 4:
            raise ValueError(f"{path}:{line_number}: expected 4 tab fields")
        try:
            start = float(fields[0])
            duration = float(fields[2])
        except ValueError as exc:
            raise ValueError(
                f"{path}:{line_number}: invalid start/duration"
            ) from exc
        label = "\t".join(fields[3:]).strip()
        if duration > 0:
            yield start, start + duration, label


def resolve_companion(metadata_path: Path, suffix: str) -> Path:
    exact = metadata_path.with_suffix(suffix)
    if exact.exists():
        return exact
    candidates = sorted(
        path
        for path in metadata_path.parent.glob(f"*{suffix}")
        if ".multitrack-" not in path.name
    )
    if len(candidates) == 1:
        return candidates[0]
    return exact


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def feasibility_read(matched: int, high_minutes: float) -> str:
    if matched < 20 or high_minutes < 60:
        return (
            "**Weak / insufficient as a standalone fine-tuning set.** "
            "The high-confidence aligned material is below a practical one-hour "
            "floor or spans fewer than 20 matched performances. Treat this as a "
            "pipeline proof and expand the lyric links/annotations before GPU use."
        )
    if matched < 50 or high_minutes < 180:
        return (
            "**Promising but small.** The set is suitable for a tightly monitored "
            "pilot or adapter experiment, not yet a robust general-purpose "
            "sung-Carnatic ASR fine-tune. Expand coverage before a large GPU run."
        )
    return (
        "**Worth a controlled fine-tuning pilot.** There is meaningful "
        "high-confidence duration across many matched tracks, though these remain "
        "weak section-level alignments and require held-out validation."
    )


def build_report(
    *,
    total_tracks: int,
    kept_forms: Counter,
    excluded_forms: Counter,
    matched_tracks: int,
    aligned_tracks: int,
    matched_without_sections: int,
    unmatched: list[dict],
    segments: list[dict],
    skipped_section_labels: Counter,
    missing_text_labels: Counter,
    match_resolutions: Counter,
) -> str:
    confidence_counts = Counter(segment["confidence"] for segment in segments)
    confidence_seconds = Counter()
    confidence_tracks: dict[str, set[str]] = defaultdict(set)
    for segment in segments:
        confidence_seconds[segment["confidence"]] += (
            segment["end_sec"] - segment["start_sec"]
        )
        confidence_tracks[segment["confidence"]].add(segment["track_rel_path"])

    high_minutes = confidence_seconds["high"] / 60.0
    low_minutes = confidence_seconds["low"] / 60.0
    kept_total = sum(kept_forms.values())
    excluded_total = sum(excluded_forms.values())
    unmatched_with_sections = sum(item["manual_sections"] for item in unmatched)

    lines = [
        "# Saraga ASR Trainset Feasibility Report",
        "",
        "Generated deterministically from local Saraga metadata, manual section "
        "annotations, the composition registry, lyric corpus, and reviewed link "
        "overrides. No audio was decoded.",
        "",
        "## Feasibility read",
        "",
        feasibility_read(matched_tracks, high_minutes),
        "",
        "These are weak section-level labels: every ≤30-second window inherits "
        "its whole section text. Pallavi/anupallavi windows are marked high; all "
        "charanam/verse windows are marked low.",
        "",
        "## Headline numbers",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Total Saraga tracks walked | {total_tracks} |",
        f"| Kept as fixed-sahitya forms | {kept_total} |",
        f"| Excluded by form | {excluded_total} |",
        f"| Kept tracks matched to local lyrics | {matched_tracks} |",
        f"| Matched tracks with emitted segments | {aligned_tracks} |",
        f"| Matched tracks lacking manual sections | {matched_without_sections} |",
        f"| Unmatched kept tracks | {len(unmatched)} |",
        f"| Unmatched kept tracks with manual sections (highest-value gaps) | "
        f"{unmatched_with_sections} |",
        f"| Total emitted segments | {len(segments)} |",
        "",
        "## Aligned audio by confidence",
        "",
        "| Confidence | Sections represented | Tracks | Segments | Minutes |",
        "|---|---|---:|---:|---:|",
        f"| high | pallavi + anupallavi | "
        f"{len(confidence_tracks['high'])} | {confidence_counts['high']} | "
        f"{high_minutes:.2f} |",
        f"| low | charanam / numbered verse | "
        f"{len(confidence_tracks['low'])} | {confidence_counts['low']} | "
        f"{low_minutes:.2f} |",
        f"| **total** |  | {aligned_tracks} | {len(segments)} | "
        f"**{high_minutes + low_minutes:.2f}** |",
        "",
        "Duration is the sum of emitted window spans, not track duration. Saraga "
        "manual section files store `start`, annotation level, and **duration** "
        "in their first three columns; the builder converts duration to an end "
        "time and clamps it to the track metadata length.",
        "",
        "## Form decisions",
        "",
        "Inclusion is allowlisted to forms that denote fixed sahitya. Empty/unknown "
        "forms, Saraga `Pallavi` (Rāgam–Tānam–Pallavi), and Thillana are excluded.",
        "",
        "| Decision | Form | Tracks |",
        "|---|---|---:|",
    ]
    for form, count in sorted(kept_forms.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| kept | {md(form)} | {count} |")
    for form, count in sorted(
        excluded_forms.items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"| excluded | {md(form)} | {count} |")

    lines.extend(
        [
            "",
            "## Match resolution",
            "",
            "| Resolution | Tracks |",
            "|---|---:|",
        ]
    )
    for resolution, count in sorted(match_resolutions.items()):
        lines.append(f"| {md(resolution)} | {count} |")

    lines.extend(
        [
            "",
            "## Skipped manual section labels",
            "",
            "Instrumental/improvised labels are intentionally not assigned lyric "
            "text. A core lyric label can also be skipped when the selected local "
            "page does not contain that section.",
            "",
            "| Reason | Label | Spans |",
            "|---|---|---:|",
        ]
    )
    for label, count in sorted(
        skipped_section_labels.items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"| non-core / non-lyrical | {md(label)} | {count} |")
    for label, count in sorted(
        missing_text_labels.items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"| lyric section absent | {md(label)} | {count} |")
    if not skipped_section_labels and not missing_text_labels:
        lines.append("| — | — | 0 |")

    lines.extend(
        [
            "",
            "## Unmatched fixed-sahitya tracks",
            "",
            "Tracks with manual section annotations are listed first because filling "
            "their registry/lyric gaps can immediately create training segments. "
            "All other unmatched kept tracks follow, so every skipped lyrical "
            "track is accounted for.",
            "",
            "| Priority | Track | Form | Raga | Work/title tried | Duration min | Reason |",
            "|---|---|---|---|---|---:|---|",
        ]
    )
    if not unmatched:
        lines.append("| — | — | — | — | — | — | none |")
    for item in sorted(
        unmatched,
        key=lambda row: (
            not row["manual_sections"],
            -row["duration_sec"],
            row["track_rel_path"],
        ),
    ):
        priority = "manual sections" if item["manual_sections"] else "no sections"
        tried = "; ".join(item["titles"]) or "(none)"
        reason = item["reason"]
        if item["detail"]:
            reason += f": {item['detail']}"
        lines.append(
            f"| {priority} | {md(item['track_rel_path'])} | "
            f"{md(item['form'])} | {md(item['raga'] or '(none)')} | "
            f"{md(tried)} | {item['duration_sec'] / 60.0:.2f} | {md(reason)} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    registry = read_json(REGISTRY)
    karnatik = read_json(KARNATIK)
    override_doc = read_json(LINK_OVERRIDES) if LINK_OVERRIDES.exists() else {}
    overrides = override_doc.get("links", override_doc)
    pages_by_id = {
        row["page"]: row for row in karnatik if row.get("page")
    }
    title_index = registry_title_index(registry)

    metadata_paths = sorted(SARAGA.rglob("*.json"))
    kept_forms: Counter[str] = Counter()
    excluded_forms: Counter[str] = Counter()
    match_resolutions: Counter[str] = Counter()
    skipped_section_labels: Counter[str] = Counter()
    missing_text_labels: Counter[str] = Counter()
    unmatched = []
    segments = []
    matched_tracks = 0
    matched_without_sections = 0
    aligned_track_paths = set()

    for metadata_path in metadata_paths:
        metadata = read_json(metadata_path)
        form = display_form(metadata)
        if not is_lyrical_form(metadata):
            excluded_forms[form] += 1
            continue
        kept_forms[form] += 1

        sections_path = resolve_companion(metadata_path, ".sections-manual.txt")
        has_sections = sections_path.exists()
        match = match_track(metadata, title_index, overrides, pages_by_id)
        if isinstance(match, MatchFailure):
            unmatched.append(
                {
                    "track_rel_path": rel(metadata_path),
                    "form": form,
                    "raga": display_raga(metadata),
                    "titles": candidate_titles(metadata),
                    "duration_sec": float(metadata.get("length") or 0) / 1000.0,
                    "manual_sections": has_sections,
                    "reason": match.reason,
                    "detail": match.detail,
                }
            )
            continue

        matched_tracks += 1
        match_resolutions[match.resolution] += 1
        if not has_sections:
            matched_without_sections += 1
            continue

        audio_path = resolve_companion(metadata_path, ".mp3")
        if not audio_path.exists():
            raise FileNotFoundError(
                f"manual sections exist but ensemble audio is missing: {metadata_path}"
            )
        lyric_sections = parse_lyric_sections(match.lyrics.text)
        track_end = float(metadata.get("length") or 0) / 1000.0
        raga = display_raga(metadata)
        before = len(segments)

        for start, annotated_end, label in parse_annotation_lines(sections_path):
            mapped = text_for_annotation(label, lyric_sections)
            if mapped is None:
                if normalized_section_name(label) is None:
                    skipped_section_labels[label] += 1
                else:
                    missing_text_labels[label] += 1
                continue
            text, confidence = mapped
            end = min(annotated_end, track_end) if track_end > 0 else annotated_end
            cursor = max(0.0, start)
            if end <= cursor:
                continue
            while cursor < end - 1e-9:
                window_end = min(cursor + MAX_WINDOW_SEC, end)
                segments.append(
                    {
                        "track_rel_path": rel(metadata_path),
                        "audio_rel_path": rel(audio_path),
                        "start_sec": round(cursor, 6),
                        "end_sec": round(window_end, 6),
                        "section_label": label,
                        "text": text,
                        "work_title": match.row["canonical"],
                        "registry_id": match.row["id"],
                        "raga": raga,
                        "form": form,
                        "confidence": confidence,
                    }
                )
                cursor = window_end
        if len(segments) > before:
            aligned_track_paths.add(rel(metadata_path))

    OUTPUT.write_text(
        json.dumps(segments, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = build_report(
        total_tracks=len(metadata_paths),
        kept_forms=kept_forms,
        excluded_forms=excluded_forms,
        matched_tracks=matched_tracks,
        aligned_tracks=len(aligned_track_paths),
        matched_without_sections=matched_without_sections,
        unmatched=unmatched,
        segments=segments,
        skipped_section_labels=skipped_section_labels,
        missing_text_labels=missing_text_labels,
        match_resolutions=match_resolutions,
    )
    REPORT.write_text(report, encoding="utf-8")

    counts = Counter(segment["confidence"] for segment in segments)
    seconds = Counter()
    for segment in segments:
        seconds[segment["confidence"]] += (
            segment["end_sec"] - segment["start_sec"]
        )
    print(
        f"tracks={len(metadata_paths)} kept={sum(kept_forms.values())} "
        f"matched={matched_tracks} aligned={len(aligned_track_paths)} "
        f"unmatched={len(unmatched)}"
    )
    print(
        f"segments: high={counts['high']} ({seconds['high'] / 60.0:.2f} min) "
        f"low={counts['low']} ({seconds['low'] / 60.0:.2f} min)"
    )
    print(f"wrote {rel(OUTPUT)}")
    print(f"wrote {rel(REPORT)}")


if __name__ == "__main__":
    main()
