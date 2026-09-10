# Architecture audit artifacts — 2026-09-07

Read [the full report](../../ARCHITECTURE_AUDIT_2026-09-07.md). This run is a
development audit, not a production release or a state-of-the-art claim.

## Reproduce

From the repository root:

```sh
venv_train/bin/python scripts/architecture_inventory.py
venv_train/bin/python scripts/raga_pipeline.py data-prep
venv_train/bin/python scripts/raga_pipeline.py feature-extract
venv/bin/python scripts/raga_pipeline.py evaluate --trees 64
venv_train/bin/python scripts/raga_pipeline.py train --trees 64
venv_train/bin/python scripts/raga_pipeline.py infer data/long_concerts/audio/long_concert_1.mp3 --start 2 --duration 60 --output data/architecture_audit/smoke_c1_1.json
venv_train/bin/python -m pytest tests/ -q
```

Use `--run /path/to/new/run` before the stage name to isolate a new experiment.
The stages write only their run directory. Existing `models/` artifacts and
historical audit caches are not rewritten. Training is archive-only in this
adapter. The feature extractor is shared by candidate training and inference;
the original waveform extraction is inherited from the existing Melodia cache.

`evaluate` compares three arms on identical folds and writes partial results
after each arm. `summarize` recomputes source-cluster confidence intervals without
fitting models. Seeds, groups, file hashes and row-level predictions are retained.
The accuracy intervals do not account for historical tuning of the source corpus.

## Continue labeling

Continue recording **raga, start, end, confidence, and explicit exclusions**.
Song names are useful metadata. Formatting with tabs or at least two spaces
between fields now works in the existing validator. Do not use model guesses as
ground truth. Alapana should be labeled by its own raga when known; do not attach
it to the previous song just because the next song has not started.

The original `data/long_concerts/LABELS.tsv` was preserved byte-for-byte. Its
eight completed items have a reviewed structural copy in `label_intervals.json`:

- Six items have explicit usable boundaries and high confidence.
- The first item's two intervals surround the stated 12:35–24:00 tani exclusion.
- The Hamir Kalyani row is diagnostic only: approximate end and muted tail.
- The Kalanidhi row is diagnostic only: confidence was not supplied.
- Everything after 42:33 in concert 3 remains unlabeled.
- Dhenuka remains outside this candidate's vocabulary; it is counted in coverage
  and all-item accuracy, not silently discarded or mapped to a different raga.

`long_concert_labels.py --validate` checks input syntax and vocabulary only; it
does **not** certify boundaries for scoring. `long_concert_score.py` uses the
explicit manifest and rejects changed source hashes, duplicate predictions,
overlapping exclusions, or mismatched model/audio hashes. When the original
labels change, review and refresh the interval copy and its source hash together.

The six `smoke_*.json` files analyze only the first 60 seconds of each primary
item. They are intentionally a small integration check. To rescore them:

```sh
venv_train/bin/python scripts/long_concert_score.py --predictions data/architecture_audit/smoke_c1_1.json data/architecture_audit/smoke_c2_1.json data/architecture_audit/smoke_c2_2.json data/architecture_audit/smoke_c2_3.json data/architecture_audit/smoke_c3_1.json data/architecture_audit/smoke_c3_2.json
```

For longer recordings, `infer` uses bounded, consecutive 60-second decoding.
These are analysis windows, not detected songs. The scorer admits only windows
fully inside a labeled interval; extracting from supplied boundaries is an
**oracle-boundary** task, not an automatic segmentation benchmark. It reports
missing items and failed extractions separately. Forest scores are uncalibrated;
only inadequate audio causes automatic abstention at present.

## Files

`inventory.json`: AST imports/calls/definitions and exact duplicate files.
`manifest.json`: development corpus, source groups and contour hashes.
`features.npz`: corrected and legacy paired feature matrices (regenerable).
`extraction.json`: rejected windows and feature version.
`benchmark.json`: 5-fold source-disjoint per-track predictions and confidence intervals.
`candidate.joblib`: unpromoted 51-class forest (regenerable).
`label_intervals.json`: held-out human labels; never a training input.
`smoke_*.json`, `long_concert_score.json`: six-item pipeline check.
