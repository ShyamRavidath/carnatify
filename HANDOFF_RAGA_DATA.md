# HANDOFF: Raga classifier — scrape to 70%+ held-out accuracy

Written 2026-07-07. Audience: agent taking over the data-collection + retrain effort.
(The older `HANDOFF.md` covers the whole MVP; this file is only the raga-accuracy workstream and supersedes anything it says about raga retraining.)

## 1. Goal

Raga classification at **≥70% held-out, track-level top-1 accuracy** at useful raga
coverage (target: all ragas with enough data — not a cherry-picked handful).
"Held-out" means grouped by `track_id` (StratifiedGroupKFold or a track-grouped
split): no slice of a recording may appear on both sides. Slice-level or
ungrouped CV numbers are inflated and don't count.

Secondary/interim target already in reach: ≥70% top-3 (see table below).

Constraints: free-of-cost only. Colab Pro is available for GPU work (Demucs).
CompMusic/Dunya audio is **dead** — multiple emails to mtg-info@upf.edu unanswered.

## 2. Why data, not modeling (evidence)

Accuracy is a near-linear function of tracks-per-raga. Measured 2026-07-07 with
the production feature pipeline, `evaluate_raga_thresholds.py` (grouped 5-fold,
track-level aggregation of slice probabilities):

| min tracks/raga | ragas | tracks | coverage | top-1 | top-3 |
|---|---|---|---|---|---|
| ≥5  | 52 | 507 | 85% | 36.9% | 59.2% |
| ≥8  | 33 | 396 | 66% | 43.2% | 67.7% |
| ≥10 | 18 | 271 | 45% | 49.1% | 76.8% |
| ≥15 | 7  | 142 | 24% | 64.8% | 88.7% |
| ≥20 | 3  | 75  | 13% | 73.3% | 100%  |

Read: 70% top-1 appears around **~20 tracks/raga**. Current corpus: 597 tracks,
88 raga labels, median ~5 tracks/raga. To get 70% top-1 over ~30 ragas we need
roughly **20+ tracks for each of those 30 ragas** — i.e. approximately double to
triple the corpus, concentrated on the thin ragas (per-raga counts in §6).

## 3. Current state of the code

**Production model (deployed):** RandomForest on tonic-normalized pitch-histogram
features from Demucs-separated vocals + pyin. Live numbers: 40.5% top-1 / 60.8%
top-3 (53 ragas, ≥5 tracks). Artifacts: `models/raga_classifier.pkl` +
`models/raga_label_encoder.pkl`.

**Feature pipeline:** `raga_v2_pipeline.py` (Demucs + pyin + tonic-normalized
histograms). Feature caches: `data/raga_v2_cache/saraga_v3/*.npz` and
`data/raga_v2_cache/archive_v3/*.npz` — one npz per track with `X` (slice
features), `raga`, `track_id`, `tonics` (tonic[0] = per-track tonic; saraga =
annotated, archive = essentia `TonicIndianArtMusic`). The unsuffixed `saraga/`
and `archive/` dirs are stale v1 caches (broken median-F0 tonics) — ignore.

**Scraper stack (the tools you'll extend):**
- `scrape_concerts.py` — shankarkrish.blog/carnatic-vocal/ concert metadata
- `download_concerts.py`, `download_archive_direct.py` — audio from archive.org/S3
- `colab_extract_features.ipynb` — GPU feature extraction (Demucs+pyin) on Colab
- Known: the old "5% accuracy" scraper result was a capped download, not a data
  ceiling — the blog/archive.org has far more than we ever pulled.

**Evaluation:** `evaluate_raga_thresholds.py` (the sweep above; rerun after every
data batch), `train_raga_v2_evaluate.py` (full CV + candidate model export; does
NOT overwrite the production pkl — shipping is a separate explicit step).

**Dead ends kept for the record:** `colab_train_cnn.ipynb`,
`build_cnn_extra_audio.py`, `data/cnn_extra_audio/` (see §5).

## 4. Files actively being edited

Nothing is mid-edit; the branch is clean and pushed (main). Last touched:
- `colab_train_cnn.ipynb` — final state = sanity cell + light-reg training; closed, do not resume
- `evaluate_raga_thresholds.py` — new, committed with this handoff
- Untracked local data (not in git, fine to leave): `data/cnn_extra_audio/`,
  `carnatic_varnam_1.1/`, `carnatic_varnam_1.1.zip`

## 5. What failed (do not retry these)

1. **CNN on tonic-rolled log-CQT of Demucs vocals** (2026-07-06/07, two runs on
   Colab GPU). Heavy regularization: chance-level. Light regularization
   (`p_conv=0.1, p_fc=0.3`, mild SpecAugment): train_slice_acc crawled to 13%,
   **val_slice_acc pinned at exact chance (2.2%) for 60 epochs**, best val track
   top-1 4.7% vs 1.9% chance. Sanity overfit check passed (94% memorizing 512
   unaugmented slices, zero dropout) — so pipeline, labels, tonics all verified
   clean. Diagnosis: pure per-recording memorization, zero cross-track transfer.
   ~29 min audio/raga cannot train a from-scratch CNN on 53 classes. More
   segments from the *same* tracks won't fix it — the wall is tracks, not minutes.
2. **Tala detection** — closed earlier at 16.5% measured (majority baseline 72%);
   documented in `HANDOFF.md` §2.2. Not part of this workstream.
3. **CompMusic audio request (H1)** — multiple emails, no response. Dead.
4. Old scraper run stopping at ~5 tracks/raga — that was a download cap, not
   exhaustion of the source.

## 6. Next step (what I would do, in order)

1. **Free win first — merge duplicate raga labels.** The cache has diacritic
   dupes, e.g. `Ābhōgī` (6 tracks) + `Ābhōgi` (2 tracks) are one raga. Fold
   labels (NFD-strip + lowercase, see `normalize_ragas.py`) at cache-load time in
   `train_raga_v2_evaluate.py` / `evaluate_raga_thresholds.py`, re-run sweep.
   Audit the full label list for other spelling splits (Karaharapriya vs
   Kharaharapriya etc.).
2. **Targeted scrape.** Current per-raga track counts (post-merge, recheck):
   28 Kalyāṇi, 27 Tōḍi, 20 Śankarābharaṇaṁ, 19 Kāṁbhōji, 17 Kamās, 16 Mōhanaṁ,
   15 Sindhubhairavi, then a long tail — 13 ragas at 10-13 tracks, ~35 ragas at
   5-9, rest under 5. Target: **every raga currently at 5-19 tracks up to 20+**.
   Sources, in order of yield: (a) rerun shankarkrish scraper WITHOUT the
   download cap — enumerate everything first, dedupe against existing
   `track_id`s, prioritize thin ragas; (b) archive.org direct search for
   Carnatic concerts beyond that blog (search by raga name + kriti names —
   `data/lyrics.db` has kriti↔raga mappings to generate queries); (c) Saraga
   Melody Synth / other MTG open datasets on Zenodo (no email needed).
   Raga labels must come from metadata/tracklists, not audio.
3. **Feature extraction.** Push new audio through `colab_extract_features.ipynb`
   (Demucs+pyin on Colab GPU; resumable). Output npz into
   `data/raga_v2_cache/archive_v3/` in the existing format (essentia tonic!).
4. **Retrain + measure.** `evaluate_raga_thresholds.py` after each batch — the
   ≥10 and ≥15 rows tell you whether the curve is bending toward 70%. Then
   `train_raga_v2_evaluate.py` to export a candidate model. Do not overwrite
   `models/raga_classifier.pkl` without Deepti's sign-off.
5. **If the curve flattens below 70%** with ~20 tracks/raga: the cheap remaining
   levers are feature-level (pitch-transition bigrams/gamaka stats appended to
   the histogram — RF handles wide features fine), or ship top-3 mode (already
   76.8% at ≥10 tracks) while data keeps accruing. Escalate to Deepti before any
   new deep-learning attempt.

## 7. Gotchas

- **Always grouped CV.** Ungrouped splits leak slices of the same recording and
  produce fantasy numbers. This killed interpretation of early results once.
- Exclude `Rāgamālika` (it's a form — multiple ragas per piece — not a raga).
- Tonic quality gates everything: annotated for Saraga, essentia
  `TonicIndianArtMusic` for scraped audio. Never median-F0 (that was the v1 bug).
- Filenames/labels carry Unicode diacritics — compare folded, store original.
- Demucs must run before pyin — raw concert mix pollutes pitch histograms with
  violin/mridangam.
- archive.org rate limits: batch downloads politely, resume support exists in
  `download_archive_direct.py`.
