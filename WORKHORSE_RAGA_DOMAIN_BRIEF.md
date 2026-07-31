# Workhorse brief — decompose the domain gap: which degradation actually kills raga, and is it the tonic or the contour?

Date: 2026-07-31. For the **Opus 5 workhorse**. Read-only measurement, no GPU
required for the primary arms, no new audio downloaded. Nothing to commit beyond
the audit artifacts until the verifier has read the result.

Written by the verifier seat after accepting `data/RAGA_DURATION_CURVE.md`. Read
that and `data/RAGA_CONTAMINATION_AUDIT.md` first — this job inherits their
tier, their level-(c) group vector, their harness, and their 60 s window offsets.

## What is established, and what is now the only open question

Three measurements now bracket the problem, and the third is new:

| condition | raga top-1 | source |
|---|---|---|
| full-track, clean archive | 72.2% | `data/RAGA_CONTAMINATION_AUDIT.md`, source-disjoint |
| 60 s window, clean archive | 60.4% | `data/RAGA_DURATION_CURVE.md`, n=1554 |
| 60 s crops, clean, independent | 6/10 | `HANDOFF_SESSION_0719.md:100` |
| 60 s, `augment_wild` degradation | 12/77 ≈ 16% | `HANDOFF_SESSION_0719.md:100` |
| wild phone clips | 0/10 | `handoff.md:279` |

Duration costs about 12 points. **Degradation costs about 44.** The wall is
domain, and it is roughly four times the duration effect. That is settled and is
not what this job re-measures.

The open question is what *inside* "degradation" does the damage, and the
existing 12/77 cannot answer it because `augment_wild.py` applies up to five
transformations at once with none of them ablated.

## The thing that reading `augment_wild.py` changes

`augment_wild.py:97` applies a **±6 semitone pitch shift**, and its own docstring
says why: *"Tonic estimation is unsolved on wild clips, so invariance is trained
in, never estimated."* That is a sound reason to augment **training** data. It is
a bad reason to put it in a **test-time** degradation, because:

**a phone recording of a concert hall is not pitch-shifted.** Neither is it
time-stretched (`augment_wild.py:104`, 0.8-1.25×). Those two transformations
simulate nothing that happens in the field. The other three do: pink noise at
8-25 dB SNR, room reverb at RT 0.15-0.6 s, and `phone_mic` — a 120-350 Hz to
3400-7500 Hz bandpass, a resample round-trip through 8/11.025/16 kHz, and mu-law
companding.

So the 16% figure conflates field-realistic damage with an artifact that cannot
occur in the field, and **nobody knows the split.** If pitch shift dominates it,
then the 16% says almost nothing about why wild clips score 0/10, and the real
cause is still unidentified.

One specific mechanism is worth stating in advance so the result can confirm or
refute it rather than be fitted to it: **`phone_mic`'s high-pass corner is drawn
from 120-350 Hz, and Carnatic vocal fundamentals sit roughly 100-400 Hz.** A
350 Hz corner removes the fundamental outright for most male voices and much of
the female range. Melodia would then be tracking harmonics or nothing. This is a
prediction, not a finding; it may be wrong.

## Primary arm — component ablation

Corpus, tier, grouping and windows are **inherited unchanged**: the 18-raga
`min_tracks >= 25` tier, 518 tracks, the level-(c) source-disjoint group vector
from `scripts/raga_audit_protocol.py`, and **the same seeded 60 s window offsets
as the duration curve**, so every cell is paired against a 60.4% anchor rather
than a fresh baseline.

Condition: **mismatched — train on clean full-tracks, test on the degraded 60 s
window.** That is the deployed situation and it is the product number. Matched
training is a registered secondary and gates nothing.

One cell per degradation component, each applied **alone** at
`augment_wild.py`'s registered severity, seeded identically across cells:

| cell | component | occurs in the field? |
|---|---|---|
| `clean` | none — the 60.4% anchor | — |
| `noise` | pink noise, 8-25 dB SNR | **yes** |
| `reverb` | room IR, RT 0.15-0.6 s | **yes** |
| `phone` | `phone_mic` bandpass + resample + mu-law | **yes** |
| `field_all` | noise + reverb + phone together | **yes — this is the realistic worst case** |
| `pitch` | ±6 semitone shift | no |
| `stretch` | 0.8-1.25× | no |
| `all` | everything, reproducing the 12/77 condition | — |

**`field_all` is the cell that matters.** It is the honest simulation of a phone
in a hall, and the gap between `field_all` and `all` is exactly the artifact
this brief suspects is inflating the 16%.

## Secondary arm — tonic or contour, run only where damage appears

Run this **only on the cells that actually cost more than ~10 points**, to avoid
spending compute on cells that turned out not to matter.

TDMS is tonic-normalized. If the tonic estimate is wrong, every pitch-class bin
rotates and the whole 40×40 surface is garbage no matter how good the contour
is. So the damage decomposes into a 2×2:

| | clean tonic | degraded-estimated tonic |
|---|---|---|
| **clean contour** | the 60.4% anchor | isolates tonic failure alone |
| **degraded contour** | isolates contour failure alone | the full damage |

**For the `pitch` cell the clean tonic is analytic, not estimated:** a global
shift of *s* semitones moves the true tonic to `clean_tonic * 2**(s/12)`, and
`augment_wild` records `params["pitch_semitones"]`. So that cell's "correct
tonic" arm is exact rather than approximate — use it, and say that you did.

Also report, independently of any classifier and before fitting anything:
**the tonic drift distribution per cell** — median |drift| in cents, fraction
within 25 cents, and the fraction landing near ±700 or ±1200 cents, which are
the classic fifth- and octave-confusion failures. If drift is negligible in the
field-realistic cells, the tonic hypothesis is dead before a single forest is
fit, and that is a cheap and welcome outcome.

## Registered tertiary — the `--fast` confound, only if budget allows

Both the 0/10 and the 6/10 at `HANDOFF_SESSION_0719.md:100` were measured under
`--fast`, i.e. **no Demucs**, and entry 1 of that same section states flatly that
**"Demucs stems are load-bearing."** So some part of the wild collapse may be
separation rather than domain.

Register one cell: `field_all` + Demucs vocal separation before melodia. State
the cost before spending it — 518 × 60 s is 8.6 h of audio through Demucs — and
if it is too expensive, **say so and skip it rather than running a subsample and
reporting it as if it were the arm.**

## Interpretation, fixed in advance so it is not chosen after the number

Bands are on **`field_all`, mismatched, source-disjoint, top-1**, against the
60.4% clean-60 s anchor.

| result | what it means |
|---|---|
| **≥ 45%** | field-realistic degradation is survivable, the 16% was dominated by pitch/stretch artifacts, and **the 0/10 on wild clips is still unexplained** — the next job is to find what wild clips have that this simulation does not. |
| **25-45%** | real but partial damage. The 2×2 then says whether a tonic fix recovers it, and that decides whether the fix is narrow or structural. |
| **≤ 25%** | field-realistic degradation alone destroys the raga path, and the simulation reproduces the wild failure. The 2×2 becomes the whole question: tonic → narrow and fixable; contour → the melody front-end is the wall and raga joins the closed doors. |

Independently, on the 2×2 wherever it is run:

- clean-contour + degraded-tonic ≈ full damage → **wrong tonic is sufficient**;
  there are cheap fixes, including asking the listener for the shruti, which a
  Carnatic audience member can supply from the tanpura.
- degraded-contour + clean-tonic ≈ full damage → **the contour is destroyed**;
  tonic is a red herring and no tonic work is worth funding.
- both partial → both channels damaged, and report the split.

## Rules of engagement

- Read-only. Do not retrain production, do not overwrite `models/raga_v3_*.pkl`
  or `models/raga_classifier.pkl`, do not touch `identify_clip.py`.
- **Write `data/raga_domain/PREREGISTRATION.md` and `git commit` it as its own
  commit before the first fold is scored.** House standard since the raga audit.
- **Do not modify `augment_wild.py`.** Its parameters are the registered
  severity and changing them breaks comparability with the 12/77. Two staleness
  notes to record but *not* act on: its line 21 claims "No ffmpeg on this
  machine", which is false — ffmpeg 8.1.2 is at `/opt/homebrew/bin/ffmpeg`, so
  the mu-law companding is a proxy for a real codec that could now be used; and
  `time_stretch` changes the effective TDMS tau exactly as
  `WORKHORSE_RAGA_DURATION_BRIEF.md` described, so the `stretch` cell carries
  that confound by construction. Record both, repair neither.
- Inherit tier, groups and window offsets rather than re-deriving them. Freeze
  all three.
- **n before the percentage in every cell**: windows scored, windows discarded
  by the voiced guard, and — new here — windows where melodia returned too few
  voiced frames to score at all. **A cell that fails by producing no contour is
  a different finding from a cell that fails by producing a wrong answer, and
  the two must not be summed into one percentage.**
- One protocol per cell, chosen before running. Do not tune until a cell looks
  better.
- No conclusion about the lyrics-ASR path may be drawn from this job.
- Environment: essentia must run in **`venv_train`** (py3.11), fork not spawn;
  `venv` (py3.14) has sklearn/librosa but no pytest. Melodia measured at ~13×
  realtime, so each cell's contour rebuild is ~40 min of CPU for 8.6 h of audio.
  Budget accordingly and **run the field-realistic cells first** — `clean`,
  `phone`, `noise`, `reverb`, `field_all` — then `all`, then `pitch` and
  `stretch`, then the 2×2, then the Demucs tertiary. Write partial results to
  disk as you go so the run is resumable across sessions.
- Write it up in `data/RAGA_DOMAIN_DECOMPOSITION.md`: the per-cell table with n
  first, then the tonic-drift distributions, then the 2×2 where it was run, then
  a one-paragraph verdict against the fixed table. Log in `AGENT_LOG.md` in
  normal prose. **Leave the verdict and any decision about what to do next to
  the verifier seat.**
