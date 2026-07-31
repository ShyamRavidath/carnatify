# Workhorse brief — audit the 72.8% / 84.7% raga number for same-source contamination

Date: 2026-07-30. For the **Opus 5 workhorse**. Read-only measurement, no GPU,
no production model overwritten. Nothing to commit until the verifier has read
the result.

Written by the verifier seat immediately after accepting
`data/QMAX_CONTAMINATION_AUDIT.md`. Read that file first — this brief is its
sequel and reuses its artifacts.

## Why this is the next thing

`HANDOFF_CLIP_ID.md:43` records **"Raga from full track: 72.8% top-1 / 84.7%
top-3 (18 ragas, ≥25 tracks/raga tier)"**, described everywhere in the repo as
"grouped CV, leak-free". With Qmax external now measured at 60.0% → 9.5%, this
is **the last surviving positive result in the repository**, and the raga-first
reading of the concert-companion product rests entirely on it.

It has never been audited, and three facts found while writing this brief say it
must be, before anything is built on top of it:

1. **It drinks from the same cache the Qmax audit just found poisoned.**
   `train_raga_v3_tdms.py:102` loads archive features from
   `MEL_DIR / f'{p.stem}.npy'` — that is `data/raga_v2_cache/melodia_full/`,
   the exact directory whose contours the audit hashed. Independently
   re-verified for this brief: 1,232 files, 72 identical groups, 182 tracks,
   **110 redundant byte-identical copies**.

2. **The grouping key is the filename, not a recording identity.** The CV
   groups on `track_ids`, and `tid = str(d['track_id'])` is one value per npz
   file. `X`, `X_r2`, `X_r3` are one recording stored three times under three
   track_ids, so `StratifiedGroupKFold` puts the same recording on both sides of
   the split. **97 redundant byte-identical copies are inside the raga
   trainset**, joined by stem against `data/qmax_audit/provenance.json` (1,168
   of 1,170 archive_v3 npz join; 2 have no melodia file).

3. **The suspected bigger leak is not the byte-copies.** The archive corpus was
   assembled by downloading concert uploads into raga directories, so one upload
   commonly contributes an alapana *and* the kriti in the same raga —
   `archive__Amṛtavarṣiṇi__Alapana` and `archive__Amṛtavarṣiṇi__AnandAmrutakarshiNi`
   are two files, two track_ids, one performance, one singer, one tonic, one
   recording chain. Measured for this brief: the trainset spans **283 archive
   items, 210 of which contribute more than one track, and 251 of 1,168 tracks
   (21.5%) sit in a same-raga cluster inside a single item.** Track-level
   grouping splits every one of those clusters across folds. That is **2.6× the
   byte-copy exposure**, and for a raga classifier it is the more dangerous of
   the two, because timbre, tonic and room are constant within a cluster.

So the question is narrow and answerable: **how much of 72.8% / 84.7% survives
when no fold can test a track against another track off its own recording, its
own concert upload, or its own artist?**

## The reproduction gate — do this first, and stop if it fails

**The CV harness that produced 72.8 / 84.7 was never committed.**
`train_raga_v3_tdms.py` only fits and exports; the number survives as a
docstring note and a `cv_note` string dated 2026-07-08.
`git log --all -S"72.8" -- '*.py'` returns only the commit that added the note.
This is the `comp_pitch_cache` failure mode again.

The difference, and the reason this audit is worth running at all, is that the
**features are fully reproducible**: `melodia_full/` is on disk, `tdms_multi()`
is committed, and the 480-dim histogram rows are in `archive_v3/*.npz` and
`saraga_v3/*.npz`. So the harness can be rebuilt exactly from the committed
constants — `TAUS`, `NB`, `sigma 1.0`, `alpha 0.75`, `FUSION_W_HIST = 0.4`,
`RandomForestClassifier(n_estimators=800, max_features='sqrt', random_state=42)`,
`min_tracks = 25`, `StratifiedGroupKFold(n_splits=5, shuffle=True,
random_state=42)`, `Rāgamālika` dropped.

**Gate: level (a) must land within ±2pp of 72.8 top-1 and 84.7 top-3 on 18
ragas.** If it does not, stop, report the reconstruction as a declared
reconstruction the way the internal Qmax arm was, and state plainly that the
number is unreproducible from this repository. Do not proceed to score levels
(b) and (c) against a baseline that does not reproduce — a delta measured off a
wrong baseline is worse than no delta.

## The three levels

One feature matrix, built once. The levels differ **only** in the `groups`
vector handed to `StratifiedGroupKFold`. Nothing else changes — not the tier,
not the fusion weight, not the RF, not the seed.

- **(a) as-originally-run.** `groups = track_id`. Reproduces the historical
  number and confirms the harness.
- **(b) recording-disjoint.** `groups = contour_sha1` for archive tracks
  (`data/qmax_audit/provenance.json`), collapsing byte-identical copies into one
  group. Saraga tracks keep their track_id at this level. Justification is
  already established in the Qmax prereg: a near-duplicate sweep over all 128
  positive pairs found zero pairs near-identical without being byte-identical,
  so the exact test is the complete test on this corpus.
- **(c) source-disjoint.** `groups = archive_identifier` for archive tracks;
  for Saraga, `groups = concert folder` (the Qmax audit established Saraga 1.5
  Carnatic has clean per-track concert and album-artist metadata across 27
  concert folders). Where artist is recoverable and shared across items, merge
  those items into one group. This is the level that matters.

Registered sensitivity, **non-gating**, declared now so it cannot be introduced
later as the reading that rescues a result: **(c′) identifier-family disjoint**,
merging two identifiers when their folded forms score
`rapidfuzz.fuzz.ratio >= 85` — the `78RPM-Chittor-V-Nagaiah` /
`78RPM-ChittoorVNagaiah` case. If (c) and (c′) disagree materially, report both
and treat the lower as honest.

## Registered readings

1. **The tier is frozen at `min_tracks >= 25` on the level-(a) track counts.**
   Coarser grouping will drop some ragas below 25 groups. **Do not re-tune
   `min_tracks` to keep 18 ragas alive** — that is the single most available way
   to launder this number, and it is forbidden. Report how many ragas and how
   many groups survive at each level; if a raga falls below the fold count,
   report it dropped and say so.
2. **n before the percentage, at every level** — tracks, groups, ragas, and
   folds actually used. If level (c) leaves too few groups per raga for a
   5-fold split, **the n is the finding**, and it must be stated as the headline
   rather than buried under a percentage.
3. **Report the chance floor at every level.** This is a classification task,
   so the floor is not 1/N-pool: report both the **majority-class rate** and the
   **class-prior expectation** over the surviving label distribution, recomputed
   per level, because item-level grouping changes that distribution.
4. **Report top-1 and top-3 at every level.** 84.7% top-3 is quoted as often as
   the top-1 and a raga-first product would plausibly ship on top-3.
5. **Secondary, non-gating: per-raga top-1 at level (c).** A raga-first product
   needs to know which ragas actually carry, not just the mean. Report it, but
   do not let it drive the verdict.

## Interpretation, fixed in advance so it is not chosen after the number

Bands are on **level (c) top-1**, against the level-(a) reproduction of 72.8%.

| level (c) result | what it means |
|---|---|
| **≥ 65%** | raga genuinely generalizes to unseen sources. It is the real asset, the concert-companion product pivots to raga-first on long-form audio, and the composition work is correctly deprioritized. |
| **45-65%** | degraded but real. Restate the number honestly everywhere and check whether top-3 still clears a product bar; do not abandon, do not keep quoting 72.8. |
| **< 45%, or within ~3× the class-prior floor** | the last positive number was contamination too. Every model-side result in the repo is then closed, and there is nothing left to measure — the only remaining moves are scope and demand. |
| **too few groups/ragas at (c)** | the corpus cannot answer the question. Report that plainly; do not fill the gap with the level-(a) number. |

## Rules of engagement

- Read-only. Do not retrain production, do not overwrite `models/raga_v3_*.pkl`
  or `models/raga_classifier.pkl`, do not touch `identify_clip.py`.
- Write the prereg to `data/raga_audit/PREREGISTRATION.md` **before the first
  fold is scored**, and commit the audit promptly so the ordering is fixed in
  git history rather than in mtimes — the Qmax audit's ordering currently rests
  on file mtimes alone, which is weaker than it should be.
- One protocol per level, chosen before running. Do not tune until the number
  improves.
- Reuse `data/qmax_audit/provenance.json` rather than re-deriving provenance;
  it resolved 1,232 of 1,232 tracks and was validated against
  `download_manifest.json` on 400 rows with zero contradictions.
- `~/sung_tests --cache-v2` remains the only scoreboard. This audit measures a
  historical claim and graduates nothing.
- Estimated cost: TDMS recompute over ~1,232 contours plus 15 RF fits
  (3 levels × 5 folds, 800 trees). Hours on 8 cores, no GPU. If it looks like
  more, report the cost before spending it.
- Write it up in `data/RAGA_CONTAMINATION_AUDIT.md`: the reproduction gate
  result first, then the three levels with n and floors, then a one-paragraph
  verdict. Log in `AGENT_LOG.md` in normal prose. **Leave the verdict to the
  verifier seat.**
