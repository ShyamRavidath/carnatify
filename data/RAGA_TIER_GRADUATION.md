# Graduating the raga tier to `min_tracks = 10`

Executed 2026-08-13 by the verifier seat against
`data/raga_tier/PREREGISTRATION.md`, which was **committed (`eb1278d`) before
the harness was parameterised and before a single fold was scored** — the
ordering is in git history, not in file mtimes.

`handoff.md` §5.2 put this on the board as a script run: retrain at
`min_tracks = 10`, admit every class, drop three dead ones. It was not a script
run, for a reason `data/RAGA_COVERAGE_CURVE.md` §8 names explicitly: **every
number on the coverage curve is TDMS-only and the exported model is fused.**
That gap had to be closed before anything could be exported.

**Headline: the graduated model is FUSED, 54 classes, and admits everything.
46.86 expected correct raga identifications per 100 heard concert items,
against 39.12 for the tier the product currently exports and 28.75 for the
narrow tier — +20% and +63%, source-disjoint, from a retrain on data already on
disk. Fusion's advantage does not shrink as the tier widens, it grows: +1.16 pp
at 18 classes, +1.21 at 32, +1.84 at 54. And the three-class drop does not
survive: its benefit reverses sign between the two arms and neither direction is
significant, so under the registered tie rule every class is admitted.**

Exported as `models/raga_v4_*`. **`models/raga_v3_*` is untouched and
`identify_clip.py` still has zero diff against `main`.**

---

## 1. Gate 1 — the parameterisation is behaviour-preserving

`scripts/raga_audit_protocol.py` hard-coded `MIN_TRACKS = 25`. It is now
reachable as an argument to `frozen_tier()`, with the default unchanged, exactly
as `scripts/raga_audit_levels.py` was parameterised for the coverage sweep.

The registered gate was not "the headline reproduces" but "**`git diff` on
`data/raga_audit/results.json` comes back empty**". The bare default run was
re-executed and the entire diff is four lines:

```
-   "fit_seconds": 22.6,      +   "fit_seconds": 24.3,
-   "fit_seconds": 23.0,      +   "fit_seconds": 24.1,
-   "fit_seconds": 22.5,      +   "fit_seconds": 24.1,
-   "fit_seconds": 22.5,      +   "fit_seconds": 23.7,
```

Wall-clock timings. **Every top-1, every top-3, every per-raga cell, every
floor, every group count, at all four levels of disjointness, is byte-identical.**
Archived at `data/raga_tier/gate1_diff.txt`; `results.json` was restored to HEAD.

## 2. Gate 2 — failed as registered, and the failure was the most useful thing here

The registered gate: the TDMS-only arm at `min_tracks = 10`, level (c), must
reproduce `data/raga_coverage/levels_min10.json`'s committed integers, **649/1139
top-1 and 812/1139 top-3**. It returned **653 and 816**.

Prereg §7.4 registered in advance that this outcome would matter more than
anything else in the job — *"the fused harness and the levels harness disagree
about the same tier, and that disagreement is a more important finding"* — so
the job stopped and isolated it (`scripts/raga_tier_gate2_diag.py`).

The two harnesses agree on the features, the tier rule, the forest, the seed,
the splitter, the level-(c) groups and the track-level read-out. They differ in
exactly one thing:

| harness | rows |
|---|---|
| `raga_audit_levels.build` (the coverage curve) | **one** row per track |
| `raga_audit_protocol.build_matrix` (the fused arm) | **three** rows per track — `d['X']`'s three augmented histogram rows, with the same TDMS vector replicated across all three (verified identical on 50 sampled tracks) |

Replication is not a no-op even for an arm that ignores the histogram: it hands
`StratifiedGroupKFold` 3,417 rows instead of 1,139, so fold boundaries can fall
differently, and it changes the forest's bootstrap draw.

Running the fused harness's own matrix **deduplicated to one row per track**:

```
replicated  (3 rows/track)   rows 3417   tracks 1139   top-1 653/1139 = 57.331%   top-3 816
deduplicated (1 row/track)   rows 1139   tracks 1139   top-1 649/1139 = 56.980%   top-3 812
committed   (levels harness)                           top-1 649/1139             top-3 812
```

**Exact, on both integers.** The harnesses do not disagree about anything; the
gap is entirely row multiplicity. Gate 2 fails as literally written and the
underlying reproduction is perfect, which is the strongest way this could have
resolved.

### What it cost to find out, and what it bought

Row replication is worth a small positive amount that **grows with tier width**:

| tier | replicated | deduplicated / committed | delta |
|---|---|---|---|
| 18 classes | 375/518 | 374/518 | +1 track, +0.19 pp |
| 32 classes | 532/826 | 529/826 | +3 tracks, +0.36 pp |
| 54 classes | 653/1139 | 649/1139 | +4 tracks, +0.35 pp |

**This is a measured noise floor for the whole audit series** — about a third of
a percentage point of pure harness bookkeeping — and every small delta in this
repo should be read against it. It is also the reason the numbers below are
quoted on the **replicated** structure: that is what `train_raga_v3_tdms.py`
actually fits, so it is the structure that describes the exported model.

**An unregistered check that landed anyway.** At `min>=25`, level (c), fused,
track-level, this harness returns **381/518** — identical to the committed
`data/raga_audit/results.json`. The fused arm reproduces its own historical
measurement exactly.

## 3. The 2×2

Level (c) source-disjoint, track-level, replicated rows.
`StratifiedGroupKFold(5, shuffle, random_state=42)`,
`RandomForestClassifier(800, max_features='sqrt', random_state=42)`,
`P = 0.6·P_tdms + 0.4·P_hist`. **Fused and TDMS-only come out of the same
forests and the same folds** — each fold fits `rf_t` and `rf_h` once, the TDMS
arm reads `pt`, the fused arm reads the combination — so the arm contrast is
exactly paired at the track level and cost nothing extra. Uncertainty is a
cluster bootstrap over that cell's own level-(c) source groups, 2,000
replicates, `default_rng(42)`.

| cell | classes | top-1 | 95% CI (cluster) | top-3 | coverage | **expected hits / 100** |
|---|---|---|---|---|---|---|
| 54, TDMS-only | 54 | 653/1139 = 57.3% | 52.9 – 62.4% | 71.6% | 79.2% | 45.40 |
| **54, fused** | **54** | **674/1139 = 59.2%** | **55.0 – 64.1%** | **72.8%** | **79.2%** | **46.86** |
| 51, TDMS-only | 51 | 657/1092 = 60.2% | 55.6 – 64.8% | 74.5% | 76.0% | 45.75 |
| 51, fused | 51 | 662/1092 = 60.6% | 56.0 – 65.4% | 73.5% | 76.0% | 46.10 |

**`54, fused` wins, and it wins on both axes of the decision:** it is the best
cell in the table, and fusion beats TDMS-only at *both* tiers, so the fusion
question and the tier question do not interact in a way that could have made the
ordering of the two decisions matter.

## 4. Fusion — the registered prediction, refuted, and refuted with a trend

Registered (prereg §7.1): *fused − TDMS at 54 classes lands in **[−2.0, +1.4] pp**,
i.e. no larger than the +1.4 pp it is worth at 18 classes.* The stated mechanism
was that the 480-dim pitch histogram is a *first-order* description of scale
content while TDMS is *second-order*, and that the classes added below
`min_tracks = 25` are disproportionately separated by gamaka and phrase rather
than by which swaras are present.

Measured: **+1.84 pp** (57.33% → 59.17%), `b = 9`, `c = 30`, **McNemar exact
p = 0.0011**. Thirty tracks flip right against nine wrong. **Refuted** — above
the band, and significantly so.

Two unregistered cells make the refutation much sharper than a single miss:

| tier | classes | TDMS-only | fused | **fusion delta** |
|---|---|---|---|---|
| `min>=25` | 18 | 72.39% | 73.55% | **+1.16 pp** |
| `min>=20` | 32 | 64.41% | 65.62% | **+1.21 pp** |
| `min>=10` | 54 | 57.33% | 59.17% | **+1.84 pp** |

**Fusion's advantage grows monotonically with tier width.** The prediction was
not merely off by 0.4 pp at one point; the direction of the whole relationship
was backwards. (The `min>=20` and `min>=25` cells were run *after* the 54-class
result, to state the improvement like-for-like rather than across arms. They are
post-hoc and labelled as such; they decide nothing.)

And the mechanism was wrong in a legible way. Fusion helps **18 classes**, hurts
**6**, and ties 30 — and its biggest single gains are on
**Hindōḷaṁ +12.5 pp** and **Śrīranjani +9.5 pp**, which are exactly the
gamaka-and-phrase classes the registered reasoning said the marginal histogram
would be useless on. Whatever the histogram is contributing at the wide tier, it
is not what I claimed it was.

Largest movers, 54-class tier:

| helped | | hurt | |
|---|---|---|---|
| Sencuruṭṭi | +16.7 pp | Mukhāri | −6.7 pp |
| Hindōḷaṁ | +12.5 | Ānandabhairavi | −5.6 |
| Ṣanmukhapriya | +10.3 | Bilahari | −4.5 |
| Maṇirangu | +10.0 | Rītigauḷa | −4.2 |
| Śrīranjani | +9.5 | Mōhanaṁ | −3.3 |

## 5. The three-class drop — refuted, and refuted by changing sign

Prereg §4 registered a break-even computed from **set membership alone, with no
model fit**: Nāṭakurinji, Janaranjani and Haṁsānandi carry 47 tracks and 3.16%
of repertoire mass, so dropping them buys top-1 by bookkeeping and costs
coverage immediately, and the drop wins only if removing three confusable
competitors helps the surviving 51 by at least **0.28 pp** beyond the
bookkeeping.

It does — in one arm, and not the other:

| arm | dropped classes carry | bookkeeping-only | **measured 51-class** | **second-order help** | break-even | verdict |
|---|---|---|---|---|---|---|
| TDMS-only | 47 tracks, 4 top-1 hits | 59.43% | **60.17%** | **+0.73 pp** | 59.71% | 51 wins by +0.45 pp |
| fused | 47 tracks, 6 top-1 hits | 61.17% | **60.62%** | **−0.55 pp** | 61.63% | 51 loses by −1.01 pp |

On expected hits: TDMS-only **+0.34** for the drop, fused **−0.77** against it.
Neither is significant — McNemar exact **p = 0.31** (TDMS) and **p = 0.46**
(fused), on 1,092 shared tracks.

**The sign of the second-order effect flips between two arms of the same model
on the same folds, and neither direction clears significance.** The honest
reading is that removing three near-dead classes does nothing measurable to the
survivors on this corpus, and the whole decision reduces to the bookkeeping,
which §4 already showed was a coin flip.

The registered rule (prereg §5) is therefore decisive and was fixed before any
of this existed:

> **Ties go to admitting everything.** A drop that does not pay must not be
> taken, because it forfeits 95 repertoire items for nothing and each dropped
> class is a thing the product can never say.

**All 54 classes are admitted.** `handoff.md` §5.2's "drop only Nāṭakurinji,
Janaranjani and Haṁsānandi" is **not** carried out, and the reason is measured
rather than argued.

This also closes the last live remnant of the admission idea. `data/RAGA_COVERAGE_CURVE.md`
§11.4 concluded that the *defensible* version of per-class admission is the
narrow one — drop the handful of classes that are stably near-zero out of
sample. Priced properly, **even the narrow version does not pay.**

## 6. What was exported

```
venv/bin/python train_raga_v3_tdms.py --min-tracks 10 --out-prefix raga_v4
  training on 54 ragas, 1139 tracks, 3417 samples
```

The track, class and row counts match the measured cell exactly.

| file | tracked? |
|---|---|
| `models/raga_v4_tdms_rf.pkl` (383 MB) | no — gitignored, regenerable in ~7 min |
| `models/raga_v4_hist_rf.pkl` (853 MB) | no — same |
| `models/raga_v4_label_encoder.pkl` | yes |
| `models/raga_v4_meta.json` | yes |

**`models/raga_v3_*` was not overwritten**, deliberately:
`data/RAGA_WILD_MEASUREMENT.md`, `data/RAGA_DURATION_CURVE.md` and
`data/RAGA_DOMAIN_DECOMPOSITION.md` all scored against it, and overwriting it
for a naming convenience would invalidate their provenance.

`train_raga_v3_tdms.py` gained `--out-prefix` (default `raga_v3`, so the bare
command is unchanged) and its metadata was repaired. `handoff.md` §2c-i flagged
that both the docstring and `raga_v3_meta.json`'s `cv_note` still carried
`min>=20 67.6/79.4` — **a level-(a) TDMS-only figure attached to a fused model,
wrong on both counts, and inflated by 3.5 pp at that tier.** Both now carry the
source-disjoint fused numbers keyed by tier, with an explicit note that a tier
off the measured grid gets **no** accuracy figure rather than a borrowed one.

## 7. Predictions, scored

| # | registered | measured | verdict |
|---|---|---|---|
| 1 | fused − TDMS at 54 classes in [−2.0, +1.4] pp | **+1.84 pp**, p = 0.0011 | **refuted** — and the trend across three tiers runs the opposite way to the stated mechanism |
| 2 | the drop lands within ±1.0 expected hits of 54 and does not clear the bar; point 44.9–45.6 | fused **46.10** vs 46.86 (−0.76); TDMS **45.75** vs 45.40 (+0.34) | **direction confirmed, point band refuted** — it does not clear the bar, but both cells sit above the 44.9–45.6 band because fusion lifted the whole table |
| 3 | top-3 favours keeping all 54 more clearly than top-1 does | expected top-3 hits 57.64 vs 55.91 (−1.73) against top-1's −0.76 | **confirmed** |
| 4 | Gate 1 passes and Gate 2 passes | Gate 1 **passed**; Gate 2 **failed** and was diagnosed to exact agreement | **half refuted** — and §7.4's registered contingency ("that disagreement is a more important finding than anything else in this job") is what actually happened |

Two of four registered predictions were wrong. Both are recorded here rather
than quietly restated, because the bands were fixed before the numbers existed.

## 8. Scope — what this does not establish

- **It does not measure the wide tier in the field.** Every number here is
  full-track corpus audio. `data/RAGA_WILD_MEASUREMENT.md`'s 59.3% is 18-class,
  and the 11 long-form concerts are frozen but unlabelled and unscored. A wider
  tier puts far more wild clips in scope; **nothing here says what the field
  accuracy on them would be.**
- **It does not measure the wide tier at short duration.** The duration curve is
  18-class. The tier × duration interaction remains unmeasured, and a companion
  working on minute-scale audio at 54 classes still has no measurement in this
  repo. This is the single largest hole left in the raga case.
- **It graduates nothing into the product.** `identify_clip.py` is untouched and
  has zero diff against `main`. Wiring `raga_v4_*` in, pushing and deploying are
  Deepti's.
- **The level-(c) artist merge is partial** on the archive side, inherited
  unchanged from the audit, so source-disjointness is an upper bound on the
  truth and never a lower one — equally at every tier, so the comparisons
  between tiers are unaffected.
- **Coverage is a proxy.** Repertoire mass is a prior over scraped concert
  programmes. It is the right prior for a concert companion and it is still a
  proxy, and it prices a wrong answer and a "raga not in vocabulary" identically
  at zero. A listener may not. **That is the abstain gate's axis**
  (`handoff.md` §5.5), it is untouched here, and it is the correct place to buy
  safety — not the tier, which buys it only by refusing to answer on 61% of the
  repertoire, silently and unconditionally.
- **Nothing here reopens the composition doors.** No number in this document may
  be quoted as evidence about the lyrics-ASR, Qmax or CSI paths in either
  direction.

## 9. Artifacts

| file | what |
|---|---|
| `data/raga_tier/PREREGISTRATION.md` | registered and committed (`eb1278d`) before the harness was touched |
| `scripts/raga_tier_score.py` | the 2×2; fused and TDMS from the same forests and folds |
| `scripts/raga_tier_gate2_diag.py` | the row-multiplicity diagnosis |
| `data/raga_tier/results.json` | every cell, per-class, per-track correctness, McNemar |
| `data/raga_tier/gate2_diagnosis.json` | replicated vs deduplicated, against the committed integers |
| `data/raga_tier/posthoc_min20_min25.json` | the two unregistered tiers, labelled post-hoc |
| `data/raga_tier/gate1_diff.txt` | the four-line timing-only diff |
| `data/raga_tier/*.log` | raw run output including both gates verbatim |
| `models/raga_v4_meta.json` | the exported model, carrying its own source-disjoint numbers |
