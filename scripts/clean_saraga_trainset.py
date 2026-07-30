#!/usr/bin/env python3
"""Clean lyric TARGETS in the Saraga ASR trainset for fine-tuning.

Codex's `data/saraga_asr_trainset.json` carries raw karnatik lyric text. ~12%
of segments have notation markup bleeding in (tala bar markers `|`/`||`,
syllable-continuation hyphens, and interleaved swaram / section-header lines).
Those would teach the ASR junk tokens, so we normalize the target text here and
quarantine anything still notation-heavy after cleaning.

Read-only on the raw trainset; writes `data/saraga_asr_trainset_clean.json`
with the same schema plus `text_raw` (original) and `notation_suspect` (bool).
Training should drop `notation_suspect` segments.

Run: venv_train/bin/python scripts/clean_saraga_trainset.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "saraga_asr_trainset.json"
OUT = ROOT / "data" / "saraga_asr_trainset_clean.json"

# Structural / notation header lines that are labels, not sung sahitya.
HEADER_RE = re.compile(
    r"^\s*(pallavi|anupallavi|cara[nṇ]am|charanam|caranam|madhyama\w*|"
    r"ci?t+ai?\s*swaram?|chittai\s*swaram?|muk?t?h?ayi\s*swaram?|"
    r"swaram?|swara|solkattu|jati)\s*\d*\s*:?\s*$",
    re.I,
)
SOLFA = set("srgmpdnSRGMPDN")


def is_swaram_line(line: str) -> bool:
    """A line dominated by single-letter solfa tokens (s r g m p d n, commas)."""
    toks = [t for t in re.split(r"[\s,]+", line) if t]
    if not toks:
        return False
    solfa_like = sum(
        1 for t in toks if len(t) <= 3 and all(c in SOLFA for c in t if c.isalpha())
        and any(c.isalpha() for c in t)
    )
    return solfa_like / len(toks) >= 0.6


def clean_text(raw: str) -> tuple[str, bool]:
    """Return (cleaned_text, notation_suspect)."""
    kept = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line or HEADER_RE.match(line) or is_swaram_line(line):
            continue
        kept.append(line)
    text = " ".join(kept)
    text = text.replace("||", " ").replace("|", " ")          # tala bars
    text = re.sub(r"-\s+", "", text)                           # fuse syllables
    text = text.replace("(", " ").replace(")", " ")           # keep inner words
    text = re.sub(r"\b\d+\b", " ", text)                       # drop bare numbers
    text = re.sub(r"[*•]", " ", text)
    # Strip structural label words that survive as inline residue (a section
    # header fused onto the following sahitya line, e.g. "... cittai Swaram
    # Saahityam ..."). These are never sung sahitya.
    text = re.sub(
        r"\b(ci?t+ai?|chittai|muk?t?h?ayi|madhyamakala|"
        r"sa+hityam?|swaram?|swara)\b",
        " ",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s+", " ", text).strip()

    # After cleaning, flag anything still notation-heavy or too short to learn.
    toks = text.split()
    if not toks:
        return text, True
    short_solfa = sum(
        1 for t in toks
        if len(t) <= 2 and all(c in SOLFA for c in t.lower() if c.isalpha())
    )
    suspect = (len(text) < 6) or (short_solfa / len(toks) >= 0.3)
    return text, suspect


def main() -> None:
    segs = json.loads(RAW.read_text())
    out = []
    n_changed = n_suspect = 0
    for s in segs:
        cleaned, suspect = clean_text(s.get("text", ""))
        row = dict(s)
        row["text_raw"] = s.get("text", "")
        row["text"] = cleaned
        row["notation_suspect"] = suspect
        out.append(row)
        n_changed += cleaned != (s.get("text") or "").strip()
        n_suspect += suspect
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")

    usable = [r for r in out if not r["notation_suspect"]]
    hi = [r for r in usable if r["confidence"] == "high"]
    print(f"segments: {len(out)}  changed: {n_changed}  "
          f"notation_suspect (quarantined): {n_suspect}")
    print(f"usable after quarantine: {len(usable)}  (high-confidence: {len(hi)})")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
