"""Third-pass downloader: label archive.org files by composition-title join.

download_targeted_deficits.py exhausted files whose *own* title/filename carries
a raga segment. This pass unlocks the remaining ~733 unlabeled files by joining
their composition title against the blog's tracklist records
(data/scraped_compositions.json: title + raga_canonical, 3,698 records) —
strictly unambiguous joins only (title must map to exactly one canonical raga
across every blog record; generic form-titles like Thillana/Mangalam/RTP are
excluded automatically by that rule when they occur in >1 raga).

Also downloads up to MAX_PER_TITLE renditions per (title, raga) instead of 1 —
extra renditions are new track_ids for the raga classifier AND reference
versions for the composition matcher.

Download only. No Demucs, no features, no training. Append-safe manifest.

Usage: python download_title_join.py
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

import numpy as np
import requests

from normalize_ragas import fold

ROOT = Path(__file__).parent
SCRAPED_PATH = ROOT / "data" / "scraped_compositions.json"
METADATA_CACHE_DIR = ROOT / "data" / "raga_v2_cache" / "archive_metadata"
CACHE_DIRS = [ROOT / "data" / "raga_v2_cache" / "saraga_v3",
              ROOT / "data" / "raga_v2_cache" / "archive_v3"]
ARCHIVE_V3 = ROOT / "data" / "raga_v2_cache" / "archive_v3"
OUT_DIR = ROOT / "data" / "concert_audio"
MANIFEST_PATH = OUT_DIR / "download_manifest.json"
ALIASES_PATH = ROOT / "data" / "raga_aliases.json"

USER_AGENT = (
    "CarnatifyResearchBot/1.0 (+https://carnatify.vercel.app; "
    "educational raga-classification research; contact: dpti0904@gmail.com)"
)
DOWNLOAD_SLEEP_S = 2.0
DISK_BUDGET_BYTES = 25 * 1024**3
DASH_SPLIT_RE = re.compile(r"\s+[–—-]\s+")
NUM_PREFIX_RE = re.compile(r"^\d{1,3}[\s._-]*")
MAX_PER_TITLE = 3
MIN_TITLE_FOLD_LEN = 8  # short folded titles are too collision-prone to join on

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
DISPLAY_BY_FOLD = {fold(n): n for n in ALL_TARGET_NAMES}
EXCLUDE_FOLDS = {fold("Rāgamālika")}


def tfold(s: str) -> str:
    """Title fold: strip a leading track number, then normalize_ragas.fold."""
    return fold(NUM_PREFIX_RE.sub("", s or ""))


def safe_title_of(composition: str, fallback: str) -> str:
    return re.sub(r"[^\w \-]", "", composition).strip() or Path(fallback).stem


def build_title_raga_map() -> dict[str, str]:
    """Folded composition title -> canonical raga, unambiguous joins only."""
    records = json.loads(SCRAPED_PATH.read_text())
    votes: dict[str, set[str]] = defaultdict(set)
    display: dict[str, str] = {}
    for r in records:
        canon = r.get("raga_canonical")
        title = (r.get("title") or "").strip()
        if not canon or not title or "/" in canon:
            continue
        tf = tfold(title)
        if len(tf) < MIN_TITLE_FOLD_LEN:
            continue
        cf = fold(canon)
        if cf in EXCLUDE_FOLDS:
            continue
        votes[tf].add(cf)
        display[cf] = DISPLAY_BY_FOLD.get(cf, canon)
    return {tf: display[next(iter(cs))]
            for tf, cs in votes.items() if len(cs) == 1}


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
    extracted = {p.stem for p in ARCHIVE_V3.glob("*.npz")}
    counts: Counter[str] = Counter()
    for raga_dir in OUT_DIR.iterdir() if OUT_DIR.exists() else []:
        if not raga_dir.is_dir():
            continue
        for mp3 in raga_dir.glob("*.mp3"):
            if f"archive__{raga_dir.name}__{mp3.stem}" not in extracted:
                counts[fold(raga_dir.name)] += 1
    return counts


def has_own_raga_label(fobj: dict, alias_folds: set[str]) -> bool:
    """True when the earlier passes could already label this file directly."""
    title = fobj.get("title") or fobj.get("name", "")
    parts = [p for p in DASH_SPLIT_RE.split(title) if p]
    if len(parts) >= 2 and fold(parts[1]) in alias_folds:
        return True
    for text in (Path(fobj.get("name", "")).stem, title):
        segs = [s.strip() for s in re.split(r"[-_]", text) if s.strip()]
        if any(fold(s) in alias_folds for s in segs[1:]):
            return True
    return False


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    title_map = build_title_raga_map()
    print(f"Unambiguous title->raga joins: {len(title_map)}")

    aliases = json.loads(ALIASES_PATH.read_text())
    alias_folds = {fold(k) for k, v in aliases.items() if v}

    targets: dict[str, int] = {fold(n): 20 for n in PRIORITY_20 + SECONDARY_20}
    targets.update({fold(n): 30 for n in TOPUP_30})

    cache_counts = feature_cache_counts()
    awaiting = awaiting_extraction_counts()
    availability: Counter[str] = Counter()
    for k in set(cache_counts) | set(awaiting):
        availability[k] = cache_counts[k] + awaiting[k]

    manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else []

    # renditions already on disk per (raga_fold, title_fold)
    per_title: Counter[tuple[str, str]] = Counter()
    for raga_dir in OUT_DIR.iterdir() if OUT_DIR.exists() else []:
        if raga_dir.is_dir():
            for mp3 in raga_dir.glob("*.mp3"):
                per_title[(fold(raga_dir.name), tfold(mp3.stem))] += 1

    # ── Candidate pool: unlabeled files joined via title map ──
    candidates: list[tuple[str, str, str, dict]] = []  # (raga_fold, title_fold, ident, fobj)
    for meta_path in sorted(METADATA_CACHE_DIR.glob("*.json")):
        ident = meta_path.stem
        try:
            files = json.loads(meta_path.read_text())
        except Exception:
            continue
        for fobj in files:
            if has_own_raga_label(fobj, alias_folds):
                continue  # earlier passes own these
            raw_title = fobj.get("title") or Path(fobj.get("name", "")).stem
            comp = DASH_SPLIT_RE.split(raw_title)[0]
            tf = tfold(comp)
            canon = title_map.get(tf)
            if canon is None or fold(canon) not in targets:
                continue
            candidates.append((fold(canon), tf, ident, fobj))

    pool_by_raga = Counter(c[0] for c in candidates)
    print(f"Joinable unlabeled candidates: {len(candidates)} across {len(pool_by_raga)} target ragas")

    # deficit ragas first, thinnest first
    candidates.sort(key=lambda c: (availability[c[0]], c[0]))

    n_new = n_skip = n_fail = 0
    bytes_dl = 0
    for raga_fold, tf, ident, fobj in candidates:
        if bytes_dl >= DISK_BUDGET_BYTES:
            print("Disk budget reached, stopping.")
            break
        if availability[raga_fold] >= targets[raga_fold]:
            continue
        if per_title[(raga_fold, tf)] >= MAX_PER_TITLE:
            continue
        canon = DISPLAY_BY_FOLD[raga_fold]
        raw_title = fobj.get("title") or Path(fobj.get("name", "")).stem
        comp = DASH_SPLIT_RE.split(raw_title)[0]
        safe_title = safe_title_of(comp, fobj.get("name", ""))
        dest_dir = OUT_DIR / canon
        dest_path = dest_dir / f"{safe_title}.mp3"
        r = 2
        while dest_path.exists():
            dest_path = dest_dir / f"{safe_title}_r{r}.mp3"
            r += 1
        url = f"https://archive.org/download/{ident}/{quote(fobj['name'])}"
        try:
            resp = session.get(url, timeout=180)
            resp.raise_for_status()
        except Exception as exc:
            n_fail += 1
            print(f"  FAILED {url}: {exc}", flush=True)
            time.sleep(DOWNLOAD_SLEEP_S)
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(resp.content)
        bytes_dl += len(resp.content)
        availability[raga_fold] += 1
        per_title[(raga_fold, tf)] += 1
        n_new += 1
        manifest.append({
            "file_path": str(dest_path.relative_to(ROOT)),
            "archive_identifier": ident,
            "file_title_raw": raw_title,
            "composition_title": comp.strip(),
            "raga_canonical": canon,
            "tala_raw_if_present": None,
            "label_source": "title_join",
        })
        if n_new % 10 == 0:
            MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        print(f"  [{n_new}] {canon}: {comp.strip()} <- {ident} ({len(resp.content)/1e6:.0f} MB)", flush=True)
        time.sleep(DOWNLOAD_SLEEP_S)

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\nDone: {n_new} new, {n_fail} failed, {bytes_dl/1e9:.2f} GB")
    still = {DISPLAY_BY_FOLD[k]: (availability[k], targets[k])
             for k in targets if availability[k] < targets[k]}
    print(f"Still under target: {len(still)} ragas")
    for name, (a, t) in sorted(still.items()):
        print(f"  {name}: {a}/{t}")


if __name__ == "__main__":
    main()
