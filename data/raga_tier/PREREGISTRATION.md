# Preregistration — graduating the raga tier to `min_tracks = 10`

Registered by the verifier seat on **2026-08-13**, against `handoff.md` §5.2.
**Committed before the harness is parameterised and before a single fold is
scored.** House standard: the ordering is in git history, not in file mtimes.

This document fixes every reading, every gate, every arm and the decision rule
*before* any number exists. Anything not written here and later reported is a
post-hoc addition and must be labelled as one.

---

## 0. What is being decided, and what is already closed

`data/RAGA_COVERAGE_CURVE.md` established, source-disjoint, that expected
correct raga identifications per 100 heard concert items rises monotonically
with tier width — 28.2 at 18 classes to **45.1 at 54** — and that the incumbent
18 classes pay only 3.5 pp for it (McNemar exact `p = 0.0096`). `handoff.md` §5.2
therefore puts "retrain at `min_tracks = 10` and admit every class" on the board
as the cheapest real product improvement available: zero new data, zero dollars.

**Closed, and not reopened here:**

- The curve itself. Four tiers, level (c), committed. This job does not re-measure
  them and may not re-tune `min_tracks` away from 10 on the strength of anything
  it finds.
- **Per-class admission thresholds are dead** (`data/RAGA_COVERAGE_CURVE.md` §11,
  `handoff.md` §4.9). Expected hits fall monotonically at every threshold tested.
  No threshold sweep is run here and none may be introduced.
- The features, the taus, `nb`, `sigma`, `alpha`, the forest, the splitter and
  the seed. Every one is inherited unchanged.

**What is genuinely open, and is what this job exists to settle:**

1. **Does fusion still help at 54 classes?** The exported model is *fused*
   (`P = 0.6·P_tdms + 0.4·P_hist`). Every number on the coverage curve is
   **TDMS-only**. `data/RAGA_COVERAGE_CURVE.md` §8 says so explicitly: *"Whether
   fusion's advantage holds, grows or shrinks with tier width is not measured
   here."* At 18 classes, level (c), fusion is **+1.4 pp top-1 and −0.4 pp top-3**
   (73.6/83.6 against 72.2/84.0). **A fused wide-tier model cannot be exported on
   the strength of a TDMS-only measurement.** This is the gap that makes the
   retrain a measurement rather than a script run.
2. **Do the three stably-dead classes come out?** `handoff.md` §5.2 says to drop
   Nāṭakurinji, Janaranjani and Haṁsānandi. §4 below shows this is **within
   0.3 pp of break-even** and therefore has to be measured.

## 1. Provenance of the three names — why this is not selection on noise

The trap that killed the admission sweep (`data/RAGA_COVERAGE_CURVE.md` §11.3) is
selection on the folds you then score on: worth **4.4 pp** of pure inflation at
matched coverage on this corpus.

These three names do not come from that. They are the classes that were **never
admitted in any of the five outer folds** by the *nested* arm at `t = 0.10`,
where each fold's admitted set came from an inner 5-fold group CV over that
fold's **training rows only**. The selection for a fold never saw the fold.

**The residual leak, registered rather than argued away.** Fixing one global set
of three names across all five outer folds does let information from fold *k*'s
test rows reach fold *k*'s class set, via the other four folds' inner selections.
The effect is bounded by three classes of 54 and by the fact that all three are
at or near zero out of sample in every fold, but it is not zero, and the
51-class figures below are therefore **very slightly optimistic by an unmeasured
amount**. Registered now so it cannot be discovered later.

## 2. Gates. Any failure stops the job; none is repaired by editing a frozen file

**Gate 1 — the parameterisation is behaviour-preserving, not merely
number-preserving.** `scripts/raga_audit_protocol.py` hard-codes
`MIN_TRACKS = 25`. It is being made reachable as an argument, exactly as
`scripts/raga_audit_levels.py` was for the coverage sweep. The bare default run
must rewrite `data/raga_audit/results.json` and **`git diff` on it must come back
empty** — every level, both read-outs, every per-raga cell, byte for byte. A run
that reproduces the headline but perturbs a per-raga cell **fails**.

**Gate 2 — the TDMS-only arm at `min_tracks = 10` reproduces the committed
integers.** `data/raga_coverage/levels_min10.json` records level (c) as
**649/1139 top-1 and 812/1139 top-3**. Not "within ±0.5 pp" — the same integers.
This gate is what makes every fused-versus-TDMS delta below a comparison against
the committed measurement rather than against an approximation of it.

**Gate 3 — the tier is computed on full level-(a) track counts and never
re-tuned.** `min_tracks = 10` selects 54 classes. The class set is fixed by that
rule alone, before any fold; the three-name drop is applied *after* the tier, as
a named list, never as a threshold.

**Gate 4 — nothing that a committed measurement reads is modified.**
`data/raga_aliases.json`, `data/raga_wild/`, `data/raga_audit/PREREGISTRATION.md`,
`data/raga_coverage/`, `models/raga_v3_*` are read-only to this job. The new
model is exported under a **new name** (§6) precisely so that
`data/RAGA_WILD_MEASUREMENT.md`'s provenance — which scored the 32-class fused
`raga_v3_*` — stays intact.

## 3. Arms and read-outs, fixed

Level **(c), source-disjoint, track-level** throughout — the level and read-out
the coverage curve is stated on. Level (a) is computed only as a diagnostic and
is never quoted as a headline (`handoff.md` §2c-i: any raga figure at
`min_tracks >= 20` or wider measured at level (a) is inflated by 3.5-4.7 pp).

Four cells, the full 2×2, all reported whichever way the result lands:

| | **54 classes** | **51 classes** (three named dropped) |
|---|---|---|
| **TDMS-only** | committed: 649/1139, 812/1139 (Gate 2) | to measure |
| **fused** `0.6/0.4` | to measure | to measure |

Reported for every cell: top-1 and top-3 as integer counts over the denominator,
repertoire coverage, **expected hits per 100 heard items**, per-class top-1, and
a 95% cluster bootstrap over that cell's own level-(c) source groups — 2,000
replicates, `default_rng(42)`, percentile interval, the method
`data/RAGA_COVERAGE_CURVE.md` §2 and `data/RAGA_DURATION_CURVE.md` §1 both used,
because the tracks are not independent.

**Paired comparisons**, exact McNemar on the discordant pairs:
fused against TDMS-only at 54 classes, on the 1,139 shared tracks; and 51-class
against 54-class on the **1,092 tracks the two share**, in the arm that wins §5.

## 4. The break-even, computed from set membership alone, before any fold

This is arithmetic over `data/scraped_compositions.json` and the committed
per-class counts. No model is fit to produce it. It is registered here because
it makes the decision rule falsifiable in advance.

| class | tracks | (c) groups | top-1 | top-1 hits | repertoire items | mass |
|---|---|---|---|---|---|---|
| Nāṭakurinji | 11 | 8 | 0.0% | 0 | 32 | 1.06% |
| Janaranjani | 15 | 10 | 6.7% | 1 | 32 | 1.06% |
| Haṁsānandi | 21 | 11 | 14.3% | 3 | 31 | 1.03% |
| **combined** | **47** | — | — | **4** | **95** | **3.16%** |

Dropping them removes 47 tracks that carry 4 top-1 hits, so if the surviving 51
classes are helped **not at all**, top-1 goes `649/1139 = 56.98%` →
`645/1092 = 59.07%`, **+2.09 pp** — while coverage falls `79.20% → 76.04%`,
**−3.16 pp**.

```
expected hits/100  =  coverage × top-1
54 classes:  0.79196 × 0.56980  =  45.13
51 classes:  0.76039 × top-1(51)
break-even:  top-1(51) ≥ 59.35%     i.e. +2.37 pp over the 54-class figure
arithmetic alone:      59.07%       i.e. +2.09 pp
                       ---------------------------------------------
                       SHORT BY 0.28 pp
```

**So the drop wins if and only if removing three confusable competitors buys the
surviving 51 classes at least 0.28 pp of top-1 beyond the bookkeeping.** That is
a small number and it is genuinely uncertain in both directions. Same arithmetic
on top-3: break-even 74.25%, bookkeeping 73.44%, short by 0.81 pp.

## 5. The decision rule, fixed now

Stated on **expected hits per 100 heard items, level (c), track-level, in the
fusion configuration that wins §3** — the product-relevant quantity
`data/RAGA_COVERAGE_CURVE.md` §3 and `handoff.md` §7 both insist on, not top-1.

| outcome | decision |
|---|---|
| 51-class expected hits **>** 54-class by more than the cluster-bootstrap noise | export **51 classes**; the drop is real |
| the two are **within noise of each other** (the expected case, given §4) | export **54 classes** — admit everything. A drop that does not pay must not be taken, because it forfeits 95 repertoire items for nothing and each dropped class is a thing the product can never say |
| 51-class expected hits **<** 54-class | export **54 classes**; §4's arithmetic was decisive and the drop is refuted |

**Ties go to admitting everything.** Registered now so that a near-tie cannot be
read afterwards as support for whichever option the write-up prefers.

Fusion is decided the same way and separately: **the exported model is fused if
and only if fused beats TDMS-only on expected hits at the tier that wins.**
Fusion is not free — it doubles the forests and requires the Demucs+pyin
histogram front end at inference — so a tie there goes to **TDMS-only**, which is
the simpler product and the arm every committed number in this series is stated
on.

## 6. What is exported, and what is deliberately not touched

- New files: `models/raga_v4_tdms_rf.pkl`, `models/raga_v4_hist_rf.pkl` (only if
  fusion wins), `models/raga_v4_label_encoder.pkl`, `models/raga_v4_meta.json`.
- **`models/raga_v3_*` is not overwritten.** `data/RAGA_WILD_MEASUREMENT.md`, the
  duration curve and the domain decomposition all scored against it; overwriting
  it would invalidate their provenance for a file-naming convenience.
- **`identify_clip.py` is not touched.** It has zero diff against `main` and
  nothing in this series has touched the production path. Wiring v4 into the
  product is a separate decision and it is Deepti's.
- `raga_v4_meta.json` carries the **source-disjoint** numbers and says which arm
  and which level they are. It does not repeat `raga_v3_meta.json`'s error of
  attaching a TDMS-only level-(a) figure to a fused model (`handoff.md` §2c-i).

## 7. Predictions, written down so they can be refuted

Registered before any fold is scored. These are predictions, not targets, and
nothing is tuned to hit them.

1. **Fusion's advantage shrinks at the wide tier, and may reverse.** Registered
   band: fused − TDMS at 54 classes lands in **[−2.0, +1.4] pp** top-1, i.e. no
   larger than the +1.4 pp it is worth at 18 classes. Mechanism: the 480-dim
   pitch histogram is a *first-order* description of scale content, while TDMS is
   *second-order* (transitions). The 36 classes added below `min_tracks = 25`
   are disproportionately ones separated by gamaka and phrase rather than by
   which swaras are present — Kāṁbhōji against Harikāmbhōji, Śrīranjani against
   Ābhōgi, Dhanyāsi against Śuddadhanyāsi — so the marginal histogram should
   carry relatively less of the discrimination as the tier widens.
2. **The three-class drop lands within ±1.0 expected hits of the 54-class
   figure, and therefore does not clear §5's bar.** Point prediction: **44.9 to
   45.6**, against 45.13. I expect the second-order help to the survivors to be
   real but under half a percentage point.
3. **Top-3 will favour keeping all 54 more clearly than top-1 does**, because the
   dropped classes' top-3 hits (10) are proportionally larger than their top-1
   hits (4) — §4's top-3 break-even is short by 0.81 pp against top-1's 0.28.
4. **Gate 1 passes and Gate 2 passes.** If Gate 2 fails, the fused harness and
   the levels harness disagree about the same tier, and that disagreement is a
   more important finding than anything else in this job.

## 8. What this job does not establish

- **It does not measure the wide tier in the field.** Every number here is
  full-track archive/Saraga corpus audio. `data/RAGA_WILD_MEASUREMENT.md`'s
  59.3% is 18-class and the 11 long-form concerts are unlabelled and unscored.
  A wider tier puts more wild clips in scope; **nothing here says what the field
  accuracy on them would be.**
- **It does not measure the wide tier at short duration.** The duration curve is
  18-class. The two-way interaction between tier width and duration remains
  unmeasured, and a companion working on minute-scale audio at 54 classes still
  has no measurement in this repo.
- **It graduates nothing into the product.** It exports a candidate. Wiring,
  pushing and deploying are Deepti's.
- **Nothing here reopens the composition doors.** No number in this document may
  be quoted as evidence about the lyrics-ASR, Qmax or CSI paths in either
  direction.

## 9. Artifacts this job will produce

| file | what |
|---|---|
| `data/raga_tier/PREREGISTRATION.md` | this file, committed before the harness is touched |
| `scripts/raga_tier_score.py` | the 2×2, cluster bootstrap, expected hits, McNemar |
| `scripts/raga_tier_export.py` | trains and exports the winning configuration |
| `data/raga_tier/results.json` | every cell, per-class, machine-readable |
| `data/raga_tier/*.log` | raw run output including both gates verbatim |
| `data/RAGA_TIER_GRADUATION.md` | the write-up and the decision |
