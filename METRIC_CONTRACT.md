# METRIC CONTRACT — the standing scoreboard format

Adopted 2026-07-21 (Codex review, accepted by Deepti; AGENT_LOG entry
[2026-07-21 20:00]). This replaces "80-90% top-1" as the product bar.
Any reported result MUST publish all five numbers below together, on the
frozen wild set in `~/sung_tests` — never a subset, never same-corpus.

## Why the old goal was retired

An arbitrary 60 s window can contain alapana, thani, tuning, applause, or
silence: no composition-identifying evidence exists, even for an expert
listener. Treating every window as a mandatory prediction creates an
irreducible error floor and rewards bluffing. The defensible product is
**selective**: answer when the evidence supports one work, abstain with an
explanation (and a guided-retry prompt) otherwise.

"80% top-1" survives only as a long-term stretch goal for
composition-eligible sung clips, potentially after one guided retry.

## The five published numbers

1. **Precision at coverage** (PRIMARY). Among answered clips, fraction
   correct top-1; coverage = answered / all queries. The denominator
   includes OOC and no-sahitya windows — an answered OOC clip is a false
   answer. Product bar: **>= 85% precision at any honest, nontrivial
   coverage**, then grow coverage without dropping precision.
2. **Overall in-catalog top-1 and top-5.** Prevents an abstain-heavy system
   from looking better without finding more compositions.
3. **OOC false-answer rate** (bluffs). Kept separate and visible.
4. **Eligibility-stratified outcomes.** Sahitya / composed instrumental /
   alapana / thani / unusable-noisy. Diagnostic strata only — never a way
   to drop hard clips from the overall result. Stratum labels are assigned
   from the audio by Deepti's ear, never from the prediction or filename
   metadata.
5. **Assisted recovery.** For routed abstentions: does one prompt to
   capture a sung pallavi produce a correct answer on the next attempt?

## Current baseline (2026-07-22, 106 clips, post-Phase-0, --cache-v2)

- answered 47/106, correct top-1 14/47 (30% precision at 44% coverage)
- in-catalog top-1 14/78, top-5 23/78
- OOC bluffs 7/28
- nominal "high" tier 9/17 correct — current confidence labels are NOT
  calibrated probabilities; treat them as UI hints only until Phase 4
  calibration lands.
- Known parked channel: transliterated native-script matching
  (`CARNATIFY_V2_TRANSLIT=1`) reaches top-5 29/78 at 85% coverage but only
  16% precision (26/28 OOC bluff) — unlocking it is the Phase 4
  calibration target.

Pre-Phase-0 reference (2026-07-20): top-1 11/78, top-5 18/78, bluffs 4/28,
27.5% precision at 38% coverage.

## Standing rules

- `~/sung_tests` (106 clips) is a **development/regression set** — it has
  already shaped design choices. Grouped cross-validation on it may
  diagnose; it cannot green-light. Green-lighting a threshold or model
  requires **prospective** evaluation: each newly acquired wild clip is
  scored once with the frozen system before joining the development set.
- The curated original 36 in-catalog clips are the **regression guard**:
  composition top-1 must not drop below 8/36 for any accepted change.
- No same-corpus benchmark, and no eval whose reference pool contains a
  crop/sibling of the query's source recording, counts for anything
  (REVIEW_BRIEF §3).
- SCORE blocks are quoted verbatim from the eval output into AGENT_LOG.md
  (HANDOFF_VERFIER.md protocol); never recomputed by hand.
