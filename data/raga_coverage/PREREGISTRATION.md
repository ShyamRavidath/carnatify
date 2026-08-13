# Raga coverage curve — readings registered before any score exists

Written 2026-08-13 against `WORKHORSE_RAGA_COVERAGE_BRIEF.md`, after
`scripts/raga_audit_levels.py --inventory-only` had assembled the feature
matrix, built the four group vectors and counted every tier, and **before a
single fold was scored**. No `RandomForestClassifier` has been fitted for this
job; `data/raga_coverage/levels_min*.json` does not exist and
`data/raga_coverage/inventory.json` and `coverage.json` contain nothing but set
membership and counts. This file is committed **as its own commit, ahead of any
result and ahead of the scoring run**, so the ordering is fixed in git history
rather than in file mtimes — the house standard set by
`data/raga_audit/PREREGISTRATION.md` and `data/raga_duration/PREREGISTRATION.md`.

The interpretation table **is** restated here, because the brief (§2.1) requires
its "means" column to be filled in before scoring. It is transcribed from
`WORKHORSE_RAGA_COVERAGE_BRIEF.md` §2 and is not to be modified afterwards.

---

## 1. The single question

Holding everything else identical, what are **source-disjoint (level (c)) top-1
and top-3 at `min_tracks` ∈ {10, 15, 20, 25}**?

`min_tracks` is not a modelling knob. It is a **coverage** choice: it decides how
much of what a listener actually hears the model is even allowed to name. Every
raga number this repo has published sits at one value of it — 25 for the
72.8/72.2 audit figures, 20 for the exported `models/raga_v3_*`. The other side
of that choice has never been priced.

## 2. What moves, and what is frozen

**Exactly one thing moves: the tier constant `MIN` in
`scripts/raga_audit_levels.py`,** now reachable as `--min-tracks`. It is applied
where it always was — on **level-(a) track counts**, `len(set(track_id))` per
raga — so the tier definition itself is unchanged and only its threshold moves.

Frozen, and **forbidden to tune**. If any of these is touched the run is void,
not improved:

- features: multi-tau TDMS, `taus = (0.1, 0.15, 0.25)`, `nb = 40`,
  `sigma = 1.0`, `alpha = 0.75`, one feature row per track, no histogram fusion;
- the corpus assembly and its drops (`Rāgamālika` excluded, `v.size < 500`
  excluded, `tonic <= 0` excluded), in `collect()`'s own order;
- `RandomForestClassifier(n_estimators=800, max_features='sqrt',
  random_state=42, n_jobs=-1)`;
- `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`;
- the read-out: mean posterior per track, `clf.classes_[argsort(-mean)]`,
  top-1 and top-3 counted on the track;
- the level-(c) group construction in `raga_audit_protocol.build_groups` —
  archive item / Saraga concert folder, union-find artist merge — including its
  known partiality on the archive side;
- the fusion weight `FUSION_W_HIST = 0.4` (irrelevant here: this is the
  TDMS-only primary arm, and the fusion arm is not run).

**No CV seed is re-drawn, no threshold is swept, no feature is added.** If the
curve is unflattering, the finding is that widening is expensive.

### Groups are re-derived at every tier, deliberately

`build_groups` is computed **once** over all 1,287 rows — it is a function of
provenance, not of the tier — but the *group vector handed to `cv.split`* is
sliced to the tier's rows at each tier, so the level-(c) group count is a
property of that tier and is reported per tier. It is **not** inherited from the
518-track run, which is what `data/RAGA_DURATION_CURVE.md` did (correctly, since
its tier never moved).

## 3. Gate 1 — reproduction, non-negotiable, registered before it is run

With `--min-tracks 25` (the default) the parameterised harness must still print

```
REPRODUCTION GATE: level (a) = 72.8% / 84.7% vs recorded 72.8% / 84.7%  ->  EXACT
```

on the **same integer counts** as `data/RAGA_CONTAMINATION_AUDIT.md` §1 and §3 —
**377/518 and 439/518 at level (a), 374/518 and 435/518 at level (c)** — and
`data/raga_audit/levels.json` must be reproduced with **no diff**. If it does
not, the parameterisation broke the harness and nothing else may be run until it
is fixed. Registered now: the gate is on integer counts, not on ±0.5 pp.

(The brief quotes the gate's level-(a) target as "72.8/84.7" and its level-(c)
counts as 374/518 and 435/518. Both are the audit's, and both are checked.)

## 4. n first — the inventory, derivable from set membership alone

From `scripts/raga_audit_levels.py --inventory-only --min-tracks 25,20,15,10`,
run before any fold. Corpus: **1,287 tracks with full melody, 87 ragas** after
the frozen drops. Provenance gaps: `unresolved_contour = 0`,
`unresolved_identifier = 0`; artist merges 90 at (c), 82 at (c′).

| tier | classes | tracks | (a) groups | (b) groups | **(c) groups** | (c′) groups | min (c) groups/raga | majority-class floor | **class-prior floor** |
|---|---|---|---|---|---|---|---|---|---|
| `min>=25` | 18 | 518 | 518 | 507 | **155** | 150 | 13 | 0.0579 | **0.0557** |
| `min>=20` | 32 | 826 | 826 | 781 | **185** | 175 | 9 | 0.0363 | **0.0319** |
| `min>=15` | 44 | 1020 | 1020 | 946 | **198** | 185 | 9 | 0.0294 | **0.0240** |
| `min>=10` | 54 | 1139 | 1139 | 1056 | **204** | 191 | 7 | 0.0263 | **0.0203** |

Two facts registered here because they are the ones that will make the curve
easy to misread:

1. **The floors move with the tier.** The class-prior floor falls 2.7× from
   `min>=25` (0.0557) to `min>=10` (0.0203). A top-1 that falls while the floor
   falls faster is an **improvement** in information terms. Both raw top-1 and
   **top-1 ÷ class-prior floor** and **top-1 − class-prior floor** will be
   reported, and the verdict will be stated against raw top-1 (the brief's
   interpretation table) while the ratio is reported alongside it.
2. **Groups grow sublinearly and this is severe.** Tracks grow 518 → 1,139
   (2.20×) while level-(c) source groups grow 155 → 204 (1.32×). The 621 tracks
   added between `min>=25` and `min>=10` bring only **49** new independent
   sources. Registered prediction: **the confidence intervals will barely narrow
   as the tier widens, and may widen**, because n in the statistical sense is the
   group count, not the track count. Tracks per group rise 3.3 → 5.6.
3. No raga has fewer than `n_splits = 5` level-(c) groups at any tier (minimum 7
   at `min>=10`), so **no class is dropped at any tier** and the 5-fold split is
   valid throughout. Registered before scoring precisely so that a class dropped
   later cannot be explained away afterwards.

## 5. Coverage — the other axis, computed before any score

`scripts/raga_coverage_mass.py`, read-only over `data/scraped_compositions.json`
(3,009 of 3,698 items carry a `raga_canonical`; 100 distinct ragas) and over the
filename labels of `~/sung_tests` (directory listing only, no audio opened).
Matching is on the harness's own NFKD-folded alphanumeric form.

| tier | classes | repertoire items covered | **repertoire coverage** | wild clips covered (of 103 labelled) | wild coverage |
|---|---|---|---|---|---|
| `min>=25` | 18 | 1176 / 3009 | **39.1%** | 29 | 28.2% |
| `min>=20` | 32 | 1794 / 3009 | **59.6%** | 50 | 48.5% |
| `min>=15` | 44 | 2134 / 3009 | **70.9%** | 58 | 56.3% |
| `min>=10` | 54 | 2383 / 3009 | **79.2%** | 64 | 62.1% |

The repertoire column reproduces the brief's §0 table exactly (39.1 / 59.6 /
70.9 / 79.2), independently recomputed from the tier's own class lists. The wild
column does **not**: the brief quotes 36 / 62 / 72 / 79% over a denominator of
81 labelled clips, and this recomputation finds 103 clips carrying a filename
label and reports over that. The wild column is **secondary and the labels are
unaudited** (`HANDOFF_SESSION_0731.md` §6.1 has two of the 29 in-tier labels
already under musical suspicion); the discrepancy is recorded here, before any
score, rather than reconciled afterwards. **Expected hits per 100 heard items is
computed on the repertoire column**, as the brief specifies.

## 6. The interpretation table, "means" column filled in before scoring

Fixed on **level (c), top-1, at `min>=10` (54 classes)**. Transcribed from the
brief; not to be modified.

| outcome at `min>=10` (54 classes) | means |
|---|---|
| **top-1 ≥ 60%** | Widening is nearly free; the 18-class tier was leaving coverage on the floor for nothing. **Retrain the product on the wide tier.** The recommendation is unconditional at this level: 79.2% coverage at ≥60% accuracy dominates 39.1% coverage at 72.2% on expected hits (47.5 vs 28.2 per 100 items) by so much that no plausible weighting of a wrong answer against a missing one reverses it. |
| **top-1 50-60%** | A real but payable trade. **Decide on expected hits per concert item, not on top-1.** In this band `min>=10` yields 39.6-47.5 expected hits per 100 items against 28.2 for `min>=25`, so the wide tier still wins on hits — but a wrong raga name shown confidently is a different failure from silence, and the decision then belongs with an abstain gate (`HANDOFF_SESSION_0731.md` §6.3), not with this table. Report the peak of the expected-hits column and hand the choice to the verifier seat. |
| **top-1 < 50%** | **The narrow tier is earning its keep.** Coverage must come from more audio per class, not from more classes; the added classes are being bought with accuracy the product cannot spare. The corollary is that the way to cover more repertoire is to *download more recordings of the ragas below threshold* until they clear it, which is a data-acquisition programme, not a threshold change. |

## 7. Predictions, written down so they can be refuted

### 7.1 The verifier seat's prediction (brief §2.2), transcribed verbatim

> *top-1 falls roughly log-linearly in class count and lands near **63-65%** at
> `min>=15` (44 classes) and **58-61%** at `min>=10` (54 classes); the `min>=10`
> tier will show a long tail of classes below 40% that carry most of the loss.*

This will be scored against the measurement in three parts, each independently
right or wrong: (i) the `min>=15` band 63-65%, (ii) the `min>=10` band 58-61%,
(iii) the existence of a long tail below 40% at `min>=10` carrying most of the
loss. "Carrying most of the loss" is operationalised **now, before scoring**, as:
the classes below 40% top-1 at `min>=10` account for **more than half** of the
total top-1 errors at that tier.

### 7.2 This seat's own registered expectations

Written before any fold, so they can be refuted too:

1. **The CIs will not narrow much.** From §4.3: 155 → 204 source groups. The
   95% cluster-bootstrap interval at `min>=10` will be **no more than ~2 pp
   narrower in half-width** than the one at `min>=25` (which the duration audit
   measured as 66.4-78.1%, half-width ≈ 5.9 pp).
2. **The McNemar flip test will show a real but small poisoning effect.** The 518
   tracks of the `min>=25` tier are being asked to survive 36 additional
   competing classes, several of which are close melodic relatives of incumbents
   (`Śuddadhanyāsi` vs `Hindōḷaṁ`, `Ābhōgi` vs `Śrīranjani`, `Kēdāragauḷa` vs
   `Harikāmbhōji`, `Bilahari` vs `Śankarābharaṇaṁ`, `Nīlāṁbari`/`Sāma` vs
   `Kāṁbhōji`). Expectation: **more correct→wrong flips than wrong→correct**,
   with a two-sided exact p **below 0.05**, and a net loss on those 518 tracks of
   **5-12 pp**. If the net loss is under 2 pp the added classes are cheap; if it
   is over 15 pp the narrow tier is protecting the incumbents materially.
3. **Expected hits per 100 items will not peak at `min>=25`.** Even at a top-1 of
   50% the `min>=10` tier yields 39.6 hits per 100 against 28.2 for `min>=25`.
   For `min>=25` to win, `min>=10` top-1 would have to fall below **35.6%**,
   which is below the level of every published figure on this path. Registered
   expectation: **the expected-hits column is monotonically increasing in
   coverage over the whole registered grid**, i.e. it peaks at `min>=10` and does
   *not* peak in the middle — which is the opposite of what the brief expects
   ("the one I expect to peak somewhere in the middle"). One of us is wrong and
   the measurement will say which.
4. **Vasanta stays the weak incumbent.** 35.7% at `min>=25` (audit §5), 36.9% at
   60 s (duration curve §4). It will remain below 45% at every wider tier.

## 8. Registered analysis choices — fixed now, not after seeing the numbers

- **Primary metric:** level-(c) top-1 on the track, exactly as the audit defines
  it. Top-3 reported alongside and is non-gating.
- **Uncertainty:** cluster bootstrap over the **level-(c) source groups** of that
  tier, resampling groups with replacement, **2,000 replicates**,
  `np.random.default_rng(42)`, percentile interval. This is the method
  `data/RAGA_DURATION_CURVE.md` §1 used, chosen for the same reason: the tracks
  are not independent, they come in 155-204 source clusters and the folds are
  disjoint on those clusters, so a binomial interval on the track count is far
  too narrow. A Wilson interval on the raw track counts is reported **beside**
  it, explicitly labelled as the too-narrow comparator.
- **Expected hits per 100 heard items** = `repertoire coverage × level-(c)
  top-1`, per tier, using §5's repertoire column. Reported for every tier; if it
  is flat across the grid, it will be reported as flat.
- **The paired flip test (brief §4.6):** restricted to the **518 tracks of the
  `min>=25` tier**, comparing level-(c) top-1 correctness at `min>=25` against
  level-(c) top-1 correctness at `min>=10`. Counts `b` (correct at 25, wrong at
  10) and `c` (wrong at 25, correct at 10); **McNemar exact**, two-sided binomial
  on `b` of `b + c` at p = 0.5 (`scipy.stats.binomtest`). It is registered here,
  before scoring, that this pairing is **exact at the track level but not at the
  fold level**: `StratifiedGroupKFold` sees a different row set at each tier, so
  a track's fold assignment and therefore its training partner set differ between
  the two tiers. Part of any flip is therefore re-randomised fold membership
  rather than added classes. The same caveat applies in the other direction and
  cannot be removed without freezing folds, which would change the frozen
  harness. It will be stated in the write-up and the p-value will be read as an
  upper bound on the evidence, not as a clean causal test. The intermediate tiers
  (20, 15) are reported on the same 518 tracks as a monotonicity check.
- **Per-class table:** level-(c) top-1 per class at `min>=10`, sorted, with each
  class's track count and level-(c) group count. Classes falling **below the
  class-prior floor** of that tier (0.0203) are named as candidates for dropping,
  per brief §4.5.
- **Levels scored:** (a) and (c) at every tier. (b) and (c′) are scored at
  `min>=25` only, as part of the full-default reproduction run; scoring them at
  every tier costs compute and answers no question in the brief. This is a
  scoping decision registered before the run, not a result-dependent one.

## 9. Abort and void conditions

- Gate 1 fails → stop, fix the parameterisation, re-run. Nothing else is
  reported until it passes.
- Any raga drops below 5 level-(c) groups at some tier → report it explicitly and
  do not silently let `StratifiedGroupKFold` degrade. (§4.3 says this will not
  happen; if it does, the inventory was wrong.)
- Any change to a frozen constant in §2 → the run is void and is re-run from
  scratch, not patched.

## 10. Scope — what this job will not establish

- It measures the **archive/Saraga corpus against itself**, full-recording, at
  four tier widths. It says nothing about wild audio, short clips or the domain
  gap; those are `data/RAGA_WILD_MEASUREMENT.md`, `data/RAGA_DURATION_CURVE.md`
  and `data/RAGA_DOMAIN_DECOMPOSITION.md`.
- It says nothing about the lyrics-ASR, Qmax or CSI composition paths in either
  direction. Those doors are shut and nothing here reopens them.
- It graduates nothing. Nothing under `models/` is written, `identify_clip.py` is
  untouched, `data/raga_aliases.json` is read but never modified, and
  `~/sung_tests` audio is never opened.
- The level-(c) artist merge is **partial** on the archive side, inherited
  unchanged from the audit, so source-disjointness here remains an upper bound on
  the truth and never a lower one — at every tier equally.
