# WORKHORSE BRIEF — the coverage/accuracy curve: what does widening the raga tier actually cost?

Written 2026-08-13 by the verifier seat, for a **workhorse (Opus 5)**.
Read-only with respect to production: **do not** write anything under `models/`,
**do not** touch `identify_clip.py`, **do not** retrain or overwrite
`models/raga_v3_*`.

## 0. Why this job exists

Every raga number this repo has ever published is measured on a tier chosen by
one frozen constant: `min_tracks`. The tier at `min_tracks >= 25` is 18 ragas.
The exported model is `min_tracks >= 20`, 32 ragas. Nothing else has ever been
measured.

That constant is not a modelling choice, it is a **coverage** choice, and the
coverage side of it has never been priced. Measured today from the cache
(`data/raga_v2_cache/{saraga_v3,archive_v3}/*.npz`, 88 distinct ragas,
1,297 tracks):

| `min_tracks` | classes | corpus tracks | % of scraped concert repertoire mass covered | % of the 81 labelled wild clips the model could even emit |
|---|---|---|---|---|
| 5  | 71 | 1,271 | 91.0% | 81% |
| 10 | 54 | 1,141 | 79.2% | 79% |
| 15 | 44 | 1,022 | 70.9% | 72% |
| 20 | 32 | 827 | 59.6% | 62% |
| 25 | 18 | 519 | 39.1% | 36% |
| 30 | 10 | 300 | 24.6% | 27% |

(Repertoire mass = the 3,009 of 3,698 items in `data/scraped_compositions.json`
that carry a canonical raga — a real prior over what gets performed. Wild =
`~/sung_tests` filename labels, folded through `data/raga_aliases.json`.)

**A companion that is 72% accurate on 36% of what it hears is worse than one
that is 60% accurate on 79%.** Nobody has ever measured the right-hand column
against the left. That is this job, and only this job.

## 1. The single question

> Holding everything else identical, what are source-disjoint top-1 and top-3
> at `min_tracks` ∈ {10, 15, 20, 25}?

## 2. Preregistration — commit this BEFORE the harness runs

Write `data/raga_coverage/PREREGISTRATION.md` and **commit it as its own commit
before you run a single fold**, as every audit in this series has done. It must
contain, written before the numbers exist:

1. The interpretation table below, filled in with what each outcome would mean.
2. The prediction of the verifier seat, so it can be refuted:
   *top-1 falls roughly log-linearly in class count and lands near **63-65%**
   at `min>=15` (44 classes) and **58-61%** at `min>=10` (54 classes); the
   `min>=10` tier will show a long tail of classes below 40% that carry most of
   the loss.* Record whether this was right.
3. A statement that **the tier is the only thing that moves.** Features, TDMS
   parameters (`taus 0.1/0.15/0.25`, `nb 40`, `sigma 1.0`, `alpha 0.75`),
   fusion weight, `RandomForestClassifier(800, 'sqrt', random_state=42)`,
   `StratifiedGroupKFold(5, shuffle=True, random_state=42)` and the level-(c)
   group construction are **frozen** and forbidden to tune. If any of them is
   touched, the run is void, not improved.

### Interpretation table — fill in the "means" column in the prereg, before scoring

| outcome at `min>=10` (54 classes) | means |
|---|---|
| top-1 >= 60% | widening is nearly free; the 18-class tier was leaving coverage on the floor for nothing. Retrain the product on the wide tier. |
| top-1 50-60% | a real but payable trade; decide on expected-hits-per-concert-item, not on top-1. |
| top-1 < 50% | the narrow tier is earning its keep; coverage must come from more audio per class, not from more classes. |

## 3. Method — reuse, do not rewrite

`scripts/raga_audit_levels.py` already is this harness. It collects the cache,
builds TDMS + histogram features, builds the four group vectors via
`scripts/raga_audit_protocol.py`, and scores level (c) = source-disjoint.
The tier is one module constant, `MIN`.

Do **not** write a new harness. Parameterise `MIN` (a `--min-tracks` argument
defaulting to the current value) and loop. Everything else stays byte-identical.

**Gate 1 — reproduction, non-negotiable.** With `MIN` at its current value the
script must still print `REPRODUCTION GATE: ... EXACT` (level (a) = 72.8/84.7)
and level (c) = **72.2% / 84.0%**, on the *same integer counts*, 374/518 and
435/518. If it does not, your parameterisation broke the harness. Stop and fix
that before running any other tier. Report the gate line verbatim.

**Groups.** `P.build_groups` derives level (c) over whatever rows it is given,
so the group vector must be **re-derived at each tier**, not inherited from the
518-track run. Report `n_groups` at every tier — if groups grow sublinearly with
tracks, say so, because that is what widens the CI.

## 4. What to report

`data/RAGA_COVERAGE_CURVE.md`, in the register of `data/RAGA_DURATION_CURVE.md`:

1. The reproduction gate line, verbatim.
2. **n first**: tracks, level-(c) groups, classes, folds, majority-class floor
   and class-prior floor at every tier. The floors move with the tier and a
   top-1 that falls while the floor falls faster is an *improvement*; report
   **top-1 minus the class-prior floor** alongside raw top-1, or the curve is
   uninterpretable.
3. The curve: top-1 and top-3 at each tier, with 95% CIs.
4. **Expected hits per 100 heard items** = `coverage x top-1`, using the
   repertoire-mass column of §0 as coverage. This is the product-relevant
   number and it is the one I expect to peak somewhere in the middle. Compute it
   for every tier. If it is flat, say it is flat.
5. Per-class top-1 at the widest tier, sorted. Name the classes that fall below
   the class-prior floor — those are classes that would be better dropped than
   kept, and they are the argument for a **per-class**, not global, threshold.
6. Whether the classes added between tiers hurt the classes that were already
   there. Paired at the track level: of the 518 tracks in the `min>=25` tier,
   how many flip correct→wrong when the tier widens to 54 classes? Report the
   flip count and a McNemar exact p. **This is the crux** — added classes that
   only cost their own accuracy are cheap; added classes that poison the
   existing 18 are not.

## 5. Rules that are not negotiable

- **Preregister and commit before scoring.** Two workhorses in this series died
  on session limits mid-run and were both recoverable because their partial
  results were on disk and their prereg was already committed. Write partial
  results to disk after every tier, not at the end.
- Deepti works in this repo from a separate terminal. **`git add <path>`,
  never `git add -A`.**
- Do not tune anything to make the curve look better. If widening is expensive,
  the finding is that widening is expensive; that is a useful result and it
  will be published as one.
- Append a dated entry to `AGENT_LOG.md` when you finish, including the failed
  predictions.
- `venv_train` (py3.11) has essentia and pytest; `venv` (py3.14) has sklearn and
  librosa. `raga_audit_levels.py` runs off the cached contours, so check which
  interpreter the existing audit used and use that one.

## 6. What this job is NOT

Not a retraining of the product model. Not a lyrics/ASR/Qmax job — those doors
are shut and nothing here reopens them. Not a change to `data/raga_aliases.json`
(a separate seat is auditing that). Not a new download. Nothing in
`~/sung_tests` is touched; the frozen wild set stays frozen.
