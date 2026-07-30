#!/usr/bin/env python3
"""Score an EXTERNAL transcript json (e.g. the fine-tuned pilot) through the
matcher, and report top-1/top-5 + the precision/coverage curve — the go/no-go
for the sung-Carnatic ASR fine-tune.

Input json: {clip_filename: transcript_text}. Keys may carry extensions and
'__OOC'; they are normalized to wild-manifest stem keys. Each transcript is fed
to `assess_variants` as a single variant, exactly like a cache row, so this
measures what these transcripts would do IN the real matcher.

Compare the printed numbers against the stock-whisper baseline (8/78 top-1,
17% precision @ 44% coverage). Success = the curve moves up.

Run: venv_train/bin/python scripts/score_external_transcripts.py transcripts_pilot.json
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import identify_clip as ic  # noqa: E402


def norm_key(name: str) -> tuple[str, bool]:
    """filename -> (stem_key, is_ooc), matching wild_truth manifest keys."""
    stem = name
    for ext in (".m4a", ".mp3", ".wav", ".flac"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    stem = unicodedata.normalize("NFC", stem)
    is_ooc = stem.endswith("__OOC")
    if is_ooc:
        stem = stem[: -len("__OOC")]
    return stem, is_ooc


def line(label: str, correct: int, answered: int, total: int) -> str:
    prec = (100.0 * correct / answered) if answered else 0.0
    cov = 100.0 * answered / total if total else 0.0
    flag = "  <-- >=85%" if prec >= 85.0 and answered else ""
    return (f"  {label:<26} precision {correct:>2}/{answered:<2} = {prec:5.1f}%"
            f"   coverage {answered:>2}/{total} = {cov:4.1f}%{flag}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: score_external_transcripts.py <transcripts.json>")
    trans = json.loads(Path(sys.argv[1]).read_text())
    targets, lyr = ic.load_targets()
    wild = json.loads(ic.WILD_TRUTH.read_text())
    wild = {unicodedata.normalize("NFC", k): v for k, v in wild.items()}

    records = []
    for name, text in trans.items():
        stem, is_ooc = norm_key(name)
        res = ic.assess_variants({"pilot": text or ""}, targets, lyr)
        comps = res["compositions"]
        answered = res["composition_confidence"] != "none" and bool(comps)
        top = comps[0]["score"] if comps else 0.0
        if is_ooc:
            correct1 = correct5 = False
        else:
            truth = set(wild.get(stem, {}).get("truth_ids", []))
            ids = [c.get("id") for c in comps]
            correct1 = bool(ids) and ids[0] in truth
            correct5 = any(i in truth for i in ids)
        records.append({"stem": stem, "ooc": is_ooc, "answered": answered,
                        "tier": res["composition_confidence"], "top": top,
                        "c1": correct1, "c5": correct5})

    incat = [r for r in records if not r["ooc"]]
    n = len(incat)
    total = len(records)
    c1 = sum(r["c1"] for r in incat)
    c5 = sum(r["c5"] for r in incat)
    answered_all = [r for r in records if r["answered"]]
    ooc_bluff = sum(1 for r in records if r["ooc"] and r["answered"])
    prec = 100.0 * c1 / len(answered_all) if answered_all else 0.0
    cov = 100.0 * len(answered_all) / total if total else 0.0

    print(f"\n===== external transcripts: {sys.argv[1]} =====")
    print(f"clips {total} ({n} in-catalog, {total - n} OOC)")
    print(f"composition top-1 {c1}/{n}   top-5 {c5}/{n}")
    print(f"OOC bluffs {ooc_bluff}/{total - n}")
    print(f"precision@coverage: {c1}/{len(answered_all)} correct "
          f"({prec:.0f}% precision at {cov:.0f}% coverage)")
    print("baseline (stock whisper): 8/78 top-1, 21/78 top-5, 17% @ 44%\n")

    print("By confidence tier (cumulative):")
    for label, keep in (("high", {"high"}), ("high+medium", {"high", "medium"}),
                        ("all answered", {"high", "medium", "low"})):
        ans = [r for r in records if r["answered"] and r["tier"] in keep]
        cor = sum(1 for r in ans if r["c1"])
        print(line(label, cor, len(ans), total))

    print("\nCorrect top-1 clips:")
    for r in sorted(incat, key=lambda r: -r["top"]):
        if r["c1"]:
            print(f"  {r['top']:.3f}  {r['tier']:<6} {r['stem'][:50]}")


if __name__ == "__main__":
    main()
