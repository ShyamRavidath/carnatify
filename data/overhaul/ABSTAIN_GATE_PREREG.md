# Preregistration: an honest abstain gate for the reference candidate

Registered 2026-09-10 by the tech-lead seat. **Committed before the harness.**

## 0. Why the current gate is unsafe, mechanically

The bundle's gate is: softmax of ridge scores at a fitted temperature (0.0658),
then a threshold (0.216) chosen for 80% empirical precision on in-vocabulary
OOF windows. It was never shown an out-of-vocabulary example. Softmax also
discards absolute distance: a query far from every reference class still gets
a peaked posterior. Result on the dev set: 145/184 accepted, 95 correct
(65.5%), and 29 of 45 OOV queries accepted (64.4%).

## 1. Fixed inputs

- Model: `data/overhaul/context180_recovered_experiment/training/raga.joblib`,
  SHA256 `f594584402cb2ae35532612e673c194661706fcdfe4b69bbecc69b6d50316e2b`
  (the reference candidate per `CANDIDATE_VERDICT.md`).
- Training features/folds/manifest in the same directory (3,547 windows,
  1,243 tracks, 69 classes, 133 groups, fixed 5 folds).
- Fit recipe, copied from `scripts/raga_kernel_benchmark.py` arm
  `legacy_kernel_ridge`: `DistributionKernelRidge(alpha=.1, gamma=2, mode='tdms')`
  on the `legacy` (voiced) 4,800-dim features, sample weight 1 / windows-per-track
  rescaled to mean 1. Not tuned here.
- Dev queries: the 184 cached Saraga 180-second queries under
  `data/overhaul/cache/saraga_audio`, exactly the ones `evaluation180.json`
  scored (139 known, 45 OOV). Their per-query correctness under the reference
  model must reproduce 102/139 (Gate 2 below).
- Query clusters: the 17 primary-artist clusters from `annotated_corpus_v2.json`.

## 2. Protocol: leave-class-bin-out on top of the fixed group folds

The 69 classes are split into 5 bins by round-robin over classes sorted by
support (seed-free, deterministic), so every bin carries a similar mix of
large and small classes. For each fold f (5) and bin b (5):

- fit on training-fold windows whose class is not in bin b;
- score every validation-fold window. Windows whose class is in bin b are
  **simulated OOV** examples; the rest are **known** examples.

25 fits. Every validation window is scored five times, four times as known
under a model that could name it and once as OOV under a model that cannot.
Group disjointness is inherited from the fixed folds; class disjointness is by
construction. OOV prevalence in the pool is 1/5, close to the dev set's 45/184.

Per scored window, three candidate signals are recorded from the raw decision
vector `d` (kernel ridge scores, before any softmax):

- `max_score` = max d
- `margin` = top-1 minus top-2 of d
- `softmax_max` = max softmax(d / T) with T = the bundle's 0.0658 (the current gate's signal)

## 3. Selection, on the pool only

For each signal, sweep every unique value as a threshold and compute on the
pool: coverage (accepted / all), accepted precision (accepted and correct and
known / accepted), OOV false acceptance (accepted / OOV). The chosen operating
point is the **largest coverage** meeting precision >= 0.85 and OOV-FA <= 0.15.
The chosen signal is the one whose chosen point has the largest coverage.
Ties go to `max_score` (simplest, no temperature). If no point meets the bar
for any signal, the gate is closed and the product abstains on everything.

Optimism check: the same selection is repeated leaving one group fold out of
the pool at a time and applied to that fold (5-fold cross-fit over the pool).
The cross-fitted pool precision / OOV-FA / coverage is reported next to the
in-pool numbers. The difference is the selection optimism; it is reported,
not corrected for.

## 4. Gates

- **Gate 1.** Feature hash, manifest hash and fold file match the bundle.
- **Gate 2.** The reference model's top-1 on the 184 cached dev queries
  reproduces 102/139 known correct and the 8 mixed-recording tracks from
  `verdict.json`. Otherwise the dev cache is not what the handoff scored.

## 5. Dev evaluation, run exactly once

Apply the chosen signal and threshold to the 184 dev queries. Report:
accepted count, accepted precision (with 17-cluster bootstrap 95% interval,
seed 42, 5,000 draws), coverage, OOV false acceptance (of 45), and the same
three numbers restricted to the 176 single-raga queries. The dev set is not
touched during selection. **Bar:** precision >= 0.85 and OOV-FA <= 0.15 with
at least 20 accepted. Passing the bar means the gate may ship behind the
product; failing means it may not, and the coverage/precision curve is
published so the trade-off is visible.

## 6. Predictions

- **P1.** `max_score` or `margin` beats `softmax_max` on the pool: at matched
  OOV-FA <= 0.15 they reach higher coverage. Softmax normalises away distance.
- **P2.** At least one signal meets the pool bar with coverage >= 0.40.
- **P3.** On dev, precision clears 0.85 but OOV-FA lands between 0.15 and 0.30.
  Real OOV ragas are often close relatives of in-vocabulary ones (Ābhēri /
  Karṇāṭaka dēvagāndhāri and friends); held-out class bins are a mix of easy
  and hard, so the pool understates dev OOV difficulty. I expect the bar to
  fail on OOV-FA, narrowly.
- **P4.** Selection optimism (in-pool minus cross-fitted precision) is under
  3 pp; the pool is large (about 17,700 scored windows).

## 7. What a failure means

- Bar fails on dev: the gate stays closed in the product. Step 6 wiring then
  ships an always-abstain raga path with the ranked candidates visible as
  "candidates", never as an answer. That is the honest state.
- P1 fails: the current signal was fine and the problem was only that OOV was
  never in the selection pool.
- Gate 2 fails: stop and report; do not proceed to selection.

## 8. Not in scope

No refit of the reference model, no new features, no threshold tuned on dev,
no field concerts (step 4).
