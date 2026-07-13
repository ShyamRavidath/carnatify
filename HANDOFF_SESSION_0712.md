# HANDOFF 2026-07-12: clip ID shipped-grade, deploy staged, awaiting clips + sign-off

Written 2026-07-12. Audience: next agent. Supersedes the composition/clip
sections of `HANDOFF_CLIP_ID.md` (its §5 failure graveyard and §8 gotchas
still fully apply — read them first). `BRAINSTORM_COMPANY.md` is the
strategy doc; its §8 sequencing is what we're executing.

Standing Deepti preferences: caveman response mode (see memory / skill);
free-of-cost infra only; Colab Pro available; she can record test material
and validate musically. Wild-clip eval is the ONLY scoreboard — no
same-corpus benchmark may green-light anything (hard rule).

## 1. The goal

SoundHound-for-Carnatic as a potential company. Point phone at performance
(or sing), get composition (headline, top-5 UX acceptable) + raga (secondary,
honest confidence) + lyrics/meaning. Target ≥50% on wild ~60s clips.
Strategy: the composition registry + rendition/query graph is the moat;
models are replaceable. User-confirm feedback loop = data flywheel.

## 2. Scoreboard (10 wild clips in ~/sung_tests/, + 1 new)

| stack | comp top-1 | comp top-5 | bluffs |
|---|---|---|---|
| 2026-07-11 morning (turbo-only prototype) | 2/10 | 6/10 | yes |
| + dual-ASR (turbo + demucs-stem) + policy v2 | 3/10 | 6/10 | 0 |
| + composition registry + quality tie-break (CURRENT, CPU) | **4/10** | **6/10** | **0** |
| + GPU large-v3-on-stems transcripts (no free serving) | 5/10 | 7/10 | 0 |

On clips the system answers: 4/6 top-1, 6/6 top-5 (CPU). All 3 no-lyrics
clips abstain cleanly. Raga on wild clips still ~0 — EXCEPT: new 11th clip
(Deepti's sister + tanbura, `nagumOmu__Jaganmōhini_realsinger.m4a` in repo
root) got raga top-1 CORRECT (Jaganmōhini 0.377). First ever. Cause: real
drone → TonicIndianArtMusic locks → TDMS in right rotation. Tonic is THE
raga bottleneck and drone-in-clip solves it. Composition on that clip:
ASR-dead (honest abstain; whisper hears English junk).

ASR-dead clips (all variants): Bhuvini Dasudane (12 variants tried), the
sister nagumOmu clip. Tulasi Bilva is CPU-dead but GPU large-v3-on-stems
cracks it reproducibly ("tudasi bilwe ×5").

## 3. Current state of the code (all committed + pushed, main @ 3509917)

**Core pipeline — `identify_clip.py` (single source of matcher truth):**
- Audio → whisper large-v3-turbo on original (langs None/ta/te/hi) AND on
  demucs vocal stem (None/ta/te) → per-variant registry matching → policy-v2
  selection (best usable variant by top score; prefer stem within 0.15;
  hallucination stoplist regex `HALLUC`; usable = max token repetition ≥ 2;
  abstain < 0.35) → top-5 + confidence high/medium/low/none.
- Matcher: token coverage + repetition bonus + order bonus (`lyr_score`),
  scored per registry entry as max over spelling-variant aliases, epsilon
  tie-break by mean fuzzy ratio of matched tokens (exact beats fuzzy-junk).
- Raga: clip RF (TDMS, 54 classes, `models/raga_clip_rf.pkl` 1.1 GB
  gitignored — rebuild `venv_train/bin/python train_raga_clip_model.py`)
  always reported low-confidence.
- Run: `venv_train/bin/python identify_clip.py <file-or-folder> [--json]
  [--no-raga] [--fast]`. Labeled folder = regression suite; filename truth
  `<title>__<raga>.m4a` (no extra `_suffix` after raga — breaks scoring).

**Registry — `build_composition_registry.py` → `data/composition_registry.json`:**
3,638 raw titles (qmax catalog + lyrics.db) → 2,231 canonical compositions,
755 alias groups, junk stripped. Deepti-facing lists:
`data/catalog_titles.txt` (grep-able, L = lyrics known),
`data/raga_model_classes.txt` (54 ragas).

**Backend (staged, NOT deployed — Deepti sign-off gates):**
- `backend/main.py`: `POST /identify` (upload → dual-ASR → matcher → top-5 +
  confidence + abstain message; `?fast=true` skips stem; 2/min rate limit)
  and `POST /feedback` (confirmed/rejected/not_in_catalog per query_id).
  Old endpoints/models untouched.
- `backend/clip_identify.py`: server wrapper; imports identify_clip (copied
  in by `bash backend/build_space.sh`). ASR engine env-selectable
  (`ASR_ENGINE=faster-whisper` opt-in; default openai-whisper).
- Feedback persistence: JSONL + best-effort push to private HF dataset
  (`HF_TOKEN` + `FEEDBACK_REPO`; create dataset repo BEFORE go-live).
  DEPLOY.md §1d has the full rollout + UI contract.
- Smoke-tested locally (module level, real cached transcripts). NOT tested
  as a running server — do one uvicorn + curl pass before deploy.

**Transcript caches (committed, keyed by filename):**
`data/whisper_transcripts_turbo.json` (original audio),
`data/whisper_transcripts_turbo_stems.json` (CPU demucs stems),
`data/transcripts_lv3_gpu.json` (GPU large-v3; Colab).
`eval/` has the variant-scoring + policy scripts. `scratch_archive_0711/`
= recovered previous-session scratchpad (historical reference).

## 4. Files actively being edited

Nothing mid-edit. Branch clean, pushed. The session scratchpad (temporary)
holds eval one-offs already superseded by `eval/` copies.

## 5. Everything tried that FAILED (this session — see HANDOFF_CLIP_ID.md §5 for the older graveyard)

1. **Max-fusion across ASR variants** (union top-10s, max score per
   composition): 5/10 top-5 — weak variants inject junk that crowds top-5.
   Selection (policy v2) beats pooling. Don't re-try pooling without
   per-source calibration data.
2. **Prompted whisper on CPU turbo** (`initial_prompt` with Carnatic
   vocab): hallucinates fluent repetitive junk that DEFEATS the repetition
   gate (alapana2 got "thank you thank you" → false answer pre-stoplist;
   Spanish loops scored rep≥2). Excluded from production pool. GPU large-v3
   + prompt on stems (BD variant) was good — it's a large-v3 property, not
   transferable to turbo.
3. **faster-whisper int8 on macOS ARM**: ~1x realtime (no speedup) and
   garbage output at beam=1. Claims are x86-specific. Left opt-in for
   on-Space benchmark only.
4. **vasista22 Indic whisper finetunes via transformers pipeline**: three
   successive failures — forced_decoder_ids hang, outdated
   generation_config incompatible with `language=`, then Colab was silently
   on CPU runtime. Never actually evaluated. Retry path: faster-whisper/
   ctranslate2 conversions of the same checkpoints, NOT transformers
   pipeline. (`colab_indic_asr.py` has the broken attempts inline.)
5. **RF-confidence tonic voting on wild clips**: still anti-informative
   (unchanged from previous handoff) — but drone-in-recording bypasses it
   (sister-clip evidence, n=1).
6. **Whisper hallucination loops observed** and stoplisted: "thank you",
   "subtitles by the amaraorg community", "satsang with mooji". The
   stoplist regex is in identify_clip.py — extend it as new loops appear.

## 6. Next steps, in the order I'd take them

1. **Deepti records 30-50 labeled clips** (protocol agreed: ~80%
   in-catalog favoring L-marked titles, ~20% deliberately out-of-catalog
   as must-abstain cases; vary singer/mic/era; with/without tanbura pairs
   to test the drone→tonic→raga effect properly). THE gate for all tuning:
   matcher fixes (sObillu-type fuzzy over-matches), voter calibration,
   clip-type router all wait on this. Do NOT tune on the current 10.
2. **Deploy on sign-off**: `bash backend/build_space.sh`, push backend/ to
   the Space, secrets per DEPLOY.md §1d (create private feedback dataset
   first). Then one end-to-end curl test + on-Space ASR latency benchmark
   (and the faster-whisper A/B there, x86).
3. **Frontend confirm-button UI**: top-5 with confidence tiers, abstain
   message rendering, confirmed/rejected/not_in_catalog buttons wired to
   /feedback. This completes the flywheel.
4. **Drone-presence detection** (cheap: low-band spectral peak stability)
   → gate raga confidence display ("drone detected" vs "rough guess") and
   prompt users to include tambura / hum Sa. Sister clip is n=1 evidence;
   the with/without-drone pairs from step 1 measure it.
5. **Clip-type router** once labeled alapana/thani/viruttam examples exist
   (voicing fraction + token stats already computed in-pipeline).
6. **IndicWhisper retry** via ctranslate2 conversions on Colab GPU —
   targets the ASR-dead clips (Bhuvini, sister nagumOmu).

## 7. Gotchas (new this session — older ones in HANDOFF_CLIP_ID.md §8)

- macOS filenames are NFD; JSON cache keys inherit it. Compare via
  `unicodedata.normalize('NFC', ...)` or the `keyof()` fold — naive `in`
  lookups silently miss (cost us one wrong eval mid-session).
- Colab reconnect after a network drop can silently land on a CPU runtime:
  ALWAYS `torch.cuda.is_available()` before long cells. "FP16 is not
  supported on CPU" in whisper output = you're on CPU.
- `models/` must be allowlist-copied into backend (build_space.sh does) —
  a blind `cp -r` drags the 1.1 GB clip RF into the Docker image.
- HF Space disk wipes on restart — feedback MUST push to the HF dataset
  repo or it dies with the pod.
- Truth filenames: exactly one `__`; anything after the raga (e.g.
  `_realsinger`) breaks raga truth-matching.
- The 5-way tie at ~0.65 with max repetition 1 is the signature of a
  garbage transcript — that's what the usability gate catches.
