# Carnatify

A Carnatic music identification and enrichment app: given a live recording or an archival clip, it identifies the raga (melodic framework) and the specific composition being performed, and surfaces the composition's lyrics and an English meaning. Built for concert-goers and students of Carnatic music who don't recognize what's being sung in real time.

Carnatic performance is inherently variable — the same composition, in the same raga, sounds different across artists (tonic, tempo, gamaka ornamentation), and improvised passages (alapana) have no fixed melody at all. Shazam-style acoustic fingerprinting fails on this outright, and static raga-reference apps don't listen to anything. Carnatify instead extracts the predominant pitch contour, normalizes it by the estimated tonic, and matches on that normalized representation — matching the actual structure of the genre rather than the raw waveform.

## What's actually working vs. what's still research

This project has an ML core with three sub-tasks, each at a different stage of maturity. Numbers below are measured, not aspirational:

| Module | Status | Measured performance |
|---|---|---|
| **Composition matching** | Shipping | Fast (L2 distance over 500-point tonic-normalized, resampled pitch contours), tempo- and tonic-invariant. Data-limited: most of the 197-track reference catalog has only one recording per composition, so it can only recognize a performance that closely resembles the one indexed rendition (~16% top-1 on the subset of compositions with 2+ reference recordings). |
| **Raga classification** | Shipping, below target | RandomForest over a 480-dim tonic-normalized pitch-histogram + bigram/trigram feature vector. Currently **40.5% top-1 / 60.8% top-3** across 53 ragas with ≥5 training tracks each — a near-linear function of tracks-per-raga (measured: 73% top-1 is reachable, but only for ragas with 20+ training tracks; the median raga has ~5). Actively being scaled up via a targeted concert-audio scraping pipeline; see `HANDOFF_RAGA_DATA.md`. |
| **Tala (rhythmic cycle) detection** | Not shipped | Unsupervised beat-tracking + cycle-periodicity approaches topped out at 32.9% (vs. a 72% majority-class baseline of always guessing Ādi) across 170 Saraga tracks — concluded not viable without supervised training on cycle annotations. Excluded from the API and the frontend; not a claimed feature. |
| **Lyrics & meaning** | Shipping (demo-scale) | 3,252 composition titles seeded from performance metadata; meanings are generated on-demand via Gemini and cached. A small number are pre-generated as a fallback for HuggingFace Spaces' ephemeral filesystem — most titles generate a meaning on first request rather than serving a pre-baked one. |

The honest read: this is a working, deployed research prototype that proves the pitch-contour-matching approach is sound, with raga classification as the open problem (data-bound, not modeling-bound — see below) and tala detection abandoned as not tractable with the unsupervised methods tried.

## Architecture

```
carnatify/
├── src/carnatify/         Core Python package (installable, tested)
│   ├── audio/              Feature extraction, catalog building, data loading utilities
│   ├── ml/                  raga_classifier, raga_features, composition_matcher,
│   │                        dtw_matcher, contour_preprocessor, tala_analyzer/detector/validator
│   ├── lyrics/               scraper (karnatik.com), database, Gemini meaning_generator, pipeline
│   └── ui/                  Streamlit pipeline glue (see "Streamlit MVP" below)
├── tests/                  pytest suite: audio, composition, lyrics, pipeline, raga, tala
├── frontend/               Next.js app — landing page + two-tab demo (archive playback / live mic)
│   └── deployed at https://carnatify.vercel.app
├── backend/                FastAPI service — /health, /tracks, /predict, /predict-audio, /meaning/{title}
│   └── deployed on HuggingFace Spaces (Docker SDK)
├── models/                 raga_classifier.pkl + label encoder, composition_catalog.npz + meta
├── data/                   lyrics.db (SQLite), raga_aliases.json, scraped_compositions.json
├── app.py                  Deprecated Streamlit MVP (hard-coded local paths; superseded by the web stack)
├── build_catalog.py, generate_meanings.py, scrape_concerts.py, download_concerts.py
│                           Pipeline/data-collection scripts (see HANDOFF*.md for what each does and why)
├── carnatify_prd.md        Original product requirements document
└── DEPLOY.md               Backend (HF Spaces) + frontend (Vercel) deployment steps
```

### Inference pipeline (live microphone path)

```
MediaRecorder (browser) → POST /predict-audio
  → Demucs htdemucs (vocal separation, two-stems)
  → librosa.pyin (pitch extraction, 60-1000 Hz)
  → tonic = median of voiced F0
  → 480-dim tonic-normalized histogram + bigram/trigram features
  → RandomForest (raga) + L2-distance catalog lookup (composition), run concurrently
  → {raga: [...], matches: [...]}
```
Demucs is the latency bottleneck: ~65s for a 30s clip on CPU, with a 2–3 minute cold start on HuggingFace's free tier while the separation model downloads. There is no GPU on the free deployment tier.

## Setup & running

**Python package** (feature extraction, ML, lyrics pipeline, tests):
```bash
pip install -e .[dev]      # from pyproject.toml — torch, torchaudio, essentia, librosa,
                            # mirdata, scikit-learn, dtaidistance, anthropic/google-genai, etc.
pytest tests/
```

**Frontend** (Next.js, local dev):
```bash
cd frontend && npm install && npm run dev
```

**Backend** (FastAPI, local dev):
```bash
cd backend && pip install -r requirements.txt
uvicorn main:app --reload
```

Full deployment steps (HuggingFace Spaces for the backend, Vercel for the frontend, environment variables, Space secrets) are in [`DEPLOY.md`](DEPLOY.md).

## Data & models

- **Raga classifier training data**: CompMusic Carnatic raga dataset (pre-extracted pitch features only — raw audio access was requested from MTG/UPF and never granted) plus a growing real-audio corpus (Saraga Carnatic recordings + scraped concert audio from archive.org), processed through the same Demucs+pyin pipeline used at inference time.
- **Composition catalog**: 197 reference contours built from Saraga Carnatic recordings.
- **Lyrics/meaning catalog**: seeded from Saraga + scraped concert metadata; meanings generated via Gemini 2.5 Flash, SQLite-cached.

None of the large source datasets (Saraga, CompMusic feature dumps, scraped concert audio) are committed to this repository — see `.gitignore`. `models/raga_classifier.pkl` and the precomputed pitch bundle used by the backend are checked in since they're needed to run inference without re-deriving them.

## Current status & known limitations

- Raga classification is the primary open problem: accuracy scales with tracks-per-raga, and most ragas in the current corpus are below the ~20-track threshold where the classifier crosses 70% top-1. A CNN/TDNN alternative was tried and abandoned (see below) — the data ceiling, not the model architecture, is the bottleneck.
- A from-scratch CNN on log-CQT features was tested on Colab GPU and hit exact chance-level validation accuracy despite a passing sanity/overfit check — confirming the failure mode is too little audio, not a pipeline bug.
- Tala detection is not exposed anywhere in the product; it was evaluated and set aside as not viable with unsupervised beat-tracking.
- The original Streamlit MVP (`app.py`) is deprecated in favor of the Next.js + FastAPI stack and is not deployed.
- No rate limiting or request queueing on the inference backend yet — concurrent `/predict-audio` calls on the free CPU tier can be slow or resource-constrained.

See `carnatify_prd.md` for the original product requirements and `HANDOFF_RAGA_DATA.md` for the active data-collection workstream targeting improved raga accuracy.
