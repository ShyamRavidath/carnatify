# Workhorse brief — how much audio does raga actually need?

Date: 2026-07-30. For the **Opus 5 workhorse**. Read-only measurement, no GPU,
no new audio, no ASR. Everything needed is already on disk. Nothing to commit
beyond the audit artifacts until the verifier has read the result.

Written by the verifier seat immediately after accepting
`data/RAGA_CONTAMINATION_AUDIT.md`. Read that first — this brief reuses its
group vectors, its tier, and its harness.

## Read this paragraph before anything else

**`HANDOFF_CLIP_ID.md` §5 contains a graveyard entry that reads "Duration as a
lever. Ruled out, not merely undetected. Do not propose *just give it more
audio* again without new evidence."** That entry is real and it is binding, and
this brief is standing right next to it.

Here is the distinction, and if you do not accept it, say so and stop rather
than run the job. The duration KILL was measured on the **lyrics-ASR
composition-recall** path: longer windows fed to Whisper did not produce more
identifiable transcripts, top-5 went 5.1% @30s → 1.7% @300s. This brief measures
a **different channel entirely** — melodic contour → TDMS → raga label, no ASR
anywhere in it — and it asks the **opposite question**: not "does more audio
help", but **"how little audio is enough"**. The two share no code, no feature,
and no model. If the answer here is "raga needs five minutes", that is a
constraint on the product, not a rescue of the killed lever.

You are also forbidden from letting any result here be quoted as evidence about
the lyrics path. Say so explicitly in the write-up.

## Why this is the next thing

`data/RAGA_CONTAMINATION_AUDIT.md` established that full-recording raga is real:
72.8% top-1 survives source-disjoint grouping at 72.2% while independent units
collapse 518 → 155. It is the only clean result left in the repository.

`handoff.md:279` records the same TDMS raga path at **0/10 on wild short
clips**. Those two facts are both true and nobody knows why. The 0/10 confounds
**two** variables at once:

- **duration** — full concert item vs a 30-60s clip;
- **domain** — clean archive/Saraga recordings vs phone-mic audio of a live hall.

**This job isolates the first.** It measures the archive corpus against itself at
shrinking durations, changing nothing else. If archive-domain raga holds at 60s,
duration is not the wall and the wall is domain — which is a different and also
cheap next test. If it collapses at 60s but holds at 300s, then the
concert-companion framing (a listener present for a 10-30 minute item, who can
give the app several minutes) survives and the inherited 30-second Shazam
contract dies for good.

Either answer is decision-grade. That is why it is worth an evening.

## The design

Corpus, tier and grouping are **inherited unchanged** from the raga audit: the
18-raga `min_tracks >= 25` tier, 518 tracks, and the level-(c) source-disjoint
group vector from `scripts/raga_audit_protocol.py`. Do not re-derive them and do
not re-tune the tier. Every number in this job is scored source-disjoint; there
is no reason to ever report a level-(a) figure again.

**Durations:** 30, 60, 120, 300, 600 seconds, plus full-track as the anchor.

**Windows.** One window is one user session, so the product-relevant unit is the
window, not the track. Take **K = 3 windows per track per duration at random
offsets**, seeded (`random_state=42`, offsets drawn once and reused across every
duration and both conditions so the arms are paired). Tracks shorter than the
duration contribute their whole length once, and **must be counted and reported
separately** — a "300s" cell where a third of tracks are shorter than 300s is
measuring something other than 300 seconds.

Random offset, not from-the-start, because these archive files are already
segmented items and a concert listener arrives mid-item. Registered secondary,
non-gating: the same measurement from the start of the track, which is what a
user who opens the app when the item begins would get.

**Two conditions, and the gap between them is the point:**

| condition | train on | test on | question it answers |
|---|---|---|---|
| **matched** | windows of duration *d* | windows of duration *d* | is the raga information present in *d* seconds at all? |
| **mismatched** | full tracks | windows of duration *d* | does the model we already exported work at *d* seconds? |

If matched is high and mismatched is low, the fix is retraining, which is hours.
If matched is low, the information is not there and no amount of engineering
recovers it. Report both at every duration.

## Two implementation traps — read the harness before you write code

1. **Truncate the raw contour, not the voiced frames.**
   `scripts/raga_audit_levels.py:117` does `v = f[(f > 0) & np.isfinite(f)]`
   over the whole track and computes TDMS on the *compacted* voiced sequence.
   If you take "the first N voiced frames" you get a window of unknown real
   duration. **Slice the raw melodia contour on the time axis first, then apply
   the voiced filter**, and let each window yield however many voiced frames it
   yields. Report the voiced-frame distribution per duration.

2. **Register a minimum-voiced-frames guard and report what it discards.**
   The frozen harness already drops tracks with `v.size < 500`. A 30s window in
   a sparse passage may fall below any sane threshold. Choose the guard **before
   scoring**, state it in the prereg, and report the discard rate per duration —
   *a high discard rate at 30s is itself a finding about what a short clip
   contains*, and it must not be silently dropped into the denominator.

**Record, do not fix:** the harness computes `tau` in frames of the original hop
but applies it to the compacted voiced array, so its nominal 0.1/0.15/0.25 s
delays are only nominal — the true delay scales with voicing density, and
therefore *changes with window length*. This is a real confound for a duration
sweep and it is pre-existing. **Do not repair it** — that would change the
frozen harness and break comparability with the audit. Measure it: report mean
voicing density per duration so the size of the confound is on the record. If it
moves a lot across durations, say so in the verdict.

## Interpretation, fixed in advance so it is not chosen after the number

Bands are on **matched, source-disjoint, top-1, at 60 s**, against the 72.2%
full-track level-(c) anchor.

| result | what it means |
|---|---|
| **≥ 65%** | duration is not the wall. A minute is enough, and the 0/10 on wild clips is **domain**, not length. Next job is a domain test, and it is cheap. |
| **45-65%** | partial. Report the knee of the curve — the shortest duration clearing 65% — because that number *is* the product spec. |
| **< 45%, but ≥ 65% at 300 s** | raga needs minutes. The concert-companion framing survives intact and the 30-second contract is dead for good. Say both plainly. |
| **< 65% at every duration including 600 s** | the full-track result depends on long-horizon statistics no clip will have. Raga is then not a clip product either, and the only honest move is scope and demand. |

The mismatched arm is reported at every duration but **gates nothing** — it
diagnoses whether a shortfall is a retraining problem or an information problem.

## Rules of engagement

- Read-only. Do not retrain production, do not overwrite `models/raga_v3_*.pkl`
  or `models/raga_classifier.pkl`, do not touch `identify_clip.py`.
- **Write `data/raga_duration/PREREGISTRATION.md` and `git commit` it before the
  first fold is scored.** The raga audit did this and it is now house standard.
- Inherit the tier and the level-(c) groups from `scripts/raga_audit_protocol.py`
  rather than re-deriving them. Freeze both.
- One protocol per cell, chosen before running. Do not tune until the curve
  looks better.
- **n before the percentage in every cell** — windows scored, windows discarded
  by the voiced guard, tracks shorter than the duration.
- No conclusion about the lyrics-ASR path may be drawn from this job. State that
  in the write-up.
- Estimated cost: ~9,300 TDMS computations (518 tracks × 6 durations × 3
  windows) plus ~60 RF800 fits (6 durations × 2 conditions × 5 folds). Hours on
  8 cores, no GPU. Cache the per-window TDMS to `data/raga_duration/` and
  gitignore anything over a few MB, as the audit did.
- Write it up in `data/RAGA_DURATION_CURVE.md`: the curve with its n first, the
  matched/mismatched gap, the voicing-density confound, then a one-paragraph
  verdict against the fixed table. Log in `AGENT_LOG.md` in normal prose.
  **Leave the verdict and any decision about what to do next to the verifier
  seat.**
