# scripts/ index

135 scripts accumulated over three months of agent relays. Nothing here is
deleted; every one is a receipt for a number somewhere in the handoffs. This
index says which ones are the **current path**, which are **measurement
harnesses** you rerun to reproduce a number, and which are **archive** (a
finished experiment; run only to reproduce its recorded result). New scoring
code goes through `src/carnatify/ml/raga_runtime.py`, not a new script.

## Current path (2026-09-10)

| script | what |
|---|---|
| `carnatify_pipeline.py` | Five-stage candidate pipeline: data-prep, feature-extract, train, evaluate, infer |
| `raga_pipeline.py` | Preparation, grouped folds, feature extraction used by the pipeline |
| `raga_kernel_benchmark.py` | Grouped kernel benchmark on fixed folds; writes per-track OOF records |
| `train_raga_svc.py` | Fit the kernel-ridge candidate bundle with OOF calibration metadata |
| `extract_context_training.py` | Matched 180 s training extraction with the inference query contract |
| `recover_context_decode_windows.py`, `merge_context_decode_recovery.py`, `finish_context_experiment.py` | Decoder recovery, merge, and the non-LLM experiment supervisor |
| `candidate_verdict.py` | Paired cluster-bootstrap verdict between two candidates (`CANDIDATE_VERDICT_PREREG.md`) |
| `abstain_gate.py` | Leave-class-bin-out gate selection and one-shot dev evaluation (`ABSTAIN_GATE_PREREG.md`) |
| `evaluate_annotated_raga.py` | 184-query Saraga development evaluation through `raga_runtime` |
| `evaluate_labeled_intervals.py` | Oracle-boundary field diagnostic on Deepti's labelled items through `raga_runtime` |
| `concert_pipeline.py` | Bounded whole-concert inference: activity, raga evidence, unverified segments |
| `long_concert_freeze.py`, `long_concert_labels.py`, `long_concert_score.py` | Frozen-hash check, label template/validator, interval scorer for the 11 concerts |
| `summarize_overhaul.py` | `paired_interval`: the cluster bootstrap every paired number uses |

## Integrity audits (rerun when data changes)

`audit_archive_audio_identity.py`, `refresh_archive_identity_metadata.py`,
`audit_file_raga_evidence.py`, `audit_strict_audio_decode.py`,
`filter_strict_decode_features.py`, `extract_recording_fingerprints.py`,
`audit_recording_fingerprint_overlap.py`, `verify_recording_overlap.py`,
`quarantine_audio_overlap.py`, `guard_archive_evaluation_artists.py`,
`regroup_file_artists.py`, `build_evaluation_audio_identity.py`,
`saraga_recording_identity.py`, `audit_training_taxonomy.py`,
`architecture_inventory.py`, `summarize_single_raga_evaluation.py`.

## Measurement harnesses, August series (committed records under `data/raga_*`)

`raga_audit_*.py` (the 72.8% contamination audit), `raga_coverage_*.py`
(coverage/accuracy trade, within-class curve, admission pricing),
`raga_duration_*.py` (duration curve), `raga_domain_*.py` (domain
decomposition), `raga_wild_*.py` (27-clip wild set), `raga_tier_*.py` (tier
graduation to `raga_v4`), `raga_fetch_recount.py`.

## Archive: negative or superseded experiments (do not re-fund without new evidence)

- Composition: `benchmark_melody_retrieval.py`, `build_compmusic_compositions.py`,
  `build_composition_catalog.py`, `fetch_compmusic_work_links.py`,
  `calibrate_composition_rejection.py`, `benchmark_pitch_sequence.py`,
  `benchmark_sequential_pitch.py`, `qmax_*.py`, `duration_probe_*.py`,
  `build_negative_*.py`, `parse_negative_labels.py`, `stamp_negative_shas.py`,
  `m1_diagnostic.py`, `cross_channel_agreement.py`, `precision_coverage_curve.py`,
  `score_external_transcripts.py`, `detect_workfamily_dupes.py`, `registry_junk_*.py`.
- ASR: `build_asr_cache_*.py`, `merge_asr_cache_v2.py`, `build_saraga_*.py`,
  `clean_saraga_trainset.py`, `benchmark_sung_asr.py`, `evaluate_sung_asr_titles.py`,
  `build_probe_colab_bundle.py`.
- Frontends: `benchmark_musicfm*.py`, `finetune_musicfm_pilot.py`,
  `probe_musicfm_gradients.py`, `compare_musicfm_gradients.py`, `fetch_musicfm_pilot.py`,
  `fetch_rmvpe_model.py`, `fetch_chromaprint_source.py`, `benchmark_recording_fingerprint.py`.
- Raga model ablations: `train_matched_forest.py`, `train_multiscale_raga.py`,
  `train_audio_domain_raga.py`, `train_tonic_disambiguator.py`, `tune_raga_kernel.py`,
  `train_admitted_raga.py`, `merge_raga_training.py`, `prepare_compmusic_features.py`,
  `build_annotated_corpus.py`, `build_vocabulary_cascade.py`,
  `benchmark_tonic_marginalization.py`, `calibrate_development_risk.py`,
  `diagnose_pitch_transfer.py`, `diagnose_training_audio_context.py`,
  `evaluate_cached_field.py`.
- Saraga AV cohorts (inspected, no longer fresh): `fetch_saraga_av_*.py`,
  `index_saraga_av_audio.py`, `plan_saraga_av_evaluation.py`,
  `saraga_av_matching.py`, `evaluate_saraga_av.py`, `remote_zip.py`.
- Concert activity/segmentation (optional, off by default): `benchmark_activity_boundaries.py`,
  `benchmark_concert_transitions.py`, `benchmark_pitch_activity.py`, `calibrate_activity.py`,
  `evaluate_activity.py`, `refine_concert_activity.py`, `score_activity_intervals.py`,
  `audit_concert_silence.py`, `fetch_audio_event_model.py`.
- Coverage lead: `fetch_dhenuka_coverage_pilot.py`, `audit_dhenuka_coverage_pilot.py`.
