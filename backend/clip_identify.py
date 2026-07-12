"""Lyrics-first clip identification + feedback logging for the Carnatify API.

Wraps the identify_clip pipeline (registry matcher + dual-ASR selection) for
server use. identify_clip.py is copied next to this file by build_space.sh,
so its matcher stays the single source of truth — do NOT fork the scoring
logic here.

ASR engine: faster-whisper int8 if installed (4-8x faster on CPU), else
openai-whisper. Both consume 16 kHz float32 numpy arrays — never file paths
(no ffmpeg in the image beyond torchaudio's).

Feedback persistence: HF Space filesystems are wiped on restart, so every
query/feedback line is also pushed to a private HF dataset repo when
HF_TOKEN + FEEDBACK_REPO are configured. Each confirmed answer is a labeled
wild clip — the data this project is starved for. Guard it.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path

logger = logging.getLogger("carnatify.identify")

_HERE = Path(__file__).resolve().parent
_FEEDBACK_DIR = _HERE / "data" / "feedback"
_FEEDBACK_REPO = os.environ.get("FEEDBACK_REPO", "")  # e.g. "deepti/carnatify-feedback"

from identify_clip import (  # noqa: E402 — copied in by build_space.sh
    HALLUC,
    MIN_ANSWER_SCORE,
    MIN_TRANSCRIPT_CHARS,
    VARIANT_CLOSE,
    fold,
    load_targets,
    match_lyrics,
)

# ── matcher targets (registry) ──────────────────────────────────────────────
_entries = None


def get_entries():
    global _entries
    if _entries is None:
        _entries, _ = load_targets()
        logger.info("Composition registry: %d entries", len(_entries))
    return _entries


# ── ASR ─────────────────────────────────────────────────────────────────────
_asr_lock = threading.Lock()
_asr_model = None
_asr_engine = None


def _load_asr():
    global _asr_model, _asr_engine
    if _asr_model is not None:
        return
    # openai-whisper is the wild-clip-validated default. faster-whisper int8
    # measured ~1x realtime with garbage output on macOS ARM (2026-07-11);
    # its 4-8x speedup claims are x86-specific. Opt in with
    # ASR_ENGINE=faster-whisper only after benchmarking ON the Space, and
    # re-run the wild-clip suite against its transcripts before trusting it.
    if os.environ.get("ASR_ENGINE") == "faster-whisper":
        from faster_whisper import WhisperModel
        _asr_model = WhisperModel("large-v3-turbo", device="cpu",
                                  compute_type="int8")
        _asr_engine = "faster-whisper-int8"
    else:
        import whisper
        _asr_model = whisper.load_model("large-v3-turbo")
        _asr_engine = "openai-whisper"
    logger.info("ASR engine: %s", _asr_engine)


def transcribe_multi(audio_16k, langs=(None, "ta", "te")) -> str:
    """Longest folded transcript across language passes (identify_clip rule)."""
    with _asr_lock:  # whisper models are not thread-safe; requests queue here
        _load_asr()
        best = ""
        for lang in langs:
            try:
                if _asr_engine == "faster-whisper-int8":
                    segs, _ = _asr_model.transcribe(audio_16k, language=lang,
                                                    beam_size=5)
                    t = fold(" ".join(s.text for s in segs))
                else:
                    r = _asr_model.transcribe(audio_16k, language=lang,
                                              fp16=False)
                    t = fold(r["text"])
                if len(t) > len(best):
                    best = t
            except Exception as exc:
                logger.warning("ASR pass (%s) failed: %s", lang, exc)
    return best


# ── identification (policy v2 over ASR variants) ────────────────────────────

def identify_from_variants(variants: dict[str, str]) -> dict:
    """variants: name -> raw transcript; 'stem*' names are vocal-stem passes.

    Mirrors identify_clip.identify()'s selection: best usable variant by
    match score, prefer stem within VARIANT_CLOSE, hallucination stoplist,
    repetition >= 2 usability gate, abstain below MIN_ANSWER_SCORE.
    """
    entries = get_entries()
    cands = []
    for name, txt in variants.items():
        txt = HALLUC.sub(" ", txt or "")
        if len(txt.replace(" ", "")) < MIN_TRANSCRIPT_CHARS:
            continue
        comps, max_rep = match_lyrics(txt, entries, None)
        if not comps or max_rep < 2:
            continue
        cands.append((comps[0]["score"], name.startswith("stem"), name, txt,
                      comps))
    pick = None
    if cands:
        best = max(c[0] for c in cands)
        strong = [c for c in cands if c[0] >= best - VARIANT_CLOSE]
        vocal = [c for c in strong if c[1]]
        pick = max(vocal or strong, key=lambda c: c[0])

    if not pick or pick[0] < MIN_ANSWER_SCORE:
        return {
            "compositions": [],
            "composition_confidence": "none",
            "clip_type": "no_lyrics",
            "asr_variant": None,
            "transcript": (variants.get("orig") or "")[:200],
            "message": ("Couldn't hear clear lyrics — this may be alapana, "
                        "instrumental, or too noisy. Raga guess below is "
                        "low-confidence. Try a section with singing, ideally "
                        "the pallavi."),
        }
    top, _, vname, txt, comps = pick
    margin = top - (comps[1]["score"] if len(comps) > 1 else 0.0)
    if top >= 0.65 and margin >= 0.15:
        conf = "high"
    elif top >= 0.5:
        conf = "medium"
    else:
        conf = "low"
    return {
        "compositions": comps,          # [{title, score, ragas}]
        "composition_confidence": conf,
        "clip_type": "sung",
        "asr_variant": vname,
        "transcript": txt[:200],
        "message": None if conf != "low" else (
            "Low confidence — if none of these look right, try a cleaner "
            "clip of the pallavi."),
    }


# ── query + feedback logging ────────────────────────────────────────────────

def _append_jsonl(name: str, record: dict) -> Path:
    _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    path = _FEEDBACK_DIR / name
    with path.open("a") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _push_to_hub(path: Path) -> None:
    """Best-effort persistence to a private HF dataset (Space disk is wiped
    on restart). Never let persistence failures break a user request."""
    if not (_FEEDBACK_REPO and os.environ.get("HF_TOKEN")):
        return
    try:
        from huggingface_hub import HfApi
        HfApi().upload_file(
            path_or_fileobj=str(path),
            path_in_repo=f"logs/{path.name}",
            repo_id=_FEEDBACK_REPO,
            repo_type="dataset",
        )
    except Exception as exc:
        logger.warning("HF feedback push failed (kept locally): %s", exc)


def log_query(result: dict, extra: dict) -> str:
    query_id = uuid.uuid4().hex[:12]
    rec = {"query_id": query_id, "ts": time.time(), **extra,
           "result": {k: result.get(k) for k in
                      ("compositions", "composition_confidence", "clip_type",
                       "asr_variant", "transcript")}}
    path = _append_jsonl("queries.jsonl", rec)
    threading.Thread(target=_push_to_hub, args=(path,), daemon=True).start()
    return query_id


def log_feedback(payload: dict) -> None:
    rec = {"ts": time.time(), **payload}
    path = _append_jsonl("feedback.jsonl", rec)
    threading.Thread(target=_push_to_hub, args=(path,), daemon=True).start()
