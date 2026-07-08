"""Targeted deficit downloader: bring every priority raga to >=20 available
tracks (feature-cache tracks + on-disk audio awaiting extraction).

Modeled on download_archive_direct.py (same alias canonicalization, same
safe_title transform, same output layout data/concert_audio/<raga>/<title>.mp3)
but:
  - no MAX_TOTAL cap; per-raga targets driven by measured availability;
  - walks the FULL archive.org metadata cache (425 identifiers);
  - recovers labels the old pass missed: raga in the *filename* with no-space
    hyphens ("06-Emi Chesite-Todi.mp3") and spelling variants ("thodi",
    "panthuvarali", "Poorvi Kalyani") via an aspiration/vowel-squashed fold —
    still strictly alias-map gated, never guessed from audio;
  - writes an append-safe manifest data/concert_audio/download_manifest.json.

Download only. No Demucs, no features, no training.

Usage: python download_targeted_deficits.py
"""
from __future__ import annotations

import json
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

import numpy as np
import requests

from normalize_ragas import fold

ROOT = Path(__file__).parent
ALIASES_PATH = ROOT / "data" / "raga_aliases.json"
METADATA_CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "archive_metadata"
CACHE_DIRS = [ROOT / "data" / "raga_v2_cache" / "saraga_v3",
              ROOT / "data" / "raga_v2_cache" / "archive_v3"]
ARCHIVE_V3 = ROOT / "data" / "raga_v2_cache" / "archive_v3"
OUT_DIR = ROOT / "data" / "concert_audio"
MANIFEST_PATH = OUT_DIR / "download_manifest.json"

USER_AGENT = (
    "CarnatifyResearchBot/1.0 (+https://carnatify.vercel.app; "
    "educational raga-classification research; contact: dpti0904@gmail.com)"
)
DOWNLOAD_SLEEP_S = 2.0
DISK_BUDGET_BYTES = 25 * 1024**3
DASH_SPLIT_RE = re.compile(r"\s+[–—-]\s+")
NUM_SEG_RE = re.compile(r"^\d{1,3}$")

PRIORITY_20 = [
    "Kāṁbhōji", "Kamās", "Mōhanaṁ", "Sindhubhairavi", "Karaharapriya",
    "Sāvēri", "Harikāmbhōji", "Bhairavi", "Kānaḍa", "Kāmavardani", "Aṭāna",
    "Behāg", "Kāpi", "Hindōḷaṁ", "Madhyamāvati", "Ṣanmukhapriya", "Rītigauḷa",
    "Nāṭa", "Nīlāṁbari", "Suraṭi", "Pūrṇacandrika", "Bēgaḍa", "Jōnpuri",
    "Śrīranjani", "Saurāṣtraṁ", "Sahānā", "Sencuruṭṭi", "Bilahari", "Vasanta",
    "Sāma", "Śuddadhanyāsi", "Puṇṇāgavarāḷi", "Mukhāri", "Hamsadhvāni",
    "Pūrvīkaḷyāṇi", "Ānandabhairavi", "Nādanāmakriya", "Haṁsānandi", "Ābhōgī",
    "Varāḷi", "Maṇirangu", "Dhanyāsi", "Cakravākaṁ", "Nāṭakurinji",
    "Yadukula kāṁbōji", "Latāngi", "Janaranjani", "Bṛndāvana sāranga",
    "Cittaranjani",
]
SECONDARY_20 = [
    "Jaganmōhini", "Gauḷa", "Karṇāṭaka dēvagāndhāri", "Kēdāragauḷa",
    "Kuntalavarāḷi", "Dēvagāndhāri", "Āhiri", "Hussēnī", "Amṛtavarṣiṇi",
    "Lalita", "Hamīr kaḷyaṇi", "Māyāmāḷavagauḷa", "Mānḍu", "Dvijāvanti",
    "Sāranga", "Sarasvatī manōhari", "Vakuḷābharaṇaṁ", "Kedāraṁ",
]
TOPUP_30 = ["Kalyāṇi", "Tōḍi", "Śankarābharaṇaṁ"]
ALL_TARGET_NAMES = PRIORITY_20 + SECONDARY_20 + TOPUP_30
# Canonical display spelling per fold (matches feature cache + disk dirs;
# also folds Ābhōgi -> Ābhōgī).
DISPLAY_BY_FOLD = {fold(n): n for n in ALL_TARGET_NAMES}
EXCLUDE_FOLDS = {fold("Rāgamālika")}


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def vfold(s: str) -> str:
    """fold() plus aspiration/long-vowel squashing so transliteration variants
    (thodi/tODi, poorvi/pUrvI, khamas/kamAs) compare equal."""
    f = fold(s)
    for a, b in [("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"),
                 ("uu", "u"), ("bh", "b"), ("ch", "c"), ("dh", "d"),
                 ("gh", "g"), ("jh", "j"), ("kh", "k"), ("ph", "p"),
                 ("sh", "s"), ("th", "t"), ("w", "v")]:
        f = f.replace(a, b)
    return f


def safe_title_of(composition: str, fallback: str) -> str:
    return re.sub(r"[^\w \-]", "", composition).strip() or Path(fallback).stem


def build_matchers() -> tuple[dict, dict, dict]:
    aliases = json.loads(ALIASES_PATH.read_text())
    alias_by_norm = {norm(k): v for k, v in aliases.items() if v}
    alias_by_fold: dict[str, str] = {}
    for k, v in aliases.items():
        if v:
            alias_by_fold.setdefault(fold(k), v)
    # vfold matching only where unambiguous across the alias file
    vf_all: dict[str, set[str]] = defaultdict(set)
    for k, v in aliases.items():
        if v:
            vf_all[vfold(k)].add(fold(v))  # compare canonicals fold-level
    alias_by_vfold = {}
    for k, v in aliases.items():
        if v and len(vf_all[vfold(k)]) == 1:
            alias_by_vfold.setdefault(vfold(k), v)
    return alias_by_norm, alias_by_fold, alias_by_vfold


def feature_cache_counts() -> Counter[str]:
    counts: Counter[str] = Counter()
    for cache_dir in CACHE_DIRS:
        for p in cache_dir.glob("*.npz"):
            try:
                raga = str(np.load(p, allow_pickle=True)["raga"])
            except Exception:
                continue
            counts[fold(raga)] += 1
    return counts


def awaiting_extraction_counts() -> Counter[str]:
    """On-disk mp3s with no matching archive_v3 npz (archive__{raga}__{stem})."""
    extracted = {p.stem for p in ARCHIVE_V3.glob("*.npz")}
    counts: Counter[str] = Counter()
    for raga_dir in OUT_DIR.iterdir() if OUT_DIR.exists() else []:
        if not raga_dir.is_dir():
            continue
        for mp3 in raga_dir.glob("*.mp3"):
            if f"archive__{raga_dir.name}__{mp3.stem}" not in extracted:
                counts[fold(raga_dir.name)] += 1
    return counts


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    alias_by_norm, alias_by_fold, alias_by_vfold = build_matchers()

    def match_raga(seg: str) -> str | None:
        c = (alias_by_norm.get(norm(seg)) or alias_by_fold.get(fold(seg))
             or alias_by_vfold.get(vfold(seg)))
        if c is None or "/" in c or fold(c) in EXCLUDE_FOLDS:
            return None
        return DISPLAY_BY_FOLD.get(fold(c), c)

    def parse_file(fobj: dict) -> dict | None:
        """Return candidate dict or None. Label sources, in order:
        1. archive.org file `title` in "{comp} - {raga}[ - {tala}]" (space-dash)
        2. filename stem split on -/_ (no-space), raga segment matched from end
        3. title split the same way."""
        title = fobj.get("title") or fobj.get("name", "")
        parts = [p for p in DASH_SPLIT_RE.split(title) if p]
        if len(parts) >= 2:
            c = match_raga(parts[1])
            if c:
                return {"composition_title": parts[0].strip(), "raga_canonical": c,
                        "tala_raw": parts[2].strip() if len(parts) >= 3 else None,
                        "file_title_raw": title}
        for text in (Path(fobj.get("name", "")).stem, title):
            segs = [s.strip() for s in re.split(r"[-_]", text) if s.strip()]
            segs = [s for s in segs if not NUM_SEG_RE.match(s)]
            if len(segs) < 2:
                continue
            for i in range(len(segs) - 1, 0, -1):
                c = match_raga(segs[i])
                if c:
                    comp = " ".join(segs[:i]).strip()
                    if not comp:
                        break
                    return {"composition_title": comp, "raga_canonical": c,
                            "tala_raw": " ".join(segs[i + 1:]).strip() or None,
                            "file_title_raw": title}
            break  # only fall through to title-split if name had <2 segments
        return None

    targets: dict[str, int] = {fold(n): 20 for n in PRIORITY_20 + SECONDARY_20}
    targets.update({fold(n): 30 for n in TOPUP_30})

    cache_counts = feature_cache_counts()
    awaiting = awaiting_extraction_counts()
    availability: Counter[str] = Counter()
    for k in set(cache_counts) | set(awaiting) | set(targets):
        availability[k] = cache_counts[k] + awaiting[k]

    # ── Candidate pool ──
    candidates: dict[str, list[dict]] = defaultdict(list)
    n_files = n_matched = 0
    unmatched_labels: Counter[str] = Counter()
    for meta_path in sorted(METADATA_CACHE_DIR.glob("*.json")):
        ident = meta_path.stem
        try:
            files = json.loads(meta_path.read_text())
        except Exception:
            continue
        for fobj in files:
            n_files += 1
            cand = parse_file(fobj)
            if cand is None:
                title = fobj.get("title") or fobj.get("name", "")
                parts = [p for p in DASH_SPLIT_RE.split(title) if p]
                if len(parts) >= 2:
                    unmatched_labels[norm(parts[1])] += 1
                continue
            n_matched += 1
            cand["identifier"] = ident
            cand["name"] = fobj["name"]
            candidates[fold(cand["raga_canonical"])].append(cand)
    print(f"Metadata cache: {n_files} mp3 files, {n_matched} raga-matched")
    print(f"Top unmatched dash-parsed labels: {unmatched_labels.most_common(12)}")

    print("\n── Availability vs targets ──")
    for name in ALL_TARGET_NAMES:
        f = fold(name)
        print(f"  {name:<28} cache={cache_counts[f]:>2} awaiting={awaiting[f]:>2} "
              f"target={targets[f]} candidates={len(candidates[f])}")

    manifest: list[dict] = (json.loads(MANIFEST_PATH.read_text())
                            if MANIFEST_PATH.exists() else [])
    manifest_paths = {m["file_path"] for m in manifest}

    rng = random.Random(42)
    total_bytes = 0
    new_per_raga: Counter[str] = Counter()
    shortfall: dict[str, str] = {}
    n_fail = n_dupe_title = 0

    order = sorted(targets, key=lambda f: availability[f] - targets[f])
    for f in order:
        deficit = targets[f] - availability[f]
        if deficit <= 0:
            continue
        canon_name = DISPLAY_BY_FOLD[f]
        cands = list(candidates.get(f, []))
        rng.shuffle(cands)  # diversify across concerts/artists
        seen_titles: set[str] = set()
        got = 0
        for cand in cands:
            if got >= deficit:
                break
            if total_bytes >= DISK_BUDGET_BYTES:
                shortfall[canon_name] = "disk budget reached"
                break
            safe_title = safe_title_of(cand["composition_title"], cand["name"])
            if safe_title in seen_titles:
                n_dupe_title += 1
                continue
            seen_titles.add(safe_title)
            dest_dir = OUT_DIR / cand["raga_canonical"]
            dest_path = dest_dir / f"{safe_title}.mp3"
            if dest_path.exists():
                continue  # already on disk, already counted in availability

            url = (f"https://archive.org/download/{cand['identifier']}/"
                   f"{quote(cand['name'])}")
            try:
                resp = session.get(url, timeout=300, stream=True)
                resp.raise_for_status()
                dest_dir.mkdir(parents=True, exist_ok=True)
                tmp = dest_path.with_suffix(".part")
                nbytes = 0
                with open(tmp, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=1 << 16):
                        fh.write(chunk)
                        nbytes += len(chunk)
                if nbytes < 200_000:  # error stub, not a track
                    tmp.unlink(missing_ok=True)
                    print(f"  SKIP tiny ({nbytes}B) {url}")
                    continue
                tmp.rename(dest_path)
            except Exception as exc:
                n_fail += 1
                print(f"  FAILED {url}: {exc}")
                time.sleep(DOWNLOAD_SLEEP_S)
                continue

            total_bytes += nbytes
            got += 1
            new_per_raga[canon_name] += 1
            rel_path = str(dest_path.relative_to(ROOT))
            if rel_path not in manifest_paths:
                manifest.append({
                    "file_path": rel_path,
                    "archive_identifier": cand["identifier"],
                    "file_title_raw": cand["file_title_raw"],
                    "composition_title": cand["composition_title"],
                    "raga_canonical": cand["raga_canonical"],
                    "tala_raw_if_present": cand["tala_raw"],
                })
                manifest_paths.add(rel_path)
                MANIFEST_PATH.write_text(
                    json.dumps(manifest, indent=1, ensure_ascii=False))
            print(f"  [{sum(new_per_raga.values())}] {canon_name} "
                  f"({availability[f] + got}/{targets[f]}): "
                  f"{cand['composition_title']} <- {cand['identifier']}",
                  flush=True)
            time.sleep(DOWNLOAD_SLEEP_S)

        if got < deficit and canon_name not in shortfall:
            shortfall[canon_name] = (
                f"source exhausted: {len(cands)} labeled files, "
                f"{len(seen_titles)} unique titles, avail {availability[f]}"
                f"+{got} new < target {targets[f]}")
        if total_bytes >= DISK_BUDGET_BYTES:
            break

    print("\n── Summary ──")
    print(f"New files: {sum(new_per_raga.values())}, {total_bytes / 1e9:.2f} GB, "
          f"{n_fail} failed, {n_dupe_title} duplicate-title renditions skipped")
    for raga, n in new_per_raga.most_common():
        print(f"  {raga:<28} +{n}")
    print("\nStill under target:")
    for raga, why in sorted(shortfall.items()):
        print(f"  {raga}: {why}")
    print(f"\nManifest: {MANIFEST_PATH} ({len(manifest)} records)")


if __name__ == "__main__":
    main()
