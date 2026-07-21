# REVIEW BRIEF — for an incoming reviewing agent

Written 2026-07-20 for a fresh, strong model asked to do code review, propose
new ideas, and rethink the system. You have no prior context on this project.
This document is the fastest honest path into it.

**Read in this order:** this file → `ARCHITECTURE.md` (what is live vs dead) →
`handoff_state_and_progress.md` §4 (the failure log) → `HANDOFF_VERFIER.md`
(verification protocol). Everything else is historical detail.

---

## 1. What the product is

Point a phone at a live Carnatic performance, or sing/hum, and get back within
seconds: **which composition** (headline), **which raga** (secondary, honest
confidence), and **lyrics + meaning**.

Why this is not Shazam: fingerprinting matches *exact recordings*. The value
here is identifying a **composition across renditions that have never been
recorded** — live concerts, students singing. That is version identification,
a different and much harder architecture. The defensible asset is a verified
Carnatic composition/rendition graph, which does not exist anywhere else.

Operator: Deepti — Carnatic musician, high-school student, CS/ML background.
She is the domain authority on anything musical. She validates by ear; the
agent does not overrule her on raga or meaning judgments.

## 2. The measured reality (read this before proposing anything)

Latest wild-clip scoreboard, 2026-07-20, verbatim from the eval's own output:

```
===== SCORE over 78 in-catalog + 28 OOC clips =====
composition top-1 11/78  top-5 18/78
OOC reject  24/28  (bluffs: 4)
raga        top-1 18/85  top-3 21/85   (clips with known raga truth)
raga via catalog backfill 8/36
```

Raga note: top-3 (21) is barely above top-1 (18) — when the raga model is
wrong the true raga usually is not even in the top 3. Wild-clip raga
posteriors collapse; the lever is the input (tonic/drone estimation), not
output reranking. Rate is unchanged from the 63-clip baseline (9/43 = 21%).

Split by how the clips were obtained:

| slice | top-1 | top-5 | note |
|---|---|---|---|
| curated by Deepti (36) | 8/36 (22%) | 12/36 | reproduces the 07-18 baseline exactly — no regression |
| auto-fetched (42) | 3/42 (7%) | 6/42 | arbitrary 60 s windows; closer to real use |

Failure decomposition on the 42 auto-fetched clips:

```
27  ASR-dead (whisper produces nothing usable in any language)
12  ASR ok, matcher missed
 3  top-1 hit
```

**The stated goal is 80-90% top-1. Current is 14%.** Treat every proposal
against that gap honestly; the project does not want encouragement, it wants
things that move the number.

## 3. The binding rule of this project

**The wild clip set in `~/sung_tests` (106 clips, filename ground truth) is
the only scoreboard. No same-corpus benchmark green-lights anything.**

This rule was bought expensively. A cover-song method (Qmax) scored 63-67% on
internal full recordings and **0%** on wild 60 s clips. A "55% end-to-end short
clip" number was artist/recording-family flattered. Most recently (2026-07-20)
a CoverHunter CSI model reached dev `hit_rate` 1.0 — but 142 of 189 validation
clips had a *different crop of the same source recording* in the reference
pool, so the metric measured near-fingerprinting, not composition ID.

The rule now extends to eval-set *construction*, not just eval results. Before
believing any metric, ask: **what is the cheapest way to get this number that
isn't the capability we care about?**

Also note from the table above: even the curated 22% was flattered relative to
arbitrary windows (7%). Curation is a leak too.

## 4. The graveyard — do not propose these

Each was built, measured, and beaten. Numbers are in
`handoff_state_and_progress.md` §4 and `HANDOFF_CLIP_ID.md` §5.

| Approach | Measured | Why it died |
|---|---|---|
| DTW / global contour matching | 16-20% same-corpus, 0% wild | structural variation + gamaka |
| melodic n-grams, Smith-Waterman, subsequence DTW | <=10% | too brittle for gamaka |
| Qmax cover-song similarity | 63-67% full-recording, **0% on wild clips** | valid for full recordings only |
| raga-gating of composition candidates | net harm, twice | wild-clip raga posteriors collapse |
| proba blending of raga into matching | net harm at 0.5 and 0.3 | same |
| tonic estimation on wild clips | 158-371 Hz scatter on same-shruti material | unsolved; do not build on estimated tonic |
| CNN raga on tonic-rolled log-CQT | val at chance for 60 epochs | memorizes per recording; wall is tracks/raga |
| tala detection | 16.5% vs 72% majority baseline | closed |
| adding 'kn' to whisper language list | v3-only slice stayed 0/8; top-5 dropped | those clips are ASR-dead in *every* language |
| prompted whisper-turbo on CPU | fluent hallucination that defeats the gates | large-v3 property, not turbo |
| faster-whisper int8 on macOS ARM | ~1x realtime, garbage at beam=1 | speedup claims are x86-specific |
| vasista22 Indic finetunes via transformers | never actually evaluated | 3 stacked integration failures; retry ONLY via ctranslate2 |
| max-fusion pooling across ASR variants | 5/10 top-5 | weak variants inject junk; selection beats pooling |
| stacking more heuristic gates | bluffs adapted around each one | the fix is calibration, not gates |

The strongest meta-lesson: **degraded audio pushes whisper into *confident*
hallucination**, so no confidence signal anywhere in this system can be trusted
as evidence of correctness without calibration.

## 5. Where fresh thinking is genuinely wanted

These are open, and the incumbent plan may well be wrong. Push back hard.

1. **Is the 80-90% top-1 goal reachable at all on arbitrary wild windows?**
   The alternative framing is precision-at-coverage: answer ~35% of clips at
   ~85% precision, abstain otherwise. Is that the right product bar? What does
   the literature actually support for sung-query composition ID?
2. **ASR is 64% of the measured gap.** IndicConformer-600M and IndicWhisper
   have never been properly evaluated here (all three prior attempts were
   integration failures). Is that the right ladder? What about singing-adapted
   ASR, VAD chunking, n-best/segment-level output instead of a single string?
3. **The matcher converts only 3 of 15 clips where ASR works.** That is a
   second wall nobody has attacked. Pallavi-line phonetic indexing?
   Segment-alternative matching? Learned reranking?
4. **Clip-type routing.** A large share of clips contain no sahitya at all
   (alapana, thani, instrumental). Today they count as composition failures.
   How should the scoreboard and the UX treat them?
5. **Score calibration.** The hardest bluff class is a *correct* transcript
   that false-matches (Om Jai Jagdish → pAhirAmadhoothA at score 1.201). No
   gate fixes this. What is the principled approach given ~100 labeled clips?
6. **Is the CSI/melody channel worth continuing?** See §3 for the
   contamination finding. The clean re-score is pending.
7. **Data strategy.** Everything data-hungry is gated on a feedback flywheel
   that is built but not deployed. Is that the right sequencing, or should
   something else come first?

## 6. Hard constraints

- **Zero cost**, ~30 days from 2026-07-18. No paid API calls. A staged Claude
  Haiku batch (~$3.54) exists but Deepti **explicitly declined** authorizing
  it; it is gated behind `CARNATIFY_BILLING_OK=1`. Do not propose spending as
  an immediate step.
- **Deploys and pushes are Deepti-run.** Agent deploys are blocked by a
  permission classifier.
- **`models/raga_classifier.pkl`** (production) must not be overwritten
  without explicit sign-off.
- Local machine: macOS ARM, **no ffmpeg** (load audio via librosa/essentia;
  feed whisper numpy arrays, never file paths). Two venvs — `venv` (py3.14)
  and `venv_train` (py3.11); matcher/ASR/eval all run in **venv_train**.
  Colab Pro is available for GPU.

## 7. How to verify claims in this repo

`HANDOFF_VERFIER.md` holds the full protocol. The short version:

- Reproduce the scoreboard: `venv_train/bin/python identify_clip.py ~/sung_tests`
  (add `--no-raga` to skip the 1.1 GB RF). **Quote the SCORE block verbatim;
  never recompute by hand.**
- Before calling a clip out-of-catalog: `grep -i "<title>" data/catalog_titles.txt`
  (7 of 10 hand-picked "OOC" clips were actually in the registry).
- Registry raga metadata is not trustworthy — it contains rows parsed from
  addresses and dates.
- A long eval's log lags: `identify_clip.py` is not run with `-u` and buffers
  through pipes. Track progress by transcript-cache key counts instead.

## 8. Repo orientation

- `identify_clip.py` (root) — **the live matcher**, standalone, ~1,500 lines.
  Everything in `src/carnatify/ml/` related to composition or tala is legacy or
  graveyard; each module carries a `STATUS:` banner in its docstring.
- `backend/` — FastAPI; `/identify` and `/feedback` are staged but NOT
  deployed. Two legacy endpoints still serve the old ~16% matcher.
- `graphify-out/` — AST code graph. **Navigation aid, not authority**: it has
  no concept of dead code. `graphify explain <symbol>` surfaces STATUS banners;
  `graphify query` does not. Read the file before acting on any node.
- Data assets and their caveats: `ARCHITECTURE.md` §"Data assets".
