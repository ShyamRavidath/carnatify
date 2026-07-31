# Raga contamination audit — readings registered before any score exists

Written 2026-07-30, after `scripts/raga_audit_protocol.py` had assembled the
feature matrix and the four group vectors, and **before a single fold was
scored**. `scripts/raga_audit_score.py` exists on disk at the time of writing
but has never been executed; no `RandomForestClassifier` has been fitted for
this audit, and `data/raga_audit/results.json` does not exist. Everything below
is derivable from set membership alone. This file is committed **as its own
commit, ahead of any result**, so the ordering is fixed in git history rather
than in file mtimes — an explicit correction to how the Qmax audit was run.

The interpretation table is not restated here. It is fixed in
`WORKHORSE_RAGA_AUDIT_BRIEF.md` and is not to be modified.

## What is being audited

`HANDOFF_CLIP_ID.md:43` and `train_raga_v3_tdms.py:14` record **72.8% top-1 /
84.7% top-3 on 18 ragas at the `min_tracks >= 25` tier**, described throughout
the repo as "grouped CV, leak-free". The harness that produced it was never
committed; `train_raga_v3_tdms.py` only fits and exports, and the number
survives as a docstring line plus a `cv_note` dated 2026-07-08. The *features*
are reproducible, so the harness is rebuilt from the committed constants —
`TAUS`, `NB`, `sigma 1.0`, `alpha 0.75`, `FUSION_W_HIST = 0.4`,
`RandomForestClassifier(n_estimators=800, max_features='sqrt',
random_state=42)`, `min_tracks = 25`, `StratifiedGroupKFold(n_splits=5,
shuffle=True, random_state=42)`, `Rāgamālika` dropped — by *importing*
`tdms_multi` and `canon` from the training script rather than re-implementing
them.

## The four levels, as the brief fixed them

One feature matrix, built once. The levels differ **only** in the `groups`
vector handed to `StratifiedGroupKFold`. Not the tier, not the fusion weight,
not the forest, not the seed.

- **(a) as-originally-run.** `groups = track_id` — one value per npz file, which
  is exactly what the 2026-07 run grouped on.
- **(b) recording-disjoint.** Archive tracks group on `contour_sha1` from
  `data/qmax_audit/provenance.json`, collapsing byte-identical melodia contours
  into one group; Saraga keeps `track_id`. Justification, established in the
  Qmax prereg before any of this existed: a near-duplicate sweep over all 128
  positive pairs found **zero** pairs near-identical without being
  byte-identical, so on this corpus the exact test is the complete test.
- **(c) source-disjoint.** Archive tracks group on `archive_identifier` (the
  concert upload); Saraga tracks group on their concert folder (Saraga 1.5
  Carnatic has clean per-track concert and album-artist metadata across 27
  folders). Any two such groups sharing a known artist are then merged, in a
  single union-find over both corpora, so an artist appearing in both an archive
  upload and a Saraga concert produces one group. **This is the level that
  matters.**
- **(c′) identifier-family disjoint — registered sensitivity, non-gating.**
  (c) with archive identifiers first collapsed into families when their folded
  forms score `rapidfuzz.fuzz.ratio >= 85`
  (`scripts/raga_audit_families.py`; 292 identifiers → 270 families, 47 pairs,
  including the `78RPM-Chittor-V-Nagaiah` / `78RPM-ChittoorVNagaiah` case the
  Qmax audit found). Declared now, before any score, precisely so it cannot be
  introduced later as the reading that rescues a result. If (c) and (c′)
  disagree materially, both are reported and **the lower is treated as honest**.

## Registered readings

1. **The tier is frozen at `min_tracks >= 25` computed on level-(a) track
   counts, and is never re-tuned.** Re-tuning `min_tracks` to keep 18 ragas
   alive under coarser grouping is the single most available way to launder this
   number and is forbidden. The tier is 18 ragas / 518 tracks / 1,554 rows, and
   it is the same 18 ragas at every level.
2. **A raga with fewer than `n_splits = 5` distinct groups at a level is dropped
   at that level** and reported by name, because it cannot be tested in every
   fold. On the group counts already computed (below) **no raga drops at any
   level**, so this rule turns out not to bite; it is registered anyway because
   it was written before the counts were consulted for the write-up and because
   dropping ragas would shrink the label set and inflate the level's top-1.
3. **n before the percentage at every level** — tracks, groups, ragas, folds
   actually used. If a level left too few groups per raga for a 5-fold split,
   the n would be the finding and would be the headline.
4. **Two chance floors at every level, recomputed per level**: the
   **majority-class rate** and the **class-prior expectation** `Σ p_i²` over the
   surviving label distribution. Item-level grouping can change that
   distribution, so neither is carried over from level (a).
5. **Top-1 and top-3 at every level.** 84.7% top-3 is quoted as often as the
   top-1 and a raga-first product would plausibly ship on top-3.
6. **Secondary, non-gating: per-raga top-1 at level (c).** Reported so a
   raga-first product knows which ragas carry, but it does not drive the verdict.

## The two read-outs, declared in advance

The original harness was not committed, so the *unit* it scored is genuinely
unrecorded. Each track contributes exactly three rows to the matrix — `orig`,
`pitch_shift`, `noise` (`d['kinds']`) — sharing one TDMS vector and differing in
the 480-dim histogram. Two readings are therefore natural, and both are
registered here rather than chosen afterwards:

- **row-level** — one prediction per augmented row, 1,554 rows, which is the
  unit `train_raga_v3_tdms.py` fits on;
- **track-level** — the three rows' fused posteriors averaged, one prediction
  per track, 518 tracks.

Grouped CV keeps all three rows of a track on the same side of every split, so
neither read-out leaks; they differ only in aggregation. **Both are computed and
both are reported at every level, whatever they show.** The gate is attempted
under both; whichever reproduces level (a) is frozen as the registered headline
for levels (b), (c) and (c′), and the other continues to be reported alongside
it. If both reproduce, **row-level is the headline**. If neither reproduces, the
audit stops at the gate.

This is a declared consequence of a missing harness, not a second attempt at a
result: the choice is fixed by level (a) alone, before any (b) or (c) number is
looked at, and no other quantity may be used to pick between them.

## The reproduction gate

**Level (a) must land within ±2pp of 72.8% top-1 and 84.7% top-3 on 18 ragas.**
If it does not, the audit stops, the rebuild is reported as a *declared
reconstruction* — the way the Qmax internal arm was — and the number is stated
plainly as unreproducible from this repository. Levels (b), (c) and (c′) are not
scored against a baseline that does not reproduce, because a delta measured off
a wrong baseline is worse than no delta.

One fact already supports the rebuild and is recorded here before any score:
the assembly yields **1,287 tracks**, matching `train_raga_v3_tdms.py:13`
("grouped 5-fold, track-level, 2026-07-08, 1287 tracks") exactly, with 8
`Rāgamālika` npz dropped and 2 archive npz having no melodia contour on disk.

## n, from set membership only — computed before any score

Provenance resolved for **1,232 of 1,232** contours (reused from
`data/qmax_audit/provenance.json`, not re-derived): 0 tracks fell back to
`track_id` at level (b) and 0 at level (c).

| level | tracks | groups | rows | ragas | majority class | class-prior Σp² |
|---|---|---|---|---|---|---|
| (a) track_id | 518 | 518 | 1554 | 18 | 0.0579 | 0.0557 |
| (b) contour sha1 | 518 | 507 | 1554 | 18 | 0.0579 | 0.0557 |
| (c) item / concert + artist | 518 | **155** | 1554 | 18 | 0.0579 | 0.0557 |
| (c′) identifier family | 518 | **150** | 1554 | 18 | 0.0579 | 0.0557 |

Per-raga group counts at level (c) run 13 to 24 (median 21), all comfortably
above the 5 folds, so **the corpus can answer the question** and the "too few
groups" row of the interpretation table is already excluded on set membership
alone. The floors are identical across levels because no raga drops, so the
label distribution is unchanged.

The collapse from 518 groups to 155 is the whole exposure. **430 of the 518
tracks (83.0%) share a source group with at least one other track in the tier**,
so at level (a) `StratifiedGroupKFold` was free to put those on opposite sides of
a split. Per raga, the mean number of distinct groups falls from 28.8 at (a) to
20.0 at (c).

## What this audit cannot do

- It cannot recover the original harness. Level (a) is a *rebuild* that agrees
  with the committed constants and the committed track count; if it reproduces
  the number that is evidence the rebuild is faithful, not proof.
- It says nothing about wild 30-60s clips. This is full-track raga on archive
  and Saraga audio. `HANDOFF_CLIP_ID.md` §5 already records that clip-domain
  raga posteriors collapse, and this audit does not revisit that.
- It graduates nothing. `~/sung_tests --cache-v2` remains the only scoreboard.
- Artist coverage is partial on the archive side, exactly as the Qmax audit
  found; level (c)'s artist merge can only act where an artist is recorded, so
  (c) is an **upper bound** on true source-disjointness, never a lower one.

---

# Addendum, 2026-07-30, after the first scoring pass — the harness was found

**This section is appended, not a rewrite.** Everything above stands exactly as
it was committed in `ec3578d`, before any fold was scored, and the numbers it
registered are reported in full in `data/RAGA_CONTAMINATION_AUDIT.md` whatever
this addendum says. This addendum is committed **before** the corrected levels
(b), (c) and (c′) are scored, so the same ordering guarantee covers them.

## What was found

The brief's premise — "the CV harness that produced 72.8 / 84.7 was never
committed" — is **false**. `git log --all -S"72.8" -- '*.py'` misses it because
the harness never contained the number. It is
**`scratch_archive_0711/raga_final_eval.py`**, committed in `c1fca59` on
2026-07-11. Run verbatim, unmodified, in `venv` today it prints:

```
1287 tracks with full melody
final multi-tau   min>=10 ragas=54 top1=61.6% top3=75.2%
final multi-tau   min>=15 ragas=44 top1=63.4% top3=76.7%
final multi-tau   min>=20 ragas=32 top1=67.6% top3=79.4%
final multi-tau   min>=25 ragas=18 top1=72.8% top3=84.7%
```

Both recorded tiers, both metrics, **exact**. The number is fully reproducible
from this repository and the environment did not drift.

## Why this changes the primary arm

`raga_final_eval.py` is **multi-tau TDMS alone**: no histogram, no fusion, and
**one feature row per track** rather than the three augmented rows
(`orig` / `pitch_shift` / `noise`) that `train_raga_v3_tdms.py` fits on. The
protocol registered above — fusion at `w_hist = 0.4` over three augmented rows —
is the *exported v3 model's* protocol, and it is a different measurement. Run at
the same tier by its own archived harness
(`scratch_archive_0711/raga_final_push.py`, `MIN` 20→25, `w=0.4`) it scores
**75.7% top-1 / 84.2% top-3**, which my rebuild reproduces to the printed
precision — so the rebuild was faithful; it was faithful to the wrong number.

The `cv_note` string in `train_raga_v3_tdms.py` and `models/raga_v3_meta.json`
therefore attaches a **TDMS-only** score to the **fused** exported model. That is
a labelling error in the repo, and it is a finding of this audit.

## The corrected arms, registered now, before either is scored at (b)/(c)

- **Primary arm — `raga_final_eval.py`'s protocol**, the one that actually
  produced 72.8 / 84.7. `scripts/raga_audit_levels.py` reproduces it and swaps
  **only** the `groups=` argument to `cv.split` for the four level vectors
  already registered above. Nothing else changes: same tier frozen at
  `min_tracks >= 25` on level-(a) track counts, same `RandomForestClassifier(800,
  'sqrt', random_state=42)`, same `StratifiedGroupKFold(5, shuffle=True,
  random_state=42)`, same read-out. **Its level (a) must print exactly 72.8 /
  84.7 or the rebuild is rejected.**
- **Secondary arm — the fusion protocol registered above**, already scored, kept
  and reported in full at all four levels. It is the exported model, so its
  contamination answer is of independent interest, and it is an independent
  replication of the primary arm's delta on a different feature set and a
  different read-out.

Both arms are reported at every level whatever they show. No level is re-run to
improve a number; the primary arm's level (a) is a pass/fail check against a
figure that is already fixed in the repo, not a quantity to be tuned.
