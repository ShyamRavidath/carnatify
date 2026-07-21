# Carnatify — State & Progress Ledger

Written 2026-07-18, immediately after the three-fix session (commit 80e4a1b).
Audience: incoming agent. Companion: `handoff_vision_and_architecture.md`
(strategy/research). Detailed historical record remains in the committed
HANDOFF_*.md files; where this file compresses, those expand:
HANDOFF_SESSION_0718.md (latest session spec), HANDOFF_CLIP_ID.md (§5
graveyard, §8 gotchas), HANDOFF_SESSION_0712.md, HANDOFF_RAGA_DATA.md,
HANDOFF.md (full repo map + web-stack bugs), BRAINSTORM_COMPANY.md (strategy),
DEPLOY.md, carnatify_prd.md.

Standing operator preferences (Deepti): caveman response mode in chat (see
memory/skill); free-of-cost infra so far (Colab Pro available); she validates
musically and records test material; production deploys are Deepti-run (agent
deploys blocked by permission classifier); **wild-clip eval is the ONLY
scoreboard — no same-corpus benchmark green-lights anything.**

---

## 1. The ultimate goal

Clip (~60 s wild audio: arbitrary artist, phone/YouTube-grade, any shruti) →
composition (headline; top-5 UX acceptable) + raga (secondary, honest
confidence) + lyrics/meaning. Interim target ≥50% top-1 on wild clips;
long-run production bar 80–90% (see vision doc §0 for the honest gap
analysis — currently 8/36). Registry + user-confirm feedback flywheel is the
moat; models replaceable.

## 2. Current state of the code (main @ 80e4a1b, clean, pushed)

### 2.1 Core pipeline — `identify_clip.py` (single source of matcher truth)

Audio → dual ASR → per-variant lyric matching → policy selection → top-5 +
confidence (+ raga). Precisely:

1. **ASR variants** (`_whisper_multi`, `transcribe`, `transcribe_stem`):
   whisper large-v3-turbo on original audio (langs None/ta/te/hi, best =
   longest folded text) AND on the demucs htdemucs vocal stem (None/ta/te).
   Cached by filename in `data/whisper_transcripts_turbo.json` /
   `..._turbo_stems.json` (committed; keys are NFD macOS filenames — naive
   NFC lookups silently miss).
2. **Matcher** (`match_lyrics` / `_score_ktoks`): IDF-weighted token coverage
   + pallavi-repetition bonus + order bonus + epsilon quality tie-break, over
   registry title variants AND karnatik lyric-line pseudo-variants (each line
   scores like a title → mid-kriti clips matchable). Transcript tokens include
   joined adjacent-word bigrams (whisper splits sung sahitya). Vectorized
   rapidfuzz cdist over the catalog vocabulary; IDF computed over
   title+line tokens (required at 8.7k scale — unweighted hits cost 3/21
   top-1 when the registry 4x'd).
3. **Usability gates** (in `identify`): HALLUC stoplist regex; min transcript
   chars 8; max token repetition ≥ 2 (sung kritis repeat pallavi, garbage
   doesn't); **NEW (80e4a1b): `_max_token_run` ≥ 4 consecutive identical
   tokens = whisper decode loop → variant unusable** (LOOP_RUN=4).
4. **Policy v2 selection:** best usable variant by top score; prefer stem
   within 0.15; abstain < 0.35; confidence high (≥0.65 & margin ≥0.15) /
   medium (≥0.5) / low.
5. **Raga:** melodia (voice-band 90–900 Hz, voicingTolerance 0.6) → tonic
   (TonicIndianArtMusic + 12-rotation max-proba vote) → TDMS (3 taus, 40
   bins) → clip RF (`models/raga_clip_rf.pkl`, 1.1 GB, gitignored; rebuild
   `venv_train/bin/python train_raga_clip_model.py`). Always reported
   low-confidence. A high/medium composition match backfills raga from the
   registry instead (measurably better).
6. **Eval harness in `main()`:** folder run = regression suite. Filename
   truth `<title>__<raga>.<ext>`, one `__`; trailing `__OOC` = must-abstain
   (answer = bluff); raga `NA` = excluded from raga denominators; prints
   per-clip TRUTH lines + final SCORE block — **always quote that block,
   never recompute**. Truth matching is soft-phonetic partial_ratio ≥ 90.

Run: `venv_train/bin/python identify_clip.py <file-or-folder> [--json]
[--no-raga] [--fast]` (fast skips demucs; --no-raga skips the 1.1 GB RF).

### 2.2 Scoreboard (2026-07-18 full eval, read from printout)

```
===== SCORE over 36 in-catalog + 27 OOC clips =====
composition top-1 8/36  top-5 13/36
OOC reject  23/27  (bluffs: 4)
raga        top-1 9/43  top-3 12/43  (clips with known raga truth)
raga via catalog backfill 6/21 (on clips with confident composition)
```

Eval set: `~/sung_tests/` = 63 clips FROZEN as baseline (36 in-catalog + 27
OOC). Remaining bluffs: Munbe Vaa + Samayaniki (interleaved hallucination
loops, max same-token run 2 — escape the unigram detector; naive phrase-period
detection would kill Sarvam Brahmamayam's genuine pallavi repetition), Brahmam
Okate (garbage stem transcript onto real entry "pAdi madi nadi" @1.151), Om
Jai Jagdish (CORRECT transcript, matcher false-matched pAhirAmadhoothA @1.201
— hardest class, needs score calibration, recorded not queued). v3-only dasa
slice: 0/8 top-1, 3/8 top-5 — those clips are ASR-dead (see failure log).

### 2.3 Registry & data assets

- `build_composition_registry.py` → `data/composition_registry.json`: 8,688
  entries ("v3") — canonical + aliases + ragas + karnatik_pages. v1 (2.2k):
  `git show feac4b6:data/composition_registry.json`.
- `data/karnatik_lyrics.json` — scraped lyric pages feeding line-level match.
- `data/lyrics.db` — 3,252 titles; lyrics_original mostly empty; 8 meanings.
- `data/catalog_titles.txt` (8,688 grep-able lines — grep BEFORE declaring
  anything OOC), `data/v3_only_titles.txt` (6,239 v3-only compositions).
- `data/scraped_compositions.json` — shankarkrish blog tracklists (source of
  registry expansion; contains some junk rows — raga-vocab check on ingest).
- Transcript caches (§2.1) — committed, all 63 clips present.
- Feature caches (gitignored): `data/raga_v2_cache/{saraga_v3,archive_v3}/`
  (65 s demucs+pyin npz, ~1,290 tracks), `melodia_full/` (~1,230 full-track
  f0). Unsuffixed saraga/archive dirs are stale v1 — ignore.
- `models/`: qmax_catalog.npz + meta (1,421 tracks — melody path, full
  recordings only), raga_v3_* (full-track raga), raga_classifier.pkl
  (PRODUCTION, 40.5% — do not overwrite without sign-off), raga_clip_rf.pkl
  (gitignored 1.1 GB).
- `fetch_sung_tests.sh` — OOC clip fetcher, works as of 0717 (three bugs
  fixed, see failure log); manifest at `~/sung_tests/fetch_manifest.tsv`.

### 2.4 Web stack (deployed old / staged new)

- **Live:** Vercel frontend (carnatify.vercel.app) + HF Space FastAPI with
  OLD models (40.5% raga RF + 16% L2 composition matcher). Untouched.
- **Staged, NOT deployed** (Deepti sign-off gates): `backend/main.py`
  POST /identify (dual-ASR matcher, top-5 + confidence + abstain, 2/min rate
  limit, ?fast=true) + POST /feedback (confirmed/rejected/not_in_catalog,
  JSONL + push to private HF dataset — create the dataset repo BEFORE
  go-live; Space disk is ephemeral). `backend/build_space.sh` assembles
  (allowlist-copies models — a blind cp -r drags the 1.1 GB RF into Docker).
  Smoke-tested at module level only — run one uvicorn+curl pass pre-deploy.
  Deploy runbook: DEPLOY.md §1d. Known web bugs (timeouts, cold-start UX,
  CORS "*", no request queue): HANDOFF.md §4.
- **Meanings:** Gemini 2.5 Flash on-demand via /meaning/{title}; free quota
  exhausted after 8; `generate_meanings.py` is resumable and correct — it
  needs a paid tier or different API (vision doc §3).

### 2.5 Environments

`venv` (py3.14: sklearn, librosa, mirdata) and `venv_train` (py3.11: demucs,
whisper, essentia, rapidfuzz) — matcher/ASR/eval all in venv_train. No ffmpeg
on the machine: load audio via librosa/essentia; feed whisper numpy arrays,
never file paths. macOS multiprocessing: fork, not spawn. numpy<2.5 pin
(dtaidistance once broke numba).

## 3. Active files

None mid-edit. Working tree clean at 80e4a1b except pre-existing untracked
leftovers (carnatic_varnam_1.1.zip/dir, data/cnn_extra_audio/,
data/whisper_transcripts_fw_int8.json, .claude/settings.local.json mod) —
leave them. The two handoff files this document belongs to are new in repo
root.

## 4. The failure log (post-mortem of everything tried that failed)

**Melody path on wild short clips (the big graveyard):**
1. Global contour matching (L2-500pt shipped, DTW full-contour, z-scored/raw):
   16–20% even on friendly internal eval. Structural variation kills it.
2. Melodic n-grams, Smith-Waterman on note strings, subsequence DTW: ≤10%.
   Too brittle for gamaka.
3. Qmax cover-song similarity: 63–67% full-recording (still valid for that
   mode) but **0% on wild 60 s clips** (true work ranks 148–1025/1110). The
   "55% e2e short clip" internal number was artist/recording-family
   flattered — the origin of the no-same-corpus-benchmark rule. All gating/
   blending/fusion variants tried; none survive wild clips.
4. Raga-gating of composition candidates: wild-clip raga posteriors collapse;
   RF-confidence tonic selection is ANTI-informative (class priors);
   12-rotation voting failed the same way. Proba blending: 0.5 swamps, 0.3
   still net harm.
5. Tonic estimation on wild clips: unsolved. TonicIndianArtMusic scatters
   158–371 Hz on same-shruti material; melodia octave errors compound.
   Voice-band constraints fixed melody extraction (keep) but not tonic.
   Exception with a pulse: real tanbura in-clip → tonic locks (n=1, sister
   clip) → drone detection is queued work.

**ASR:**
6. Prompted whisper on CPU turbo (initial_prompt with Carnatic vocab):
   hallucinates fluent repetitive junk that DEFEATS the repetition gate.
   GPU large-v3 + prompt on stems is good — large-v3 property, not turbo.
7. faster-whisper int8 on macOS ARM: ~1x realtime, garbage at beam=1 —
   speedup claims are x86-specific. Left opt-in for on-Space benchmark.
8. vasista22 Indic finetunes via transformers pipeline: three stacked
   failures (forced_decoder_ids hang; stale generation_config vs language=;
   Colab silently on CPU). Never actually evaluated — retry ONLY via
   ctranslate2/faster-whisper conversions.
9. **'kn' in whisper language lists (2026-07-18, reverted):** v3-only dasa
   slice stayed 0/8 top-1 and top-5 slice DROPPED 3/8→2/8. Transcripts on
   those clips are near-empty junk in every language — the audio is ASR-dead
   for whisper-turbo-CPU, the language list was never the blocker. Don't
   retry language-list tweaks; the lever is better ASR (GPU large-v3,
   IndicConformer).
10. Max-fusion pooling across ASR variants (union top-10s): 5/10 top-5 —
    weak variants inject junk. Selection beats pooling absent per-source
    calibration.

**Matcher/gates:**
11. Matcher variants that did NOT beat token coverage: char n-gram Jaccard,
    vowel-squashed phonetic partial_ratio, plain IDF over titles (sinks true
    titles — common devotional words), melody-Qmax tiebreak.
12. Loop detector nuance (2026-07-18, kept fix): unigram run ≥4 kills
    verbatim decode loops with zero collateral, but interleaved loops
    ("again and again again", "love you love you") have max run 2 and
    escape; phrase-period detection would also kill genuine pallavi
    repetition (Sarvam Brahmamayam is a top-1 hit BECAUSE of phrase-level
    repetition). Next principled step is score calibration, not more gates.
13. "pAdi madi nadi" junk-magnet hypothesis (2026-07-18): inspected — it is
    a REAL blog tracklist row (Madurai Somasundaram concert, Ṣanmukhapriya),
    not a parse artifact. Left in registry.

**Raga modeling:**
14. CNN on tonic-rolled log-CQT: val pinned at exact chance for 60 epochs
    while sanity-overfit passed — pure per-recording memorization. ~29 min
    audio/raga cannot train a from-scratch CNN on 53 classes; the wall is
    TRACKS, not minutes. More segments from same tracks won't fix it.
15. Tala detection: 16.5% vs 72% majority baseline. Closed.
16. Pitch-transition bigrams on 65 s segments: ~0 gain. RF hyperparams: ±1%.
    TDMS needs FULL-track melody to shine (+13 pt there).
17. CompMusic/Dunya audio: dead (unanswered emails). Saraga tonic
    annotations contain fifth errors (4/18 rendition pairs).

**Ops traps (cost real time):**
18. fetch_sung_tests.sh had three stacked bugs (mktemp pre-creation, macOS
    mktemp mid-name XXXXXX, ffmpeg/yt-dlp eating heredoc stdin → truncated
    titles). Fixed; if titles truncate again it's the stdin one.
19. NFC/NFD cache-key mismatch (single-file runs silently re-run ASR);
    zsh `=word` expansion aborts compound commands (`echo ===` — quote it);
    demucs times out under CPU contention; Colab reconnect lands on CPU
    silently ("FP16 is not supported on CPU" = you're on CPU); HF Space disk
    wipes on restart; grouped-CV-or-fantasy for any raga number; Rāgamālika
    is a form, not a raga — always excluded.
20. Deepti's first OOC hunt: 7/10 hand-picked "out-of-catalog" clips were
    actually IN the 8.7k registry — grep data/catalog_titles.txt before
    declaring OOC.

## 5. Immediate next steps (chronological)

1. **Deploy the staged stack** on Deepti's sign-off: create private HF
   feedback dataset → `bash backend/build_space.sh` → secrets per DEPLOY.md
   §1d → one uvicorn+curl smoke test → Deepti pushes (agent deploys blocked).
2. **Frontend confirm-button UI** (top-5 + confidence tiers + abstain message
   + confirmed/rejected/not_in_catalog wired to /feedback). Flywheel live is
   the precondition for everything data-hungry in the vision doc.
3. **Meanings sprint:** run Karnatik scraper at scale → paid batch LLM
   generation (vision doc §3, ~$10 one-time) → verification queue → persist
   in committed DB. Kills the "sketchy semantics" deficit.
4. **GPU serving decision** (first infra spend): small GPU box or serverless
   → whisper large-v3 on stems in production + latency fix.
5. **IndicConformer-600M + IndicWhisper via ctranslate2** as additional ASR
   variants; rerun the 63-clip eval; targets the ASR-dead slice (Bhuvini,
   dasa kritis, sister nagumOmu).
6. **Drone-presence detection** (needs Deepti's with/without-tanbura pairs)
   + clip-type router (features already computed in-pipeline).
7. **Score calibration / margin analysis** across the eval set → fixes the
   Om Jai class and replaces ad-hoc gates.
8. **Eval set growth to 200+** stratified clips (Deepti recordings + script
   fetches + flywheel confirms); per-stratum scoreboard; CI regression gate.
9. Then the CSI embedding channel (vision doc §2.2) — the NN bet, after the
   flywheel provides fine-tuning and calibration data.

Pending human checks (do not silently resolve): Kurai Onrum Illai and Paluke
Bangaramayena raga-window ear-checks (Deepti); raga model swap on production
needs explicit sign-off.
