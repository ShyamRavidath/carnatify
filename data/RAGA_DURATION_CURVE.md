# Raga duration curve — how much audio does the TDMS raga path actually need?

Executed 2026-07-31 against `WORKHORSE_RAGA_DURATION_BRIEF.md`. Read-only: no
retraining of production, nothing under `models/` written, no edit to
`identify_clip.py`. The readings were registered in
`data/raga_duration/PREREGISTRATION.md` and **committed as their own commit
(`87e6555`) before the harness scripts (`570b29c`) and before a single fold was
scored** — the ordering is in git history, not in file mtimes.

Everything below is **source-disjoint**. The tier (18 ragas, `min_tracks >= 25`,
518 tracks) and the level-(c) group vector (155 source groups: archive item /
Saraga concert, artist-merged) are inherited unchanged from
`data/RAGA_CONTAMINATION_AUDIT.md` and were not re-derived or re-tuned. No
level-(a) figure was computed.

**This job says nothing about the lyrics-ASR composition path, in either
direction.** See §7.

**Headline: 72.2% full-track → 60.4% at 60 s → 52.5% at 30 s, matched and
source-disjoint. The information is partly there in a minute and the curve is
still climbing at 600 s.**

---

## 0. The reproduction gate — passed on the exact integer counts

The full-track matched cell is the audit's level (c) re-run through this
pipeline: same 518 tracks in the same order, same level-(c) groups, same
`StratifiedGroupKFold(5, shuffle=True, random_state=42)`, same
`RandomForestClassifier(800, 'sqrt', random_state=42)`, one window per track.

```
REPRODUCTION GATE (matched:full vs audit level (c) 72.2% / 84.0%): 72.2% / 84.0%  ->  PASS
                   374/518 = 72.2%      435/518 = 84.0%
```

Not "within ±0.5 pp" — the **same integer counts** as
`data/RAGA_CONTAMINATION_AUDIT.md` §3. The windowing pipeline is therefore the
audit's own harness with the time axis sliced, and every number below is
measured off the audit's own baseline rather than an approximation of it.

---

## 1. The curve — n first

**Unit is the window, not the track**, because one window is one user session.
`K = 3` random-offset windows per track per duration; offset fractions drawn
once at `random_state=42` and reused at every duration and in both conditions,
so the arms are exactly paired. 5 folds used at every cell; 155 level-(c)
groups; no raga dropped at any duration.

| duration | windows scored | discarded (`min_voiced`) | discarded (`tdms_none`) | tracks shorter than *d* | mean **real** window | **matched top-1** | matched top-3 |
|---|---|---|---|---|---|---|---|
| 30 s | 1552 | 2 | 0 | 0 | 30.0 s | **815/1552 = 52.5%** | 1127/1552 = 72.6% |
| 60 s | 1554 | 0 | 0 | 0 | 60.0 s | **938/1554 = 60.4%** | 1198/1554 = 77.1% |
| 120 s | 1538 | 0 | 0 | 8 (1.5%) | 119.8 s | **982/1538 = 63.8%** | 1223/1538 = 79.5% |
| 300 s | 1190 | 0 | 0 | **182 (35.1%)** | 285.1 s | **819/1190 = 68.8%** | 971/1190 = 81.6% |
| 600 s | 926 | 0 | 0 | **314 (60.6%)** | 496.3 s | **657/926 = 71.0%** | 760/926 = 82.1% |
| **full** | 518 | 0 | 0 | — | 785.4 s | **374/518 = 72.2%** | 435/518 = 84.0% |

Chance floors, recomputed per cell over that cell's *window* label distribution:
class-prior expectation `Σ p_i²` runs 0.0557 (30/60 s and full) to 0.0578
(600 s); majority-class rate runs 0.0580 to 0.0734. The rise at 300/600 s is
real and mechanical — short tracks contribute one window instead of three, which
shifts the window distribution — and is why the floors were registered as
per-cell rather than carried over. **52.5% at 30 s is 9.4× the class-prior
floor; 60.4% at 60 s is 10.8×.** Nothing on this curve is near chance.

### Uncertainty, computed after the cells and labelled as such

The 1,554 windows at 60 s are not 1,554 independent observations: they come from
518 tracks in **155 source groups**, and the folds are disjoint on the groups. A
binomial interval on n = 1554 would be about three times too narrow. Resampling
the **155 source groups** with replacement, 2000×:

| duration | matched top-1 | 95% CI |
|---|---|---|
| 30 s | 52.5% | 47.6 – 57.3% |
| 60 s | 60.4% | 54.8 – 65.0% |
| 120 s | 63.8% | 57.9 – 68.8% |
| 300 s | 68.8% | 62.0 – 74.5% |
| 600 s | 71.0% | 64.9 – 76.5% |
| full | 72.2% | 66.4 – 78.1% |

The cells overlap heavily, so the *paired* differences are the informative
quantity. Resampling the same groups and taking the difference within each
replicate (the arms share identical test windows, and the durations share
identical tracks):

| difference | delta | 95% CI |
|---|---|---|
| full − matched 30 s | **+19.7 pp** | +16.0 .. +23.8 |
| full − matched 60 s | **+11.8 pp** | +8.0 .. +15.8 |
| full − matched 120 s | **+8.4 pp** | +4.8 .. +12.4 |
| full − matched 300 s | +3.4 pp | −0.8 .. +8.2 |
| full − matched 600 s | +1.3 pp | −2.2 .. +4.9 |

**The shortfall at 30, 60 and 120 s is real and well outside noise. At 300 s and
600 s the shortfall is no longer distinguishable from zero.**

### The knee

The interpretation table asks for the shortest duration clearing 65% matched
top-1. **On the registered grid that is 300 s** (68.8%). 120 s reaches 63.8%
with a CI of 57.9 – 68.8%, so 120 s is *not* statistically distinguishable from
65% either — the true crossing is bracketed in **(120 s, 300 s]**. No
intermediate duration was run: the grid was fixed in the brief before any score
and adding a 150 s or 180 s point after seeing the curve would be tuning.

### The 300 s and 600 s cells are not clean points on the curve

Registered before scoring, and it matters: **35.1% of tier tracks are shorter
than 300 s and 60.6% are shorter than 600 s**, and those contribute their whole
length once rather than three windows. The 600 s cell's mean real window is
496 s, not 600 s. Disaggregating the primary read-out by window kind:

| duration | full-length (`rand`) windows | short-track (whole-track) windows |
|---|---|---|
| 120 s | 978/1530 = 63.9% | 4/8 = 50.0% (mean 85 s) |
| 300 s | 700/1008 = 69.4% | 119/182 = 65.4% (mean 203 s) |
| 600 s | 437/612 = 71.4% | 220/314 = 70.1% (mean 294 s) |

(The prereg's inventory quoted 265.9 s and 414.6 s as the mean real window at
300 s and 600 s; those are **track-weighted** means of each track's own windows.
The 285.1 s and 496.3 s above are **window-weighted**, which is the right
denominator once a short track contributes one window instead of three. Same
data, different weighting, and the window-weighted figure is the one that
matches the cells.)

Removing the short tracks moves the cells by at most +0.6 pp, so the mixture is
**not** what produces the shape of the curve. It does mean the 600 s cell should
be read as "roughly 500 s of audio", and that the 600 s and full-track cells
share a great deal of the same audio.

---

## 2. The matched / mismatched gap — is a shortfall retraining or information?

`matched` trains on windows of duration *d*; `mismatched` trains on full tracks
and tests on the identical held-out windows — it is the model we already export,
asked to work at *d* seconds. The mismatched arm gates nothing.

| duration | matched top-1 | mismatched top-1 | gap (paired) | 95% CI on the gap |
|---|---|---|---|---|
| 30 s | 815/1552 = 52.5% | 698/1552 = 45.0% | **+7.5 pp** | +5.1 .. +10.1 |
| 60 s | 938/1554 = 60.4% | 850/1554 = 54.7% | **+5.7 pp** | +2.8 .. +8.3 |
| 120 s | 982/1538 = 63.8% | 933/1538 = 60.7% | **+3.2 pp** | +1.1 .. +5.2 |
| 300 s | 819/1190 = 68.8% | 816/1190 = 68.6% | +0.3 pp | −2.6 .. +2.4 |
| 600 s | 657/926 = 71.0% | 645/926 = 69.7% | +1.3 pp | −0.6 .. +3.2 |

Top-3 behaves the same way: at 30 s, 72.6% matched against 67.1% mismatched.

**Both readings are true at once and neither cancels the other.** Retraining on
short windows is worth a real 5.7 pp at 60 s and a real 7.5 pp at 30 s — a
train/test duration mismatch is a genuine and cheaply fixable part of the
shortfall, and the exported full-track model is measurably the wrong model for a
one-minute clip. But retraining does not come close to closing the gap to
full-track: the matched arm at 60 s is still **11.8 pp below** the full-track
anchor with a CI that excludes zero. **Most of the shortfall at 30-120 s is
information that is not in the window, not a model that has not seen windows.**
Above 300 s the mismatch penalty vanishes entirely, which is the expected null
and confirms the gap at short durations is a duration effect rather than an
artefact of fitting on 3× more rows.

---

## 3. The voicing-density confound (Trap 2) — measured, deliberately not repaired

The frozen harness computes `tau = round(tau_s / hop)` in frames of the original
hop and then applies it to the **compacted voiced array**. The nominal
0.1 / 0.15 / 0.25 s delays are therefore only nominal; the true delay is
approximately `tau_s / density`, so it scales with voicing density — and if
density moved with window length, the duration sweep would be partly a *tau*
sweep in disguise. Repairing it would change the frozen harness and break
comparability with the audit, so it was left exactly as it is and measured:

| duration | n | mean density | sd | p05 – p95 | mean voiced frames | min voiced frames | effective delay for τ = 0.1 s | for τ = 0.25 s |
|---|---|---|---|---|---|---|---|---|
| 30 s | 1552 | 0.692 | 0.150 | 0.404 – 0.885 | 7,149 | 558 | 0.145 s | 0.361 s |
| 60 s | 1554 | 0.693 | 0.130 | 0.453 – 0.862 | 14,328 | 615 | 0.144 s | 0.361 s |
| 120 s | 1538 | 0.692 | 0.116 | 0.483 – 0.841 | 28,550 | 1,306 | 0.145 s | 0.361 s |
| 300 s | 1190 | 0.679 | 0.106 | 0.509 – 0.812 | 66,613 | 5,777 | 0.147 s | 0.368 s |
| 600 s | 926 | 0.671 | 0.092 | 0.536 – 0.801 | 113,991 | 13,764 | 0.149 s | 0.372 s |
| full | 518 | 0.678 | 0.066 | 0.576 – 0.783 | 181,224 | 13,764 | 0.147 s | 0.369 s |

**Mean voicing density moves by 2.2 percentage points across the whole sweep
(0.693 at 60 s to 0.671 at 600 s), so the mean effective delay moves from
0.144 s to 0.149 s — about 3%.** The confound is real, it is now on the record,
and it is roughly an order of magnitude too small to explain a 19.7 pp
difference between 30 s and full-track. It does not go the right way either:
short windows have *slightly higher* density and therefore a *slightly shorter*
effective tau, closer to the nominal value, which if anything should favour the
short cells.

The one thing that does change materially with duration is the **spread**: the
per-window density sd falls from 0.150 at 30 s to 0.066 at full-track, and the
p05 – p95 band narrows from 0.404 – 0.885 to 0.576 – 0.783. A 30-second window's
effective tau therefore varies between roughly 0.11 s and 0.25 s depending on
which passage it lands in, where a full track's is stable near 0.147 s. **Part
of what "a short window" costs this feature is not less data but a less
predictable time constant** — a mechanism, not a measurement, and it is not
tested here.

### The voiced guard

Registered before scoring as `min_voiced = 500` voiced frames per window — the
frozen harness's own track-level constant (`v.size < 500`), reused unchanged
rather than invented for this job. It bit **6 windows out of 9,366** (0.06%),
all of them at 30 s (2 random-offset, 4 from-the-start); no window at any other
duration was discarded, and `tdms_none` never fired. The lowest voiced-frame
count at 30 s among scored windows was 558 and the 5th percentile was 4,172.
**A 30-second window of this archive corpus essentially always contains enough
voiced melody to compute the feature — the shortfall at 30 s is not a
"there was nothing to measure" artefact.** The registered pre-score expectation
(density mean 0.678, so the guard should rarely bite) is confirmed.

---

## 4. Registered secondaries — non-gating

### From-the-start windows

The primary arm uses random offsets because a concert listener arrives mid-item.
The registered secondary asks what a user who opens the app when the item begins
would get. Test-only; the matched models never trained on these.

| duration | matched, from start | matched, random offset | delta |
|---|---|---|---|
| 30 s | 245/514 = 47.7% | 52.5% | −4.8 pp |
| 60 s | 295/518 = 56.9% | 60.4% | −3.5 pp |
| 120 s | 334/510 = 65.5% | 63.9% | +1.6 pp |
| 300 s | 247/336 = 73.5% | 69.4% | +4.1 pp |
| 600 s | 153/204 = 75.0% | 71.4% | +3.6 pp |

**The first 30-60 seconds of an item are harder than an average 30-60 seconds of
it, and the first 2-10 minutes are easier than an average 2-10 minutes.** The
sign flips between 60 s and 120 s. This is consistent with the opening of a
Carnatic item being a slow, sparse alapana exposition — thin at 30 s, and
strongly raga-defining once there is enough of it — but this document measures
the sign of the effect, not its cause. n is smaller here (one window per track,
and only tracks longer than *d*).

### Per-raga at 60 s matched

| raga | n windows | 60 s top-1 | 60 s top-3 | full-track top-1 |
|---|---|---|---|---|
| Kāmavardani | 90 | 76.7% | 86.7% | 80.0% |
| Nāṭa | 90 | 73.3% | 86.7% | 76.7% |
| Kamās | 87 | 72.4% | 82.8% | 72.4% |
| Pūrvīkaḷyāṇi | 78 | 70.5% | 88.5% | 96.2% |
| Kalyāṇi | 90 | 70.0% | 82.2% | 83.3% |
| Aṭāna | 78 | 69.2% | 83.3% | 80.8% |
| Sindhubhairavi | 87 | 69.0% | 80.5% | 75.9% |
| Mōhanaṁ | 90 | 68.9% | 81.1% | 83.3% |
| Tōḍi | 90 | 65.6% | 81.1% | 83.3% |
| Hamsadhvāni | 90 | 64.4% | 76.7% | 70.0% |
| Sāvēri | 90 | 55.6% | 70.0% | 63.3% |
| Ṣanmukhapriya | 87 | 55.2% | 74.7% | 72.4% |
| Śankarābharaṇaṁ | 90 | 54.4% | 70.0% | 73.3% |
| Harikāmbhōji | 87 | 50.6% | 73.6% | 65.5% |
| Bhairavi | 90 | 47.8% | 76.7% | 63.3% |
| Kānaḍa | 75 | 42.7% | 76.0% | 64.0% |
| Karaharapriya | 81 | 39.5% | 69.1% | 59.3% |
| **Vasanta** | 84 | 36.9% | 47.6% | 35.7% |

Ten of eighteen ragas hold at or above 64% top-1 on a single minute. The loss
from full-track to 60 s is not uniform: Kamās and Vasanta do not move at all,
while Pūrvīkaḷyāṇi drops 25.7 pp — it is the strongest raga on a full track
(96.2%) and only mid-table on a minute. **Vasanta remains the one genuinely weak
class at every duration**, exactly as the audit found, and it is the only raga
whose 60 s top-3 fails to clear 50%. Every track contributes windows at every
duration, so the 155 source groups and the 13-24 groups per raga are unchanged
from the audit and **no raga was dropped at any duration**; all 518 tracks are
represented in every cell.

---

## 5. Where this lands on the fixed interpretation table

The table is fixed on **matched, source-disjoint, top-1, at 60 s**:
**60.4% (938/1554, 95% CI 54.8 – 65.0%)**. That is the **45-65% row —
"partial. Report the knee of the curve — the shortest duration clearing 65% —
because that number *is* the product spec."**

The knee on the registered grid is **300 s**; the true crossing is bracketed in
**(120 s, 300 s]**, because 120 s reaches 63.8% with a CI that contains 65%.

For completeness against the other rows: the ≥ 65% row is not reached at 60 s;
the "< 45% but ≥ 65% at 300 s" row does not apply because 60 s is above 45%; and
the bottom row is excluded because 300 s and 600 s do clear 65%. Two further
facts belong with the band. **First, the matched/mismatched gap says the
shortfall at 60 s is mostly information and only partly retraining** — retraining
on 60 s windows is worth a real +5.7 pp, but the matched arm is still 11.8 pp
below full-track with a CI excluding zero, so retraining alone does not move a
minute into the top band. **Second, the curve has not flattened by 600 s**: full
minus 600 s is +1.3 pp [−2.2, +4.9], indistinguishable from zero, so the
duration effect is essentially exhausted somewhere between 300 s and full-track,
and there is no evidence here of a long-horizon statistic beyond ~5 minutes that
a clip could never have.

**The verdict on what to do with this belongs to the verifier seat.** This
document states the measurement and the row.

---

## 6. Scope — what this does not establish

- **It does not separate duration from domain.** It measures the archive/Saraga
  corpus against itself at shrinking durations, changing nothing else. The
  `0/10` on wild short clips (`handoff.md:279`) confounds duration with
  phone-mic domain; this isolates the first only. A 60 s archive window scoring
  60.4% and a 60 s phone-mic clip scoring 0/10 are consistent with each other
  and the difference between them is untested here.
- **It graduates nothing.** `~/sung_tests --cache-v2` remains the only
  scoreboard. No model was trained for production, nothing under `models/` was
  written, `identify_clip.py` was not touched.
- The level-(c) artist merge is **partial** on the archive side, inherited from
  the audit along with the group vector, so source-disjointness here is an upper
  bound on the truth and never a lower one.
- The 600 s cell measures ~496 s of mean real audio over a corpus 60.6% of which
  is shorter than 600 s, and shares much of its audio with the full-track cell.

## 7. This says nothing about the lyrics-ASR path

`HANDOFF_SESSION_0730.md:79` and `handoff.md:283` record **"Duration as a lever.
Ruled out, not merely undetected"** — top-5 5.1% @30 s → 1.7% @300 s, curve
peaking at 90 s. That was measured on **lyrics-ASR composition recall**: Whisper
transcripts matched against a title catalogue. This document measures the
**melodic-contour → TDMS → random-forest raga** channel, which shares no code,
no feature and no model with it, and it asks the opposite question — not "does
more audio help" but "how little audio is enough". **No number in this document
may be quoted as evidence about the lyrics-ASR path in either direction**, and
the fact that raga improves with duration is not a reason to revisit a lever
that was killed on a different channel.

The one prior this *does* speak to is `HANDOFF_CLIP_ID.md` §5's unquantified
"TDMS on FULL-track melody was the breakthrough (+13pt) — 65s segments are too
short for it to shine", registered in the prereg before any score. It is now
quantified: 60 s costs 11.8 pp [8.0, 15.8] against full-track, matched and
source-disjoint.

---

## 8. Artifacts

| file | what |
|---|---|
| `data/raga_duration/PREREGISTRATION.md` | readings registered and committed (`87e6555`) before the harness and before any fold |
| `scripts/raga_duration_protocol.py` | corpus, frozen tier, inherited level-(c) groups, window inventory — no score |
| `scripts/raga_duration_windows.py` | per-window multi-tau TDMS; Trap 1 handled, Trap 2 recorded verbatim |
| `scripts/raga_duration_score.py` | both arms, one fold assignment, bootstrap, aggregation |
| `data/raga_duration/protocol.json` | tier, groups, per-track offsets and contour lengths |
| `data/raga_duration/results.json` | every cell, per-kind disaggregation, voicing, paired CIs, per-raga |
| `data/raga_duration/*.log` | raw run output including the reproduction gate |
| `data/raga_duration/tdms_*.npz`, `preds_fold*.json` | gitignored (~190 MB); regenerable from the committed contours |
