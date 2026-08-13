# Have we hit a data ceiling? — a holistic evaluation of the raga path

Written 2026-08-13 by the verifier seat, at Deepti's request, after her audit of
the 29 wild raga labels (`data/RAGA_WILD_MEASUREMENT.md` §11) closed the last
open condition on the field number.

**Answer in one line: no. The raga path has never been near a data ceiling. It
has been sitting under three stacked collection caps, all of them chosen by a
constant in a script, and the largest one costs nothing to lift.**

Every number below is either measured in a committed audit or computed here from
committed artifacts, and each is labelled with which. Where a number is an
estimate, it says so.

---

## 1. The corrected field number, and what it is not evidence of

The expert label audit dropped two ineligible clips. Both were misses, and both
were named in advance in `data/RAGA_WILD_MEASUREMENT.md` §3 as a registered
sensitivity, so the audit chose between two published branches rather than
creating one:

| | value |
|---|---|
| top-1, fused, `mix`, whole clip, 27 audited in-tier wild clips | **16/27 = 59.3% [40.7, 75.5]** |
| top-3, tier-restricted | 20/27 = 74.1% [55.3, 86.8] |
| chance floor / best-constant floor | 5.6% / 17.2% |

Median clip length in that set is 60.0 s.

**Now put it next to the clean-audio duration curve, at the same duration and
the same 18-raga tier** (`data/RAGA_DURATION_CURVE.md`, source-disjoint):

| condition | duration | top-1 |
|---|---|---|
| clean studio/concert corpus, source-disjoint CV | 60 s | **60.4%** |
| real wild phone/YouTube audio, exported model | ~60 s | **59.3%** |

**These are the same number.** Different corpora and a different model
(TDMS-only vs fused), so this is not a paired comparison and 1.1 pp is far
inside either CI — but it is the third independent line of evidence pointing the
same way. `data/RAGA_DOMAIN_DECOMPOSITION.md` measured field-realistic
degradation at **7.5 pp**, with phone chain (+0.4), room (+2.1) and pink noise
(+2.7) each having a CI touching zero. And `data/RAGA_WILD_MEASUREMENT.md`
measured **zero** contour failures, zero tonic failures, and voicing density
inside the training corpus's own band.

> **The field is not the problem. Wild audio costs approximately nothing.** The
> whole gap between "72.2% on full tracks" and "59.3% in the wild" is
> **duration**, not domain. This retires the last version of the "it dies on
> real audio" pessimism, which has now been refuted from four directions.

That matters for the product because the framing since 2026-07-25 is a
**concert companion**, and a listener present for an item hears **10-30
minutes**, not 60 seconds. On the measured duration curve that is the 300-600 s
region: **68.8% and 71.0%**, against the 60.4% the wild set was measured at.

**The one thing this does not establish** is that long *wild* audio behaves like
long *clean* audio. Every wild clip in `~/sung_tests` is 43-85 s, so the
long-form field cell has never been measured. It is the cheapest remaining
experiment and §6 lists it first.

---

## 2. The real ceiling is vocabulary, and it is three caps deep

Accuracy was never the binding constraint. **Coverage** was, and nobody priced
it. Of the 106 wild clips, the model can emit the correct answer for **29** at
the 18-raga tier — 27% — and on the other 77 it cannot be right at any accuracy.

Here is where those clips go, measured today from
`data/raga_v2_cache/{saraga_v3,archive_v3}/*.npz` (88 distinct ragas, 1,297
tracks, counted here) and `~/sung_tests` (81 clips carrying a real raga label):

### Cap 1 — the label vocabulary (`normalize_ragas.py`)

Scraped raga spellings are canonicalised against **compmusic's 40 Carnatic ragas
∪ Saraga's track-metadata raaga set**. Anything that misses becomes `null`. That
bucket is **274 spellings covering 689 of 3,698 concert items (18.6%)**, and the
repo has described it as junk. Sorted by item count, it opens:

```
36 Arabhi     28 darbAr    18 Vocal      16 dEvamanOhari  12 hamsanAdam
12 nAyaki     12 paras     11 AbhEri     11 keeravANi     11 Sivakavi
10 rEvati     10 kannaDagowLa  10 vAchaspati   9 valaji     8 jayamanOhari
```

Seventeen of the top twenty are standard concert ragas. **Ābhēri is in there** —
mapped to `null`, in the same bucket as `'14 April, 1991'` — which is precisely
why `nagumomu ganaleni` carried a wrong label into the frozen wild set and was
unhittable. Ārabhi and Darbār alone are 64 items.

The same gap runs the other way: `~/sung_tests/Kande Kandenu__Shankarabharana.mp3`
is Śankarābharaṇaṁ, a tier class with 30 training tracks, and it was **not
selected into the frozen 29** because the spelling `Shankarabharana` is not in
the alias file. `Ma Janaki__Khamboji.mp3` is a second. The frozen set should
have been at least 31.

### That audit landed, and it corrected me three ways

`data/RAGA_VOCABULARY_AUDIT.md` classified all 274 nulls. The headline confirms
the hypothesis: **561 of the 689 null items (81.4%) carry recoverable raga
labels; only 126 (18.3%) are junk.** Correct canonicalisation would take
labelled programme rows from 81.4% to 96.5% of the corpus. "Junk keys → null" is
wrong as a description and this repo should stop repeating it.

Three corrections to what I wrote above, all of which stand:

1. **The nulls were deliberate, not accidental.** `normalize_ragas.py` has a
   `_FORCE_NONE` set that *quarantines* absent names on purpose — 59 raw keys
   and 326 items — precisely because the 0.6-0.9 fuzzy band merges distinct
   ragas. **Preferring a null to a poisoned class was the right call.** The
   failure was downstream: calling the whole bucket junk and never expanding the
   registry. I framed this as a bug; it is an un-finished job.
2. **Ārabhi is not an alias bug.** It is absent from the 103-name
   CompMusic ∪ Saraga union entirely, so it is a missing raga, not a missing
   spelling. My "should have matched" framing was wrong for the single
   highest-count entry.
3. **The class ceiling is real but the audio is not there.** At `min>=10`,
   correct labelling would admit **+18 classes (54 → 72)** — Ārabhi, Darbār,
   Kīravāṇi, Dēvamanōhari, Kannaḍagauḷa, **Ābhēri**, Hamsanādam, Rēvati,
   Vācaspati and more. But only **57 of the 561 recoverable rows (10.2%)**
   exact-match already-cached archive.org metadata, and **on those 57, zero new
   classes clear `min_tracks = 10`.** Programme rows are not training audio.
   Treat §2's "1,712 unfetched items" as an **optimistic ceiling, not a promised
   corpus** — see §6.4.

### And it found something worse than the nulls

The **non-null** aliases contain live wrong merges, silently poisoning training
labels. Verified against `data/raga_aliases.json` by this seat:

```
'AbEri'             -> 'Sāvēri'              'gaulipantu'  -> 'Gauḷa'
'garuDwani'         -> 'Kāmavardani'         'jayantasri'  -> 'Dhanaśrī'
'sunAdavinOdhini'   -> 'Jaganmōhini'         'nalainakAnti'-> 'Kalāvati'
'navarasas kannaDa' -> 'Bṛndāvana sāranga'   'veera vasanatam' -> 'Vasanta'
```

**`AbEri -> Sāvēri` is the exact mechanism behind Deepti's correction #2.**
`data/RAGA_WILD_MEASUREMENT.md` §3 flagged that the archive training corpus
carries `nagumomu ganaleni` under a `Sāvēri` directory and said "either the
label is right or both inherited the same error". They inherited the same error,
and the error is **one line in the alias map**. It is small in volume — 17
scraped items across all eight merges — but it is label noise pointing in a
direction no accuracy metric can see, and it is the first evidence in this
project of *wrong* training labels rather than *missing* ones.

### Cap 2 — the download target is literally `30`

```
scratch_archive_0711/dl_deficits30.py:185
    targets: dict[str, int] = {fold(n): 30 for n in PRIORITY_20 + SECONDARY_20}
```

**No raga in the corpus has more than 30 tracks.** Ten sit exactly at 30. The
learning curve in tracks-per-class has therefore never been measured past 30 —
not because more audio does not exist, but because the fetcher was told to stop.

What is already scraped, identified, and **not downloaded**:

| | items |
|---|---|
| canonically-labelled scraped concert items | 3,009 |
| in the training cache | 1,297 |
| **identified but never fetched** | **1,712 (57%)** |
| …of those, in the 10 classes already at the cap | 440 |
| …in the 56 classes sitting *below* `min_tracks = 20` | 638 |

Plus the 689 null-labelled items behind Cap 1, most of which are real ragas.

### Cap 3 — `min_tracks`, the tier constant

Every published raga number uses one of two values of this constant, and the
coverage cost of the choice has never appeared next to the accuracy benefit:

| `min_tracks` | classes | corpus tracks | % of scraped repertoire mass covered | % of the 81 labelled wild clips emittable |
|---|---|---|---|---|
| 10 | 54 | 1,141 | 79.2% | 79% |
| 15 | 44 | 1,022 | 70.9% | 72% |
| 20 | 32 | 827 | 59.6% | 62% |
| 25 | 18 | 519 | 39.1% | 36% |

Repertoire mass is over the 3,009 canonically-labelled items in
`data/scraped_compositions.json` — real concert programmes, so a real prior over
what a listener actually hears.

---

## 3. The number that should have been the headline all along

A companion that is right 72.8% of the time about 39.1% of what it hears is
**worse** than one that is right 61.6% of the time about 79.2% of it. The
product metric is **expected correct answers per 100 items heard = coverage ×
top-1**, and it has never been computed.

**Measured, 2026-08-13**, by `data/RAGA_COVERAGE_CURVE.md` — source-disjoint
(level c), tier the only thing that moved, reproduction gate EXACT on the
integer counts at both level (a) and level (c). Counts independently re-derived
by this seat from `data/raga_coverage/levels_min*.json` and they match:

| `min_tracks` | classes | tracks | groups | top-1 (source-disjoint) | top-3 | coverage | **correct per 100 items heard** |
|---|---|---|---|---|---|---|---|
| 25 | 18 | 518 | 155 | **72.2%** [66.4, 78.1] | 84.0% | 39.1% | **28.2** |
| 20 | 32 | 826 | 185 | **64.0%** [60.0, 68.3] | 76.5% | 59.6% | **38.2** |
| 15 | 44 | 1,020 | 198 | **59.9%** [55.8, 64.4] | 71.3% | 70.9% | **42.5** |
| 10 | 54 | 1,139 | 204 | **57.0%** [52.7, 61.7] | 71.3% | 79.2% | **45.1** |

**Monotone increasing, and it peaks at the widest tier measured.** Going from
18 to 54 classes costs 15.2 pp of top-1 and buys **+60% more correct answers per
concert** (+72% on top-3). For the 18-class tier to win, top-1 at 54 classes
would have to be below **35.6%**; it is 57.0%. Top-1 falls log-linearly in class
count (R² = 0.9997, −13.8 pp per natural-log unit) while coverage rises faster.

### Correction to an earlier draft of this section

The first version of this table used the level (a) figures sitting in
`data/raga_audit/archived_tierscan_tdms_only.log` and argued the
source-disjointness penalty was 0.6 pp at the 18-tier and would not explode at a
wider one. **That was wrong, and it is the most useful thing the workhorse seat
found.** The level (a)→(c) penalty is tier-dependent: 0.6 pp at 18 classes but
**3.5 / 3.5 / 4.7 pp** at 32 / 44 / 54, and 8.0-11.8 pp on same-raga-same-source
clustered tracks against 1.2 pp at the narrow tier. So 61.6% at 54 classes was
optimistic by 4.6 pp and 48.8 hits/100 by 3.7.

Two consequences beyond this table:

- **Any raga figure at `min_tracks >= 20` or wider that was measured at level
  (a) is inflated.** That includes the `min>=20 67.6/79.4` line in
  `models/raga_v3_meta.json`'s `cv_note` and in `train_raga_v3_tdms.py`'s
  docstring. The exported model's own tier now has its first source-disjoint
  number: **64.0% / 76.5%**, TDMS-only arm.
- The conclusion survives the correction with room to spare. The direction was
  never in doubt; the magnitude was, and it is now measured rather than
  estimated.

**The 54-class model needs no new data. It is trainable today, from the cache
already on disk.**

### The added classes do damage the existing ones — a little, and significantly

McNemar, paired on the 518 tracks of the `min>=25` tier at level (c): −2.5 pp at
32 classes (p = 0.0295), −3.1 pp at 44 (p = 0.0166), **−3.5 pp at 54**
(b = 31, c = 13, exact p = 0.0096). Real, monotone, statistically significant —
and small. The added tracks themselves run at 47.2%, so most of the 15.2 pp
aggregate fall is **composition, not damage**: the wide tier is not mostly
breaking what worked, it is mostly adding harder classes. Pairing is exact at
the track level but not the fold level, so p is an upper bound on the evidence.

### A global `min_tracks` is the wrong knob

Only one class at 54 sits below the class-prior floor of 2.03%: **Nāṭakurinji,
0/11 top-1** (2/11 top-3, across eight distinct sources). Meanwhile five of the
ten best classes at that tier are *new* ones — Saurāṣtraṁ 92.3% on 13 tracks,
Gauḷa 86.7% on 15, Bēgaḍa 83.3%, Varāḷi 81.0%, Rītigauḷa 79.2%. A track-count
threshold cannot tell Saurāṣtraṁ (13 tracks, 92.3%) from Nāṭakurinji (11 tracks,
0.0%). **Per-class admission, priced on measured accuracy rather than on corpus
size, is the lever.** It is under measurement now, with the obvious trap —
selecting classes on the folds you then score on — called out in advance.

---

## 4. So: is it a data ceiling?

| claim | verdict | evidence |
|---|---|---|
| "wild audio kills the raga path" | **false** | 59.3% wild ≈ 60.4% clean at matched duration; 7.5 pp measured field cost; zero contour failures |
| "we need better features / a better model" | **not yet the constraint** | the binding loss is 61-73% of field clips having no emittable class at all |
| "we need more audio per class" | **open, and the evidence flipped** | across the 54 classes r(tracks, top-1) = **0.519**, p = 5.8e-05, cleanly monotone in bins: 39.9% (10-14 tracks) → 41.5% (15-19) → 52.6% (20-24) → **68.6%** (25-30). An earlier draft called this "weakly contradicted" on r = 0.066 — that r was computed over the 18-class tier, whose track counts only span 25-30, and range restriction made it meaningless. **But 0.519 is confounded**: the 25-30 bin is exactly the `PRIORITY_20`/`SECONDARY_20` set the fetcher deliberately topped up, so track count and "popular, canonical, easy" are entangled. Saurāṣtraṁ is 92.3% on 13 tracks and Nāṭakurinji 0.0% on 11 — n is not destiny. The within-class subsampling curve settles it and is in flight |
| "we need more *classes*" | **yes, and they are free** | +60% correct answers per concert (28.2 → 45.1 per 100), measured source-disjoint, from a retrain on existing data |
| "we need more audio, full stop" | **yes — but far less of it is reachable than §2 implies** | 1,712 scraped-and-labelled items are unfetched and 561 more are recoverable from the null bucket, but only ~10-13% of programme rows exact-match cached archive.org metadata, and on the 57 demonstrably matchable recoveries **zero** new classes clear `min_tracks = 10`. Programme rows are not training audio |
| "training labels are clean" | **false, newly** | eight live wrong merges in the non-null alias map, `AbEri -> Sāvēri` among them — the exact mechanism behind one of the two wild-set label errors |
| **"we have hit a data ceiling"** | **no** | the largest single lever, +60% correct answers per concert, is a retrain on data already on disk. The corpus is 43% of the repertoire already scraped, under a fetch target hard-coded to `30`. Nothing here has been tested at a ceiling |

The honest summary of a month and a half: the measurement discipline has been
excellent and it worked — five audits in three days killed one inflated number
and rescued four. What it audited was **accuracy on a tier**, over and over,
while the tier itself went unexamined. **Nobody asked what the model could not
answer.**

---

## 5. What is genuinely hard, and is not fixed by data

Three things, so this document is not just optimism.

1. **The catastrophic tail.** On the 27 audited wild clips the miss ranks are
   `[2, 2, 2, 4, 5, 5, 21, 22, 25, 28, 30]` out of 32. Six near-misses and
   **five catastrophes** — including `vAtApi gaNapathim` (Hamsadhvāni, the most
   famous concert opener in the repertoire) at rank 25. A companion that is
   confidently, absurdly wrong one time in five is worse than one that abstains.
   Widening the tier can only make this tail longer.

2. **The abstain gate is unbuilt, and the evidence for it is promising and
   thin.** Thresholding the fused top-1 probability on the corrected 27:

   | thr | fires on | top-1 among fired | catastrophes surviving |
   |---|---|---|---|
   | 0.00 | 100% | 59.3% [40.7, 75.5] | 5 |
   | 0.15 | 70% | 68.4% [46.0, 84.6] | 1 |
   | **0.20** | **63%** | **76.5% [52.7, 90.4]** | **1** |
   | 0.25 | 33% | 77.8% [45.3, 93.7] | 1 |

   At p ≥ 0.20 it answers on two-thirds of clips at 76.5% and drops four of the
   five catastrophes. **That threshold was chosen by reading this table, on the
   same 27 clips it is scored on** — it is a hypothesis, not a result, and it
   needs a held-out set before it goes anywhere near a user. Reported because it
   is the shape of the thing worth building, not because 76.5% is real.

3. **Out-of-vocabulary is a different problem from low confidence.** Even a
   54-class model is silent on 21% of repertoire mass. The 24/28 OOC rejection
   the handoffs cite is the **composition** path, not the raga path — there is no
   raga novelty detector and building one is not the same job as thresholding a
   softmax.

---

## 6. What to do, in cost order

1. **Retrain the raga model at `min_tracks = 10`, with per-class admission on
   top.** Zero new data, zero dollars, hours not days. **+60% correct answers
   per concert, measured source-disjoint, not estimated.** Drop Nāṭakurinji
   (0/11, the one class below the class-prior floor) and whatever else the
   per-class admission sweep condemns. **No longer blocked** —
   `data/RAGA_COVERAGE_CURVE.md` has landed and the curve is monotone to the
   widest tier measured. The one thing still open is whether admission should be
   priced per class rather than by track count; the sweep is in flight, and it
   only improves this number.
2. **Fix the alias map — as an exact reviewed registry expansion, never a lower
   fuzzy cutoff.** 561 recoverable items, +18 candidate classes at `min>=10`,
   and the eight live wrong merges above. *Landed:
   `data/RAGA_VOCABULARY_AUDIT.md` + `data/raga_aliases_audit.json`, which is a
   NEW file — `data/raga_aliases.json` is untouched because five committed
   measurements read it.* **Needs Deepti before any merge**: nine
   low-confidence rows, two ambiguous, and the equivalence table
   (Ābhēri / Karṇāṭaka dēvagāndhāri, Bhīmpalās, Udayaravicandrika /
   Śuddhadhanyāsi, Durgā / Śuddha Sāvēri). Merging Ābhēri into Karṇāṭaka
   dēvagāndhāri adds a class at `min>=15` and `min>=20`; splitting does not.
   That is a musician's call, not a model's. Fixing the eight wrong merges is
   the part that needs no adjudication — do it with regression tests.
3. **Measure long-form wild audio.** The entire product case rests on 10-30
   minute items and every wild clip on disk is under 85 s. Needs ~10 new
   recordings of full concert items, frozen and hashed before anything is
   predicted. This is the one place where **Deepti's own attendance is the
   scarce resource**, and it is worth more than any model change on this list.
4. **Raise the fetch target from 30 — but only if the within-class curve says
   so.** 1,712 identified items are unfetched; ~13 GB more disk and a few hours
   of melodia at 5 workers, on free archive.org. **This is now explicitly
   conditional.** The cross-class r = 0.519 argues for it and is confounded; the
   within-class subsampling curve is the honest test and is in flight. If that
   curve is flat from 20 to 30 tracks, more classes is the whole lever and this
   job is not worth doing. Note also the outside-voice seat's early finding that
   only ~10% of recoverable null items exact-match cached archive.org metadata,
   so 1,712 is an **optimistic ceiling, not a promised corpus**.
5. **Build the abstain gate, with a held-out set.** Not with the threshold in
   §5.2 — with a fresh one, fit on data the score never sees.
6. **Then, and only then, ask about features.** No feature work is justified
   while the model cannot name 40-60% of what it hears.

**Do not fund** (unchanged from `HANDOFF_SESSION_0731.md` §7.5): the rendition
corpus, tonic estimation, the lyrics/ASR composition path, Qmax, CoverHunter.
None of that is reopened by anything here.

---

## 7. Artifacts

| file | what |
|---|---|
| `scripts/raga_wild_relabel.py` | applies the expert label audit to the frozen results; re-scores without re-running any model |
| `data/RAGA_WILD_MEASUREMENT.md` §11 | the label audit and the corrected headline |
| `WORKHORSE_RAGA_COVERAGE_BRIEF.md` | the source-disjoint coverage/accuracy sweep — in flight |
| `CODEX_RAGA_VOCABULARY_BRIEF.md` | the 274-null alias audit — in flight |
| `data/raga_audit/archived_tierscan_tdms_only.log` | the tier scan that has been on disk since July and was never read against coverage |
