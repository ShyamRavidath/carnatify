# Autonomous overhaul execution

## Handoff-time completion update — supersedes running-job notes below

The user requested a quota-preserving handoff with only 8% weekly usage remaining.
Read the new September section of `handoff.md` first. Both context extraction and
the automatic follow-on experiment have COMPLETED; their old session handles are
gone. Do not restart them. Latest cohort: 1,243 tracks /3,547 windows /69 classes /
133 groups. Fixed-track/fold CV 76.6693% versus 68.7852% cleaning-only comparator
(140 wins, 42 losses). Estimated-tonic validation 102/139 known, versus 97/139.
Confidence is unsafe: 95/145 accepted correct, 29/45 OOV false accepts. No model
promoted. Full regression 497 passed /1 xfailed; handoff-time five tiny tests pass.
Latest artifacts: `data/overhaul/context180_recovered_experiment/training`.
`handoff.md` documents next actions and the prior agent's mistakes for independent
review. No new model experiment was started while preparing the handoff.

Goal: execute the user's complete raga/song training and inference overhaul,
eliminate any requirement for new manual labeling, and verify performance on
independent recordings. The active product goal references the user's attached
task. Completion is not established by the preceding audit or passing tests.

## Evidence and strategy

The last turn made concrete progress: repaired confirmed defects, recovered
existing labels, and measured a failed corrected-feature RF candidate. Current
state confirms those edits/artifacts remain on disk. That candidate has not
reached the performance target.

Prioritize the following based on evidence, revising only with measurements:

1. Improve the discriminative model on the already extracted 3,017 windows.
   Compare distribution-aware kernels against the paired 46.09% RF benchmark.
   Persist exact grouped folds, per-track predictions and source-cluster CIs.
   Development CV remains development evidence; no SOTA claim from it.
2. Use existing Saraga/CompMusic annotations for independent automated evaluation
   and existing recording/title metadata for supervised/weak supervision. No
   additional human annotation is a prerequisite. Model-derived labels must be
   stored as pseudo-labels and must never become evaluation truth.
3. Add automatic long-concert segmentation using acoustic activity, melody
   stability and change detection, with duration-aware evidence aggregation.
   Evaluate with annotated item concatenations including held-out source groups
   and real concert files. Synthetic concatenations are separately identified.
4. Add group-disjoint confidence calibration and unknown-raga rejection. Measure
   coverage, conditional accuracy and OOV false acceptance, not just top-1.
5. Repair/replace composition retrieval using independently sourced rendition
   pairs and automatic reference alignment; measure recording- and artist-disjoint
   retrieval. Do not revive a contaminated metric as evidence of improvement.
6. Consolidate runtime contracts, artifacts and CLI into reproducible components,
   validate incremental/bounded audio inference, and wire only verified models.
7. If compact pitch models plateau, test pretrained music representations and/or
   a temporal pitch encoder with supervised contrastive learning on the existing
   labels. Expensive external compute remains gated; bounded local work proceeds.

## Completion requirements

- Demonstrated gains over a matched >=50% target/baseline and the strongest
  existing relevant model; dataset/class/window differences explicitly controlled.
- Complete reproducible preparation, extraction, fit, evaluation and inference.
- Automatic annotation/segmentation route requires no new human labels.
- Song identification evaluated on independent renditions, with rejection.
- Real long-file execution, source-disjoint tests, numerical sanity/gradient
  checks, uncertainty/coverage and resource behavior verified.
- State-of-the-art claim supported by comparable independent evidence, not a
  training score, inherited published number or an easy corpus subset.

## Execution/accounting

The product goal is already active; do not close or replace it with an audit-only
objective. Available accounting is `get_goal`; no callable `/usage` or account
quota tool is exposed in this session. Do not fabricate quota measurements.
Keep model artifacts and completed cell results on disk for continuation.
Original user label/audio files and existing reference artifacts are preserved.

## Measured execution update (2026-09-08)

- Matched five-fold archive benchmark: RF 46.09%, distribution SVC 51.04%,
  voiced-time kernel ridge 58.28% (1,009 tracks, 51 classes). The original TDMS
  paper explicitly compresses voiced time; this is a legitimate ablation, not
  an unconditional DSP defect. The earlier audit now carries that correction.
- Real mixed-audio center-60s Saraga queries, with estimated tonic: ridge
  67/108 = 62.04% in-vocabulary versus repaired RF 56/108 = 51.85%.
  Overall 67/184 = 36.41%; 76 tracks are outside model vocabulary. Annotated
  tonic increases ridge to 72/108 = 66.67%. Source/known artist groups checked,
  unresolved provenance remains a limitation. This corpus is now validation,
  not an untouched final test after repeated model comparisons.
- OOF-selected ridge threshold .7178 accepts 36/184 queries; 29 correct,
  4 accepted OOV tracks. Thus 80.56% empirical accepted precision at only
  19.57% coverage, OOV false acceptance 4/76 = 5.26%. This is not a guarantee.
- Removed fuzzy label creation from the normalizer, added regression tests,
  and generated provenance-linked admission without altering legacy JSON.
  487 tracks have consistent strict tag candidates, 395 lack exact title
  provenance, and 127 are quarantined as unresolved/conflicting (not all
  proven wrong). Quarantine-only ridge gets 66/108 = 61.11% estimated-tonic
  validation; filtering alone did NOT improve the 67/108 candidate.
- Automatic event+melody inference completed a 1,606-second concert in 542s
  cold CPU time. Decoder stabilization reduced 43 proposals to 17, but only
  one raga answer passed the gate. Segmentation is not yet validated.
- New time-aware tonic-relative subsequence retrieval: 14/27 = 51.85% top-1,
  59.26% top-5 across 181 references, excluding identical audio, concert,
  source-group and exact-normalized artist overlap. Real mixed-audio queries,
  distributed reference pitch/tonic, existing work IDs as truth. Small corpus,
  no acceptance threshold or production claim; open-set evaluation underway.
- No new human labeling, cloud training, paid API calls, or raw-audio deletion.
  Local model download is an immutable public BSD-licensed AudioSet AST;
  dependencies are isolated under data/overhaul/runtime_deps.

Remaining: improve tonic stability and vocabulary/source depth, establish
same-raga composition discrimination and open-set rejection, validate automatic
boundaries, wire a versioned end-to-end runtime, and test the strongest existing
models on identical inputs. Current evidence does not establish SOTA.

## Later validation and reproducibility update

- Rebuilt the stronger v4-style 800+800-tree RF on the same archive-only
  cohort, avoiding its existing checkpoint's Saraga training contamination.
  Real Saraga estimated-tonic result: 62/108 = 57.41%. The combined candidate
  scores 71/108 = 65.74% on that exact vocabulary intersection; artist-cluster
  paired bootstrap gain +8.33 pp, 95% interval [-0.97, +17.24] pp. This interval
  includes zero: the gain is not statistically established by this small set.
- CompMusic reference-only, excluding 95 tracks from Saraga evaluation artists:
  382 tracks / 40 classes; artist-grouped CV 86.39%. Live Saraga transfer falls
  to 55/90 = 61.11%; its OOF threshold falsely accepts 75.5% of OOV queries.
  Do not deploy its apparent reference-corpus confidence.
- Combined admitted archive + CompMusic: 1,264 tracks, 56 classes, 3,778 windows,
  216 source/known-artist groups. CV 70.25%; Saraga 74/113 = 65.49% known-class,
  74/184 = 40.22% overall. Training-selected threshold has only 57.78% accepted
  precision on Saraga, so it is not production validated.
- Frozen historical field features: combined mixed-audio 15/29, voice-band
  16/29, Demucs 14/29. No verified field improvement. The adapter initially
  loaded only eight explicit w60 files; corrected to the registered <=60s
  whole-clip fallback for the other 21 and regenerated the report with all 29.
  Field source/artist identity and some labels remain unresolved.
- Six voiced-time scales (.1, .15, .25, .5, 1, 2s): matched CV 70.02%, Saraga
  estimated tonic 70/113 = 61.95%, annotated tonic 80/113 = 70.80%. Not promoted.
- Song retrieval with one global profile-selected transposition plus unchanged
  temporal alignment: 19/27 = 70.37% top1, 22/27 = 81.48% top5; macro-work top1
  66.88% across 11 works. Open-set 154 unanswerable queries expose poor distance
  rejection. No production song-identity acceptance claim.
- Added scripts/carnatify_pipeline.py as a single stage dispatcher. A clean run
  under data/overhaul/repro_smoke reproduced preparation, feature extraction,
  training, all 184 validation predictions, and full 1,606s concert inference.
  Deferred DSP imports reduced cached validation from ~115s to ~20s.
- Fresh Saraga AV test: CC-BY-4.0 metadata and ZIP index verified. One eligible
  SHA-ranked track per artist, 29 artists / 22 known ragas, 0.86 GB compressed;
  selection and three comparator hashes frozen before any fresh predictions.
  Bounded HTTP range download completed all 29 files with ZIP CRC validation,
  using 982.4 MB on the wire; no 65 GB full-archive download.
- Frozen fresh Saraga AV evaluation: combined and six-scale candidates each
  19/29 top-1, strong RF 17/29. On the 28-track common vocabulary: 19 versus 17.
  This is a small, size-limited known-raga test, not evidence of SOTA or reliable
  open-set rejection. Do not tune on it and describe it as untouched again.
- Experimental relative-percussion calibration passed 16 development excerpts
  but failed on the real long concert: it labeled almost the entire recording
  percussion (tani precision 45.4%). Disabled by default; explicit opt-in only.
  The conservative decoder produces seven proposals on that recording, but
  reliable musical-item boundaries and correct raga identity remain unresolved.
- Root identify_clip.py no longer searches 12 tonic rotations for maximal raga
  confidence or substitutes arbitrary 146.83 Hz. It uses bounded phase-safe
  audio loading and explicit DSP sample rates, abstaining on invalid tonic.
- Added a pickle-free, versioned 181-reference composition catalog to the clean
  CLI and verified full-concert inference with per-window composition candidates.
  Candidates remain unverified: no unsupported song acceptance is enabled.
- Tonic development diagnostic: baseline 141/184 within 50 cents; 35 of 43
  errors are fifth-related. Audio-only stationary harmonic logistic regression
  regressed to 137/184 in artist-disjoint folds. A conservative margin selected
  by nested artist-disjoint validation only recovers the baseline 141/184.
  Not adopted. Versioned evidence cache includes audio, window and tonic hashes;
  synthetic 10-second harmonic, gain and candidate-invariance tests pass.
- Concert output now explicitly demotes development-gate "recognized" states
  to unverified candidates. Scores and candidate ragas remain available, but
  the semantic raga field abstains until production rejection is established.
- Fixed legacy-vocal Melodia extraction regressed to 72/113 from 74/113 with
  estimated tonic (annotated tonic: 78 versus 77). Defaults retained. Separate
  caches prevent cross-profile reuse; fresh AV did not select these parameters.
- Added real mixed-audio training features using existing Saraga annotations,
  with five artist-held-out folds and fixed original training corpus. This also
  regressed slightly: 73/113 versus 74/113. The fitted audio-domain model is an
  uncalibrated experiment, not promoted, and includes Saraga training audio.
- Hardened artist provenance propagation and future AV selection. A post-score
  audit against the full existing provenance map found no known overlap for the
  frozen AV cohort; the original frozen selection/report were not overwritten.
- Fixed composition-evaluation denominator semantics: extraction/alignment
  failure cannot turn an answerable query into an excluded unknown. Rerun on all
  181 queries reproduces 19/27 top1 and 22/27 top5. Added failure-case tests.
- Full suite: 294 passed, one expected failure; additional artist-provenance and
  retrieval-denominator regression tests passed separately after that run.
- Nested nine-configuration kernel search (three inner source-group folds,
  five outer folds) reached 70.57% versus 70.25%. Its selected alpha=.01,
  gamma=2 candidate regressed on Saraga to 66/113, despite 17/29 on historical
  field mixes (original combined: 15/29). Not promoted on mixed evidence.
- Quarter-second melody frames scored 18/27 top1, 23/27 top5 versus the original
  19/27 and 22/27. Equal reciprocal-rank fusion of the top-five lists gives
  19/27, no top1 gain. Half-second catalog retained.
- Distributed reference-pitch diagnostic on the same 60-second intervals:
  77/113, matching live extraction with annotated tonic (estimated: 74/113).
  Reference tracks are not human framewise gold or deployable audio inference.
- Candidate bundles now record training track IDs; the evaluator rejects an
  explicitly overlapping training/evaluation cohort. Domain-adapted Saraga
  scores must come from its artist-held-out OOF output, not its full-fit model.
- User LABELS.tsv SHA256 remains unchanged at
  a0d137ea236e48b7cab710feff1abb7f8fc42fa46ce8c0b3877bb023263e44bb.
  Latest AST inventory: 274 Python files, 19 exact duplicate groups; the only
  three syntax errors remain known notebook-magics scripts.
- Three-minute context (same models, longer audio task) improved combined
  estimated-tonic recognition to 84/113 in the original metadata cohort.
  Metadata v2 uses the source's explicit common_name to resolve the one
  Kāmavardani/Pantuvarāḷi synonym: corrected results are 85/114 at 180 seconds
  and 75/114 at 60 seconds. This extra correct item is a scoring correction.
- Matched corrected 180-second vocabulary: combined 82/109, strong RF 74/109;
  artist-cluster difference +7.34 pp, 95% interval [0.00, +15.45] pp. Development
  evidence only; the interval reaches zero, and open-set rejection remains weak.
- Unified preparation now builds run-scoped metadata and composition references;
  evaluation consumes that same manifest. Original frozen reports remain intact.
- Contradictory duplicate-recording labels are now quarantined before minimum
  class filtering, so a discarded rare label cannot conceal a conflict. The
  original preparation cohort still reproduces 1,009 tracks / 51 classes.
- Broader cached-data experiment (minimum five tracks before admission): 1,140
  archive tracks / 69 classes, 169 quarantined; combined admitted corpus has
  1,353 tracks / 69 classes / 4,045 windows / 225 groups. CV is 68.29% on this
  harder vocabulary. Some classes have only one admitted track; their missing
  held-out training classes count as errors, not excluded favorable cases.
- Broader model, metadata v2: 83/184 overall (83/139 known) at 60 seconds;
  99/184 overall (99/139 known) at 180 seconds. The 56-class comparator scores
  75/184 and 85/184 respectively. Known-class accuracy and coverage are distinct.
- Artist-cross-fitted 90%-target rejection on the broader 180-second development
  predictions: 48/184 accepted, 43 correct (89.58% precision), 26.09% coverage,
  3/45 OOV falsely accepted. Artist-bootstrap precision interval [83.33%, 100%].
  No production gate exported or enabled.
- Direction-conditioned SPD-inspired variant: 58.12% on the same 382-track
  CompMusic artist-disjoint cohort versus TDMS 86.39%. Failed variant retained
  as an ablation; not an exact reproduction of the published SPD ensemble.
- Revised run-scoped pipeline at repro_v2 completed all five stages, reproducing
  70.25% training CV and 85/114 known-raga 180-second validation. Concert output
  remains seven unverified proposals, not validated identification of the first
  Shankarabharanam item. Broader AV post-development validation is underway;
  original frozen fresh-test evidence is not overwritten.
- Intermittent sklearn threaded-prediction warning flooding was isolated to the
  per-tree parallel path. Serial prediction for tiny evaluation batches preserves
  probabilities, avoids that path, and reran all 184 predictions without flooding.
  Persisted models and parallel training settings were not changed.
- Previously inspected AV cohort, three-minute post-development validation:
  combined 22/29, broader 21/29, RF 20/29, multiscale 21/29. This is not a new
  untouched test; the original frozen 60-second report remains preserved.
- Fixed vocabulary cascade retains the broader model's new-class probability
  mass and uses narrow conditional probabilities for shared classes. It scored
  98/184 versus the broader model's 99/184 at 180 seconds; not promoted.
- Optional composition catalog expansion adds 499 explicitly weak archival
  references, totaling 680 performances / 561 identities. The first concert's
  labeled song still failed top-three retrieval. Default annotated catalog and
  its separate 19/27 benchmark remain unchanged.
- Harmonic/percussive separation regressed to 81/184 versus 83/184 for the
  broader 60-second model (annotated tonic: 87 versus 91). Tonic was estimated
  on the original mix in both arms. No default profile was changed.
- Found a concert-query mismatch: the prior implementation concatenated block
  contours and borrowed the nearest 60-second tonic even for 180-second queries.
  Added exact bounded query extraction with boundary/parameter/hash-scoped cache;
  the old path is available only through --legacy-block-frontend for comparison.
  Shared waveform equivalence and cache tests pass. The first concert still
  produces an incorrect low-confidence Begada candidate on its first three
  minutes. Warm cached six-query inference takes 0.3 seconds after startup.
- Latest full suite: 316 passed, one expected failure; four subsequent
  exact-query frontend and labeled-window planning tests passed separately.
- All six existing primary labeled items now have a deterministic centered
  180-second oracle-boundary check: combined 4/6, broader 3/6, strong RF 3/6.
  Dhenuka is outside each vocabulary. This is neither fresh artist-independent
  evidence nor automatic boundary accuracy. No new labels were collected.
- Small tonic-relative temporal CNN experiment now preserves elapsed silence
  and circular pitch moments at 10 Hz, with dilated temporal convolutions and
  attentive statistics pooling. Ten-second invariance and tiny-batch gradient/
  convergence tests pass. Fixed 20-epoch source-held-out fold: 44.49% (254 test
  tracks), versus the kernel baseline's 66.93% on exactly that fold. Training
  loss fell from 4.02 to 1.29. This failed model is not promoted; no favorable
  intermediate epoch is substituted for the predeclared final epoch.
- Latest complete suite: 322 passed, one expected failure. Three additional
  AV filename-join/recording-identity tests passed after that run.
- AV metadata audit found only 37 distinct top-level mbid values across 232
  records: IDs repeat within artist. The original claimed hash ranking tied
  and actually picked the first eligible sorted metadata path. Original audio,
  labels and scores are preserved, with that selection limitation now explicit.
- Case-normalized joins plus four archive artist spelling correspondences,
  each corroborated by multiple exact distinctive title directories, resolve
  228/232 mixture records. No fuzzy raga label assignment was added.
- A separate eight-artist test excludes all previously evaluated AV artists
  and known training artists. Its recording-specific selection and comparator
  hashes are frozen before new audio predictions, using center 180 seconds.
  Eight selected ragas are in the broader vocabulary; seven are in the 56-class
  vocabulary. About 380 MB compressed of CC-BY source audio is needed. The
  source currently returns repeated HTTP 504s; its alternate official route
  also timed out, and a metadata request returned 429. No new AV score exists.
- Added capped transient range retries without full-archive fallback, and
  required frozen-download receipt hashes before AV extraction/scoring. The
  latest full suite passed 329 tests with one expected failure.
- A pinned MIT-tagged RMVPE ONNX model downloaded and passed its publisher SHA256
  verification after resuming an interrupted transfer. Local CPU inference
  uses ten-second central chunks with one-second context, not remote code.
  An actual ten-second 220 Hz tone produced 1,000 voiced frames, median 220.24 Hz
  (1.89 cents error), in 5.25 seconds. On the six labeled field queries, with
  identical original-mix tonic estimates and unchanged classifiers, all three
  models scored 3/6. The best Melodia candidate scores 4/6. RMVPE recovered some
  items but lost Varali; it is not adopted. The default frontend and frozen
  eight-artist test protocol remain unchanged.
- Derived audio-cache writes now use unique temporary files and atomic replace.
  A simulated failed write preserves the previous valid feature file. Raw audio
  and the user's label file are untouched; the original label SHA still matches.
- Latest full suite: 333 passed, one expected failure. Two subsequent pitch-
  activity descriptor tests passed separately.
- Pitch-only activity classifier, fixed C=.1 and threshold .5: artist-held-out
  9/16 correct on the existing public section excerpts (tani recall 25%, melodic
  recall 66.67%). The full fit scores 135/148 labeled ten-second windows in the
  first concert (tani recall 94.12%, melody recall 88.75%). This mixed evidence
  demonstrates the field/domain mismatch, not production reliability. Neither
  the pitch detector nor the earlier AudioSet-relative gate is enabled by default.
- Expanded section audit found two tani sections spelled tani_avartana that
  the earlier "all tani" evaluation omitted. There are six annotated tani
  sections across four artists, not four sections. Tanam/thanam remains melodic,
  not percussion. The old 16-excerpt evidence is preserved; future AudioSet
  section checks write a separate v2 report.
- Expanded pitch-activity training uses three fixed 10-second queries per
  supported annotated section: 930 windows / 310 sections / four artists.
  Artist-held-out window recall: tani 88.89%, melody 95.61%. Section-averaged
  decisions: 306/310 correct, all six tani sections correct. These windows are
  correlated, not 930 independent examples. Full-fit field result: 137/148
  labeled windows correct, tani recall 92.65%, melody recall 92.5%.
- Exact ten-second field extraction scores 136/148 (tani recall 91.18%, melody
  92.5%), versus the default AudioSet tags' 118/148 on the same windows. This
  separate report avoids the initial 60-second contour-slicing mismatch.
- Added optional `--pitch-activity-model` and an activity-only replay command.
  The temporal decoder now preserves optional probability evidence rather than
  hardening barely-positive scores to .995. Default behavior is unchanged.
  On concert 1, the replay produces music 0–760, percussion 760–1440, then
  music through EOF. Existing tani truth is 755–1440. Duration-weighted activity
  accuracy on 1,501 explicitly labeled seconds is 99.67%, versus 89.01% for
  the original decoded timeline. This is a repeatedly inspected single-concert
  development result, not independent evidence, song segmentation accuracy, or
  raga accuracy. Raga probabilities are copied unchanged and remain unreliable.
- Added a reusable interval scorer: unlabeled time is excluded, missing coverage
  counts as error, overlapping intervals fail closed, and audio/label/report
  provenance is verified. Its tests cover fractional boundaries and denominators.
- Fixed a second temporal bug: distinct adjacent nonmusic activities no longer
  collapse to a majority tag simply because all share an unknown-raga state.
  A regression test preserves consecutive speech, applause and silence regions.
- Frozen a continuous activity diagnostic around all six public tani sections:
  336 ten-second queries with 60-second context margins, leave-artist-out fits,
  fixed .5 threshold and switch penalty 6. Annotation-centered query selection
  is explicit; this is not full-concert automatic-discovery evaluation.
- Completed that fixed diagnostic in 583.56 seconds: 3,313.74 explicitly labeled
  seconds, four held-out artists, six tani regions. Duration-weighted accuracy
  improves from raw 80.89% to decoded 95.18%; tani recall 77.60% to 94.36%,
  melody recall 97.44% to 99.26%. Five regions improve, one regresses (92.19%
  to 89.25%, chiefly delayed onset). Three regions share Sanjay's held-out
  artist fold; neither seconds nor regions are independent artist samples.
  Predictions and the pre-extraction protocol are preserved under
  `data/overhaul/activity_boundaries/`. This supports optional development use,
  not default promotion or a production accuracy claim.
- The integrated exact-query frontend plus optional activity model passed a
  180-second smoke test: six cached raga queries, one melodic region, uncertain
  raga identity, 0.83 seconds warm-cache elapsed. This excludes cold extraction
  and is not end-to-end real-time throughput. Five-stage CLI opt-in routing is
  unit-tested; the default remains unchanged.
- Latest clean full-suite run: 354 passed, one expected failure, one legacy
  Gemini SDK deprecation warning. An earlier concurrent-edit run loaded the
  pre-fix decoder and failed the newly added test; the fresh run passes it.
  The user label SHA remains unchanged and the scoped diff check passes.
- All 11 frozen recordings passed beginning/middle/end bounded decoding checks:
  33 ten-second reads in 5.24 seconds, measured process peak RSS 76 MB. This is
  decoding/latency evidence, not classification accuracy or complete segmentation.
- Public ZIP downloads now optionally persist checksum-protected range blocks,
  scoped by URL, size, block size and archive checksum. Completed WAVs can be
  verified fully offline. Tests cover cache resume, corrupt-cache refetch, and
  no network use for an already-completed selection. No full-archive fallback.

### Song discrimination and rejection follow-up

- Whole-reference regression reproduces 19/27 top-1 and 22/27 top-5, with
  all 181 queries retained (154 have no independent-artist work reference).
- A composed-section reference arm scores 17/27 top-1 and 22/27 top-5.
  Correcting an omitted muktayi-swara label leaves those results unchanged.
  Separate passages are never joined across excluded time; unannotated
  recordings retain whole-reference fallback. This arm is not adopted.
- Three independent query passages with one shared global pitch shift score
  17/27 top-1 and 21/27 top-5. Relaxing phrase order did not help; not adopted.
- Rejection cross-fitting unions shared artists, sources and work identities.
  The 181 queries form only five connected components; all 19 correct matches
  fall in two of them. Neither distance proximity nor relative margin achieves
  a 90% calibration-precision target with at least ten answers in any fold.
  Both therefore abstain throughout. This is infeasibility, not certified
  precision or a usable production gate; no gate is exported.
- Added a bounded, rate-limited public MusicBrainz lookup for local CompMusic
  recording IDs, with immutable input plan and per-record receipts. Only an
  explicit single performance-to-work relation can qualify a future reference;
  title resemblance is not identity evidence. Multi-work recordings quarantine.
- Full suite after the retrieval arms: 362 passed, one expected failure. Five
  subsequent rejection/provenance tests pass separately. The initial public
  recording lookup returned HTTP 503; no work identities were admitted. The
  Zenodo audio source also continues to return HTTP 504 outside the sandbox.
- Latest full suite after metadata-outage regression coverage: 368 passed,
  one expected failure, one legacy SDK warning. Refreshed AST inventory covers
  321 Python files, with only the three previously known Colab-magic parse
  failures and 19 exact duplicate groups. The label hash and scoped diff check
  remain clean. The frozen CompMusic metadata plan contains 477 local pitch
  references; zero public work links have been obtained so far.

### Verified reference expansion after source recovery

- MusicBrainz recovered intermittently. Completed receipts survive later timeouts;
  the progress report now checkpoints every recording. Transport failures and
  HTTP failures remain distinct from absent works. Requests are spaced at least
  three seconds apart, with at most three attempts and 10/20-second backoff.
- Built a separate partial catalog from the first ten explicit work relations:
  191 references / 171 identities, with the source lookup snapshot, catalog,
  receipt, pitch and tonic hashes preserved. No title-based work matching is used.
- On the same 181 Saraga queries, two additional works become answerable:
  Dinamani Vamsa and Vanajaksha Ninne Kori. Both rank first. The original
  answerable cohort remains 19/27 top-1; expanded coverage yields 21/29 top-1
  and 24/29 top-5. Overall correct identifications are 21/181, not 21/29 of all
  queries. This remains development evidence with no validated rejection gate.
- The metadata resolver is continuing through the frozen 477-recording plan.
  Partial artifacts are explicitly marked incomplete and do not replace the
  deployed or default catalog. Additional reference evaluation excludes shared
  artist aliases and sources, and requires the catalog's exact 0.5-second frame
  contract.
- Full suite after the verified-reference extension and timeout recovery:
  371 passed, one expected failure, one legacy SDK warning. User labels remain
  byte-identical. The metadata process was confirmed live beyond 32 checked
  recordings; it should be polled, not restarted merely because a turn ends.

### Cross-corpus recording identity guard

- Saraga's distributed metadata supplies 184 unique recording IDs for the 184
  local evaluation tracks. Unlike the AV metadata's artist-level IDs, none of
  these repeat or coincide with the declared album artist IDs.
- There are 37 exact recording overlaps with the 477 CompMusic references.
  All are already caught by the artist exclusion; no measured gain was caused
  by one of these duplicates. Added explicit recording-ID exclusion plus source
  metadata hashes as a second guard. Original manifests are not rewritten.
- The first-ten-reference benchmark with this guard reproduces 21/29 top-1
  and 24/29 top-5. Tests reject artist IDs used as recording IDs, changed work
  annotations, and absent-ID equality. The metadata fetch remains live and has
  passed 83 checked recordings; future turns must poll its existing handle.
- Full regression suite after the explicit recording guard: 374 passed, one
  expected failure, one legacy SDK warning.

### Fixed first-100-recording checkpoint

- The fixed recording-ID-sorted prefix contains 83 unique-work links and 17
  unresolved/multi-work cases. Nine linked recordings are already in the base
  catalog. The deduplicated candidate therefore adds 74 recordings, for 255
  references / 224 work identities. Original duplicate-containing and unique
  artifacts are preserved separately; their top-1/top-5 counts agree.
- On the unchanged 181 queries, 38 now have eligible independent references;
  24 rank first and 28 rank in the top five. Seven of eleven newly answerable
  queries rank first, but two prior hits are displaced: the original cohort
  falls from 19/27 to 17/27. Overall correct identifications rise from 19/181
  to 24/181; conditional accuracy is 24/38, not a production accuracy claim.
- Both predeclared connected-group rejection arms still find the 90%-precision,
  ten-answer calibration target infeasible and abstain throughout. No default
  catalog or gate is changed.
- Builder now supports frozen lookup snapshots plus an explicit receipt
  directory, and excludes duplicate recordings before feature loading. A
  conflicting work identity for the same recording is quarantined, not merged.
- The metadata lookup remains live beyond 165 checked recordings. The fresh
  eight-artist audio source has also recovered enough to transfer data: its
  first partial WAV grew from about 80 MB to 130 MB. Neither a partial WAV nor
  a live transfer is treated as a verified test input or a new score.
- Latest full suite: 375 passed, one expected failure, one legacy SDK warning.

### Estimated-raga ranking preference

- A fixed .1 bounded ranking penalty uses only the independent broader model's
  estimated raga posterior, and only above its existing development confidence
  gate. No query title or annotated query raga enters ranking; unknown reference
  ragas remain eligible. The prior was applied on 80/181 queries.
- On the fixed first-100 unique catalog, top-1 improves from 24/38 to 26/38 and
  top-5 from 28/38 to 31/38. Three matches improve and one regresses. This is a
  repeatedly inspected development ablation; no default inference change.
- Rejection explicitly uses the joint ranking cost rather than unsorted raw
  distances. Both connected-group calibration arms remain infeasible at the
  same 90%-precision/ten-answer requirement; no production gate is exported.
- Full suite after the ranking prior: 378 passed, one expected failure. Seven
  targeted ranking/rejection tests pass after adding the explicit score-field
  check. Two fresh AV WAVs are checksum-verified and their 180-second features
  cached without predictions. Remaining transfers are being resumed from cache.

### Generic work entities are not necessarily compositions

- One later MusicBrainz relationship identifies “Kedaragaula Ragam,” a generic
  improvisation entity. A single work relationship alone is therefore not a
  sufficient composition-reference admission rule. Added narrow exclusion of
  explicit raga/improvisation-only work titles; no raw features are removed.
- This excludes none of the measured first-100 checkpoint's work links, so its
  counts and predictions remain unchanged. Tests distinguish those generic
  entities from named compositions and titled tillanas.
- The audio download has two complete verified WAVs and cached features, with
  a partial third file retained through subsequent HTTP 504 failures. Metadata
  collection remains live beyond 256 recordings. Neither process completion nor
  fresh-test accuracy is claimed from partial progress.
- Full suite after the explicit ranking-score and improvisation checks: 380
  passed, one expected failure, one legacy SDK warning. Metadata collection was
  confirmed live past 272 recordings. The latest audio resume terminated on
  HTTP 504 with two verified WAVs retained; it is resumable, not currently live.

### Exact song frontend and completed fresh artist evaluation

- Song inference previously sliced the first 60 seconds of a longer raga
  extraction, borrowing its tonic. It now uses the exact independent query
  contract, reusing only already matching short contexts. Song extraction and
  retrieval are independent of successful raga feature construction.
- Three new contract tests cover re-extraction, short-query reuse and recording
  identity rejection. Full suite: 383 passed, one expected failure, one legacy
  SDK warning. The 180-second concert smoke completed six song windows in 109
  seconds, with no asserted raga answers. Warm 255-reference ranking was about
  0.15 seconds; cold DSP/startup latency remains separate and not isolated.
- All eight fresh AV recordings were downloaded and verified before scoring
  the previously frozen comparators. Combined, multiscale and broader each
  score 6/8; forest800 scores 5/8. On the seven shared-vocabulary recordings,
  this is 6/7 versus 5/7. Combined accepts six, all correct; multiscale and
  broader each accept five, all correct. These small counts do not establish
  production precision, natural-prevalence rejection or SOTA performance.
- The immutable result includes model, plan and audio hashes. Do not tune
  against these outcomes and retain a fresh-test claim for subsequent models.
- The metadata import was confirmed live beyond 393/477 recordings. No manual
  labeling, paid compute, raw-audio deletion or deployed-model change occurred.

### Remove redundant block melody extraction

- Default exact-query inference now caches activity-only blocks in a separate
  `concert_mix_events_only_v2` namespace. It no longer runs a discarded block
  Melodia/tonic pass. The legacy diagnostic path retains its original namespace
  and complete contours; old caches are not overwritten or reinterpreted.
- An automated main-entry-point test fails if the default path invokes block
  pitch/tonic extraction, then checks cache resume and unchanged outputs. Eight
  targeted frontend/pipeline tests passed.
- Actual three-minute concert output has exactly equal events, windows and
  segments to the preceding exact-query smoke. The run took 26.5 seconds with
  query features already cached; it is not a matched cold speedup benchmark.
- The metadata process exited normally at 419/477 after consuming its bounded
  request-attempt budget. It was then resumed from validated local receipts.
- Full suite after the events-only cache change: 384 passed, one expected
  failure and one legacy SDK warning, in 109.96 seconds. The label file SHA-256
  is unchanged; 109 GiB disk space remains available.
- Concert inference also now applies the existing runtime-only serial forest
  safeguard used by evaluation, avoiding the observed Python warning-filter
  race on small queries. Three targeted cache/runtime tests pass after this
  addition; persisted weights and model files are unchanged.

### Complete verified CompMusic reference expansion

- The fixed 477-recording lookup is complete: 392 single-work relationships,
  83 absent links and two ambiguous relationships. Raw response receipts and
  their derived plan/result hashes are retained.
- The full builder adds 353 performances to the original 181, giving 534
  references / 423 work identities. Exclusions: 37 duplicate recordings,
  85 unresolved/ambiguous links and two generic improvisation work entities.
  No conflicting work identity for the same recording was encountered.
- Artifact: `data/overhaul/compmusic_compositions_full_unique.npz`, SHA-256
  `4857e4879d666e62071f08210627b71c245e61178870d23fb8db47351bab1a26`.
  The source-links snapshot is complete, not a selected partial checkpoint.
- Fixed 181-query melody-only and .1 estimated-raga-prior comparisons were
  completed against this catalog. Answerability is 53/181. Melody-only scores
  24/53 top-1 and 35/53 top-5; the fixed prior scores 30/53 and 39/53. Overall
  correct identification therefore rises from 19/181 originally to 30/181,
  not 56.6% across all queries. Both connected-group rejection signals remain
  infeasible in every fold, so no gate is exported.
- A subsequent fixed-context ablation uses exact centered 180-second cached
  queries, independently extracted melody/tonic, and unchanged references.
  Cache checks enforce recording hash, extraction profile, center and complete
  expected boundaries. This is not three subdivisions of a 60-second query.
  Both unchanged ranking policies completed: melody-only 32/53 top-1 and 40/53
  top-5; estimated-raga prior 37/53 and 43/53. Relative to the 60-second prior,
  nine queries improve and two regress. Overall correctness is 37/181, not
  69.8% across the corpus. Runtime was 235.5/250.0 seconds with cached features.
  On the same 53 answerable queries, a 5,000-resample primary-artist cluster
  bootstrap (seed 42, 15 artist groups) gives a +13.21 percentage-point mean
  gain with 95% interval [0.00, +30.96] points. It reaches zero and is not
  independent production evidence.
- Connected-group rejection still fails: distance proximity abstains in both
  arms; melody-only margin accepts five with four correct (80%), while prior
  margin accepts one incorrect unknown-work query. This is evidence against
  promoting a gate despite better ranks. Default inference stays at 60 seconds
  for song queries; no default catalog or model has been promoted.
- All 184 original 60-second cached queries pass the new provenance checks with
  unchanged contours. Full suite after exact-context support: 391 passed, one
  expected failure, one legacy SDK warning, in 168.08 seconds.

### Wire the measured song configuration into candidate inference

- Added independent exact song context (60/180 seconds) and a fixed .1
  estimated-raga preference as explicit concert inference options. The selected
  raga model processes the exact song query; low-confidence posteriors do not
  affect ranking. No annotated query raga is consumed.
- `CompositionCatalog.rank` retains raw distances and ranking costs, applies
  the penalty before work-level rendition deduplication, and skips infeasible
  alignments. Default ranking and context remain unchanged.
- The unified pipeline forwards the optional context, prior and alternate
  catalog. README includes the measured broader-model/full-catalog invocation.
- Fourteen targeted tests pass; full suite: 395 passed, one expected failure,
  one legacy SDK warning, in 115.56 seconds.
- First-concert 180-second smoke completed six cached windows in 3.53 seconds,
  with no asserted identities. No window passed the raga prior gate, and the
  labeled composition was not identified. This is an integration check, not a
  new accuracy improvement. The second-concert smoke completed in 120.24
  seconds, also with six abstained priors and zero asserted raga answers.
  Neither real smoke exercises an active prior; the controlled integration
  test explicitly verifies forwarding a threshold-passing posterior through
  song ranking, along with cache resume and end-of-recording clipping.

### Matched vocal-separation diagnostic (September 9)

- Historical cached field scores did not support default Demucs adoption:
  combined-model top-1 was 14/29 versus mixed-audio 15/29, with unresolved
  source/artist provenance. A separate matched test now uses the six fixed
  explicit concert queries, unchanged original-mix tonics and frozen models.
- The already-cached htdemucs checkpoint is authenticated before upstream
  deserialization: SHA-256
  `8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4`.
  No model download or network service is used. CPU inference uses four Torch
  threads, zero random shifts, split inference and .25 overlap. Cache identity
  includes model hash, query boundaries, package versions and frontend settings.
- A real ten-second clip produced 441,000 finite vocal samples in 8.53 seconds.
  Tests cover wrong-checkpoint rejection before deserialization, bounded finite
  input, silence, restored normalization and input preservation. Full suite:
  398 passed, one expected failure, one legacy SDK warning in 163.85 seconds.
- The six-query separation run completed: combined 4/6 (unchanged), broader
  4/6 (was 3/6), forest800 4/6 (was 3/6). Shankarabharanam remains wrong and
  Dhenuka remains out of vocabulary. Query boundaries, original-mix metadata,
  label manifest and all model hashes exactly match the mixed-audio comparator.
  A complete cache replay produced a byte-identical result report.
- An additional cached historical field check for the broader model scores
  14/29 in all three arms (mix, vocal-band mix, Demucs). Demucs accepts nine
  at the existing development gate, eight correct, versus mixed audio's 15
  accepted with 11 correct; this is a coverage tradeoff on a provenance-limited
  diagnostic, not production precision. No separation default is adopted.
- The controlled active-prior integration test from the preceding change also
  completed: all 14 targeted frontend/catalog/pipeline tests passed.
  Separately, exact-fold label checks find no Dhenuka rows in the available
  archive matrix or full CompMusic plan; lowering admission thresholds alone
  cannot resolve that class's coverage gap.

### Directional-control retrieval hypothesis

- A fixed ablation compares forward DTW with the same query-time costs in
  reverse order. Both use exactly the same candidate pitch shifts, preventing
  floating-point marginal-pitch ties from changing the control condition.
  The score is forward/(forward+reverse), with zero/zero assigned .5 rather
  than falsely treated as strong directional evidence.
- The existing forward-distance implementation is numerically preserved.
  Thirteen targeted alignment/rejection tests passed, including tempo,
  transposition, stationary-pitch and invalid-input cases.
- Both 180-second, 181-query full-catalog arms completed. Melody-only remains
  32/53 top-1 and scores 39/53 top-5 (previously 40). With the unchanged .1
  raga preference, top-1 remains 37/53 and top-5 rises to 46/53 (previously 43).
  Eight top-1 gains offset eight losses. Runtime was 330.7/344.8 seconds.
- Connected artist/work rejection still fails: without the prior both signals
  accept nothing; with it, proximity accepts one incorrect query and margin
  accepts nothing. No threshold or default inference setting is promoted.
  Rejection explicitly consumes ranking cost, not unsorted raw distance.
- Full suite: 401 passed, one expected failure, one legacy SDK warning in
  159.51 seconds. The expanded catalog also yields no exact normalized work-
  title joins for the six existing high-confidence field items; approximate
  title matches are not silently converted into evaluation ground truth.
- Existing ASR caches were checked for reuse: v2 has 546 entries, Indic mix
  and stem have 106 each, with zero exact full-audio hash matches to the 184
  Saraga query recordings. This does not prove no related excerpts exist, but
  it supplies no verified same-query join; cached text is not attached by
  approximate filename or treated as independently aligned evidence.

### Bounded offline sung-ASR pilot

- Existing ASR text could not be joined to the benchmark by exact recording
  hash, so a new isolated pilot records exact query boundaries, audio/waveform
  hashes, decoder settings and raw diagnostic fields. It never prompts with
  a title, raga, lyric or other query truth.
- The existing local Whisper large-v3-turbo checkpoint is SHA-256 verified
  against the digest in the installed publisher model URL before loading its
  explicit path. No download or paid transcription service is used. CPU,
  greedy decoding, temperature zero and no previous-text conditioning are
  fixed in the plan. Every transcript remains an unverified hypothesis.
- The fixed track-hash-first ten-second query ran in 14.55 seconds and emitted
  “Say Pamaga,” detected as English, with average log probability -1.53. This
  does not demonstrate lyric recognition or word accuracy. The eight-query
  fixed-prefix pilot completed in 122.53 seconds: all eight were detected as
  English, with short generic outputs and one severe repetitive hallucination
  despite average token log probability near -.15. Token score alone is not
  a reliable acceptance signal on this music.
- A follow-up keeps the same eight recordings, uses native 30-second context
  and fixed auto/Tamil/Telugu/Hindi lanes applied to every query. No query
  metadata selects the language, and every hypothesis is preserved rather
  than choosing the longest string. All eight queries completed. A separate
  title-only probe screens segment log probability, no-speech probability and
  compression ratio, then uses transliterated character 3–5-gram TF-IDF against
  catalog titles. It finds usable text in 6/8 queries, top-1 matches in 2/8 and
  top-5 in 3/8. All eight truth titles are in this text vocabulary. This is a
  closed metadata-title-vocabulary development diagnostic, not WER, a fresh
  test, or cross-rendition audio retrieval; its denominator is not the 53
  independently answerable melody queries. No ASR default or gate is enabled.
- Two unit tests cover checkpoint rejection, bounded/finite audio, silence,
  unprompted decoding and preservation of raw model diagnostics.
  Full suite before the language-lane extension: 403 passed, one expected
  failure, one legacy SDK warning in 150.72 seconds; both targeted ASR tests
  also pass after adding the fixed-language option.
- Four targeted tests now pass, including rejection of repetitive,
  diagnostic-free and punctuation-only hypotheses and preservation plus
  transliteration of native Indic text. Results are recorded in
  `data/overhaul/sung_asr_pilot30_title_results.json` with source hashes.
- Full suite after the ASR title probe: 405 passed, one expected failure,
  one legacy SDK warning in 102.96 seconds.

### Legacy lyrics registry admission

- Tracing possible lyric evidence uncovered 14 unsupported concert/event
  header rows among 8,688 legacy entries. Examples include AIR Chennai with
  `9-9-2002` as its raga and a Mysore address with `Sept 13, 1997` as its raga.
  The builder admits weak source fields and assigns sequential local IDs;
  these are not MusicBrainz work identities and cannot be joined as such.
- `registry_hygiene.py` now conservatively filters at consumption only when
  all raga fields contain calendar years and the row has no recording,
  lyric-page, lyric, or composer support. Unknown/absent raga names are not
  rejected. `identify_clip.load_targets` uses the guard; no source registry
  or reviewed IDs are rebuilt, renumbered, or overwritten.
- Two tests cover conservative admission and end-to-end target loading with
  stable IDs and unchanged source bytes. Both pass. The source-hashed audit
  is `data/overhaul/registry_header_audit.json`. This removes demonstrated
  false candidates; no accuracy gain is inferred without a benchmark.
- Actual target loading retains 8,665 entries (the pre-existing short-title
  filter also applies), excludes all 14 headers, and preserves the registry
  checksum. The manual-label SHA remains
  `a0d137ea236e48b7cab710feff1abb7f8fc42fa46ce8c0b3877bb023263e44bb`.
  Approximately 109 GiB of local disk remains free; no external spend is needed
  for these checks.
- Final combined suite: 407 passed, one expected failure, one legacy Gemini
  SDK deprecation warning in 103.10 seconds. Scoped whitespace checks pass.

### Synthetic concert transition stress test

- A frozen source/model-hashed fixture concatenates three track-hash-selected,
  distinct in-vocabulary 90-second excerpts (Nata, Ritigaula, Anandabhairavi)
  with two 10-second digital-silence gaps. This is a 290-second synthetic
  development stress test, not natural-concert or untouched test accuracy.
  No predictions select sources or boundaries, and no manual labels are added.
- Fixed 60-second context correctly ranks ragas over all 270 musical seconds;
  180-second context scores 180/270. Pure-query scores are 5/5 and 2/2,
  respectively, which alone would conceal the longer-context regression.
  Mixed-item query counts are 3/9 versus 7/9. All identities remain unasserted.
- An explicit `--silence-bounded-context` inference option first capped at
  existing silence tags. It had no effect: both true silent gaps were tagged
  uncertain. Reproducing the block resampling shows whole-gap RMS 3.42e-5,
  above the 1e-5 silence threshold, despite interior RMS exactly zero.
- The optional policy now independently checks finite event audio after
  trimming 50 ms from each edge, with the same 1e-5 RMS threshold. Interior
  transients and merely quiet signals do not pass. It leaves shared event
  caches and default inference unchanged. Both raga and composition context
  obey detected boundaries. The energy-cap-only run removes mixed queries
  and scores 240/270 musical seconds; missing coverage is 20+10 seconds after
  pauses because the fixed query grid does not start at item onsets.
- A follow-up adds query anchors at detected silence ends (not annotated
  boundaries), preserving the failed and partial runs. It restores 270/270
  correct musical seconds with full candidate coverage, zero mixed queries,
  and zero asserted identities. Ten queries are pure, eight correct; the
  timeline uses overlapping evidence and has a different denominator.
  All 11 actual raga/song query bounds obey the detected pauses. Song ranking
  is exercised only as an integration check, not a cross-rendition score:
  the synthetic sources may occur in the reference catalog.
  This conservative detector is not semantic song segmentation and may miss
  noisy pauses; synthetic results do not justify enabling it by default.
- Full suite before the anchor extension: 413 passed, one expected failure,
  one legacy SDK warning in 112.95 seconds. Query scoring retains missing
  predictions in denominators and never assigns dominant-raga gold labels
  to mixed-item contexts.
- After adding anchors, all 21 targeted transition, pipeline-command and
  temporal-decoding tests pass. The manual-label checksum is unchanged and
  scoped whitespace checks pass. No deployed artifact or default is changed.

### Natural silence transfer and remaining tonic fallbacks

- A frozen, resumable activation audit scans all 11 existing natural concert
  recordings in bounded 10-second queries. It checks source hashes and uses
  the exact interior-energy policy, without consuming manual labels. The
  full scan completed in 452.58 seconds: 35,461.47 seconds / 9.85 hours,
  3,553 windows. This measures activation, not boundary precision/recall.
  Ten recordings have no qualifying silence. Concert 3 has 11
  consecutive quiet windows at 2220–2330 seconds, consistent with an already
  documented muted region, not proof of semantic item-boundary detection.
  No threshold was relaxed after inspecting these outcomes. The current
  policy cannot solve general natural-concert item boundaries. A cached
  replay verifies source hashes and reproduces the same activation counts.
- Tracing the older UI/backend path found remaining median-F0 tonic fallbacks.
  `FeatureExtractor` now raises an explicit error when tonic estimation is
  absent or fails instead of substituting the phrase median. The full-clip
  loader now shares the finite, anti-phase-safe downmix policy with windowed
  ingestion; it remains a full-clip API, not a bounded concert-memory claim.
- `/predict-audio` requires a valid tonic before Demucs and fails with HTTP
  422 if unavailable. `/identify` preserves independent lyric candidates but
  cannot emit tonic-dependent raga predictions without a tonic. Both median
  and arbitrary-130-Hz fallbacks are removed. Mixed-audio tonic context is
  now the same first 60 seconds used for these routes' raga features.
  No backend deployment or model artifact overwrite was performed.
- The 23 targeted audio/fallback tests pass. The full suite including the
  feature-extractor and loader changes (before the final backend tests)
  passes 417 tests, with one expected failure and one legacy SDK warning in
  125.22 seconds.
- All five targeted backend/feature fallback and phase-safe loader tests pass
  after the backend changes. The backend tests execute the tonic guard and
  check route ordering/no-median structure without starting ASR or a server;
  they are not a deployed HTTP integration test. Source files compile and
  scoped whitespace checks pass. The original manual-label SHA is unchanged.

### Browser-upload phase handling and local HTTP verification

- All eight backend audio loads now use an explicitly bounded upload decoder:
  native channels are decoded first, shared phase-safe downmix is applied,
  and mono audio is resampled once. Browser WebM/audioread fallback is retained;
  bounds are 5, 60 or 90 seconds. The windowed corpus loader shares the same
  downmix function with numerically unchanged policy.
- A real 10-second stereo anti-phase tone is encoded to WebM/Opus locally.
  Five-second decoding retains the 220 Hz pitch and >.1 RMS, exceeding the
  legacy channel-average decode RMS by more than 20x. Ordinary stereo means,
  invalid layouts, finite checks and explicit bounds are also tested.
- Local FastAPI tests (no running server, external calls, model downloads,
  or feedback writes) confirm HTTP 422 before separation when tonic is missing,
  preservation of independent lyric candidates with an empty raga list, and
  cleanup of temporary uploads in both cases.
- The Space assembly copy list now includes `registry_hygiene.py`, required
  by the shared matcher. The destructive staging script was not executed and
  nothing was deployed. Nine targeted upload/backend tests pass, with codec
  fallback and existing dependency-deprecation warnings. Full suite completes:
  426 passed, one expected failure, nine warnings in 100.89 seconds. No manual
  labels changed; scoped whitespace checks pass.

### Pinned MusicFM encoder feasibility

- MusicFM-MSD source, normalization statistics, configuration and the 1.32 GB
  checkpoint are pinned to publisher revisions. Interrupted network transfers
  resumed from saved byte offsets; the completed checkpoint matches publisher
  SHA-256 `218b483a0256ddef736267425fabb166fd97008983696bb9270def464b47bded`.
  Source modules and full upstream license are retained unmodified.
- The local CPU-only frontend verifies source/config/weight hashes before
  importing the reviewed modules. It uses local configuration and restricted
  checkpoint loading, with no inference downloads. The unused output head,
  quantizer and CLS state are explicitly accounted for; encoder state loads
  strictly. An older weight-normalization naming convention is migrated
  exactly; a convolution-equivalence test verifies the migration.
- A fixed ten-second, source-hashed Saraga query produces finite 250x1024
  frame features and a 1024-dimensional temporal mean. Observed loading /
  inference times were 12.48 / 20.24 seconds initially and 10.16 / 9.66 seconds
  on repeat, using four CPU threads. These are observed wall times, not an
  isolated throughput guarantee. The resulting NPZ files are byte-identical.
- Runtime: Torch/Torchaudio 2.5.1, Transformers 4.44.2 from the existing isolated
  runtime dependencies, Einops 0.8.2. Input is explicitly finite mono 24 kHz,
  1–30 seconds. Three targeted tests pass. Full suite: 429 passed, one expected
  failure, ten dependency/codec warnings in 184.01 seconds. Source/label
  preservation and scoped whitespace checks pass; 107 GiB remains free.
- This establishes feasibility and repeatability only, not tonic invariance,
  raga/song accuracy, improved boundaries, or production eligibility. No model
  has been promoted. Next useful evidence is a matched grouped representation
  benchmark, not a claim based on pretrained-model reputation.

### Matched MusicFM/pitch grouped ablation

- A new frozen plan admits 31 unique recordings across five single ragas
  (Bhairavi, Behag, Khamas, Todi, Saurashtram) after exact-audio duplicate and
  conflicting-label checks, excluding Ragamalika and requiring at least five
  recordings per class. There are 13 connected artist/source groups; every
  class spans at least four groups. No prediction selects the sources.
- Both representations consume the exact same centered ten-second region.
  Pitch uses estimated tonic from that region, never annotated tonic or a
  longer neighboring context. Frozen MusicFM layer-7 frames are averaged over
  time. The three fixed arms are pitch, MusicFM, and concatenated features,
  using class-balanced RBF kernel ridge (alpha .1, gamma 2) on L2-normalized
  vectors. There is no held-out hyperparameter selection or identity gate.
- Connected groups are left out intact. Missing pitch features and classes
  absent from a training fold remain in evaluation denominators. Bootstrap
  comparisons use the same connected groups. This is selected-vocabulary,
  repeatedly inspected development data, not broad natural-concert accuracy
  or a composition-held-out/generalization guarantee.
  Overlap between MusicFM's original pretraining data and these recordings
  has not been independently audited; encoder pretraining is not claimed to
  be proven disjoint merely because the fitted classifier heads are grouped.
- Extraction completed for all 31 recordings, with valid pitch features on
  all 31. Pitch-only scores 12/31 (38.71%; macro recall 38.86%), raw MusicFM
  scores 8/31 (25.81%; macro 25.14%), and combined scores 11/31 (35.48%; macro
  36%). This fixed frozen-layer/pooled-representation setup does not improve
  the pitch baseline; no model is exported or promoted. It does not rule out
  tonic-normalized inputs, temporal modeling or supervised fine-tuning.
- Runtime was 459.58 seconds. All three full crossfit results reproduce exactly
  from saved features. Connected-group bootstrap differences versus pitch are
  -12.90 percentage points for MusicFM (95% interval -39.41 to +14.29) and
  -3.23 points for combined (-18.75 to +8.70). Both intervals include zero;
  the small experiment establishes no reliable positive gain.
- Three targeted admission/grouping/scoring tests pass. Full suite: 432
  passed, one expected failure, ten dependency/codec warnings in 284.26 seconds
  while feature extraction was also running.

### Estimated-tonic-normalized MusicFM ablation

- The same 31-query, five-raga, 13-group protocol now has a separate normalized
  arm. Input audio is shifted by the smallest pitch-class displacement in
  [-6,6) semitones that maps estimated Sa to A, retaining the nearest register.
  Tonic comes only from the exact ten-second query's cached extraction.
  Annotated tonic, query raga and longer-context estimates are not inputs.
- The librosa phase-vocoder/resampling parameters and version are frozen in
  a separate plan. Original waveforms, raw embeddings and prior results stay
  unchanged. Missing tonic would abstain for normalized embeddings rather
  than silently substitute raw input. Eight targeted tests pass, including
  octave equivalence, no arbitrary fallback, preserved duration, correct
  pitch-shift direction and unchanged input arrays.
- A read-only diagnostic against existing public tonic annotations finds
  22/31 estimates within 50 cents modulo octave, with median absolute error
  5.91 cents. These annotations are not consumed by the transformation; the
  larger errors remain in the experimental cohort rather than being filtered.
- Normalized extraction completed in 202.59 seconds. MusicFM scores 9/31
  (29.03%; macro recall 28%), combined scores 12/31 (38.71%; macro 38.86%),
  and the unchanged pitch control scores 12/31. The original raw arms scored
  8/31 and 11/31. This recovers one match in each arm, but yields no improvement
  over pitch alone. All full crossfit outputs reproduce exactly from saved
  features, and the pitch control is identical to the prior result.
- Group-bootstrap differences versus pitch are -9.68 points for normalized
  MusicFM (95% interval -27.78 to 0) and zero for combined (-15.79 to +14.29).
  No model is promoted. Classifier, groups and denominators remain unchanged.
  Full suite: 434 passed, one expected failure, ten dependency/codec warnings
  in 242.84 seconds. Original labels and raw-arm artifacts remain unchanged.
- A path-availability check of the broader training manifest finds 971 local
  archival audio files among 1,353 training rows, with 971 distinct paths;
  the 382 CompMusic pitch-only rows have no local audio. This is only an
  availability inventory, not yet an authenticated audio-to-label/source join
  or authorization to claim stronger data independence.

### Raw archival byte audit: evaluation leakage confirmed

- `scripts/audit_archive_audio_identity.py` hashes all 971 broader-training
  archival files with MD5, SHA1 and SHA256. Cached metadata matches require
  exact size and MD5 plus SHA1 whenever available; no title/size-only proof.
  Output: `data/overhaul/archive_audio_identity.json`, pinning all 1,857 cached
  metadata files and the input manifest.
- 515 assigned archive sources match cached bytes; four assignments disagree
  (Kapi, Latangi, Mukhari, Suddhadhanyasi tracks assigned to
  `NeeveRakshavarnamKadanakuthoohalam` actually match `DP-007` cached bytes).
  Another 452 files have no exact cached match; many listings omit hashes.
  This is unresolved provenance, not evidence that those files are corrupt.
- 49 exact-byte duplicate sets contain 106 training rows. All already share
  their respective connected split groups and labels. No cross-group duplicate
  leakage was found by this check, but duplicated weighting remains relevant.
- CRITICAL: joining local SHA256 to existing Saraga evaluation audio receipts
  finds 26 broader-training rows / 15 evaluation files, and 16 combined-training
  rows / nine evaluation files. Existing Saraga accuracy and rejection results
  must not be cited as fully recording-disjoint. Track-name and contour-hash
  guards did not detect these byte-identical raw recordings.
- `scripts/quarantine_audio_overlap.py` creates a separate run, removes entire
  connected groups implicated by exact evaluation bytes or incorrect source
  assignments, rechecks local audio SHA256, pins all input artifacts, and keeps
  originals untouched. This is a minimum exact-byte guard, not proof against
  transcoding, excerpt copies, unknown-artist overlap, or wrong musical labels.
- Four new targeted tests pass: hash/size/SHA1 consistency, source mismatch,
  whole-group exclusion, and missing/changed evidence rejection. The previous
  full-suite result remains 434 passed / one expected failure; a new full-suite
  run has not yet been performed for these additions.

- Completed `broader_audio_quarantined`: 91 tracks / two whole connected groups
  removed, 1,262 tracks / 69 classes / 3,772 windows / 223 groups retained.
  Feature arrays, row labels/groups and manifest hashes verified aligned.
  Fixed legacy kernel ridge grouped CV is 68.225% (top-3 79.239%), 9.38 seconds;
  the changed cohort/folds prevent interpreting this as a paired improvement.
  One class now has one track; sklearn warns about five-fold class support.
- Fitted a separate calibrated candidate; SHA256
  `0855df234e0aec077a5e7ccf96082691e2bfb631222e7cd29676a37a78f625bb`.
  Its 845 unique archival SHA256 values are embedded after another actual
  byte verification. Pitch-only CompMusic has no raw-byte receipt. Known
  normalized performer names do not overlap Saraga, but 635 retained archive
  rows still lack usable artist provenance, so artist independence is unproven.
- Corrected 180-second replay: estimated tonic 96/184 overall, 96/139 known
  vocabulary (69.06%); annotated tonic diagnostic 92/184. Development gate
  accepts 79, correct 61 (77.22%), with eight of 45 OOV falsely accepted.
  All 184 query hashes checked disjoint against the new archival inventory.
  This is exact-byte-guarded development, not a fresh or fully artist-disjoint
  test. The legacy RF baseline was deliberately omitted. No gate/model promoted.
- `train_raga_svc.py --audio-identity` verifies and embeds raw hashes;
  `assert_unseen_audio` rejects renamed byte copies, and legacy admitted track
  IDs are now also checked. The Saraga evaluator requires an explicit
  `--allow-unverified-audio-split` override when a model lacks hash inventory;
  such output is marked diagnostic, not independent accuracy. Seven targeted
  integrity tests pass. Historical raga-prior composition scores using the
  affected models need reevaluation too; melody-only protocols are separate.

- Corrected 60-second replay completes at 79/184 overall, 79/139 known
  vocabulary (56.83%); gate accepts 75 with 46 correct and 11/45 OOV false
  accepts. The 180-second repeat reproduces all 184 complete per-query rows and
  summaries exactly. These are the same inspected development queries, not a
  newly untouched benchmark. A direct legacy-model CLI check fails before
  scoring/writing output as intended when hash inventory is absent.
- Composition benchmark raga priors now also require training audio hashes and
  check all available query receipts before scoring. No melody-only path changed.

- Full regression suite after the integrity changes: **439 passed, one expected
  failure, ten dependency/codec warnings**, 245.91 seconds. Changed scripts
  compile, scoped whitespace checks pass, and the original manual-label SHA256
  remains `a0d137ea236e48b7cab710feff1abb7f8fc42fa46ce8c0b3877bb023263e44bb`.
  About 107 GiB disk remains; no external compute, deployment or raw deletion.
  Next: cached hash omissions (173 unresolved source identifiers), transformed
  copies, archival artist provenance, and exact-duplicate training weighting
  before expanding representation training. Raw path availability alone is
  explicitly no longer an admission criterion for an independent benchmark.

### Publisher checksum refresh and duplicate weighting

- Re-read the active execution objective; the previous turn is classified as
  progress (confirmed raw-audio leakage, guarded retraining and replay), not a
  wait or a blocker. Production/SOTA completion remains unproven.
- Fetching public file-checksum metadata for the 173 unresolved archive source
  identifiers into a separate resumable, checksum-pinned cache. No audio
  downloads, paid API or legacy metadata edits. Individual receipts record the
  exact public endpoint and raw response SHA256.
- IMPORTANT CORRECTION: fresh publisher metadata for
  `NeeveRakshavarnamKadanakuthoohalam` contains exact size/MD5/SHA1 matches for
  all four previously suspected mismatches. Those files are also in `DP-007`;
  the original assignments are valid shared-upload sources, not demonstrated
  mistakes. The first quarantined run's exclusion of that entire connected
  group was therefore unnecessary. It remains a historical conservative run,
  not the final cleaned training cohort. The 26 Saraga byte overlaps are real
  and unaffected by this correction.
- Added optional deterministic exact-audio deduplication to the quarantine
  builder: lexical track representative, no prediction-based selection,
  conflicting labels or groups fail closed. In the first quarantined run this
  identifies 35 redundant rows, all with identical cached contour hashes too.
  This fixes weighting, not a newly discovered split leak. Six targeted tests
  pass, including refreshed-byte receipt validation and deduplication guards.

- Refresh completed: all 173 public item requests succeeded (2,762,988 response
  bytes). Rehashing all 971 local archival files finds 961 single-source matches
  and ten shared-upload matches, zero unresolved or conflicting assignments.
  Every match has publisher SHA1 as well as size/MD5 evidence; all local SHA256
  values are unchanged from the original audit. New output:
  `data/overhaul/archive_audio_identity_refreshed.json`. This authenticates
  byte/source correspondence, not musical tags or performer identity.
- `broader_audio_deduplicated` is now built from the original broader feature
  run with the refreshed audit: 37 rows from the evaluation-overlap connected
  group quarantined, 43 redundant exact-audio rows removed. Retained: 1,273
  tracks, 69 classes, 3,805 windows. The prior source-mismatch group's otherwise
  eligible rows are restored. No known normalized artist-name overlap with
  Saraga is found; 611 retained archive rows still lack usable artist identity.
  Fixed kernel CV and fresh calibration/replay are running, without tuning.

- Refreshed/deduplicated candidate completed: grouped CV 68.3425%, top-3
  79.8115%, 224 groups. Model SHA256
  `18da6ca9c8c4e2d46e11d31cff70ce00ca70a7a77746adac27fdd79aab4bfc1e`;
  891 unique archival audio hashes embedded. Manifest/features verified aligned.
  Same inspected Saraga queries: 180s estimated-tonic 98/184 overall, 98/139
  known (70.50%); 60s 82/184 overall. At 180s the development gate accepts 78
  with 61 correct, including seven OOV false accepts. At 60s it accepts 76
  with 48 correct, including 12 OOV false accepts. No gate/model promoted.
  Restoring valid sources and removing duplicate weights change the cohort;
  this is not a controlled architecture improvement or a fresh evaluation.
- Full regression suite for provenance/deduplication: 441 passed, one expected
  failure, ten dependency/codec warnings, 257.77 seconds.

### Near-identical recording fingerprint audit

- Built pinned Chromaprint 1.5.1 locally with CMake 3.31.6 and vDSP; source,
  binary hashes, license scope and build commands recorded in
  `THIRD_PARTY_CHROMAPRINT.md`. No system installation or deployment. Initial
  safe extraction rejected an upstream header symlink; fixed by materializing
  only that exact internal alias, keeping arbitrary symlinks forbidden.
- Added a checksum-verified, finite-mono, bounded-block native wrapper. Three
  tests pass for checksum rejection, stream-partition determinism, unchanged
  inputs and invalid-stream cleanup. No native randomized matcher is used.
- Fixed four-recording 30s robustness pilot: gain changes produce bit error
  0–0.000142, 64kbps MP3 re-encoding 0.00297–0.00622, and 3.7s inserted silence
  0.01711–0.02135 after offset alignment. Six different-recording controls are
  0.43326–0.50375. This small pilot is not a corpus-wide threshold validation.
- Full-recording streaming pilot processed eight recordings in 12.2 seconds,
  including a 3,608.5s file. Full inventory of 891 training and 184 evaluation
  files is now running in `data/overhaul/recording_fingerprints`; it must finish
  before the overlap screener runs. Some MP3s emit native decoder warnings;
  source-byte authenticity does not establish decode cleanliness.
- Added exact-landmark offset voting plus continuous 160-frame bit-error
  screening, with low-information-code suppression and diversity guards.
  Two synthetic matcher tests pass (offset/re-encoding-bit noise recovery,
  reversed and constant-sequence rejection). Its output is flags only, never
  automatic labels/quarantine; no corpus-wide result exists yet.

- First full-stream attempt stopped at row 92 with a libsndfile MP3 resync
  failure (`Hamsadhvani/nAdha harE.mp3`). Independent FFmpeg decoding completed
  cleanly. Added native-rate/channel-preserving bounded FFmpeg fallback, with
  strict stderr/exit checks, native process cleanup and explicit decoder
  provenance. The 91 completed cache entries were preserved and reused.
  Fallback succeeds for row 92; declared duration 484.80s versus decoded
  484.57s is recorded in sample-count metadata, not silently conflated.
- Row 115 (`Varali/ne pogadakunTE.mp3`) fails libsndfile and emits invalid
  packet/header errors under FFmpeg. It is explicitly recorded as
  `decode_failed`, not a successful fingerprint or proof of no overlap. The
  full inventory continues; the matcher reports all such coverage gaps.
  Two additional fallback tests pass for exact native stereo PCM preservation
  and decoder-error rejection. These decoder changes are isolated to the audit
  extractor; shared production audio decoding has not been silently replaced.

### Completed recording guards and latest end-to-end candidate

- Full fingerprint inventory completed: 1,058 successful files, 17 failed
  training decodes, 15 successful strict FFmpeg fallbacks, ~195.4 decoded hours.
  One Akkarai Sisters evaluation/training pair was flagged and independently
  confirmed by identical full decoded PCM SHA256. Creator metadata corroborates
  this renamed-file overlap. Guarding only raw file bytes was insufficient.
- Refreshed all 266 retained-source metadata receipts. The standardized train
  stage now applies creator, verified recording-copy and decode-coverage guards.
  `repro_audio_identity/train_integrity_guarded`: 1,254 tracks, 3,748 windows,
  69 classes, 219 groups, 872 archival raw hashes. Candidate SHA256:
  `0dc8ee8b7298cb8fa1d90faf7af896c6a3ba04f9a78f23158acfb5cabf176e5f`.
- Latest grouped CV 68.5008%; estimated-tonic 180s replay 98/184 overall and
  98/139 known-class. Gate: 61 correct / 78 accepted, seven OOV false accepts.
  Same inspected development cohort; not fresh-test accuracy or promotion.
- All 11 field concerts (~9.85 hours) fingerprinted, zero flags against 874
  successful archival references. Matcher limitations and unknown artists remain.
- All five standard pipeline stages executed. First field concert: 1,605.75s,
  53 query windows, seven proposed segments, zero asserted raga identities.
  Last complete regression suite: 453 passed, one expected failure, 10 warnings.
- Discovered local MPS availability differs across sandbox contexts. Optional
  CPU-mel/MPS-backbone forward path preserves default CPU behavior; CPU/MPS
  frame relative L2 difference 9.13e-7. Warm 10s forward passes 0.54–0.74s,
  non-isolated pilot. Native convolution backward failed with a tensor-stride
  error; contiguous output gradients fix the exception. CPU controls then found
  incorrect first-LayerNorm affine gradients when its input was frozen. Requesting
  boundary input gradients repairs the observed discrepancy. Three synthetic
  steps pass CPU/MPS loss, per-parameter norm and encoder-update checks:
  maximum norm/control discrepancy 6.82e-7, encoder max update 2.083e-5,
  loss 2.39085 -> 0.000822802. Evidence: `musicfm_gradient_control.json` and
  separate CPU/MPS `gradient_boundary_diagnostic` artifacts. Five comparator
  tests reject finite-but-wrong/nonfinite gradients and absent updates; seven
  frontend tests pass. Workarounds remain isolated to the probe. No weights saved,
  no pretrained artifacts changed, no real-data fine-tuning result yet.

### Mixed-recording evaluation diagnostic

- Added a source-hash-checked summary that separates eight recording-level
  Rāgamālika labels from single-raga window evaluation without changing source
  labels, predictions or historical reports. Wrong source-corpus receipts are
  rejected. The run's exact `evaluation_corpus.json` is the authoritative input.
- `repro_audio_identity/evaluation_single_raga_diagnostic.json`: estimated
  98/176 overall, unchanged 98/139 known-raga; 61/77 accepted correct, six/37
  OOV false accepts. This denominator correction is not a model improvement.
  Other recording-level labels still lack independent window-level verification.
  Two focused tests pass, including preservation of inputs and known-class counts.
- Full regression suite completed: 460 passed, one expected failure, 10 warnings
  in 112.04s. The two summary tests were added after collection and passed
  separately. Scoped whitespace check passes. Manual LABELS.tsv SHA256 remains
  `a0d137ea236e48b7cab710feff1abb7f8fc42fa46ce8c0b3877bb023263e44bb`.
  Approximately 102 GiB free; no paid external compute, deployment, or raw deletion.

### Grouped MusicFM fine-tuning execution

- Added `scripts/finetune_musicfm_pilot.py`: fixed five-epoch connected-group
  holdouts on the same inspected 31-recording, five-raga, 13-group normalized
  development cohort. Arms train a zero-initialized linear head either alone or
  with Conformer block 6; SGD head LR .01, block LR .0001, batch size four,
  inverse training-fold class-frequency weights. No held-out checkpoint selection,
  vocabulary expansion, model export or production claim. Frozen backbone prefix
  caches are checksum-bound to source queries, normalized waveforms and run plan.
- First run failed before completing fine-tuning because rotary embeddings were
  cached as inference tensors. Explicitly clone the cache before autograd; the
  revised run is `musicfm_finetune_pilot_v2`, preserving the failed original.
  Cached-prefix block replay is checked against full-encoder output before training.
  Five focused fine-tuning/grouping tests pass. The five-epoch SGD run completed
  all 26 fold/arm fits in 130.3s: frozen head 7/31, fine-tuned block 7/31.
  Mean final training loss remains 1.41445; this is an underfit optimization
  pilot, not evidence that supervised MusicFM cannot work.
- Started a separate fixed 20-epoch AdamW optimization control after observing
  training underfit: head LR .001, block LR .00001, weight decay .01, gradient
  norm cap 1 with nonfinite-gradient rejection. Same groups, inputs, seeds and
  two arms; no checkpoint selection. Run `musicfm_finetune_pilot_v3_adamw_20`.
  Its outcome remains development evidence, not an independent model selection
  test or justification to promote a model.
- AdamW 20-epoch run completed all 26 fits in 574.1s: frozen head 10/31,
  fine-tuned block 8/31. Mean final training losses 0.44361 and 0.01151,
  respectively. Fine-tuning fits training data but does not improve held-out
  recognition; do not scale/promote this recipe. Eleven predictions differ
  between arms. The earlier normalized kernel head scored 9/31 and pitch
  baseline 12/31 under the same small cohort's grouped protocol.
- Full regression suite completed with both new summary and fine-tuning tests:
  464 passed, one expected failure, 10 warnings, 295.15s during concurrent local
  GPU work. Subsequent focused optimization/control tests: nine passed.
- Started the matched 180s composition replay with the latest guarded raga
  bundle, full unique CompMusic catalog, transposition-invariant alignment and
  unchanged .1 prior weight. Output `composition_full_180_guarded_raga_prior_shift.json`.
  An initial command omitted the transposition flag and was explicitly interrupted
  (exit 130); its separate output is not a matched benchmark. No historical
  result is overwritten. Final corrected-prior results pending.
- Corrected-prior composition replay completed: 181 queries, 53 answerable,
  36/53 top-1, 43/53 top-5, MRR .74196, 531.44s. Five work-ranks differ from
  the historical contaminated-prior report; one fewer top-1 match. Exact same
  query order and catalog/alignment protocol. Bound to model SHA256
  `0dc8ee8b7298cb8fa1d90faf7af896c6a3ba04f9a78f23158acfb5cabf176e5f`.
  Cross-fitted ranking-cost rejection accepts zero queries in both arms; no gate
  exported. It is not yet replayed with the subsequent six-label-exclusion model.

### Exact publisher-file label audit

- Added `audit_file_raga_evidence.py`, joining each retained raw-audio identity
  to the exact publisher file (size, MD5 and SHA1 checked against hashed metadata
  receipts), then resolving only delimited vocabulary tokens/explicit aliases.
  No fuzzy matching, arbitrary substring search, or automatic relabeling.
- Longest explicit compounds are resolved first: Ananda-bhairavi must not become
  Bhairavi. This both removes a false conflict and exposes a separately mislabeled
  Bhairavi training record. Three parser tests pass; seven parser/quarantine tests
  pass together.
- Final 872-file audit: 707 consistent file tags, 157 without explicit file tags,
  eight conflicts/ambiguities. Two are composition-title Sri tokens, not verified
  conflicting ragas. Five have documentary contradictions: one Anandabhairavi
  file labeled Bhairavi, one Shankarabharanam file labeled Dhanyasi, and three
  Kanada/Bhairavi varnam files labeled Nata. One lecture covers both
  Mayamalavagaula and Chakravakam without time-aligned labels.
- Added exact-audio exclusions for those six unsupported supervision cases with
  source URLs and immutable metadata receipts. Raw audio and original labels are
  unchanged. Building separate `file_tag_guarded` cohort; existing candidate and
  running composition replay remain bound to the previous model, not silently
  updated. Publisher tags remain weak supervision, not verified acoustic truth.
- `file_tag_guarded` completed: 1,248 tracks, 3,730 windows; exactly six additional
  supervision exclusions, no additional group or duplicate removals. Grouped CV
  69.5513%, top-3 80.7692%, macro recall 60.0194%. One rare class has only one
  track, triggering an explicit five-fold stratification warning. This changed
  cohort/CV assignment is not a paired causal improvement estimate. Candidate
  fitting completed; identical 180s query replay is running separately.
- Replay completed: unchanged 98/184 overall and 98/139 known-raga estimated,
  annotated diagnostic 94/184. Single-raga summary: 98/176, gate 62/79 correct
  accepts, seven/37 OOV false accepts. Latest separate candidate SHA256
  `2f7b88927602c62e4625ddc9efe1dc984f9856385ea5ab09fd763b0920534bee`.
  This is cleaner supervision, not a measured recognition gain or promotion.
- Expanded byte audit to all 1,140 original archival rows using an explicit
  legacy-row option (no training admission): 1,072 assigned-source matches,
  10 shared uploads, 57 unresolved cached matches, one apparent identifier
  mismatch, 68 duplicate groups. Refreshed full publisher metadata is running
  with verified cache reuse before judging previously rejected rows. No rows
  have been readmitted or relabeled.
- Full metadata refresh completed for 283 sources with prior-receipt reuse.
  Re-audited all 1,140 files: 1,124 assigned-source matches, 16 shared uploads,
  zero unresolved/mismatched identities, 68 exact duplicate groups. The apparent
  Chittoor/Chittor source discrepancy was shared audio, not a wrong assignment.
- Generalized the explicit publisher-token audit to a supplied manifest/identity/
  metadata set. A relative-path receipt bug was caught in the actual CLI run and
  fixed before output. All-row results: 755 consistent tags, 376 without tags,
  nine conflicts/ambiguities. Among the 169 previously unadmitted rows: 25 have
  consistent file tags, 142 no tag, two conflicts. These remain unadmitted pending
  the rest of the identity/decode/group guards; no acoustic label verification.
- Started a separate fixed 24-recording training-context diagnostic: SHA-ordered
  file-tag-consistent training rows, exact central legacy 60s interval, old
  contour/full-recording tonic versus independently extracted query contour/tonic.
  No evaluation queries or classification claims. It measures tonic pitch-class
  disagreement, jointly voiced pitch agreement and feature cosine; neither arm is
  treated as ground truth. Eight focused context/parser/identity tests pass.
- Training-context diagnostic completed all 24 recordings: median pitch-class
  contour agreement within 50 cents is .99774, median feature cosine .99169,
  median tonic difference zero. However, six/24 have >50-cent tonic disagreements:
  five around 500 cents and one around 202 cents, with feature cosine .38–.89.
  This is meaningful tonic ambiguity, not proof which estimate is correct.
  Native MP3 warnings occurred; successful libsndfile reads are not claimed to
  certify perfectly clean decodes.

### Tonic uncertainty ablation

- Fixed three-tonic posterior mixture (offsets 0, 5, 7 semitones; weights .8,
  .1, .1) reproduces every base top-three prediction before comparison. Uses
  the six-label-exclusion model, not a subsequently recalibrated bundle.
  Development known-raga top-1 98 -> 100/139, top-3 119 -> 123/139; three wins,
  one loss. Across 17 connected artist/source/audio groups, 5,000-bootstrap
  known-query difference is +1.44 percentage points, 95% interval [-1.04, 5.00].
  No significant/fresh-test improvement is established and no old gate is reused.
- Existing six-query field replay: both baseline and mixture 3/6, five classes
  in vocabulary. No field improvement. Mixture is an explicit diagnostic flag
  only, not a production inference/default change. Five mixture tests pass.
- Full regression suite at this point: 474 passed, one expected failure,
  10 warnings in 119.07 seconds.

### File-level artist grouping and matched-context rebuild

- Publisher file artist tags exist for 770/866 retained archival recordings;
  96 remain missing/generic. Added exact-name unions with existing artist/source
  components, preserving labels and features: 219 -> 133 groups across the same
  1,248 tracks. Aliases and ensemble-string variations remain unresolved.
- Separate reserved-artist check excludes zero additional groups on this cohort.
  The standard train stage now performs these unions and checks reserved artists
  before CV/fitting (four commands rather than three). A macOS /tmp resolution
  assertion in a new test was corrected; 14 targeted grouping/pipeline/context/
  label-window tests subsequently pass.
- More conservative grouped CV: 68.5096%, top-3 80.6891%, macro recall 57.9448%.
  `file_artist_grouped/raga.joblib` fitted and evaluated: unchanged 98/139 known
  top-1; diagnostic gate accepts 92/184 with 70 correct and 11/45 OOV false
  accepts. This gate is unsafe, not promoted. Earlier CV figures do not represent
  full artist independence.
- Added resumable `extract_context_training.py`: exact 180s archival audio query
  and independently estimated query tonic; CompMusic remains explicitly tagged
  reference-pitch/annotated-tonic input. Original labels/group components preserved,
  invalid/unvoiced queries explicitly rejected. Caches bind source files, query
  contracts, code dependencies and plans; source hashes are rechecked on resume.
  Model fitting now records the actual context length instead of hardcoding 60s.
- Bounded pilot: 24 tracks (21 archive, three CompMusic), 72 windows, 340.40s.
  Exact executed source archived and verified against its plan hash. Three focused
  context tests cover extraction/resume, changed-source rejection and model window
  metadata. Full `context180_full` extraction is running on four local CPU workers
  over the 1,248-track artist-grouped cohort; verified pilot query caches are reused.
  This may take several hours; no cloud resources or new manual labels are used.
- Coverage lead, not an admission: refreshed metadata includes a 4.6 MB public
  `Teliyaleru Rama - Denuka` recording that the old vocabulary missed. Independent
  work/raga corroboration is available at https://www.karnatik.com/c31447.shtml.
  No new audio has yet been downloaded or readmitted for this lead; another
  Dhenuka/Natakapriya lecture is mixed and not uniform-raga training material.

### Strict decoder audit and extraction recovery

- Full strict FFmpeg audit completed: 861 clean, five decoder errors across 866
  archival recordings, 535.80s. The earlier 24-recording diagnostic subset is
  entirely clean under FFmpeg; mpg123 warnings alone did not prove corruption.
- Failed full extraction `context180_full` saved 193 track caches before an
  exception in libsndfile's window read for Kamās/mODi jEsEvElrA. This recording
  passes full FFmpeg decode. Original executed source was archived after checking
  its hash against the frozen plan. No old outputs were overwritten or deleted.
- `extract_context_training.py` now requires exact-path/hash decode evidence,
  excludes non-clean archival recordings and records libsndfile window errors as
  rejected windows. Other provenance/programming errors still fail loudly.
  Revised run `context180_strict_decode` starts with 1,243 tracks, reuses unchanged
  query-contract caches and writes a new plan. Partial-window selection is recorded;
  window rejection is not an acoustic repair. Full results remain pending.
- Full regression: 482 passed, one expected failure, 10 warnings, 200.08s.
  Seven targeted context/decode/download tests subsequently pass in 3.09s.
- Dhenuka coverage candidate was downloaded with publisher MD5/SHA1/size checks:
  4,632,616 bytes, raw SHA256
  `1225bbe673a950a861904d63c7a209a36ffb9700abcff9080ef67d54c4f0a0c2`.
  Strict decode is clean; fingerprint screening against 1,069 unique successfully
  fingerprinted reference recordings finds zero flags. This is not proof against
  every transformed copy. It is not admitted or trained; artist independence and
  additional independent performances remain unresolved. Existing Dhenuka is OOV.
- Added `filter_strict_decode_features.py` for a separate cleaning-only ablation
  retaining surviving features, labels, groups and original development folds.
  No production model, raw recording or manual annotation is changed.
- Cleaning-only ablation `file_artist_strict_decode`: 1,243 tracks, 3,715 windows;
  grouped CV 68.7852%, top-3 81.0941%, macro recall 57.8423%, 5.12s fit time.
  Five exclusions versus 68.5096% previous CV do not establish meaningful gains.
  Candidate fitted; matched 180s development evaluation launched separately.
- Standard train stage now has six commands: artist guard, file-artist unions,
  strict decode audit, feature quarantine, grouped benchmark, candidate fitting.
  Twelve context/pipeline tests pass, plus a separate feature/fold-preservation
  integration test. Full regression after these changes is running separately.
- Cleaning-only model's matched estimated-tonic evaluation is 97/139 known top-1
  (previous 98/139), 118/139 top-3; 70/90 accepted predictions correct, 11/45 OOV
  false accepts. Annotated-tonic top-1 remains 94/184. No improved recognition
  claim, and this confidence gate is not production-safe.
- Separate experimental `audio/ffmpeg_window.py` preserves native channel/rate,
  uses strict output-side seeking and bounded temporary float PCM. It is NOT
  enabled in the active frozen query frontend. Five tests pass, including exact
  stereo anti-phase seek comparison. The libsndfile-failing Kamās recording
  successfully decodes 6,981,120 native stereo frames at 44.1kHz (158.3s) with no
  FFmpeg diagnostic. Probe receipt: `context180_window_fallback_probe.json`.
  This demonstrates a viable decoder recovery path, not yet recovered features.
- Post-recovery full suite completed: 485 passed, one expected failure, 10 warnings
  in 168.50s. Five separately added FFmpeg fallback tests also pass. Scoped
  `git diff --check` is clean; manual-label SHA256 remains unchanged. Available
  local storage is 104GiB. Rebuild remains active in session 39220, plan SHA256
  `cc4aad541aa15a2488ba0748f8daebb4db9a23b1b4420eeca950a17e4cbae042`.
  Last structured checkpoint: 226/1,243 tracks, 647 retained windows at 320.68s;
  229 track caches existed (ordered progress can lag completed workers).

### Decoder recovery and evaluation-input audit

Latest continuation: confirmed the extraction session is live; previous turn
classified as concrete progress, not a blocker. Added separately planned decoder
feature recovery, tested parent-cache preservation/resume/raw-identity guards.
Kamās/mODi jEsEvElrA now has recovered 158.302s audio, 98.981s voiced pitch and
145.382Hz estimated tonic in `context180_decode_recovery_kamas`. No recovered
features have yet been merged into training. Six recovery/fallback tests pass.
Strict decode audit now supports explicit evaluation-corpus identity receipts;
the 184-recording Saraga audit is running in `strict_decode_saraga`. The active
context rebuild remains untouched and has passed 272 tracks.

The Saraga strict audit subsequently completed successfully: **184/184 clean**.
This establishes decoder success, not correct labels, boundaries, artist
independence or acoustic quality. The recovery completed in 93.24s and remains
separate from the parent cohort. Fifteen targeted recovery/fallback/pipeline/
evaluation-identity tests pass; scoped diff whitespace checks are clean. Main
rebuild session 39220 was confirmed live; latest inspected checkpoint was 296
tracks / 849 retained windows. No external authorization blocker or model
promotion occurred. Next dependency is the full rebuild result, followed by
explicit recovery merge, grouped fitting and matched evaluation.

### Automatic completion of the matched-context experiment

Added `merge_context_decode_recovery.py`: requires the completed extraction's
exact ordered track list, verifies parent/cache/raw-file/recovery receipts,
rejects duplicate accepted windows, preserves labels/groups and imports fixed
development folds. It writes a separate cohort. Candidate bundles now record
the decoder-recovery plan hash. Eight merge/context tests pass; five additional
runner/merge checks pass (overlapping coverage, not thirteen unique tests).

`finish_context_experiment.py` observes the verified extractor PID 58717 and
automatically runs remaining recovery, merge, fixed-fold kernel benchmark,
fitting and matched 180s evaluation when extraction completes. It freezes source
dependencies, has a four-hour observation bound, stops if the specific parent
disappears without completion, and never promotes/deploys a model. It was launched
locally into `context180_recovered_experiment`; log is
`/private/tmp/carnatify-context180-followon.log`. Existing completed recovery is
reused only after merge receipt checks; any additional rejected tracks trigger
their own recovery. Source extraction remains active and unchanged. Follow-on
session 15350 is live and its progress records `waiting_for_parent`.

### Pipeline execution

Latest continuation completed the full follow-on regression: **497 passed,
one expected failure, 10 warnings, 162.55s**. The preceding turn is classified as
progress (implemented/tested/started the automatic experiment); this turn also
verified extraction and supervisor handles live. Extraction passed 381 tracks;
supervisor remains `waiting_for_parent`. No dependency edits were made to the
frozen experiment during this continuation.

Reviewed primary DeepSRGM and January-2026 generalized-category-discovery
protocols; comparability details and citations are in the architecture audit.
Neither supplies a matched production benchmark for the present estimated-tonic,
artist-grouped, multi-raga concert objective. In particular, source-recording
equivalence must not become pseudo-label truth for whole concerts.

Use venv_train/bin/python scripts/carnatify_pipeline.py with each stage in order:
data-prep, feature-extract, train, evaluate, infer. Supply --run with a dedicated
repository-relative run directory; infer also requires --audio and --output.
Existing CompMusic/Saraga metadata and archive source caches are prerequisites.
Current integrity guards also require the completed refreshed archive metadata,
fingerprint inventory and independently verified copy report. These audit
artifacts are not yet generated automatically by the five-stage wrapper.
File-level artist grouping also requires the completed `all_archive_metadata`
receipt cache. The matched-context rebuild remains a separate evaluated-experiment
path until its full-cohort results are available; it is not silently the default.
The new scripts are research/candidate components; old deployed artifacts remain
untouched while confidence, field generalization and song rejection are unresolved.
