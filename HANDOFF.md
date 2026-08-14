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
