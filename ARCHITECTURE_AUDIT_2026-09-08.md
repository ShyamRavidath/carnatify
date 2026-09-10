# Carnatify: current architecture and execution findings

**Handoff-time update:** the matched-context run has completed. Read the September
section of `handoff.md` before older chronological status below. Latest fixed-fold
CV is 76.6693%; estimated-tonic known-raga development accuracy is 102/139. The
confidence gate remains unsafe (29/45 OOV false accepts), so no model is promoted.
The user requested a comprehensive handoff to preserve remaining weekly quota.

The audit is ongoing; substantial local refactoring is implemented. The candidate training
and inference workflow runs end to end. **Production/SOTA performance is not
established, and no model has been deployed or promoted.**

## Latest verified state — September 9

### Published benchmark comparability check

DeepSRGM reports 88.1% for its ensemble on CMD-40. Its protocol uses supplied
tonics, 12 recordings per raga, and one held-out recording per class in each
cross-validation round. This does not establish the artist-group-disjoint,
estimated-tonic, unsegmented-concert result required here. Its temporal sequence
model remains a relevant method family, but its headline score cannot be used
as a matched baseline for our 69-class candidate. Source:
[DeepSRGM, preprocessing and evaluation sections](https://arxiv.org/html/2402.10168v1).

The January 2026 generalized-category-discovery paper evaluates Hindustani
PIM/Saraga subsets, not this Carnatic task. Its positive-pair construction assumes
each original recording has a single raga; its K-means procedure assumes the
number of classes is known. Applying those assumptions to multi-raga concerts
would create false positive pairs (our inference from the stated protocol).
Reported clustering accuracy is not a production unknown-raga rejection metric.
The paper also reports its supervised CNN-LSTM outperforming pretrained MERT
variants for its embedding comparison; this is task-specific evidence, not a
general argument against foundation models. Source:
[Learning to Discover, sections III-D, III-F and IV](https://arxiv.org/html/2601.18766v1).

Decision: keep the current matched-context experiment frozen. Do not replace
manual labels with same-concert pseudo-label equivalence, and do not declare
SOTA by comparing unlike datasets, tonic assumptions or clustering metrics.

### Current experiment status

**Current ongoing work:** file-level artist tags now merge the 1,248-track cohort
from 219 to 133 groups. Grouped CV is 68.51%; matched known-raga accuracy remains
98/139. The standard pipeline includes these unions and reserved-artist checks.
An explicit tonic-mixture diagnostic scores 100/139 on development queries, but
its paired 95% interval includes no gain and field accuracy remains 3/6. Neither
the mixture nor any diagnostic confidence gate is promoted.

A 24-recording training-only check found six tonic disagreements between the
full-recording training path and exact-window inference, despite close pitch
agreement. The 180s matched-context extraction pilot completed 24 tracks/72
windows; a resumable four-worker rebuild of the entire artist-grouped cohort is
restarted in `data/overhaul/context180_strict_decode`. The first run stopped on
a libsndfile window-read error after saving 193 track caches; its executed source
and outputs are preserved. That recording passes full FFmpeg decoding, so the
window error is not classified as source corruption. Failed windows now receive
explicit rejection receipts. Completed query caches are reused under unchanged
DSP contracts. Full-cohort results are pending.
Strict full-file FFmpeg audit: 861/866 clean, five decoder errors (535.80s).
The rebuilt cohort excludes those five recordings and requires matching audit
evidence. Latest full suite: 482 passed, one expected failure; seven targeted
context/decode/download checks passed after the extraction repair.

Cleaning-only candidate `file_artist_strict_decode`: 1,243 tracks/3,715 windows,
CV 68.79%, but matched estimated-tonic development accuracy is 97/139 known
(previously 98/139). Strict decode filtering is now a standard training guard;
it did not improve recognition. A separate FFmpeg fallback passes five tests and
recovers the native waveform for the libsndfile-failing recording; it is not yet
enabled in the active frozen extraction protocol.

Strict evaluation-input audit is now complete: all 184 Saraga recordings decode
cleanly. The previously rejected Kamās query now has separately recovered pitch
features (98.98s voiced, estimated Sa 145.38Hz); those features are not yet merged
into training. Fifteen targeted recovery, fallback, pipeline and identity tests
pass. The full matched-context rebuild remains active, not a completed benchmark.

**Further execution update:** `data/overhaul/file_tag_guarded` is a separate
newer fitted/evaluated candidate: 1,248 tracks, 3,730 windows after six additional
documented supervision exclusions (five publisher-label contradictions and one
two-raga lecture). Its estimated-tonic result remains 98/139 known-raga; the
single-raga diagnostic gate has 62/79 correct accepts and seven/37 OOV false
accepts. No recognition gain or production gate is established. The end-to-end
concert run below still refers to the preserved `repro_audio_identity` model.

Real-audio MusicFM fine-tuning has now been tested on the inspected 31-recording,
five-raga, 13-group cohort. Five-epoch SGD: both arms 7/31. Twenty-epoch AdamW:
frozen head 10/31, trainable block 8/31, despite final training loss ~0.0115 for
the block arm. Do not scale/promote this overfitting recipe. A matched composition
replay using the byte/PCM/creator-guarded raga model scores 36/53 top-1 and 43/53
top-5 (181 queries, 53 answerable); both cross-fitted rejection arms accept zero
queries. This is unusable identity coverage, not production success.

Last full suite: 464 passed, one expected failure, 10 warnings. Three additional
publisher-file parser tests pass, including compound-raga handling; seven combined
parser/quarantine tests pass. Original labels and raw recordings remain intact.

The end-to-end reference candidate is `data/overhaul/repro_audio_identity`, not
the historical runs below. Its guarded cohort has 1,254 tracks, 3,748 windows,
69 classes and 219 groups, including 872 unique archival audio hashes.
Grouped development CV is 68.5008%. The 180-second estimated-tonic replay
scores 98/184 overall, 98/139 in vocabulary (70.5036%); its diagnostic gate
accepts 78 queries with 61 correct and seven out-of-vocabulary false accepts.
These are repeatedly inspected development queries, not a fresh test or SOTA
claim. Eight recording-level Rāgamālika labels also lack single-raga window
ground truth; current aggregate/OOV figures retain that known protocol caveat.
The separate source-checked `evaluation_single_raga_diagnostic.json` excludes
those eight recordings without modifying predictions: 98/176 overall, unchanged
98/139 known-raga, 61/77 accepted correct and six/37 OOV false accepts. This is
a denominator correction, not an accuracy gain; remaining truth is still
recording-level rather than time-aligned.

Raw-byte quarantine alone was insufficient: full-recording fingerprints found
one additional Akkarai Sisters copy with different file hashes. Independently
decoded full PCM hashes match exactly. Publisher creator metadata corroborates
the overlap. The latest guard excludes this connected group, 17 failed or
unaudited archival decodes, and a separately documented mixed radio programme
that had an invalid uniform Mukhāri label. Original recordings are preserved.
The fingerprint inventory completed 1,058/1,075 files (~195.4 decoded hours),
including 15 clean FFmpeg fallbacks; 17 training files failed decoding. All 11
field concerts decoded (~9.85 hours), with zero flags against 874 successfully
fingerprinted archival references. This is not proof against every transformed
copy, alternate microphone recording, or unknown-artist overlap.

All five standard pipeline stages have run. The first 1,605.75-second field
concert produced 53 query windows, seven proposed segments, and zero asserted
raga identities. Functional completion does not demonstrate segmentation or
recognition accuracy. Last full suite: 460 passed, one expected failure,
10 warnings (112.04s); two subsequently added mixed-recording summary tests
also passed separately. No deployment or model promotion.

**Labeling verdict: stop the additional manual tagging task for this workflow.**
Existing labels remain useful diagnostics and are preserved. Automated source,
identity and decoder audits remove concrete defects, but tonic estimation,
separation and pretrained embeddings do not manufacture reliable raga or song
ground truth. Frozen MusicFM and separation pilots have not demonstrated an
accuracy gain.

Local MPS is available outside the filesystem sandbox, despite appearing
unavailable inside it. CPU-mel/MPS-backbone MusicFM forward inference matches
CPU closely (frame relative L2 error 9.13e-7); warm 10-second forward passes
took 0.54–0.74 seconds in a small, non-isolated pilot. Native backward failed at
a convolution tensor-stride operation. Contiguous convolution output gradients
repair that exception, but a CPU control then exposed incorrect affine-only
LayerNorm gradients at the frozen-prefix boundary. Explicitly requesting that
boundary input gradient repairs the observed discrepancy. Three synthetic
optimization steps now agree with CPU in loss and all parameter gradient norms
(maximum absolute discrepancy 6.82e-7); both update encoder parameters by
2.083e-5 maximum and reduce loss from 2.39085 to 0.000822802. The fixes remain
in an experimental probe, not production training. Norm agreement is not full
gradient-vector parity, and a single synthetic example proves no raga accuracy.

### Historical integrity findings and superseded candidates

**Evaluation-integrity correction (September 9):** a new full raw-audio hash
audit found 26 broader-training rows identical to 15 of the 184 Saraga evaluation
files. The combined training run contains 16 overlapping rows / nine evaluation
files. Earlier Saraga results below are historical contaminated development
results, NOT fully recording-disjoint accuracy. Contour hashes and track IDs
failed to catch raw-audio copies under different names. A separate whole-group
quarantine/retraining run now scores 96/184 overall and 96/139 in-vocabulary
on the same 180-second estimated-tonic queries. Its 845 recorded archival audio
hashes are disjoint from all 184 query hashes; transformed copies and unknown
artists remain unresolved. This finding does not establish whether AV or field recordings overlap;
those require their own byte/recording identity checks.

The new run is `data/overhaul/broader_audio_quarantined`: 1,262 tracks, 69
classes, 3,772 windows, 223 groups, grouped development CV 68.23%. It excludes
91 tracks across two connected groups (evaluation copies and source mismatches).
Publisher metadata subsequently proved that the four apparent source mismatches
were shared audio across two uploads, not incorrect assignments. That exclusion
was conservative but unnecessary. The refreshed `broader_audio_deduplicated`
run restores eligible rows, quarantines 37 overlapping-group rows and removes
43 exact duplicates: 1,273 tracks, 69 classes, 224 groups. It scores 98/184 on
180s queries (98/139 in vocabulary) and 82/184 on 60s queries. Its gate remains
unsafe: 61 correct among 78 accepted at 180s. All 971 original archival files
now have publisher size/MD5/SHA1 matches; 10 are shared across archive uploads.
This supersedes the source-mismatch diagnosis, not the confirmed Saraga leak.
Its development gate accepts 79/184 with 61 correct (77.22%) and eight OOV false
accepts among 45 OOV queries. It is not a production rejection policy. Candidate
bundles can now carry training audio hashes; the Saraga evaluator rejects
byte-identical training audio and requires an explicit diagnostic override for
legacy bundles without raw-audio hash inventories. Raga-prior composition arms
using affected historical raga models also require reevaluation; the overlap
finding alone does not invalidate independently structured melody-only tests.

Latest verification: 439 tests passed, one expected failure; the complete
180-second replay reproduces every per-query result. The 60-second corrected
run scores 79/184 overall. Original manual labels and historical artifacts are
preserved. Remaining provenance gaps must be resolved before scaling training.

## 1. System topology

Previously, the backend's 480-bin RF/DTW path, root clip ASR/TDMS path, v4 fused
forests, notebook neural experiments, and labeling scripts were separate systems
with incompatible features and evaluation assumptions. The principal classifier
was a forest, not a distributed transformer. At 51 classes, 50% accuracy is far
above uniform random chance; it does not by itself demonstrate representation
collapse.

The authoritative candidate entry point is `scripts/carnatify_pipeline.py`:

```text
existing source audio / contours / annotations
  -> duplicate and taxonomy admission + source/known-artist groups
  -> run-scoped evaluation manifest and composition references
  -> shared tonic-relative, versioned features
  -> grouped training / evaluation + separate candidate artifact
  -> bounded audio blocks + activity tags + temporal raga evidence
  -> timestamped, explicitly unverified raga/song candidates
```

The revised `data/overhaul/repro_v2` run exercised all five stages. Full-concert
inference was verified on the 1,606-second first recording. This is not a claim
that every hour of the entire concert collection has been accurately segmented.

## 2. Critical flaws and repairs

| Location | Confirmed issue and disposition |
|---|---|
| `src/carnatify/audio/feature_extractor.py:71` and `:95` | Essentia default rate disagreed with resampled audio; explicit rates fix the demonstrated doubled-pitch failure. |
| `src/carnatify/audio/feature_extractor.py:48` | Zero cents conflated Sa with silence; explicit Hz voicing mask now retains Sa. |
| `src/carnatify/audio/utils.py:21` | Added bounded native-rate reads, finite checks, resampling, clipping/RMS diagnostics, and anti-phase-safe downmixing. |
| `src/carnatify/ml/raga_features.py` | Historical repeated-index transition updates did not accumulate counts. Corrected features are separately versioned; old pickle-compatible behavior is retained. |
| `src/carnatify/ml/raga_dataset.py` | Removed default random rotation of already tonic-relative pitch-class distributions. |
| `identify_clip.py:1009` | Removed maximum-raga-confidence search across tonic rotations and arbitrary tonic fallback. Invalid tonic now abstains. |
| `scripts/raga_pipeline.py:45` | New grouped splits union duplicate recordings; contradictory labels are quarantined before class-count filtering. Historical nongrouped scripts are not trusted evaluation entry points. |
| `normalize_ragas.py:209` | Removed fuzzy label manufacture and problematic hand aliases. Existing generated alias artifacts remain historical, not ground truth. |
| `scripts/long_concert_labels.py:123` | Fixed space/tab parsing. Independent interval scoring respects explicit ends and tani exclusions rather than silently extending partial labels. |
| `src/carnatify/ml/raga_trainer.py:138` | Restores the best checkpoint rather than reporting final-epoch weights. Prediction inputs follow model device. |
| `backend/main.py`, `backend/clip_identify.py` | Local imports now resolve the canonical checkout instead of stale bundled copies. |
| `backend/main.py:224`, `src/carnatify/audio/feature_extractor.py:78` | Remaining legacy median-F0/arbitrary-130-Hz tonic fallbacks were removed. Missing tonic now fails explicitly for tonic-dependent audio classification; independent lyric candidates remain available. Backend tonic context matches its 60-second raga query. |
| `src/carnatify/audio/utils.py`, `backend/main.py` | All eight upload decode sites now preserve native channels until the shared anti-phase guard, then resample once, with explicit duration limits and WebM fallback. Actual WebM/Opus and local HTTP tests cover retained signal, missing-tonic rejection and temporary-upload cleanup. |
| `src/carnatify/ml/evaluation_integrity.py:4` | Explicitly overlapping training tracks are rejected by evaluation; new candidate bundles record training IDs and class support. |
| `src/carnatify/ml/concert_segments.py:6` | Development-gate outputs cannot masquerade as validated identities. Rankings are retained; asserted raga identity abstains. |
| `src/carnatify/audio/melody_frontend.py` and `scripts/concert_pipeline.py` | Concert inference borrowed a nearby 60-second tonic for longer queries, unlike the benchmark. Default inference now extracts melody and tonic on the exact bounded query, with parameter/boundary-scoped caching; the old path is an explicit diagnostic option. |
| `scripts/saraga_av_matching.py` / `scripts/plan_saraga_av_evaluation.py` | AV artist spelling/case differences silently dropped joins. Corroborated filename correspondences now join 228/232 records. Top-level source `mbid` is artist-like, not recording-unique: 232 records have only 37 values. Future recording IDs and selection hashes use archive member paths. |

Important correction: voiced-time compression is intentional in the original
TDMS method. The elapsed-time variant was tested, did not improve accuracy, and
was not substituted on theoretical preference alone. Fixed windows are not
inherently invalid merely because they cut tala cycles; mixed items and weak
melodic evidence are the demonstrated concerns.

## 3. Manual labeling verdict

**Stop the new manual labeling task for this overhaul.** No new human labels are
required by the candidate workflow. Existing public annotations, work IDs, and
the user's already-entered intervals provide supervision and evaluation.

The existing labels are useful, not redundant. Their file remains byte-for-byte
unchanged. Six explicit high-confidence musical intervals across three concerts
were recovered for primary scoring. Demucs, tonic estimation, self-supervision,
and clustering are not substitutes for independent semantic ground truth.

## 4. Measured results and autonomous actions

These are different cohorts/tasks; do not collapse them into one accuracy claim.

| Evaluation | Result |
|---|---|
| Combined training, source/known-artist grouped | 70.25%, 1,264 tracks, 56 classes |
| Broader training, same grouping policy | 68.29%, 1,353 tracks, 69 classes; some very sparse classes |
| Corrected Saraga metadata, 60s, shared-vocabulary queries | Combined 72/109 versus strong RF 63/109 |
| Corrected Saraga metadata, 180s, same shared vocabulary | Combined 82/109 versus strong RF 74/109 |
| Broader model, all 184 Saraga queries, 180s | 99/184 overall; 99/139 in vocabulary |
| Original frozen AV test, 60s | Combined 19/29 versus RF 17/29 |
| Later AV validation, 180s, previously inspected cohort | Combined 22/29; broader 21/29; RF 20/29 |
| Fresh eight-artist AV test, frozen centered 180s protocol | Combined/multiscale/broader 6/8; RF 5/8; common vocabulary 6/7 versus 5/7 |
| Six existing labeled concert items, fixed centered 180s oracle-boundary queries | Combined 4/6; broader 3/6; RF 3/6; Dhenuka outside all three vocabularies |
| Same six queries, Demucs vocals with unchanged original-mix tonic | Combined 4/6; broader 4/6; RF 4/6; no improvement over the best mixed-audio model |
| Cross-rendition song retrieval, 181 references | 19/27 top1, 22/27 top5; 154 additional unanswerable queries expose weak rejection |
| Full verified 534-reference catalog, same 181 song queries | 53 answerable; melody-only 24/53 top1 and 35/53 top5; fixed estimated-raga prior 30/53 and 39/53; overall 30/181 correct with prior |
| Same full catalog, exact 180-second song queries | Melody-only 32/53 top1 and 40/53 top5; fixed prior 37/53 and 43/53; overall 37/181 correct with prior; rejection still fails |

The corrected metadata resolves one explicit source-provided synonym,
Kāmavardani/Pantuvarāḷi. Its additional correct item is a scoring correction, not
a learned improvement. The original reports remain preserved.

AV selection correction: the original within-artist hashes tied because the
source `mbid` repeats. Its actual choice was the first eligible sorted metadata
path per artist, not a hash-randomized rendition. Selection still preceded
predictions, and the 29 frozen audio files/scores are unchanged. That cohort is
small, known-vocabulary and lexically selected; future plans use recording-unique
archive-member hashes and do not overwrite it.

At 180 seconds, the common-vocabulary raga improvement has artist-bootstrap
95% interval [0.00, +15.45] percentage points: it reaches zero. An artist-cross-
fitted rejection experiment accepted 48/184 clips with 43 correct (89.58%), but
only 26.09% coverage. Its precision interval is [83.33%, 100%]; this is not a
production guarantee and no gate was enabled.

Failed or mixed ablations were retained, not promoted: acoustic tonic
disambiguation, vocal-band extraction, additional time-delay scales, direct
audio-domain adaptation, nested kernel tuning, finer song frames, conditional
vocabulary combination, and an SPD-inspired bounded-excursion variant.
The small temporal CNN reached 44.49% on one fixed 254-track held-out fold,
versus 66.93% for the kernel model on that same fold. Its training loss fell
from 4.02 to 1.29; gradients and optimization work, but generalization is worse.
Harmonic separation also regressed: 81/184 versus 83/184 for the broader
60-second model, so the original mixed-audio profile remains default.
A pinned pretrained RMVPE ONNX frontend passed the actual synthetic tone test
but scored 3/6 for each classifier on the six labeled field items, versus
4/6 for the best Melodia candidate. It is not adopted.
The initial pitch-only activity detector was inconsistent (9/16 held-out public
excerpts). A section audit then found two omitted `tani_avartana` annotations;
tanam/thanam is correctly kept melodic. Expanded training uses 930 fixed queries
from 310 sections but only four artists, including six tani sections. Artist-
held-out recall is 88.89% for tani and 95.61% for melody; section-averaged decisions
are correct on 306/310 sections. These are correlated development observations.
Exact ten-second field queries score 136/148 versus default AudioSet's 118/148.
An optional uncertainty-preserving activity replay locates the first concert's
tani at 760–1440 seconds (existing annotation 755–1440), with 99.67% duration-
weighted activity accuracy over 1,501 explicitly labeled seconds, versus 89.01%
before refinement. This repeatedly inspected single-concert result does not
establish raga/song accuracy or production reliability. The detector is optional,
disabled by default; original raga evidence is unchanged and still unreliable.
An additional fixed continuous check covers all six public tani regions with
each artist excluded from training. Across 3,313.74 labeled seconds, decoding
improves activity accuracy from 80.89% to 95.18%, with tani recall 94.36% and
melody recall 99.26%. One region regresses. Only four artists are represented,
and query regions are annotation-centered; this is not automatic full-concert
discovery or a statistically broad production test.

A separate optional catalog now has 680 reference performances / 561 identities.
Its 499 archival additions carry explicit weak-metadata provenance; the 19/27
song result does not apply to that expanded catalog. Generic improvisation titles
are excluded. Its first-concert smoke test still did not identify the labeled
song in the top three. The default catalog remains the annotated 181-reference
version.

The full test suite including browser-upload, local HTTP and MusicFM frontend
tests passed 434 tests with one expected failure and ten dependency/codec warnings. Ten-second
synthetic tests cover pitch/rate correctness, tonic invariance, stereo handling,
gradient flow and loss convergence. No raw audio was deleted, no paid API or
cloud cluster was launched, and deployed model artifacts were not overwritten.

Further song ablations did not improve the 19/27 top-1 baseline: composed-only
reference passages and three-passage query alignment each scored 17/27.
Artist/source/work-connected rejection checks expose only five independent
components, with all correct matches in two. Neither distance nor margin meets
the 90%-precision/ten-answer calibration requirement; both abstain everywhere.
No acceptance gate is promoted. Rejection/provenance and temporary-outage
regression tests are included in that full-suite result.
Public recording-to-work metadata lookup subsequently recovered intermittently.
The first ten explicit relationships support a separate 191-reference catalog.
On the unchanged 181-query development set, two more queries become answerable
and both rank first: 21/29 top-1, while the original cohort stays 19/27. Thus
overall identification remains only 21/181. That partial catalog has no
validated rejection threshold.
The first-100-recording checkpoint adds 74 nonduplicate performances, yielding
255 references. It scores 24/38 top-1 and 28/38 top-5 over 181 total queries:
seven new correct identifications offset two displaced prior hits. The original
27-query cohort falls to 17/27. Rejection remains infeasible; the default catalog
is unchanged. This is a coverage/discrimination tradeoff, not uniform improvement.
An optional estimated-raga ranking preference subsequently scores 26/38 top-1
and 31/38 top-5 on that fixed catalog (three gains, one loss). It uses model
predictions, not oracle query ragas. Rejection remains infeasible and the option
is not enabled in default inference. All eight fresh AV audio inputs were
checksum-verified before the frozen models were scored. The combined model
accepted six predictions, all correct; the broader and multiscale models each
accepted five, all correct. This tiny selected cohort is not a natural-prevalence
open-set test or proof of production precision. Frozen results and model hashes
are preserved in `data/overhaul/saraga_av/remaining_artists/fresh_results.json`.

Song inference now separately extracts its exact 60-second query instead of
slicing a longer raga query and borrowing its tonic. Song retrieval also no
longer depends on successful raga feature construction. A 180-second concert
smoke exercised six independently bounded song queries in 109 seconds and made
no asserted raga identifications. Warm ranking against 255 references took
about 0.15 seconds per query; this excludes audio DSP and startup costs.
The longer-context experiment is now explicitly selectable in concert inference
with `--composition-window-s 180` and `--composition-raga-prior`. The unified
pipeline also accepts an explicit `--composition-catalog`. The prior uses the
selected model on the exact song query, and selection of a reference rendition
occurs after the bounded ranking penalty. All remain candidate-only; defaults
are unchanged and the failed rejection experiment is not promoted.
Default activity blocks now use a separate events-only cache, eliminating
discarded block pitch/tonic computation. A real three-minute regression check
preserved events, windows and segments exactly. The legacy diagnostic cache
remains intact. Its 26.5-second runtime reused query features and is not a
matched cold-latency comparison.

## 5. Remaining work and resource position

The first labeled Shankarabharanam concert item remains a field failure. The
exact-query frontend still leads with an incorrect low-confidence Begada
candidate on its first three minutes; consistent DSP is necessary, not sufficient.
Reliable item boundaries, unseen-raga rejection, and high-coverage cross-rendition song
identity are unresolved. The tiny accepted-prediction and composition cohorts
cannot establish production reliability.
An exact-label check finds no Dhenuka rows in either the available 1,287-row
archive coverage matrix or the 477-recording CompMusic plan. Its absence from
the candidate vocabulary is a source-coverage gap, not just minimum-count
filtering. The matched six-query vocal-separation diagnostic scores 4/6 for
each model with original estimated tonics held fixed. The broader model and
forest each gain one item; the best mixed-audio model is unchanged. On 29
historical field clips with unresolved provenance, the broader model remains
14/29 with or without separation. Separation is not made the default.

Continue with independent field/front-end validation and richer reliable
reference coverage, while keeping weak metadata and predictions out of gold
evaluation. Longer context is available through `--window-s 180`; broader
preparation through `--min-tracks 5`. Both are explicit experiment settings,
not silently changed defaults. The separate eight-artist test has completed
under its frozen protocol, with results reported above. All 477 public work-
relationship lookups are complete. The full deduplicated candidate catalog has
534 reference performances / 423 work identities. The fixed 60-second tests
are complete, with results above; rejection remains infeasible at 60 seconds.
Exact 180-second song queries improve ranking, but connected-group margin
rejection accepts only five queries with four correct without the prior, and
one incorrect query with the prior. Distance proximity abstains throughout.
Neither establishes the required precision or coverage; no gate is promoted.
A forward-versus-reversed-query control preserves the best 37/53 top-1 and
raises top-5 from 43/53 to 46/53, but exchanges eight top-1 hits for eight
misses and still fails rejection. It remains an experiment, not a default.
A bounded offline Whisper pilot uses the existing checksum-verified model,
exact audio hashes and unprompted fixed language lanes. Thirty-second queries
on eight fixed recordings yield usable text in six; a title-only TF-IDF probe
gets 2/8 top-1 and 3/8 top-5. All eight titles are present in that text vocabulary.
This is neither word-accuracy measurement nor the independent-reference melody
task. Repetitive hallucinations remain a problem; ASR is not enabled for identity
assertions and does not remove the need for independent semantic evaluation.
The legacy 8,688-entry lyrics registry also contains 14 unsupported event
headers with dates in their raga fields. A conservative consumption-time guard
removes those false candidates while preserving stored IDs, source files and
all rows with musical support. These local sequential IDs are not authoritative
work identities; the registry is not silently joined to MusicBrainz ground truth.
A source-hashed synthetic transition test now exposes a context tradeoff:
over the same 270 musical seconds, 60-second queries rank all ragas correctly,
while fixed 180-second queries rank 180 seconds correctly despite perfect scores
on their two pure queries. An optional silence-bounded policy with post-silence
query anchors restores all 270 seconds, with no mixed-item queries. Its earlier
energy-only cap scored 240 seconds because of post-pause grid gaps; that failed
intermediate run is retained. All identities remain unasserted. This is a
three-item synthetic diagnostic, not natural-concert accuracy, and the option
remains off by default. Twenty-one targeted tests pass after the anchor change.
Natural-audio transfer was then checked over all 11 frozen recordings:
35,461.47 seconds (9.85 hours), 3,553 bounded windows. Only the documented
110-second muted region in concert 3 qualifies; the other ten recordings
have no near-digital silence. The policy is therefore a conservative mute
guard, not a demonstrated solution for natural song boundaries. Thresholds
were not relaxed to force detections. The full audit and cached replay
preserve source hashes and require no new manual labels.
No external compute authorization is currently
needed. Core environment constraints are recorded, but are not a complete
cross-platform lock file.

A pinned MusicFM-MSD frozen encoder now runs locally with restricted checkpoint
loading and inference networking disabled. A ten-second concert excerpt yields
finite 250x1024 frame embeddings, reproduced byte-for-byte in a separate run.
Observed inference times were 20.24 and 9.66 seconds on four CPU threads.
This establishes feasibility only: no raga/song head is trained, no tonic
invariance is established, and no model is promoted on this evidence.
A matched ten-second representation probe subsequently covered 31 unique
recordings in five single ragas with 13 connected artist/source holdouts.
Fixed class-balanced kernel ridge scores 12/31 with pitch features, 8/31 with
pooled MusicFM layer-7 features, and 11/31 combined. All queries have valid
pitch features. This setup does not improve the baseline. It is a small,
selected-vocabulary development ablation, not a 69-class comparison or proof
about all possible MusicFM adaptations. Pretraining overlap is not independently
audited; no new model or acceptance gate is promoted.
A separate estimated-tonic-normalized audio arm preserves that exact cohort,
classifier and grouping. MusicFM reaches 9/31 and combined features 12/31,
still no gain over the unchanged pitch control's 12/31. All results reproduce
from saved features. Public tonic annotations, used only for diagnosis, show
22/31 query estimates within 50 cents modulo octave. Neither a normalized
embedding nor an estimated tonic is assumed correct merely because it exists.

See [OVERHAUL_EXECUTION.md](OVERHAUL_EXECUTION.md) for execution detail and
[RESEARCH_NOTES_2026-09-08.md](RESEARCH_NOTES_2026-09-08.md) for primary-source
comparisons and the limits of published benchmark numbers.
