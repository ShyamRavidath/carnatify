#!/usr/bin/env python3
"""Diagnostic: precision-vs-coverage curve of the EXISTING matcher confidence.

Answers one strategic question: is there ANY operating point at which the
current pipeline reaches >=85% top-1 precision, and at what coverage? This does
NOT fit or ship a gate -- it measures the separability of the confidence signal
already produced (top-1 score, margin, and the high/medium/low tier), so we can
decide whether a shippable high-confidence slice exists or the front-end
(sung-Carnatic ASR) is the ceiling.

Runs over ~/sung_tests for a given backend using the frozen caches (no ASR).

Run:
  venv_train/bin/python scripts/precision_coverage_curve.py whisper
  CARNATIFY_ASR_BACKEND=hybrid_stem \
    venv_train/bin/python scripts/precision_coverage_curve.py hybrid_stem
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import identify_clip as ic  # noqa: E402

CLIPS = Path("~/sung_tests").expanduser()
AUDIO = (".wav", ".mp3", ".m4a", ".flac")


def confidence_tier(res: dict) -> str:
    return res["composition_confidence"]


def run(backend: str) -> list[dict]:
    """Return one record per in-catalog clip: score, margin, tier, correct."""
    targets, lyr = ic.load_targets()
    wild = json.loads(ic.WILD_TRUTH.read_text())
    wild = {unicodedata.normalize("NFC", k): v for k, v in wild.items()}

    if backend == "hybrid_stem":
        wcache = ic.load_cache_v2("whisper")
        icache = ic.load_cache_v2("indic")
        stcache = ic.load_cache_v2("indic_stem")
    elif backend == "hybrid":
        wcache = ic.load_cache_v2("whisper")
        icache = ic.load_cache_v2("indic")
    else:
        cache2 = ic.load_cache_v2()

    files = sorted(p for p in CLIPS.iterdir() if p.suffix.lower() in AUDIO)
    records = []
    for p in files:
        stem = unicodedata.normalize("NFC", p.stem)
        if "__" not in stem:
            continue
        is_ooc = stem.endswith("__OOC")
        if backend == "hybrid_stem":
            res = ic.identify_v2_hybrid_stem(
                p, targets, lyr, wcache, icache, stcache, want_raga=False
            )
        elif backend == "hybrid":
            res = ic.identify_v2_hybrid(
                p, targets, lyr, wcache, icache, want_raga=False
            )
        else:
            res = ic.identify_v2(p, targets, lyr, cache2, want_raga=False)

        comps = res["compositions"]
        answered = res["composition_confidence"] != "none" and bool(comps)
        top = comps[0]["score"] if comps else 0.0
        margin = top - (comps[1]["score"] if len(comps) > 1 else 0.0)

        if is_ooc:
            correct = False  # any answer on an OOC clip is a false positive
        else:
            key = stem
            truth_ids = set(wild.get(key, {}).get("truth_ids", []))
            correct = bool(comps) and comps[0].get("id") in truth_ids

        records.append(
            {
                "clip": stem,
                "ooc": is_ooc,
                "answered": answered,
                "tier": res["composition_confidence"],
                "top": round(top, 4),
                "margin": round(margin, 4),
                "correct": correct,
            }
        )
    return records


def pr(records: list[dict], keep) -> tuple[int, int, int]:
    """(correct, answered, total) where a clip counts as answered iff keep()."""
    total = len(records)
    answered = [r for r in records if r["answered"] and keep(r)]
    correct = sum(1 for r in answered if r["correct"])
    return correct, len(answered), total


def line(label: str, correct: int, answered: int, total: int) -> str:
    prec = (100.0 * correct / answered) if answered else 0.0
    cov = 100.0 * answered / total if total else 0.0
    flag = "  <-- >=85%" if prec >= 85.0 and answered else ""
    return (
        f"  {label:<26} precision {correct:>2}/{answered:<2} = {prec:5.1f}%"
        f"   coverage {answered:>2}/{total} = {cov:4.1f}%{flag}"
    )


def main() -> None:
    backend = sys.argv[1] if len(sys.argv) > 1 else "whisper"
    records = run(backend)
    total = len(records)
    n_ooc = sum(r["ooc"] for r in records)
    print(f"\n===== precision/coverage curve: backend={backend} =====")
    print(f"clips: {total} ({total - n_ooc} in-catalog, {n_ooc} OOC)\n")

    print("By existing confidence tier (cumulative, most-confident first):")
    tiers = {"high": {"high"},
             "high+medium": {"high", "medium"},
             "high+medium+low (all answered)": {"high", "medium", "low"}}
    for label, keep_tiers in tiers.items():
        c, a, t = pr(records, lambda r, kt=keep_tiers: r["tier"] in kt)
        print(line(label, c, a, t))

    print("\nBy top-1 score threshold (answer iff top-1 score >= t):")
    for t in [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        c, a, tot = pr(records, lambda r, thr=t: r["top"] >= thr)
        print(line(f"score >= {t:.2f}", c, a, tot))

    print("\nBy score AND margin (answer iff top>=t and margin>=0.15):")
    for t in [0.50, 0.60, 0.65, 0.70, 0.75, 0.80]:
        c, a, tot = pr(
            records,
            lambda r, thr=t: r["top"] >= thr and r["margin"] >= 0.15,
        )
        print(line(f"score>={t:.2f} & margin>=.15", c, a, tot))

    # correct answers sorted by confidence, to eyeball the ceiling
    ans = [r for r in records if r["answered"]]
    ans.sort(key=lambda r: r["top"], reverse=True)
    n_correct = sum(r["correct"] for r in ans)
    print(f"\nanswered clips: {len(ans)}  correct top-1: {n_correct}  "
          f"(max achievable precision on any answered subset is bounded by "
          f"how these interleave)")
    print("top of the confidence ranking (score | margin | tier | ok? | clip):")
    for r in ans[:16]:
        print(f"  {r['top']:.3f}  {r['margin']:+.3f}  {r['tier']:<6} "
              f"{'OK ' if r['correct'] else 'x  '} {r['clip'][:44]}")


if __name__ == "__main__":
    main()
