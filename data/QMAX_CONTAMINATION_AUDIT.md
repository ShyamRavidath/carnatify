# Qmax contamination audit — how much of "60-67%" survives disjointness

Executed 2026-07-30 by the Opus 5 workhorse against
`WORKHORSE_QMAX_AUDIT_BRIEF.md`. Read-only: no retraining, no catalog rebuild,
no edit to `identify_clip.py`. The readings were registered in
`data/qmax_audit/PREREGISTRATION.md` before the first row of the distance
matrix existed.

**Headline: 60.0% → 9.5%. Of the 36 correct answers in the original run, 34 were
won by a byte-identical copy of the query.**

---

## 1. What "60-67%" actually is

It is not one number. Commit `7e9bc7e` (2026-07-09) reports two runs:

> Internal (saraga, work-mbid identity, 194-track catalog, LOO):
>   min(pyin-vocal, melodia-mix) windowed Qmax = 66.7% top-1 / 76.7% top-5
> External (scraped concerts, 108 multi-rendition works, 800-track catalog,
> melodia-only): 60.0% top-1 / 61.7% top-5 on 60 cross-artist queries.

`HANDOFF_CLIP_ID.md:45`, `ARCHITECTURE.md:72` and `HANDOFF_SESSION_0725.md:77`
compress the two endpoints into a single range, "60-67% top-1 (Qmax)". They are
different corpora, different feature channels, and different catalog sizes. The
top-5 figures pin the internal denominator exactly: 76.7% = 23/30 and 66.7% =
20/30, so the internal arm was **n = 30 queries**.

Both eval scripts are byte-identical to their state at that commit
(`git diff 7e9bc7e -- evaluate_composition_qmax.py evaluate_composition_external.py`
is empty), so this audit runs against the exact code that produced the claim.

### The protocol, quoted

`evaluate_composition_external.py` groups tracks into "works" by folded title
and raga directory, **after stripping a rendition suffix**:

```python
REND_SUFFIX = re.compile(r'_r\d+$')

def work_key(path):
    # archive__<raga>__<title stem>.npy
    parts = path.stem.split('__', 2)
    if len(parts) != 3: return None
    raga, stem = parts[1], parts[2]
    stem = REND_SUFFIX.sub('', stem)
    t = fold(NUM_PREFIX.sub('', stem))
    if len(t) < 6: return None
    return (t, fold(raga))
```

Queries are every track whose work has two or more members, capped at 60. The
only thing that ever prevents a query from being scored against a reference is
one line:

```python
def eval_query(i):
    s = np.full(N, np.inf)
    for j in range(N):
        if j == i: continue
        ...
    order = np.argsort(s)
    ranked = [keys[j] for j in order[:5]]
    return i, ranked[0] == keys[i], keys[i] in ranked
```

**`if j == i: continue` is the entire leakage control.** It excludes the
query's own array index. Nothing excludes another file containing the same
recording, another track from the same archive upload, or another performance
by the same artist. The internal script `evaluate_composition_qmax.py:65` has
exactly the same single guard.

Answering the brief's point 1 directly: the **evaluation** protocol is fully
determinable from the repo for both arms. The **feature** protocol is not, for
one of the two internal channels — see §5.

---

## 2. What the corpus turned out to contain

`data/raga_v2_cache/melodia_full/` filenames carry no provenance, so it was
rebuilt (`scripts/qmax_provenance.py`): `download_manifest.json` resolves 735 of
1,232 tracks directly, and an exact file-size join against the 1,857 cached
archive.org item listings resolves the remaining 497, disambiguated by MD5 where
several items share a size. The join was validated against the manifest before
use — on 400 manifest rows it agreed on 400 and contradicted none.
**Result: archive_identifier recovered for 1,232 of 1,232 tracks (100%), across
292 distinct archive items.**

That made the decisive check possible. Hashing each melodia contour:

| | |
|---|---|
| contour-identical groups | 72 |
| tracks inside them | 182 (14.8% of the corpus) |
| **redundant byte-identical copies** | **110** |

Because `work_key()` strips `_r\d+$`, files like `Soundararajam`,
`Soundararajam_r2`, `_r3`, `_r4` — one recording stored four times — are counted
as four renditions of one work, and each is eligible to be another's correct
answer. `Varāḷi__aparAdamula_r2` through `_r6` are five copies of a single
Chittoor V Nagaiah recording, filed under two spellings of one archive
identifier (`78RPM-Chittor-V-Nagaiah` and `78RPM-ChittoorVNagaiah`).

A near-duplicate sweep over all 128 positive pairs (lengths within 0.5%, ≥90% of
voiced frames agreeing within 5 cents) found **zero** pairs that were
near-identical without being byte-identical. The exact test is therefore not a
weak proxy for the intended one; on this corpus it is the same test.

**Of the 128 positive pairs available to the 60 queries, 51 (40%) are
byte-identical to the query.**

Corpus-level rendition inventory, which matters beyond this audit:

| grouping | with ≥2 tracks | with ≥2 **distinct recordings** |
|---|---|---|
| (folded title, raga) — the eval's own key | 108 of 1,011 works | **73** |
| folded title only | 121 of 957 titles | **87** |

`HANDOFF_SESSION_0725.md:88` counts "65 titles with 2+ renditions" as a retrain
asset. On the same corpus, 367 tracks in multi-track title groups collapse to
**261 distinct recordings**. The rendition-corpus lever is real but roughly 28%
smaller than a file count implies.

---

## 3. External arm — the three levels

One distance matrix, computed once (`scripts/qmax_audit_matrix.py`, 60 × 800,
checkpointed every row), read out four times under different masks
(`scripts/qmax_audit_score.py`). No distance was recomputed for any level, so no
level could be tuned by re-running.

The protocol state was reproduced exactly: **1,203 tracks, 1,011 works, 108
multi-rendition works, N = 800 after the seeded 500-distractor slim, 60
queries** — matching the commit's "108 multi-rendition works, 800-track catalog,
60 queries" on every figure.

| level | evaluable n | top-1 | 95% CI | top-5 | mean refs | chance top-1 |
|---|---|---|---|---|---|---|
| **(a)** as-originally-run | 60/60 | **36/60 = 60.0%** | [46.5%, 72.4%] | 37/60 = 61.7% | 799 | 0.0027 |
| **(b)** recording-disjoint | 43/60 | **3/43 = 7.0%** | [1.5%, 19.1%] | 5/43 = 11.6% | 798 | 0.0023 |
| **(c)** source-disjoint | 42/60 | **4/42 = 9.5%** | [2.7%, 22.6%] | 5/42 = 11.9% | 778 | 0.0023 |
| (c′) sensitivity, registered | 39/60 | 4/39 = 10.3% | [2.9%, 24.2%] | 5/39 = 12.8% | 775 | 0.0022 |

Over all 60 queries rather than the evaluable subset — the lower bound, counting
a query with no surviving positive as a miss — level (b) is 5.0% and level (c)
is 6.7%.

**Level (a) reproduces the historical number exactly: 36/60 = 60.0% top-1,
37/60 = 61.7% top-5, identical to the commit message in both places.** The
harness is not bit-rotted and needed no repair; essentia 2.1-beta6-dev imports
and runs in both `venv` (py3.14) and `venv_train` (py3.11).

### Chance floor, arithmetic shown

Computed as `colab_coverhunter_rescore.py:212` does it — mean positives per
**clip** over pool size, never averaged over songs, which is the error that once
printed 0.006 for 0.031:

```
chance = mean over evaluable clips of ( positives surviving the mask
                                        / references surviving the mask )
```

Level (a): 2.13 positives / 799 references = 0.0027.
Level (c): 1.76 positives / 778 references = 0.0023.

So level (c)'s 9.5% is roughly **41× the chance floor** — real signal, but see
§6 on what that does and does not license.

### Where the 60% went

Of the 36 top-1 hits at level (a), **34 were won by a reference whose melodia
contour is byte-identical to the query's.** The signature is visible in the
distances: every duplicate-won hit sits at exactly **0.036**, the Serra09
asymmetric floor for an identical sequence, while genuine cross-recording
matches land at 0.064-0.108. Removing the copies drops those same queries to
ranks 11, 279, 715, or leaves them with no true positive at all — 17 of the 60
queries had no positive that was not a copy of themselves.

Level (c) scores *higher* than level (b) — 4/42 against 3/43. This is not noise
in the matcher: masking removes distractors as well as positives, and
`Kānaḍa__sri mAtrubhootam` wins at (c) because same-item distractors that had
been outranking its genuine cross-item match were removed. No query that hit at
(b) lost at (c).

### The four survivors, verified individually

With n this small every hit was checked by hand rather than trusted:

| query | matched | same recording? | same item? |
|---|---|---|---|
| `Kānaḍa__sri mAtrubhootam` (`tvs-concert-25`, T V Sankaranarayanan) | `Kānaḍa__07 sri mAtrubhootam` (`300ssi`) | no | no |
| `Māyāmāḷavagauḷa__mEru samAna` (`22-emani-msg`) | `Māyāmāḷavagauḷa__mErusamAna` (`8-tnk-kwm`) | no | no |
| `Bhairavi__brOvavamma_r2` (`305-tns`) | `Bhairavi__brOvavamma_r3` (`74-tsk`) | no | no |
| `Madhyamāvati__nagumOmu_r5` (`3-MR-TC-…`, Manakkal Rangarajan) | `Madhyamāvati__nagumOmu_r3` (`78RPM-Musiri-Subramanya-Iyer`) | no | no |

All four are genuine cross-recording, cross-upload matches; two are also
cross-artist by name. Margins over the runner-up are thin: 0.010 to 0.027.

### The "cross-artist" label was never checked

The commit calls these "60 cross-artist queries". The repo has no artist field
for most of them. At level (c), **only 4 of the 42 evaluable queries have an
artist recorded on both sides**; the other 38 are cross-artist by assumption.
Corpus-wide, just **13 of 1,011 works** have two or more *known, distinct*
artists. And 32 of the 42 evaluable queries draw all their surviving positives
from a single archive item, so level (c) usually rests on one alternative source
rather than several.

Answering the brief's point 4 plainly: **the corpus cannot support a
cross-artist claim at all**, at any level, and never could have.

---

## 4. Internal arm — clean, and separately unreproducible

The internal arm cannot be re-run: `evaluate_composition_qmax.py` reads
`comp_pitch_cache/` and `melodia_cache/`, and neither directory exists. What was
scored instead is a declared reconstruction from the committed
`models/qmax_catalog.npz` (`scripts/qmax_audit_internal.py`), differing from the
original in three named ways — one pyin-vocal channel instead of
`min(pyin-vocal, melodia-mix)`; `W_REF` 800 with zero-padding of short tracks
instead of 1000 unpadded; `MIN_CHROMA` 200 instead of 30.

| level | n | top-1 | top-5 | chance top-1 |
|---|---|---|---|---|
| (a) as-originally-run | 26 | 7/26 = 26.9% | 8/26 = 30.8% | 0.0066 |
| (b) recording-disjoint | 26 | 7/26 = 26.9% | 8/26 = 30.8% | 0.0066 |
| (c) source-disjoint (+concert, +artist) | 26 | **7/26 = 26.9%** | 8/26 = 30.8% | 0.0070 |

**Identical at all three levels — not one query changed, not one rank.** The
reason is structural and provable without any Qmax score: all 17 Saraga
multi-rendition works span distinct concerts *and* distinct artists. Saraga 1.5
Carnatic is 249 recordings across 27 concert folders with clean per-track
concert and album-artist metadata, and no work has two renditions from one
concert. **The internal arm carries zero same-recording, same-concert and
same-artist contamination, by construction.**

26.9% is **not** a corrected 66.7% and must never be written as one. The
reconstruction is a different measurement — 60 of its 187 tracks receive up to
800 frames of zero padding, which degrades chroma cross-similarity — so it is a
floor, not an estimate of what the original would score.

---

## 5. What cannot be repaired, and what it costs

- **The pyin-vocal channel: not repairable at any price.** Twelve scripts in
  `scratch_archive_0711/` read `comp_pitch_cache/meta.json` and its `d['f']` /
  `d['tonic']` arrays. **Nothing in the repository, and nothing in any commit,
  ever wrote it** — `git log --all -S"comp_pitch_cache"` returns only the two
  consumers. Whether `d['f']` was librosa.pyin over a Demucs stem, pyin over
  Saraga's multitrack vocal, or the `pitch_vocal` annotation is unrecorded, and
  those are different measurements. The `tonic` field has no recorded origin at
  all.
- **The melodia-mix channel: repairable, ~2.2 h wall on 8 cores.**
  `scratch_archive_0711/comp_melodia_full.py:32` documents it exactly —
  `PredominantPitchMelodia(frameSize=2048, hopSize=128)` after `EqualLoudness`,
  on `t.audio_path` — and all 249 Saraga mixes are on disk. Measured on one
  34-minute track: 13× realtime, so ≈1.4 h to rebuild the cache on 8 cores plus
  ≈50 min of Qmax at the original `W_REF=1000` parameters.

This spend was **not** taken. It would refine the absolute value of a number
outside the audit's registered question, and it cannot change the internal arm's
contamination answer, which is already zero with certainty from metadata alone.
That call belongs to the verifier seat.

---

## 6. Verdict

**Against the interpretation table fixed in advance in the brief, level (c) does
not hold near 60-67% and does not land in the 20-40% band; the closest row is
"collapses toward the chance floor — the last positive number was
contamination", and that is the reading taken.** The external arm falls from
60.0% to 9.5% once a query cannot be scored against its own recording, own
upload or own artist, and the mechanism is not subtle: 34 of the original 36
correct answers were byte-identical copies of the query, sitting at the exact
Serra09 distance floor for an identical sequence. Two qualifications belong with
that sentence and must travel with it. First, 9.5% is about 41× the 0.23% chance
floor and all four surviving hits are individually verified genuine
cross-recording matches, so the residual is real signal, not zero — but its 95%
CI is [2.7%, 22.6%], it is well below the "real but weak" band, and it is not a
product-relevant number under a bar of ~85% precision. Second, the internal
66.7% is a *different* claim: it is not contaminated at all, and the audit found
no leak in it at any level — but it rests on a feature cache whose builder was
never committed, so it is unreproducible in principle from this repository, and
it was always n = 30. The practical consequence is that **"60-67% top-1 (Qmax)"
should stop being quoted as a single range**: the external half of it was
contamination, and the internal half cannot be reproduced. With every model-side
door in `handoff.md` §1 now measured and closed, the honest next move is scope
and demand rather than another model — and any future melodic work needs a
rendition corpus built recording-disjoint from the start, because this one has
73 usable works and 13 with verifiable artist diversity.

**Scope.** This measures full-recording archive-domain Qmax only. It graduates
nothing, it does not touch `~/sung_tests --cache-v2` (still the only
scoreboard), and it does not revisit Qmax on wild 30-60s clips, where
`ARCHITECTURE.md:72` already records 0%.

---

## 7. Artifacts

| file | what |
|---|---|
| `data/qmax_audit/PREREGISTRATION.md` | readings registered before the first matrix row existed |
| `scripts/qmax_provenance.py` | track → archive item → artist recovery, 100% resolved |
| `scripts/qmax_audit_protocol.py` | exact replication of the original protocol state |
| `scripts/qmax_audit_matrix.py` | the 60 × 800 distance matrix, checkpointed per row |
| `scripts/qmax_audit_score.py` | the four masked read-outs |
| `scripts/qmax_audit_internal.py` | the declared Saraga reconstruction |
| `data/qmax_audit/provenance.json` | per-track item, artist, contour hash |
| `data/qmax_audit/external.json`, `internal.json`, `protocol.json` | machine-readable results |
| `data/qmax_audit/D_rows.npz`, `D_internal.npz` | the distance matrices (gitignore candidates) |
