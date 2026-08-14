# Carnatify handoff

Last rewritten **2026-08-13** (second rewrite that day) by the verifier seat, for
a fresh session that will start with no memory of this one.

Repository: `/Users/shyamravidath/carnatify`
Branch: **`probe/duration-and-negative-arm`** · HEAD `3218fdc` · **53 commits at the time of writing, NOT PUSHED**
`main` is the PR target. **`identify_clip.py` has zero diff against `main`** —
nothing in this entire series has touched the production path.

**The previous version of this file is in git at `c84a4b4`.** It described the
state before the tier graduation, the alias repair and the fetch recount. Read
this one; reach for that only for archaeology.

> **`handoff.md` and `HANDOFF.md` are ONE FILE** on this case-insensitive
> filesystem. Git tracks both paths, so committing one leaves the other showing
> as modified. Do not "fix" this; just commit whichever path git shows you.

**Respond to Deepti in caveman style** (her standing preference — terse, drop
articles and filler, keep every technical term, code symbol and number exact).
Write docs, commits and `AGENT_LOG.md` in normal prose.

**Read order for a cold start:** this file → `data/RAGA_TIER_GRADUATION.md` (the
current model) → `data/RAGA_FETCH_RECOUNT.md` (why the fetch just got much
smaller) → `data/RAGA_CEILING_EVALUATION.md` (the thesis) →
`data/RAGA_COVERAGE_CURVE.md` → `HANDOFF_SESSION_0731.md` → `HANDOFF_CLIP_ID.md`
§5 (the master graveyard).

---

## 1. The goal

**An app that identifies what is being performed at a live Carnatic concert and
explains it.** Deepti is a Carnatic musician and a high-school student with a
CS/ML background. This began as a personal tool and is being evaluated as a
possible company.

The framing since 2026-07-25 is a **concert companion**, not a Shazam clone. The
listener is physically present for a 10-30 minute item. The 30-second
identification contract was inherited from Shazam and was never actually
required by the use case — undoing that inheritance is the single most important
reframing in this project's history.

**Demand evidence is no longer zero.** Jon — the one named real user, a Western
listener with no Carnatic exposure — was confused at a concert and, *unprompted*,
reached for an AI assistant to identify the piece. **It failed**, mostly with
refusals. He asked two questions:

1. *what is the song being sung* — composition ID. **Every door there is shut**
   (§4). Do not reopen without new information.
2. *what does the melody mean* — raga character plus sahitya meaning. Needs
   **no ASR, no CSI, no Qmax**, and the repo has **never attempted it**.

Any handoff older than `HANDOFF_SESSION_0731.md` says "demand evidence is zero";
**that line is stale and wrong.**

---

## 2. Current state

### 2a. The thesis, in one paragraph

The composition side is **genuinely closed**. The raga side **survived every
audit**, including the field. Its constraint is not accuracy — it is that the
model **cannot name 40-60% of what a listener actually hears**. As of today one
of the two levers against that has been **taken** (the tier is now 54 classes,
exported) and the other has been **re-priced and mostly closed** (there are only
193 more reachable tracks in the world this repo knows about, not 1,712). So the
vocabulary problem is now bounded by **data that does not exist**, not by a
constant in a script.

### 2b. The door table

| door | verdict | evidence |
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
| **the narrow 3-class drop** | **also loses — sign flips between arms, p = 0.31 / 0.46** | **2026-08-13** |
| **fusion at a wide tier** | **HELPS, and more than at a narrow one: +1.84 pp** | **2026-08-13** |
| **"1,712 more tracks are fetchable"** | **FALSE — 193 in-tier, and the metadata is exhausted** | **2026-08-13** |

### 2c. The numbers that matter, all source-disjoint

**The exported model** (`models/raga_v4_*`, `min_tracks = 10`, 54 classes,
fused): **top-1 59.2% [55.0, 64.1], top-3 72.8%, repertoire coverage 79.2%,
46.86 expected correct raga identifications per 100 heard concert items.**

Expected hits by tier, all fused, all level (c) — this is the product number and
it is monotone:

| tier | classes | top-1 | top-3 | coverage | **exp hits / 100** |
|---|---|---|---|---|---|
| `min>=25` | 18 | 73.6% | 83.6% | 39.1% | 28.75 |
| `min>=20` | 32 | 65.6% | 76.3% | 59.6% | 39.12 |
| **`min>=10`** | **54** | **59.2%** | **72.8%** | **79.2%** | **46.86** |

**Field (the only real-world number this project has):** 16/27 = **59.3% top-1
[40.7, 75.5]** on expert-audited wild clips of median length 60.0 s, 18-class
tier, `raga_v3`. Chance floor 5.6%, best-constant floor 17.2% — the CI excludes
both. **This has not been re-measured against the 54-class model.**

**Wild audio costs approximately nothing.** 59.3% wild against 60.4% clean at
matched 60 s duration and matched tier. `data/RAGA_DOMAIN_DECOMPOSITION.md`
measured field-realistic degradation at **7.5 pp** (phone +0.4, room +2.1, pink
noise +2.7, each CI touching or crossing zero). **The whole gap between "72.2% on
full tracks" and "59.3% in the wild" is DURATION, not domain.**

**Duration curve** (18-class tier, TDMS-only): 52.5% @30s → **60.4% @60s** →
63.8% @120s → **68.8% @300s** → 71.0% @600s → 72.2% full. Knee in (120 s, 300 s].
Top-3 decays far more gently: 84.0% full → 77.1% @60s.

**Within-class learning curve** (confound-free, each class against itself, 3
seeds), on the 18 classes spanning the range:

| cap (tracks/class) | 10 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|
| top-1 | 50.4% | 57.8% | 64.1% | 66.5% | **68.7%** |

**+18.4 pp, no saturation anywhere**; the last 68 tracks bought as much per track
as the first 239. **This lever is real and it is now supply-constrained** — see
§2f.

### 2c-i. Which numbers are inflated and must not be quoted

The level-(a) → level-(c) penalty is **tier-dependent**: 0.6 pp at 18 classes but
**3.5 / 3.5 / 4.7 pp** at 32 / 44 / 54. **Any raga figure at `min_tracks >= 20`
or wider measured at level (a) is inflated.**

The two places that carried such a figure — `train_raga_v3_tdms.py`'s docstring
and `models/raga_v3_meta.json`'s `cv_note`, both quoting `min>=20 67.6/79.4` —
**were repaired on 2026-08-13**. Both now carry source-disjoint fused numbers
keyed by tier, and a tier off the measured grid gets **no** figure rather than a
borrowed one.

**A second, smaller correction, new today.** There are two harnesses and they
carry a different number of rows per track — one row (`raga_audit_levels`, the
coverage curve) versus three (`raga_audit_protocol`, the fused arm). Replication
is worth about **+0.35 pp** and grows with tier width (+1 track at 18 classes, +3
at 32, +4 at 54). **That is the noise floor of this whole audit series**, and any
delta under half a point should be read against it. Deduplicating the fused
harness reproduces the coverage curve's integers exactly — 649/1139 and 812/1139
— so the harnesses do not disagree about anything.

### 2d. Model, features, and what "fused" means

- **Exported and current: `models/raga_v4_*`** — `raga_v4_tdms_rf.pkl`,
  `raga_v4_hist_rf.pkl`, `raga_v4_label_encoder.pkl`, `raga_v4_meta.json`.
  54 classes, `min_tracks = 10`, fused. The two forests are **gitignored**
  (1.2 GB) and regenerate in ~7 min via
  `venv/bin/python train_raga_v3_tdms.py --min-tracks 10 --out-prefix raga_v4`.
- **`models/raga_v3_*` is deliberately untouched** — 32 classes. The wild,
  duration and domain measurements all scored against it and overwriting it
  would invalidate their provenance. Numbers quoted from those docs are v3
  numbers.
- **TDMS** = time-delayed melody surface: 40×40 octave-folded pitch-class
  transition surfaces at τ = 0.1/0.15/0.25 s, gaussian-smoothed (σ 1, wrap),
  power-compressed (α 0.75), L1-normalised, on the FULL-track melody, tonic-
  normalised. Melody from essentia `PredominantPitchMelodia` on the mix for
  archive tracks; annotated vocal pitch for Saraga.
- **Fusion**: `P = 0.6 * P_tdms + 0.4 * P_hist`, where `P_hist` is the production
  480-dim tonic-normalised pitch histogram (65 s Demucs+pyin slices). **Fusion
  is now measured at three tiers and its advantage grows with tier width**:
  +1.16 pp at 18 classes, +1.21 at 32, **+1.84 at 54** (McNemar exact
  p = 0.0011). It is not optional and it is not free — it doubles the forests and
  drags the Demucs+pyin front end into inference.
- Classifier: `RandomForestClassifier(800, max_features='sqrt', random_state=42)`.
- CV: `StratifiedGroupKFold(5, shuffle=True, random_state=42)` on level-(c)
  source groups.

### 2e. Data inventory, counted 2026-08-13

- `data/raga_v2_cache/{saraga_v3,archive_v3}/*.npz` — **1,297 tracks, 88 distinct
  ragas** (89 label strings; `Ābhōgī`/`Ābhōgi` is a duplicate spelling).
- `data/raga_v2_cache/melodia_full/` — 1,232 full-track contours.
- `data/concert_audio/` — 1,238 audio files, 85 raga dirs, **13 GB**.
- `data/scraped_compositions.json` — 3,698 programme items, **3,009 with a
  canonical raga**. This is the repertoire prior coverage is computed against.
- `~/sung_tests` — 108 files, 106 audio, 81 with a real raga label. The short-clip
  wild set. **Its composition is load-bearing for six committed measurements.**
- **`data/long_concerts/audio/` — 11 concerts, 9.85 h, 851 MB, frozen, gitignored,
  UNLABELLED.** New today. See §5.1.

### 2f. Reachable audio — the number that changed today

`data/RAGA_FETCH_RECOUNT.md`. Done entirely offline against the metadata cache,
then bounded by running both fetchers to exhaustion.

| quantity | value |
|---|---|
| mp3 files in cached archive.org metadata | 6,692 |
| **reachable NEW (raga, title) pairs** | **378** |
| — in the 54-class tier | **193** |
| — off-tier (would add *new* classes) | **185** |
| the old "optimistic ceiling" | 1,712 |
| **realised fraction** | **11%** |

**Ten of 54 classes have ZERO reachable audio; 41 of 54 have fewer than five;
only 4 have ten or more.** The top two classes hold 25% of it and the bottom 27
hold 10%.

**The metadata is exhausted.** All 258 previously-uncached identifiers were
fetched and returned **zero** mp3s. There is no cheaper step that changes this
short of adding a genuinely new source.

**Calibration, so the count can be trusted:** the same pass predicts 1,291 files
already on disk against 1,238 actually there — within 4.3%.

### 2g. Tests

**`126 passed, 1 xfailed`** (was 103 + 1 before today's 23 new alias tests):

```
venv_train/bin/python -m pytest tests/test_clip_policy.py tests/test_registry_junk.py \
    tests/test_negative_arm.py tests/test_raga_aliases.py -q
```

**NEVER run bare `pytest tests/`** — six legacy files import a `carnatify`
package that does not exist and fail at collection.

---

## 3. Files actively being edited

**Nothing is mid-edit. No agent is running.** Working tree at handoff time:

```
 M .claude/settings.local.json          (harness noise, not project state)
?? data/raga_coverage/matrix.npz        (~50 MB, regenerable, deliberately UNcommitted)
?? data/long_concerts/labels_validation.json  (regenerated by --validate; harmless)
```

**Frozen and must stay frozen:** `data/raga_wild/FROZEN_CLIPS.json`,
`data/long_concerts/FROZEN_CONCERTS.json`, and the committed measurement records
`data/raga_audit/`, `data/raga_duration/`, `data/raga_domain/`,
`data/raga_coverage/`, `data/raga_tier/` — append, never rewrite.

**`data/raga_aliases.json` was edited today** (ten wrongly-merged keys → `null`)
after the tier work was decided, which was the required ordering.
`data/scraped_compositions.json` was **deliberately not regenerated**, so the map
and the materialised `raga_canonical` field disagree by 20 items. Re-deriving is
a separate dated step and its only measured effect is coverage 79.196% → 79.224%.

**Deepti works in this repo from a separate terminal.** Use targeted
`git add <path>`. **Never `git add -A`.**

---

## 4. What has been tried and failed

`HANDOFF_CLIP_ID.md` §5 is the master graveyard. **Do not re-fund any of these.**

1. **Lyrics-ASR composition ID.** No precision operating point at any threshold
   (≤31%). Whisper `large-v3-turbo`, Indic variants, Demucs stems, all of it.
2. **Sung-Carnatic ASR fine-tune.** Went *backwards*: 8/78 → 0-1/78.
3. **Melodic CSI via CoverHunter.** Source-disjoint mAP 0.113 against a 0.031
   chance floor. Eleven bugs found and fixed on the way; full log in
   `HANDOFF_SESSION_0719B.md`. The training ran; the result was still NO-GO.
4. **More audio duration for the lyrics channel.** KILL: top-5 went *down*.
5. **Qmax composition matching.** The "60-67% top-1" headline was
   **contamination** — 34 of 36 top-1 hits were byte-identical copies of the
   query. Source-disjoint it is **9.5%**.
6. **The rendition corpus.** Confirmed do-not-fund. 73 usable works, 13 with
   verifiable artist diversity.
7. **Tonic estimation / shruti-from-the-listener.** Perfect tonic recovery buys
   **2.2 pp** in the field cell. Contour beats tonic 3:1. **Do not fund.**
8. **`augment_wild.py` as a domain simulator.** Its ±6 semitone pitch shift and
   0.8-1.25× time stretch dominate the damage and simulate nothing real. **Use
   `field_all`.**
9. **Per-class admission thresholds.** Expected hits fall monotonically:
   45.1 → 43.6 → 42.8 → 42.1 → 39.6. No threshold beats admitting everything.
10. **The narrow version of admission — dropping the stably-dead classes — also
    loses.** *New today, and it closes the last live remnant of this idea.*
    `data/RAGA_COVERAGE_CURVE.md` §11.4 had preserved a defensible narrow
    version: drop the three classes never admitted in any fold (Nāṭakurinji,
    Janaranjani, Haṁsānandi). Priced properly it does not pay. The second-order
    help to the surviving 51 is **+0.73 pp in the TDMS arm and −0.55 pp in the
    fused arm** — the sign flips between two arms of the same model on the same
    folds — and neither direction is significant (McNemar p = 0.31, p = 0.46). On
    expected hits: fused **46.10 against 46.86**. **All 54 classes are admitted.**
11. **"Raise the fetch target above 30" as a broad top-up.** *New today.* Not
    refuted in principle — the within-class curve still says +18.4 pp — but **not
    executable**: only 4 of 54 classes have ten or more reachable recordings and
    ten have none (§2f).

### Predictions written down in advance and then refuted

Keeping these because the habit is why this project's numbers are trustworthy.

- **"`phone_mic`'s high-pass will strip the fundamental."** Refuted — **zero**
  no-contour failures in all 517 windows.
- **"The 72.8 CV harness was never committed."** Wrong. `-S` over source is a
  test for a literal, not for a capability.
- **"The source-disjointness penalty won't explode at a wider tier."** Refuted —
  4.7 pp at 54 classes.
- **"More audio per class is weakly contradicted (r = 0.066)."** Refuted; that r
  was range-restricted.
- **"The within-class curve will be flatter, +6 to +12 pp."** Refuted — **+18.4**.
- **"The coverage/accuracy trade will peak in the middle."** Refuted — it peaks
  at the widest tier measured.
- **"Ārabhi is an alias bug."** Refuted — it is absent from the vocabulary
  entirely. A missing raga, not a missing spelling.
- **"The null alias bucket is junk."** Refuted — 81.4% are recoverable ragas.
- **"Fusion's advantage will shrink or reverse at a wide tier; band [−2.0, +1.4]
  pp."** *New today.* **Refuted at +1.84 pp, p = 0.0011** — and refuted as a
  *trend*, not a point: fusion helps more at every wider tier (+1.16 / +1.21 /
  +1.84). The stated mechanism was backwards; fusion's biggest gains are
  Hindōḷaṁ +12.5 pp and Śrīranjani +9.5 pp, exactly the gamaka-and-phrase classes
  I predicted the marginal pitch histogram would be useless on.
- **"Gate 2 will pass."** *New today.* Refuted — and the registered contingency
  ("that disagreement is a more important finding than anything else in this
  job") is what actually happened. See §2c-i.

### Three errors of process worth not repeating

- **Two workhorses died on session limits mid-run.** Both recoverable *only*
  because their briefs demanded partial results on disk and prereg-before-score.
  **Keep demanding both.**
- **The verifier must not take the workhorse at face value.** On 2026-08-13 a
  workhorse reported r = −0.777 between a class's accuracy and what more data
  buys it and concluded the fetch should be *targeted at weak classes*. The
  correlation reproduces; **the inference is regression to the mean**, because
  `gain = acc@30 − acc@10` carries `acc@10` on both sides. Regressed on the
  noise-free endpoint the signal vanishes. **Fetch broadly, not targeted.**
- **The verifier must not take *itself* at face value either.** *New today.* The
  fetch recount initially found reachable-audio-versus-gain at Spearman −0.531,
  p = 0.023, and reachable-versus-accuracy@10 at r = +0.556, p = 0.017 — and I
  nearly published "the audio that exists is the audio that buys least" on that.
  It is **the same trap**, one step removed. On `acc@30` it falls to p = 0.10 and
  is not significant. The published finding is the *concentration* (10 classes at
  zero, 41 under five), which is set-membership arithmetic with no model in it.

---

## 5. The next step

Items 1 and 2 are the live ones. **Item 2 is the top unblocked engineering job.**

1. **Measure the 11 long-form concerts. BLOCKED ON DEEPTI'S LABELS.**
   Still the only unmeasured cell in the product case: every wild clip on disk is
   43-85 s, the concert-companion thesis rests on 10-30 minute items, and that
   region has never been tested on *wild* audio.

   **Done today:** the audio has a home at `data/long_concerts/audio/`
   (gitignored) and is **frozen** at `data/long_concerts/FROZEN_CONCERTS.json` —
   per-file sha256, byte length, ffprobe duration, committed before any scoring
   harness or preregistration exists. All eleven are byte-identical to their
   `~/Downloads` copies and every duration reproduces the conversion table.
   `scripts/long_concert_freeze.py --verify` re-checks and exits non-zero on any
   mismatch.

   **What is needed:** Deepti fills `data/long_concerts/LABELS.tsv` — one row per
   item: concert, start time, raga. The item ends where the next starts, so no
   end times are typed. `scripts/long_concert_labels.py --validate` checks it
   with no model in the loop and reports, never summed together: items excluded
   as `ragamalika`/`unsure`, items whose raga **is** in the corpus vocabulary,
   and items whose raga is **not** — that last count is the **out-of-vocabulary
   rate measured on concerts a real listener attended**, which is worth as much
   as the accuracy number given §2a.

   **Deliberately not done:** no preregistration, no harness, no prediction. The
   prereg must fix the model, the windowing and the read-outs and be committed
   before the harness. It was correct to wait: the tier moved today, so a prereg
   written this morning would have registered a model that no longer exists.
   **Write it once the labels are in, against `raga_v4`.**

2. **Build the abstain gate, with a genuinely held-out set. THE TOP UNBLOCKED
   JOB.** It got more valuable today, not less: a 54-class model that speaks
   about 79% of the repertoire needs to know when to shut up, and §4.9/§4.10 just
   established that **the tier is the wrong place to buy that safety** — it buys
   it only by refusing to answer on 61% of the repertoire, silently and
   unconditionally, including on the classes it would have got right.

   The wild failures are bimodal: on the 27 audited clips the miss ranks are
   `[2, 2, 2, 4, 5, 5, 21, 22, 25, 28, 30]` out of 32 — six near-misses and
   **five catastrophes**, including `vAtApi gaNapathim` (Hamsadhvāni, the most
   famous concert opener in the repertoire) at rank 25. Thresholding fused top-1
   probability at p ≥ 0.20 fires on 63% of clips at 76.5% top-1 and drops four of
   five catastrophes. **That threshold was chosen by reading the table on the
   same 27 clips it is scored on — it is a hypothesis, not a result**, and the
   admission experiment measured exactly this class of inflation at **4.4 pp**.
   Fit it on data the score never sees; the nested pattern in
   `scripts/raga_coverage_admission.py` is the template. What this axis buys is
   **precision, not hits** (57.0% → 63.8% accuracy-when-it-speaks at 79.2% →
   62.2% coverage).

3. **Build what Jon actually asked for.** Raga name + raga character + sahitya
   meaning, on long-form audio, with abstention as the guard against lying. Half
   his question needs no ASR, no CSI, no Qmax, and has never been attempted.
   **Do not start with composition ID.**

4. **Re-measure the field against `raga_v4`.** The 59.3% wild number is
   18-class `raga_v3`. The 54-class model puts far more wild clips in scope
   (62.1% of labelled `~/sung_tests` clips against 28.2%) and **nothing says what
   its field accuracy on them would be.** Cheap: the harness is
   `scripts/raga_wild_*.py` and the clip set is frozen. **Do not touch
   `FROZEN_CLIPS.json`.**

5. **Measure the tier × duration interaction.** The duration curve is 18-class;
   the model is now 54-class. A companion working on minute-scale audio at 54
   classes has **no measurement at all** in this repo. This is the largest hole
   left in the raga case and item 1 would close much of it.

6. **The fetch, re-scoped.** §2f killed the broad top-up. What survives:
   **185 off-tier pairs attach to ragas *below* `min_tracks = 10`** — classes the
   model cannot name at all today. Given that the thesis is a vocabulary
   constraint, that is a **vocabulary lever, not a depth lever**, and whether it
   brings any class over the line is unmeasured and cheap to check offline.
   Do that before fetching anything.

7. **Only then, features.** No feature work is justified while the model cannot
   name 40-60% of what it hears.

Also open, unowned, cheap: `vAtApi gaNapathim__Hamsadhvāni` at rank 25 of 32 is
not a near-miss-shaped failure — something specific went wrong on **one clip**.
And **catalog restriction** in `load_targets` remains the one untested cheap
lever on the lyrics side; deprioritised five times, still not in the graveyard,
honest expectation is precision up and recall flat.

---

## 6. Pending Deepti — do not decide these for her

1. **Push the branch / open a PR.** ~53 commits, none pushed. Pushes and deploys
   are always hers.
2. **Label the 11 long concerts** — `data/long_concerts/LABELS.tsv`. **Nothing in
   §5.1 can be scored without this**, and it is the only unmeasured cell in the
   product case. Partial is fine and useful.
3. **Delete the source `.mp4`/`.MOV` files in `~/Downloads`** (8.1 GB). The
   mp3s are verified byte-identical to the copies now in the repo, so the
   `~/Downloads` mp3s are redundant too. Nothing here deletes a source.
4. **Wire `raga_v4` into the product?** It is a candidate only.
   `identify_clip.py` is untouched and has zero diff against `main`. Wiring it
   changes 32 classes to 54 and requires the fused front end.
5. **`'garuDadhwani' -> 'Śuddadhanyāsi'` in `data/raga_aliases.json`.** Looks like
   the same class of wrong merge as the ten repaired today and its sibling
   `garuDadwani` is `null`, but unlike them it asserts a *specific different
   raga* rather than being a typo of an already-null name, so repairing it is a
   musical claim. A test pins its current value so it cannot be closed silently.
6. **One raga-equivalence ruling still open:** Udayaravicandrika /
   Śuddhadhanyāsi. No threshold consequence, so nothing is blocked.
7. **Nine low-confidence rows, one low-confidence variant and two ambiguous
   rows** in `data/raga_aliases_audit.json` (filter `"confidence": "low"`).
8. **Hindustani imports as product policy**, not musical fact: 31 items
   (Bhīmpalās 8, Durgā 6, Gauḍ Malhār 3, …), all attached to Carnatic artists on
   Carnatic-vocal concert pages. Does "concert companion" cover every item on a
   programme, or only core elaborated Carnatic ragas?
9. **Back up `asr_cache_fullhistory/`** — local-only and gitignored. If deleted,
   `DEVICE_MAP.md` becomes unfalsifiable.
10. **Wire the registry junk blocklist** (a load-time merge in `load_targets`).
11. **Do NOT fund:** the rendition corpus, tonic-estimation work, prospective long
    OOC audio, the 28-clip short-OOC sentinel, or anything on the composition
    path.

---

## 7. Guardrails — the discipline that produced these results

This is the part to copy, not the numbers.

- **Preregister, and commit the prereg as its own commit before the scoring
  harness exists.** Every audit in this series did it, including today's tier
  job (`eb1278d` before `a7eb0dc`).
- **Gate on reproducing the historical number first, on the exact integer
  counts** — and prefer the *strong* form: the tier job's Gate 1 required
  `git diff` on `data/raga_audit/results.json` to come back empty, and the entire
  diff was four `fit_seconds` lines. That proves the parameterisation is
  behaviour-preserving, not merely number-preserving.
- **When a gate fails, stop and diagnose it.** Today's Gate 2 failed by 4 tracks.
  Chasing it produced exact agreement between two harnesses *and* a measured
  noise floor for the whole series. Register in advance what a gate failure
  means, so the temptation to wave it through never arises.
- **Fix the interpretation table in the brief before the number exists**, and fix
  the tie-break too. Today's tier decision was a near-tie and the rule "ties go
  to admitting everything" had been written down first.
- **Write predictions down so they can be refuted.** Ten have been, this month;
  two of the four registered today were wrong.
- **Separate "produced no output" from "produced a wrong output"** and never sum
  them into one percentage.
- **The verifier re-derives every headline with its own code, and distrusts its
  own findings as hard as a workhorse's.** It has now caught regression to the
  mean twice — once in a workhorse's inference and once in its own.
- **Coverage × accuracy, not accuracy.** A companion right 72.8% of the time
  about 39.1% of what it hears is worse than one right 59.2% of the time about
  79.2% of it.
- **Selection on the folds you then score on inflates by ~4.4 pp.** Measured, not
  assumed. Nested selection or an explicit "optimistic bound" label.
- **A named list is not a threshold.** Dropping three classes by name after the
  tier rule is auditable; a threshold sweep is a tuning knob and it is dead.

---

## 8. Environment facts worth not rediscovering

- **`venv_train`** py3.11 — demucs, essentia, whisper, rapidfuzz, **pytest**.
  **`venv`** py3.14 — sklearn, librosa, mirdata, scipy, **no pytest**.
  essentia must run in `venv_train`, **fork not spawn**.
- **Never run bare `pytest tests/`.** Run the four named files (§2g).
- **ffmpeg 8.1.2 IS installed** at `/opt/homebrew/bin/ffmpeg`. The "no local
  ffmpeg" lines in `ARCHITECTURE.md`, `HANDOFF_CLIP_ID.md` §3 and
  `augment_wild.py:21` are **stale**.
- `codex` CLI 0.145.0. Non-interactive:
  `codex exec --sandbox workspace-write --skip-git-repo-check "<prompt>"`.
  Give it a brief on disk and tell it to read the brief.
- **Zsh eats `"` inside `git commit -m`.** Use `git commit -F -` with a heredoc.
  Zsh also fails on unmatched globs — quote or guard them.
- **Logs are gitignored** (`*.log`). The series tracks them anyway; use
  `git add -f data/<dir>/*.log`.
- `data/raga_aliases.json`: 958 keys → **284 null** (was 274 before today's
  repair). **Never trust registry `ragas` metadata without it, and never trust it
  without `data/raga_aliases_audit.json`.**
- The composition registry contains junk rows — addresses and dates parsed as
  compositions.
- Melodia runs **~13× realtime**; ~400 s per domain cell at 5 workers.
- The fused 2×2 at 54 classes is **~90 s per tier** on this machine. Cheap. The
  matrix build is the slow part and it is cached at
  `data/raga_coverage/matrix.npz` and `data/raga_audit/tdms_cache.npz`.
- **Billing:** a 30-day no-billing window is in force. Submits gated on
  `CARNATIFY_BILLING_OK=1`. No GEMINI key locally. archive.org is free; Colab
  Pro T4 has been used for GPU work.
- **Production deploys are Deepti-run** — the permission classifier blocks them
  from an agent seat. Never keep the Space mirror in `/tmp`.
- **Synth clips must never enter `~/sung_tests`.** Its purity is load-bearing.

### The agent roster and how seats collaborate

- **Verifier seat** (Opus 5) — owns briefs, prereg discipline, re-derivation of
  every headline. Does not take a workhorse at face value, or itself.
- **Workhorse seats** (Opus 5, GPT-5.6 / codex) — execute a brief on disk.
- Seats collaborate **only through files on disk and `AGENT_LOG.md`**, never
  through chat.
- Deepti also launches workhorses by hand in a separate terminal. **Assume
  concurrent repo work at all times.**
- Briefs must demand: prereg-before-score, partial results to disk after every
  cell, targeted `git add`, an `AGENT_LOG.md` entry naming refuted predictions,
  and an explicit list of paths the seat must not touch.

---

## 9. The one-line version, if you read nothing else

**The composition path is dead. The raga model was graduated today to 54 classes,
fused, and exported as `models/raga_v4_*` — 46.86 expected correct answers per
100 concert items against 39.12 for the tier the product ships, source-disjoint,
from a retrain on data already on disk. The free lever is now spent: the second
lever, more audio per class, is real (+18.4 pp, no saturation) but the audio does
not exist — 193 reachable tracks in the tier, not 1,712, and the metadata is
exhausted. So the two live jobs are the abstain gate, which is what actually buys
safety, and the eleven long-form concerts, which are frozen and waiting only on
Deepti's labels and are still the only unmeasured cell in the product case.**
