# Carnatify architecture audit and execution report

> **Current status, September 8:** This document preserves the initial audit;
> its original benchmark and labeling recommendation below are superseded by
> [OVERHAUL_EXECUTION.md](OVERHAUL_EXECUTION.md). No new manual labeling is
> required for the current workflow. Existing expert annotations and public
> annotated corpora supply supervision and evaluation; automated predictions
> are not being substituted for ground truth. Fresh known-raga evaluation is
> 19/29 for the combined candidate versus 17/29 for the matched strong RF.
> Cross-rendition song retrieval is 19/27, with unresolved open-set rejection.
> These small tests do not establish state-of-the-art production performance.

> Follow-up correction: the original [TDMS paper](https://archives.ismir.net/ismir2016/paper/000030.pdf)
> explicitly removes unvoiced frames. The timing behavior described below is an
> intentional voiced-time representation in that method, not an unconditional
> algorithmic bug. Calling it a defect without this qualification overstated the
> finding. Wall-clock delay claims still require elapsed-time features. The two
> representations are now compared empirically. See `OVERHAUL_EXECUTION.md` for
> the active overhaul, including removal of new manual labeling as a prerequisite.

## Outcome

Confirmed DSP, data-ingestion, model-lifecycle and source-resolution defects
were repaired. A versioned, reproducible candidate pipeline and an independent
long-concert scorer now run locally. **The state-of-the-art performance target
has not been reached.** The corrected candidate did not beat the paired legacy
baseline, so it has not replaced any existing model or been deployed.

**Current verdict: stop the new manual labeling task; it is not a prerequisite
for this overhaul.** Existing labels remain valuable and have been preserved.
Public, already-annotated audio supports automatic preparation and independent
evaluation. This sidesteps additional labeling, but does not mean Demucs, tonic
estimation or self-supervised predictions can create trustworthy ground truth.

## 1. System topology

The repository is not one neural training/inference system. It contains several
incompatible generations, plus an untracked staging copy used by local backend
imports. There is no active distributed PyTorch training system to tune.

| Path | Actual computation | State before this work |
|---|---|---|
| `backend/main.py` legacy routes | separation + pYIN + 480-D pitch features + sklearn raga model; DTW/L2 composition matcher | Older deployed-code path, not the v4 model |
| Root `identify_clip.py` | multi-ASR lyrics matching; separate 60-second TDMS RF with a maximum-confidence search across 12 tonic rotations | Current local composition CLI; no whole-concert item segmentation |
| `train_raga_v3_tdms.py` and v4 artifacts | full-contour TDMS RF plus 65-second pYIN/Demucs histogram RF, posterior fusion | Stronger offline candidate family, distinct from the clip RF |
| `src/carnatify/ml/raga_model.py` / trainer | small 1-D CNN or PCD MLP | Generic legacy neural framework, not the principal live classifier |
| `colab_train_cnn.ipynb` | custom CNN on tonic-rolled CQT; track-grouped split; weighted cross-entropy | Recorded unsuccessful experiment; not an ImageNet backbone |
| `scripts/raga_*` audit family | increasingly strict grouped evaluation, domain and duration probes | Valuable historical evidence, not a single executable production pipeline |
| `scripts/long_concert_labels.py` | parse starts, infer ends, check vocabulary, write JSON | No downstream long-concert inference/scoring consumer existed |

New executable development path:

```text
archive raw contour + tonic + source provenance
  -> manifest, source/artist groups unioned with duplicate-recording groups
  -> deterministic 60-second windows, shared versioned features
  -> paired source-disjoint evaluation
  -> separate candidate bundle
  -> bounded audio decoding -> mixed-audio tonic/Melodia -> same feature function
  -> timestamped uncalibrated candidate scores / extraction abstentions

human labels + explicit exclusions -> held-out interval manifest
timestamped predictions + frozen audio/model hashes -> independent item scorer
```

The production target additionally needs automatic music/nonmusic and item
boundary detection, stable evidence accumulation over an item, calibrated
out-of-vocabulary rejection, and a composition system validated across genuinely
different renditions. These capabilities are not supplied by fixed windows.

## 2. Critical flaws and silent failures

Line references below point to the working tree after repairs; the report
distinguishes repaired code from retained artifact-compatible legacy behavior.

| Severity | Location | Finding and disposition |
|---|---|---|
| P0 evaluation | `scripts/long_concert_labels.py:123`, original parser in `validate` | User followed the space-aligned example, but parser required tabs. Completed rows became unknown concert IDs or empty labels. Repaired mixed-format parsing; eight items recovered from three concerts. |
| P0 evaluation | `scripts/long_concert_labels.py:254` | Next-start/file-end inference ignored explicit endings and tani in notes. On partial concert 3 it could extend Kalanidhi from 39:39 to the 91.6-minute file end. Old output is now explicitly not scoring-ready; the new scorer requires reviewed explicit intervals. |
| P0 compatibility | `backend/main.py:52`, `backend/clip_identify.py:30` | Bundled copies shadowed the actual checkout. Fixed checkout resolution, retaining bundled behavior for a standalone Space. Actual import smoke verified root matcher, root package and root model. |
| P1 DSP | `src/carnatify/audio/feature_extractor.py:71`, `:95` | Audio resampled to configured rate, but Essentia algorithms assumed default 44,100 Hz. At 22,050 Hz a 220-Hz test tone produced ~440-Hz pitch. Explicit sample-rate parameters repair pitch to ~220 Hz. |
| P1 DSP | `src/carnatify/audio/feature_extractor.py:141` | Zero cents meant both genuine Sa and silence; PCD dropped Sa. Extraction now passes the Hz-derived voicing mask. Mask-free private calls preserve their historical convention. |
| P1 feature semantics | `src/carnatify/ml/raga_features.py:69`, `:76` | Repeated advanced-index `+=` operations do not accumulate repeated transitions. The purported transition frequencies act like occupied-cell indicators. Corrected `np.add.at` features live in `melody_features.py`; old vectors remain unchanged for old pickles. |
| P1 timing | `train_raga_v3_tdms.py:80`, `identify_clip.py:988`, copied TDMS implementations | Removing unvoiced frames before applying time delays turns elapsed time into compressed voiced time. Corrected candidate preserves elapsed time and requires a continuously voiced span for each counted transition. Paired benchmark did not establish an accuracy gain. |
| P1 labels/features | `src/carnatify/ml/raga_dataset.py:172` | Default augmentation randomly rotated tonic-relative PCD bins while retaining the raga label. Removed this transform from the default PCD augmentation. Legacy transform remains explicitly callable; contour-offset augmentation is still a separate legacy concern. |
| P1 leakage | `train_raga.py:84`, `train_raga_v2_evaluate.py:101`, notebook stage 4 | Old StratifiedKFold lacks source groups; later track grouping keeps augmentations together but does not necessarily keep whole concerts or duplicate renditions together. Historical source-group audit exists. New pipeline uses source/artist groups and additionally unions duplicate contours across uploads. |
| P1 noisy supervision | New manifest construction | Six archive records had identical contour files but conflicting raga labels. Excluded from candidate supervision before feature extraction. Two more lacked required contour/source information. |
| P1 model lifecycle | `src/carnatify/ml/raga_trainer.py:137` | Early stopping saved the best checkpoint but returned/evaluated the final in-memory epoch. Restores best weights before reporting confusion matrix. Dedicated regression verifies this. |
| P2 device execution | `src/carnatify/ml/raga_model.py:68` | `predict` created CPU input regardless of model device. Inputs now follow the model device. Weight-only state loading is explicit. GPU hardware execution itself was not exercised. |
| P2 audio ingestion | `src/carnatify/audio/utils.py:21`, existing `librosa.load(... mono=True)` call sites | Channel averaging can cancel anti-phase stereo; full-file loaders can allocate hours of audio. Added bounded native-rate reads, explicit sample layout, finite-input checks, clipping/RMS diagnostics, and strongest-channel fallback when mean power collapses. Used by the candidate; not retroactively applied to historical caches. |
| P2 cache provenance | `raga_v2_pipeline.py:124`, `scripts/raga_coverage_matrix.py:37` | Existence-only cache reuse can survive changed code, audio or tonic rules. New run records input hashes, contour hashes, feature version and manifest hash and rejects a changed manifest at fit time. Historical caches remain untouched. |

### Tonic, windowing and architecture interpretation

Absolute pitch is **not** the principal demonstrated failure: existing principal
features already divide pitch by a tonic. However, median voiced F0 remains a
fallback in `raga_v2_pipeline.py:167` and backend code; that statistic does not
establish musical Sa. The root clip classifier also selects whichever of 12
tonic rotations maximizes classifier confidence (`identify_clip.py:1036`), which
can select a different modal interpretation. Neither practice was enabled in
the new candidate. It estimates tonic on the mix and records extraction failures.

Essentia documents `sampleRate=44100` as the default and identifies tonic from
multipitch salience, not the median melody note. A pure sine cannot uniquely
establish the musical tonic octave. The old sine test conflated that ambiguity
with the genuine pitch-rate defect; it now independently checks pitch frequency
and octave-equivalent tonic. [Essentia reference](https://essentia.upf.edu/reference/std_TonicIndianArtMusic.html)

Fixed crops need not coincide with every tala cycle for raga recognition to be
possible. The demonstrated risks are mixed ragas, nonmelodic material, short
evidence and wrong item labels. Current training assumes each archive track is a
single-raga item; this assumption has not been verified by listening to all
tracks. Voicing thresholds do **not** reliably distinguish speech, instruments,
applause, tuning and tani. No nonmusic classifier is claimed here.

The leading models are Random Forests, not transformer heads or copied ImageNet
networks. Consequently gradient/loss diagnosis does not explain their field
accuracy. The neural notebook does have class-weighted CE; the generic trainer
does not. The new candidate uses balanced-subsample forests with equal total
window weight per track. No unsupported hierarchical loss was introduced:
janya/parent relationships alone are insufficient to define the correct penalty
between ragas sharing swaras but differing in characteristic phrases.

### Taxonomy and composition constraints

The global alias map is not safe ground truth. Examples include
`kalAnidhi -> Kalyāṇi` (`data/raga_aliases.json:454`) and the previously disputed
`garuDadhwani` mapping. The new held-out manifest keeps the user's Kalanidhi
label separate and does not use fuzzy nearest-raga substitution. Corpus
membership and model membership are separately checked: Dhenuka has no output
class in this candidate. The eight human rows are not converted to training data.

Historical evidence already invalidated Qmax's apparent ~60% composition
accuracy: the source-disjoint result was 9.5%, with many apparent hits identical
to their query recordings. See `data/QMAX_CONTAMINATION_AUDIT.md`. Lyrics ASR,
CoverHunter and short-contour alternatives have their own failed evaluation
records in `HANDOFF_CLIP_ID.md` and the later handoffs. A new architecture alone
cannot establish cross-rendition composition performance when the evaluation
corpus barely contains independent renditions. No composition accuracy improvement
is claimed from this session.

### Cruft and audit coverage

The first AST scan covered 218 Python files outside environments/dependencies;
the persisted post-change inventory covers 223. It records every parsed import,
call and definition, along with exact file duplicates. The initial scan found
multiple copied TDMS functions and four exact root/scratch experiment duplicates.
The final inventory has 19 duplicate groups, mostly the untracked backend staging
package. Staging source divergence was resolved by import routing, not deletion.

Three `.py` files do not parse as ordinary Python: `colab_asr_finetune.py:54`,
`colab_asr_sprint.py:21`, `colab_indic_asr.py:21`. They contain notebook shell
magics and are not working local CLIs. CQT notebook cells were also inspected.
Hardcoded home paths remain in historical train/lyrics/audit scripts. Both venvs
are used by existing workflows; neither was classified as abandoned or deleted.
The inventory is a static navigation artifact, not a claim that every historical
script or external deployment was executed.

## 3. Labeling verdict

**Continue. The labeling is useful evaluation work, not a training task that has
already improved the classifier.** Before this session only the label validator
consumed it. The scorer was missing. That missing downstream path is now built.

Eight original items are preserved. Six have high confidence and explicit usable
boundaries; the first has two intervals around its tani. Two items remain
diagnostic: Hamir Kalyani has an approximate/muted ending, and Kalanidhi lacks a
confidence value. The source TSV was not edited. No raga was guessed from model
output. Partial concerts are valid; unlabeled tails remain unknown.

Continue noting start, end, raga, confidence, and interruption intervals. Alapana
can be useful raga evidence but should receive its own correct raga boundary, not
inherit the preceding item's label. Song names help future composition evaluation.
The practical instructions are in `data/architecture_audit/README.md`.

Demucs is already used by existing pipelines. The historical wild raga ablation
reports 51.7% versus 55.2% for mix, not a win (`data/RAGA_WILD_MEASUREMENT.md`).
MERT is a plausible representation experiment, not an automatic Carnatic label
oracle. Its paper establishes general music representation results; it does not
validate this repo's live-concert task or eliminate independent evaluation labels.
[MERT paper](https://arxiv.org/abs/2306.00107)

## 4. Actions and measured results

### Paired development benchmark

1,009 archive tracks, **934 distinct contour-file hashes**, 51 classes, 175
source/artist/duplicate groups, 3,017 deterministic windows. Ten windows rejected
for inadequate melody. Five folds split at track level with all source groups
kept disjoint. Same folds, RF settings, 64 trees, seed 42 and track-balanced
window weights for all arms. Metrics average window posteriors into one result
per track. Duplicate track IDs representing one recording stay in one group;
track-weighted metrics still count those separate IDs. Confidence intervals
resample source groups, not windows.

| Arm | Top-1 | Top-3 | Macro recall | Top-1 source-cluster 95% interval |
|---|---:|---:|---:|---:|
| Legacy compressed-time TDMS | 465/1009 = **46.09%** | 657/1009 = 65.11% | 41.76% | 41.78–51.63% |
| Corrected elapsed-time TDMS | 450/1009 = **44.60%** | 642/1009 = 63.63% | 40.46% | 40.74–49.26% |
| Corrected histogram + TDMS | 451/1009 = **44.70%** | 644/1009 = 63.83% | 41.27% | 40.87–49.37% |

Majority baseline: **2.97%**. Corrected fusion minus legacy: **−1.39 percentage
points**, paired source-cluster 95% interval **[−3.65, +1.03] pp**. No demonstrated
improvement. This candidate remains unpromoted. Correct semantics may still be
necessary for future duration-aware modeling, but they did not buy accuracy here.

This is a new **archive-only, 60-second, 51-class development benchmark**, not a
rerun of the prior 18/32/54-class full-recording or wild evaluations. The corpus
has been used for historical tuning; this CV is not an untouched final test.
It would be misleading to compare its percentage directly with the old 55.2%
29-clip field result. No claim of calibrated confidence follows from RF votes.

### Real-audio integration check

All 11 frozen files (9.85 hours, 851 MB) passed the existing SHA-256, byte-length
and duration checks. The new candidate processed the first 60 seconds of each
of six high-confidence items in three phone concerts, without extraction failure.
The independent scorer reports **2/6 top-1 overall, 2/5 in-vocabulary**, one
out-of-vocabulary item, and zero missing selected items. Boundaries came from
human labels: **this is an oracle-boundary smoke test, not an automatic
segmentation or reliable field accuracy estimate.** No acoustic near-duplicate
search against the entire training waveform corpus was performed in this run.

### Verification

- Before changes: **232 passed, 3 failed, 1 xfailed**. Failures: the sine
  pitch/tonic test and two lyrics tests using an obsolete provider-shaped fake.
- After core repairs: **253 passed, 1 xfailed** in the full suite.
- After adding interval scoring and checkpoint restoration: **48 passed** in
  the focused melody-integrity and raga suites, covering those later changes.
- Synthetic ten-second contour patterns: finite gradients, loss reduction by
  more than 80%, perfect tiny-batch fit. This is a numerical sanity test, not
  evidence of generalizable raga classification.
- Transpose contour and tonic together: feature equality tested across three
  shifts. Repeated transitions, silence spans, valid Sa, NaN/time rejection,
  anti-phase 48-kHz stereo resampled to a bounded ten-second clip all tested.
- Actual local backend import resolves the intended root matcher and package.
- Whitespace checks pass for edited code; pre-existing user-label trailing
  whitespace is preserved. The remaining Google SDK deprecation warning is
  unrelated to raga execution and no API call was made.

## 5. Remaining work and resources

The audit and local repair/benchmark pass are complete. The requested production
performance target remains an empirical research objective, not a completed
deliverable. The specific unresolved work is:

1. Finish an independently labeled long-concert evaluation set with explicit
   nonmusic/unknown regions. The new scorer consumes partial work already.
2. Compare the frozen v4 fused model and further candidates on a development
   portion; retain separate concert/artist groups for final evaluation. These
   six inspected items are no longer an untouched model-selection test.
3. Develop automatic boundary and nonmusic detection, evaluated separately from
   classification given human boundaries. Fixed windows are not song boundaries.
4. Fit and evaluate an abstention/calibration policy using held-out source
   groups; report accuracy versus coverage and unknown-raga false acceptance.
   The current candidate only abstains on extraction quality.
5. Address training depth, unresolved taxonomy and independent composition
   renditions before justifying a large representation-model training run.
   MERT or a temporal encoder should be compared against the existing strongest
   model with the same labels, splits and compute accounting.

No external spend, model downloads, dedicated long-running GPU jobs, deployments,
raw-audio deletions, or writes to the original label TSV occurred. Existing
historical models/results and the user's other worktree changes were preserved.
New regenerable feature/model artifacts occupy about 270 MB locally and are
gitignored. All commands and evidence are under `data/architecture_audit/`.
