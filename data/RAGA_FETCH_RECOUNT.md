# How much audio is actually reachable? — the recount `handoff.md` §5.3 asked for

Executed 2026-08-13 by the verifier seat, **entirely offline**, against the
1,857 already-cached archive.org metadata files in
`data/raga_v2_cache/archive_metadata/`. No network, no downloads, no audio
opened. Harness: `scripts/raga_fetch_recount.py`.

`handoff.md` §5.3 ranks "raise the fetch target above 30" as the best-value job
on the board, on the strength of `data/RAGA_COVERAGE_CURVE.md` §10's within-class
learning curve: **+18.4 pp from 10 to 30 tracks per class, with the marginal
track at the cap worth as much as the marginal track at the floor, and no
saturation anywhere.** Every class in the corpus is capped at 30 and nobody has
seen where the curve bends.

That argument is untouched. **This document is about whether the audio exists.**

> **Headline: it mostly does not. Against the handoff's own optimistic ceiling of
> 1,712 unfetched programme items, the cached metadata yields 378 genuinely new
> (raga, title) pairs, of which only 193 fall in the 54-class tier — 11% of the
> ceiling, exactly the "~10-13%" the handoff warned it would be. Ten of the 54
> classes have ZERO reachable audio and 41 of 54 have fewer than five. The
> reachable audio is also severely concentrated: the top two classes hold 25% of
> it and the bottom 27 classes hold 10%.**

This does not kill the fetch. It re-prices it, and it says the fetch cannot be
executed as "top every class up past 30" because for most classes there is
nothing to top up with.

---

## 1. The calibration check, reported before the headline

The count is only worth as much as its attribution logic, which mirrors the two
committed fetchers rather than reimplementing them:

- **own-label** — the raga is in the file's own `title` or filename, resolved
  strictly through `data/raga_aliases.json`, never guessed from audio. Mirrors
  `download_targeted_deficits.py:parse_file`'s three label sources and imports
  that module's own `norm` / `fold` / `vfold` matchers.
- **title-join** — the filename matches a composition title that maps to exactly
  one canonical raga across every blog record. Uses `download_title_join.py`'s
  own `build_title_raga_map` and `tfold`.

Registered as the check: the same pass counts how many cached files resolve to a
`(raga, title)` pair **already on disk**. The fetchers have put 1,238 files in
`data/concert_audio`, so that number has to land nearby or the attribution has
drifted and nothing else here can be trusted.

```
mp3 files in cached archive.org metadata        6692
resolve to a pair already on disk               1291
files actually in data/concert_audio            1238
```

**Within 4.3%.** The logic tracks the fetchers.

## 2. The count

| quantity | value |
|---|---|
| mp3 files in cached metadata | 6,692 |
| resolve to a pair already on disk | 1,291 |
| **reachable NEW distinct (raga, title) pairs** | **378** |
| — in the 54-class tier | **193** |
| — off-tier (would add *new* classes) | 185 |
| `handoff.md` §2e's optimistic ceiling | 1,712 |
| **realised fraction of the ceiling** | **11%** |

`handoff.md` §2e already said "only ~10-13% of programme rows exact-match cached
archive.org metadata" and told the reader to treat 1,712 as a ceiling. **That
warning was exactly right and is now a measurement.** The 1,712 figure should not
appear again except as a ceiling.

### How much more metadata could be pulled

The recount is bounded by what is cached, so the obvious objection is that more
metadata would find more audio. It is bounded:

| source | identifiers |
|---|---|
| blog `source_url` pages (`archive_identifiers.json`) | 425 |
| archive.org search (`archive_search_identifiers.json`) | 2,022 |
| union | 2,115 |
| metadata already cached | 1,857 |
| **identifiers with no cached metadata** | **258 (12%)** |

Pulling the remaining 258 is a cheap network job and would, at the same yield,
add roughly 50 more tier-relevant pairs. **It does not change the verdict** —
193 does not become 1,712 by adding 12% more metadata.

## 3. Where the reachable audio is, and it is not where it is needed

Ten of the 54 classes have **zero** reachable audio. Forty-one of 54 have fewer
than five. The distribution is severely concentrated:

| | reachable pairs | share |
|---|---|---|
| top 2 classes (Tōḍi 26, Kalyāṇi 22) | 48 | **25%** |
| top 5 classes | 78 | 40% |
| bottom 27 classes | 20 | **10%** |

The most reachable classes, against what more audio was measured to buy them
(`data/RAGA_COVERAGE_CURVE.md` §10.4, within-class, three seeds):

| raga | on disk | reachable new | top-1 at cap 10 | **measured gain 10→30** |
|---|---|---|---|---|
| Tōḍi | 23 | **26** | 73.3% | +13.3 pp |
| Kalyāṇi | 26 | **22** | 83.3% | **+0.0 pp** |
| Sāvēri | 27 | 11 | 60.0% | **−3.3 pp** |
| Hamsadhvāni | 30 | 10 | 73.3% | **−3.3 pp** |
| Kāmavardani | 30 | 9 | 46.7% | +26.7 pp |
| Śankarābharaṇaṁ | 27 | 9 | 56.7% | +16.7 pp |

Against the classes with the most to gain:

| raga | on disk | reachable new | top-1 at cap 10 | measured gain 10→30 |
|---|---|---|---|---|
| Bhairavi | 30 | **3** | 20.0% | +50.0 pp |
| Kānaḍa | 27 | 7 | 20.0% | +40.0 pp |
| Ṣanmukhapriya | 25 | **4** | 36.7% | +32.3 pp |
| Karaharapriya | 27 | **2** | 20.0% | +28.1 pp |
| Harikāmbhōji | 26 | **3** | 30.0% | +25.2 pp |

**Kalyāṇi is the single decisive example and it needs no statistics.** It is the
second-most-reachable class in the corpus, with 22 new recordings available, and
tripling its training data was measured to move it **+0.0 pp**. Meanwhile
Bhairavi, which went 20.0% → 70.0% on the same tripling, has **three** recordings
available.

### The correlation — and why it is reported as suggestive, not established

The tempting claim is "reachable audio is anti-correlated with what audio buys".
Across the 18 classes with a full within-class curve:

| pairing | Pearson | Spearman |
|---|---|---|
| reachable vs **gain (10→30)** | r = −0.431, p = 0.074 | ρ = −0.531, **p = 0.023** |
| reachable vs **accuracy at cap 10** | r = +0.556, **p = 0.017** | ρ = +0.500, p = 0.035 |
| reachable vs **accuracy at cap 30** (noise-free) | r = +0.398, p = 0.102 | ρ = +0.251, p = 0.314 |

**The first two significant-looking rows are the trap `handoff.md` §4 records**,
and this seat walked into it before checking. `gain = acc@30 − acc@10` carries
`acc@10` on both sides, and `acc@10` is a noisy 10-track draw, so regressing
anything on either quantity mixes signal with regression to the mean. Regressed
on **`acc@30`, the noise-free endpoint**, the association drops to
p = 0.10 / p = 0.31 and **is not significant at n = 18.**

So the honest statement is: **the concentration is a fact and the anti-correlation
is not established.** The concentration alone is enough — 10 classes at zero and
41 under five is a hard constraint on what a fetch can do, and it is set
membership arithmetic with no model and no correlation in it.

## 4. What this means for `handoff.md` §5.3

§5.3 reads: *"Raise the fetch target above 30. ~13 GB more disk, a few hours of
melodia at 5 workers, free archive.org. Fetch broadly, not targeted at weak
classes. Recount reachable audio first — 1,712 is an optimistic ceiling."*

The recount is done and it changes the job:

1. **"Raise the fetch target above 30" is not executable for most classes.**
   Only 4 of 54 classes have 10 or more reachable recordings. For 41 classes the
   reachable audio would not move them by five tracks.
2. **"Fetch broadly" survives and is now the only option anyway** — not because
   breadth was shown to be better (the handoff correctly retired the "target the
   weak classes" inference as regression to the mean), but because there is no
   targeting to do. You take what exists.
3. **The 185 off-tier pairs are the more interesting half of this count.** They
   attach to ragas *below* `min_tracks = 10`, i.e. classes the model cannot name
   at all today. `data/RAGA_CEILING_EVALUATION.md`'s thesis is that the binding
   constraint is vocabulary — the model cannot name 40-60% of what a listener
   hears — and 185 recordings spread over new classes is a **vocabulary** lever,
   not a depth lever. Whether it is enough to bring any class over the line is
   not measured here and is the obvious next question.
4. **The cheap network job first.** Pull metadata for the 258 uncached
   identifiers before deciding anything. It is free, it is offline-safe
   afterwards, and it bounds the whole question properly.

**This does not retire the within-class curve.** +18.4 pp from tripling a class's
audio remains the best-measured lever in the repo. What changed is the estimate of
how much audio can be tripled with: for most classes, none.

## 5. Scope — what this does not establish

- **It counts candidate recordings, not training tracks.** Every reachable file
  still has to survive download, Demucs, melodia, and the frozen `v.size < 500`
  / `tonic <= 0` drops. **378 is itself an upper bound**, a tighter one than
  1,712 but an upper bound.
- **It is bounded by cached metadata**, and 258 identifiers (12%) are uncached.
  §2 bounds what that can add; it does not measure it.
- **It says nothing about audio outside archive.org.** Other sources exist and
  none of them were counted.
- **It does not measure what the off-tier audio would buy.** 185 pairs across
  classes below the tier is a vocabulary lever whose value is unmeasured.
- **No model was fit and nothing was retrained.** The within-class figures quoted
  here are read from `data/raga_coverage/within_class.json` as committed.

## 6. Artifacts

| file | what |
|---|---|
| `scripts/raga_fetch_recount.py` | the recount, offline, using the fetchers' own matchers |
| `data/raga_tier/fetch_recount.json` | per-class counts, machine-readable |
