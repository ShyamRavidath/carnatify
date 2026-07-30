# Codex — design brief: whisper↔indic arbitration + abstain gate (Rung 4)

You are the reviewer/ideator (read-only on code). Deliverable: a **Fable-ready,
one-shot implementation spec** for the next rung, written into `AGENT_LOG.md`,
plus a critique of the diagnostic it rests on. Do NOT write code. Front-load the
design here so Fable spends its scarce credits building, not exploring.

## Read first
`AGENT_LOG.md`, newest-first: the three latest Opus entries — "Rung 3 landed"
(Fable's SCORE), and **"Rung 3 diagnostic"** (the evidence this brief is built
on) — then `METRIC_CONTRACT.md` and the graveyard (`REVIEW_BRIEF.md §4`).

## The situation (from the diagnostic)
- IndicConformer is a real **recall** channel: top-5 21→29. But as-is it answers
  ~everything → **27/28 OOC bluffs**, precision 8% @ 91%. Not shippable alone.
- whisper and indic win **disjoint** clips. **Union ceiling: top1 12 / top5 36**
  (vs 8/29 best single channel). That is the prize.
- **Raw score cannot gate** the indic channel — bluff vs true score medians
  1.25 vs 1.28, fully overlapping. Proven dead; do not propose score-threshold
  calibration.
- The separating feature is **q_cov** (share of the transcript's IDF weight the
  matched work explains): bluff med 0.12 vs true med 0.28. A `q_cov>=~0.26 AND
  ordered` gate would cut OOC bluffs 27→~4 (reject ~24/28) while keeping ~5/8 of
  indic's true top-1. All 8 true answers had `ordered=1`.

## What the spec must resolve (be concrete)
1. **Abstain gate design.** Which M1 align feature(s) (`q_cov`, `ordered`,
   `distinct_hits`, `matched_idf/total_idf`) and what operating point — and how
   to choose it **without overfitting** n=8 true / 27 bluff. Prefer a simple
   reviewed rule over a fitted model (M3/learned rankers are parked; a logistic
   on 35 points would be graveyard-shaped). State whether the gate applies to
   the indic/translit channel only or to whisper too (whisper is already ~21-24/
   28 OOC — does the same gate help or hurt it?).
2. **Arbitration policy — explicitly NOT max-fusion** (graveyarded: weak
   variants inject junk, 5/10 top-5). Define per-clip channel selection: e.g.
   whisper as primary answerer; indic answers only when it passes the gate and
   (whisper abstains OR indic's evidence dominates). Give the exact decision
   rule and the tie-break, so Fable implements one thing.
3. **Plumbing flag for Fable.** Arbitration needs BOTH caches in one eval run;
   today `CARNATIFY_ASR_BACKEND` selects a single v2 cache. Name the minimal
   change (read both caches per clip; merge candidate rows before selection) —
   without changing thresholds elsewhere in the same rung.
4. **Metric + guards.** Co-publish precision-at-coverage WITH top1/5 + OOC
   bluffs (`METRIC_CONTRACT`). Curated-36 guard must stay ≥8/36. One
   behavior change = one verbatim `~/sung_tests --cache-v2` SCORE.
5. **Scope.** This rung is arbitration+abstain ONLY. The pre-approved
   one-variable ASR ablations (RNNT-same-mix / segmentation / stem-lane) are
   LATER and chosen from this rung's SCORE — do not bundle them.

## Also do (reviewer duty)
Critique the diagnostic before building on it: is q_cov computed the same at
answer-time as in the detail pass? Is the n=8 separation plausibly signal vs
noise? Any confound (e.g. the gate quietly killing whisper's existing OOC
precision, or the union-12 double-counting the 2 equivalent-set clips)? If the
evidence is too thin to commit Fable, say so and name the cheaper measurement
that would settle it (Opus can run it zero-cost).

Graveyard reminder: no max-fusion, no raga gating/blending, no global DTW/Qmax,
no fitted reranker on tiny n, no new answer gates beyond the single abstain rule
this rung introduces. Nothing here touches push/deploy/paid actions.
