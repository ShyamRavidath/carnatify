"""Carnatify — Carnatic music identifier backed by Saraga dataset.

Select any Saraga track from the sidebar, click Analyse, and see:
  • Top-3 raga predictions with confidence bars
  • Top-3 composition matches with similarity scores
  • Lyrics catalog entry (title, raga, composer, meaning) for the top match
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

# ── ANTHROPIC key: st.secrets first, then environment ────────────────────────
try:
    _api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if _api_key:
        os.environ.setdefault("ANTHROPIC_API_KEY", _api_key)
except Exception:
    pass  # secrets file absent — rely on env var

import mirdata

from carnatify.ml.raga_classifier import predict_raga
from carnatify.ml.composition_matcher import match_composition
from carnatify.lyrics.pipeline import LyricsCatalog

_DATA_HOME = "/Users/shyamravidath/carnatify"
_MODELS_DIR = Path(__file__).parent / "models"
_RAGA_MODEL = _MODELS_DIR / "raga_classifier.pkl"
_RAGA_ENC = _MODELS_DIR / "raga_label_encoder.pkl"


# ── cached resources ──────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Scanning saraga track index…")
def _get_track_index() -> list[dict]:
    """Return metadata for every saraga track that has pitch data + tonic."""
    saraga = mirdata.initialize("saraga_carnatic", data_home=_DATA_HOME)
    entries = []
    for tid in saraga.track_ids:
        t = saraga.track(tid)
        has_pitch = bool(
            (t.pitch_path and Path(t.pitch_path).exists())
            or (t.pitch_vocal_path and Path(t.pitch_vocal_path).exists())
        )
        if not has_pitch or t.tonic is None:
            continue
        meta = t.metadata or {}
        work = meta.get("work") or []
        title = work[0]["title"] if work else meta.get("title", tid)
        raaga_list = meta.get("raaga") or []
        raga = ""
        if raaga_list:
            r = raaga_list[0]
            raga = r.get("common_name") or r.get("name", "")
        entries.append(
            {"track_id": tid, "title": title, "tonic": float(t.tonic), "raga": raga}
        )
    return entries


@st.cache_resource(show_spinner=False)
def _get_catalog() -> LyricsCatalog:
    return LyricsCatalog()


@st.cache_data(show_spinner=False, ttl=3600)
def _load_pitch(track_id: str) -> tuple:
    """Load (frequencies_list, tonic) for track_id; returns (None, None) on error."""
    saraga = mirdata.initialize("saraga_carnatic", data_home=_DATA_HOME)
    t = saraga.track(track_id)
    pv = t.pitch_vocal if t.pitch_vocal is not None else t.pitch
    if pv is None or t.tonic is None:
        return None, None
    return pv.frequencies.tolist(), float(t.tonic)


# ── inference ─────────────────────────────────────────────────────────────────

def _run_inference(frequencies, tonic: float) -> tuple[list, list]:
    """Run predict_raga + match_composition in parallel threads."""

    def _raga():
        if not (_RAGA_MODEL.exists() and _RAGA_ENC.exists()):
            return []
        try:
            return predict_raga(
                frequencies,
                tonic,
                model_path=_RAGA_MODEL,
                label_encoder_path=_RAGA_ENC,
                top_k=3,
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
        return f_raga.result(), f_comp.result()


# ── section renderers ─────────────────────────────────────────────────────────

def _render_raga(predictions) -> None:
    st.subheader("Raga")
    if not predictions:
        st.info("Raga model not available, or audio had too little pitched content.")
        return
    for pred in predictions:
        conf = min(1.0, max(0.0, float(pred.confidence)))
        st.progress(conf, text=f"{pred.raga_name}  —  {conf * 100:.1f}%")


def _render_compositions(matches) -> None:
    st.subheader("Composition Matches")
    if not matches:
        st.info("Composition catalog not available or returned no matches.")
        return
    for title, score, _ in matches:
        score = min(1.0, max(0.0, float(score)))
        st.progress(score, text=f"{title}  —  {score * 100:.1f}%")


def _render_lyrics(top_title: str) -> None:
    st.subheader("Lyrics & Meaning")
    catalog = _get_catalog()

    try:
        row = catalog.lookup(top_title)
    except Exception as exc:
        st.warning(f"Lyrics catalog error: {exc}")
        return

    if row is None:
        st.info(f"**{top_title}** is not in the lyrics catalog yet.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Title", row["title"] or "—")
    c2.metric("Raga", row["raga"] or "—")
    c3.metric("Composer", row["composer"] or "Unknown")

    st.divider()

    if row.get("meaning_en"):
        st.markdown("**Meaning & cultural context**")
        st.write(row["meaning_en"])
        if row.get("meaning_generated_at"):
            st.caption(f"Generated: {row['meaning_generated_at'][:10]}")
    else:
        st.caption("No meaning generated yet for this composition.")
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        if not has_key:
            st.warning(
                "Set **ANTHROPIC_API_KEY** in the environment or `.streamlit/secrets.toml` "
                "to enable meaning generation."
            )
        else:
            if st.button("Generate meaning (Claude)", key="btn_gen_meaning"):
                with st.spinner("Calling Claude API…"):
                    try:
                        meaning = catalog.generate_meaning(row["title"])
                    except Exception as exc:
                        st.error(f"Generation failed: {exc}")
                        meaning = None
                if meaning:
                    st.success("Done!")
                    st.write(meaning)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Carnatify",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("Carnatify — Carnatic Music Identifier")
    st.caption(
        "Select a Saraga concert track in the sidebar and click **Analyse** "
        "to identify its raga, match the composition, and read its meaning."
    )

    # ── sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Track Selection")

        with st.spinner("Loading track index…"):
            index = _get_track_index()

        if not index:
            st.error("No saraga tracks found with pitch data.")
            return

        # Group by title for a cleaner dropdown (show rendition count next to name)
        from collections import Counter
        title_counts = Counter(e["title"] for e in index)
        labels = [
            f"{e['title']}  [{e['track_id']}]"
            if title_counts[e["title"]] > 1
            else e["title"]
            for e in index
        ]
        label_to_entry = dict(zip(labels, index))

        chosen_label = st.selectbox(
            "Composition / Rendition",
            labels,
            help="197 tracks with pre-extracted pitch data are available.",
        )
        entry = label_to_entry[chosen_label]

        st.caption(f"**Track ID:** `{entry['track_id']}`")
        st.caption(f"**Raga (metadata):** {entry['raga'] or '—'}")
        st.caption(f"**Tonic:** {entry['tonic']:.1f} Hz")
        st.divider()

        analyse = st.button("Analyse", type="primary", use_container_width=True)

    if not analyse:
        st.info("Select a track in the sidebar, then click **Analyse**.")
        return

    # ── load pitch ────────────────────────────────────────────────────────────
    track_id = entry["track_id"]
    with st.spinner("Loading pitch contour…"):
        freq_list, tonic = _load_pitch(track_id)

    if freq_list is None:
        st.error("Could not load pitch data for this track.")
        return

    import numpy as np
    frequencies = np.asarray(freq_list, dtype=np.float64)
    voiced = int((frequencies > 0).sum())
    st.caption(
        f"Loaded **{len(frequencies):,}** pitch frames "
        f"({voiced:,} voiced) · tonic **{tonic:.1f} Hz**"
    )

    # ── parallel inference ────────────────────────────────────────────────────
    with st.spinner("Analysing raga and composition (running in parallel)…"):
        raga_preds, comp_matches = _run_inference(frequencies, tonic)

    # ── display results ───────────────────────────────────────────────────────
    left, right = st.columns(2)
    with left:
        _render_raga(raga_preds)
    with right:
        _render_compositions(comp_matches)

    st.divider()

    top_title = comp_matches[0][0] if comp_matches else None
    if top_title:
        _render_lyrics(top_title)
    else:
        st.subheader("Lyrics & Meaning")
        st.info("No composition match available to look up.")


if __name__ == "__main__":
    main()
