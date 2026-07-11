# HANDOFF: Clip identification (SoundHound-for-Carnatic) + project robustness

Written 2026-07-11, ~3am, after two days of continuous work. Audience: agent
taking over. Supersedes `HANDOFF_RAGA_DATA.md` (that workstream is DONE) and
the composition sections of `HANDOFF.md`.

## 1. The goal

Deepti's product vision, stated explicitly: **SoundHound for Carnatic music,
as a serious product — potentially a company.** Point the phone at a
performance (or sing/hum), get back within seconds:

1. **Composition** (which kriti) — the headline feature. Target: ≥50% from a
   ~60s clip, on *wild* audio (arbitrary artists, phone/YouTube-grade,
   any shruti). Top-5 presentation is acceptable UX.
2. **Raga** — secondary display, with honest confidence.
3. Lyrics + meaning for the matched composition (already built, lyrics.db).

Constraints: free-of-cost infrastructure only. Colab Pro available for GPU.
Deepti is a Carnatic musician (HS student, CS/ML background) — she can
validate musically and record test material.

**The critical lesson of this handoff: benchmarks lie, wild clips don't.**
Every internal benchmark we built was flattered by same-corpus effects. The
only eval that predicted real behavior was 10 clips of professional artists
Deepti recorded off real performances (`/Users/shyamravidath/sung_tests/`,
filenames carry ground truth as `<title>__<raga>.m4a`). Treat that folder
(and expansions of it) as the only scoreboard that matters.

## 2. Scoreboard (2026-07-11, on the 10 wild clips)

| approach | top-1 | top-5 | verdict |
|---|---|---|---|
| Lyrics: whisper large-v3-turbo + fuzzy token-coverage | 2/8 | **6/8** | **winner, ship-grade with top-5 UI** |
| Melody: Qmax cover-song, any gating/blending variant | 0/8-10 | 0/8-10 | dead on wild clips |
| Raga: TDMS clip classifier (60s clips) | 0/10 | 1/10 top-3 | weak on wild clips |

(2 of the 8 lyric-scored clips produce no usable transcript — ASR ceiling,
not matcher ceiling. Alapana clips have no lyrics by definition; raga path
is their only hope.)

Numbers that still stand (full-recording domain, grouped CV, leak-free):
- **Raga from full track: 72.8% top-1 / 84.7% top-3** (18 ragas, ≥25
  tracks/raga tier) — models exported `models/raga_v3_*`, TDMS features.
- **Composition, full-recording cross-artist: 60-67% top-1** (Qmax).
- Corpus: ~1,290 feature-complete tracks / 87 ragas (was 597 two days ago).

## 3. Current state of the code (all committed + pushed, main)

**Working pipeline pieces:**
- `identify_clip_lyrics_prototype.py` — the lyrics path prototype (whisper +
  token matching). The *best matcher variant* (token coverage + repetition +
  order bonus: top-5 6/8) lives only in the scratchpad history; the committed
  file has the simpler matcher. Reconstruct from §5 notes or the transcript
  cache logic — 30 min job. Transcripts cache to a JSON next to the script.
- `test_sung_clip.py` — melody-path runner (kept for full-recording mode;
  do NOT trust it for short wild clips).
- `models/qmax_catalog.npz` + `_meta.json` — 1,421 tracks, 3,465 chroma
  windows (committed, 3 MB). `models/raga_clip_rf.pkl` (1.1 GB, gitignored)
  — rebuild: `venv/bin/python train_raga_clip_model.py`.
- `models/raga_v3_*` — full-track raga candidates (rf pkls gitignored;
  rebuild: `venv/bin/python train_raga_v3_tdms.py --min-tracks 20`).
- `train_raga_v3_tdms.py`, `train_raga_clip_model.py`, `build_qmax_catalog.py`,
  `extract_melodia_full.py` (parallel full-track melody), `raga_v2_pipeline.py`
  (Demucs+pyin 65s features), `evaluate_raga_thresholds.py`,
  `evaluate_composition_qmax.py`, `evaluate_composition_external.py`,
  `evaluate_composition_shortclip.py`.
- Data collection stack: `fetch_all_archive_metadata.py`,
  `fetch_archive_search_metadata.py` (archive.org-wide search),
  `download_targeted_deficits.py`, `download_title_join.py` (labels files via
  blog-tracklist title joins), manifest at
  `data/concert_audio/download_manifest.json`.
- Feature caches (local, gitignored): `data/raga_v2_cache/archive_v3/` +
  `saraga_v3/` (65s Demucs+pyin npz, ~1290 tracks),
  `data/raga_v2_cache/melodia_full/` (full-track melodia f0, ~1230 npy).
- Deployed app (untouched by this work): Vercel frontend + HF-space backend,
  old 40.5% raga model + 16% L2 composition matcher still live.

**Environments:** `venv` (py3.14: sklearn, librosa, mirdata) and `venv_train`
(py3.11: demucs, essentia, whisper, rapidfuzz). essentia things must run in
venv_train. No ffmpeg on the machine — load audio via librosa/essentia, never
subprocess ffmpeg; whisper must be fed numpy arrays, not file paths.

## 4. Files actively being edited

Nothing mid-edit. Branch clean, pushed (last commit: lyrics prototype).
Scratchpad experiments (session-temporary, will vanish):
`comp_*.py`, `whisper_*.py`, `fusion_test.py`, `raga_*.py` in the session
scratchpad + `whisper_transcripts_turbo.json` (cached transcripts of the 10
test clips — cheap to regenerate, ~20 min CPU).

## 5. Everything tried that FAILED (do not retry blindly)

**Melody path on wild short clips (the big graveyard):**
1. Global-contour matching (shipped L2-500pt, DTW full-contour, z-scored or
   raw): 16-20% even on friendly internal eval. Structural variation between
   renditions kills it.
2. Exact melodic n-grams, Smith-Waterman on note strings, subsequence DTW on
   snippets: all ≤10% internal. Too brittle for gamaka.
3. Qmax cover-song (essentia ChromaCrossSimilarity+CoverSongSimilarity): the
   only thing that worked internally (63-67% full-recording — still valid for
   that mode) but **0% on wild 60s clips** (true work ranks 148-1025/1110).
   Same-corpus benchmarks (55% "e2e short clip") were artist/recording-family
   flattered. Windowing, gate widths (top-3/5/8, union-of-tonic-hypotheses),
   proba blending (0.5 → swamps distances; 0.3 → still net harm), rank/min/mean
   fusion with L2 — all tried, none survive wild clips.
4. Raga gating on clips: clip-trained TDMS RF is domain-matched (77% top-8 on
   internal clips) but wild-clip posteriors collapse (true raga p≈0.05, rank
   3-8 at ORACLE tonic; garbage at estimated tonic). RF-confidence tonic
   selection is ANTI-informative (wrong tonics score higher — class priors).
   12-rotation voting failed for the same reason.
5. Tonic estimation on wild clips: essentia TonicIndianArtMusic returns
   scattered values (158-371 Hz for same-shruti material); melodia octave
   errors compound it. Voice-band constraint (minFrequency=90,
   maxFrequency=900, voicingTolerance=0.6) fixed melody extraction — keep it —
   but tonic remains unsolved without user input.
6. Lyrics-matcher variants that did NOT beat simple token coverage: character
   n-gram Jaccard, vowel-squashed phonetic partial_ratio, IDF weighting
   (Carnatic titles are all common words — IDF sinks true titles), melody-Qmax
   fusion as tiebreak (melody signal too weak to break ties, `dinf` for
   lyrics-db-only titles with no catalog track).

**Raga modeling (older, still true):** CNN on CQT memorizes (val at chance);
tala detection 16.5% vs 72% majority baseline (closed); pitch-transition
bigrams on 65s segments add ~0 over histograms; RF hyperparam tuning ±1%.
TDMS on FULL-track melody was the breakthrough (+13pt) — 65s segments are
too short for it to shine.

**Ops traps:** macOS multiprocessing needs fork not spawn (essentia+Pool);
demucs times out under CPU contention (don't run heavy evals concurrently
with extraction); dtaidistance C extension won't build (use numba);
`pip install dtaidistance` upgraded numpy and broke numba once — pin numpy<2.5.

## 6. Next steps, in the order I'd take them

1. **Rebuild + commit the best lyrics matcher** (token coverage + repetition
   + order bonus + variant dedup — the exact scoring that got 6/8 top-5) as
   `identify_clip.py`, single entry point: audio in → {composition top-5,
   raga top-5, confidence flags}. Add lyrics-absent fallback (alapana →
   raga-only answer).
2. **ASR quality — the single biggest lever.** 2/8 clips have no transcript.
   Try, on the same 10 clips: (a) ai4bharat / IndicWhisper checkpoints (free,
   HF), (b) whisper large-v3 (non-turbo) on Colab GPU, (c) demucs vocal-stem
   isolation BEFORE whisper (kills violin/mridangam interference — untested!),
   (d) chunking with VAD instead of whole-clip transcribe.
3. **Grow the test set — 10 clips is statistically thin.** Deepti records
   30-50 more labeled wild clips across eras/genders/recording quality. This
   is the scoreboard for every decision; it should also become a regression
   suite (`test_sung_clips/` + expected-answer manifest).
4. **Catalog title hygiene**: dedupe spelling variants (soft-phonetic key),
   strip timestamp/junk titles ("1:32:39 dEvAdidEva", "B"), merge lyrics.db
   titles with catalog titles into one canonical composition table with
   aliases. The matcher's rank-1 errors are half title-collision noise.
5. **Integrate + deploy** lyrics-first clip ID into the backend (HF space:
   whisper-turbo CPU is ~2-4x realtime — a 60s clip = ~30-60s processing;
   acceptable for v1, show progress in UI). Raga v3 model swap needs Deepti's
   explicit sign-off (production pkl untouched so far).
6. **Melody path**: keep for full-recording mode only. If someone wants to
   resurrect it for clips, the only ideas with a pulse are: contrastive
   embedding trained on our ~300-track multi-rendition set (GPU, weeks,
   risky) or massive rendition growth per work.

## 7. Robustness / "make it a company" brainstorm — for the next agent

Deepti asked for this explicitly: go all-in on effectiveness; treat it like it
could become a company. Seed ideas to develop (brainstorm beyond these):

- **Data moat**: the composition catalog + rendition graph IS the product.
  Systematize ingestion (archive.org, sangeethapriya, YouTube-with-permission,
  user contributions), canonical composition IDs with alias tables, composer/
  raga/tala metadata, and a human-verification queue Deepti can drive.
- **User-in-the-loop labeling**: every query where the user confirms "yes,
  that was X" is a labeled wild clip — the exact data we're starved for.
  Design the feedback loop from day one.
- **Confidence-aware UX**: never bluff. Top-5 with confidence tiers, "sing a
  cleaner pallavi" prompts, raga-only answers for alapana, explicit "not in
  catalog yet — want to add it?".
- **Segmented pipeline**: detect clip type first (kriti vs alapana vs thani
  avartanam vs viruttam) and route: lyrics path, raga path, tala path, or
  "instrumental — melody only". Cheap classifier, big robustness win.
- **Hybrid retrieval**: lyrics tokens + raga posterior + melody embedding as
  three noisy voters over ONE canonical composition index, with per-source
  calibration learned from user confirmations.
- **Latency/cost**: whisper-turbo on HF CPU is the only real cost center;
  quantized (faster-whisper/ctranslate2) runs 4-8x faster — test it.
- **Community angle**: rasika + student market; concert-companion mode
  (continuous listening, setlist generation); lyrics+meaning display is
  already differentiated. A "verified by musicians" badge on catalog entries
  builds trust the big players can't fake in this niche.
- **Eval culture**: every model change must run the wild-clip regression
  suite. No same-corpus benchmark is ever again allowed to green-light a ship.

## 8. Gotchas for the next agent

- Caveman response mode is a standing Deepti preference (see memory).
- Sing-clip ground truth: filename `<title>__<raga>.m4a`, fuzzy-match truth
  with soft-phonetic fold ≥90, never exact string.
- Saraga annotated tonics contain fifth errors (4 of 18 rendition pairs) —
  OTI-based methods immune, tonic-normalized features are not.
- `Rāgamālika` is a form, not a raga — always excluded.
- Grouped CV by track_id or the number is fantasy. Wild-clip eval > all CV.
- Don't overwrite `models/raga_classifier.pkl` (production) without sign-off.
