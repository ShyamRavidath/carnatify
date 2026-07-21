# Carnatify — Vision & Architecture Handoff

Written 2026-07-18. Audience: incoming agent taking the project from validated
prototype toward production. Companion file: `handoff_state_and_progress.md`
(state ledger, failure log, roadmap). This file is strategy + architecture +
external research. Both files supersede nothing — the committed HANDOFF_*.md
docs remain the detailed historical record; these two are the consolidated
forward-looking package.

---

## 0. Reality check (read before believing any plan)

**Current wild-clip scoreboard (2026-07-18, 63 frozen clips, measured):
composition top-1 8/36 (22%), top-5 13/36 (36%), OOC reject 23/27, raga top-1
9/43.** The production mandate is 80–90% top-1. That is a ~4x gap and no
single fix in this codebase closes it. Every prior internal benchmark that
suggested otherwise (55–67% same-corpus numbers) was proven flattered; the
binding rule of the project is: **wild-clip eval is the only scoreboard, and
no same-corpus benchmark may green-light anything.** Any architecture below
must be judged against that eval (and its successors as it grows).

The honest decomposition of the gap, from measured per-clip failure analysis:

| Failure bucket | Share of misses | Binding constraint |
|---|---|---|
| ASR-dead clips (whisper hears junk/empty in every language) | ~1/3 of in-catalog misses | ASR quality on wild Carnatic audio — THE bottleneck |
| ASR partial but matcher misses | ~1/3 | Matching/scoring, registry coverage of sung line |
| No-lyrics clips (alapana, instrumental) | rest | Needs melody/raga path, currently weak on wild audio |

So: 80–90% is not reachable by tuning the current lyrics matcher. It requires
(a) a step-change in ASR on sung Indic audio, (b) a second, melody-based
retrieval channel that actually works on wild clips (the current one is 0%),
and (c) the data flywheel to train/calibrate both. That is the architecture
below.

## 1. Ultimate production goal and commercial vision

**Product:** SoundHound-for-Carnatic. Point phone at a live performance (or
sing/hum) → within seconds: composition (headline, top-5 UX acceptable),
raga (secondary, honest confidence), lyrics + meaning. Then: concert-companion
mode (continuous listening, live setlist), student mode ("you're singing X in
raga Y"), lyrics/meaning depth as the freemium layer.

**Why incumbents can't trivially do this:** Shazam-class systems match exact
recordings via fingerprints; Carnatic value is *composition-level* ID across
renditions that have never been recorded before (live concerts, students).
That is version identification / cover-song ID, not fingerprinting — a
different and much harder architecture, and it is data-starved without a
verified Carnatic composition/rendition graph. **The moat is the data asset**:
canonical composition registry (8,688 entries today) + alias tables + lyric
lines + rendition graph + user-confirmed wild queries. Models are replaceable;
this asset is not. Every architectural choice must feed it.

**Monetization path (App Store):** free tier = ID + basic lyrics; subscription
= meanings/notation depth, concert-companion mode, student feedback. Do NOT
build payment infrastructure before the accuracy bar makes the product
non-embarrassing; do build the feedback flywheel into the very first public
release, because early user queries are irreplaceable training data.

**Deployment honesty:** today's stack is Next.js on Vercel + FastAPI on a free
HF Space (CPU, ephemeral disk, ~30–60 s per 60 s clip). There is no iOS/React
Native pipeline yet. The mobile path is: (1) keep inference server-side
initially (a phone app is a thin client — RN or Swift — hitting /identify);
(2) only consider on-device (whisper.cpp / CoreML) after the server pipeline
is accurate, because on-device constraints would freeze today's weak models.
Free-tier serving will not survive real traffic: budget for one small GPU box
(or serverless GPU per-request) as the first real infrastructure spend —
it simultaneously solves the latency problem and unlocks large-v3-grade ASR,
which is worth measured accuracy points (GPU large-v3-on-stems was +1 top-1
on the old 10-clip set and cracked a CPU-dead clip).

## 2. Target architecture (hybrid, calibrated, abstention-first)

One canonical composition index; multiple noisy retrieval channels voting over
it; per-channel calibration learned from user-confirmed queries; abstention as
a first-class output ("not sure — sing a cleaner pallavi" beats a bluff).

```
audio (60s)
  ├─ clip-type router (kriti / alapana / thani / instrumental)  [cheap, high win]
  ├─ ASR channel:  vocal separation → best-of-N ASR → phonetic fold
  │                → token/line matcher over registry (today's path, hardened)
  ├─ melody channel: CSI-style embedding (ByteCover/CoverHunter-class)
  │                → ANN search over rendition embeddings  [to be built]
  ├─ raga channel:  TDMS/RF today → filter+prior, never sole decider
  └─ fusion: calibrated log-odds per channel → top-5 + confidence → abstain below threshold
```

### 2.1 ASR channel (biggest near-term lever)

Measured facts: whisper large-v3-turbo CPU + demucs stems is the shipped path;
8 dasa-kriti clips are ASR-dead in *every* language tried (adding 'kn' was
tested 2026-07-18 and reverted — transcripts are near-empty junk regardless of
language; the audio/domain mismatch is the problem, not the language list).

Upgrade ladder, in order of expected value per effort:

1. **GPU whisper large-v3 on stems** — already proven to add points; blocked
   only on free-infra constraint. First infra spend.
2. **Indic ASR checkpoints via ctranslate2** (NOT transformers pipeline —
   three failures documented): IndicWhisper (best WER on 39/59 Vistaar
   benchmarks), AI4Bharat **IndicConformer-600M multilingual** (22 languages
   incl. Kannada/Telugu/Tamil — directly targets the dasa-kriti dead zone).
   Run as an *additional variant* in the existing best-of-N selection, not a
   replacement.
3. **Singing-adapted ASR.** Literature: source-separation + Whisper is SOTA
   on the Jam-ALT lyrics-transcription benchmark *without fine-tuning*
   (arXiv 2506.15514) — validates our demucs-first design; the next step it
   suggests is better separation (see 2.4) and long-form chunking with VAD.
   Fine-tuning Whisper on aligned Carnatic sahitya (lyrics.db + audio via
   forced alignment) is the eventual domain-adaptation play — a Colab-scale
   project, gated on the flywheel producing aligned data.
4. **N-best / segment-level matching** — match registry n-grams against
   whisper's segment alternatives instead of the single final string; the
   matcher is coverage-based, so recall-oriented transcripts help.

### 2.2 Melody channel (the NN investment — do it right this time)

Everything tried so far (Qmax cover-song, DTW variants, n-grams,
Smith-Waterman) is 0% on wild 60 s clips — fully documented in the failure
log. The modern equivalent of what SoundHound did with melody matching is
**learned version-identification embeddings**:

- **State of the art:** ByteCover2/3/3.5 (ResNet-based; ByteCover3 explicitly
  targets **short queries** — our exact regime), CoverHunter (attention +
  alignment, 128-d embeddings, open PyTorch implementation), CQTNet, MOVE.
  Retrieval = one ANN lookup over precomputed rendition embeddings —
  milliseconds at our catalog scale, phone-friendly server cost.
- **Dataset for pretraining:** Discogs-VI (2024): ~1.9 M versions / 348 k
  cliques — pretrain a version-ID embedding on Western versions, then
  **fine-tune on the Carnatic rendition graph** (same composition, different
  artist/era = positive pair). We already have the seed: qmax catalog maps
  1,421 tracks with multi-rendition works, and the registry/rendition graph
  is designed to grow exactly this.
- **Data augmentation pipeline (train-time):** pitch shift ±6 semitones
  (shruti invariance — do NOT rely on tonic estimation, it is unsolved on
  wild clips), time-stretch 0.8–1.25x, random 20–60 s crops (structure
  invariance), additive mridangam/violin/tanbura stems and crowd noise
  (wild-audio robustness), codec/phone-mic simulation (opus/AAC re-encode,
  bandpass). This augmentation set directly encodes every failure mode the
  melody path died on.
- **Synthetic data:** Saraga-Carnatic-Melody-Synth (SCMS, Zenodo) provides
  time-aligned vocal pitch for synthesis; Sanidha (2025) is a studio-quality
  multi-stem Carnatic dataset. Both usable for augmentation/eval without
  scraping.
- **Honest gate:** this is weeks of GPU work with real risk; the failure log
  says contrastive embedding was always the "only idea with a pulse" for
  melody-on-clips. Build it AFTER the flywheel ships, not before — confirmed
  user queries are the fine-tuning set that makes it work.

### 2.3 Raga channel

Full-track raga is solved-ish (72.8% top-1 / 84.7% top-3 grouped CV, 18
ragas); clips are weak (9/43 wild). Two real levers, both cheap relative to
new modeling: **drone-presence detection** (the single n=1 win: real tanbura →
correct tonic → correct raga; detect drone, gate confidence display, prompt
users to include tambura) and **catalog backfill** (a confident composition
match pins raga better than any model — already implemented, 6/21). Deep
raga modeling (DeepSRGM-style LSTM on pitch sequences, 88% on CompMusic) is
published but note: those numbers are same-corpus, exactly the benchmark trap
this project already fell into; treat as architecture reference, not expected
accuracy. The measured data-curve (accuracy linear in tracks-per-raga, 70%
needs ~20 tracks/raga) says raga accuracy is bought with data, not models.

### 2.4 Vocal separation

Demucs htdemucs is generic-Western-trained and is both the latency bottleneck
(CPU) and a quality ceiling on Carnatic mixes. ISMIR 2025: regression-guided
latent diffusion trained on Carnatic live multi-stem recordings with bleed
(Plaja-Roglans/Rocamora line of work) — a repertoire-specific separator that
targets exactly our audio. Evaluate it as a drop-in stem source for the ASR
channel; even a modest stem-quality gain compounds through ASR and melody
channels.

### 2.5 Fusion, calibration, abstention

- Each channel emits calibrated log-odds; calibration fit ONLY on
  user-confirmed wild queries (never internal CV — proven to lie).
- Raga as *filter with escape hatch* (posterior top-8 shrinks candidates;
  lyrics can override) — proba blending was measured harmful twice.
- Abstention thresholds tuned on the OOC half of the eval set (27 must-abstain
  clips today). The remaining hard class — genuine-transcript false match
  (Om Jai Jagdish → pAhirAmadhoothA at 1.201) — is a score-calibration /
  margin-analysis problem: collect score distributions of true matches vs
  OOC matches across the eval set and place the answer/abstain boundary
  empirically. No gate hack fixes it; this is the principled fix.

## 3. Lyrics → meaning pipeline (the "sketchy semantic" deficit)

Current state, honestly: 3,252 titles seeded, **8 meanings generated** (free
Gemini quota exhausted), `lyrics_original` empty for most titles (Karnatik
scraper built but never run at scale), HF Space cache is ephemeral so runtime
generations die on rebuild. The quality of generated meanings was good; the
pipeline is starved, not broken.

Fix, in order:

1. **Run the Karnatik scraper at scale** — meanings generated from actual
   sahitya text are categorically better than title-only guesses; this also
   feeds the matcher's lyric-line channel (karnatik_lyrics.json already
   drives line-level matching).
2. **Replace free-tier LLM with a paid batch job.** This is a one-time bulk
   generation + trickle for new entries — the perfect Batches API workload.
   Concrete option (Claude API, from current docs): **Haiku 4.5**
   ($1/$5 per MTok) via the **Message Batches API at 50% off** → ~8.7k
   meanings × (~1.5k tokens in / ~500 out) ≈ 13M in / 4.4M out ≈ **$8–10
   one-time** at batch pricing; step up to Sonnet 5 (~$2/$10 intro) only if
   Deepti's spot-checks of Haiku quality fail — she is the musical QA. A paid
   Gemini tier is the same order of magnitude; the point is: stop engineering
   around free-tier rate limits, the whole corpus costs less than lunch.
3. **Verification queue:** meanings are product surface; wrong meanings burn
   trust with exactly the community that is the moat. Deepti (later: musician
   volunteers) approves; store verifier + timestamp per row; "verified by
   musicians" badge.
4. **Persist generated meanings** in the committed lyrics.db (or the private
   HF dataset), never only on Space disk.

## 4. Data & eval infrastructure to reach the accuracy bar

- **Feedback flywheel is the whole ballgame** — every confirmed query is a
  labeled wild clip (the starved data class), a calibration point, a
  fine-tuning pair, and an alias discovery. /identify + /feedback are built
  and staged; ship with confirm-button UI from day one.
- **Regression suite growth:** 63 → 200+ clips, stratified (era, gender,
  recording quality, clip type, language, in/out-of-catalog). Track
  per-stratum numbers; aggregates hide failure modes (the v3-only dasa slice
  going 0/8 was invisible in the aggregate).
- **CI gate:** one command prints the scoreboard (exists:
  `identify_clip.py ~/sung_tests`); wire it so any matcher/model change
  diffs against the last committed SCORE block and a regression blocks merge.
- **Registry hygiene as ongoing product work:** alias merge, raga-vocabulary
  validation on ingest (address/date rows have leaked in before), pallavi-line
  phonetic index (most 60 s clips capture the pallavi — index it explicitly).

## 5. Sequencing (payoff-ordered)

1. Ship staged backend + confirm-button frontend (flywheel live). Deepti
   sign-off gates deploy; feedback dataset created before go-live.
2. Meanings: Karnatik scrape → paid batch generation → verification queue.
3. GPU serving (small box or serverless) → large-v3 ASR + latency fix.
4. IndicConformer/IndicWhisper via ctranslate2 as added ASR variants; rescore.
5. Clip-type router + drone detection (cheap, both measured-motivated).
6. Score calibration / margin analysis across the growing eval set.
7. CSI embedding channel (pretrain Discogs-VI, fine-tune rendition graph,
   augmentation pipeline as specced) once confirmations accumulate.
8. Mobile thin client (RN) once accuracy is demo-worthy; on-device later.

## Sources

- ByteCover3 (short-query CSI): https://www.researchgate.net/publication/371287966_Bytecover3_Accurate_Cover_Song_Identification_On_Short_Queries
- CoverHunter (open impl): https://github.com/Liu-Feng-deeplearning/CoverHunter
- Discogs-VI dataset: https://arxiv.org/abs/2410.17400
- QbH semi-supervised dataset collection: https://arxiv.org/pdf/2312.01092
- Source separation + Whisper for lyrics transcription (Jam-ALT SOTA, MUSDB-ALT): https://arxiv.org/abs/2506.15514
- DeepSRGM raga recognition: https://arxiv.org/abs/2402.10168
- Unseen-raga identification/clustering: https://arxiv.org/pdf/2411.18611
- Carnatic singing-voice separation, regression-guided latent diffusion (ISMIR 2025): https://ismir2025program.ismir.net/poster_191.html
- Repertoire-specific vocal pitch (SCMS): https://transactions.ismir.net/articles/10.5334/tismir.137
- Saraga-Carnatic-Melody-Synth: https://zenodo.org/records/5553925
- Sanidha multi-modal Carnatic dataset: https://arxiv.org/html/2501.06959v1
- AI4Bharat IndicConformer 600M multilingual: https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual
- AI4Bharat Vistaar benchmarks: https://github.com/AI4Bharat/vistaar
