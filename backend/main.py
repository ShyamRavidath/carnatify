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

import asyncio
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("carnatify")

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

# Deliberate default rather than "*": if the env var is missing on the Space,
# we still only serve the production frontend (plus localhost for dev).
_FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "https://carnatify.vercel.app")
_ALLOWED_ORIGINS = [_FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"]

# HF Spaces sits behind a proxy, so the client IP arrives in X-Forwarded-For.
def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Demucs saturates the 2-vCPU Space; never run two separations at once.
_DEMUCS_SEM = asyncio.Semaphore(1)

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
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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


def _estimate_tonic_mix(audio_path: str) -> float | None:
    """Drone-based tonic (Sa) estimation on the mixed upload via essentia.

    Runs before Demucs because separation strips the tambura drone. Validated
    on Saraga annotated tonics: ~87% within ±50 cents on 180s windows, ~70% on
    60s clips. The previous median-of-voiced-F0 tonic was within ±50 cents only
    ~10% of the time, so every feature vector reached the classifier rotated by
    a near-random offset — the main cause of wrong live raga predictions.
    """
    try:
        import essentia.standard as es
    except ImportError:
        logger.warning("essentia not installed — falling back to median-F0 tonic")
        return None
    import librosa

    try:
        y_mix, _ = librosa.load(audio_path, sr=22050, mono=True, duration=180.0)
        if len(y_mix) < 22050 * 10:
            return None
        tonic = float(es.TonicIndianArtMusic(sampleRate=22050)(y_mix))
    except Exception as exc:
        logger.warning("Tonic estimation failed (%s) — falling back to median-F0", exc)
        return None
    return tonic if 80.0 <= tonic <= 400.0 else None


def _separate_vocals_sync(audio_path: str, out_dir: str) -> str:
    """Run Demucs htdemucs vocal separation; returns path to vocals.wav."""
    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems=vocals",
        "-n", "htdemucs",
        "-o", out_dir,
        audio_path,
    ]
    logger.info("Demucs: launching %s", " ".join(cmd))
    started = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    elapsed = time.monotonic() - started
    logger.info(
        "Demucs: finished in %.1fs, returncode=%d, stderr_tail=%r",
        elapsed, result.returncode, result.stderr[-500:],
    )
    if result.returncode != 0:
        raise RuntimeError(f"Demucs failed (rc={result.returncode}): {result.stderr[-500:]}")
    track_name = Path(audio_path).stem
    vocal_path = Path(out_dir) / "htdemucs" / track_name / "vocals.wav"
    if not vocal_path.exists():
        raise RuntimeError(f"Vocals file not found at {vocal_path}")
    logger.info("Demucs: vocals written to %s", vocal_path)
    return str(vocal_path)


@app.post("/predict-audio")
@limiter.limit("2/minute")
async def predict_audio(request: Request, file: UploadFile = File(...)):
    import librosa

    data = await file.read()
    if len(data) > 30 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (30 MB limit)")

    # Determine file suffix from content-type so ffmpeg picks the right demuxer.
    ct = (file.content_type or "").lower()
    if "ogg" in ct or "opus" in ct:
        suffix = ".ogg"
    elif "mp4" in ct or "m4a" in ct or "aac" in ct:
        suffix = ".m4a"
    elif "webm" in ct:
        suffix = ".webm"
    elif "mpeg" in ct or "mp3" in ct:
        suffix = ".mp3"
    elif "wav" in ct:
        suffix = ".wav"
    else:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio content-type: {file.content_type or 'none'}. "
            "Send webm, ogg, m4a, mp3, or wav.",
        )

    tmp_path = None
    demucs_dir = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        # Decode to confirm it's valid audio before running the expensive Demucs step.
        try:
            y_check, sr_check = librosa.load(tmp_path, sr=22050, mono=True, duration=5.0)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Could not decode audio — unsupported format or corrupt file: {exc}",
            )
        if len(y_check) / sr_check < 5.0:
            raise HTTPException(status_code=422, detail="clip too short, need at least 15 seconds")

        # Tonic from the mixed audio, while the upload still exists on disk.
        tonic_est = _estimate_tonic_mix(tmp_path)

        # Re-encode as a true 2-channel wav, trimmed to 60s, before Demucs:
        # (a) torch>=2's mono->stereo expand() creates an aliased view that
        # crashes Demucs's in-place ops on mono uploads (same fix as
        # raga_v2_pipeline), and (b) trimming before separation instead of
        # after cuts Demucs latency on longer uploads.
        import soundfile as sf_write

        demucs_dir = tempfile.mkdtemp()
        y_mix, sr_mix = librosa.load(tmp_path, sr=44100, mono=True, duration=60.0)
        demucs_in = os.path.join(demucs_dir, "input.wav")
        sf_write.write(demucs_in, np.repeat(y_mix[:, None], 2, axis=1), sr_mix)

        logger.info("Starting Demucs separation for %s (%d bytes)", tmp_path, len(data))
        try:
            loop = asyncio.get_running_loop()
            async with _DEMUCS_SEM:
                vocal_path = await loop.run_in_executor(
                    None, lambda: _separate_vocals_sync(demucs_in, demucs_dir)
                )
            logger.info("Demucs separation done, vocal path: %s", vocal_path)
        except RuntimeError as exc:
            logger.error("Demucs FAILED: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        # Load the isolated vocal track for pitch extraction.
        try:
            y, sr = librosa.load(vocal_path, sr=22050, mono=True, duration=60.0)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not load separated vocals: {exc}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if demucs_dir:
            shutil.rmtree(demucs_dir, ignore_errors=True)

    duration = float(len(y) / sr)
    if duration < 5.0:
        raise HTTPException(status_code=422, detail="clip too short, need at least 15 seconds")

    # pyin (not yin) to match the raga classifier's training pipeline exactly —
    # see train_raga_v2_saraga.py, which extracts features the same way.
    f0, voiced_flag, _ = librosa.pyin(y, fmin=60, fmax=1000, sr=sr)
    frequencies = f0[voiced_flag].astype(np.float64)
    if tonic_est is not None:
        tonic, tonic_method = tonic_est, "essentia"
    else:
        tonic = float(np.median(frequencies)) if len(frequencies) else 130.0
        tonic_method = "median_f0"
    logger.info("Tonic: %.2f Hz (%s)", tonic, tonic_method)

    if len(frequencies) < 10:
        raise HTTPException(
            status_code=422,
            detail="Recording contained too little pitched audio — try singing or playing closer to the mic",
        )

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
        "tonic_method": tonic_method,
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
