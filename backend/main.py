"""Carnatify API — FastAPI backend for the Carnatic music identifier.

Drives the existing Carnatify ML pipeline (raga classification + composition
matching + lyrics/meaning) over a small HTTP surface. Pitch contours come from
a precomputed bundle (``data/tracks_pitch.npz``) so neither mirdata nor the raw
Saraga dataset is needed at runtime.

Endpoints
---------
GET  /health             → {"status": "ok"}
GET  /tracks             → [{track_id, title, raga, tonic}, ...]
POST /predict {track_id} → {raga: [{name, confidence}], matches: [{title, score, track_id}]}
GET  /meaning/{title}    → {title, composer, meaning}

The Gemini API key is read from the GEMINI_API_KEY environment variable
(set as a HuggingFace Space secret) — it never leaves the backend.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import io

import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── resource resolution ─────────────────────────────────────────────────────
# In the Docker image, src/ models/ and lyrics.db are copied next to this file.
# For local dev they live one level up in the repo root. Prefer bundled, else
# fall back to the repo root so the same code runs in both places.
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent


def _resolve(rel: str) -> Path:
    bundled = _HERE / rel
    return bundled if bundled.exists() else _ROOT / rel


sys.path.insert(0, str(_resolve("src")))

from carnatify.ml.raga_classifier import predict_raga  # noqa: E402
from carnatify.ml.composition_matcher import match_composition  # noqa: E402
from carnatify.lyrics.pipeline import LyricsCatalog  # noqa: E402

# ── resource paths ──────────────────────────────────────────────────────────
_RAGA_MODEL = _resolve("models/raga_classifier.pkl")
_RAGA_ENC = _resolve("models/raga_label_encoder.pkl")
_PITCH_NPZ = _HERE / "data" / "tracks_pitch.npz"
_TRACKS_META = _HERE / "data" / "tracks_meta.json"
_LYRICS_DB = _resolve("data/lyrics.db")

_FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")

# ── lazily-loaded singletons ────────────────────────────────────────────────
_tracks: list[dict] | None = None
_tracks_by_id: dict[str, dict] = {}
_pitch: "np.lib.npyio.NpzFile | None" = None
_catalog: LyricsCatalog | None = None


def _load_tracks() -> list[dict]:
    global _tracks
    if _tracks is None:
        _tracks = json.loads(_TRACKS_META.read_text())
        _tracks_by_id.clear()
        _tracks_by_id.update({t["track_id"]: t for t in _tracks})
    return _tracks


def _get_pitch() -> "np.lib.npyio.NpzFile":
    global _pitch
    if _pitch is None:
        # mmap keeps memory low; arrays are read on demand.
        _pitch = np.load(_PITCH_NPZ, mmap_mode="r")
    return _pitch


def _get_catalog() -> LyricsCatalog:
    global _catalog
    if _catalog is None:
        _catalog = LyricsCatalog(db_path=_LYRICS_DB if _LYRICS_DB.exists() else None)
    return _catalog


# ── request/response models ─────────────────────────────────────────────────
class PredictRequest(BaseModel):
    track_id: str


# ── app ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="Carnatify API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_FRONTEND_ORIGIN] if _FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/tracks")
def tracks() -> list[dict]:
    return [
        {"track_id": t["track_id"], "title": t["title"], "raga": t["raga"], "tonic": t["tonic"]}
        for t in _load_tracks()
    ]


@app.post("/predict")
def predict(req: PredictRequest) -> dict:
    _load_tracks()
    entry = _tracks_by_id.get(req.track_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown track_id: {req.track_id}")

    frequencies = np.asarray(_get_pitch()[entry["key"]], dtype=np.float64)
    tonic = float(entry["tonic"])

    def _raga() -> list:
        if not (_RAGA_MODEL.exists() and _RAGA_ENC.exists()):
            return []
        try:
            return predict_raga(
                frequencies, tonic,
                model_path=_RAGA_MODEL, label_encoder_path=_RAGA_ENC, top_k=3,
            )
        except Exception:
            return []

    def _comp() -> list:
        try:
            return match_composition(frequencies, tonic, top_k=3)
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_raga = pool.submit(_raga)
        f_comp = pool.submit(_comp)
        raga_preds, comp_matches = f_raga.result(), f_comp.result()

    return {
        "raga": [
            {"name": p.raga_name, "confidence": float(p.confidence)} for p in raga_preds
        ],
        "matches": [
            {"title": title, "score": float(score), "track_id": tid}
            for title, score, tid in comp_matches
        ],
    }


@app.post("/predict-audio")
async def predict_audio(file: UploadFile = File(...)):
    import librosa

    data = await file.read()
    if len(data) > 30 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (30 MB limit)")

    y, sr = librosa.load(io.BytesIO(data), sr=22050, mono=True, duration=60.0)
    duration = float(len(y) / sr)
    if duration < 5.0:
        raise HTTPException(status_code=422, detail="clip too short, need at least 15 seconds")

    f0_full = librosa.yin(y, fmin=60, fmax=500, sr=sr)
    voiced = f0_full[f0_full > 0]
    tonic = float(np.median(voiced)) if len(voiced) else 130.0

    f0 = librosa.yin(y, fmin=60, fmax=1000, sr=sr)
    frequencies = f0[f0 > 0].astype(np.float64)

    def _raga():
        if not (_RAGA_MODEL.exists() and _RAGA_ENC.exists()):
            return []
        try:
            return predict_raga(
                frequencies, tonic,
                model_path=_RAGA_MODEL, label_encoder_path=_RAGA_ENC, top_k=3,
            )
        except Exception:
            return []

    def _comp():
        try:
            return match_composition(frequencies, tonic, top_k=3)
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_raga = pool.submit(_raga)
        f_comp = pool.submit(_comp)
        raga_preds, comp_matches = f_raga.result(), f_comp.result()

    return {
        "raga": [{"name": p.raga_name, "confidence": float(p.confidence)} for p in raga_preds],
        "matches": [{"title": title, "score": float(score), "track_id": tid} for title, score, tid in comp_matches],
        "tonic": tonic,
        "duration": duration,
    }


@app.get("/meaning/{title:path}")
def meaning(title: str) -> dict:
    catalog = _get_catalog()
    row = catalog.lookup(title)
    composer = (row.get("composer") if row else "") or ""

    try:
        text = catalog.generate_meaning(row["title"] if row else title)
    except Exception as exc:  # missing key, API error, etc.
        raise HTTPException(status_code=502, detail=f"Meaning generation failed: {exc}")

    if text is None:
        raise HTTPException(status_code=404, detail=f"'{title}' is not in the lyrics catalog.")

    return {"title": (row["title"] if row else title), "composer": composer, "meaning": text}
