# Codex — design brief: pick the next ASR ablation + write its Fable spec (Rung 5)

You are the reviewer/ideator (read-only on code). Deliverable: **(1) a reasoned
choice** of which single pre-approved ASR ablation goes first, and **(2) a
Fable-ready, one-shot implementation spec** for that one ablation, written into
`AGENT_LOG.md`. Do NOT write code. Front-load design here so Fable spends its
scarce credits building the right thing once.

## Read first
`AGENT_LOG.md`, newest-first: **"Rung 4 landed"** (hybrid arbitration SCORE),
the **"Rung 3 diagnostic"**, and Fable's **"Rung 3 landed"**. Then
`METRIC_CONTRACT.md` and the graveyard (`REVIEW_BRIEF.md §4`).

## Where we are
- Whisper (default): top-1 8/78, top-5 21/78, 17% @ 44%, 7 OOC bluffs.
- Indic CTC mix-only: top-5 29 but 27/28 bluffs (recall channel, not precise).
- **Hybrid (Rung 4, landed): top-1 11/78, top-5 25/78, 20% @ 52% coverage,
  10 bluffs, guard 10/36.** Experimental, kept; Whisper still the default.
- The q_cov>=0.25 + ordered gate admits indic only 10× of ~96 raw answers —
  precision is the binding constraint (20% vs the 85% product bar), not raw
  recall. **Any new ASR recall only helps if the recovered sahitya PASSES that
  gate** (high q_cov, ordered) rather than adding more filtered bluffs.

## The three pre-approved one-variable ablations (choose ONE)
All go through the existing hybrid arbitration unchanged; one variable; own
full `--cache-v2` SCORE; guard must stay >=8/36.
1. **RNNT-same-mix** — IndicConformer's RNNT decoder on the SAME mix audio
   Fable already caches (CTC-only today). Better decoder, but same
   instrumentally-polluted input.
2. **Stem-as-independent-lane** — run IndicConformer on the Demucs vocal stem
   (indic is mix-only today; Whisper already runs mix+stem because "violin/
   mridangam drown the sahitya" — that stem pass is a KEPT rescue). Likely the
   strongest recall prior for instrument-dense Carnatic audio, and may reuse
   existing Demucs stems. New lane, arbitrated like any channel — never fused.
3. **Vocal-active segmentation (VAD)** — ASR on vocal-active windows, yielding
   per-segment hypotheses. Its main payoff (per-segment candidate generation)
   is really M2 fuel and a LATER rung; heaviest to build.

## What the spec must resolve (be concrete)
- **The pick + why**, argued from the evidence above — specifically which
  ablation most raises TRUE recall that clears the q_cov+ordered gate, not just
  raw candidate count. State the expected failure mode it targets (e.g. "10/12
  dead clips are instrument-masked" ⇒ stem) with whatever support the log gives.
- **Cache/config identity** for the new hypotheses (own config_id, own or
  extended v2 cache; must not collide with the CTC-mix indic cache or the
  whisper cache; error!=empty preserved). It plugs into `variants_from_v2` /
  the hybrid arbitration without changing the 0.25 gate this rung.
- **Smoke test** (few known dead + live) before the 106-run; smoke makes no
  capability claim. Then one full hybrid SCORE + precision@coverage + per-
  channel/arbitration-reason counts + both cache hit/miss + curated-36 guard.
- **Scope:** exactly one ablation. Do not bundle the other two, ISO/SCES, M2/M3,
  or any gate re-tuning. The next ablation is chosen from this rung's SCORE.

## Reviewer duty (the pattern that has worked)
Before committing Fable, say whether a **cheap zero-cost Opus pre-diagnostic**
should gate the spend (this is how Rung 3→4 was de-risked). Note: RNNT and VAD
have NO existing data to preview without the model, but the **whisper cache
already holds mix+stem hypotheses** — Opus can cheaply measure how often
whisper's stem pass beats its mix pass and whether the ~12 still-dead clips show
any whisper-stem signal, as a proxy for the stem-lane hypothesis. If that proxy
is worth running first, say so and I'll run it before Fable is prompted.

Graveyard reminder: no max-fusion (arbitrate, never pool), no raga gating/blend,
no DTW/Qmax, no fitted ranker on tiny n, no new answer gates, no prompted/`kn`
Whisper, vasista22 only via CTranslate2. Nothing here touches push/deploy/paid
or any Deepti-blocked action.
