# Fable — Rung 5 (Indic CTC on the Demucs vocal stem). One shot.

You are the implementer/eval-runner/committer. **The complete, frozen spec is
in `AGENT_LOG.md`** — read newest-first: **"Rung 5 one-shot spec"** (Codex,
implement this exactly), then "Rung 5 pre-diagnostic" (Opus, why stem), and
"Rung 4 landed" (the hybrid `arbitrate()` you build on). Then `METRIC_CONTRACT.md`
and the graveyard (`REVIEW_BRIEF.md §4`). Do not re-derive the design — Codex
froze it; implement it.

## The one question
Whisper's vocal stem is the sole source of 6 of its ~9 correct top-1s (3× mix).
IndicConformer has only seen the polluted mix. Does an Indic CTC **stem** lane
recover composition-bearing sahitya that Indic-mix misses, and pass the frozen
`q_cov>=0.250 AND ordered` gate — or just add more filtered false answers?

## Build exactly what Codex froze (no more)
- **New source row only.** Indic CTC on the htdemucs vocal stem, 5 fixed lanes
  (`te,ta,kn,hi,ml`), whole-clip. Whisper and Indic-mix rows unchanged.
- **Effective-Indic selector (conservative, cannot regress Rung 4):** mix
  passes the gate → use mix; elif stem passes → use stem; else → mix
  (ineligible). Then `arbitrate(whisper, effective_indic)` with **zero changes
  to the Rung 4 decision rule**. Mix wins if both pass. Never pool lists.
- **Third cache** `data/asr_cache_indic_stem.json`, own `ASR_CONFIG_INDIC_STEM`
  + `INDIC_STEM_CONFIG_ID`, addressed by `cache2_key(sha, INDIC_STEM_CONFIG_ID)`.
  Extend `load_cache_v2()` with an explicit `indic_stem` mapping — **no silent
  fallthrough to Whisper** for unknown backend names. `source:"stem"`,
  error≠empty at both Demucs and decode stages.
- **New opt-in mode `CARNATIFY_ASR_BACKEND=hybrid_stem`.** Keep `whisper`,
  `indic`, and landed `hybrid` **byte-identical**. Default stays Whisper.
- **Builder:** add `--source mix|stem` to `scripts/build_asr_cache_indic.py`;
  `mix` byte-identical to today. Stem mode pulls audio ONLY through the existing
  `identify_clip._vocal_stem_16k(path)` (confirmed at `identify_clip.py:628`),
  shares encoder logits across the 5 lane masks, **atomic write per clip** so an
  interrupted run resumes without redoing Demucs.
- Diagnostics per Codex: `asr_channel ∈ {none,whisper,indic_mix,indic_stem}`,
  `indic_source_reason`, three-way `channel_evidence`. Final top-5 = exactly one
  source row's list, never a union.

## Verified for you (don't re-check)
- `_vocal_stem_16k()` exists (`identify_clip.py:628`, htdemucs → 16 kHz f32).
- `build_asr_cache_indic.py` exists and currently hardcodes `source:'mix'`.
- Whisper's cache holds stem **transcripts, not reusable stem PCM** — you MUST
  re-separate each clip (no persisted Demucs waveform set exists).

## Procedure
1. **Smoke** the 5 clips Codex names (Devadideva, nannu pAlimpa, Bhuvini
   Dasudane, nagumomu ganaleni, Achyutam Keshavam) — verifies Demucs→ONNX,
   per-lane source/config_id/status, native text survives, failures not
   mislabelled empty, resume works. **No accuracy claim.**
2. Full stem build. **Demucs is CPU-bound and timeout-prone under contention**
   (handoff): `caffeinate -dims venv_train/bin/python -u
   scripts/build_asr_cache_indic.py --source stem ~/sung_tests`, lid open, no
   concurrent heavy eval. `python -u` if you track progress.
3. When the stem cache is 106/106, run **one** eval:
   `CARNATIFY_ASR_BACKEND=hybrid_stem venv_train/bin/python identify_clip.py
   ~/sung_tests --no-raga --cache-v2`, then the same on `~/sung_tests_curated`.

## Acceptance (Codex's — strict)
Quote the verbatim 106 SCORE + precision@coverage + source counts + arbitration
& indic_source reason counts + how many stem rows passed the gate and how many
selected stem rows were correct vs wrong + all THREE cache hit/miss. A valid
SCORE needs whisper=indic_mix=indic_stem=106 hits/0 misses. Compare to **Rung 4:
11/78 top-1, 25/78 top-5, 10 bluffs, 11/55=20% @ 52%, guard 10/36**. Graduates
ONLY on a strictly better precision/coverage tradeoff while the guard holds
≥8/36 — a top-5 gain made of more gate-passing false answers does NOT graduate.
**Do not retune 0.25 after seeing the result.** Even a win stays experimental
(this set shaped both the stem hypothesis and the gate; product needs a
prospective wild set + the 85% bar). Whisper stays default.

## Env / graveyard
venv_train (py3.11), numpy<2.5, macOS **fork not spawn**, cache keys **NFD**,
no ffmpeg (numpy audio). No RNNT, VAD/segmentation, M2/M3, ISO/SCES, new
thresholds/languages/prompts, raga features, max-fusion, raga gating, DTW/Qmax,
prompted turbo, or `kn`-list tweak. One variable = the stem source. Commit is
yours; push is Deepti's.
