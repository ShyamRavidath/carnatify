# Preregistration — domain-gap decomposition for the TDMS raga path

Registered 2026-07-31 against `WORKHORSE_RAGA_DOMAIN_BRIEF.md`, **before any
fold was scored and before the harness scripts were written**. Committed as its
own commit; the ordering is in git history, not in file mtimes.

The brief's cell design, its registered predictions and its interpretation table
are fixed and are not restated as choices here — they are inputs. What this
document registers is everything the brief left to the workhorse: how a cell is
built, what the tonic is in each arm, what counts as a discard, what the
reproduction gate is, and what will be reported whichever way the numbers fall.

Read-only. Production is not retrained, nothing under `models/` is written,
`identify_clip.py` is not touched, `augment_wild.py` is not modified.

---

## 1. What is inherited and frozen

Nothing in the corpus definition is re-derived.

* **Tier**: 18 ragas, `min_tracks >= 25`, **518 tracks**, from
  `data/RAGA_CONTAMINATION_AUDIT.md`.
* **Groups**: the level-(c) source-disjoint group vector, **155 groups**
  (archive item / Saraga concert, artist-merged) from
  `scripts/raga_audit_protocol.build_groups()`.
* **Windows**: the seeded 60 s window offsets already recorded in
  `data/raga_duration/protocol.json` (`offsets`, drawn once at
  `random_state=42`). All three are read out of that file; none is recomputed.
* **Folds**: `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`
  over the 518 tracks in `protocol.json` order with `groups=group_c`, exactly as
  `scripts/raga_duration_score.py` computes it. Every cell reuses the same fold
  assignment, so all cells are exactly paired.
* **Classifier**: `RandomForestClassifier(n_estimators=800, max_features='sqrt',
  random_state=42)`.
* **Feature**: the frozen multi-tau TDMS (`tau = 0.1/0.15/0.25 s`, 40 bins,
  sigma 1.0, alpha 0.75, 3×1600 dims), copied verbatim from
  `scripts/raga_duration_windows.py`, which is verbatim from
  `scripts/raga_audit_levels.py`. **Trap 2 (tau computed in original-hop frames
  and applied to the compacted voiced array, so the true delay is
  `tau_s / voicing_density`) is inherited unrepaired** and per-window voicing
  density is recorded so its size can be reported per cell.

### One window per track, not three

The duration curve used `K = 3` random-offset windows per track. This job uses
**`K = 1`, the first seeded offset (`offsets[0]`)**, giving **518 windows per
cell**. Registered reason: the brief's own cost model is `518 × 60 s = 8.6 h` of
audio per cell, and each cell here requires a full re-run of melodia and of tonic
estimation on freshly degraded audio, where the duration curve only sliced a
cached contour. Three windows per cell would triple nine cells of audio compute
for a within-track replicate that the duration curve already showed does not
change the cell means. The offsets are the *same* seeded offsets, so this is a
subset of the duration curve's windows and not a new draw.

Consequence, registered in advance: n per cell is 518, not 1554, so the
confidence intervals here are wider than the duration curve's and the
source-group bootstrap is the only interval that will be quoted.

---

## 2. The three baselines, and why there are three

The 60.4% anchor is *matched* training on a *cached* contour with a *reference*
tonic. Every degraded cell in this job differs from it in three ways at once, so
three baseline rows are registered and reported separately. Confounding them
would attribute pipeline change to degradation.

| row | contour | tonic | purpose |
|---|---|---|---|
| `cached` | the inherited cached contour (melodia cache for archive, Saraga annotation for Saraga), sliced on the time axis | the cached reference tonic (`protocol.json:tonic`) | **the reproduction gate** — links this harness to the duration curve and to the 60.4% anchor |
| `clean_reftonic` | melodia re-run on the clean 60 s audio through this job's own load path | the cached reference tonic | isolates "re-running melodia on a decoded 60 s window" from "estimating the tonic on it" |
| `clean` | melodia re-run on the clean 60 s audio | **estimated from the same 60 s window** | **the paired baseline every degraded cell is compared against** |

`clean` is the honest control, because a degraded cell also has its tonic
estimated from its own 60 s window. Both the `clean → cell` delta (paired, same
pipeline) and the absolute number against the 60.4% anchor will be reported for
every cell; the brief's interpretation bands are absolute, so the absolute
number is what the table is read on.

### Reproduction gate

`cached`, mismatched arm, must reproduce the duration curve's `mismatched:60`
restricted to the offset-0 windows. Two checks, both registered as gates:

1. **Bit-level**: the TDMS vector recomputed here from the cached contour at
   offset 0 must equal the corresponding row of `data/raga_duration/tdms_60.npz`
   to within `1e-6` max absolute difference, for all 518 windows.
2. **Score-level**: the `cached` mismatched top-1 must equal the offset-0 subset
   of the duration curve's `mismatched:60` cell on the same folds, exactly.

If gate 1 fails the harness is wrong and no cell is reported. The 60.4% anchor
itself is a *matched* 1554-window number and is not expected to be reproduced
exactly by a 518-window mismatched subset; it is quoted as the anchor, not as a
gate.

---

## 3. How a cell is built

Per track, one window, identical seeds across all cells.

1. **Load** 60.0 s of the source audio at **22050 Hz mono**, starting at
   `offsets[0]` of the usable range in the same raw-frame arithmetic as
   `raga_duration_windows.plan()` (`need = round(60/hop)`, `room = n_raw - need`,
   `start = round(u * room)`, converted to seconds via the track's own hop).
   22050 Hz because that is `augment_wild.SR` and the registered severity of
   every component is defined at that rate (filter corners in `fs=SR`, resample
   targets, IR lengths).
2. **Degrade** by calling `augment_wild`'s own functions, **imported, not
   copied and not modified**, in `augment_chain`'s order.
3. **Resample to 44100 Hz** — the rate the melodia cache was built at.
4. **Tonic**: `essentia.standard.TonicIndianArtMusic()` on the 44100 Hz
   *degraded* signal of that same 60 s window.
5. **Melody**: `PredominantPitchMelodia(frameSize=2048, hopSize=128)` applied to
   `EqualLoudness()` of the same signal — **exactly `extract_melodia_full.py`'s
   parameters**, because the training features come from that cache.
6. **Feature**: voiced filter `(f0 > 0) & isfinite`, then multi-tau TDMS of
   `1200 * log2(v / tonic)`.

The `clean` cell runs steps 1, 3, 4, 5, 6 — the same 22050 → 44100 round trip,
so the only difference between `clean` and any degraded cell is the degradation
itself.

### Seeding, so components are identical across cells

Each component draws from its own dedicated stream,
`random.Random(f"raga_domain|{component}|{stem}")`. The `phone` parameters for
track *i* are therefore bit-identical in the `phone` cell, in `field_all` and in
`all`, and no component's draw can be displaced by another component's presence
or absence. This is what "seeded identically across cells" is implemented as.

### Cell composition, fixed before running

| cell | components applied, in `augment_chain` order |
|---|---|
| `cached` | — (cached contour, reference tonic) |
| `clean_reftonic` | — (re-run melodia, reference tonic) |
| `clean` | — (re-run melodia, estimated tonic) |
| `noise` | `add_noise` |
| `reverb` | `room_reverb` |
| `phone` | `phone_mic` |
| `field_all` | `room_reverb` → `add_noise` → `phone_mic` |
| `pitch` | `pitch_shift` |
| `stretch` | `time_stretch` |
| `all` | `pitch_shift` → `time_stretch` → `room_reverb` → `add_noise` → `phone_mic` → `agc_clip` |

Two things registered in advance about `all`:

* `augment_chain` applies each component behind a probability gate (0.8 / 0.7 /
  0.6 / 0.7 / 0.7 / 0.5) and begins with a fresh `rand_crop`. Neither is used
  here: the crop would move the window and break pairing, and the gates would
  make the cells unpaired. `all` applies **all six deterministically**, which
  makes it the *upper* end of the 12/77 condition rather than its mean.
* `agc_clip` is in `all` and, per the brief's fixed cell table, not in
  `field_all`. **The `all` − `field_all` gap therefore bundles AGC with pitch
  and stretch and is not a clean pitch+stretch contrast.** Recorded here, not
  repaired, because the cell table is fixed. No `agc` cell is added.

`augment_chain`'s two output rules are kept: truncate to 60 s if a component
made the signal longer (only `time_stretch` can), and peak-normalise if the peak
exceeds 1.0. Both are applied in every cell including `clean`, so they are not a
difference between cells.

### Registered staleness notes — recorded, not acted on

* `augment_wild.py:21` claims "No ffmpeg on this machine". **This is false**:
  ffmpeg 8.1.2 is at `/opt/homebrew/bin/ffmpeg`. The mu-law companding in
  `phone_mic` is therefore a proxy for a real opus/AAC round trip that could now
  be measured instead. Not changed — changing it breaks comparability with the
  12/77.
* `time_stretch` at rate *r* rescales the time axis, so the frozen TDMS's
  effective tau becomes `tau_s / r` in musical time. **The `stretch` cell
  carries a tau confound by construction** and its result is a joint statement
  about stretch and tau. It also changes the real window length to `60/r`
  seconds (48 – 75 s, truncated at 60 s), so `stretch` is additionally a
  duration cell. Both recorded here in advance.
* `HANDOFF_CLIP_ID.md` §5 entry 5 records that the voice-band melodia
  constraint (`minFrequency=90, maxFrequency=900, voicingTolerance=0.6`) fixed
  melody extraction on wild clips and should be kept. **This job deliberately
  does not use it**, because the training features in `tdms_full.npz` come from
  `extract_melodia_full.py`'s default parameters and a train/test extractor
  mismatch would be a second uncontrolled variable. Recorded as a scope limit:
  every number here is for the *cache's* melodia settings, not the deployed
  clip settings.

---

## 4. n before the percentage — the discard taxonomy, fixed now

Four mutually exclusive outcomes per window, reported as counts for every cell
before any rate is quoted. **They are never summed into one percentage.**

| outcome | rule |
|---|---|
| `no_contour` | melodia returned **zero** voiced frames in the 60 s window |
| `min_voiced` | `0 < n_voiced < 500` — the frozen harness's own guard, reused verbatim |
| `tdms_none` | the TDMS returned `None` at any tau (voiced array no longer than tau) |
| `scored` | everything else; only these enter the numerator and denominator |

`no_contour` is separated from `min_voiced` because the brief requires it: **a
cell that fails by producing no contour is a different finding from a cell that
fails by producing a wrong answer.** Both the "of windows scored" rate and the
"of all 518 windows" rate will be printed for every cell so neither reading can
be quoted selectively.

Registered pre-score expectation, so it can be wrong on the record: the
`phone_mic` high-pass corner is drawn uniformly from 120–350 Hz and Carnatic
vocal fundamentals sit roughly 100–400 Hz, so the `phone` and `field_all` cells
are where `no_contour` and `min_voiced` should appear if the brief's mechanism
is right. If they do not appear there, that mechanism is refuted.

**Tonic failure** is a fifth count, orthogonal to the four: if
`TonicIndianArtMusic` throws or returns outside 80–400 Hz (`identify_clip.py`'s
own range), the window is scored with `identify_clip.py`'s own fallback of
146.83 Hz and counted as `tonic_fail`.

---

## 5. Arms

**Primary, and the only arm the interpretation table is read on: mismatched.**
Train on **clean full-track** TDMS — the existing `data/raga_duration/tdms_full.npz`
shard, reference tonic, no degradation — and test on the degraded 60 s window.
That is the deployed situation: the exported model meets a phone clip. Five
forests, one per fold, fitted once and reused for every cell.

**Registered secondary, non-gating: matched.** Train on the *same cell's*
degraded windows (train folds) and test on its held-out windows. Reported for
every cell because the marginal cost is one forest fit on 518 rows. It gates
nothing and is not the row the table is read on.

---

## 6. Tonic drift — reported before any forest is fitted

Per cell, independently of the classifier, over all windows where a tonic was
obtained:

* signed drift in cents, `1200 * log2(t_est / t_ref)`, where `t_ref` is the
  cached reference tonic — **except for the `pitch` cell**, where the true tonic
  is analytic: `t_ref_pitch = t_ref * 2 ** (s / 12)` with *s* the recorded
  `pitch_semitones` for that track. That cell's drift is measured against the
  analytic tonic and its 2×2 "clean tonic" arm uses the analytic tonic exactly,
  not an estimate;
* **median |drift|** in cents;
* **fraction within 25 cents**;
* **fraction near ±700 cents** (fifth confusion) and **near ±1200 cents**
  (octave confusion), both with a ±50 cent tolerance;
* the same three fractions after octave-folding the drift into (−600, +600],
  because the estimator is clamped to 80–400 Hz and can return the right pitch
  class in the wrong octave.

Registered in advance: **if median |drift| in `field_all` is small and the
within-25-cents fraction is high, the tonic hypothesis is dead before a single
forest is fit, and that is a welcome outcome, not a failed job.**

---

## 7. The 2×2, and when it is interpreted

Four arms per cell, all four using the **mismatched** classifier:

| | clean tonic | degraded-estimated tonic |
|---|---|---|
| **clean contour** | `clean_reftonic` | isolates tonic failure alone |
| **degraded contour** | isolates contour failure alone | the cell itself |

"Clean contour" means this job's own melodia-on-clean-audio contour for the same
window, not the cached contour, so the only variable is the tonic. Because all
four arms are a TDMS recomputation plus a forest `predict_proba` — no new audio
work — the 2×2 is **computed for every cell**. Per the brief it is
**interpreted only for cells costing more than ~10 points against `clean`**, and
that trigger is registered here so it cannot be moved after the numbers are
seen. The three-way verdict (tonic sufficient / contour destroyed / both
partial) is the brief's and is not restated.

---

## 8. Tertiary — Demucs, cost stated in advance

Measured on this machine before registering: `htdemucs --two-stems=vocals` on a
60 s clip takes **40 s wall / 166 s CPU at ~470% CPU**. For 518 windows that is
**≈ 5.8 hours wall**, already core-saturated so it does not parallelise further.
The whole primary arm, by comparison, is ~3.5 s per window per cell, ≈ 5 minutes
wall per cell at 6 workers.

Registered decision rule, fixed now: the Demucs cell is run **only if the
primary arms leave it decision-relevant**, and if it is not run, that is stated
as a skip with the cost. **It will not be run on a subsample and reported as if
it were the arm.**

---

## 9. What will be reported whichever way it falls

* Every cell's four-way n before any percentage, both denominators.
* The tonic-drift distribution for every cell, before the classifier section.
* The paired `clean → cell` delta and the absolute number against the 60.4%
  anchor, for every cell.
* Source-group bootstrap intervals (2000×, resampling the 155 level-(c) groups
  with replacement) on every cell and on every paired difference, computed after
  the cells and labelled post-hoc.
* The row of the brief's fixed interpretation table that `field_all`,
  mismatched, source-disjoint, top-1 lands on — and nothing beyond it.
* Per-raga breakdown at `field_all` and at `clean`, non-gating.

## 10. Scope limits, registered now

* **Nothing here is a scoreboard number.** `~/sung_tests --cache-v2` remains
  the only scoreboard. This is a simulation of degradation on archive/Saraga
  audio; agreement with wild clips is a hypothesis it can support or refute,
  never a substitute.
* **No conclusion about the lyrics-ASR composition path may be drawn from this
  job.** The channels share no code, no feature and no model.
* The level-(c) artist merge is partial on the archive side, inherited, so
  source-disjointness is an upper bound on the truth and never a lower one.
* Melodia here uses the *cache's* parameters, not the deployed clip parameters
  (§3). Numbers do not transfer to `identify_clip.py`'s settings.
* **The verdict, and any decision about what to do next, belong to the verifier
  seat.** This job states the measurement and the row.
