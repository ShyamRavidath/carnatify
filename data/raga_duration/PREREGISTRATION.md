# Raga duration curve — readings registered before any score exists

Written 2026-07-31 against `WORKHORSE_RAGA_DURATION_BRIEF.md`, after
`scripts/raga_duration_protocol.py` had assembled the corpus, frozen the tier,
rebuilt the inherited level-(c) group vector and drawn the window offsets, and
**before a single fold was scored**. `scripts/raga_duration_windows.py` (feature
extraction) and `scripts/raga_duration_score.py` exist on disk at the time of
writing; no `RandomForestClassifier` has been fitted for this job and
`data/raga_duration/results.json` does not exist. Everything below is derivable
from set membership and contour lengths alone. This file is committed **as its
own commit, ahead of any result**, so the ordering is fixed in git history
rather than in file mtimes — the house standard set by
`data/raga_audit/PREREGISTRATION.md`.

The interpretation table is not restated here. It is fixed in
`WORKHORSE_RAGA_DURATION_BRIEF.md` §"Interpretation" and is not to be modified.

## The graveyard entry this job stands next to

`HANDOFF_SESSION_0730.md:79` and `handoff.md:283` record **"Duration as a lever.
Ruled out, not merely undetected."** That entry is real and binding. It was
measured on the **lyrics-ASR composition-recall** path: longer windows into
Whisper, top-5 5.1% @30s → 1.7% @300s, curve peaking at 90s. This job measures
the **melodic-contour → TDMS → random-forest raga** channel, which shares no
code, no feature and no model with it, and asks the **opposite** question — not
"does more audio help" but "how little audio is enough". The distinction is
accepted here explicitly, and **no result from this job may be quoted as
evidence about the lyrics-ASR path in either direction.**

A second, closer prior is also on the record and is registered here before any
score so it cannot be produced afterwards as a prediction: `HANDOFF_CLIP_ID.md`
§5 says *"TDMS on FULL-track melody was the breakthrough (+13pt) — 65s segments
are too short for it to shine."* That sentence is an unquantified impression
from the 2026-07 modelling; this job is the measurement of it.

## What is inherited, frozen, and not re-derived

From `data/RAGA_CONTAMINATION_AUDIT.md` and `scripts/raga_audit_protocol.py`:

- **Corpus assembly** — `raga_audit_levels.collect()`'s order and drops
  (`Rāgamālika` excluded, archive tracks need a melodia contour on disk, tracks
  need `v.size >= 500` and `tonic > 0`). 1,287 tracks with full melody, matching
  `train_raga_v3_tdms.py:13`.
- **The tier** — `min_tracks >= 25` on level-(a) track counts. **18 ragas, 518
  tracks.** Frozen; never re-tuned at any duration. Re-tuning the tier to keep
  18 ragas alive at 30 s would be the available way to launder this curve and is
  forbidden.
- **The level-(c) source-disjoint group vector** — archive item / Saraga concert
  folder, artist-merged in one union-find, from
  `raga_audit_protocol.build_groups()`. Over the tier it yields **155 groups**
  (`unresolved_contour 0, unresolved_identifier 0, artist_merges_c 90`),
  identical to the audit. **Every number in this job is source-disjoint. No
  level-(a) figure is computed or reported.**
- **The harness** — `tdms()` verbatim (`NB = 40`, `TAUS = 0.1/0.15/0.25`,
  `sigma 1.0`, `alpha 0.75`), `RandomForestClassifier(n_estimators=800,
  max_features='sqrt', random_state=42, n_jobs=-1)`,
  `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`.

## The unit is the window, not the track

One window is one user session, so the product-relevant unit is the window.
Predictions are scored **per window with no aggregation to the track** — this is
the one deliberate departure from the audit's read-out and it is registered
here, before any score, because averaging three windows' posteriors back to a
track would measure a listening session nobody has.

## Windows

`K = 3` random-offset windows per track per duration, plus one from-the-start
window as a registered secondary. Offset **fractions** `u ~ U(0,1)` are drawn
once per track (`np.random.default_rng(42)`, tracks in sorted-stem order) and
reused at **every duration and in both conditions**, so the arms are paired: the
start frame is `round(u * (n_raw - need))`.

Random offset rather than from-the-start because these archive files are already
segmented concert items and a listener arrives mid-item.

**Tracks shorter than the duration contribute their whole length once** (window
kind `short`) and are counted and reported separately at every duration. From
set membership alone, before any score:

| duration | tier tracks | shorter than *d* | windows in the primary read-out | mean real window |
|---|---|---|---|---|
| 30 s | 518 | 0 | 1554 | 30.0 s |
| 60 s | 518 | 0 | 1554 | 60.0 s |
| 120 s | 518 | 8 (1.5%) | 1538 | 119.5 s |
| 300 s | 518 | **182 (35.1%)** | 1190 | 265.9 s |
| 600 s | 518 | **314 (60.6%)** | 926 | 414.6 s |
| full | 518 | — | 518 | 785 s (median 425 s) |

Tier track durations run 61 s / p25 225 s / median 425 s / p75 1080 s / max
8203 s, 113.0 h in total. **The 300 s and 600 s cells are therefore already
known, before any score, not to be measuring 300 s and 600 s** — they measure
266 s and 415 s of mean real audio, and at 600 s a majority of the corpus is
contributing one whole short track rather than three windows. This is registered
now so the 600 s cell cannot later be read as a clean point on the curve. The
30 s / 60 s / 120 s cells are clean.

## The voiced guard, chosen before scoring

**`min_voiced = 500` voiced frames per window** — the frozen harness's own track
guard (`v.size < 500`), reused unchanged at the window level rather than
invented for this job. At the 2.902 ms hop that is 1.45 s of voiced audio. A
window failing it is **discarded, not scored**, and is reported in its cell
alongside the scored n; it never enters a denominator silently. A window whose
`tdms()` returns `None` (`b.size <= tau`, or an all-zero surface) is discarded
under reason `tdms_none` and reported the same way.

Registered expectation, so the result is checkable against it: full-track
voicing density over the tier is mean 0.678, median 0.676, **min 0.516**, so a
30 s window holds ~7,000 voiced frames on average and the guard is expected to
bite rarely. **If the 30 s discard rate is nevertheless high, that is a finding
about what a short clip contains and it is reported as the headline of that
cell, not as a footnote.**

## Trap 1 — truncate the raw contour, then filter

The window is a slice of the **raw** contour on the time axis
(`f[start:stop]` in original-hop frames); the voiced filter
`(f > 0) & isfinite(f)` is applied to the slice **afterwards**. Each window has
a known real duration and an unknown voiced-frame count, and the voiced-frame
distribution per duration is reported. "The first N voiced frames" would be a
window of unknown real duration and is not used anywhere.

## Trap 2 — recorded, not repaired

The frozen harness computes `tau = round(tau_s / hop)` in frames of the original
hop and applies it to the **compacted voiced array**. The nominal 0.1 / 0.15 /
0.25 s delays are therefore only nominal: the true delay is approximately
`tau_s / density`, so it **scales with voicing density and changes with window
length**. This is pre-existing and it is a real confound for a duration sweep.

**It is not repaired** — repairing it would change the frozen harness and break
comparability with `data/RAGA_CONTAMINATION_AUDIT.md`. Instead, mean and spread
of per-window voicing density are reported at every duration, together with the
implied effective delay for each nominal tau. If density moves materially across
durations, the verdict says so and the curve is read with that caveat.

## The two conditions

| condition | train on | test on |
|---|---|---|
| **matched** | windows of duration *d* from the training groups | windows of duration *d* from the held-out groups |
| **mismatched** | full tracks from the training groups | windows of duration *d* from the held-out groups |

The **fold assignment is computed once**, at the track level, by
`StratifiedGroupKFold(5, shuffle=True, random_state=42).split(X_full, y,
groups=g_c)` over the 518 tier tracks in the audit's own row order, and every
cell of both arms reuses it. The two arms therefore have **identical test window
sets at every duration** and are exactly paired; the mismatched arm's model for
a fold is literally the full-track model of that fold.

The matched arm trains on `rand` + `short` windows only. The `start` window is
**test-only** and never trains.

## Registered readings

1. **n before the percentage in every cell**: windows scored, windows discarded
   by `min_voiced`, windows discarded by `tdms_none`, tracks shorter than *d*,
   and the number of distinct level-(c) groups and folds actually used.
2. **Top-1 and top-3, per window, at every duration, in both conditions.**
   Top-3 is reported because the audit reported it and a raga-first product
   would plausibly ship on top-3.
3. **Two chance floors recomputed per cell** — majority-class rate and the
   class-prior expectation `Σ p_i²` over that cell's *window* label
   distribution. The window distribution is not the track distribution once
   short tracks contribute one window instead of four, so neither is carried
   over from the audit.
4. **A raga with fewer than `n_splits = 5` distinct level-(c) groups is dropped
   and named.** On the inherited counts (13-24 groups per raga) no raga drops,
   so this rule is not expected to bite; it is registered because dropping ragas
   would shrink the label set and inflate top-1.
5. **Secondary, non-gating:** (a) the from-the-start window at every duration,
   both conditions, reported over the non-short tracks only; (b) per-raga top-1
   at 60 s matched; (c) the per-window voiced-frame distribution per duration.
   None of these drives the verdict.

## The reproduction gate

The **full-track matched cell is the audit's level (c) re-run through this
pipeline**: same tracks, same order, same folds, same features, same forest, one
window per track. **It must land within ±0.5 pp of 374/518 = 72.2 % top-1 and
435/518 = 84.0 % top-3.** If it does not, the feature or fold path here differs
from the audit's, every delta below would be measured off a baseline that is not
the audit's, and the curve is reported as a *declared reconstruction* with that
stated plainly rather than compared to the 72.2 % anchor.

## What this job cannot do

- It cannot separate duration from **domain**. It measures the archive/Saraga
  corpus against itself at shrinking durations, changing nothing else. The
  `0/10` on wild short clips (`handoff.md:279`) confounds duration with
  phone-mic domain; this job isolates the first and says nothing about the
  second.
- It says nothing about the **lyrics-ASR path**, in either direction.
- It graduates nothing. `~/sung_tests --cache-v2` remains the only scoreboard.
- The level-(c) artist merge is **partial** on the archive side, exactly as the
  audit recorded, so source-disjointness here is an upper bound on the truth,
  never a lower one — inherited along with the group vector.
- **The verdict and any decision about what to do next belong to the verifier
  seat.** This job states which row of the fixed table the number lands on and
  stops there.
