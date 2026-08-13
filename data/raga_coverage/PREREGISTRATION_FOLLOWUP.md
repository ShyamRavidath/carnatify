# Raga coverage follow-ups — readings registered before any score exists

Written 2026-08-13, after `data/RAGA_COVERAGE_CURVE.md` landed (`0297e17`) and in
response to the verifier seat's two follow-up jobs. **Committed as its own
commit, before either scoring script exists and before a single fold of either
job is scored.** `data/raga_coverage/within_class_*.json` and
`data/raga_coverage/admission_*.json` do not exist at the time of writing.

`data/raga_coverage/PREREGISTRATION.md` is **not** modified — it is committed and
correct, and its frozen list (§2) governs both jobs below unchanged. This file
adds only what the two new jobs introduce.

---

## Job A — the within-class learning curve

### A.1 The question, and the confound it is designed to break

`data/RAGA_CEILING_EVALUATION.md` §"we need more audio per class" reports
`r(tracks, top-1) = 0.519`, `p = 5.8e-05`, `n = 54` across classes, cleanly
monotone in bins: 39.9% (10-14 tracks) → 41.5% (15-19) → 52.6% (20-24) → 68.6%
(25-30). **This is confounded and is not evidence that audio buys accuracy.** The
25-30 bin is exactly the set `scratch_archive_0711/dl_deficits30.py` topped up as
`PRIORITY_20` / `SECONDARY_20` / `TOPUP_30` — the popular, canonical,
well-recorded ragas — so track count and "easy to classify" are entangled through
popularity. The measured counterexamples are in the committed per-class table:
Saurāṣtraṁ 92.3% on 13 tracks, Nāṭakurinji 0.0% on 11.

The within-class test breaks the confound because every class is compared against
**itself**: popularity, recording quality and melodic distinctiveness are held
constant by construction, and only the number of tracks moves.

### A.2 Protocol

Tier held fixed at **`min_tracks >= 10`, 54 classes** — the class set is computed
on **full, uncapped** level-(a) track counts and does **not** move with the cap.
For a cap `c ∈ {10, 15, 20, 25, 30}`, every class is subsampled to at most `c`
tracks; classes with fewer than `c` keep all of theirs.

- **Subsampling is at the track level and is nested by construction.** For each
  class, its track ids are sorted and then permuted once by
  `np.random.default_rng(cap_seed)`; cap `c` takes the first `c` of that
  permutation. The `c = 10` subset is therefore a subset of the `c = 15` subset,
  and so on up the grid, so the arms are paired and the curve cannot be an
  artifact of which tracks were drawn.
- **`cap_seed ∈ {0, 1, 2}`** — three seeds, registered now, all three reported,
  spread reported as min-max across seeds at every cell. The subsample seed is a
  **new** knob and is declared here as separate from the frozen `random_state=42`
  of the forest and the splitter, which do not move. **Three seeds were chosen
  before any result; the reported curve is the mean over all three, and no seed
  may be dropped afterwards.**
- Level (c) only, source-disjoint. The level-(c) group vector is computed once
  over all rows (it is a function of provenance, not of the cap) and sliced to
  the surviving rows at each cell, so `n_groups` is a property of the cell and is
  reported per cell.
- **Folds are necessarily re-derived at each cell**, because the row set changes.
  Unlike Job B this cannot be avoided, and it is registered as a noise source.
- Everything in `PREREGISTRATION.md` §2 stays frozen. `scripts/raga_audit_levels.py`
  is **imported**, not copied: `collect`, `build`, `tdms` and `run_cv` are the
  same code objects that passed Gate 1.

### A.3 Cell inventory — derivable from set membership, computed before scoring

From the committed `data/raga_coverage/inventory.json`. Track counts per class
run 10 to 30, with 9 classes at exactly 30 and no class above it.

| cap `c` | tracks retained | classes truncated by the cap |
|---|---|---|
| 10 | 540 | 53 of 54 |
| 15 | 779 | 37 |
| 20 | 953 | 30 |
| 25 | 1071 | 17 |
| **30** | **1139** | **0** |

**Gate A — registered before the run.** No class in the corpus has more than 30
tracks, so the `c = 30` cell is the *whole* tier and must reproduce the committed
`min>=10` level-(c) result **exactly — 649/1139 = 57.0% top-1 and 812/1139 =
71.3% top-3 — for all three seeds**, since the subsample is a no-op there. If any
seed disagrees at `c = 30`, the subsampling code is wrong and nothing else from
Job A may be reported.

### A.4 The two read-outs

Both are registered; **(ii) is primary**, as the verifier seat specified.

- **(i) all 54 classes.** Contaminated by the 1 class (10 tracks) that is
  constant across the whole grid and the 37 classes that stop varying above their
  own track count; reported for completeness.
- **(ii) restricted to the 18 classes with ≥ 25 tracks** — which is exactly the
  `min>=25` tier. The classifier remains the **full 54-way problem** at every
  cell; only the *evaluation set* is restricted to those 18 classes' tracks.
  Changing the vocabulary as well would confound the cap with the tier and this
  job already has a tier curve. Registered explicitly so it cannot be swapped
  afterwards for whichever reading looks better.

Note the range restriction that remains inside (ii): only 17 of those 18 classes
have more than 25 tracks and only 9 have 30, so the `c = 25 → c = 30` step moves
less data than any earlier step. This is a property of the corpus, it is why the
last segment of the curve is the least well determined, and it is recorded now
rather than offered afterwards as an excuse.

### A.5 Per-class slopes

For each of the 18 classes with ≥ 25 tracks, per-class top-1 at every cap,
averaged over the three seeds, plus the `c=20 → c=30` and `c=25 → c=30`
differences. The question is whether the curve is still climbing at `c = 30` or
flat from `c = 20`.

### A.6 The decision this settles, fixed before the numbers exist

| outcome on read-out (ii), `c=10 → c=30` | means |
|---|---|
| **flat from `c=20` to `c=30`** (Δ ≤ 2 pp, and the `c=25→30` step ≤ 1 pp) | `r = 0.519` is confounding. **Do not raise the fetch target and do not spend hours on the 1,712 unfetched items for the purpose of deepening existing classes.** More *classes* is the whole lever, and the vocabulary/alias work is the job. |
| **still climbing at `c=30`** (`c=25→30` step ≥ 1.5 pp and the `c=20→30` step ≥ 3 pp) | The corpus is under a collection cap that is costing real accuracy. **The fetch is the best-value job on the board**, and the fetch target should go above 30 rather than to more classes first. |
| **climbing but decelerating** (total rise real, `c=25→30` between 1 and 1.5 pp) | Report the marginal pp-per-10-tracks at the top of the range and hand the trade to the verifier seat; the fetch is worth doing only for classes that are *not* already at 30. |

### A.7 Predictions

**The verifier seat's, transcribed verbatim, to be refuted:**

> *the within-class curve is much flatter than the cross-class correlation
> implies, roughly +6 to +12 pp from c=10 to c=30 on the 18-class restriction,
> and visibly flattening by c=25.*

Scored in two independent parts: (i) the total rise `c=10 → c=30` on read-out
(ii) lands in **6-12 pp**; (ii) the curve is **visibly flattening by `c = 25`**,
operationalised now as **the `c=25 → c=30` step being smaller than half the
`c=15 → c=20` step**.

**This seat's own, registered to be refuted:**

1. **Bigger than that, and still climbing.** Ten to thirty tracks is a desperately
   small training set for a 4,800-dimensional feature and a 54-way problem, and
   the whole cross-class correlation cannot be confound — the confound explains
   the *level* of the 25-30 bin, not the existence of a slope. Registered:
   **+13 to +20 pp** from `c=10` to `c=30` on read-out (ii), and the `c=25 → c=30`
   step **≥ 1.5 pp**, i.e. the curve is *not* flat at the top and the verifier's
   "visibly flattening by c=25" is wrong.
2. The all-54 read-out (i) will show a **smaller** total rise than (ii), because
   37 of its classes stop varying partway up the grid.
3. Per-class slopes will be **strongly heterogeneous** — at least 3 of the 18
   classes will have a non-positive `c=10 → c=30` slope. n is not destiny within
   a class either.
4. Seed spread will be **widest at `c = 10`** and will fall monotonically with
   `c`, reaching zero at `c = 30` by construction (Gate A).

---

## Job B — pricing per-class admission

### B.1 The question

`data/RAGA_COVERAGE_CURVE.md` §4 argues that a global `min_tracks` cannot
separate Saurāṣtraṁ (13 tracks, 92.3%) from Nāṭakurinji (11 tracks, 0.0%), and
that the lever is per-class admission. This job prices that claim: admit classes
by **measured per-class level-(c) top-1** rather than by track count, sweeping an
admission threshold `t ∈ {0, 0.10, 0.20, 0.30, 0.40}`, and compare expected hits
per 100 heard items against the best **global** `min_tracks` (which is
`min>=10`, 45.1, from the committed curve).

### B.2 The trap, named before it can be fallen into

**Selecting classes on the same folds you then score on is selection on noise and
manufactures a fake gain.** With 10-30 tracks per class, a class's measured top-1
has a standard error of roughly 9-15 pp, so thresholding on it and then scoring
on the same numbers keeps the classes that got lucky. The gain would be real in
the table and absent in the field.

### B.3 Protocol — nested, so the selection never sees the evaluation data

**Primary arm, honest:**

- The **outer** fold assignment is `StratifiedGroupKFold(5, shuffle=True,
  random_state=42)` over the **full 54-class tier** with the level-(c) group
  vector — i.e. exactly the fold assignment of the committed `min>=10` run. It is
  computed **once** and is **identical at every threshold**, so the thresholds are
  paired at the track level and a difference between two `t` values cannot be
  fold churn. (Job A cannot do this; Job B can, and does.)
- For each outer fold `k`: run an **inner** `StratifiedGroupKFold(5, shuffle=True,
  random_state=42)` over the *training* rows of fold `k` only, 54 classes, same
  forest, and take per-class top-1 from that inner CV. **Admit** the classes whose
  inner top-1 `>= t`.
- Then fit the frozen forest on outer-train rows restricted to the admitted
  classes, and score outer-test rows restricted to the admitted classes.
- Pool over the five outer folds. **The selection for fold `k` never sees fold
  `k`'s data**, at any stage, and the outer split is source-disjoint.

**Secondary arm, explicitly labelled as an optimistic bound:** identical in every
respect except that the admitted set is chosen from the **committed full-tier
per-class top-1** (`data/raga_coverage/curve.json`), i.e. from the same folds
that are then scored. It is reported **only** as the in-sample bound, beside the
honest number, so the size of the selection-on-noise effect is visible rather
than hidden. It is never quoted alone.

**Gate B — registered before the run.** At `t = 0` every class is admitted, so
both arms collapse to the plain 54-class tier and must return **exactly 649/1139
= 57.0% top-1 and 812/1139 = 71.3% top-3**, the committed `min>=10` level-(c)
numbers. If `t = 0` does not reproduce them, the outer fold assignment is not the
committed one and nothing else from Job B may be reported.

### B.4 Read-out

Per threshold `t`: classes admitted (mean and range over the five outer folds),
repertoire coverage of the admitted set, top-1 and top-3 on admitted-class
tracks, and **expected hits per 100 heard items**. Because the admitted set
differs per outer fold in the honest arm, the primary figure is registered now as
**the mean over the five outer folds of `coverage_k × top1_k`**, with the
per-fold spread reported; the pooled top-1 and the mean coverage are reported
beside it.

Comparators, both already committed and not re-derived: the best global tier is
`min>=10` at **45.1** expected hits, and the tier the product exports (`min>=20`)
is at **38.2**.

### B.5 Predictions

**This seat's, registered to be refuted:**

1. **The honest gain will be small.** Nested per-class admission beats the best
   global `min_tracks` by **0 to +3 expected hits per 100**, and it is possible
   that no threshold beats `t = 0` at all.
2. **The in-sample arm will look materially better than the honest arm** — by
   **≥ 2 expected hits per 100** at the threshold that maximises it — and that gap
   is the measurement of selection on noise, which is the real deliverable of Job
   B whichever way the honest number lands.
3. **The optimum, if there is one, is at a low threshold** (`t = 0.10` or
   `t = 0.20`), because coverage is lost fast: the four sub-10% classes alone are
   worth 3.9 pp of repertoire mass (measured in `RAGA_COVERAGE_CURVE.md` §4), and
   `t = 0.40` would drop 17 classes.
4. **Class admission will be unstable across the five outer folds** — the number
   of admitted classes at `t = 0.30` will vary by **≥ 4** between the most and
   least permissive fold. Instability *is* the selection-on-noise story, and if
   admission were stable the trap would not be a trap.

---

## Scope and rules, unchanged

Nothing under `models/` is written. `identify_clip.py` is untouched.
`data/raga_aliases.json` is read but never modified. No audio in `~/sung_tests`
is opened. Neither job graduates anything, neither says anything about the
lyrics-ASR, Qmax or CSI paths, and neither is a retraining of the product model.
Partial results are written to disk after every cell. `git add <path>` only.

**No tuning.** If the within-class curve is flat, the finding is that the fetch is
not worth doing; if per-class admission does not beat a global threshold, the
finding is that it does not. Both are useful results and both will be published
as they come out.
