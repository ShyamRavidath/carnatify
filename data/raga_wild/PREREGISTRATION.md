# Preregistration — raga on the 29 in-tier wild clips

Registered by the Opus 5 workhorse against `WORKHORSE_RAGA_WILD_BRIEF.md`
(verifier seat) on 2026-07-31. **Committed before any prediction exists.** House
standard: the ordering is in git history, not in file mtimes.

This document fixes every reading, every arm, every convention and every
failure category *before* the classifier is run on a single clip. Anything not
written here and later reported is a post-hoc addition and must be labelled as
one.

---

## 0. What is already closed and cannot be reopened here

- **The clip set.** `data/raga_wild/FROZEN_CLIPS.json`, n = 29, committed at
  `f67ef98` by the verifier seat before any prediction existed. Selection is
  closed. This job may only *verify* it. Clips are not added, removed, swapped
  or re-selected.
- **The interpretation table** in the brief (≥ 40% / 20-40% / < 20% / too few
  clips survive), fixed on **top-1 over the 29, `mix` arm, best available
  window**, against the domain job's `field_all` simulation of **48.7%** and a
  chance floor of **1/18 ≈ 5.6%**.
- **The power statement.** n = 29 over 18 classes. This job separates "near the
  48.7% simulation" from "near the chance floor" and nothing finer. No fine
  distinction may be drawn from it.

## 1. Gates that must pass, and what happens if they do not

**Gate 1 — hash.** Every clip is re-hashed on disk (sha256 + byte length)
against the frozen record. A mismatch is a **blocker** reported as such; it is
not repaired and the frozen file is not edited.

**Gate 2 — readability.** A clip that cannot be decoded is reported with its
reason and excluded from the numerator *and* named explicitly, with the
denominator reported both ways (29 and 29 − k). The denominator is never
silently shrunk.

**Gate 3 — source-disjointness.** Two independent checks, both reported before
any accuracy figure:

- **3a, audio hash.** sha256 of every training audio file under
  `data/concert_audio/**` (archive half) and `saraga1.5_carnatic/**` (Saraga
  half) against the 29. Byte length is joined first as an exact prefilter —
  byte-identity implies equal length, so the size join is a *complete* screen
  for the Qmax failure mode (34/36 hits byte-identical copies) — and the full
  sha256 is computed anyway so the statement is unconditional.
- **3b, identity.** Folded title joined against
  `data/qmax_audit/provenance.json` (1232 training rows with
  `archive_identifier`, `title_stem`, `raga_dir`, `artist`), plus
  `~/sung_tests/fetch_manifest.tsv` source URL and window where the clip was
  auto-fetched.

**A *work* match (same composition, different performance) is not
contamination and is reported separately from a *recording* match.** Only a
recording match is contamination. **Any clip with a recording match is reported
and the headline is given with and without it.** Registered in advance: a work
match is *expected* to be common — the training corpus is Carnatic concert
audio and these are famous kritis — and its commonness is not a finding.

**Gate 4 — window inventory.** Each clip's real duration from `ffprobe`.

## 2. Windowing, fixed before any duration was inspected in a scoring context

- Every clip is scored on its **whole clip**, whatever its length, and the
  length is reported per clip.
- A clip **longer than 60 s** is additionally scored on a **60 s window** using
  the duration curve's own seeded-offset convention:
  `np.random.default_rng(42)`, `K = 3` fractions drawn per clip with clips
  visited in **sorted-filename order**, **offset index 0** used
  (`scripts/raga_duration_protocol.py:offset_fractions`,
  `data/raga_domain/protocol.json:offset_index`), and
  `start_s = round(u0 * (duration − 60))`.
- **"Best available window", named now so it cannot be chosen after seeing the
  numbers, is the WHOLE CLIP** — the longest audio the clip actually has. The
  duration curve is monotone in duration (52.5% at 30 s → 72.2% full-track), so
  the whole clip is the best-available window by construction and not by
  outcome. The 60 s window is reported beside it for every clip that has one.
- A clip shorter than 60 s is scored on what exists and its length is reported.
  It is **not** padded, repeated or dropped.

## 3. The model. Primary, secondary, and one restricted read-out

**Primary — the exported fused model, exactly as a product would run it.**
`models/raga_v3_tdms_rf.pkl` + `models/raga_v3_hist_rf.pkl` +
`models/raga_v3_label_encoder.pkl`, combined as
`P = (1 − 0.4)·P_tdms + 0.4·P_hist` with `FUSION_W_HIST = 0.4` read from
`models/raga_v3_meta.json`. Nothing under `models/` is written.

**Registered in advance, because it moves the number and was not anticipated by
the brief: the exported model has 32 classes, not 18.** `raga_v3_meta.json`
records `min_tracks: 20` and 32 ragas. The 18-raga `min_tracks >= 25` tier that
selected the clip set is a *subset* of those 32. The brief's reference points —
48.7% and the 1/18 ≈ 5.6% floor — are both 18-class quantities. Therefore:

- the **primary** figure, and the one the interpretation table is read on, is
  the **as-exported 32-class fused model**, because that is what a product
  would run and the brief says so plainly. Its chance floor is 1/32 ≈ 3.1%;
- a **registered restricted read-out** is reported immediately beside it: the
  same posterior restricted to the 18 tier ragas and renormalised. This is the
  figure directly comparable to 48.7% and to the 5.6% floor. It is registered
  as a read-out, not as a second model, and it can only be higher than or equal
  to the unrestricted one.

Both are reported in the same table for every arm and window. Neither is chosen
after the fact.

**Secondary — TDMS-only.** `models/raga_v3_tdms_rf.pkl` alone. This is the
configuration whose source-disjoint archive score is 72.2% / 84.0%, identical to
`data/RAGA_CONTAMINATION_AUDIT.md` level (c), so it is the arm comparable to the
audit series. Also reported unrestricted and tier-restricted. Non-gating.

**Correctness.** A prediction is correct when the model class folds equal to the
clip's `raga_canonical` under the harness's own fold (`unicodedata` NFKD,
combining marks stripped, lowercased, non-alphanumerics removed) — the same
`_fold` used by `train_raga_v3_tdms.py` and `scripts/raga_duration_protocol.py`.
Top-3 is membership of the truth in the three highest-probability classes.

## 4. Front end and arms

Both arms share everything except the audio handed to melodia.

- **`mix`** — melodia on the clip window as-is. This is the arm every prior
  measurement in this series used and **it is the arm the interpretation table
  is read on.**
- **`demucs`** — `htdemucs --two-stems=vocals` on the clip window first, then
  melodia on the separated vocal. **Gates nothing.** Registered because the
  domain job registered it and skipped it, and because
  `HANDOFF_SESSION_0719.md` §4.1 claims separation is load-bearing on the ASR
  path.
- **`mix_voiceband`** — non-gating diagnostic, registered here and nowhere else
  in the series. Melodia with `identify_clip.py`'s own wild-clip constraint
  (`minFrequency=90, maxFrequency=900, voicingTolerance=0.6`), which
  `HANDOFF_CLIP_ID.md` §5 item 5 records as the thing that "fixed melody
  extraction — keep it" on wild clips, against the unconstrained parameters the
  training cache was built with. **It cannot move the verdict**; it exists so
  that a front-end/training mismatch, if there is one, is on the record rather
  than confounded into the headline.

**Melodia parameters, primary:** `PredominantPitchMelodia(frameSize=2048,
hopSize=128)` on `EqualLoudness()` of 44.1 kHz mono — `extract_melodia_full.py`
verbatim, which is what the training cache and every cell of the domain job
used.

**Sample rate.** Clips are decoded natively at **44100 Hz**, the rate the
melodia cache was built at. The domain job's 22050 → 44100 round trip existed
only because `augment_wild.SR` is 22050 and the severities are defined there;
there is no augmentation here, so the round trip is dropped and the wild audio
reaches melodia at the training cache's own rate. Registered as a deliberate
difference from the domain cells.

**Tonic, both arms, one estimate.** `TonicIndianArtMusic()` on the **mix**
window, accepted if within `identify_clip.py`'s own range [80, 400] Hz, else
`identify_clip.py`'s own fallback 146.83 Hz, with the fallback counted and
reported. The tonic is estimated on the mix in the `demucs` arm too, because
`raga_v2_pipeline.py:56` records that the drone-based estimator must run before
separation — Demucs strips the tambura the estimator relies on. This keeps the
two arms differing **only** in the melodia input. The tonic estimated on the
separated vocal is recorded as a diagnostic and used for nothing.
`identify_clip.py`'s 12-rotation tonic vote is **not** used: `HANDOFF_CLIP_ID.md`
§5 item 4 records it as failed and anti-informative, and it is not part of the
audit-series harness.

**The histogram half of the fused model uses Demucs by construction, in both
arms.** `raga_v2_pipeline.py` defines the production 480-dim feature as
`librosa.pyin` on the **htdemucs vocal** of the segment, tonic-normalised via
`carnatify.ml.raga_features.extract_features`. There is no mix-only version of
that feature and inventing one would not be the exported model. So the `mix`
arm's *fused* prediction still contains a Demucs-derived component; only its
TDMS half is mix-only. **This is registered now, in advance, as a limit on how
cleanly the two arms separate "with and without separation".** The TDMS-only
secondary is completely free of Demucs in the `mix` arm and is the clean
contrast.

**Histogram window.** The 480-dim feature is computed on the *same* window as
the TDMS branch, with the same tonic, rather than on `raga_v2_pipeline.py`'s
"skip 30 s, take 65 s" training convention — because these clips are 43-85 s
long and that convention would leave several of them with nothing. Registered
as a deliberate difference.

## 5. Failure taxonomy, mutually exclusive, never summed

Per clip per window per arm, exactly one of:

`scored` · `audio_unavailable` (decode failed) · `demucs_fail` ·
`no_contour` (zero voiced melodia frames) · `min_voiced` (fewer than **500**
voiced frames, the frozen harness's own `v.size < 500` guard reused verbatim) ·
`tdms_none` · `error`.

`tonic_fail` (estimator out of range, fallback used) is a **flag, not an
outcome** — the clip is still scored, exactly as `scripts/raga_domain_cells.py`
does it. Counts for all categories are reported whether or not they are zero.

Registered in advance: **a failure to produce a contour is a different finding
from producing a wrong answer**, and the two are never added together. If a
material number of clips fail to produce a contour, the brief's fourth row
("too few clips survive the checks") applies and **n is the finding** — the gap
is not filled with the archive number.

## 6. Read-outs, fixed

- **n before every percentage.** The per-clip table is reported **always** and
  in full; at n = 29 it is more informative than the mean.
- **95% CI beside every percentage**, never a point estimate alone. Interval:
  **Wilson score**, unit = the clip (29 independent wild recordings; there is no
  group structure to resample here as there was in the archive corpus). Wilson
  is used rather than a bootstrap because at n = 29 a bootstrap of a proportion
  is discrete and no better behaved.
- **top-1 and top-3** for each of: {fused, TDMS-only} × {as-exported 32-class,
  tier-restricted 18-class} × {`mix`, `demucs`, `mix_voiceband`} × {whole clip,
  60 s window}.
- **Paired arm comparison:** exact McNemar (binomial on the discordant pairs),
  `demucs` against `mix`, on the fused primary at the whole-clip window.
- **Per-clip:** truth, top-1, its probability, top-3, rank of the truth,
  duration, window, voiced frames, voicing density, estimated tonic and whether
  the fallback fired.
- Also reported: **rank of the true raga** distribution, and how often the truth
  is in the top 5 — because at n = 29 the rank distribution carries information
  the top-1 count throws away.

## 7. Pre-score expectations, written down so they can be wrong

Registered before any clip was scored. These are predictions, not targets, and
nothing is tuned to hit them.

1. **Contour failures will be rare.** The domain job produced a usable contour
   in 517 of 517 windows through bandpass, 8 kHz resampling and mu-law
   companding. These clips are cleaner than that. Expect `no_contour` and
   `min_voiced` at 0-2 clips total, dominated by the shortest clip (43 s).
2. **Tonic fallback will fire more often than in the archive corpus.**
   `HANDOFF_CLIP_ID.md` §5 item 5 records the estimator returning 158-371 Hz on
   same-shruti wild material. Expect the fallback on 0-5 of 29, and expect tonic
   error — not contour damage — to be a *larger* share of the damage here than
   the 3:1 contour:tonic ratio the domain job measured, because in the field
   there is often no sustained tambura at all.
3. **The 32-class read-out will land below the 18-class read-out by roughly
   5-12 pp**, mechanically, from the four extra confusable neighbours the tier
   excludes (Kāṁbhōji against Harikāmbhōji, Madhyamāvati, Śrīranjani, Bilahari).
4. **Point prediction for the primary (fused, `mix`, whole clip, 32-class):
   20-40%**, i.e. the middle row of the fixed table — real signal, below the
   48.7% simulation. Reasoning: the simulation was 18-class, matched-domain
   archive audio at 60 s; this is 32-class, genuinely out-of-domain, 43-85 s,
   and the domain job could not reproduce the wild failure, so an unmodelled
   field factor of *some* size is more likely than none. **I expect to be
   wrong in the direction of the top row if the tier-restricted read-out is
   used, and wrong in the direction of the bottom row if tonic estimation fails
   badly.**
5. **`demucs` will beat `mix` by a small positive amount that n = 29 cannot
   resolve** — expect a delta of 0-15 pp with a McNemar p above 0.05. A
   *material* win for `demucs` is the outcome that would matter most, and it is
   not the one I expect.

## 8. What this job does not do, registered as boundaries

- **It does not touch the composition scoreboard.** It reads `~/sung_tests`,
  which is the only scoreboard, but it is a **raga** measurement on those files.
  It is never merged into, compared against, or reported alongside the
  `~/sung_tests --cache-v2` composition numbers, which are untouched by this
  job and remain the only composition scoreboard.
- **No conclusion about the lyrics-ASR path may be drawn from it**, in either
  direction. Different channel, different features, different model.
- **It graduates nothing and decides nothing.** The verdict against the fixed
  table, and any decision about what happens next, belong to the verifier seat.
  This job states the measurement and the row it lands on.
- Read-only: no retraining, nothing under `models/` written,
  `identify_clip.py` untouched, `augment_wild.py` unmodified,
  `data/raga_wild/FROZEN_CLIPS.json` unmodified.
- **The labels are unaudited.** Every figure in this job is provisional on the
  filename raga labels, which have never been verified by a musician. The label
  table is printed in full so they can be. If a label is wrong the clip's result
  is wrong in an unknown direction, and at n = 29 a single mislabelled clip is
  3.4 percentage points.

## 9. Artifacts this job will produce

| file | what |
|---|---|
| `data/raga_wild/PREREGISTRATION.md` | this file, committed before any prediction |
| `scripts/raga_wild_protocol.py` | hash gate, label table, disjointness, window inventory — no score |
| `scripts/raga_wild_features.py` | per clip / window / arm: melodia, tonic, TDMS, Demucs+pyin histogram |
| `scripts/raga_wild_score.py` | the exported models, both arms, all read-outs, CIs, McNemar |
| `data/raga_wild/protocol.json` | gate output, machine-readable |
| `data/raga_wild/results.json` | every cell and every per-clip row |
| `data/RAGA_WILD_MEASUREMENT.md` | the write-up |
