# Workhorse brief — measure raga on real wild audio it can actually answer

Date: 2026-07-31. For the **Opus 5 workhorse**. Small job, no GPU needed for the
primary arm, ~29 clips. Nothing to commit beyond the audit artifacts until the
verifier has read the result.

Written by the verifier seat after accepting `data/RAGA_DOMAIN_DECOMPOSITION.md`
including its §9 addendum. Read that first.

## Why this exists

The repo has quoted **0/10 raga on wild short clips** since 2026-07-19 as
evidence that the raga path dies in the field. §9 of the domain decomposition
showed that only **29 of 106** clips in `~/sung_tests` name a raga the 18-raga
model can emit at all; on the other 77 the classifier cannot be right because
the answer is not in its label set. A ten-clip draw from that set has
**P(0 hits) ≈ 14%** — an unremarkable draw.

So the honest position is not "raga fails on wild audio". It is that **raga has
never been measured on wild audio it could answer.** This job is that
measurement, and it is the first in this series that is a real field number
rather than a simulation.

## The clip set is already frozen. Do not change it.

`data/raga_wild/FROZEN_CLIPS.json` was written and committed by the verifier
seat **before any prediction existed**, and carries per-clip `sha256`. It holds
**n = 29**, selected purely on the filename raga label folded through
`data/raga_aliases.json` against the 18-raga `min_tracks >= 25` tier.

- **Do not add clips.** Do not remove clips. Do not re-run selection.
- **Verify the hashes before scoring** and report any mismatch as a blocker.
- If a clip turns out to be unreadable or unusable, report it as such with its
  reason and score the rest; do not silently shrink the denominator.

Distribution is uneven and that is a fact about the set, not something to fix:
Tōḍi 5, Kalyāṇi 4, Bhairavi 3, Mōhanaṁ 3, then Nāṭa / Karaharapriya /
Harikāmbhōji 2 each, and eight ragas with 1. Three of the tier's eighteen ragas
have no clip at all. Two clips carry an `OOC` marker, which is
**out-of-composition-catalog and irrelevant here** — raga truth is unaffected.

## The power problem, stated up front

**n = 29 over 18 classes.** A 50% result carries a 95% CI of roughly
[31%, 69%]; a 20% result roughly [8%, 39%]. This job can distinguish "works
roughly as the simulation predicts" from "near the 5.6% chance floor". **It
cannot resolve anything finer, and no fine distinction may be drawn from it.**
Report the CI beside every percentage and never quote the point estimate alone.

## Two things that must be checked before the number means anything

1. **Label trust.** The filename raga labels have never been audited, and some
   clips were auto-fetched with metadata from the fetch source. Print the 29
   `(file, raga_label, raga_canonical)` rows in the write-up so a musician can
   read them. **If Deepti has not verified them, say the number is provisional
   on unverified labels** — do not bury that.

2. **Source-disjointness against the training corpus.** These are wild clips of
   different performances, so overlap is unlikely — but "unlikely" is exactly
   what was assumed about Qmax before it turned out 34 of 36 hits were
   byte-identical copies. Check each clip against the training corpus by
   audio hash and, where the title and artist are recoverable, by archive item
   using `data/qmax_audit/provenance.json`. Report any clip whose source may be
   in training, and score with and without it.

## The measurement

- **Model:** the exported `models/raga_v3_*` **fused** model — that is what a
  product would run. Report the TDMS-only harness as a registered secondary, so
  the number is comparable to the audit series.
- **Front end:** the same melodia path the cells used.
- **Arms, both registered:**
  - **mix** — melodia on the clip as-is, matching every prior measurement;
  - **demucs** — Demucs vocal separation first. This is the `--fast` confound
    that the domain job registered and skipped; here it is 29 clips and cheap,
    and it is finally being asked on audio where it matters.
- **Windowing:** report each clip's real duration. If a clip exceeds 60 s, score
  a 60 s window with the same seeded-offset convention as the duration curve
  **and** the whole clip, reporting both. If it is shorter, score what exists
  and report the length.
- **Read-outs:** top-1 and top-3, each with a 95% CI, plus per-clip results so
  every one of the 29 can be inspected by hand. At this n, the per-clip table is
  more informative than the mean.

## Interpretation, fixed in advance

Bands are on **top-1 over the 29, mix arm, best available window**, against the
domain job's `field_all` simulation of 48.7% and a chance floor of 1/18 ≈ 5.6%.

| result | what it means |
|---|---|
| **≥ 40%** (CI overlapping 48.7%) | the simulation was valid and **raga survives real field audio**. The 0/10 was a coverage artifact and nothing more. The raga-first concert companion has a measured component, and the next question is product, not model. |
| **20-40%** | real signal, but worse than the simulation predicts, so there is an unmodelled field factor. Identify it before building on the number. The `demucs` arm is the first place to look. |
| **< 20%** | the field genuinely kills it and the simulation is invalid despite being carefully built. Raga joins the closed doors, and the honest move is scope and demand. |
| **too few clips survive the checks** | report n as the finding. Do not fill the gap with the archive number. |

The `demucs` arm gates nothing but is decisive for what happens next: if it
materially beats `mix`, separation is load-bearing in the field exactly as
`HANDOFF_SESSION_0719.md` §4.1 claimed for the ASR path, and any product must
budget for it.

## Rules of engagement

- **This job reads `~/sung_tests`, which is the only scoreboard.** Every prior
  brief in this series said "does not touch the scoreboard"; this one does, and
  the boundary matters: **it is a raga measurement on those clips and must never
  be merged into, compared against, or reported alongside the composition
  scoreboard.** `~/sung_tests --cache-v2` composition numbers are untouched by
  this job and stay the only composition scoreboard.
- Read-only otherwise. Do not retrain, do not overwrite anything under
  `models/`, do not touch `identify_clip.py`, do not modify `augment_wild.py`.
- **Write `data/raga_wild/PREREGISTRATION.md` and `git commit` it before the
  first prediction is made.** House standard.
- **The clip list is frozen and committed. Selection is closed.** If you believe
  a clip should not be in it, say so in the write-up with the reason and report
  the number both ways — do not quietly drop it.
- n before the percentage; CI beside every percentage; per-clip table always.
- No conclusion about the lyrics-ASR path may be drawn from this job.
- Environment: essentia in **`venv_train`** (py3.11), fork not spawn; `venv`
  (py3.14) has sklearn/librosa and is what the audit scripts run under, no
  pytest there. Demucs lives in `venv_train`. Never run bare `pytest tests/`;
  run only `tests/test_clip_policy.py tests/test_registry_junk.py
  tests/test_negative_arm.py`.
- The user may be working in this repo from a separate terminal — prefer
  targeted `git add <path>` over `git add -A`.
- Write it up in `data/RAGA_WILD_MEASUREMENT.md`: the hash check and the
  disjointness check first, then the per-clip table, then top-1/top-3 with CIs
  for both arms, then a one-paragraph verdict against the fixed table. Log in
  `AGENT_LOG.md` in normal prose. **Leave the verdict and any decision about
  what to do next to the verifier seat.**
