#!/usr/bin/env python3
"""Diagnostic: does CROSS-CHANNEL AGREEMENT separate correct from wrong?

The precision/coverage curve showed the single-channel match score carries
almost no correctness signal. This tests an independent signal: when two ASR
channels (Whisper vs IndicConformer mix/stem), scored separately, land on the
SAME top-1 composition, is that agreed answer much more likely correct?

If agreement yields high precision at even low coverage, a tiny shippable slice
exists today. If it does not separate either, the front-end (sung-Carnatic ASR)
is confirmed as the ceiling. Read-only; frozen caches; no ASR run.

Run:
  venv_train/bin/python scripts/cross_channel_agreement.py
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


def top1(res: dict):
    """(id, score) of a channel's top-1, or (None, 0) if it did not answer."""
    comps = res.get("compositions") or []
    if res.get("composition_confidence") == "none" or not comps:
        return None, 0.0
    return comps[0].get("id"), comps[0].get("score", 0.0)


def main() -> None:
    targets, lyr = ic.load_targets()
    wild = json.loads(ic.WILD_TRUTH.read_text())
    wild = {unicodedata.normalize("NFC", k): v for k, v in wild.items()}
    wcache = ic.load_cache_v2("whisper")
    mcache = ic.load_cache_v2("indic")
    stcache = ic.load_cache_v2("indic_stem")

    files = sorted(p for p in CLIPS.iterdir() if p.suffix.lower() in AUDIO)
    rows = []
    for p in files:
        stem = unicodedata.normalize("NFC", p.stem)
        if "__" not in stem:
            continue
        is_ooc = stem.endswith("__OOC")
        sha = ic.audio_sha256(p)
        wentry = wcache["entries"].get(ic.cache2_key(sha, ic.WHISPER_CONFIG_ID))
        mentry = mcache["entries"].get(ic.cache2_key(sha, ic.INDIC_CONFIG_ID))
        sentry = stcache["entries"].get(
            ic.cache2_key(sha, ic.INDIC_STEM_CONFIG_ID)
        )
        wres = ic.assess_variants(
            ic.variants_from_v2(wentry) if wentry else {}, targets, lyr
        )
        mres = ic.assess_variants(
            ic.variants_from_v2(mentry) if mentry else {}, targets, lyr
        )
        sres = ic.assess_variants(
            ic.variants_from_v2(sentry) if sentry else {}, targets, lyr
        )
        wid, _ = top1(wres)
        mid, _ = top1(mres)
        sid, _ = top1(sres)
        truth = set(wild.get(stem, {}).get("truth_ids", []))
        rows.append(
            {
                "clip": stem, "ooc": is_ooc, "truth": truth,
                "wid": wid, "mid": mid, "sid": sid,
            }
        )

    total = len(rows)

    def report(label: str, agree_id) -> None:
        """agree_id(row) -> the agreed composition id, or None if no agreement."""
        answered = []
        for r in rows:
            aid = agree_id(r)
            if aid is not None:
                answered.append((r, aid))
        correct = sum(1 for r, aid in answered if aid in r["truth"])
        a = len(answered)
        prec = (100.0 * correct / a) if a else 0.0
        cov = 100.0 * a / total if total else 0.0
        flag = "  <-- >=85%" if prec >= 85.0 and a else ""
        print(f"  {label:<34} precision {correct:>2}/{a:<2} = {prec:5.1f}%"
              f"   coverage {a:>2}/{total} = {cov:4.1f}%{flag}")

    def eq(a, b):
        return a is not None and a == b

    print(f"\n===== cross-channel agreement over {total} clips "
          f"({sum(r['ooc'] for r in rows)} OOC) =====\n")
    print("Agreement rules (answer only when two channels pick the SAME id):")
    report("whisper == indic_mix",
           lambda r: r["wid"] if eq(r["wid"], r["mid"]) else None)
    report("whisper == indic_stem",
           lambda r: r["wid"] if eq(r["wid"], r["sid"]) else None)
    report("whisper == (mix OR stem)",
           lambda r: r["wid"]
           if (eq(r["wid"], r["mid"]) or eq(r["wid"], r["sid"])) else None)
    report("mix == stem",
           lambda r: r["mid"] if eq(r["mid"], r["sid"]) else None)
    report("all three agree",
           lambda r: r["wid"]
           if (eq(r["wid"], r["mid"]) and eq(r["wid"], r["sid"])) else None)

    print("\nBaselines (single channel, any answer):")
    report("whisper only", lambda r: r["wid"])
    report("indic_mix only", lambda r: r["mid"])
    report("indic_stem only", lambda r: r["sid"])

    # enumerate the agreeing pairs so we can eyeball them
    print("\nwhisper==(mix or stem) agreeing clips:")
    for r in rows:
        if eq(r["wid"], r["mid"]) or eq(r["wid"], r["sid"]):
            ok = "OK " if r["wid"] in r["truth"] else "x  "
            which = "mix" if eq(r["wid"], r["mid"]) else ""
            which += "+stem" if eq(r["wid"], r["sid"]) else ""
            print(f"  {ok} {r['wid']:<10} [{which:<8}] {r['clip'][:50]}")


if __name__ == "__main__":
    main()
