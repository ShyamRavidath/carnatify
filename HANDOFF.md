# Carnatify: authoritative handoff for the next engineering agent

## 2026-09-10 tech-lead pass: read this before the September 9 sections

Goal that was set and completed: **one trustworthy raga path: audited
candidate, honest abstain gate, single contract, green tests, committed.**
Every number below has a prereg committed before its harness; the docs named
here are the receipts. This section takes precedence over everything after it.

1. **Worktree landed.** The September overhaul (199 untracked files, 1.4 GB
   of which was caches) is now 13 topic commits from `b70cb91` to `38cb399`.
   Caches, arrays, audio, the cmake wheel and the chromaprint checkout are
   gitignored; plans, manifests, receipts and result JSON are tracked.
   Only `data/long_concerts/LABELS.tsv` and `.claude/settings.local.json`
   remain modified: they are Deepti's and were not touched.
2. **Verdict on context180** (`data/overhaul/CANDIDATE_VERDICT.md`, harness
   `scripts/candidate_verdict.py`). Paired cluster bootstrap over the 133
   groups: **+7.88 pp CV, 95% [+5.69, +10.19]**; archive rows +9.18, CompMusic
   reference-pitch rows +4.97, so about five points are duration/window and
   about four are the tonic/DSP match. Dev 184 queries, 17 artist clusters:
   +3.60 pp known top-1, [−1.68, +8.57], includes zero; top-3 unchanged at
   118/139. **Promoted to reference candidate** by the registered rule.
   Do not quote 102/139 as external evidence.
3. **Abstain gate** (`data/overhaul/ABSTAIN_GATE.md`, harness
   `scripts/abstain_gate.py`). Selected on a 17,735-window leave-class-bin-out
   pool that never sees dev: signal `margin` (top-1 minus top-2 raw ridge
   score) ≥ 0.1628. Dev, applied once: **70/184 accepted, 82.9% precision
   [75.0, 92.7], 7/45 OOV accepted (15.6%)**, versus the bundle's own gate at
   145 accepted, 65.5%, 29/45. Registered bar 85% / 15% **fails narrowly**;
   by rule the gate is **off in the product**. The dev trade-off curve is in
   the doc for Deepti to choose from; any point taken from it is dev-tuned.
4. **Field** (`data/overhaul/FIELD.md`). Six labelled items, oracle
   boundaries, 180 s: **3/5 in-vocabulary top-1**, gate accepts 2 (both
   correct) and abstains on Dhēnukā with 0.009 to spare. Same 3/6 as the
   previous guarded candidates: **the CV gain did not show up in the field.**
   Śankarābharaṇaṁ and Tōḍi are wrong with near-zero margin.
5. **One contract.** `src/carnatify/ml/raga_runtime.py`: `RagaCandidate.load`
   (name from `configs/raga_candidates.json`, SHA256-verified, or a path),
   `RagaGate.load` (registered JSON, never invented), `score_contour` and
   `identify_raga` returning one `RagaResult` dict with ranked classes, the
   three signals, the gate decision, and the model identity. The dev
   evaluator, the field evaluator and `concert_pipeline.py` all go through it.
   `scripts/INDEX.md` classifies all 135 scripts (current / audits / August
   harnesses / archive). Tests: 503 passed, 1 xfailed.
6. **Not wired into the product.** `backend/main.py` and `identify_clip.py`
   still serve the legacy models, per Deepti's August directive. Wiring the
   reference candidate is gated on her decision and, if the gate is to speak,
   on a bar it has not met. The registry status string says so.

What I would do next, in order: (a) label the other eight concerts, which is
the only cheap thing that makes the field number mean anything; (b) decide
the gate operating point from the published curve, or keep it off; (c) wire
`identify_raga` with the gate closed so the product shows ranked candidates
as candidates; (d) only then spend on the model again, and start with the
two near-zero-margin field failures, not with a new encoder.

### 2026-09-13 follow-up, run while Deepti labels the remaining concerts

Five cheap items, each with its receipt; none changes the reference
candidate or the gate's status (off).

- **Field failures diagnosed** (`data/overhaul/FIELD_FAILURES.md`). Both
  near-zero-margin misses are right-mela-wrong-raga: c1_1 Śankarābharaṇaṁ is
  heard as Bēgaḍa / Dēvagāndhāri / Behāg / Bilahari (its janyas) in 15 of 20
  windows; c2_1 Tōḍi as Sāvēri / Dhanyāsi / Māyāmāḷavagauḷa / Cakravākaṁ (same
  R1 M1 D1 skeleton) in 8 of 8. Tonic is stable to 0 cents across windows;
  position, duration and 0/+5/+7 tonic candidates rescue nothing. Two
  predictions refuted (tonic instability, Tōḍi top-3). The next model lever,
  if any, is phrase-level evidence within a mela, not more classes/duration/tonic.
- **Wild clips** (`data/overhaul/WILD.md`). Reference candidate on the frozen
  27: **16/27 = 59.3%**, top-3 20/27, the same integers as the July `raga_v3`
  number on a 69-class answer space. Gate: 11 accepted, 8 correct (72.7%),
  0/2 OOV accepted; the most confident wrong answer anywhere (Mōhanaṁ →
  Hindōḷaṁ, margin 0.416) is here. Third set where gate precision misses its bar.
  **Together with FIELD.md: the CV gain has now failed to transfer on two
  independent phone-audio sets.**
- **Off-tier fetch** (`data/overhaul/OFFTIER_FETCH.md`). Ten off-vocabulary
  ragas would cross the five-track admission line with reachable archive.org
  audio (Ranjani 16, Simhēndra madhyamaṁ 10, then 5–7 each). The August
  "185 off-tier pairs" contained 93 files where the tala word *Adi* matched
  the raga Pāḍi through the fetchers' vowel-folded matcher; the bug is in
  `download_targeted_deficits.py`, excluded in the new script, not yet fixed
  at source. Real off-tier supply: 79 pairs across 21 ragas. No fetch run.
- **Backend** (`backend/main.py` `/identify-raga`, tests in
  `tests/test_backend_identify_raga.py`). Serves the registry's reference
  candidate through `raga_runtime`: ranked candidates, the three signals,
  `gate.would_accept` for information, `asserted: false` always. Legacy
  routes untouched. 503 on a deployment without the registry. Not deployed.
- **Blind concert runs**: `concert_pipeline.py` over all 11 frozen concerts,
  180 s windows, gate reported, outputs under
  `data/overhaul/context180_recovered_experiment/blind_concerts/`. Queries are
  cached, so scoring against the labels when they land is instant. No number
  is read from these until the labels exist. **Complete**: 1,178 windows, 438
  gate-accepted; see `data/overhaul/BLIND_CONCERTS.md`. Concert 2 shows the
  model at its most confident during the Hindōḷaṁ *alapana* (margin 0.91):
  label alapana as its own row with the raga.

The 2026-09-09 handoff follows unchanged.

Prepared 2026-09-09, after the user reported only 8% weekly usage remaining and
explicitly requested a comprehensive handoff rather than more autonomous LLM work.

## 0. Read this first: precedence and honesty

This September handoff supersedes the August handoff preserved below. The older
text is historical evidence, not current instructions or a current measurement.
In particular, its claims that composition work is permanently closed, that the
production files have zero diff, and that earlier raga evaluations survived all
audits are NOT reliable descriptions of this worktree now.

The next agent is explicitly asked to audit and correct my mistakes, not defend
my decisions. Treat raw artifacts and the current code as authoritative. Treat
my interpretations as hypotheses unless the cited experiment actually proves them.
Do not declare completion just because tests pass or one CV number is high.

The user now wants quota preservation. Do not revive the previous cycle of
frequent autonomous LLM continuations merely to print another progress count.
Non-LLM local jobs were allowed to keep running. The two jobs I was monitoring
have now completed; they must NOT be restarted just because their old session
handles no longer exist. No new experiment was started during handoff preparation.

## 1. Goal, authority, and completion requirements

Build a trustworthy live Carnatic concert companion: identify ragas and
compositions from multi-hour, unsegmented recordings, with tonic invariance,
source/artist-disjoint evaluation, useful unknown/rejection behavior, and a
reproducible preparation/extraction/train/evaluate/infer pipeline. The user seeks
state-of-the-art production performance, not an easy closed-set benchmark.

The active product goal references this exact user attachment:
`/Users/shyamravidath/.codex/attachments/3a81b37d-ad8f-4a05-9239-d027ad5fdfc6/pasted-text-1.txt`.
Read it if continuing the full project. The newer request to preserve weekly
usage and make this handoff controls the immediate task.

Earlier authority covered local code changes, tests, refactoring, and bounded
local experiments without confirmation. Significant external spending, dedicated
external long-running compute, or destructive raw-audio deletion remained gated.
No deployment, push, paid APIs, cloud cluster, or raw-audio deletion was performed
as part of the recent overhaul. Do not infer authority to incur those costs.

The full goal remains UNACHIEVED. Missing proof includes robust natural-concert
boundaries, useful song rejection, calibrated unknown-raga handling, broad fresh
artist-independent generalization, and a comparable SOTA benchmark. No candidate
has been promoted or deployed. The job supervisor's `result.json` means that one
development experiment completed; it does not certify the user's full goal.

## 2. Newly completed result: this supersedes all 'still extracting' updates

The 180-second matched-context rebuild and automatic follow-on experiment FINISHED
while the user was away. At handoff creation I read completion files, final logs,
metrics and the actual model hash. Old process handles returned `Unknown process
id`; completion artifacts independently confirm success, rather than relying on
the missing handle alone.

### Latest candidate

- Directory: `data/overhaul/context180_recovered_experiment/training`.
- Model: `raga.joblib`; SHA256
  `f594584402cb2ae35532612e673c194661706fcdfe4b69bbecc69b6d50316e2b`.
- 1,243 tracks, 3,547 windows, 69 raga classes, 133 source/artist groups.
- Raw extraction retained 1,240 tracks / 3,544 windows; separate FFmpeg recovery
  restored three fully decoder-rejected tracks/windows. No relabeling occurred.
- Raw extraction elapsed 6,152.18 seconds, including reused query caches.
- Supervisor elapsed 5,133.36 seconds, including its wait for the parent.
- Development grouped CV: top-1 **76.6693%**, top-3 **85.1167%**, macro recall
  **66.2493%**, macro F1 **65.9881%**; benchmark fit time 3.153 seconds.
- Cleaning-only 60-second-training comparator: top-1 **68.7852%**. I explicitly
  checked identical track sets AND identical saved fold assignments. Across 1,243
  tracks, 140 changed from wrong to correct and 42 from correct to wrong: net +98.
- This is a changed context/frontend training experiment, not a pure architecture
  ablation: duration, query tonic, window positions/counts and DSP context changed.
  Compute paired group-bootstrap uncertainty before claiming a robust effect.

### Matched 180-second Saraga development evaluation

- 184 recordings; 139 in the model vocabulary and 45 out of vocabulary.
- Estimated-tonic top-1: **102/139 = 73.3813% known**, 102/184 overall = 55.4348%.
- Estimated-tonic known top-3: **118/139 = 84.8921%**.
- Cleaning-only comparator: 97/139 known top-1, same 118/139 known top-3.
- Previous artist-grouped pre-strict-decode model: 98/139 known top-1.
- Annotated-tonic latest result: 97/139 known top-1, 117/139 known top-3;
  97/184 overall. Estimated beating annotated here is an observation, not proof
  that estimated Sa is more correct; feature/domain interactions need diagnosis.
- **DANGEROUS GATE:** estimated-tonic gate accepts 145/184 queries, only 95 correct
  (65.5172% accepted precision), including **29/45 OOV false accepts = 64.4444%**.
- Annotated-tonic gate accepts 137/184, 96 correct, including 22/45 OOV false accepts.
- DO NOT DEPLOY THIS CONFIDENCE GATE. Improved discrimination did not produce
  trustworthy confidence. Earlier calibration thresholds do not transfer safely.
- All 184 evaluation files passed strict full-file FFmpeg decoding. This does not
  validate their labels, single-raga assumption, artist independence or boundaries.
- The Saraga evaluation set has been inspected and reused many times. It is a
  development set now, NOT a fresh test. Do not tune on it and call the next score
  independent. Some mixed-raga evaluation recordings need separate reporting.

### Completion and provenance receipts

- Parent: `data/overhaul/context180_strict_decode/plan.json`, `extraction.json`,
  `manifest.json`, `features.npz`, `tracks/`, `progress.json`.
- Parent plan SHA256:
  `cc4aad541aa15a2488ba0748f8daebb4db9a23b1b4420eeca950a17e4cbae042`.
- Supervisor: `data/overhaul/context180_recovered_experiment/result.json`.
- Supervisor plan SHA256:
  `57d63ed66b3de23361b2fe07a7c931991c57895cf48a940fc2b3dc6c7a7b790a`.
- Merged training `merge.json`: 1,243 tracks, 3,547 windows, three recovered.
- Merge plan SHA256:
  `dfb99204d3187a5bd84059423b64d871e964ddec06f9201a610140f18f2d4afc`.
- Latest features SHA256:
  `b3ec0b6a7c79f229dde076772c0c590a204d5ef276a59ed4511cfad6ddf5a243`.
- `kernel_benchmark.json` contains per-track CV predictions; `folds.json` contains
  exact fold assignments; `legacy_kernel_ridge_oof.npz` contains calibration inputs.
- `evaluation180.json` contains exact query metadata, predictions and summaries.
- Logs: `/private/tmp/carnatify-context180-strict.log`,
  `/private/tmp/carnatify-context180-followon.log`, and per-script logs directly
  inside `data/overhaul/context180_recovered_experiment/`.

## 3. Process and environment handoff

- Repository: `/Users/shyamravidath/carnatify`; shell zsh; macOS Apple Silicon.
- Branch verified: `probe/duration-and-negative-arm`.
- HEAD verified: `f80ac00 fix(long-concerts): the labels template now has room for the many songs per concert`.
- The overhaul changes are largely uncommitted/untracked in a dirty worktree.
  Do not reset, clean, discard, or assume untracked files are disposable.
- Python: `venv_train/bin/python`, Python 3.11. Existing local dependencies are
  the practical environment; a clean-machine setup has NOT been demonstrated.
- Last disk check: 105 GiB free. No storage blocker.
- Extraction session **39220**, PID **58717**: completed, old handle missing.
- Follow-on session **15350**: completed, old handle missing.
- Full regression session **59608**: completed earlier, 497 passed / 1 xfailed.
- Do not kill unrelated old terminals or processes. User explicitly allows stale
  non-LLM terminals to remain. I did not inventory or terminate all old jobs.
- MPS may appear unavailable inside the sandbox. Earlier read-only/local compute
  escalation demonstrated MPS available outside it. Do not conclude 'no local GPU'
  solely from a sandboxed `torch.backends.mps.is_available()` result.
- Network access is restricted in sandbox; small public archive downloads were
  approved through escalation. No credentials are needed for those public sources.
- Torch 2.5.1 / Torchaudio 2.5.1 and Transformers 4.44.2 were used in the MusicFM
  work; optional runtime dependencies live locally. Preserve checkpoint hashes.
- `/usage` was not exposed as a callable tool. `get_goal` is usage accounting, NOT
  a weekly-quota tool. Never fabricate quota availability from goal token counts.
- The long autonomous goal consumed over 4.4 million reported tokens. This was
  excessively expensive and included many repetitive polling turns. The next
  agent should be substantially more economical and respect the user's quota stop.

## 4. Files most recently edited and why

### Active context-training/recovery implementation

- `scripts/extract_context_training.py`: deterministic .2/.5/.8 offset windows;
  exact archival raw-audio query extraction; query-local estimated tonic; explicit
  reference-pitch/annotated-tonic CompMusic path; source hash checks; per-track
  atomic caches; required strict-decode report; recorded libsndfile rejections.
- `src/carnatify/audio/melody_frontend.py`: shared bounded query contract, original
  mix tonic estimate, Melodia pitch, parameter-keyed query cache. Default version
  remains `mixed_tonic_query_melodia_v1`, hop 128/44100 seconds.
- `src/carnatify/audio/utils.py`: finite validation, bounded native-channel read,
  phase-safe downmix, single resampling; browser upload fallback handled separately.
- `src/carnatify/audio/ffmpeg_window.py`: separate experimental strict FFmpeg
  decoder, native rate/channels, accurate output-side seek, bounded temporary float
  PCM. Not globally enabled in the production/shared query frontend.
- `scripts/recover_context_decode_windows.py`: recovers only explicitly rejected
  decoder windows into a separate planned artifact; does not overwrite parent caches.
- `scripts/merge_context_decode_recovery.py`: requires exact complete parent track
  list; checks recovery parent/cache/raw identity and boundaries; preserves labels,
  groups and fixed folds; writes a new cohort instead of changing the parent.
- `scripts/finish_context_experiment.py`: non-LLM local supervisor. Observes one
  specific extractor PID, freezes named dependencies, recovers all rejected tracks,
  merges, benchmarks, fits, evaluates; four-hour wait bound; no deployment.
- `scripts/train_raga_svc.py`: actual model window length rather than hardcoded
  60 seconds; embeds context/recovery provenance and training raw-audio hashes.
- Tests: `test_context_training.py`, `test_context_decode_recovery.py`,
  `test_context_recovery_merge.py`, `test_context_experiment_runner.py`,
  `test_ffmpeg_window.py`.

### Integrity and standard pipeline

- `scripts/audit_strict_audio_decode.py`: full FFmpeg `-xerror` audit; distinguishes
  clean, diagnostics-only, nonzero decoder error and timeout; verifies raw hashes;
  supports explicit evaluation-corpus identity receipts.
- `scripts/filter_strict_decode_features.py`: cleaning-only feature filter; no
  regeneration/relabeling; preserves surviving original development folds.
- `scripts/regroup_file_artists.py`: exact normalized publisher-file artist unions
  with existing artist/source groups; transitive reserved-artist exclusions.
- `scripts/carnatify_pipeline.py`: five named stages. Current train stage has six
  commands: reserved artist guard, file-artist grouping, strict decode audit,
  feature quarantine, grouped kernel benchmark, fitting. Context rebuild is a
  separately evaluated experiment, not silently the default pipeline.
- `scripts/audit_archive_audio_identity.py`, `quarantine_audio_overlap.py`,
  `build_evaluation_audio_identity.py`, `guard_archive_evaluation_artists.py`:
  raw-byte identities, overlap quarantine, duplicates and source/artist guards.
- `scripts/audit_file_raga_evidence.py`: exact filename/raga-token evidence,
  longest compound raga matches first; no fuzzy relabeling.
- `configs/known_audio_exclusions.json`: documented supervision exclusions.
- `scripts/fetch_dhenuka_coverage_pilot.py`, `audit_dhenuka_coverage_pilot.py`:
  integrity-checked independent coverage lead; not admitted into any trained model.
- Documents: `OVERHAUL_EXECUTION.md`, `ARCHITECTURE_AUDIT_2026-09-08.md`, this file.

### Earlier overhaul implementation (still important)

- `src/carnatify/ml/melody_features.py`, `distribution_classifier.py`,
  `calibration.py`, `evaluation_integrity.py`, `inference_runtime.py`.
- `src/carnatify/ml/melody_retrieval.py`, `composition_catalog.py`,
  `retrieval_prior.py`, `concert_segments.py`.
- `src/carnatify/audio/pitch_profiles.py`, `cache_io.py`, `events.py`,
  `pitch_activity.py`, `sections.py`, `recording_fingerprint.py`.
- `scripts/concert_pipeline.py`, `evaluate_annotated_raga.py`,
  `evaluate_labeled_intervals.py`, `benchmark_melody_retrieval.py`,
  `calibrate_composition_rejection.py`, `build_compmusic_compositions.py`.
- Optional experimental frontends: MusicFM, Demucs, RMVPE, sung ASR, tonic evidence;
  each has distinct cache contracts and tests. They are not interchangeable defaults.
- `backend/main.py`, `backend/clip_identify.py`, `identify_clip.py` and upload tests
  contain real edits from earlier work. The old August statement of zero diff is false.
- `normalize_ragas.py`, `registry_hygiene.py`, legacy raga dataset/features/trainer
  modules have integrity fixes; inspect current diffs before further restructuring.

Nothing is actively being edited after this handoff except documentation. The
completed experiment's code can now be audited, but keep its executed plans and
outputs intact; new semantics require a new experiment directory.

## 5. Current topology and contracts

Archived tracks and CompMusic reference pitch are admitted using strict taxonomy,
publisher evidence and known exclusions. Raw byte identities eliminate obvious
duplicates and evaluation copies. Source and known-artist groups are unioned.
Strict decode failures are quarantined. Feature extraction then produces tonic-
relative distributions and time-delayed melody surfaces. Fixed grouped folds drive
kernel comparison, training-weighting and OOF calibration. Evaluation uses bounded
raw-audio queries with estimated tonic, plus a separately reported annotated-tonic
diagnostic. Concert inference adds activity/boundary candidates, raga aggregation,
melodic composition retrieval and abstention mechanisms.

Important distinctions:

- Current features concatenate 480 histogram and 4,800 temporal entries (5,280).
  The legacy/voiced temporal representation has 4,800 entries.
- Elapsed-time transitions and voiced-compressed transitions are different
  representations. The TDMS literature legitimately uses voiced compression.
  My initial suspicion that all voiced compression was a bug was too broad.
- Current strongest inexpensive classifier is distribution kernel ridge on voiced
  TDMS, not a new deep neural architecture. SVC is also implemented.
- Track weighting is inverse window count, normalized to mean one; multiple windows
  from one recording must never create train/validation independence.
- The latest fit uses 180-second-training metadata. Older bundles use 60 seconds.
  Do not change bundle metadata to pretend incompatible features are matched.
- CompMusic remains pitch-only reference input with annotated tonic; the archival
  raw-byte audit does NOT cover absent CompMusic audio. Do not overstate its scope.
- Query cache identity includes raw hash, start, duration, frontend parameters and
  profile. It does not automatically hash every transitive dependency or decoder
  binary. See the self-audit risks below.
- The standard five-stage wrapper still depends on prepared metadata, fingerprint,
  corpus and identity artifacts; it is not a proven one-command fresh installation.

## 6. Manual-labeling verdict and protected user work

No NEW manual tagging is required to run the current experiments. Existing Saraga
annotations, verified performance/work metadata and already supplied field labels
are consumed automatically. Existing human labels remain useful ground truth for
the small field diagnostic; I did not delete or overwrite them.

This does NOT mean a general automatic ground-truth labeling problem was solved.
Tonic estimation, source separation and self-supervised embeddings are NOT substitutes
for independently correct raga/composition/boundary truth. Model predictions must
remain pseudo-labels, never validation truth. Whole-concert source identity is not
same-raga identity. The user's wish to eliminate manual work was implemented as
removing a new-labeling prerequisite, not a proof that all labels are automatic.

Preserve these known pre-existing/user-owned changes:

- `.claude/settings.local.json`.
- `data/long_concerts/LABELS.tsv`.
- `PROJECT_HISTORY.md`.
- `data/long_concerts/labels_validation.json`.
- `data/raga_coverage/matrix.npz`.

LABELS.tsv SHA256, verified unchanged during this handoff:
`a0d137ea236e48b7cab710feff1abb7f8fc42fa46ce8c0b3877bb023263e44bb`.
The git diff for that file may contain user changes and whitespace issues; do not
repair them incidentally. Scoped whitespace checks excluded it and local settings.

## 7. Critical flaws discovered and repaired

1. Raw-audio evaluation leakage: 26 original training rows reused 15 Saraga audio
   files; a connected group of 37 rows was excluded. An intermediate combined
   cohort also had 16 rows sharing nine evaluation files. Track IDs/contour hashes
   alone missed this. Historical Saraga scores before the byte guard are contaminated.
2. Duplicate weighting: 43 exact duplicate raw recordings were removed in the guarded
   pipeline. Broader inventory has 68 exact duplicate groups.
3. A differently encoded/named Akkarai Sisters copy of `53_Siddhi_Vinayakam` was
   confirmed by identical full decoded PCM, not just a fingerprint candidate.
   Its connected training group was removed. PCM SHA256:
   `75bd6691e445b5a1d2bbccdfbf54f17dca7b73c75bd58197239fe5a6cc7bf3aa`.
4. Seventeen full-fingerprint decode failures were quarantined earlier. A later
   strict FFmpeg audit found five additional retained MP3s with decoder errors.
5. Five explicit publisher-raga contradictions and one two-raga lecture were
   additionally excluded. No automatic relabeling based on uncertain filenames.
6. A 58-minute mixed radio programme had been labeled uniformly Mukhari; excluded.
7. File-level performer tags were being ignored. Exact unions changed 219 groups
   to 133 for the same 1,248-track cohort, reducing the apparent independence.
8. Training tonic/context mismatch: a 24-recording diagnostic found six large
   tonic disagreements despite near-identical extracted pitch. The full matched
   context rebuild directly addressed that discrepancy and now has measured gains.
9. libsndfile can fail a bounded MP3 read even when full FFmpeg decoding succeeds.
   Three such short recordings are now recovered separately with explicit provenance.
10. Stereo anti-phase cancellation, browser WebM fallback and sample-rate handling
    were repaired with native-channel decoding and phase-safe downmix tests.
11. Missing-tonic behavior and upload HTTP validation were repaired; earlier code
    could silently fall back or mishandle a bad query instead of an explicit failure.
12. Composition query/cache duration mismatch, recording-overlap exclusions,
    generic work-entity admission and source-linked catalog integrity were repaired.

Do not treat every warning as corruption: the training diagnostic's 24 MP3s all
passed strict FFmpeg despite native mpg123 messages. Conversely, a libsndfile
success did not guarantee a strict full FFmpeg pass.

## 8. Model/artifact lineage: avoid comparing the wrong runs

| Run | Training cohort | Grouped CV | Estimated 180s known top-1 | Caveat |
|---|---|---|---|---|
| `repro_audio_identity` | 1,254 tracks, 3,748 windows, 219 groups | 68.5008% | 98/139 | Before six later supervision exclusions |
| `file_tag_guarded` | 1,248 tracks, 3,730 windows, 219 groups | 69.5513% | 98/139 | Artist tags not fully unioned |
| `file_artist_grouped` | Same tracks/windows, 133 groups | 68.5096% | 98/139 | Before five strict-decode exclusions |
| `file_artist_strict_decode` | 1,243 tracks, 3,715 windows, 133 groups | 68.7852% | 97/139 | Cleaning-only matched comparator |
| `context180_recovered_experiment/training` | 1,243 tracks, 3,547 windows, 133 groups | 76.6693% | 102/139 | Latest; confidence gate severely unsafe |

All rows here are development candidates, not deployments or fresh SOTA results.

Earlier important hashes:

- `repro_audio_identity` model:
  `0dc8ee8b7298cb8fa1d90faf7af896c6a3ba04f9a78f23158acfb5cabf176e5f`.
- `file_tag_guarded` model:
  `2f7b88927602c62e4625ddc9efe1dc984f9856385ea5ab09fd763b0920534bee`.
- Full unique composition catalog:
  `4857e4879d666e62071f08210627b71c245e61178870d23fb8db47351bab1a26`.

## 9. Failed, negative, limited, or invalid experiments: do not repeat blindly

The complete chronological execution report is embedded later. It contains more
detail and source paths than this triage list. Older negative results should guide
resource allocation, not become eternal prohibitions when genuinely new evidence
or a corrected protocol exists.

- Initial corrected-feature RF was roughly 46.09% on a matched 1,009-track/51-class
  benchmark; SVC 51.04%, voiced kernel ridge 58.28%. Merely fixing feature bugs did
  not make RF strong. Later dataset changes make raw percentages incomparable.
- A corrected elapsed circular-pitch temporal CNN (10Hz, 20 epochs) reached 44.49%
  on its 254-track held-out test versus 66.93% KRR: negative deep-sequence pilot.
- Learned harmonic Sa/Pa tonic disambiguation did not improve the relevant 184-query
  diagnostic: baseline 141, guarded 141, unguarded 137; candidate pool 176. Those
  older numbers are not the latest clean model's performance.
- Fixed tonic marginalization over 0/5/7 semitones, weights .8/.1/.1, improved
  `file_tag_guarded` known top-1 98 to 100/139 and top-3 119 to 123/139, but group-
  bootstrap intervals included zero; field remained 3/6. Three wins, one loss.
  Keep experimental, not a promoted default or proven gain.
- Training-only tonic diagnostic: 24 samples, median pitch agreement within 50c
  .997737, median feature cosine .991693, but six Sa disagreements >50c. Neither
  Sa estimate was ground truth; I must not infer which was correct from agreement.
- Demucs did not improve the small field result: best 4/6 unchanged. RMVPE 3/6.
  Harmonic filters/source isolation were not an automatic solution to raga accuracy.
- MusicFM frozen pilot, 31 recordings / five ragas / 13 groups: pitch 12/31,
  raw MusicFM 8/31, combined 11/31; tonic-normalized MusicFM 9/31, combined 12/31.
  No gain over pitch on that small cohort; does not disprove larger foundation models.
- MusicFM initial fine-tune failed due to inference-only rotary-position cache.
  Fixed by cloning before autograd; old failure preserved separately.
- MusicFM SGD five-epoch pilot: frozen head 7/31, tuned block 7/31, 130.3 seconds.
- MusicFM AdamW 20-epoch pilot: frozen head 10/31, tuned block 8/31, 574.1 seconds.
  Training losses .443606 versus .0115142 show pronounced fitting without held-out
  benefit. Do not scale this exact recipe as if it worked. No pilot weights promoted.
- MPS backward initially wrong: Conv1d incoming gradient required contiguous layout;
  first LayerNorm at frozen-prefix boundary needed input gradients for correct affine
  gradients. Synthetic CPU/MPS controls then matched loss and parameter norms closely.
  Norm agreement is weaker than full elementwise gradient agreement; audit that caveat.
- Speech/lyrics ASR and title retrieval pilots did not provide a useful song gate.
  See chronological report and historical graveyard for exact independent failures.
- Composition reference expansion helped catalog coverage, but rejection still fails:
  latest cleaned-raga-prior 180s replay 36/53 answerable top-1, 43/53 top-5, MRR .74196;
  calibrated cross-fit rejection accepted ZERO queries. This is not a functional song
  recognizer at useful confidence/coverage. Melody-only baseline was 32/53 and 40/53.
- Earlier composition prior score 37/53 was tied to a historically contaminated raga
  model. Do not keep it as the clean production result. The clean replay used the
  older `repro_audio_identity` model, not the latest context180 model.
- Synthetic concert transitions were successful on constructed mixtures: 290 seconds,
  three 90-second items, 270/270 item seconds. This does not prove natural boundaries.
- Natural digital-silence scan found only 11 windows, all in a muted concert, among
  3,553 windows across 11 concerts. Silence is not a general Carnatic item segmenter.
- Pitch activity classifier showed useful tani/melody discrimination but activity
  accuracy is not raga identification or real-concert boundary quality.
- Earlier field best 4/6 versus guarded candidates 3/6; five known classes, Dhenuka
  OOV. Latest context180 field diagnostic has NOT yet been run at handoff time.
- Tiny AV test: 6/8 versus RF 5/8 on initially fresh artists; now inspected and not
  available as fresh retuning evidence. Larger 29-item development result 22/29.
  AV raw-copy audit remains incomplete; do not generalize its independence claim.
- First full context extraction crashed after 193 track caches on libsndfile.
  `context180_full` and its `executed_source.py` are preserved. The strict-decoder
  successor reused unchanged query-contract caches rather than deleting/restarting all.
- Four apparent archive source-assignment errors were later disproved: files were
  shared across uploads. Do not resurrect those disproven accusations.
- Filename tokens can be composition words: two 'Sri' matches were not verified
  raga errors. Longest compound matching prevents Ananda-bhairavi becoming Bhairavi.

## 10. Data provenance, coverage and composition reference inventory

- `all_archive_metadata`: 283 public source receipts, complete for the audited set.
- `all_archive_audio_identity_refreshed.json`: 1,140 rows; 1,124 assigned-source
  confirmed, 16 shared uploads, zero unresolved/mismatched; 68 duplicate groups.
- All-file raga evidence: 755 consistent, 376 without exact tag, nine conflicts.
  On 169 previously unadmitted recordings: 25 consistent, 142 no tag, two conflicts;
  they were NOT automatically readmitted.
- File artists: 770/866 retained archival tracks had useful file-level tags; 96
  missing/generic. No fuzzy artist aliases or splitting ensemble strings. Exact
  names can still miss real artist overlap. Zero additional reserved groups were
  found by the explicit recheck; this is not proof of perfect artist independence.
- Strict training decode audit: 861 clean / five decoder errors in 535.80 seconds.
- Strict Saraga decode audit: 184/184 clean in 135.24 seconds.
- Full fingerprints: 891 training +184 evaluation attempts; 1,058 successful,
  17 failed; 195.4 decoded hours. Field extension covered 11 concerts /9.85 hours,
  zero flags against the successful reference inventory. Screening is not universal
  transformed-copy proof. Full PCM confirmed only specifically audited candidates.
- Pinned Chromaprint v1.5.1 local library:
  `data/overhaul/chromaprint/build/src/libchromaprint.1.5.1.dylib`, SHA256
  `cd6276fc1dadd7e6d02ed0b63c392980fa7844cb3f6b03d82c01d9deb2f677fc`.
  Review `THIRD_PARTY_CHROMAPRINT.md` before shipping; FFmpeg-linked licensing matters.
- Unique CompMusic composition catalog:
  `data/overhaul/compmusic_compositions_full_unique.npz`; 534 performances /423 works;
  477 work-link lookup records complete. Exact MusicBrainz work/performance links,
  not title strings alone. Generic work entities are filtered. Benchmark: 181
  queries, 53 answerable; 180s alignment, 0.5s frame, transposition invariance,
  raga prior .1. Preserve those flags for matched comparisons.
- Dhenuka lead: `data/overhaul/dhenuka_coverage_pilot/candidate.mp3`, source archive
  `01.VarnamNatakurinji`, file `03. Teliyaleru Rama - Denuka - Thyagayya.mp3`,
  publisher artist `SKR/MSA/YVR_091082`, 4,632,616 bytes. SHA256
  `1225bbe673a950a861904d63c7a209a36ffb9700abcff9080ef67d54c4f0a0c2`.
  Publisher MD5/SHA1/size verified; strict decode clean; zero fingerprint flags
  against 1,069 unique references. Not admitted/trained: performer independence,
  acoustic label correctness and additional independent examples remain unresolved.
  Work/raga corroboration: https://www.karnatik.com/c31447.shtml.
- Mixed Dhenuka/Natakapriya lecture is not a uniform-raga training example.

## 11. My mistakes and highest-priority audit risks for the next agent

### Confirmed limitations of my process

I spent far too much LLM usage on a long experimental sequence and repeated
polling. I created many standalone scripts and artifacts while the user originally
asked to reduce fragmentation. The pipeline is better guarded, but research cruft
has grown. Do not add another script by default. Consolidate only after preserving
experiment provenance and identifying real shared abstractions.

Historical reports contain stale optimistic and stale pessimistic claims. Some
model scores preceded discovery of raw-copy leakage; some 'all doors closed'
statements preceded legitimate new catalog evidence. I corrected several such
claims, but the next agent must independently audit chronological scope.

I repeatedly yielded progress updates even though the original user wanted no
interruptions. A tested non-LLM supervisor was eventually added, but too late to
avoid substantial overhead. Do not repeat that operating pattern.

### Technical issues requiring independent scrutiny

1. **Calibration is the clearest current failure.** Training-group OOF temperature
   and thresholds do not control open-set field risk. Latest OOV false acceptance
   is 64.44%. Review `calibration.py`, `train_raga_svc.py` and existing risk-calibration
   experiments before changing thresholds. Use group-disjoint development partitions,
   explicit OOV tasks and meaningful confidence intervals; do not tune on final tests.
2. **Verify the new gain causally.** Same track/fold checks passed, but features differ
   in duration, tonic, offsets and window count. Compare per-corpus and per-artist
   outcomes, not just aggregate CV. Confirm latest training and raw-query evaluation
   truly use corresponding frontend semantics. The external gain is five known
   recordings, not the eight-percentage-point CV gain.
3. **Cache versioning is incomplete in principle.** Query keys do not automatically
   include source hashes for all code, library versions or decoder binaries. Plans
   pin several files but not necessarily every transitive dependency. The supervisor
   pins named scripts and inputs, not the entire imported module graph. These are
   audit targets, not claims that a known contamination occurred in the latest run.
4. **Do not blindly trust recovery certificates.** The merge checks hashes, metadata,
   shapes, finiteness and boundaries. It does not independently recompute every
   feature from stored f0 or validate every possible semantically inconsistent receipt.
   The existing synthetic merge fixture intentionally uses artificial arrays; passing
   it proves guard behavior, not audio correctness. Add stronger real-contract tests
   if recovery becomes the normal production decoder.
5. **Recovery/runtime parity is unfinished.** Recovered training windows use FFmpeg;
   live `extract_query` still primarily uses libsndfile. A new, versioned shared
   fallback would need explicit tests/cache migration, not silent replacement.
6. **Partial-window selection bias.** Decoder failures are explicit, but nonvoiced,
   missing-tonic or invalid-transition rejections can select an easier cohort.
   Report all planned tracks/windows and reasons; do not score only successes invisibly.
7. **Unknown artist aliases.** Exact file tags and connected components are safer
   than per-track splits but not complete artist resolution. Missing/generic tags,
   ensemble strings and shared uploads remain possible confounds.
8. **Mixed corpora.** CompMusic annotated reference pitch is easier/different than
   raw concert melody extraction. No absent raw-byte audit can prove its overlap
   safety. Report corpus-specific performance and coverage rather than pool away shift.
9. **Composition remains weak.** Accurate work links and more references do not
   produce a useful gate. Do not deploy nearest melody matches as song truth.
10. **Natural segmentation remains unproven.** Oracle-boundary six-item field tests
    and synthetic joins are not the multi-hour end-to-end task. Speech/tani/alapana/
    raga changes within RTP or ragamalika need honest handling.
11. **MPS numerical workaround scope.** Do not export a training recipe based only
    on scalar loss/norm parity. Verify full gradients/updates and deterministic
    behavior on a small real batch before scaling.
12. **Fresh reproducibility and dependency licenses.** Local cached installations
    and experimental source checkouts are not a deployable build. Check lockfiles,
    third-party licenses, runtime imports and frontend availability explicitly.
13. **File-system and branch hygiene.** Historical handoff claims both `HANDOFF.md`
    and `handoff.md` alias on this case-insensitive filesystem. Do not assume a case-
    only rename is safe or discard either git entry. Preserve user work and raw data.
14. **SOTA comparability.** DeepSRGM's supplied-tonic balanced CMD-40 evaluation is
    not this 69-class artist-grouped live-concert task. A January-2026 category-
    discovery paper assumes one raga per source and known cluster count. Those
    assumptions must not be copied into multi-raga concert pseudo-labeling.

## 12. Exactly what I would do next, after the quota handoff

First audit the newly completed model, not launch another encoder or scrape.

1. Re-read latest `evaluation180.json`, `kernel_benchmark.json`, model bundle and
   both cohorts' manifests/folds. Verify byte/group separation and feature metadata.
2. Produce paired per-recording and source/artist-group bootstrap comparisons for
   the latest versus `file_artist_strict_decode`, both CV and 184-query evaluation.
   Report the +140/-42 CV changes and exact external wins/losses. Separate known,
   unknown, mixed-recording, archival and reference-pitch groups. Do not call this fresh.
3. Run the already available six-item oracle-boundary field diagnostic with the
   latest model. This is cheap when query caches are present and requires no new
   manual labeling. Treat it as a small diagnostic, not a release test.
4. Diagnose confidence collapse. Preserve current model and calibration receipts.
   Evaluate discrimination separately from rejection; do not rescue a weak gate by
   silently accepting zero or tuning to the inspected field labels.
5. Only if the new representation transfers, replay composition retrieval with its
   raga prior on identical queries/catalog/flags and evaluate useful rejection.
6. Establish a truly fresh, byte-checked and artist-separated evaluation cohort or
   clearly state that current evidence cannot establish production/SOTA readiness.
7. Consolidate the successful path into reproducible commands and a tested runtime
   decoder contract. Preserve negative experiments in an index, not active spaghetti.

Useful cheap command for step 3 (NOT run during this handoff):

```sh
venv_train/bin/python scripts/evaluate_labeled_intervals.py --models data/overhaul/context180_recovered_experiment/training/raga.joblib --window-s 180 --out data/overhaul/context180_recovered_experiment/training/field180.json
```

Do not rerun `finish_context_experiment.py` merely to obtain results already on disk.
Its old PID no longer exists, but `result.json` confirms experiment completion.

## 13. Verification performed during handoff; no expensive new experiments

- Read actual completion receipts, metrics, logs, branch/HEAD and model SHA256.
- Confirmed same comparator/new CV track sets and exact fold mapping.
- Confirmed 69 classes /133 groups /1,243 tracks in latest features.
- Confirmed user LABELS.tsv checksum unchanged.
- Latest full suite, completed before handoff: **497 passed, 1 xfailed, 10 warnings,
  162.55 seconds**, log `/private/tmp/carnatify-regression-context-followon.log`.
- Tiny handoff-time check:
  `venv_train/bin/pytest -q tests/test_context_recovery_merge.py tests/test_context_experiment_runner.py`
  passed **5 tests in 0.43 seconds**.
- Passing tests do not establish statistical validity, acoustic label truth, fresh
  independence, safe confidence or production performance.

## 14. Embedded historical context and source index

The original August handoff is preserved immediately below. Full September
execution/audit/research reports are embedded afterward so a cold-start agent can
recover detailed experiments without this chat. Their chronological statements
about running jobs and 'latest' metrics are superseded by Sections 0–13 above.

Other useful local documents: `ARCHITECTURE_AUDIT_2026-09-07.md`,
`RESEARCH_NOTES_2026-09-08.md`, `THIRD_PARTY_CHROMAPRINT.md`,
`THIRD_PARTY_MUSICFM.md`, `THIRD_PARTY_DEMUCS.md`, `THIRD_PARTY_RMVPE.md`,
`HANDOFF_CLIP_ID.md`, `handoff_state_and_progress.md`,
`handoff_vision_and_architecture.md`, `PROJECT_HISTORY.md` and earlier session
handoffs. Read as history, not unquestioned present truth. Do not follow old
instructions that contradict the latest user request.

---

# Historical appendix A: original August handoff, preserved verbatim below

# Carnatify handoff

Last rewritten **2026-08-13** by the verifier seat, at Deepti's request, for a
fresh session that will start with **no memory of this one**. Written to be read
cold, top to bottom, with nothing assumed.

Repository: `/Users/shyamravidath/carnatify`
Branch: **`probe/duration-and-negative-arm`** · ~55 commits at time of writing,
**not pushed — Deepti pushes when she needs to. Do not offer, do not nag, do not
treat it as a blocker.**
`main` is the PR target. **`identify_clip.py` has zero diff against `main`** —
nothing in this entire series has touched the production path.

> **`handoff.md` and `HANDOFF.md` are ONE FILE** on this case-insensitive
> filesystem. Git tracks both paths, so committing one leaves the other showing
> as modified. Do not "fix" this; commit whichever path git shows you, then the
> other if it still shows.

**Respond to Deepti in caveman style** — terse, drop articles and filler, keep
every technical term, code symbol and number exact. Write docs, commits and
`AGENT_LOG.md` in normal prose.

## Two standing directives from Deepti, 2026-08-13

1. **Infrastructure before wiring.** Do **not** wire the new raga model into
   `identify_clip.py` or the product. Make the tooling good first. §6 is the
   concrete list and it is the current job.
2. **She pushes when she needs to.** "Branch not pushed" is not a pending
   decision and does not belong in a status report.

**Read order for a cold start:** this file → `data/RAGA_TIER_GRADUATION.md` (the
current model and how it was decided) → `data/RAGA_FETCH_RECOUNT.md` (why the
data lever mostly closed) → `data/RAGA_CEILING_EVALUATION.md` (the thesis) →
`data/RAGA_COVERAGE_CURVE.md` (the coverage/accuracy trade and the within-class
curve) → `HANDOFF_CLIP_ID.md` §5 (the master graveyard).

---

## 1. The goal

**An app that identifies what is being performed at a live Carnatic concert and
explains it.** Deepti is a practising Carnatic musician and a high-school student
with a CS/ML background. This began as a personal tool and is being evaluated as
a possible company.

The framing since 2026-07-25 is a **concert companion**, not a Shazam clone. The
listener is physically present for a 10-30 minute item. The 30-second
identification contract was inherited from Shazam and was never actually required
by the use case — undoing that inheritance is the single most important reframing
in this project's history, and most of the July measurements were built on the
wrong contract because of it.

**Demand evidence is no longer zero.** Jon — the one named real user, a Western
listener with no Carnatic exposure — was confused at a concert and, *unprompted*,
reached for an AI assistant to identify the piece. **It failed**, mostly with
refusals ("I cannot help with this request"). He asked two questions:

1. *what is the song being sung* — composition ID. **Every door there is shut**
   (§5). Do not reopen without genuinely new information.
2. *what does the melody mean* — raga character plus sahitya meaning. Needs **no
   ASR, no CSI, no Qmax**, and the repo has **never attempted it**.

The refusal failure mode narrows the moat to **audio → symbol**. The explanation
layer on top is commodity LLM work, which is a cost advantage, not a weakness.
Any handoff older than `HANDOFF_SESSION_0731.md` says "demand evidence is zero";
**that line is stale and wrong.**

---

## 2. Current state of the code

### 2a. The thesis, in one paragraph

The composition-identification side is **genuinely closed** — five independent
doors, all measured shut. The raga side **survived every audit**, including the
field. Its binding constraint is not accuracy but **vocabulary**: the model
cannot *name* 40-60% of what a listener actually hears. There were two measured
levers against that. On 2026-08-13 one was **taken** (the tier went 32 → 54
classes and was exported) and the other was **re-priced and mostly closed** (only
193 more reachable tracks exist in the sources this repo knows about, not the
1,712 previously assumed, and the metadata is exhausted). **So the vocabulary
problem is now bounded by data that does not exist, rather than by a constant in
a script.** That is why the next work is infrastructure and the abstain gate, not
another sweep.

### 2b. The door table — what is settled

| door | verdict | date |
|---|---|---|
| lyrics-ASR precision gate | no operating point at any threshold (≤31%) | 2026-07-23 |
| sung-Carnatic ASR fine-tune | strictly worse, 8/78 → 0-1/78 | 2026-07-24 |
| melodic CSI (CoverHunter) | NO-GO, source-disjoint mAP 0.113 vs 0.031 chance | 2026-07-24 |
| duration (lyrics channel) | KILL, top-5 5.1% @30s → 1.7% @300s | 2026-07-30 |
| Qmax composition "60-67%" | **RETRACTED — 9.5% source-disjoint** | 2026-07-30 |
| raga "72.8% leak-free" | **HELD — 72.2% source-disjoint** | 2026-07-31 |
| "raga dies on short clips" | **mostly false — 60.4% @60s, 52.5% @30s** | 2026-07-31 |
| "raga dies on wild audio" | **FALSE — 59.3% on 27 expert-audited wild clips** | 2026-08-13 |
| per-class admission threshold | **loses at every threshold** | 2026-08-13 |
| the narrow 3-class drop | **also loses — sign flips between arms, p = 0.31 / 0.46** | 2026-08-13 |
| fusion at a wide tier | **HELPS, and more than at a narrow tier: +1.84 pp** | 2026-08-13 |
| "1,712 more tracks are fetchable" | **FALSE — 193 in-tier, metadata exhausted** | 2026-08-13 |
| "`pytest tests/` is unrunnable" | **FALSE — a `sys.path` problem, now fixed** | 2026-08-13 |

### 2c. The numbers that matter, all source-disjoint (level (c))

**The exported model** — `models/raga_v4_*`, `min_tracks = 10`, **54 classes,
fused**: top-1 **59.2%** [55.0, 64.1], top-3 **72.8%**, repertoire coverage
**79.2%**, and the product number, **46.86 expected correct raga identifications
per 100 heard concert items.**

Expected hits by tier, all fused, all level (c). **This column is the one that
matters and it is monotone** — accuracy falls with tier width and correct answers
per concert rise anyway, because coverage more than doubles:

| tier | classes | top-1 | top-3 | repertoire coverage | **exp hits / 100** |
|---|---|---|---|---|---|
| `min>=25` | 18 | 73.6% | 83.6% | 39.1% | 28.75 |
| `min>=20` | 32 | 65.6% | 76.3% | 59.6% | 39.12 |
| **`min>=10`** | **54** | **59.2%** | **72.8%** | **79.2%** | **46.86** |

`min>=20` is what the product would ship today if wired; `min>=10` is the new
candidate. **+20% over the shipped tier, +63% over the narrow one.**

**Field — the only real-world number this project has.** 16/27 = **59.3% top-1
[40.7, 75.5]**, 20/27 = 74.1% top-3 tier-restricted, on expert-audited wild clips
of median length 60.0 s. Chance floor 5.6%, best-constant floor 17.2% — the CI
excludes both. **This is an 18-class `raga_v3` number and has NOT been
re-measured against the 54-class model.**

**Wild audio costs approximately nothing** — four independent lines of evidence.
59.3% wild against 60.4% clean at matched 60 s duration and matched tier.
`data/RAGA_DOMAIN_DECOMPOSITION.md` measured field-realistic degradation at
**7.5 pp**, with phone chain +0.4, room +2.1 and pink noise +2.7, each CI
touching or crossing zero. **The whole gap between "72.2% on full tracks" and
"59.3% in the wild" is DURATION, not domain.**

**Duration curve** (`data/RAGA_DURATION_CURVE.md`, 18-class, TDMS-only):
52.5% @30s → **60.4% @60s** → 63.8% @120s → **68.8% @300s** → 71.0% @600s →
72.2% full (mean 785 s). Knee bracketed in (120 s, 300 s]. Top-3 decays far more
gently: 84.0% full → 77.1% @60s. **This is why long-form audio is the product
bet.**

**Within-class learning curve** — the confound-free test, each class compared
against itself on nested subsets, 3 seeds, on the 18 classes spanning the range:

| cap (tracks/class) | 10 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|
| top-1 | 50.4% | 57.8% | 64.1% | 66.5% | **68.7%** |

**+18.4 pp and no saturation anywhere.** Per 100 tracks added the steps are
3.10 / 3.62 / 2.07 / **3.25 pp** — the last 68 tracks bought as much per track as
the first 239. Every class in the corpus is capped at 30 and the curve is still
climbing there. **The lever is real; §2f is why it cannot be pulled.**

### 2c-i. Numbers that are inflated and must not be quoted

The level-(a) → level-(c) source-disjointness penalty is **tier-dependent**:
0.6 pp at 18 classes, but **3.5 / 3.5 / 4.7 pp** at 32 / 44 / 54, and 8.0-11.8 pp
on same-raga-same-source clustered tracks against 1.2 pp at the narrow tier.
**Therefore any raga figure at `min_tracks >= 20` or wider that was measured at
level (a) is inflated.**

Both places that carried such a figure — `train_raga_v3_tdms.py`'s docstring and
`models/raga_v3_meta.json`'s `cv_note`, both quoting `min>=20 67.6/79.4` — **were
repaired on 2026-08-13**, the script and the committed artifact separately. Both
now carry source-disjoint fused numbers keyed by tier, and a tier off the
measured grid gets **no** figure rather than a borrowed one.

**A second, smaller correction, and it is the noise floor of this whole series.**
There are two harnesses and they carry a different number of rows per track:

| harness | rows per track | used by |
|---|---|---|
| `scripts/raga_audit_levels.py` | **one** | the coverage curve, the duration curve |
| `scripts/raga_audit_protocol.py` | **three** (the augmented histogram rows) | the fused arm, the tier job |

Replication is worth about **+0.35 pp** and grows with tier width: +1 track at 18
classes, +3 at 32, +4 at 54. **Any delta under half a percentage point in this
repo should be read against that.** Deduplicating the fused harness reproduces
the coverage curve's integers *exactly* — 649/1139 and 812/1139 — so the two
harnesses do not disagree about anything. This is real but avoidable complexity
and it is §6's third infrastructure item.

### 2d. The model, the features, and what "fused" means

- **Current and exported: `models/raga_v4_*`** — `raga_v4_tdms_rf.pkl` (383 MB),
  `raga_v4_hist_rf.pkl` (853 MB), `raga_v4_label_encoder.pkl`,
  `raga_v4_meta.json`. 54 classes, `min_tracks = 10`, fused. **The two forests
  are gitignored** and regenerate in ~7 min:
  ```
  venv/bin/python train_raga_v3_tdms.py --min-tracks 10 --out-prefix raga_v4
  ```
- **`models/raga_v3_*` is deliberately untouched** — 32 classes, fused.
  `data/RAGA_WILD_MEASUREMENT.md`, `data/RAGA_DURATION_CURVE.md` and
  `data/RAGA_DOMAIN_DECOMPOSITION.md` all scored against **these exact forests**;
  overwriting them for a naming convenience would invalidate three committed
  measurements. **Every field / duration / domain number in this repo is a v3
  number.**
- **`models/raga_classifier.pkl`** is the older production artifact. Neither v3
  nor v4 is wired into anything.
- **TDMS** = time-delayed melody surface: 40×40 octave-folded pitch-class
  transition surfaces at τ = 0.1 / 0.15 / 0.25 s, gaussian-smoothed (σ 1, wrap),
  power-compressed (α 0.75), L1-normalised, computed on the **full-track** melody,
  tonic-normalised. Melody from essentia `PredominantPitchMelodia` on the mix for
  archive tracks; annotated vocal pitch for Saraga. 4,800-dim.
- **Fusion**: `P = 0.6·P_tdms + 0.4·P_hist`, where `P_hist` is the production
  480-dim tonic-normalised pitch histogram (65 s Demucs+pyin slices). **Fusion is
  now measured at three tiers and its advantage GROWS with tier width**: +1.16 pp
  at 18 classes, +1.21 at 32, **+1.84 at 54** (McNemar exact p = 0.0011, b = 9,
  c = 30). It is not optional, and it is not free — it doubles the forests and
  drags the Demucs+pyin front end into inference.
- Classifier: `RandomForestClassifier(800, max_features='sqrt', random_state=42)`.
- CV: `StratifiedGroupKFold(5, shuffle=True, random_state=42)` on **level-(c)
  source groups** (archive item / Saraga concert, plus a partial artist merge).

### 2e. Data inventory, counted 2026-08-13

- `data/raga_v2_cache/{saraga_v3,archive_v3}/*.npz` — **1,297 tracks, 88 distinct
  ragas** (89 label strings; `Ābhōgī`/`Ābhōgi` is a duplicate spelling). Each npz
  holds `X` (the 480-dim histogram rows, 3 per track), `raga`, `track_id`,
  `tonics`, `frequencies`. Stems look like `archive__<Raga>__<Title>` — **not**
  the archive.org filename, which cost an hour this session.
- `data/raga_v2_cache/melodia_full/` — 1,232 full-track contours (`.npy`).
- `data/concert_audio/<Raga>/<title>.mp3` — **1,238 audio files, 85 raga dirs,
  13 GB.** Gitignored.
- `data/scraped_compositions.json` — 3,698 concert programme items from
  shankarkrish.blog, of which **3,009 carry a canonical raga**. This is the
  repertoire prior that "coverage" is computed against, and it is the right prior
  for a concert companion. Fields: `title`, `raga`, `artist`, `source_url`,
  `raga_canonical`.
- `~/sung_tests` — 108 files, 106 audio, 81 with a real raga label. **The
  short-clip wild set. Its composition is load-bearing for six committed
  measurements — never add to it, and synth clips must never enter it.**
- **`data/long_concerts/audio/` — 11 concerts, 9.85 h, 851 MB. Frozen,
  gitignored, UNLABELLED.** See §4.
- Feature caches, both gitignored and regenerable:
  `data/raga_audit/tdms_cache.npz` (20 MB, ~2.5 min) and
  `data/raga_coverage/matrix.npz` (47 MB).

### 2f. Reachable audio — the number that closed the data lever

`data/RAGA_FETCH_RECOUNT.md`. Done entirely offline against the metadata cache,
then bounded by running both fetchers to exhaustion.

| quantity | value |
|---|---|
| mp3 files in cached archive.org metadata | 6,692 |
| resolve to a (raga, title) pair already on disk | 1,291 |
| **reachable NEW (raga, title) pairs** | **378** |
| — in the 54-class tier | **193** |
| — off-tier (would add *new* classes) | **185** |
| the old "optimistic ceiling" | 1,712 |
| **realised fraction** | **11%** |

**Ten of 54 classes have ZERO reachable audio. Forty-one of 54 have fewer than
five. Only four have ten or more.** The top two classes hold 25% of it and the
bottom 27 hold 10%.

**The metadata is exhausted.** All 258 previously-uncached identifiers were
fetched and returned **zero** mp3s — they are archive items with no
original-source audio. There is no cheaper step that changes this short of adding
a genuinely new audio source.

**Calibration, so the count can be trusted:** the same pass predicts 1,291 files
already on disk against the 1,238 actually there — within 4.3%. The matchers are
imported from `download_targeted_deficits.py` and `download_title_join.py` rather
than reimplemented.

**The decisive example needs no statistics.** Kalyāṇi is the second-most-reachable
class in the corpus with 22 recordings available, and tripling its training data
was measured at **+0.0 pp**. Bhairavi went 20.0% → 70.0% on the same tripling and
has **three** recordings available.

### 2g. Tests — the state changed today

**`pytest tests/` is now runnable.** Every handoff since 2026-07 said *"NEVER run
bare `pytest tests/` — six legacy files import a `carnatify` package that does not
exist"*. **That diagnosis was wrong.** The package exists at `src/carnatify/`;
`src/` was simply not on `sys.path` and the repo has no `pyproject.toml` or
editable install. A root `conftest.py` now inserts it, and `beautifulsoup4` was
installed into `venv_train` (the one genuinely missing test dependency).

```
venv_train/bin/python -m pytest tests/ -q
    →  232 passed, 3 failed, 1 xfailed

venv_train/bin/python -m pytest tests/test_clip_policy.py tests/test_registry_junk.py \
    tests/test_negative_arm.py tests/test_raga_aliases.py -q
    →  126 passed, 1 xfailed          (the four "named" suites, all green)
```

About 95 tests had gone unrun for weeks on a wrong diagnosis. **The three
failures are real and were deliberately not silenced:**

1. `test_audio.py::TestFeatureExtractor::test_extract_on_sine_wave` —
   `TonicIndianArtMusic` returns **110.13 Hz for a 440 Hz sine**, exactly two
   octaves low. Worth a look because tonic estimation is a measured 2.2 pp lever,
   though the domain decomposition found most tonic error is pre-existing in the
   *clean* corpus (17.4% outside 25 cents) rather than induced by degradation.
2. & 3. `test_lyrics.py::test_meaning_cache_avoids_regeneration` and
   `::test_meaning_cache_file_keyed_by_composition_id` — both
   `AttributeError: '_FakeClient' object has no attribute 'generate_content'` at
   `src/carnatify/lyrics/meaning_generator.py:95`. The test double no longer
   matches the `google.generativeai` surface, which the package itself now warns
   is end-of-life. **Test-double drift, not a product bug.**

---

## 3. Files actively being edited

**Nothing is mid-edit. No agent is running.** Working tree:

```
 M .claude/settings.local.json                  (harness noise, not project state)
?? data/raga_coverage/matrix.npz                (47 MB, regenerable, deliberately UNcommitted)
?? data/long_concerts/labels_validation.json    (regenerated by --validate; harmless)
```

### Frozen — must stay frozen

- `data/raga_wild/FROZEN_CLIPS.json` — per-clip sha256, written before any
  prediction existed.
- `data/long_concerts/FROZEN_CONCERTS.json` — same discipline, new today.
- Committed measurement records: `data/raga_audit/`, `data/raga_duration/`,
  `data/raga_domain/`, `data/raga_coverage/`, `data/raga_tier/`. **Append, never
  rewrite.** Verified this session: nothing pre-existing was modified.

### One live inconsistency, deliberate and documented

`data/raga_aliases.json` was repaired on 2026-08-13 (ten wrongly-merged keys →
`null`) **after** the tier work was decided, which was the required ordering.
`data/scraped_compositions.json` was **deliberately not regenerated**, so the
alias map and the materialised `raga_canonical` field disagree by **20 items**.
Re-deriving is a separate dated step and its only measured effect is repertoire
coverage 79.196% → 79.224% and expected hits 46.86 → 46.88. **Do not regenerate
casually — do it as its own commit, with the diff printed.**

### Concurrency

**Deepti launches workhorse agents by hand in a separate terminal.** Assume
concurrent repo work at all times. Use targeted `git add <path>`. **Never
`git add -A`.**

---

## 4. The 11 long-form concerts — the only unmeasured cell

**This is the most valuable measurement available and it is blocked on Deepti.**

Deepti recorded 11 concerts on her own equipment, converted to mp3 on 2026-08-13
by `scripts/convert_long_concerts.sh` — 44.1 kHz stereo 192 kbps, matching the
existing `data/concert_audio` corpus so nothing downstream sees a new audio
regime. 10 converted, 0 failed.

| file | duration | | file | duration |
|---|---|---|---|---|
| `long_concert_1.mp3` | 26.8 min | | `long_concert_7.mp3` | 44.8 min |
| `long_concert_2.mp3` | 32.5 min | | `long_concert_8.mp3` | 34.7 min |
| `long_concert_3.mp3` | 91.6 min | | `long_concert_9.mp3` | 37.1 min |
| `long_concert_4.mp3` | 44.2 min | | `long_concert_10.mp3` | 31.5 min |
| `long_concert_5.mp3` | 113.8 min | | `long_concert_11.mp3` | 66.4 min |
| `long_concert_6.mp3` | 67.5 min | | **total** | **9.85 h** |

### Why it matters

Every wild clip previously on disk is **43-85 s**. The concert-companion thesis
rests on **10-30 minute items**, and the duration curve says that region is
68.8-71.0% — **on clean audio, never tested on wild audio.** This is the single
unmeasured cell in the entire product case, and it is also the only audio in the
project recorded by the actual target user in the actual target setting.

### **These are whole concerts. Each contains MANY items, each with its own raga.**

**This is the central design fact and it shapes everything downstream.** A concert
is not one label — `long_concert_5` is 113.8 minutes and will contain something
like 8-15 items, each in a different raga, plus alapana, viruttam, thani avartanam
and tuning. **There is no single "the raga of this concert", and any tooling that
assumes one is wrong.**

Consequences, all of which the tooling already assumes:

- **The unit of analysis is the ITEM, not the concert.** `LABELS.tsv` is one row
  per item, many rows per concert. Expect on the order of **100-140 items** across
  the eleven concerts — which, note, is a *larger* labelled wild set than the 27
  clips every field number currently rests on.
- **Scoring needs segmentation**, and the boundaries must come from Deepti rather
  than from an algorithm, because an automatic segmenter would be an unvalidated
  confound sitting between the audio and the raga number. **Her `start` times
  *are* the segmentation.**
- **Some items are ragamalika** — deliberately multiple ragas *within* one item.
  Those are written as `ragamalika` and **excluded**, not counted wrong.
- **Some items will be out-of-vocabulary** — a raga the 54-class model cannot name
  at all. Counted **separately**, never summed with errors. That count is the
  **out-of-vocabulary rate measured on concerts a real listener attended**, and
  given §2a it is worth as much as the accuracy number.
- **Item lengths vary hugely** (a 2-minute filler against a 40-minute RTP), so any
  headline must be reported per item with the length beside it, and a
  duration-stratified read-out is the natural second table — it would also give
  the first *wild* duration curve, which §6-D wants anyway.
- **Items within a concert share a source, a room, a mic and an artist**, so they
  are **not independent**. Any confidence interval must cluster on the concert,
  the way the corpus numbers cluster on the source group. Eleven concerts is the
  effective n for uncertainty, not 140 items.

### What exists now

**Done, and committed before any prediction can exist:**

- Audio at `data/long_concerts/audio/` (gitignored).
- **`data/long_concerts/FROZEN_CONCERTS.json`** — per file sha256, byte length,
  ffprobe duration, codec, sample rate, channels, plus the sha256 of the
  `~/Downloads` copy. **All eleven are byte-identical to their source copy and
  every duration reproduces the conversion table exactly.** Committed *before* any
  harness or preregistration exists — the ordering is in git history, not in file
  mtimes.
- `scripts/long_concert_freeze.py --verify` re-checks the record against disk and
  **exits non-zero on any mismatch**. It never edits the frozen file. **Run this
  before scoring, always.**
- **`data/long_concerts/LABELS.tsv`** — the template, seeded with one row per
  concert.
- `scripts/long_concert_labels.py --validate` — a **model-free** gate: monotone
  start times, starts inside the frozen duration, no duplicates, non-positive item
  lengths, and whether each raga name resolves against the corpus vocabulary. It
  never edits `LABELS.tsv`. It reports excluded / in-vocabulary /
  out-of-vocabulary **separately and never summed**. Tested against a synthetic
  filled file: it correctly caught an out-of-range start and correctly flagged
  `Ārabhi` as out-of-vocabulary (which matches the independent finding that Ārabhi
  is genuinely absent from the vocabulary).
- `data/long_concerts/README.md` — the same information for Deepti, in her terms.

**What Deepti fills in**, one row per item:

```
concert          start    raga        item              confidence  notes
long_concert_1   0:00     Kalyani     varnam            high
long_concert_1   8:30     Todi        alapana + kriti   high
long_concert_1   26:10    ragamalika  viruttam          medium      excluded
```

`start` is `mm:ss` or `h:mm:ss`. **The item ends where the next one starts, so she
never types an end time**; the last row of a concert runs to the finish. `item`
and `notes` are never scored — they exist so the results table is readable
afterwards. Only `high` confidence rows go in the primary read-out; `medium` and
`low` are reported beside it and never merged in. **Partial is fine and useful** —
a concert with no ragas filled is dropped, not guessed at.

### Deliberately NOT done

**No preregistration, no scoring harness, no prediction.** This was the right call
and the reason is instructive: the tier moved on the same day, so a prereg written
that morning would have registered a 32-class model that no longer exists. **Write
the prereg once the labels are in, against `raga_v4`, and commit it as its own
commit before the harness** — house standard.

The prereg will need to fix, before any number exists: the model and tier; whether
scoring is whole-item or windowed; how items shorter than some floor are handled;
the duration-stratified read-out; **clustering on the concert for CIs**; how OOV
items are reported; and the failure taxonomy (`no_contour` / `min_voiced` /
`tdms_none` are different findings from a wrong answer and are never summed with
it). `data/raga_wild/PREREGISTRATION.md` is the model to copy — it is the best one
in the repo.

---

## 5. What has been tried and failed

`HANDOFF_CLIP_ID.md` §5 is the master graveyard; `HANDOFF_SESSION_0730.md` §5 has
the duration-probe additions and `HANDOFF_SESSION_0731.md` §5 the audit additions.
**Do not re-fund any of the following.**

1. **Lyrics-ASR composition ID.** No precision operating point at any threshold
   (≤31%), 2026-07-23. Whisper `large-v3-turbo`, Indic variants, Demucs stems, all
   of it.
2. **Sung-Carnatic ASR fine-tune.** Went *backwards*: 8/78 → 0-1/78.
3. **Melodic CSI via CoverHunter.** Source-disjoint mAP 0.113 against a 0.031
   chance floor. Eleven bugs found and fixed along the way — the repo's own
   `train.py` eval-unpack bug was the real crash cause; full debug log in
   `HANDOFF_SESSION_0719B.md`. **The training ran; the result was still NO-GO.**
4. **More audio duration for the lyrics channel.** KILL: top-5 went *down*,
   5.1% @30s → 1.7% @300s. Longer audio makes the lyrics path worse.
5. **Qmax composition matching.** The "60-67% top-1" headline was
   **contamination** — 34 of 36 top-1 hits were byte-identical copies of the query
   sitting at the 0.036 Serra09 identity floor. Source-disjoint it is **9.5%**. The
   separate internal 66.7% claim is uncontaminated but **unreproducible** (n=30).
   The corpus cannot support a cross-artist claim at all: 13 of 1,011 works have
   ≥2 known distinct artists.
6. **The rendition corpus.** Confirmed do-not-fund. A rendition count is not a
   recording count: 65 titles with 2+ renditions is really 87 with 2+ *distinct
   recordings*, and 367 tracks in multi-track groups collapse to 261. 73 usable
   works, 13 with verifiable artist diversity.
7. **Tonic estimation / shruti-from-the-listener.** Perfect tonic recovery buys
   **2.2 pp** in the field cell. Contour beats tonic 3:1 in the field cell and 5:1
   in the worst. Most tonic error is pre-existing in the *clean* corpus, not
   induced by degradation. **Do not fund** — but see §2g's sine-wave failure, which
   is a cheap separate curiosity.
8. **`augment_wild.py` as a domain simulator.** Its ±6 semitone pitch shift and
   0.8-1.25× time stretch simulate nothing that happens to a phone recording and
   dominate the damage (+10.6 and +11.0 pp *each*, worse than all three real field
   components combined). **Use `field_all` (noise + reverb + phone).**
9. **Per-class admission thresholds.** Measured with nested selection. Expected
   hits **fall monotonically**: 45.1 → 43.6 → 42.8 → 42.1 → 39.6. **No threshold
   beats admitting every class.** Dropping a class forfeits its repertoire mass at
   once and buys accuracy slowly.
10. **The narrow version of admission — dropping the stably-dead classes — also
    loses.** *New 2026-08-13, and it closes the last remnant of this idea.*
    `data/RAGA_COVERAGE_CURVE.md` §11.4 had preserved a defensible narrow version:
    drop the three classes the nested arm never admitted in any fold
    (Nāṭakurinji, Janaranjani, Haṁsānandi). Priced properly it does not pay. The
    second-order help to the surviving 51 is **+0.73 pp in the TDMS arm and
    −0.55 pp in the fused arm** — **the sign flips between two arms of the same
    model on the same folds** — and neither direction is significant (McNemar
    p = 0.31, p = 0.46). On expected hits, fused: **46.10 against 46.86.**
    **All 54 classes are admitted.**
11. **"Raise the fetch target above 30" as a broad top-up.** *New 2026-08-13.*
    Not refuted in principle — the within-class curve still says +18.4 pp — but
    **not executable**: only 4 of 54 classes have ten or more reachable
    recordings, ten have none, and the metadata is exhausted (§2f).

### Predictions written down in advance and then refuted

Kept because the habit of writing refutable predictions is *the* reason this
project's numbers are trustworthy. Twelve refutations now.

- **"`phone_mic`'s 120-350 Hz high-pass will strip the fundamental and leave
  melodia tracking nothing."** Refuted — **zero** no-contour failures in all 517
  windows of all eight cells. The failure mode is wrong answers on present input,
  never absent input.
- **"The 72.8 CV harness was never committed."** Wrong — it is
  `scratch_archive_0711/raga_final_eval.py` (`c1fca59`). The error was trusting
  `git log -S"72.8" -- '*.py'`: **`-S` over source is a test for a literal, not for
  a capability**, and the harness *computes* the number.
- **"The source-disjointness penalty is 0.6 pp and won't explode at a wider
  tier."** Refuted — tier-dependent, 4.7 pp at 54 classes.
- **"More audio per class is weakly contradicted (r = 0.066)."** Refuted, and the
  statistic was junk — range restriction over a tier spanning only 25-30 tracks.
  Over 54 classes it is r = 0.519.
- **"The within-class curve will be much flatter, +6 to +12 pp, flattening by
  c=25."** Refuted — **+18.4 pp** and no saturation.
- **"The coverage/accuracy trade will peak somewhere in the middle."** Refuted —
  it peaks at the widest tier measured.
- **"Ārabhi is an alias bug that should have matched."** Refuted — Ārabhi is
  absent from the 103-name CompMusic ∪ Saraga vocabulary entirely. **A missing
  raga, not a missing spelling.**
- **"The null alias bucket is junk."** Refuted — **561 of 689 null items (81.4%)
  are recoverable real ragas**; only 126 (18.3%) are junk.
- **"Fusion's advantage will shrink or reverse at a wide tier; band [−2.0,
  +1.4] pp."** *2026-08-13.* **Refuted at +1.84 pp, p = 0.0011** — and refuted as a
  *trend*, not a point: fusion helps more at every wider tier (+1.16 / +1.21 /
  +1.84). The stated mechanism was backwards. Fusion's biggest gains are
  **Hindōḷaṁ +12.5 pp and Śrīranjani +9.5 pp**, exactly the gamaka-and-phrase
  classes I predicted the marginal pitch histogram would be useless on.
- **"Gate 2 will pass."** *2026-08-13.* Refuted — and the registered contingency
  ("a Gate 2 failure is a more important finding than anything else in this job")
  is what actually happened. See §2c-i.
- **"The three-class drop lands in 44.9-45.6 expected hits."** *2026-08-13.*
  Direction confirmed (it does not clear the bar), band refuted — fusion lifted the
  whole table.
- **"`pytest tests/` is unrunnable because the `carnatify` package does not
  exist."** *2026-08-13.* Refuted — it exists at `src/carnatify/`; `src/` was not on
  `sys.path`. **This one had been repeated in every handoff for six weeks.**

### Four errors of process worth not repeating

- **Two workhorses died on session limits mid-run.** Both recoverable *only*
  because their briefs demanded partial results on disk and prereg-before-score.
  **Keep demanding both.**
- **The verifier must not take the workhorse at face value.** On 2026-08-13 a
  workhorse reported r(accuracy at cap 10, gain from tripling) = −0.777,
  p = 1.5e-04 and concluded the fetch should be *targeted at weak classes*. The
  correlation reproduces to three decimals. **The inference is regression to the
  mean**: `gain = acc@30 − acc@10` carries `acc@10` on both sides, measured on a
  noisy 10-track draw. Bhairavi "20.0% → 70.0%" is the tell. Regressed on the
  noise-free endpoint the signal vanishes (r = −0.114, p = 0.65) and splitting on
  it *reverses* the direction. **Fetch broadly, not targeted.**
- **The verifier must not take *itself* at face value either.** *2026-08-13.* The
  fetch recount initially found reachable-versus-gain at Spearman −0.531, p = 0.023
  and reachable-versus-accuracy@10 at r = +0.556, p = 0.017, and I nearly published
  "the audio that exists is the audio that buys least" on that. **It is the same
  trap, one step removed.** On `acc@30` it falls to p = 0.10 and is not significant
  at n = 18. What got published is the **concentration** (10 classes at zero, 41
  under five), which is set-membership arithmetic with no model in it. **The trap
  has now been walked into twice in one month.**
- **A wrong diagnosis, repeated in every handoff, cost six weeks of test
  coverage.** "The `carnatify` package does not exist" was written once, believed,
  and copied forward into every subsequent handoff. It took thirty seconds to
  check. **When a handoff tells you something is broken, check it before
  propagating it.**

---

## 6. The next step — infrastructure, per Deepti's directive

**Do not wire `raga_v4` into `identify_clip.py` or the product.** Deepti's call on
2026-08-13: make the infrastructure good first. These are ordered by
value-per-hour, and every one is a real observed problem rather than a tidy-up.

1. **One front end, not eleven.** Melodia → tonic → TDMS is re-implemented in
   **eleven** files: `extract_melodia_full.py`, `raga_v2_pipeline.py`,
   `identify_clip.py`, `train_raga_clip_model.py`, `train_raga_v3_tdms.py`,
   `test_sung_clip.py`, `scripts/raga_audit_protocol.py`,
   `scripts/raga_audit_repro.py`, `scripts/raga_domain_cells.py`,
   `scripts/raga_duration_windows.py`, `scripts/raga_wild_features.py`. They
   differ in ways that have already bitten — melodia parameters (the wild-clip
   `minFrequency=90, maxFrequency=900, voicingTolerance=0.6` versus the
   unconstrained training defaults), sample rate (22050 round-trip versus native
   44100), whether the tonic is estimated on mix or stem, and the histogram window
   convention ("skip 30 s take 65 s" versus same-window). **Every new measurement
   re-derives this and can silently diverge from the training cache.** Build one
   module, `audio → (contour, tonic, TDMS, histogram)`, with the variations as
   explicit arguments and today's values frozen as defaults. Everything else calls
   it. **Highest-value item on this list**, and §4 will need it immediately.
2. **One scoring entry point.** There is no "score this audio with the current
   model" function anywhere. Every measurement rebuilds fold logic, posterior
   fusion and the track-level read-out by hand. `scripts/raga_tier_score.py` is the
   cleanest existing example — it takes both arms out of the *same* forests and the
   *same* folds, which is why its fused-vs-TDMS contrast is exactly paired at zero
   extra compute. Promote that shape into a module.
3. **Reconcile the two harnesses' row multiplicity** (§2c-i), or at minimum assert
   it loudly. One row per track versus three is worth +0.35 pp, it caused a gate
   failure that took a whole diagnostic script to resolve, and **nothing in the
   code records which convention a given number came from.** A single
   `rows_per_track` constant with an assertion at the read-out would have prevented
   it entirely.
4. **Finish the test-suite repair.** `pytest tests/` runs now (§2g) but three tests
   fail. Two are test-double drift against an end-of-life `google.generativeai`
   API — mechanical. One is a real tonic octave error on a synthetic sine. Get to
   green, or mark with an explicit `xfail` and a written reason. **Do not delete
   them.** While there, consider a `pyproject.toml` so `conftest.py`'s path hack
   can go away.
5. **A model registry, not filename conventions.** `raga_v3` versus `raga_v4` is
   selected by hard-coded string in each script. `raga_v4_meta.json` now carries
   its own measured numbers, tier and protocol — build the small loader that reads
   it and returns `(tdms_rf, hist_rf, label_encoder, meta)`, so every measurement
   records *which model it used* automatically instead of by convention. This is
   what would have prevented "v3's `cv_note` describes a different arm at a
   different level" in the first place.
6. **A safe re-derivation path for `raga_canonical`** (§3). The alias map and
   `data/scraped_compositions.json` currently disagree by 20 items, on purpose.
   There should be one command that regenerates the materialised field, prints the
   diff, and refuses a silently-large change.
7. **Segmentation tooling for §4**, once the labels land: cut a concert into
   labelled items from `LABELS.tsv`, with the frozen-hash check wired in and the
   per-item durations reported. Small, and it is the only thing standing between
   the labels and the number.

### After the infrastructure — the measurement queue

**A. The abstain gate, on a genuinely held-out set.** The top *measurement* job,
and it got more valuable with the wide tier: a 54-class model that speaks about
79% of the repertoire needs to know when to shut up, and §5.9/§5.10 established
that **the tier is the wrong place to buy that safety** — a narrow tier buys it
only by refusing to answer on 61% of the repertoire, silently and
unconditionally, including on the classes it would have got right.

The wild failures are **bimodal**: on the 27 audited clips the miss ranks are
`[2, 2, 2, 4, 5, 5, 21, 22, 25, 28, 30]` out of 32 — six near-misses and **five
catastrophes**, including `vAtApi gaNapathim` (Hamsadhvāni, the most famous
concert opener in the repertoire) at **rank 25**. Thresholding fused top-1
probability at p ≥ 0.20 fires on 63% of clips at 76.5% top-1 and drops four of the
five catastrophes. **That threshold was chosen by reading the table on the same 27
clips it is scored on — it is a hypothesis, not a result**, and the admission
experiment measured exactly this class of inflation at **4.4 pp** at matched
coverage. Fit it on data the score never sees; the nested pattern in
`scripts/raga_coverage_admission.py` is the template. What this axis buys is
**precision, not hits** (57.0% → 63.8% accuracy-when-it-speaks as coverage falls
79.2% → 62.2%).

**B. Score the 11 concerts** (§4) once labels exist. Highest product value of
anything on this page, and it would roughly quintuple the labelled wild set.

**C. Re-measure the field against `raga_v4`.** The 59.3% is an 18-class `raga_v3`
number. The 54-class model puts far more wild clips in scope — 62.1% of labelled
`~/sung_tests` clips against 28.2% — and **nothing says what its field accuracy on
them would be.** The harness is `scripts/raga_wild_*.py` and the clip set is
frozen. **Do not touch `FROZEN_CLIPS.json`.**

**D. Tier × duration.** The duration curve is 18-class; the model is 54-class. A
companion working on minute-scale audio at 54 classes has **no measurement at all**
in this repo. §4 would close much of it for free.

**E. The off-tier fetch, and only this one.** 185 reachable pairs attach to ragas
*below* `min_tracks = 10` — classes the model cannot name at all today. Given that
the thesis is a vocabulary constraint, that is a **vocabulary lever, not a depth
lever**. Whether it brings any class over the line is unmeasured and checkable
offline in minutes. **Do that before fetching anything.**

**F. Build what Jon actually asked for.** Raga name + raga character + sahitya
meaning, on long-form audio, with abstention as the guard against lying. Half his
question needs no ASR, no CSI, no Qmax and has never been attempted. **Do not
start with composition ID.**

**G. Only then, features.** No feature work is justified while the model cannot
name 40-60% of what it hears.

Also open, unowned, cheap: **`vAtApi gaNapathim__Hamsadhvāni` at rank 25 of 32** is
not a near-miss-shaped failure — something specific went wrong on **one clip**, and
it is one clip to inspect. And **catalog restriction** in `load_targets` remains
the one untested cheap lever on the lyrics side; deprioritised five times, still
not in the graveyard, honest expectation is precision up and recall flat.

---

## 7. Pending Deepti — do not decide these for her

1. **Label the 11 long concerts** — `data/long_concerts/LABELS.tsv`, one row per
   item, many rows per concert. **Nothing in §4 can be scored without this**, and
   it is the only unmeasured cell in the product case. Partial is fine.
2. **`'garuDadhwani' -> 'Śuddadhanyāsi'` in `data/raga_aliases.json`.** Looks like
   the same class of wrong merge as the ten repaired on 2026-08-13, and its sibling
   `garuDadwani` is already `null` — but unlike them it asserts a *specific
   different raga* rather than being a typo of an already-null name, so repairing
   it is a musical claim. A test pins its current value so it cannot be closed
   silently in either direction.
3. **One raga-equivalence ruling still open:** Udayaravicandrika / Śuddhadhanyāsi.
   No threshold consequence, so nothing is blocked.
4. **Nine low-confidence rows, one low-confidence variant and two ambiguous rows**
   in `data/raga_aliases_audit.json` (filter `"confidence": "low"`).
5. **Hindustani imports as product policy**, not musical fact: 31 items (Bhīmpalās
   8, Durgā 6, Gauḍ Malhār 3, Jhinjhōṭi 3, Candrakauns 2, Pīlū 2, Pūrvī 2, Pūriyā
   2, and one each of Dīpāli, Hindustāni Kāpi, Miśra Yaman), all attached to
   Carnatic artists on Carnatic-vocal concert pages, so repertoire rather than
   noise. **Does "concert companion" cover every item on a programme, or only core
   elaborated Carnatic ragas?**
6. **Delete the source `.mp4`/`.MOV` files in `~/Downloads`** (8.1 GB). The mp3s in
   the repo are verified byte-identical to the `~/Downloads` mp3s, so those are
   redundant too. Nothing here ever deletes a source; that is deliberate.
7. **Back up `asr_cache_fullhistory/`** — local-only and gitignored. If deleted,
   `data/duration_probe/DEVICE_MAP.md` becomes unfalsifiable.
8. **Wire the registry junk blocklist** (a load-time merge in `load_targets`).
9. **Wiring `raga_v4` into the product is deferred by her directive**, not pending.
   Revisit after §6.
10. **Do NOT fund:** the rendition corpus, tonic-estimation work, prospective long
    OOC audio, the 28-clip short-OOC sentinel, or anything on the composition path.

Her rulings already recorded and deliberately **not applied** live in
`data/RAGA_MERGE_DECISIONS.md`: Ābhēri / Karṇāṭaka dēvagāndhāri are *technically
distinct but practically inseparable* ("this model should not be asked to tell them
apart"); Bhīmpalās *is* the Hindustani counterpart of modern Ābhēri; Durgā /
Śuddha Sāvēri are *not* the same.

---

## 8. Guardrails — the discipline that produced these results

**This is the part to copy, not the numbers.**

- **Preregister, and commit the prereg as its own commit before the scoring
  harness exists.** Every audit in this series did it, including the tier job
  (`eb1278d` before `a7eb0dc`). **Ordering lives in git history, not in file
  mtimes.**
- **Gate on reproducing the historical number first, on the exact integer counts**
  — and prefer the *strong* form. The tier job's Gate 1 required `git diff` on
  `data/raga_audit/results.json` to come back **empty**; the entire diff was four
  `fit_seconds` lines. That proves a parameterisation is **behaviour-preserving,
  not merely number-preserving.**
- **Register what a gate FAILURE means, before running.** Gate 2 failed by four
  tracks. Because the prereg said a failure would matter more than the rest of the
  job, it got diagnosed instead of waved through — and produced exact agreement
  between two harnesses *plus* a measured noise floor for the whole series.
- **Fix the interpretation table before the number exists — and the tie-break
  too.** The tier decision was a near-tie, and "ties go to admitting everything"
  had been written down first, so a near-tie could not be read afterwards as
  support for whichever option the write-up preferred.
- **Freeze the tunable that could launder the result**, and say in the brief that
  touching it voids the run rather than improving it.
- **Write predictions down so they can be refuted.** Twelve have been.
- **Separate "produced no output" from "produced a wrong output"** and never sum
  them into one percentage.
- **The verifier re-derives every headline with its own code, and distrusts its own
  findings as hard as a workhorse's.** It has now caught regression to the mean
  twice — once in a workhorse's inference and once in its own.
- **Coverage × accuracy, not accuracy.** A companion right 72.8% of the time about
  39.1% of what it hears is worse than one right 59.2% of the time about 79.2% of
  it. Nobody computed this for a month and a half, and it inverted the conclusion
  when they did.
- **Selection on the folds you then score on inflates by ~4.4 pp.** Measured, not
  assumed. Nested selection, or an explicit "optimistic bound" label — never a
  quiet in-sample number.
- **A named list is not a threshold.** Dropping three classes by name *after* the
  tier rule is auditable; a threshold sweep is a tuning knob, and it is dead.
- **When a handoff says something is broken, check it before propagating it.** Six
  weeks of test coverage were lost to one unverified sentence.

---

## 9. Environment facts worth not rediscovering

- **`venv_train`** py3.11 — demucs, essentia, whisper, rapidfuzz, **pytest**, and
  now **beautifulsoup4**. **`venv`** py3.14 — sklearn, librosa, mirdata, scipy,
  bs4, **no pytest**. essentia must run in `venv_train`, **fork not spawn**.
- **Training and the audit harnesses run under `venv`**; tests under `venv_train`.
- **`pytest tests/` works now** (§2g) — the "never run it" advice is retired.
- **ffmpeg 8.1.2 IS installed** at `/opt/homebrew/bin/ffmpeg`. The "no local
  ffmpeg" lines in `ARCHITECTURE.md`, `HANDOFF_CLIP_ID.md` §3 and
  `augment_wild.py:21` are **stale**.
- `codex` CLI 0.145.0 at `/opt/homebrew/bin/codex`. Non-interactive:
  `codex exec --sandbox workspace-write --skip-git-repo-check "<prompt>"`. Give it
  a brief on disk and tell it to read the brief; do not inline the job.
- **Zsh eats `"` inside `git commit -m`** when the message contains quoted phrases.
  Use `git commit -F -` with a heredoc. Zsh also fails on unmatched globs
  (`ls data/raga_v3*` → "no matches found") — quote or guard them.
- **Logs are gitignored** (`*.log`) but this series tracks them deliberately:
  `git add -f data/<dir>/*.log`.
- `data/raga_aliases.json`: **958 keys → 284 null** (was 274 before the 2026-08-13
  repair). **Never trust registry `ragas` metadata without it, and never trust it
  without `data/raga_aliases_audit.json`.**
- The composition registry contains junk rows — addresses and dates parsed as
  compositions.
- **Melodia runs ~13× realtime**; the domain cells took ~400 s each at 5 workers,
  6× faster than the single-threaded estimate.
- **The fused 2×2 at 54 classes is ~90 s per tier** on this machine — cheap. The
  matrix build is the slow part and it is cached
  (`data/raga_audit/tdms_cache.npz`, `data/raga_coverage/matrix.npz`).
- **Billing:** a 30-day no-billing window is in force. Submits are gated on
  `CARNATIFY_BILLING_OK=1`. **There is no GEMINI key locally.** archive.org is
  free; Colab Pro T4 has been used for GPU work (`colab_coverhunter.py`,
  `colab_duration_probe.py`).
- **Production deploys are Deepti-run** — the permission classifier blocks them
  from an agent seat. Never keep the Space mirror in `/tmp`.
- **Synth clips must never enter `~/sung_tests`.** That directory is the wild set
  and its purity is load-bearing for six measurements.

### The agent roster and how seats collaborate

- **Verifier seat** (Opus 5) — owns briefs, prereg discipline, and re-derivation of
  every headline. Does not take a workhorse at face value, or itself.
- **Workhorse seats** (Opus 5, GPT-5.6 / codex) — execute a brief on disk.
- Seats collaborate **only through files on disk and `AGENT_LOG.md`**, never
  through chat. A brief goes on disk; the agent is told to read the brief.
- Deepti also launches workhorses by hand in a separate terminal. **Assume
  concurrent repo work at all times.**
- Briefs must demand: prereg-before-score, partial results to disk after every
  cell, targeted `git add`, an `AGENT_LOG.md` entry naming refuted predictions, and
  an explicit list of paths the seat must not touch.

---

## 10. The one-line version, if you read nothing else

**The composition path is dead. The raga model was graduated on 2026-08-13 to 54
classes, fused, exported as `models/raga_v4_*` — 46.86 expected correct answers per
100 concert items against 39.12 for the tier the product would ship,
source-disjoint, from a retrain on data already on disk. The free lever is now
spent and the paid one is supply-constrained: more audio per class is worth
+18.4 pp with no saturation, but only 193 reachable tracks exist and the metadata
is exhausted. Deepti's directive is infrastructure before wiring, so the job is
§6 — one front end instead of eleven, one scoring entry point, and the test suite
that turned out to have been runnable all along. The two measurements waiting
behind it are the abstain gate, which is what actually buys safety, and the eleven
long-form concerts — frozen, multi-item, multi-raga, ~100-140 items, and blocked
only on her labels.**


---

# Embedded September evidence: historical chronological reports

The fresh completed-run summary at the beginning of this handoff takes precedence over older running-job notes in these reports. Contents below are preserved to expose both successes and mistakes, not to endorse all earlier conclusions.


---

# Appendix B: full execution history

Source snapshot: `OVERHAUL_EXECUTION.md`. Consult the live file for subsequent edits.

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


---

# Appendix C: September architecture audit

Source snapshot: `ARCHITECTURE_AUDIT_2026-09-08.md`. Consult the live file for subsequent edits.

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


---

# Appendix D: earlier exhaustive architecture audit

Source snapshot: `ARCHITECTURE_AUDIT_2026-09-07.md`. Consult the live file for subsequent edits.

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


---

# Appendix E: research notes

Source snapshot: `RESEARCH_NOTES_2026-09-08.md`. Consult the live file for subsequent edits.

# Research comparison and implementation decisions

Published scores are not interchangeable with live, unsegmented, open-set
concert accuracy. This repository's source/artist-disjoint development evidence,
the small AV test, and published recording-level benchmarks remain separate.

## Sequence learning

[DeepSRGM (2024)](https://arxiv.org/html/2402.10168v1) reports 88.1% on the
40-raga CompMusic task using an LSTM ensemble, annotated tonic normalization,
and whole-recording voting. Its described recording-held-out evaluation is not
the same as our artist-held-out/open-set task. It supports testing longer
temporal evidence, but does not establish that copying its network will deliver
that accuracy here. Its printed triplet-loss equation uses `min(..., 0)`;
implementation would need the usual nonnegative margin violation, not a blind
copy of that formula.

## Direction-conditioned pitch

[Sequential Pitch Distributions (2023)](https://aimc2023.pubpub.org/pub/j9v30p0j/release/1)
reports 88.13% on Carnatic reference-pitch data. We implemented an explicitly
different, bounded-excursion variant with silence boundaries and last-start
resetting, using the existing kernel classifier instead of its learned KNN
ensemble. The matched 382-track artist-disjoint experiment scored only 58.12%,
versus 86.39% for the current TDMS kernel. It is not promoted. This failure does
not refute the published method: interval enumeration and model combination
differ, and the evaluation is stricter.

## Unknown ragas

[Identification and Clustering of Unseen Ragas (ISMIR 2025)](https://ismir2025program.ismir.net/poster_256.html)
separates unknown-class detection from clustering. That distinction matters:
clustering unlabeled audio does not by itself assign correct named raga labels.
The abstract describes uncertainty-based rejection and contrastive learning;
we have not reproduced its method or claimed its performance for Carnatic audio.

## Current decision

Retain the measured kernel recognizer and independent-artist melody alignment.
Longer context and broader existing vocabulary have produced the clearest
development gains. Production acceptance and reliable long-concert item
boundaries remain unresolved; no research artifact has replaced deployed models.

## Neural pitch frontend

[RMVPE](https://arxiv.org/abs/2306.15412) explicitly targets vocal pitch in
polyphonic music. The original paper repository is
[Dream-High/RMVPE](https://github.com/Dream-High/RMVPE); the separate
[RVC publisher checkpoint](https://huggingface.co/lj1995/VoiceConversionWebUI)
has an MIT model-card declaration. The bounded ONNX experiment follows a pinned
RVC preprocessing/decoder contract, with its source license retained in
THIRD_PARTY_RMVPE.md. Its synthetic tone test is not evidence of Carnatic
melody accuracy, and the RVC checkpoint is not claimed as the paper's exact
training/evaluation reproduction.

## Composed reference passages

The section-aware song diagnostic treats muktayi/mukthayi swaras as composed
material, separate from kalpana swaras. The Music Academy's
[1987 journal, “Swara Decorations in Karnatic Music”](https://musicacademymadras.in/catalogue/files/journals/Vol.58_1987.pdf)
discusses attributed composed swara additions, including a muktayi swaram.
Existing section annotations—not inferred song boundaries—select this optional
reference arm. Unannotated recordings retain full-reference fallback, and
removed passages never shrink the answerable-query denominator.

## Recording-to-work metadata

The [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) exposes
recording `work-rels` and requires an identifying User-Agent and no more than
one request per second. The new CompMusic resolver spaces requests by at least
3 seconds, locks against concurrent local instances, and caps response size.
It does not search by title. A recording with multiple performed works is
quarantined rather than forced into a single composition identity. Initial
public requests returned HTTP 503; subsequent intermittent recovery enabled
the separately evaluated partial catalogs documented in OVERHAUL_EXECUTION.md.
Explicit generic improvisation work entities are excluded from song references.
The fixed 477-recording lookup has now completed; full-catalog evaluation is
documented alongside the preserved partial checkpoints.

## Foundation representation screening

The official [MERT-v1-95M](https://huggingface.co/m-a-p/MERT-v1-95M) and
[MERT-v0-public](https://huggingface.co/m-a-p/MERT-v0-public) model cards both
declare CC-BY-NC-4.0. Neither is silently admitted to the production path.
The official [MusicFM repository](https://github.com/minzwon/musicfm) releases
an FMA-trained checkpoint, and its linked
[model card](https://huggingface.co/minzwon/MusicFM/blob/main/README.md) declares
MIT. Its authors explicitly caution that frozen representations do not
inherently learn musical keys. It remains an untested possible representation
baseline, not an established solution to Carnatic raga grammar; no MusicFM
weights have been downloaded or executed in this session.

## Matched Demucs frontend diagnostic

The [publisher repository](https://github.com/facebookresearch/demucs) identifies
`htdemucs` as the single, non-fine-tuned Hybrid Transformer checkpoint and
documents split CPU inference. Its reported source-separation benchmarks are
not Carnatic raga evaluations. The local diagnostic authenticates the existing
checkpoint, follows publisher waveform normalization/restoration, fixes random
shifts to zero, and keeps the original mixed-audio tonic unchanged. Installed
version, hash, settings and license notice are recorded in THIRD_PARTY_DEMUCS.md.
Any result applies to this matched diagnostic, not the publisher's benchmark.
# MusicFM implementation feasibility follow-up (2026-09-09)

Official sources rechecked: https://github.com/minzwon/musicfm,
https://huggingface.co/minzwon/MusicFM/tree/main, and
https://raw.githubusercontent.com/minzwon/musicfm/master/model/musicfm_25hz.py.
The hosted FMA and MSD checkpoints are each approximately 1.32 GB, with MIT
license metadata. The implementation uses a 12-layer, width-1024 Conformer
and 24 kHz audio. Its constructor fetches a separate pretrained Conformer
configuration and uses an unrestricted `torch.load`; a local pilot must pin
all artifacts and use restricted checkpoint loading, not execute that loader
unchanged. The README pooling example averages the last axis despite its
batch/time/channel comment; actual returned tensor shape must be verified
before pooling. A subsequent pinned MusicFM-MSD pilot now produces finite
250x1024 frame embeddings on one ten-second source-hashed excerpt; a repeat
produces a byte-identical file. See `THIRD_PARTY_MUSICFM.md` and
`OVERHAUL_EXECUTION.md` for pins, compatibility migration and timings. This is
not evidence of Carnatic accuracy or a selected production architecture.


---

# Appendix F: exact working-tree inventory at handoff

This is not an ownership declaration. Preserve pre-existing/user edits. Modified and untracked code has not been consolidated into a clean release commit.

```text
 M .claude/settings.local.json
 M .gitignore
 M HANDOFF.md
 M README.md
 M backend/build_space.sh
 M backend/clip_identify.py
 M backend/main.py
 M data/long_concerts/LABELS.tsv
 M identify_clip.py
 M normalize_ragas.py
 M scripts/long_concert_labels.py
 M src/carnatify/audio/feature_extractor.py
 M src/carnatify/audio/utils.py
 M src/carnatify/ml/raga_dataset.py
 M src/carnatify/ml/raga_features.py
 M src/carnatify/ml/raga_model.py
 M src/carnatify/ml/raga_trainer.py
 M src/carnatify/ui/app.py
 M tests/test_audio.py
 M tests/test_lyrics.py
?? ARCHITECTURE_AUDIT_2026-09-07.md
?? ARCHITECTURE_AUDIT_2026-09-08.md
?? OVERHAUL_EXECUTION.md
?? PROJECT_HISTORY.md
?? RESEARCH_NOTES_2026-09-08.md
?? THIRD_PARTY_CHROMAPRINT.md
?? THIRD_PARTY_DEMUCS.md
?? THIRD_PARTY_MUSICFM.md
?? THIRD_PARTY_RMVPE.md
?? configs/
?? constraints-overhaul.txt
?? data/architecture_audit/
?? data/long_concerts/labels_validation.json
?? data/overhaul/
?? data/raga_coverage/matrix.npz
?? registry_hygiene.py
?? scripts/architecture_inventory.py
?? scripts/audit_archive_audio_identity.py
?? scripts/audit_concert_silence.py
?? scripts/audit_dhenuka_coverage_pilot.py
?? scripts/audit_file_raga_evidence.py
?? scripts/audit_recording_fingerprint_overlap.py
?? scripts/audit_strict_audio_decode.py
?? scripts/audit_training_taxonomy.py
?? scripts/benchmark_activity_boundaries.py
?? scripts/benchmark_concert_transitions.py
?? scripts/benchmark_melody_retrieval.py
?? scripts/benchmark_musicfm.py
?? scripts/benchmark_musicfm_raga.py
?? scripts/benchmark_pitch_activity.py
?? scripts/benchmark_pitch_sequence.py
?? scripts/benchmark_recording_fingerprint.py
?? scripts/benchmark_sequential_pitch.py
?? scripts/benchmark_sung_asr.py
?? scripts/benchmark_tonic_marginalization.py
?? scripts/build_annotated_corpus.py
?? scripts/build_compmusic_compositions.py
?? scripts/build_composition_catalog.py
?? scripts/build_evaluation_audio_identity.py
?? scripts/build_vocabulary_cascade.py
?? scripts/calibrate_activity.py
?? scripts/calibrate_composition_rejection.py
?? scripts/calibrate_development_risk.py
?? scripts/carnatify_pipeline.py
?? scripts/compare_musicfm_gradients.py
?? scripts/concert_pipeline.py
?? scripts/diagnose_pitch_transfer.py
?? scripts/diagnose_training_audio_context.py
?? scripts/evaluate_activity.py
?? scripts/evaluate_annotated_raga.py
?? scripts/evaluate_cached_field.py
?? scripts/evaluate_labeled_intervals.py
?? scripts/evaluate_saraga_av.py
?? scripts/evaluate_sung_asr_titles.py
?? scripts/extract_context_training.py
?? scripts/extract_recording_fingerprints.py
?? scripts/fetch_audio_event_model.py
?? scripts/fetch_chromaprint_source.py
?? scripts/fetch_compmusic_work_links.py
?? scripts/fetch_dhenuka_coverage_pilot.py
?? scripts/fetch_musicfm_pilot.py
?? scripts/fetch_rmvpe_model.py
?? scripts/fetch_saraga_av_metadata.py
?? scripts/fetch_saraga_av_selection.py
?? scripts/filter_strict_decode_features.py
?? scripts/finetune_musicfm_pilot.py
?? scripts/finish_context_experiment.py
?? scripts/guard_archive_evaluation_artists.py
?? scripts/index_saraga_av_audio.py
?? scripts/long_concert_score.py
?? scripts/merge_context_decode_recovery.py
?? scripts/merge_raga_training.py
?? scripts/plan_saraga_av_evaluation.py
?? scripts/prepare_compmusic_features.py
?? scripts/probe_musicfm_gradients.py
?? scripts/quarantine_audio_overlap.py
?? scripts/raga_kernel_benchmark.py
?? scripts/raga_pipeline.py
?? scripts/recover_context_decode_windows.py
?? scripts/refine_concert_activity.py
?? scripts/refresh_archive_identity_metadata.py
?? scripts/regroup_file_artists.py
?? scripts/remote_zip.py
?? scripts/saraga_av_matching.py
?? scripts/saraga_recording_identity.py
?? scripts/score_activity_intervals.py
?? scripts/summarize_overhaul.py
?? scripts/summarize_single_raga_evaluation.py
?? scripts/train_admitted_raga.py
?? scripts/train_audio_domain_raga.py
?? scripts/train_matched_forest.py
?? scripts/train_multiscale_raga.py
?? scripts/train_raga_svc.py
?? scripts/train_tonic_disambiguator.py
?? scripts/tune_raga_kernel.py
?? scripts/verify_recording_overlap.py
?? src/carnatify/audio/cache_io.py
?? src/carnatify/audio/demucs_frontend.py
?? src/carnatify/audio/events.py
?? src/carnatify/audio/ffmpeg_window.py
?? src/carnatify/audio/melody_frontend.py
?? src/carnatify/audio/musicfm_frontend.py
?? src/carnatify/audio/pitch_activity.py
?? src/carnatify/audio/pitch_profiles.py
?? src/carnatify/audio/recording_fingerprint.py
?? src/carnatify/audio/rmvpe_frontend.py
?? src/carnatify/audio/sections.py
?? src/carnatify/audio/sung_asr.py
?? src/carnatify/audio/tonic_evidence.py
?? src/carnatify/ml/calibration.py
?? src/carnatify/ml/composition_catalog.py
?? src/carnatify/ml/concert_segments.py
?? src/carnatify/ml/distribution_classifier.py
?? src/carnatify/ml/evaluation_integrity.py
?? src/carnatify/ml/fused_forest.py
?? src/carnatify/ml/inference_runtime.py
?? src/carnatify/ml/melody_features.py
?? src/carnatify/ml/melody_retrieval.py
?? src/carnatify/ml/pitch_sequence.py
?? src/carnatify/ml/retrieval_prior.py
?? src/carnatify/ml/sequential_pitch.py
?? src/carnatify/ml/vocabulary_cascade.py
?? tests/test_activity_boundary_planning.py
?? tests/test_activity_calibration.py
?? tests/test_activity_interval_scoring.py
?? tests/test_activity_sections.py
?? tests/test_archive_artist_guard.py
?? tests/test_archive_audio_identity.py
?? tests/test_archive_composition_identity.py
?? tests/test_artist_provenance.py
?? tests/test_audio_cache_io.py
?? tests/test_audio_overlap_quarantine.py
?? tests/test_av_download_integrity.py
?? tests/test_av_offline_resume.py
?? tests/test_backend_audio_http.py
?? tests/test_backend_tonic_policy.py
?? tests/test_clip_tonic_policy.py
?? tests/test_compmusic_work_links.py
?? tests/test_composed_references.py
?? tests/test_composition_catalog.py
?? tests/test_composition_frontend.py
?? tests/test_composition_rejection.py
?? tests/test_concert_event_cache.py
?? tests/test_concert_segments.py
?? tests/test_concert_transition_scoring.py
?? tests/test_context_decode_recovery.py
?? tests/test_context_experiment_runner.py
?? tests/test_context_recovery_merge.py
?? tests/test_context_training.py
?? tests/test_coverage_download_integrity.py
?? tests/test_decode_feature_filter.py
?? tests/test_demucs_frontend.py
?? tests/test_development_risk.py
?? tests/test_directional_retrieval.py
?? tests/test_distribution_classifier.py
?? tests/test_evaluation_audio_identity.py
?? tests/test_evaluation_integrity.py
?? tests/test_ffmpeg_window.py
?? tests/test_file_artist_grouping.py
?? tests/test_file_raga_evidence.py
?? tests/test_fingerprint_overlap.py
?? tests/test_inference_runtime.py
?? tests/test_labeled_interval_queries.py
?? tests/test_melody_frontend.py
?? tests/test_melody_integrity.py
?? tests/test_melody_retrieval.py
?? tests/test_metadata_raga.py
?? tests/test_musicfm_finetune_pilot.py
?? tests/test_musicfm_frontend.py
?? tests/test_musicfm_gradient_control.py
?? tests/test_musicfm_raga_probe.py
?? tests/test_patch_retrieval.py
?? tests/test_pipeline_commands.py
?? tests/test_pitch_activity.py
?? tests/test_pitch_profiles.py
?? tests/test_pitch_sequence.py
?? tests/test_preparation_integrity.py
?? tests/test_recording_fingerprint.py
?? tests/test_recording_identity.py
?? tests/test_registry_hygiene.py
?? tests/test_remote_zip.py
?? tests/test_retrieval_evaluation.py
?? tests/test_retrieval_prior.py
?? tests/test_retrieval_query_window.py
?? tests/test_rmvpe_frontend.py
?? tests/test_saraga_av_matching.py
?? tests/test_sequential_pitch.py
?? tests/test_single_raga_summary.py
?? tests/test_strict_decode_audit.py
?? tests/test_strict_raga_normalization.py
?? tests/test_sung_asr.py
?? tests/test_sung_asr_titles.py
?? tests/test_tonic_evidence.py
?? tests/test_tonic_fallback_contract.py
?? tests/test_tonic_marginalization.py
?? tests/test_training_context_diagnostic.py
?? tests/test_upload_audio.py
?? tests/test_verified_composition_extension.py
?? tests/test_vocabulary_cascade.py
```
