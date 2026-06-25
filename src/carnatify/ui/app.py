"""Streamlit MVP for Carnatify — upload audio and identify raga, tala, and composition."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import streamlit as st

from carnatify.audio.utils import load_audio, validate_audio
from carnatify.config import (
    COMPOSITION_CONFIDENCE_THRESHOLD,
    MIN_AUDIO_DURATION_SECONDS,
    RAGA_CONFIDENCE_THRESHOLD,
    SAMPLE_RATE,
    TALA_CONFIDENCE_THRESHOLD,
)
from carnatify.schemas import CarnatifyResult
from carnatify.ui.pipeline import CarnatifyPipeline

_LANGUAGE_COLORS = {
    "telugu": "violet",
    "sanskrit": "orange",
    "tamil": "green",
    "kannada": "blue",
}


@st.cache_resource(show_spinner=False)
def get_pipeline() -> CarnatifyPipeline:
    """Build the pipeline once and keep its models resident across reruns."""
    return CarnatifyPipeline()


def _clamp(value: float) -> float:
    """Clamp a confidence/score into the [0, 1] range st.progress expects."""
    if value is None or not np.isfinite(value):
        return 0.0
    return float(min(1.0, max(0.0, value)))


def _render_raga(result: CarnatifyResult) -> None:
    st.subheader("Raga")
    if not result.raga_predictions:
        st.caption("No raga model available — train a model to enable this.")
        return

    for pred in result.raga_predictions:
        label = pred.raga_name
        if pred.confidence < RAGA_CONFIDENCE_THRESHOLD:
            label += "  ·  _Uncertain_"
        st.markdown(f"**{label}**")
        st.progress(_clamp(pred.confidence), text=f"{pred.confidence * 100:.0f}%")


def _render_tala(result: CarnatifyResult) -> None:
    st.subheader("Tala")
    tala = result.tala_prediction
    if tala is None:
        st.caption("Tala detection unavailable.")
        return

    if tala.tala_name == "Unknown":
        st.markdown("**Unknown** — could not confidently detect a tala.")
    else:
        st.markdown(f"**{tala.tala_name}**")
    st.progress(_clamp(tala.confidence), text=f"{tala.confidence * 100:.0f}%")

    details = []
    if tala.beats_per_cycle:
        details.append(f"{tala.beats_per_cycle} beats/cycle")
    if tala.cycle_duration_seconds:
        details.append(f"{tala.cycle_duration_seconds:.1f}s cycle")
    if details:
        st.caption("  ·  ".join(details))


def _render_compositions(result: CarnatifyResult) -> None:
    st.subheader("Composition Match")
    if not result.composition_matches:
        st.caption("No reference catalog available — build one to enable matching.")
        return

    for rank, match in enumerate(result.composition_matches, start=1):
        name = match.composition_name or match.composition_id
        composer = f" · {match.composer}" if match.composer else ""
        suffix = "  ·  _Low confidence_" if match.similarity_score < COMPOSITION_CONFIDENCE_THRESHOLD else ""
        st.markdown(f"**{rank}. {name}**{composer}{suffix}")
        st.progress(
            _clamp(match.similarity_score),
            text=f"similarity {match.similarity_score * 100:.0f}%",
        )


def _render_lyrics(result: CarnatifyResult) -> None:
    st.subheader("Lyrics & Meaning")
    lyrics = result.lyrics
    if lyrics is None:
        st.caption("Lyrics not found for the top composition match.")
        return

    color = _LANGUAGE_COLORS.get(lyrics.language.lower(), "gray")
    st.markdown(f"**{lyrics.composition_name}** — :{color}[{lyrics.language}]")

    st.markdown("**Pallavi**")
    st.text(lyrics.pallavi)
    if lyrics.anupallavi:
        st.markdown("**Anupallavi**")
        st.text(lyrics.anupallavi)
    for i, charanam in enumerate(lyrics.charanam, start=1):
        st.markdown(f"**Charanam {i}**")
        st.text(charanam)

    with st.expander("Show English meaning"):
        if result.meaning is not None and result.meaning.meaning:
            st.write(result.meaning.meaning)
        else:
            st.caption("Meaning not available (no cached meaning / API key).")


def _load_uploaded_audio(uploaded) -> tuple[np.ndarray, int]:
    """Persist the upload to a temp file so librosa can decode any container."""
    suffix = Path(uploaded.name).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name
    try:
        return load_audio(tmp_path, target_sr=SAMPLE_RATE)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def main() -> None:
    st.set_page_config(page_title="Carnatify — Carnatic Music Identifier", layout="wide")
    st.title("Carnatify — Carnatic Music Identifier")
    st.write(
        "Upload a Carnatic music clip to identify its **raga**, **tala**, and likely "
        "**composition**, then read the lyrics and an English meaning."
    )

    uploaded = st.file_uploader(
        "Upload audio (MP3 / WAV / FLAC)", type=["mp3", "wav", "flac"]
    )
    st.info(
        "Recording from a microphone? Record with any app, then upload the file here.",
        icon="🎙️",
    )

    if uploaded is None:
        st.info("Upload an audio file to begin.")
        return

    try:
        audio, sr = _load_uploaded_audio(uploaded)
    except Exception as exc:  # noqa: BLE001 — surface any decode failure to the user
        st.error(f"Could not read audio file: {exc}")
        return

    st.audio(uploaded)

    if not validate_audio(audio, sr, min_duration=MIN_AUDIO_DURATION_SECONDS):
        st.warning(
            f"Please provide at least {MIN_AUDIO_DURATION_SECONDS} seconds of audio."
        )
        return

    duration = audio.size / sr if sr else 0.0
    st.caption(f"Loaded {duration:.1f}s of audio at {sr} Hz.")

    if not st.button("Identify", type="primary"):
        return

    progress = st.progress(0, text="Starting analysis...")
    try:
        with st.spinner("Analyzing audio..."):
            pipeline = get_pipeline()
            progress.progress(25, text="Extracting features...")
            result = pipeline.run(audio, sr)
            progress.progress(100, text="Done")
    except Exception as exc:  # noqa: BLE001 — show pipeline failures rather than crash
        progress.empty()
        st.error(f"Analysis failed: {exc}")
        return

    progress.empty()

    col1, col2 = st.columns(2)
    with col1:
        _render_raga(result)
        _render_tala(result)
    with col2:
        _render_compositions(result)

    _render_lyrics(result)


if __name__ == "__main__":
    main()
