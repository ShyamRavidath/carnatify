#!/usr/bin/env python
"""generate_meanings_batch.py — staged meanings pipeline (Claude Message Batches).

Replaces the Gemini free-tier drip (generate_meanings.py) with a one-time batch
job. Fully staged: every network/billing step is separated and gated so the
whole thing can be prepared and reviewed at zero cost.

Stages (run in order):

  import-karnatik   ZERO COST, run now. Copies human-written meanings (598)
                    and sahitya text from data/karnatik_lyrics.json into
                    data/lyrics.db where titles match. No network.

  build             ZERO COST, run now. Assembles Message Batches request file
                    for every lyrics.db title still missing a meaning, using
                    lyrics-grounded prompts where sahitya exists. Prints an
                    offline cost estimate. Writes data/meanings_batch/.

  submit            BILLED. Refuses to run unless CARNATIFY_BILLING_OK=1 is
                    set (Deepti's explicit approval). Creates the batch via
                    the Anthropic SDK (claude-haiku-4-5, Batches = 50% off).

  status            Free API call. Prints batch processing status.

  fetch             Streams results into lyrics.db (meaning_en +
                    meaning_generated_at + meaning_source='claude_batch'),
                    unverified until Deepti approves (verification queue).

Uses `venv` (py3.14 — has anthropic 0.112.0), NOT venv_train:
    venv/bin/python generate_meanings_batch.py import-karnatik
    venv/bin/python generate_meanings_batch.py build
    CARNATIFY_BILLING_OK=1 venv/bin/python generate_meanings_batch.py submit
    venv/bin/python generate_meanings_batch.py status
    venv/bin/python generate_meanings_batch.py fetch
"""

from __future__ import annotations

import hashlib
import json
import re
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / "data" / "lyrics.db"
KARNATIK = ROOT / "data" / "karnatik_lyrics.json"
OUT_DIR = ROOT / "data" / "meanings_batch"
REQ_FILE = OUT_DIR / "requests.json"
MAP_FILE = OUT_DIR / "custom_id_map.json"
BATCH_ID_FILE = OUT_DIR / "batch_id.txt"

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 700
SYSTEM = (
    "You are a scholar of Carnatic music and its devotional poetry. "
    "Explain compositions clearly for a general audience. "
    "Write in plain English — no headers, no bullet points."
)


def norm_title(t: str) -> str:
    """Match key: lowercase alnum, parenthetical form-suffixes stripped."""
    t = re.sub(r"\([^)]*\)", " ", t or "")
    return re.sub(r"[^a-z0-9]", "", t.lower())


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cols = {r[1] for r in conn.execute("PRAGMA table_info(lyrics_catalog)")}
    if "meaning_source" not in cols:
        conn.execute("ALTER TABLE lyrics_catalog ADD COLUMN meaning_source TEXT")
        conn.commit()
    return conn


def load_karnatik() -> dict[str, dict]:
    """norm_title -> best karnatik entry (prefer ones with meaning, then
    longer lyrics)."""
    best: dict[str, dict] = {}
    for e in json.loads(KARNATIK.read_text()):
        key = norm_title(e.get("title", ""))
        if not key:
            continue
        cur = best.get(key)
        score = (bool(e.get("meaning", "").strip()),
                 len(e.get("lyrics", "") or ""))
        cur_score = (bool(cur and cur.get("meaning", "").strip()),
                     len(cur.get("lyrics", "") or "")) if cur else (False, -1)
        if score > cur_score:
            best[key] = e
    return best


# ------------------------------------------------------------------ stages ---

def stage_import_karnatik() -> None:
    conn = db_conn()
    kmap = load_karnatik()
    now = datetime.now(timezone.utc).isoformat()
    meanings = lyrics = 0
    for row in conn.execute("SELECT title, meaning_en, lyrics_original "
                            "FROM lyrics_catalog").fetchall():
        e = kmap.get(norm_title(row["title"]))
        if not e:
            continue
        ktext = (e.get("lyrics") or "").strip()
        if ktext and not (row["lyrics_original"] or "").strip():
            conn.execute("UPDATE lyrics_catalog SET lyrics_original=? "
                         "WHERE title=?", (ktext, row["title"]))
            lyrics += 1
        kmean = (e.get("meaning") or "").strip()
        if kmean and not (row["meaning_en"] or "").strip():
            conn.execute(
                "UPDATE lyrics_catalog SET meaning_en=?, "
                "meaning_generated_at=?, meaning_source='karnatik_scrape' "
                "WHERE title=?", (kmean, now, row["title"]))
            meanings += 1
    conn.commit()
    total, have = conn.execute(
        "SELECT COUNT(*), SUM(meaning_en IS NOT NULL) FROM lyrics_catalog"
    ).fetchone()
    print(f"imported: {meanings} human meanings, {lyrics} sahitya texts")
    print(f"db now: {have}/{total} titles have meanings")


def build_prompt(row: sqlite3.Row) -> str:
    raga = row["raga"] or "an unspecified raga"
    composer = row["composer"]
    lyrics = (row["lyrics_original"] or "").strip()
    title = row["title"]
    if lyrics:
        return (
            f"Carnatic composition: '{title}'"
            + (f" by {composer}" if composer else "")
            + f", set in raga {raga}.\n\nLyrics:\n{lyrics[:6000]}\n\n"
            "Give a brief English meaning and cultural context."
        )
    composer_clause = f", composed by {composer}" if composer else ""
    return (
        f"The Carnatic composition '{title}'{composer_clause} is set in "
        f"raga {raga}. Provide a brief English meaning and cultural context: "
        "what emotional sentiment or devotional theme it likely expresses, "
        "the deity or subject being addressed, and any notable character of "
        "this raga in Carnatic tradition. Keep it to 2-3 short paragraphs."
    )


def stage_build() -> None:
    conn = db_conn()
    OUT_DIR.mkdir(exist_ok=True)
    rows = conn.execute(
        "SELECT * FROM lyrics_catalog WHERE meaning_en IS NULL "
        "OR meaning_en = ''").fetchall()
    requests, id_map = [], {}
    grounded = 0
    in_chars = 0
    for row in rows:
        cid = "m-" + hashlib.sha1(row["title"].encode()).hexdigest()[:16]
        prompt = build_prompt(row)
        in_chars += len(prompt) + len(SYSTEM)
        grounded += bool((row["lyrics_original"] or "").strip())
        requests.append({
            "custom_id": cid,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM,
                "messages": [{"role": "user", "content": prompt}],
            },
        })
        id_map[cid] = {"title": row["title"],
                       "grounded": bool((row["lyrics_original"] or "").strip())}
    REQ_FILE.write_text(json.dumps(requests, ensure_ascii=False))
    MAP_FILE.write_text(json.dumps(id_map, ensure_ascii=False, indent=0))
    in_tok = in_chars / 4                      # rough offline estimate
    out_tok = len(requests) * 450              # ~450 output tokens typical
    # Haiku 4.5 $1/$5 per MTok, Batches 50% off
    cost = (in_tok * 0.5 + out_tok * 2.5) / 1e6
    print(f"built {len(requests)} requests ({grounded} lyrics-grounded, "
          f"{len(requests) - grounded} title-only) -> {REQ_FILE}")
    print(f"offline estimate: ~{in_tok/1e6:.2f}M in / ~{out_tok/1e6:.2f}M out "
          f"tokens ≈ ${cost:.2f} at batch pricing. NOT submitted.")


def _client():
    import anthropic
    return anthropic.Anthropic()


def stage_submit() -> None:
    if os.environ.get("CARNATIFY_BILLING_OK") != "1":
        sys.exit("REFUSING: paid API call. Set CARNATIFY_BILLING_OK=1 "
                 "(Deepti approval) to submit the batch.")
    requests = json.loads(REQ_FILE.read_text())
    batch = _client().messages.batches.create(requests=requests)
    BATCH_ID_FILE.write_text(batch.id)
    print(f"submitted batch {batch.id} ({len(requests)} requests), "
          f"status {batch.processing_status}")


def stage_status() -> None:
    batch_id = BATCH_ID_FILE.read_text().strip()
    b = _client().messages.batches.retrieve(batch_id)
    print(batch_id, b.processing_status, b.request_counts)


def stage_fetch() -> None:
    batch_id = BATCH_ID_FILE.read_text().strip()
    client = _client()
    if client.messages.batches.retrieve(batch_id).processing_status != "ended":
        sys.exit("batch not finished — run `status` to check")
    id_map = json.loads(MAP_FILE.read_text())
    conn = db_conn()
    now = datetime.now(timezone.utc).isoformat()
    ok = err = 0
    for result in client.messages.batches.results(batch_id):
        meta = id_map.get(result.custom_id)
        if meta is None:
            continue
        if result.result.type != "succeeded":
            err += 1
            continue
        msg = result.result.message
        text = next((b.text for b in msg.content if b.type == "text"), "").strip()
        if not text:
            err += 1
            continue
        conn.execute(
            "UPDATE lyrics_catalog SET meaning_en=?, meaning_generated_at=?, "
            "meaning_source='claude_batch' WHERE title=? AND "
            "(meaning_en IS NULL OR meaning_en='')",
            (text, now, meta["title"]))
        ok += 1
    conn.commit()
    total, have = conn.execute(
        "SELECT COUNT(*), SUM(meaning_en IS NOT NULL) FROM lyrics_catalog"
    ).fetchone()
    print(f"fetched: {ok} meanings written, {err} failed/empty")
    print(f"db now: {have}/{total} titles have meanings "
          f"(unverified — Deepti verification queue next)")


STAGES = {
    "import-karnatik": stage_import_karnatik,
    "build": stage_build,
    "submit": stage_submit,
    "status": stage_status,
    "fetch": stage_fetch,
}


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in STAGES:
        sys.exit(f"usage: {sys.argv[0]} {{{'|'.join(STAGES)}}}")
    STAGES[sys.argv[1]]()
