# Verdict on the context180 candidate

Harness: `scripts/candidate_verdict.py`. Prereg: `CANDIDATE_VERDICT_PREREG.md`
(committed first, `b397ac8`). Output: `context180_recovered_experiment/verdict.json`.
Run 2026-09-10. Paired, cluster-bootstrapped, seed 42, 5,000 draws. Nothing refitted.

## Gates

- Gate 1 (identity): pass. Same 1,243 tracks, truth, 133 groups, identical folds.
- Gate 2 (reproduction): pass. From raw per-track records: CV 953 vs 855 correct,
  140 wins / 42 losses; dev known 102/139 vs 97/139. The handoff's integers are
  what the artifacts say.

## Results

| analysis | n | clusters | A − B | 95% interval |
|---|---|---|---|---|
| A1 CV top-1, all | 1,243 | 133 | **+7.88 pp** | [+5.69, +10.19] |
| A2 CV top-3, all | 1,243 | 133 | see verdict.json | |
| A3 CV top-1, archive rows | 861 | 98 | +9.18 pp | [+6.26, +12.29] |
| A3 CV top-1, CompMusic reference-pitch rows | 382 | 47 | +4.97 pp | [+2.34, +7.46] |
| A4 macro recall | 69 classes | | 57.84% to 66.25% | report only |
| B1 dev estimated-tonic top-1, known | 139 | 17 | +3.60 pp (11 wins, 6 losses) | [−1.68, +8.57] |
| B2 dev annotated-tonic top-1, known | 139 | 17 | +2.16 pp (8 / 5) | [−2.74, +7.09] |
| B3 dev estimated-tonic top-3, known | 139 | 17 | 0.00 pp (118 both) | [−5.22, +6.09] |
| B1m mixed-recording (ragamalika) queries | 8 | | 0 vs 0 correct | reported separately |
| C1 OOV false accepts (of 45) | 45 | | **29 vs 11** | report only |

## Decision

Rule 1 (CV lower bound above zero): **holds**. Rule 2 (dev paired mean at or
above zero): **holds**. **A is promoted to reference candidate.**

## Predictions

All four held. P1 (CV excludes zero), P2 (dev includes zero), P3 (archive gain
larger than CompMusic gain), P4 (annotated gain smaller than estimated).

## What it means, honestly

- The grouped CV gain is real at the group level, not an artifact of window
  count or fold luck. Roughly five points of it appear even on CompMusic rows,
  where only the window duration and count changed; the archive rows get about
  four more, which is the part attributable to matching the training tonic and
  DSP to the inference contract.
- The external gain is five recordings on a repeatedly inspected development
  set and its interval includes zero. Top-3 did not move at all. Do not quote
  102/139 as evidence the model is better in the wild.
- Per-class: the biggest gains are in Kāṁbhōji, Ābhōgi, Maṇirangu (+50 pp each,
  small support), and the biggest losses are Cakravākaṁ (−36 pp, n=11) and
  Kuntalavarāḷi (−20 pp, n=5). A per-class swing that size on n=11 is noise-adjacent.
- The candidate's confidence gate is **worse** than the comparator's on OOV
  queries (29 vs 11 false accepts of 45). Better discrimination did not buy
  safer confidence. Step 3 fits the abstain gate on this model, from scratch.

## Not shown

No field number (step 4). No fresh cohort. The dev set stays a dev set.
