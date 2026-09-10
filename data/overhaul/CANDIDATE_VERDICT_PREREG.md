# Preregistration: verdict on the context180 candidate

Registered 2026-09-10 by the tech-lead seat. **Committed before the harness
exists.** The ordering is in git history, not file mtimes.

## 0. Question

Is `context180_recovered_experiment/training` (candidate A) better than
`file_artist_strict_decode` (comparator B) by more than group-level noise, on
the same tracks, folds and groups? The September handoff reports +7.88 pp
grouped CV (76.67% vs 68.79%) and +5 known recordings on the 184-query Saraga
development set (102/139 vs 97/139), but computed no paired uncertainty.

## 1. Fixed inputs

| role | path | identity |
|---|---|---|
| A model | `data/overhaul/context180_recovered_experiment/training/raga.joblib` | SHA256 `f594584402cb2ae35532612e673c194661706fcdfe4b69bbecc69b6d50316e2b` |
| A CV | `.../training/kernel_benchmark.json`, arm `legacy_kernel_ridge`, `per_track` | hashed at run time |
| A dev | `.../training/evaluation180.json`, prediction keys `context180_recovered_estimated` / `_annotated` | hashed at run time |
| B CV | `data/overhaul/file_artist_strict_decode/kernel_benchmark.json`, same arm | hashed at run time |
| B dev | `data/overhaul/file_artist_strict_decode/evaluation180.json`, keys `strict_decode_estimated` / `_annotated` | hashed at run time |
| folds | both `folds.json`; verified identical (1,243 tracks) before registration | |
| corpus tag | A `manifest.json` row field `corpus` (archive 861 / compmusic 382) | |
| query clusters | `data/overhaul/annotated_corpus_v2.json` `artists`, folded and joined, exactly as `scripts/summarize_overhaul.py` does | 17 clusters expected |
| mixed recordings | the 8 tracks whose Saraga raga label contains "gamalika" | reported separately, never in the primary |

Verified at registration: same 1,243 tracks, same truth per track, same group
per track, identical fold assignment, 133 groups. Wins 140 / losses 42.

## 2. Gates

- **Gate 1, identity.** Track sets, truth, groups and folds must match exactly
  between A and B. Any mismatch is a blocker; nothing is repaired.
- **Gate 2, reproduction.** The harness must reproduce 953/1243 (A) and
  855/1243 (B) CV top-1 counts, 140/42 wins/losses, and 102/139 vs 97/139 on
  the dev set from the raw per-track records. A miss means the handoff's numbers
  were not what the artifacts say, and that finding outranks everything below.

## 3. Analyses, all paired, all cluster-bootstrapped (seed 42, 5,000 draws)

Uncertainty method is `paired_interval` from `scripts/summarize_overhaul.py`,
unchanged: resample clusters with replacement, ratio of summed paired
differences to summed counts. Tracks are not independent; clusters are.

- **A1** CV top-1, all 1,243 tracks, clusters = the 133 manifest groups.
- **A2** CV top-3, same.
- **A3** CV top-1 by corpus: archive (861) and CompMusic reference-pitch (382)
  separately, clusters restricted to each corpus.
- **A4** CV macro recall A vs B, and the per-class recall difference table.
  Report only; no rule.
- **B1** Dev estimated-tonic top-1, the 139 in-vocabulary queries, clusters = the
  17 primary-artist groups. Mixed-recording tracks are removed from the
  primary and reported as B1m beside it.
- **B2** Dev annotated-tonic top-1, same.
- **B3** Dev estimated-tonic top-3, same.
- **C1** OOV gate behaviour, the 45 out-of-vocabulary queries: false-accept
  count for A and B. Report only; the gate is step 3's problem.

## 4. Decision rule, fixed now

**Promote A to reference candidate** if and only if:

1. A1 95% interval lower bound is strictly above zero, **and**
2. B1 paired mean is at or above zero.

Otherwise B stays the reference and step 3 (abstain gate) is fitted on B.
Ties go to the comparator. The dev interval (B1) is *not* required to exclude
zero: 139 queries in 17 clusters cannot exclude a 3.6 pp effect and asking it to
would be a rule designed to fail.

## 5. Predictions, written so they can be refuted

- **P1.** A1 mean about +7.9 pp, interval roughly [+5, +11], excluding zero.
- **P2.** B1 mean about +3.6 pp (5/139), interval includes zero.
- **P3.** A3: the archive-corpus gain is larger than the CompMusic gain. For
  CompMusic rows only the window count and duration changed (reference pitch
  and annotated tonic in both cohorts); for archive rows the tonic and DSP
  changed too. If P3 fails, the gain is a duration/window effect, not the
  tonic/DSP match the handoff credits.
- **P4.** B2 (annotated tonic) shows a smaller A-minus-B gain than B1. The
  handoff observed estimated beating annotated for A; the paired view should
  show the same asymmetry.

## 6. What a failure means

- A1 includes zero: the 76.67% is not established over 68.79% on this data.
  The "match training context to inference context" thesis then rests only on
  five development recordings, and the reference stays B.
- Gate 2 fails: the handoff's headline numbers are wrong and must be corrected
  in `HANDOFF.md` before anything else.
- P3 fails: report it as the finding; it changes what step 5 should freeze as
  the default training frontend.

## 7. Not in scope

Field concerts (step 4), calibration (step 3), any fresh cohort. No model is
refitted. No threshold is tuned. The dev set is a development set.
