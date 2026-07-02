# Carnatify — Production Handoff Document
**Prepared for:** Fable 5 (next agent, zero prior context)  
**Written by:** Claude Sonnet 4.6, 2026-07-01  
**Status:** Project is partially deployed; ML accuracy is the primary blocker to production.

---

## 1. Project Vision & Goals

### What Carnatify is
A Carnatic music identification and enrichment app with three interlocking features:
1. **Raga classification** — identify the melodic framework (raga) being performed from a pitch contour, even during improvised passages (alapana) with no fixed melody
2. **Composition matching** — identify which specific kriti (composition) is being performed, tolerant of artist variation, tempo differences, and improvisation
3. **Lyrics & meaning** — surface the original-language lyrics (sahityam) and an English meaning for the matched composition

### Who it's for
- **Concert-goers** who don't recognize what's being sung and want to know in real-time
- **Students** who want to verify compositions and access lyrics for study
- **The builder (Deepti)** — practicing Carnatic musician, HS student, built it for personal use first

### End state
App Store release on iOS, available to the global Carnatic music community. The web app on Vercel is an intermediate milestone to prove the pipeline; the iOS layer wraps the same ML core.

### Why this doesn't exist already
- **Shazam** performs acoustic fingerprinting — matches a specific waveform to a stored recording. Carnatic music is inherently variable: same composition, same raga, but every artist performs at different shruti (tonic), tempo, with different gamakas (ornamental variations). Shazam fails completely on live Carnatic audio.
- **Raga reference apps** (e.g., "Carnatic Raga" on iOS) are static lookup databases — you search by raga name, they don't listen to anything.
- **Western MIR tools** (chroma features, beat tracking, key detection) are designed for tonal harmony and fixed tempo — fundamentally wrong representations for Carnatic music which is monophonic, gamaka-heavy, and has complex rhythmic cycles.

Carnatify's approach: extract the predominant pitch contour from the vocal/melodic line, normalize by the estimated tonic, and match against tonic-normalized reference contours. This is genre-specific and correct.

---

## 2. Original Buildspec vs Current Reality

The PRD (`carnatify_prd.md`) was approved June 2026. Here is the honest status of each module:

### 2.1 Raga Classifier

**Buildspec promised:** ≥75% accuracy on held-out test set, covering ≥60 ragas, ≤3s inference time on CPU.

**What was built:**
- `src/carnatify/ml/raga_features.py`: 480-dim feature vector — 120-bin tonic-normalized pitch histogram + 12×12 pitch-class bigram matrix + 6×6×6 trigram tensor. Features capture melodic motion, not just note inventory.
- `src/carnatify/ml/raga_classifier.py`: Two paths — `RagaClassifier` (PyTorch CNN/TDNN, **not used in production**) and `predict_raga()` (sklearn RandomForest from joblib pkl, **this is what ships**).
- `train_raga.py`: Trains on `compmusic_raga` via mirdata, using pre-extracted `.pitch` and `.pitch_post_processed` files. 477 tracks, 40 ragas. Best model: RandomForest, 77.8% 5-fold CV.
- `models/raga_classifier.pkl` (28MB), `models/raga_label_encoder.pkl`: The production model, in git.

**What works:** 77.8% cross-validation accuracy on the CompMusic dataset features. The feature extraction pipeline (histogram + bigrams + trigrams) is principled and more expressive than histogram-only baselines.

**What is broken / underperforming:**

**CRITICAL — Domain mismatch between training and inference.** The CompMusic dataset provides pre-extracted pitch using MELODIA (Vamp plugin, proprietary, produces smoothed, post-processed vocal pitch contours). Production inference uses `librosa.pyin` on Demucs-separated vocals. These are **categorically different pitch pipelines**: MELODIA fills silence with interpolated values and applies smoothing; pyin produces raw YIN-based F0 with voiced/unvoiced flags and no smoothing. The training features were computed from MELODIA pitch. Inference features are computed from pyin pitch on Demucs output. The model has never seen pyin-derived features during training.

This is the fundamental reason the live-audio raga classifier underperforms. A Kalyani test on a real recording returned wrong results despite Kalyani being in the 40-raga training vocabulary.

**Retrain attempts and their outcomes (commit f2273df):**
- **Candidate A (CompMusic + augmentation):** Replaced raw `.pitch` with `.pitch_post_processed` (closer to MELODIA), added pitch-shift ±1 semitone and white-noise augmentation. Result: 77.2% 5-fold StratifiedGroupKFold — within noise of baseline 77.8%. Not an improvement.
- **Candidate B (Real audio — Demucs+pyin pipeline):** Used Saraga Carnatic audio (the only freely accessible labeled Carnatic audio) as a stand-in while waiting for CompMusic audio access. Ran Demucs → pyin → 480-dim features. Result: **5.0% accuracy, near random chance on 43 classes.** Root cause: Saraga Carnatic has ~3 tracks/raga with StratifiedGroupKFold (groups = tracks, so splits only have 1-2 tracks for training). Model cannot generalize from 1-2 training examples.
- Both candidates archived in `models/candidates/`; neither ships.

**CompMusic audio situation:** The CompMusic dataset (`RagaDataset/Carnatic/features/`) contains pre-extracted features only — not the raw audio files. Audio access requires manual request to mtg-info@upf.edu. Request not yet sent as of 2026-07-01. If CompMusic audio becomes available, the correct fix is to run the Demucs+pyin pipeline over it to build a large (477-track, 40-raga) real-audio training set that matches inference exactly.

**Vocabulary:** 40 ragas only. Common ragas **not in the vocabulary**: Saveri, Arabhi, Darbar, Keeravani, Abheri, Bhupalam, Poorvikalyani, and others. These return `None` from `raga_aliases.json` lookup and are OOV for the classifier — the model will hallucinate a wrong in-vocabulary raga instead.

**Confidence calibration:** Top prediction confidence is typically 10–22% even for correct predictions. This is not a bug — it's expected from a multi-class RF trained on 40 ragas with limited data. But it makes the confidence scores meaningless as a quality signal to users.

**What was explicitly deferred:** PyTorch CNN/TDNN path (`RagaClassifier` class, `RagaCNN`, `RagaTDNN`) — these exist in `src/carnatify/ml/raga_model.py` and `raga_dataset.py` but are never called in production. The sklearn path is faster and currently superior given the data constraints.

---

### 2.2 Tala Detector

**Buildspec promised:** Detect Adi, Misra Chapu, Rupaka, Khanda Chapu talas with ≥70% accuracy.

**What was built:**
- `src/carnatify/ml/tala_analyzer.py`: Rule-based beat-cycle analyzer. Uses librosa beat tracking, autocorrelation of inter-beat intervals to find the dominant period, maps beat count to a tala name.
- `src/carnatify/ml/tala_detector.py`: Thin wrapper with confidence threshold.
- `src/carnatify/ml/tala_validator.py`: Evaluation against Saraga ground truth annotations.
- `detect_tala()` standalone function.

**What is broken:** **Near-zero accuracy on Saraga ground truth.** The Saraga `beats_per_cycle` annotation encodes **subdivisions** (aksharas), not beats. Adi tala = 8 beats × 4 aksharas/beat = 32 subdivisions in the ground truth file, but the code's `_BEATS_TO_TALA` maps `8 → "Adi"` and expects the beat count directly. The autocorrelation algorithm operating on inter-beat intervals (at the beat level) will find 8 beats per cycle, but the ground truth says `32`, so every valid Adi detection is scored as wrong.

This was identified as the root cause (see original HANDOFF) but **the fix was never implemented.** The tala detector was effectively abandoned rather than fixed.

**What was explicitly deferred:** Tala detection was removed from the live inference pipeline entirely. The web app frontend does not display tala results. `/predict` and `/predict-audio` return no tala field.

**Fix required:** Divide ground truth `beats_per_cycle` by the correct subdivision factor (4 for Adi, 2 for Rupaka, 3 for Misra Chapu, 5 for Khanda Chapu) before comparison, or re-read the Saraga annotation format documentation carefully.

---

### 2.3 Composition Matcher

**Buildspec promised:** ≥70% top-1 accuracy, DTW or cross-correlation matching, 100–150 composition catalog.

**What was built:**
- `src/carnatify/ml/composition_matcher.py`: Two implementations:
  1. `CompositionMatcher` class: full DTW via `DTWMatcher` + `ContourPreprocessor` — **not used in production**
  2. `match_composition()` flat function: L2 distance on fixed-length (500-point) tonic-normalized z-scored contours, similarity = `1 / (1 + dist / N_POINTS)` — **this is what ships**
- `models/composition_catalog.npz`: 197 × 500 float32 array of reference contours
- `models/composition_catalog_meta.json`: track_id + title for each of the 197 tracks
- `build_catalog.py`, `backend/precompute_tracks.py`: tools to rebuild the catalog

**What works:** The L2-on-resampled-contours approach is fast (milliseconds), tempo-invariant by design (resampling normalizes tempo), and tonic-invariant (cents relative to Sa). It returns plausible results.

**What is broken / underperforming:**
- **Data ceiling:** The catalog has 197 tracks from 197 distinct Saraga recordings, but many compositions have only one rendition. Matching a query against a single reference means the matcher can only recognize a composition if the user's performance closely resembles the one indexed recording. The PRD evaluation (16% top-1 on 19 compositions with 2+ renditions) reflects this ceiling, not a code bug.
- **L2 vs DTW:** The shipped code uses L2 distance on fixed-length resampled contours. This is tempo-invariant (resampling handles it) but **not alignment-invariant**: if the user starts singing from the anupallavi instead of the pallavi, the contour offset breaks matching. True DTW would handle this, but the `DTWMatcher` implementation was not deployed because its O(N²) complexity on 197 × 60s-worth of contours was too slow for a web request.
- **Score inflation:** Similarity scores are systematically high (0.93–0.95 for top-3 matches) because the L2 distance on 500-point z-scored contours clusters all scores in a narrow band. These scores are not meaningful probability estimates.

**What was explicitly deferred:** Subsequence DTW (partial query matching), multi-segment averaging across multiple renditions, and catalog expansion beyond the 197 Saraga tracks.

---

### 2.4 Lyrics & Meaning Pipeline

**Buildspec promised:** Original-language lyrics (sahityam) and English meaning for matched compositions. Catalog broad from day one.

**What was built:**
- `src/carnatify/lyrics/pipeline.py`: `LyricsCatalog` class — SQLite-backed, Gemini-powered on-demand meaning generation with caching
- `src/carnatify/lyrics/scraper.py`: Karnatik.com scraper (lyrics from public domain source)
- `src/carnatify/lyrics/meaning_generator.py`: Gemini 2.5 Flash meaning generation
- `data/lyrics.db`: 3,252 title entries seeded from Saraga metadata. Schema: `title, composer, raga, language, lyrics_original, meaning_en, meaning_generated_at`
- `backend/data/lyrics.db`: Copy deployed to HF Space (same 3,252 titles, 8 meanings)
- `generate_meanings.py`: Resumable batch generator, 7s pacing, ResourceExhausted backoff

**What works:** The 8 pre-generated meanings are real and correct. The on-demand `/meaning/{title}` endpoint generates meanings live via Gemini on first request and caches them. The generation quality is good.

**What is broken / underperforming:**
- **3,244 titles have no pre-generated meaning.** The free Gemini API quota was exhausted after generating 8 during a batch run. The `generate_meanings.py` script is resumable and correct — it just needs quota.
- **lyrics_original is empty for most titles.** The Karnatik.com scraper was implemented but not actually run at scale (only the 3,252 titles from Saraga metadata were seeded; the actual lyric text was not bulk-scraped). The meaning generation prompt works with just the title + composer when lyrics aren't available.
- **Cache is ephemeral on HF Spaces.** HF's free tier has an ephemeral filesystem — the `lyrics.db` resets on every Docker rebuild. Any meanings generated at runtime are lost. The pre-baked 8 meanings in the committed `backend/data/lyrics.db` survive rebuilds; runtime-generated ones don't.

**Note on Anthropic → Gemini switch:** The original meaning generator used Claude (Anthropic API). It was switched to Gemini 2.5 Flash (commit 85d2271) because the Gemini free tier has much higher rate limits for this use case.

---

### 2.5 Streamlit App (Original MVP)

**Buildspec promised:** Working Python MVP with a Streamlit UI taking audio input and returning raga, tala, composition, lyrics.

**What exists:** `app.py` at the repo root. Loads `saraga_carnatic` via mirdata, lists tracks with pitch data + tonic, runs `predict_raga()` + `match_composition()` + `LyricsCatalog` for a selected track.

**Current status:** **Functional but unmaintainable for production.** Hard-coded `data_home='/Users/shyamravidath/carnatify'` path throughout. Requires local Saraga dataset (13.5 GB). No live audio input. No Demucs integration. Not deployed anywhere. Effectively replaced by the Next.js + FastAPI web stack.

---

### 2.6 Next.js Frontend

**Buildspec promised:** Not in original PRD (web frontend was additive).

**What was built:**
- `frontend/app/page.tsx`: Landing page with scroll-driven SVG waveform hero, "How It Works" section, CTA to /demo
- `frontend/app/demo/page.tsx`: Two-tab demo — "Saraga Archive" (select from 197 tracks, hit Analyse) and "Record Audio" (microphone, 24-bar live waveform, auto-stop at 60s, submit to /predict-audio)
- `frontend/components/`: `WaveSkeleton` (loading animation), `ScoreBar` (confidence bars), `WaveformHero` (animated SVG), `Nav`, `Reveal`, `HowItWorks`
- `frontend/lib/api.ts`: Typed fetch wrappers for all backend endpoints

**What works:** Both tabs are wired to the real backend. Results panels show raga predictions with confidence bars, composition matches, and a meaning panel with on-demand "Generate meaning" button. Deployed at `https://carnatify.vercel.app`.

**Known issues:**
- No error recovery UX if the HF Space is cold-starting (the first request can take 3 minutes while the htdemucs model downloads — the user sees a spinner with no feedback)
- No timeout/retry logic in `predictAudio()` — the fetch can silently hang for the browser's default timeout
- MediaRecorder content-type varies by browser: Chrome sends `audio/webm;codecs=opus`, Safari sends `audio/mp4`, Firefox sends `audio/ogg` — all handled on the backend, but not tested cross-browser
- No mobile layout testing — the mic permission UX on iOS Safari is untested
- Progress messages ("Uploading recording…" → "Separating vocals…" → "Analysing raga…") are timer-based guesses, not actual backend events. If Demucs takes longer than 60s on a cold start, the UI says "Analysing raga…" while still waiting for Demucs.

---

### 2.7 FastAPI Backend (HuggingFace Spaces)

**Buildspec promised:** Not in original PRD (web backend was additive).

**What was built:** `backend/main.py` — FastAPI app serving:
- `GET /health` → `{"status": "ok"}`
- `GET /tracks` → 197 Saraga tracks (from precomputed `tracks_meta.json`)
- `POST /predict` → raga + composition matches for a Saraga track_id (uses precomputed pitch)
- `POST /predict-audio` → raga + composition matches from uploaded audio file (runs Demucs + pyin)
- `GET /meaning/{title}` → composer + English meaning (Gemini on-demand)

**What works:** All endpoints are live and returning correct responses. `/predict-audio` runs the full Demucs + pyin + feature extraction + raga classification + composition matching pipeline end-to-end.

**Performance:** `/predict-audio` takes ~65s for a 30s audio clip on CPU (Demucs bottleneck). First request after cold start also downloads the htdemucs model (~80 MB) — allow 2-3 minutes.

**Known issues:**
- No rate limiting. Any user can POST unlimited audio files, triggering unlimited Demucs jobs. On the free tier (2 vCPU, 16 GB RAM), concurrent requests will OOM-kill the container.
- No request queue. Concurrent Demucs runs on 2 vCPU will be extremely slow (Demucs is not thread-safe in CPU mode with shared model weights).
- The `FRONTEND_ORIGIN` CORS header is currently set to `"*"` as fallback — should be restricted to `https://carnatify.vercel.app` in production.
- Ephemeral filesystem: the htdemucs model cache (`~/.cache/torch/hub/`) and any runtime-generated lyrics meanings are lost on rebuild.

---

### 2.8 Concert Metadata Scraper (shankarkrish.blog)

**Buildspec promised:** Scrape concert metadata to expand composition catalog + raga labels for retraining.

**What was built:**
- Scraper for `shankarkrish.blog/carnatic-vocal/` — 3,698 concert records collected into `data/scraped_compositions.json`, with fields: title, raga_raw, raga_canonical, composer, concert_date, artist
- `data/raga_aliases.json`: 958 raw raga spellings (from scraped data), 684 normalized to canonical form, 274 mapped to `null` (OOV / unrecognized variants)
- `download_concerts.py` + `train_raga_v2_archive.py`: Downloads the audio for each scraped concert from archive.org; extracts 65s segment per track, runs Demucs+pyin, stores 480-dim features in `data/raga_v2_cache/archive/`
- `data/concert_audio/`: 224 MP3 files downloaded across 21 raga labels (the ragas with the most shankarkrish.blog entries)

**What works:** The scraping and download pipeline runs. The 224 concert audio files are downloaded and organized by raga name. The Demucs+pyin feature extraction pipeline runs over them.

**What is underperforming:** The archive.org concert audio + Saraga audio combined into a real-audio training set yielded 5% CV accuracy (commit f2273df evaluation). Root cause: too few tracks per raga even after combining both sources. The shankarkrish.blog concerts give more data but not enough by raga category — many ragas have 1-3 concerts total. Minimum viable training set for a RandomForest to generalize across tracks is ~10-15 tracks per raga with StratifiedGroupKFold.

---

### 2.9 Audio Inference Pipeline (Live Mic Recording)

**Buildspec promised:** Accept ≥30s audio, return raga + composition in ≤5s.

**Current pipeline:**
```
MediaRecorder (browser, WebM/M4A/OGG) 
→ POST /predict-audio (multipart)
→ NamedTemporaryFile(suffix from Content-Type)
→ librosa.load(tmp_path, duration=5.0) [validation check]
→ asyncio run_in_executor → Demucs htdemucs --two-stems=vocals
   output: demucs_dir/htdemucs/{stem}/vocals.wav
→ librosa.load(vocals.wav, duration=60.0)
→ librosa.pyin(fmin=60, fmax=1000)  [pitch extraction]
→ tonic = median of voiced F0
→ extract_features(frequencies, tonic) [480-dim]
→ ThreadPoolExecutor: predict_raga + match_composition
→ return {raga, matches, tonic, duration}
```

**Latency:** ~65s for 30s audio on CPU. This is **unacceptable for production UX** where the PRD specified ≤5s.

**Root cause:** Demucs `htdemucs` on CPU with a single 30s audio clip takes ~60-90s. There is no faster drop-in.

**Alternatives not yet explored:**
- `demucs` model `mdx_extra_q` is smaller/faster but still CPU-bound
- `spleeter` (older, much faster on CPU but lower vocal separation quality)
- Running pitch extraction directly on the mixed audio with a robust multi-pitch estimator (skipping vocal separation entirely) — loses quality but gains 10× speed
- GPU acceleration — not available on HF free tier

---

## 3. Full Repository Map

### Root-level files
| File | Type | Description |
|------|------|-------------|
| `app.py` | Deprecated | Original Streamlit MVP. Hard-coded paths, requires local Saraga. Not deployed. |
| `train_raga.py` | Production-adjacent | sklearn raga classifier trainer on CompMusic features. Hard-coded `data_home`. |
| `raga_v2_pipeline.py` | Experimental | Shared Demucs+pyin feature extraction pipeline for retrain candidates. Not imported by production. |
| `train_raga_v2_saraga.py` | Experimental | Real-audio retrain over Saraga Carnatic tracks. |
| `train_raga_v2_archive.py` | Experimental | Real-audio retrain over archive.org concert downloads. |
| `train_raga_v2_evaluate.py` | Experimental | Side-by-side evaluation of CompMusic vs real-audio retrain candidates. |
| `download_concerts.py` | Production-adjacent | Downloads concert audio from archive.org based on shankarkrish.blog scrape. |
| `build_catalog.py` | Production-adjacent | Builds composition_catalog.npz from Saraga pitch contours. |
| `generate_meanings.py` | Production-adjacent | Batch Gemini meaning generator. Resumable. Requires `GEMINI_API_KEY`. |
| `pyproject.toml` | **Broken** | `build-backend = "setuptools.backends._legacy:_Backend"` does not exist. `pip install -e .` fails. Hard-coded `requires-python = ">=3.10"`. |
| `carnatify_prd.md` | Documentation | Original product requirements document. |
| `DEPLOY.md` | Documentation | Backend + frontend deployment instructions. Some details outdated. |
| `HANDOFF.md` | Documentation | This file. |
| `README.md` | Documentation | Project overview. |
| `.gitignore` | Config | Correctly ignores `saraga1.5_carnatic/`, `venv/`, `data/concert_audio/`, `data/raga_v2_cache/`. **Missing:** `RagaDataset/` is NOT gitignored and is committed (features-only, ~several hundred MB). |
| `.env.local` | **Sensitive** | Gitignored via `.env*`. Contains `GEMINI_API_KEY`. Never committed. |
| `Indian Art Music Raga Recognition Dataset (features).zip` | Data | Zip of RagaDataset — committed to git. Should be gitignored. |

### `src/carnatify/`
| File | Type | Description |
|------|------|-------------|
| `config.py` | Production | Constants: `MODELS_DIR`, `TOP_K_RESULTS`, confidence thresholds. Hard-coded path pointing to `../models/`. |
| `schemas.py` | Production | Pydantic/dataclass models: `AudioFeatures`, `RagaPrediction`, `TalaPrediction`, `CompositionMatch`, `LyricsEntry`, `MeaningEntry`. |
| `audio/feature_extractor.py` | Production | `FeatureExtractor` class — wraps pyin + tonic estimation. Used by `RagaClassifier.classify_audio()` (not the production sklearn path). |
| `audio/catalog.py` | Production | `ReferenceCatalog` — composition catalog loader (used by the OOP `CompositionMatcher`, not the flat function that ships). |
| `audio/data_loader.py` | Experimental | `SaragaLoader` — mirdata-based Saraga track loader. Local dataset required. |
| `ml/raga_classifier.py` | Production | Both paths: `RagaClassifier` (PyTorch, unused in prod) + `predict_raga()` (sklearn, ships). |
| `ml/raga_features.py` | Production | 480-dim feature extraction: histogram + bigrams + trigrams. Shared by train and inference. |
| `ml/raga_model.py` | Unused | `RagaCNN`, `RagaTDNN` PyTorch model definitions. Not deployed. |
| `ml/raga_dataset.py` | Unused | `RagaLabelEncoder`, `RagaDataset` for PyTorch training. Not deployed. |
| `ml/raga_trainer.py` | Unused | PyTorch training loop. Not deployed. |
| `ml/composition_matcher.py` | Production | Two implementations: `CompositionMatcher` (DTW, unused in prod) + `match_composition()` (L2 flat, ships). |
| `ml/composition_evaluator.py` | Experimental | Top-1/top-3/MRR evaluator. |
| `ml/contour_preprocessor.py` | Production | `ContourPreprocessor` — used by OOP `CompositionMatcher`, not the flat function. |
| `ml/dtw_matcher.py` | Unused in prod | `DTWMatcher` — full DTW implementation, too slow for web use. |
| `ml/tala_analyzer.py` | Broken | Beat-cycle analysis. Accuracy near 0% due to ground-truth annotation mismatch. |
| `ml/tala_detector.py` | Broken | Wrapper around `TalaAnalyzer` with threshold. Not called in production. |
| `ml/tala_validator.py` | Broken | Evaluation vs Saraga ground truth. Flawed comparison (subdivisions vs beats). |
| `lyrics/pipeline.py` | Production | `LyricsCatalog` (ships) + `LyricsPipeline` (not called in prod). |
| `lyrics/scraper.py` | Production-adjacent | Karnatik.com lyrics scraper. Correct but not run at scale. |
| `lyrics/meaning_generator.py` | Production | Gemini 2.5 Flash meaning generator. |
| `lyrics/database.py` | Production | SQLite operations for the lyrics catalog. |
| `ui/app.py` | Deprecated | Streamlit UI, local paths, not deployed. |
| `ui/pipeline.py` | Deprecated | Streamlit pipeline orchestrator. |

### `backend/`
| File | Type | Description |
|------|------|-------------|
| `main.py` | **Production** | FastAPI app. The live HF Space code. Keep in sync with `/tmp/hf-space/main.py`. |
| `Dockerfile` | **Production** | Python 3.11-slim, ffmpeg, torch==2.5.1, torchaudio==2.5.1 (pinned), uvicorn on port 7860. |
| `requirements.txt` | **Production** | `torch>=2.2,<2.6`, `demucs>=4.0.0`, `python-multipart`, all deps. |
| `build_space.sh` | Production-adjacent | Assembles `/tmp/hf-space/` from `src/`, `models/`, `data/`. Run before HF push. |
| `precompute_tracks.py` | Production-adjacent | Precomputes `tracks_pitch.npz` + `tracks_meta.json` from local Saraga data. |
| `data/tracks_pitch.npz` | **Data — in git** | 197-track precomputed pitch bundle. 19 MB. Tracked by git-lfs in HF Space. |
| `data/tracks_meta.json` | **Data — in git** | 197 track metadata entries. Small JSON. |
| `data/lyrics.db` | **Data — in git** | 3,252 title entries, 8 meanings. Ephemeral on HF — rebuilt from this copy on each Docker rebuild. |
| `models/raga_classifier.pkl` | **Data — in git** | 28 MB RandomForest. Production model. |
| `models/raga_label_encoder.pkl` | **Data — in git** | 40 raga classes. LabelEncoder. |
| `models/composition_catalog.npz` | **Data — in git** | 197 × 500 reference contour matrix. |
| `models/composition_catalog_meta.json` | **Data — in git** | Track titles + IDs for catalog. |
| `src/` | **Gitignored** | Assembled copy of `src/carnatify/`. Generated by `build_space.sh`. Not committed here. |

### `models/candidates/`
| File | Type | Description |
|------|------|-------------|
| `raga_classifier_compmusic_v2_reference.pkl` | Experimental | 77.2% CV, CompMusic pitch + augmentation. Does not ship. |
| `raga_classifier_saraga_v2_realaudio.pkl` | Experimental | 5.0% CV, real audio via Demucs+pyin. Does not ship. |
| `raga_label_encoder_compmusic_v2_reference.pkl` | Experimental | 40-class encoder matching above. |
| `raga_label_encoder_saraga_v2_realaudio.pkl` | Experimental | 43-class encoder for Saraga audio model. |

### `frontend/`
| File | Type | Description |
|------|------|-------------|
| `app/page.tsx` | Production | Landing page — scroll-driven SVG waveform hero, brand palette, CTA. |
| `app/layout.tsx` | Production | Root layout, Crimson Pro serif font, global metadata. |
| `app/globals.css` | Production | Tailwind + custom animations (`wave-pulse`), brand CSS vars. |
| `app/demo/page.tsx` | Production | Two-tab demo UI. Both tabs share results panels. ~400 lines. |
| `components/WaveSkeleton.tsx` | Production | Loading animation, 40 animated bars, accepts `label: string` prop. |
| `components/ScoreBar.tsx` | Production | Animated confidence bar for raga predictions. |
| `components/WaveformHero.tsx` | Production | Scroll-driven animated waveform SVG. |
| `components/Nav.tsx` | Production | Site navigation. |
| `components/Reveal.tsx` | Production | Scroll-reveal animation wrapper. |
| `components/HowItWorks.tsx` | Production | "How It Works" landing section. |
| `lib/api.ts` | Production | Typed fetch wrappers: `getTracks`, `predict`, `predictAudio`, `getMeaning`. |
| `next.config.mjs` | Production | Next.js config. |
| `tailwind.config.ts` | Production | Tailwind setup. |
| `package.json` | Production | Next.js 14, Phosphor icons, React 18. |
| `.vercel/project.json` | Config | `projectId: prj_nsJUj8BBDJURSLy7zKP4baziYEtt`. Used by `vercel --prod`. |

### Root-level data
| File | Type | Description |
|------|------|-------------|
| `data/lyrics.db` | Data | Source copy of the lyrics DB (3,252 titles, 8 meanings). `backend/data/lyrics.db` is a copy. |
| `data/scraped_compositions.json` | Data | 3,698 concert records from shankarkrish.blog. Has `raga_canonical` field (null for OOV). |
| `data/raga_aliases.json` | Data | 958 raw raga spellings → canonical form map. 274 null (OOV). |
| `data/concert_audio/` | **Gitignored** | 224 MP3 files from archive.org, organized by raga name. Not committed. |
| `data/raga_v2_cache/` | **Gitignored** | Cached Demucs+pyin features from retrain pipeline. |
| `RagaDataset/` | Data — **should be gitignored** | CompMusic feature files only (audio restricted). In git. Large. |
| `Indian Art Music Raga Recognition Dataset (features).zip` | Data — **should be gitignored** | Zip of above. In git. |
| `*.png` (01–13) | Screenshots | Playwright / manual screenshots from testing sessions. Can be deleted. |

### `/tmp/hf-space/` (not in git repo)
The live HF Space is assembled in `/tmp/hf-space/` on the dev machine. Its git remote points to `https://huggingface.co/spaces/shyamravidath/carnatify`. This directory contains the bundled production deployment: `main.py`, `Dockerfile`, `requirements.txt`, `src/`, `models/`, `data/`, plus the HF Space `README.md` header. **Always push from here, not from `backend/`.** After editing `backend/main.py`, mirror the change manually to `/tmp/hf-space/main.py` and push.

---

## 4. Known Bugs & Loopholes

### Bug 1 — Raga classifier domain mismatch (BLOCKS PRODUCTION)
**Description:** The production `raga_classifier.pkl` was trained on CompMusic pre-extracted MELODIA pitch features. Live inference runs `librosa.pyin` on Demucs-separated vocals. These are fundamentally different pitch representations.  
**Root cause:** CompMusic only provides pre-extracted features (not audio). Training was done on what was available. Inference uses a modern, correct pitch extraction pipeline.  
**Severity:** Blocks production accuracy. The classifier sees a completely different feature distribution at inference time than it was trained on.  
**What was tried:** (1) CompMusic `.pitch_post_processed` + augmentation → 77.2% (no improvement). (2) Real-audio Saraga + archive.org → 5% (data sparsity). (3) Email to mtg-info@upf.edu for CompMusic audio — not yet sent.  
**Fix:** Get CompMusic audio (mtg-info@upf.edu), run Demucs+pyin over all 477 tracks, retrain. Expected result: 77%+ accuracy on a genuinely pipeline-matched training set. Use `train_raga_v2_evaluate.py` structure with `raga_v2_pipeline.py`.

### Bug 2 — Tala detector near-zero accuracy (blocks tala feature)
**Description:** `TalaAnalyzer.estimate_beats_per_cycle()` returns the right number (8 for Adi) but the Saraga ground truth `beats_per_cycle` encodes subdivisions (aksharas): Adi = 32 (8 beats × 4 aksharas). Every Adi prediction is scored as wrong because `8 ≠ 32`.  
**Root cause:** Misread of the Saraga annotation format. The field is `beats_per_cycle` but its value is aksharas-per-cycle.  
**Severity:** Blocks tala detection. Feature is entirely absent from the web UI as a result.  
**What was tried:** The validator code was written but the annotation mismatch was identified and not fixed (task was abandoned).  
**Fix:** In `tala_validator.py`, convert ground truth by dividing by the aksharas-per-beat for the tala. Alternatively, reread the Saraga annotation schema at `saraga_carnatic/annotations/beats/` to get the actual format (may use `beats` files with beat times rather than `beats_per_cycle` integers).

### Bug 3 — Composition matcher data ceiling (degrades quality)
**Description:** 16% top-1 accuracy on compositions with ≥2 renditions in the 197-track catalog.  
**Root cause:** Not a code bug. The catalog has one or very few reference renditions per composition. L2 distance matching requires the query to resemble the indexed recording closely.  
**Severity:** Degrades quality significantly. A catalog with 1 rendition per composition cannot generalize across artists.  
**What was tried:** Nothing. The ceiling was documented but not addressed.  
**Fix:** (1) Expand the catalog: download more Saraga tracks (Saraga Audiovisual dataset has additional concert recordings), add archive.org concerts. (2) Multi-rendition averaging: store the mean contour across multiple renditions per composition. (3) Replace L2 with subsequence DTW for partial-query robustness.

### Bug 4 — Demucs CPU latency (blocks production UX)
**Description:** `/predict-audio` takes 60-90s for a 30s audio clip on CPU. PRD requires ≤5s.  
**Root cause:** `htdemucs` model is a 1D convolutional U-Net with encoder-decoder architecture. CPU inference on a full-resolution audio segment is inherently slow.  
**Severity:** Blocks production. 60-90s wait is unacceptable for a mobile app use case.  
**What was tried:** Nothing — accepted as a known constraint of the free HF tier.  
**Fix options (in order of impact):**  
  (a) GPU-enabled HF Space ($0.60/hr on A10G) — 10-20× speedup, estimated 5-10s  
  (b) Skip Demucs entirely: run pyin directly on the mixed audio with higher `fmin`/`fmax` bounds and the vocal-specific model; loses quality but gains 60s  
  (c) Use `spleeter:2stems` (older, CPU-faster, lower quality)  
  (d) Trim input to 15s before Demucs (currently 60s max) — halves latency

### Bug 5 — Confidence scores systematically low and uncalibrated
**Description:** Top raga prediction confidence is 10-22% even for correct predictions. This is shown to users as a percentage bar, which looks like the app is uncertain when it's actually correct.  
**Root cause:** RandomForest `predict_proba()` in a 40-class problem where training data is limited produces well-spread probabilities. This is a consequence of the data volume, not a bug in the code.  
**Severity:** UX degradation. Users may distrust results when they're correct.  
**Fix:** Calibrate the RF probabilities using `sklearn.calibration.CalibratedClassifierCV` with `cv="prefit"`. Or don't show raw confidence — show ordinal rank ("most likely", "also possible") instead.

### Bug 6 — `pyproject.toml` broken (`pip install -e .` fails)
**Description:** `build-backend = "setuptools.backends._legacy:_Backend"` — this class does not exist. Any agent attempting `pip install -e .` will fail.  
**Root cause:** An agent auto-generated this field incorrectly.  
**Severity:** Breaks developer setup. Production code doesn't use `pip install -e .` (it uses `sys.path.insert` instead), so this only affects local dev.  
**Fix:** Change to `build-backend = "setuptools.build_meta"`.

### Bug 7 — RagaDataset and zip committed to git (bloats repo)
**Description:** `RagaDataset/` (CompMusic feature files) and `Indian Art Music Raga Recognition Dataset (features).zip` are tracked in git, bloating the repo history.  
**Root cause:** Missing from `.gitignore` when originally added.  
**Fix:** Add to `.gitignore`, then `git rm --cached -r RagaDataset/ "Indian Art Music Raga Recognition Dataset (features).zip"` + commit.

### Bug 8 — No rate limiting on `/predict-audio`
**Description:** Any user can POST unlimited audio files. Each triggers a ~60-90s Demucs job on CPU. Two concurrent requests will saturate the free tier (2 vCPU, 16 GB RAM) and likely OOM.  
**Root cause:** Not implemented.  
**Severity:** Blocks public launch. One malicious user can take down the Space.  
**Fix:** Add `slowapi` rate limiting to FastAPI (e.g., 2 requests/minute per IP). Also add a request queue or `asyncio.Semaphore(1)` to prevent concurrent Demucs runs.

### Bug 9 — HF Space `FRONTEND_ORIGIN` CORS set to `"*"` by default
**Description:** If `FRONTEND_ORIGIN` env var is not set, CORS allows all origins. The HF Space env var is set, so in practice this is fine, but the fallback is insecure.  
**Root cause:** `_FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")` in `backend/main.py`.  
**Fix:** Change fallback to `"https://carnatify.vercel.app"` or remove the fallback entirely and raise at startup if not set.

### Bug 10 — Frontend has no timeout or cold-start UX
**Description:** The first `/predict-audio` request after a cold HF Space start triggers htdemucs model download (~80 MB) + container init. Total time: 2-4 minutes. The frontend has no timeout — the fetch will hang until the browser's default network timeout.  
**Root cause:** Not implemented.  
**Fix:** Add `AbortController` with a 5-minute timeout in `predictAudio()`. Add a "warming up the model…" message if the request takes >30s with no response.

### Bug 11 — `lyrics.db` in git contains scraped data (license unclear)
**Description:** `data/lyrics.db` and `backend/data/lyrics.db` are committed to git and contain 3,252 title/composer entries seeded from Saraga Carnatic metadata. The Saraga data is under CC-BY-NC-SA. The generated meanings are LLM-generated from the title alone (no scraped text), so those should be fine.  
**Severity:** Legal uncertainty for public release.  
**Fix:** Verify Saraga's CC-BY-NC-SA allows redistribution of the metadata (titles, composer names, raga names) — these are likely factual/public domain. Add attribution. The scraper targets karnatik.com (`public domain` claimed on the site) but the bulk scrape was never run, so no scraped content is in the DB.

---

## 5. Data Assets & Their Status

| Asset | Location | Size | In git? | Status |
|-------|----------|------|---------|--------|
| `saraga1.5_carnatic/` | `/Users/shyamravidath/carnatify/saraga1.5_carnatic/` | ~13.5 GB | No (gitignored) | 249 tracks, 54 with vocal pitch + raga labels. Access via mirdata `saraga_carnatic`. |
| `RagaDataset/Carnatic/features/` | repo root | ~few hundred MB | **Yes (should be gitignored)** | CompMusic pre-extracted features only. 477 tracks, 40 ragas. Audio is RESTRICTED. |
| `data/scraped_compositions.json` | repo root | ~1 MB | Yes | 3,698 concert records from shankarkrish.blog. `raga_canonical` null for 689 OOV. 101 unique canonical ragas. |
| `data/raga_aliases.json` | repo root | ~80 KB | Yes | 958 raw raga spellings → canonical. 274 null (OOV). Hand-curated. |
| `data/lyrics.db` | repo root | 260 KB | Yes | 3,252 titles, 8 meanings pre-generated. Schema: title (PK), composer, raga, language, lyrics_original, meaning_en, meaning_generated_at. |
| `data/concert_audio/` | repo root | ~3-5 GB estimated | No (gitignored) | 224 MP3s from archive.org across 21 raga directories. |
| `data/raga_v2_cache/` | repo root | variable | No (gitignored) | Demucs+pyin feature cache from retrain experiments. |
| `backend/data/tracks_pitch.npz` | `backend/data/` | 19 MB | Yes (git-lfs in HF Space) | 197-track precomputed pitch bundle. Key `t0`…`t196`, mapping in `tracks_meta.json`. |
| `backend/data/tracks_meta.json` | `backend/data/` | 40 KB | Yes | 197 entries: `{track_id, key, title, tonic, raga}`. |
| `backend/data/lyrics.db` | `backend/data/` | 260 KB | Yes | Copy of `data/lyrics.db`. Committed so Docker image has meanings at startup. Ephemeral at runtime. |
| `models/raga_classifier.pkl` | `models/` + `backend/models/` | 28 MB | Yes | RandomForest, 480-dim features, 40 ragas. 77.8% CV on CompMusic features. Underperforms on live audio due to domain mismatch. |
| `models/raga_label_encoder.pkl` | `models/` + `backend/models/` | 3 KB | Yes | `sklearn.preprocessing.LabelEncoder`, 40 classes. |
| `models/composition_catalog.npz` | `models/` + `backend/models/` | ~400 KB | Yes | 197 × 500 float32 reference contours. |
| `models/composition_catalog_meta.json` | `models/` + `backend/models/` | 8 KB | Yes | Titles + track_ids for catalog. |
| `models/candidates/raga_classifier_compmusic_v2_reference.pkl` | `models/candidates/` | 48 MB | Yes | Retrain candidate A (77.2%). Does not ship. |
| `models/candidates/raga_classifier_saraga_v2_realaudio.pkl` | `models/candidates/` | 37 MB | Yes | Retrain candidate B (5.0%). Does not ship. |

**CompMusic audio access:** The `RagaDataset/Carnatic/features/` directory contains `.pitch`, `.pitchSilIntrpPP`, `.tonic`, `.taniSegKNN` files for 477 tracks across 40 ragas. Audio files (.wav/.mp3) are **not included** and require a manual access request to: `mtg-info@upf.edu` (Music Technology Group, Universitat Pompeu Fabra). This is the highest-priority data acquisition action — getting this audio would unblock the correct retrain.

---

## 6. Infrastructure & Deployment

### Architecture

```
User Browser
    │
    ├── GET carnatify.vercel.app/          → Vercel (Next.js SSR)
    └── GET carnatify.vercel.app/demo      → Vercel (Next.js client)
            │
            ├── GET/POST shyamravidath-carnatify.hf.space/*
            └── (Gemini API is called server-side from HF Space, never from browser)
```

### Frontend (Vercel)
- **URL:** `https://carnatify.vercel.app`
- **Project ID:** `prj_nsJUj8BBDJURSLy7zKP4baziYEtt`
- **Org ID:** `team_gWZCFaSG1F9xc0I06W4FNms8`
- **Framework:** Next.js 14 (auto-detected)
- **Root directory:** `frontend/`
- **Deploy trigger:** `npx vercel --prod` from `frontend/` directory. **GitHub push does NOT auto-deploy** (GitHub integration watches main but the project was initially misconfigured as Python SDK — even after fixing, the integration has been unreliable). Always deploy manually via CLI.
- **Environment variable:** `NEXT_PUBLIC_API_BASE = https://shyamravidath-carnatify.hf.space`
- **`.vercel/project.json`:** Lives at `frontend/.vercel/project.json` (and a duplicate at the repo root `/.vercel/project.json` from an earlier misconfiguration — ignore the root one).

### Backend (HuggingFace Spaces)
- **URL:** `https://shyamravidath-carnatify.hf.space`
- **Space:** `shyamravidath/carnatify` on HuggingFace
- **SDK:** Docker
- **Hardware:** CPU basic — 2 vCPU, 16 GB RAM (free tier)
- **Git remote:** `https://huggingface.co/spaces/shyamravidath/carnatify` (stored in `/tmp/hf-space/.git/config` on the dev machine; credentials in `.git/config`, not in URL)
- **HF Space secrets set:**
  - `GEMINI_API_KEY`: Gemini API key for `/meaning/` endpoint
  - `FRONTEND_ORIGIN`: `https://carnatify.vercel.app` (CORS)
- **Push pattern:** Edit `backend/main.py` → mirror change to `/tmp/hf-space/main.py` → `cd /tmp/hf-space && git add . && git commit -m "..." && git push`. Code-only changes rebuild in ~2 minutes. Dockerfile/requirements changes rebuild in ~10 minutes.
- **First-request latency:** htdemucs model (~80 MB) downloads from torchaudio hub on first `/predict-audio` call after cold start. Allow 2-4 minutes.
- **Binary files in HF Space git:** `models/raga_classifier.pkl` (28 MB), `backend/data/tracks_pitch.npz` (19 MB), `models/composition_catalog.npz` are tracked with Git LFS in the HF Space repo. Do not attempt to push these without LFS set up.

### HF Space deploy: full workflow from scratch (if `/tmp/hf-space/` is lost)
```bash
# 1. Clone the HF Space (credentials in HF write token)
git clone https://huggingface.co/spaces/shyamravidath/carnatify /tmp/hf-space

# 2. Assemble backend into /tmp/hf-space (copies src/, models/, data/)
cd /Users/shyamravidath/carnatify && bash backend/build_space.sh

# 3. Copy assembled files to Space
cp -r backend/* backend/.dockerignore /tmp/hf-space/

# 4. Commit and push
cd /tmp/hf-space && git add -A && git commit -m "redeploy" && git push
```

### Local development
```bash
# Backend (terminal 1)
cd /Users/shyamravidath/carnatify
source venv/bin/activate  # or venv_train for training dependencies
cd backend && uvicorn main:app --port 8077 --reload

# Frontend (terminal 2)
cd /Users/shyamravidath/carnatify/frontend
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8077 npm run dev
```

---

## 7. What the Next Agent Must Do (Prioritized)

### Requires human (Deepti) action first — do not start without confirmation

**H1. Email CompMusic for audio access** ← **HIGHEST PRIORITY UNBLOCKED ACTION FOR HUMAN**  
Email `mtg-info@upf.edu` requesting audio files for the Carnatic subset of the CompMusic Raga Recognition Dataset. Subject: "Audio access request — CompMusic Carnatic Raga dataset for ML research". Note the features-only version (`RagaDataset/Carnatic/`) is already downloaded. This is the only path to a properly matched training set without relying on Saraga/archive.org data.

**H2. Confirm Gemini API quota before running generate_meanings.py**  
The batch script needs ~54 hours of continuous generation at 10 RPM free tier to cover 3,244 remaining titles (at 7s pacing = ~8.6 requests/minute). Check quota at https://aistudio.google.com — the key is in `.env.local`. If quota is available: `GEMINI_API_KEY=<key> python generate_meanings.py 3244` from the repo root.

**H3. Decide on HF Space hardware tier**  
Production UX requires ≤10s inference. GPU (A10G at ~$0.60/hr) would bring Demucs from 65s to ~5s. The free CPU tier is sufficient for a demo but not a public launch. This is a cost/priority decision only the owner can make.

---

### Can start immediately (parallelizable agent workstreams)

**Agent A — Fix pyproject.toml and developer setup (30 min, trivial)**  
Fix: `build-backend = "setuptools.build_meta"` in `pyproject.toml`. Verify `pip install -e .` works in a clean venv. Add missing packages to `[project.dependencies]` if needed (demucs, google-generativeai, fastapi are missing — they're in `backend/requirements.txt` but not `pyproject.toml`). Update `requires-python` to `>=3.11`.

**Agent B — Fix tala detector (2-4 hours)**  
Step 1: Read the Saraga annotation format for beats. The beat annotations are in `saraga1.5_carnatic/<track>/annotations/` — open a few `.beats` files to understand the format (are they beat times? beat numbers? aksharas?). Step 2: Correct `tala_validator.py` to compare at the correct granularity. Step 3: Run validation against the subset of Saraga tracks that have tala annotations. Report actual accuracy before deploying. Step 4: If accuracy is ≥70%, add the tala field to the `/predict-audio` response and `/predict` response in `backend/main.py`, and display it in the frontend results panel.

**Agent C — Rate limiting on `/predict-audio` (2 hours)**  
Add `slowapi` to `backend/requirements.txt`. Wrap the `predict_audio` FastAPI endpoint with a rate limiter (2 requests/IP/minute). Also add `asyncio.Semaphore(1)` to prevent concurrent Demucs runs (a single simultaneous request can OOM on 2 vCPU). Mirror changes to `/tmp/hf-space/` and push.

**Agent D — Frontend hardening (4-6 hours)**  
Issues to fix:  
(1) Add `AbortController` with 5-minute timeout to `predictAudio()` in `frontend/lib/api.ts`  
(2) Add a "Model is warming up (this takes ~2 minutes on first request)…" message if the request hasn't returned in 30s  
(3) Test cross-browser: Chrome (WebM), Safari (M4A), Firefox (OGG) — at minimum verify the content-type strings that each browser sends and confirm they match the suffix mapping in `backend/main.py`  
(4) Add a minimum duration check in the frontend (warn if recording < 30s before submitting)  
(5) Test on iOS Safari — the `getUserMedia` permission flow is different, and `MediaRecorder` may not be available in older Safari  
After fixes, deploy: `cd frontend && npx vercel --prod`

**Agent E — gitignore cleanup (30 min)**  
Add to `.gitignore`: `RagaDataset/`, `"Indian Art Music Raga Recognition Dataset (features).zip"`, `__MACOSX/`, `*.png` (screenshots at root), `models/candidates/`. Run `git rm --cached -r` for each. Commit. This reduces repo size.

**Agent F — CORS and security hardening (1 hour)**  
(1) In `backend/main.py`, change CORS fallback from `"*"` to a deliberate choice (raise `RuntimeError` at startup if `FRONTEND_ORIGIN` is unset). (2) Add input validation: max file size already enforced (30 MB); add min duration check at decode time (already present); add content-type allowlist (reject `application/octet-stream` with no suffix mapping). (3) Mirror to `/tmp/hf-space/` and push.

**Agent G — Meanings batch (conditional on human H2)**  
After Deepti confirms Gemini quota is available: `GEMINI_API_KEY=<key> python generate_meanings.py 3244`. The script is already resumable. Monitor for `ResourceExhausted` errors. If quota runs out, the script will stop cleanly and can be restarted. When complete, copy the updated DB to `backend/data/lyrics.db` and push to HF.

---

### Blocked on CompMusic audio (requires human H1 first)

**Agent H — Raga classifier retrain (1-2 days, highest ML impact)**  
Prerequisites: CompMusic audio files received.  
Steps:  
1. Place audio files in the correct location for the CompMusic mirdata loader  
2. Run `raga_v2_pipeline.py` over all 477 CompMusic Carnatic tracks (Demucs+pyin pipeline, same as inference). Use the `venv_train` environment.  
3. Run `train_raga_v2_evaluate.py` — this will train the CompMusic real-audio candidate and compare against the baseline  
4. If accuracy is ≥77.8%, overwrite `models/raga_classifier.pkl` and `models/raga_label_encoder.pkl`. Run `build_space.sh` and push to HF.  
5. Test with `curl /predict-audio` on the Saraga MP3 and at least 3 live recordings across different ragas in the vocabulary.

---

## 8. Accuracy Targets & Current Baselines

| Module | Current Baseline | Production Target | Gap & Path |
|--------|-----------------|-------------------|------------|
| Raga classifier (CV on CompMusic features) | 77.8% (40 ragas, train set only) | ≥85% top-1 on live recordings | Gap is the domain mismatch. Fix: CompMusic audio retrain. |
| Raga classifier (live audio, in-vocabulary) | Unknown — tested informally, Kalyani returned wrong answer | ≥80% top-1 | Unknown until systematic eval on live recordings |
| Raga classifier (live audio, OOV ragas like Saveri) | 0% (always wrong, returns a wrong in-vocabulary raga) | N/A for OOV | Vocabulary expansion requires more data |
| Raga top-3 accuracy | Unknown | ≥95% | Likely higher than top-1 but not measured |
| Composition matching (top-1) | 16% on 19 compositions with ≥2 renditions | ≥70% | Data ceiling. Need catalog expansion + multi-rendition averaging |
| Composition matching (top-5) | 24% | ≥85% | Same |
| Tala detection | ~2% (broken) | ≥70% on Saraga ground truth | Fix the ground-truth annotation mismatch |
| Inference latency `/predict-audio` | ~65s (30s clip, CPU) | ≤10s | GPU tier or vocal-separation bypass |
| Meanings coverage | 8 / 3,252 = 0.25% | 100% | Run generate_meanings.py when quota available |

---

## 9. Security & Privacy Checklist

| Issue | Status | Action Required |
|-------|--------|-----------------|
| HF write tokens exposed in conversation history | Unknown (check with Deepti) | If tokens were pasted in earlier chat sessions, rotate them at huggingface.co/settings/tokens immediately |
| `GEMINI_API_KEY` in `.env.local` | Gitignored — safe | Verify it never appears in git history: `git log -S GEMINI_API_KEY --all` |
| `GEMINI_API_KEY` in frontend code | Not present (server-side only) | Confirm with grep: `grep -r GEMINI frontend/` |
| `NEXT_PUBLIC_API_BASE` in Vercel env | Correct (points to HF, no auth token) | Fine — this is a public URL |
| No rate limiting on `/predict-audio` | **Missing** | Add slowapi (see Agent C above) |
| CORS allows `"*"` if `FRONTEND_ORIGIN` not set | Risk in fallback | Fix fallback (see Agent F) |
| `data/lyrics.db` committed to git | Committed | Verify CC-BY-NC-SA allows redistribution of Saraga metadata; add attribution in README |
| `models/raga_classifier.pkl` in git (28 MB) | Committed | Acceptable for a demo/research tool; no training data embedded |
| `RagaDataset/` in git | Committed — should be removed | Add to `.gitignore` and `git rm --cached` |
| `app.py` has hard-coded `data_home` path | Local dev only | Not a security issue; just technical debt |
| `train_raga.py` has hard-coded `data_home` path | Local dev only | Same |

---

## 10. Agent Skills & Agent Workflow

### Design skills
Design skills are vendored at `.agents/skills/` — 26 directories including:
- `impeccable/SKILL.md` — comprehensive reference for production-quality UI (color, typography, motion, interaction design, spatial design, UX writing). Read this before writing any frontend code.
- `high-end-visual-design/SKILL.md` — design system and visual language for elevated UI
- `animate/SKILL.md`, `delight/SKILL.md` — motion and interaction design guidance
- `design-taste-frontend/SKILL.md` — frontend taste and quality bar
- `stitch-design-taste/SKILL.md` + `DESIGN.md` — detailed brand and component guidelines
- Other skills: `adapt`, `audit`, `bolder`, `clarify`, `colorize`, `critique`, `distill`, `layout`, `minimalist-ui`, `optimize`, `overdrive`, `polish`, `quieter`, `redesign-existing-projects`, `shape`, `typeset`

**Any agent writing frontend code must read relevant SKILL.md files first.**

### Agent swarm pattern (proven in this session)
1. Orchestrator identifies independent workstreams
2. Spawns background agents for each workstream
3. Each agent is self-contained in its directory scope
4. Orchestrator wires results after all agents report completion
5. One integration agent merges the pieces and runs E2E tests

### Deployment pattern
```
Backend change:
  Edit backend/main.py
  Mirror to /tmp/hf-space/main.py
  cd /tmp/hf-space && git add . && git commit && git push
  Poll /health for 200, then test /predict-audio

Frontend change:
  Edit frontend/...
  cd frontend && npx vercel --prod
  (git push origin main is NOT sufficient to trigger Vercel auto-deploy)
```

### HF Space detection during rebuild
HF Space does zero-downtime blue-green deploys — `/health` stays 200 throughout. To detect a successful rebuild, test the changed behavior directly rather than watching `/health`.

### Playwright MCP
Installed and connected. Tools available: `browser_navigate`, `browser_click`, `browser_fill_form`, `browser_snapshot`, `browser_take_screenshot`, `browser_network_request`, etc. Use for all live frontend testing. Screenshots go to the repo root (01-13 exist; the next one would be 14).

---

## 11. Questions the New LLM Must Answer Before Proceeding

Do not assume answers. Read the code, run evaluations, and interrogate the data before acting.

**Q1. Is the raga classifier fundamentally broken for live audio, or just needs pipeline alignment?**  
The 5% result on the Saraga real-audio candidate suggests the data problem (too few tracks/raga) is as important as the pipeline mismatch. Even with perfectly aligned training, a model trained on 3 tracks/raga cannot generalize. The answer depends on how many tracks CompMusic audio gives us per raga. Run a count: `python3 -c "from pathlib import Path; p=list(Path('RagaDataset/Carnatic/features').rglob('*.tonic')); print(len(p)); import json; mapping=json.load(open('RagaDataset/Carnatic/_info_/ragaId_to_ragaName_mapping.json')); ..."` Estimate: 477 tracks / 40 ragas ≈ 12 tracks/raga average. With StratifiedGroupKFold this is marginal but potentially workable.

**Q2. Is the composition matcher worth improving given the 197-track data ceiling?**  
The matcher is architecturally sound. The bottleneck is catalog size, not the algorithm. The pragmatic answer: the matching is better than random and useful for users who sing compositions in the catalog. Expanding the catalog (downloading more Saraga audio, using Saraga Audiovisual) is worth doing. The composition matcher should NOT be replaced — the DTW approach is correct for this problem.

**Q3. Should Demucs be replaced with a lighter vocal separator for production latency?**  
If GPU is available: No — keep Demucs (quality is important, and GPU makes it fast enough). If stuck on CPU: Yes — explore `spleeter:2stems` (faster, lower quality but possibly acceptable) or skipping separation entirely. Measure the raga classification accuracy drop before and after, using the Saraga test tracks where ground truth is known.

**Q4. Is HuggingFace free tier viable for production?**  
For a demo: Yes. For public launch: No. 65s per request, no concurrency, ephemeral filesystem (cache resets), no rate limiting built-in. The minimum viable paid plan is the A10G GPU ($0.60/hr). Alternatively: deploy the API to a VPS (Hetzner CX41, ~$16/month) with a GPU-enabled docker image and keep HF for the demo.

**Q5. Are there copyright/licensing issues with shipping shankarkrish.blog metadata in the lyrics DB?**  
The 3,252 titles in `lyrics.db` were seeded from Saraga Carnatic metadata (CC-BY-NC-SA). The composition titles, composer names, and raga names are factual information and likely public domain regardless. The generated English meanings are LLM-generated from the title alone — not scraped from any source. The scraped concert records in `scraped_compositions.json` are from shankarkrish.blog — the blog's terms of service should be checked. Recommend: add attribution to Saraga/CompMusic in the README and Terms of Service page before public launch.

**Q6. Is the Next.js frontend complete enough for public launch?**  
Functionally: mostly yes (both tabs work, results are displayed correctly). Quality blockers: (a) no cold-start UX, (b) no timeout handling, (c) not tested on mobile/iOS Safari, (d) progress messages are timer-based guesses, (e) no error analytics. It needs 1-2 days of hardening before a public launch.

**Q7. What is the minimum viable raga accuracy for public launch?**  
The PRD specifies ≥75% on held-out test. Since we don't have a systematic live-audio test set, the current accuracy on live audio is unknown. Before launch, create a small test set: record 5 clips each of 10 ragas (in vocabulary), get ground truth from a Carnatic musician (Deepti), measure top-1 and top-3 accuracy. ≥70% top-1 on in-vocabulary ragas is the minimum viable bar. If the classifier is consistently wrong on common ragas like Kalyani, it is not ready.
