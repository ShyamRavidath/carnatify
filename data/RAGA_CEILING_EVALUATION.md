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

*A full classification of the 274 nulls is under audit by the outside-voice seat
(`CODEX_RAGA_VOCABULARY_BRIEF.md` → `data/RAGA_VOCABULARY_AUDIT.md`). The
adversarial half matters: `_CANONICAL_ALIASES` exists because fuzzy matching at
0.6 merges genuinely different ragas, and a wrong merge poisons a class more
than a null does.*

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

Both columns already exist. The accuracy column has been sitting in
`data/raga_audit/archived_tierscan_tdms_only.log` since the July audit:

| `min_tracks` | classes | coverage | top-1 | **correct per 100 items heard** |
|---|---|---|---|---|
| 25 | 18 | 39.1% | 72.8% | **28.5** |
| 20 | 32 | 59.6% | 67.6% | **40.3** |
| 15 | 44 | 70.9% | 63.4% | **45.0** |
| 10 | 54 | 79.2% | 61.6% | **48.8** |

**Monotone increasing, and it nearly doubles.** Going from the 18-class tier to
a 54-class tier costs 11.2 pp of top-1 and buys **+71% more correct answers per
concert**.

**Caveats, stated plainly.** Those top-1 figures are level (a), not
source-disjoint — but the audit measured the disjointness penalty at the 18-tier
as **0.6 pp** (72.8 → 72.2), so it is small and there is no reason it explodes
at a wider tier. Coverage is repertoire mass, which weights by how often a raga
is *programmed*, not by how often it is programmed in the concerts Deepti
attends. And a wider tier means more ways to be confidently wrong, which is what
§5 is about. **A workhorse seat is re-running this column source-disjoint with
per-class accuracy and a McNemar test on whether the added classes poison the
existing 18** (`WORKHORSE_RAGA_COVERAGE_BRIEF.md` →
`data/RAGA_COVERAGE_CURVE.md`). Until that lands, this table is the best
available estimate and not a measurement.

**But the direction is not in doubt, and the 54-class model needs no new data.
It is trainable today, from the cache that is already on disk.**

---

## 4. So: is it a data ceiling?

| claim | verdict | evidence |
|---|---|---|
| "wild audio kills the raga path" | **false** | 59.3% wild ≈ 60.4% clean at matched duration; 7.5 pp measured field cost; zero contour failures |
| "we need better features / a better model" | **not yet the constraint** | the binding loss is 61-73% of field clips having no emittable class at all |
| "we need more audio per class" | **unproven, and weakly contradicted** | r(tracks, top-1) = 0.066 over the 18 tier classes; Vasanta 35.7% at 28 tracks vs Pūrvīkaḷyāṇi 96.2% at 26. Range is restricted to 25-30 so this is weak — the wide-tier per-class curve settles it |
| "we need more *classes*" | **yes, and they are free** | +71% correct answers per concert from a retrain on existing data |
| "we need more audio, full stop" | **yes, and it is already identified** | 1,712 scraped-and-labelled items never fetched, plus ~689 behind a fixable alias map |
| **"we have hit a data ceiling"** | **no** | nothing here has been tested at the ceiling. The corpus is 43% of the repertoire already scraped, under a fetch target that says `30` |

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

1. **Retrain the raga model at `min_tracks = 10` and measure it properly.**
   Zero new data, zero dollars, hours not days. Estimated +71% correct answers
   per concert. Blocked only on `data/RAGA_COVERAGE_CURVE.md` confirming the
   estimate source-disjoint. *In flight.*
2. **Fix the alias map.** ~689 concert items and an unknown number of real
   classes are behind a `null` that says "not in compmusic's 40". Ābhēri alone
   would have changed the wild set. *In flight —
   `data/RAGA_VOCABULARY_AUDIT.md`. Note the risk: a wrong merge is worse than a
   null.*
3. **Measure long-form wild audio.** The entire product case rests on 10-30
   minute items and every wild clip on disk is under 85 s. Needs ~10 new
   recordings of full concert items, frozen and hashed before anything is
   predicted. This is the one place where **Deepti's own attendance is the
   scarce resource**, and it is worth more than any model change on this list.
4. **Raise the fetch target from 30.** 1,712 identified items are unfetched;
   ~13 GB more disk and a few hours of melodia at 5 workers, on free
   archive.org. Do this *after* (1) tells us whether the wide tier holds up,
   because it is the same lever aimed at the classes that are short.
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
