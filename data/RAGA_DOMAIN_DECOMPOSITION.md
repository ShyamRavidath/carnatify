# Raga domain decomposition — which degradation kills raga, and is it the tonic or the contour?

Executed 2026-07-31 against `WORKHORSE_RAGA_DOMAIN_BRIEF.md`. Read-only: nothing
under `models/` written, `augment_wild.py` unmodified, `identify_clip.py`
untouched. Readings registered in `data/raga_domain/PREREGISTRATION.md` and
**committed** (`3792d42`) before the harness (`c236462`) and before any fold was
scored.

Cells were built by the Opus 5 workhorse, which terminated on a session limit
with all eight on disk and scoring not yet run. Scoring and this write-up were
completed from its own committed scripts by the verifier seat.

**Headline: field-realistic degradation costs 7.5 points, not 44. The 16%
figure was dominated by pitch-shift and time-stretch — two transformations that
cannot happen to a phone recording. The 0/10 on wild clips is now
*unexplained*.**

---

## 1. Gate

`GATE 1 (bit-level vs tdms_60.npz offset-0): n=518 max|diff|=0.000e+00 -> PASS`

The TDMS recomputed here from the cached contour is bit-identical to the
duration curve's own 60 s shard, so this harness is the same harness. All 518
tier tracks, 155 level-(c) source-disjoint groups, 5 folds, fold assignment
computed once and reused by every cell and every arm, so **all cells are exactly
paired**.

**The anchor is 56.3%, not 60.4%.** The prereg (§64, §92-94) registered this
explicitly: 60.4% is the duration curve's *matched* training on a *cached*
contour, whereas the primary arm here is *mismatched* — train on clean
full-track TDMS, test on the degraded 60 s window — which is the deployed
situation. The within-experiment `clean` cell at 56.3% is the paired baseline
and every delta below is against it.

## 2. Nothing failed to produce a contour. Anywhere.

| cell | windows | scored | no contour | min-voiced discard | TDMS none | tonic fail |
|---|---|---|---|---|---|---|
| every one of the eight | 518 | 517 | **0** | **0** | **0** | **0** |

The single unscored window in each cell is one `audio_unavailable` source file,
the same one throughout.

The brief predicted the opposite, in writing and in advance: *"`phone_mic`'s
high-pass corner is drawn from 120-350 Hz, and Carnatic vocal fundamentals sit
roughly 100-400 Hz. A 350 Hz corner removes the fundamental outright for most
male voices... Melodia would then be tracking harmonics or nothing."*
**Refuted.** Melodia produced a usable contour through bandpass, resample to
8 kHz and mu-law companding in all 517 windows. The brief's own rule — that
failing to produce a contour is a different finding from producing a wrong
answer — resolves entirely to the second. Whatever the damage is, it is bad
answers on present input.

## 3. Primary arm — component ablation

Mismatched, source-disjoint, top-1, n = 517 per cell. Paired
`clean − cell` deltas with a 2,000× **source-group** bootstrap.

| cell | field? | top-1 | top-3 | clean − cell | 95% CI |
|---|---|---|---|---|---|
| `clean` | — | **56.3%** | 74.5% | — | — |
| `phone` | yes | 55.9% | 75.0% | +0.4pp | −2.5 .. +4.1 |
| `reverb` | yes | 54.2% | 73.9% | +2.1pp | −0.8 .. +5.2 |
| `noise` | yes | 53.6% | 74.5% | +2.7pp | +0.0 .. +5.3 |
| **`field_all`** | **yes** | **48.7%** | 69.4% | **+7.5pp** | **+3.7 .. +12.4** |
| `pitch` | **no** | 45.6% | 67.3% | +10.6pp | +7.6 .. +13.8 |
| `stretch` | **no** | 45.3% | 68.1% | +11.0pp | +7.8 .. +14.7 |
| `all` | — | **35.0%** | 55.3% | +21.3pp | +16.0 .. +26.8 |

Three things in that table matter.

**No single field-realistic component does meaningful damage.** `phone` costs
0.4pp with a CI straddling zero. `reverb` costs 2.1pp, CI straddling zero.
`noise` costs 2.7pp with a CI whose lower bound is exactly zero. Individually,
a phone capture chain, a 0.15-0.6 s room and pink noise at 8-25 dB SNR are each
indistinguishable from no degradation at all.

**Together they cost 7.5pp — more than the sum of their parts** (0.4 + 2.1 + 2.7
= 5.2), so there is mild interaction, but the total is still small.

**Each artifact alone costs more than all three field components combined.**
`pitch` costs 10.6pp and `stretch` 11.0pp, against `field_all`'s 7.5pp. The
`all` cell, which is the condition behind the historical 12/77 ≈ 16%, costs
21.3pp — and roughly two thirds of that is transformations that do not occur in
the field.

## 4. Secondary arm — the 2×2. Tonic is a red herring.

All four arms scored on the same mismatched forests; a TDMS recomputation only,
no new audio work. `Cc/Tc` is the clean contour with the reference tonic and is
the same 56.7% cell in every row by construction.

| cell | Cc/Tc | Cd/Tc *contour damage only* | Cc/Td *tonic damage only* | Cd/Td *the cell* |
|---|---|---|---|---|
| `clean` | 56.7% | 56.7% | 56.3% | 56.3% |
| `noise` | 56.7% | 54.4% | 56.1% | 53.6% |
| `reverb` | 56.7% | 52.8% | 55.5% | 54.2% |
| `phone` | 56.7% | 53.8% | 58.2% | 55.9% |
| **`field_all`** | 56.7% | **50.5%** | 54.5% | **48.7%** |
| **`all`** | 56.7% | **37.1%** | 52.8% | **35.0%** |
| `pitch` | 56.7% | 46.6% | 54.0% | 45.6% |
| `stretch` | 56.7% | 44.9% | 54.2% | 45.3% |

For the `pitch` cell the correct tonic is analytic rather than estimated —
`tonic_ref * 2**(s/12)` with `s` the recorded `pitch_semitones` — so that row's
"clean tonic" arm is exact.

Reading it against the branches the brief fixed in advance:

- **`field_all`:** contour damage alone is −6.2pp; tonic damage alone is
  −2.2pp; the full cell is −8.0pp. Contour is **~3×** tonic.
- **`all`:** contour alone is −19.6pp; tonic alone is −3.9pp. Contour is **5×**
  tonic, and degraded-contour-with-clean-tonic (37.1%) is already
  indistinguishable from the full damage (35.0%).

That is the brief's third branch, verbatim: *"degraded-contour + clean-tonic ≈
full damage → the contour is destroyed; tonic is a red herring and no tonic work
is worth funding."* **Perfect tonic recovery would buy 2.2pp in the
field-realistic cell and 3.9pp in the worst cell.** The shruti-from-the-listener
idea, and any other tonic-estimation work, is not worth funding on this
evidence.

## 5. Tonic drift, reported before any forest was fit

Against each cell's *true* tonic, analytic for `pitch`:

| cell | median \|drift\| | p90 | ≤25c | ~700c | ~1200c |
|---|---|---|---|---|---|
| `clean` | 2.9c | 514.9c | 82.6% | 5.4% | 3.3% |
| `noise` | 3.7c | 691.2c | 80.5% | 5.8% | 4.4% |
| `reverb` | 3.7c | 701.2c | 79.5% | 7.4% | 4.3% |
| `phone` | 2.9c | 675.1c | 81.0% | 5.2% | 3.9% |
| `field_all` | 10.0c | 701.2c | 75.0% | 7.0% | 4.8% |
| `all` | 9.1c | 1196.6c | 61.1% | 12.0% | 12.6% |
| `pitch` | 7.3c | 1194.8c | 68.7% | 8.1% | 12.2% |
| `stretch` | 3.7c | 581.0c | 81.0% | 5.4% | 3.7% |

Drift in the field-realistic cells is small — a 10-cent median at `field_all`,
75% within 25 cents. **The clean cell already carries 17.4% of tonics outside
25 cents and 8.7% at a fifth or an octave**, so most of the tonic error is
pre-existing in the archive corpus, not caused by degradation. Only `all` and
`pitch` push the fifth/octave confusion materially (12% each), and those are the
non-field cells. This corroborates §4 independently of any classifier.

## 6. Confounds measured, not repaired

Voicing density moves 0.621-0.703 across all eight cells, so effective
`tau(0.1)` moves 0.142-0.161 s — a ~13% spread, and it is the two artifact
cells (`pitch`, `stretch`, both 0.621) that sit at the extreme. Too small to
explain a 21-point drop and it points the wrong way, exactly as the duration
curve found. `all` and `stretch` have real window length 56.2 s [48-60] because
time-stretching changes duration; registered in advance and confined to the two
non-field cells.

`augment_wild.py:21`'s claim that there is "No ffmpeg on this machine" remains
false — ffmpeg 8.1.2 is at `/opt/homebrew/bin/ffmpeg` — so its mu-law companding
is a proxy for a real codec that could now be used. **Recorded, not acted on:**
changing it would break comparability with the historical 12/77.

The `--fast` / Demucs tertiary was **not run**. It is reported as not run rather
than subsampled.

## 7. Verdict

**Against the interpretation table fixed in advance, `field_all` at 48.7% lands
in the top row — "≥ 45%: field-realistic degradation is survivable, the 16% was
dominated by pitch/stretch artifacts, and the 0/10 on wild clips is still
unexplained."** That is the reading taken. A phone capture chain costs 0.4
points, a room costs 2.1, pink noise costs 2.7, none of them separately
distinguishable from zero, and all three together cost 7.5 — while a ±6 semitone
pitch shift alone costs 10.6 and a time stretch alone costs 11.0. The
transformation that `augment_wild.py`'s own docstring describes as a way to
*train invariance in* was, used as a test-time degradation, the single largest
contributor to the number that has stood since 2026-07-19 as evidence that wild
audio destroys the raga path. It does not. The 2×2 closes the other half of the
question just as cleanly: contour damage outweighs tonic damage 3:1 in the
field-realistic cell and 5:1 in the worst cell, degraded-contour-with-perfect-
tonic is already indistinguishable from full damage, and most tonic error is
pre-existing in the clean corpus rather than induced by degradation — so no
tonic-estimation work is worth funding, including asking the listener for the
shruti.

**What this leaves is a gap that no longer has a mechanism.** Clean 60 s
archive windows score 56.3% mismatched; the honest simulation of a phone in a
hall scores 48.7%; real wild clips score 0/10. The simulation does not reproduce
the wild failure, so something real wild clips have is not in
`augment_wild.py` — and until that is identified, no statement of the form "the
raga path fails on wild audio because X" is supported by evidence. The most
mundane candidates should be eliminated before any expensive one: whether the
ten wild clips' true ragas were even inside the trained 18-raga tier, n = 10
itself, and the `--fast`/Demucs difference that this job registered and did not
spend.

**Scope.** This measures 60 s windows of archive-domain audio under synthetic
degradation, on the 18-raga `min_tracks >= 25` tier, mismatched training. It
graduates nothing, it does not touch `~/sung_tests --cache-v2`, and it makes no
claim about the lyrics-ASR path, whose duration KILL is a separate result on a
separate channel.

---

## 8. Artifacts

| file | what |
|---|---|
| `data/raga_domain/PREREGISTRATION.md` | registered and committed before the harness existed |
| `scripts/raga_domain_protocol.py` | inherited tier, groups, window offsets |
| `scripts/raga_domain_cells.py` | the eight degradation cells |
| `scripts/raga_domain_score.py` | gates, primary arm, 2×2, drift, bootstrap |
| `data/raga_domain/results.json` | machine-readable results |
| `data/raga_domain/cell_*.npz` | per-cell TDMS + tonic (gitignored, regenerable) |
| `data/raga_domain/score_run.log`, `cells_field.log` | raw run output |

---

## 9. Verifier addendum, same day — the mundane candidate was the answer

§7 left the wild 0/10 without a mechanism and named the cheapest candidate
first: *"whether the ten wild clips' true ragas were even inside the trained
18-raga tier."* Checked immediately, since the wild set carries its raga truth
in the filename (`Title__Raga.ext`) and `data/raga_aliases.json` folds the
spellings.

Over the whole wild set (`~/sung_tests`, audio files only):

| | count |
|---|---|
| clips with a raga label | 81 |
| **label inside the trained 18-raga tier** | **29 (35.8%)** |
| label outside it | 52 |
| `NA` or Rāgamālika (the latter dropped from training by construction) | 25 |

**Only 29 of 106 clips — 27% — have a true raga the model is capable of
emitting.** The 52 outside include Bilahari, Madhyamāvati, Kambhōji,
Jaganmōhini, Śrī, Ānandabhairavi, Kēdāram, Rēvati, Śrīranjani and Bōwli. On
those the classifier cannot be right; the answer is not in its label set.

If the ten clips behind the 0/10 were drawn like the set as a whole, the
expected number even *eligible* to be correct is ~3.6, and at the in-tier
accuracy this job measures on degraded audio (~50%) the expected hits are ~1.8.
**P(0 hits) ≈ 14% — an unremarkable draw, not a signal.**

This does not prove the raga path works in the field; it removes the evidence
that it does not. The honest position is that **the raga path has never been
measured on wild audio it could answer.** The 0/10 should stop being quoted as a
domain result, and the measurement that would replace it is a re-score on the
**29 in-tier wild clips** — small, but real, and it has never been run.

Caveat: the exact ten clips behind the historical 0/10 are not recorded, so this
is a base-rate argument about how that sample was probably drawn, not a
reconstruction of it.
