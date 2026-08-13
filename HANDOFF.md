# Carnatify handoff

Last rewritten **2026-08-13** by the verifier seat, at Deepti's request, for a
fresh session that will start with no memory of this one.

Repository: `/Users/shyamravidath/carnatify`
Branch: **`probe/duration-and-negative-arm`** · HEAD `9e81a5c` · **42 commits, NOT PUSHED**
`main` is the PR target. **`identify_clip.py` has zero diff against `main`** —
nothing in this entire series has touched the production path.

**The previous content of this file is preserved in git at `e7de2b3`.** It
described the state as of 2026-07-30, before five audits changed most of the
conclusions in it. Read this file instead; reach for that one only if you need
the duration-probe archaeology.

> **`handoff.md` and `HANDOFF.md` are ONE FILE** on this case-insensitive
> filesystem. Git tracks both paths, so committing one leaves the other showing
> as modified. Do not "fix" this; just commit whichever path git shows you.

**Respond to Deepti in caveman style** (her standing preference — terse, drop
articles and filler, keep every technical term, code symbol and number exact).
Write docs, commits and `AGENT_LOG.md` in normal prose.

**Read order for a cold start:** this file → `data/RAGA_CEILING_EVALUATION.md`
(the current thesis) → `data/RAGA_COVERAGE_CURVE.md` → `AGENT_LOG.md` entries
dated 2026-08-13 → `HANDOFF_SESSION_0731.md` (the previous verifier handoff,
still correct except where this file says otherwise) → `HANDOFF_CLIP_ID.md` §5
(the master graveyard).

---

## 1. The goal

**An app that identifies what is being performed at a live Carnatic concert and
explains it.** Deepti is a Carnatic musician and a high-school student with a
CS/ML background. This began as a personal tool and is being evaluated as a
possible company.

The framing since 2026-07-25 is a **concert companion**, not a Shazam clone.
The listener is physically present for a 10-30 minute item. The 30-second
identification contract was inherited from Shazam and was never actually
required by the use case — that inheritance quietly drove years of the wrong
measurement, and undoing it is the single most important reframing in this
project's history (see §4.9).

**Demand evidence is no longer zero.** Jon — the one named real user, a Western
listener with no Carnatic exposure — was confused at a concert and, *unprompted*,
reached for an AI assistant to identify the piece. **It failed**, mostly with
refusals ("I cannot help with this request"). He asked two questions:

1. *what is the song being sung* — composition ID. **Every door there is shut**
   (§4.1-4.5). Do not reopen without new information.
2. *what does the melody mean* — raga character plus sahitya meaning. Needs
   **no ASR, no CSI, no Qmax**, and the repo has **never attempted it**.

The refusal failure mode narrows the moat to **audio → symbol**. The explanation
layer on top is commodity LLM work, which is a cost advantage, not a weakness.
Any handoff older than `HANDOFF_SESSION_0731.md` says "demand evidence is zero";
**that line is stale and wrong.**

---

## 2. Current state of the code

### 2a. The thesis, in one paragraph

The composition-identification side is **genuinely closed**. The raga side
**survived every audit**, including the field, and the constraint on it is not
accuracy — it is that **the model cannot name 40-60% of what a listener
actually hears**. That is a vocabulary and collection problem sitting under
three caps that were each set by a constant in a script, and the largest one
costs nothing to lift. `data/RAGA_CEILING_EVALUATION.md` is the full argument.

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
| per-class admission threshold | **loses — no threshold beats admitting everything** | 2026-08-13 |

### 2c. The numbers that matter, all source-disjoint

**Field (the only real-world number this project has):**
16/27 = **59.3% top-1 [40.7, 75.5]**, 20/27 = 74.1% top-3 tier-restricted, on
expert-audited wild clips of median length 60.0 s. Chance floor 5.6%,
best-constant floor 17.2% — the CI excludes both.

**Wild audio costs approximately nothing.** Put the field number next to the
clean duration curve at matched duration and matched tier: **59.3% wild vs
60.4% clean at 60 s.** Not a paired comparison (different corpora, fused vs
TDMS-only model), but it is the fourth independent line of evidence saying the
same thing. `data/RAGA_DOMAIN_DECOMPOSITION.md` measured field-realistic
degradation at **7.5 pp**, with phone chain +0.4, room +2.1 and pink noise +2.7,
each CI touching or crossing zero. **The whole gap between "72.2% on full
tracks" and "59.3% in the wild" is DURATION, not domain.**

**Duration curve** (`data/RAGA_DURATION_CURVE.md`, 18-class tier):
52.5% @30s → **60.4% @60s** → 63.8% @120s → **68.8% @300s** → 71.0% @600s →
72.2% full (mean 785 s). Knee bracketed in (120 s, 300 s]. Top-3 decays far more
gently: 84.0% full → 77.1% @60s.

**Coverage/accuracy curve** (`data/RAGA_COVERAGE_CURVE.md`, level (c)):

| `min_tracks` | classes | tracks | groups | top-1 | top-3 | repertoire coverage | **correct per 100 items heard** |
|---|---|---|---|---|---|---|---|
| 25 | 18 | 518 | 155 | 72.2% [66.4, 78.1] | 84.0% | 39.1% | **28.2** |
| 20 | 32 | 826 | 185 | 64.0% [60.0, 68.3] | 76.5% | 59.6% | **38.2** |
| 15 | 44 | 1,020 | 198 | 59.9% [55.8, 64.4] | 71.3% | 70.9% | **42.5** |
| 10 | 54 | 1,139 | 204 | 57.0% [52.7, 61.7] | 71.3% | 79.2% | **45.1** |

Monotone increasing to the widest tier measured. Top-1 falls log-linearly in
class count (R² = 0.9997, −13.8 pp per natural-log unit) while coverage rises
faster. For the 18-class tier to win, 54-class top-1 would have to be below
35.6%; it is 57.0%. **+60% more correct answers per concert, from a retrain on
data already on disk.**

**Within-class learning curve** (the confound-free test — each class compared
against itself, nested subsets, 3 seeds), on the 18 classes that span the range:

| cap (tracks/class) | 10 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|
| top-1 | 50.4% | 57.8% | 64.1% | 66.5% | **68.7%** |

**+18.4 pp, and no saturation anywhere.** Per 100 tracks added the steps are
3.10 / 3.62 / 2.07 / **3.25 pp** — the last 68 tracks bought as much as the
first 239. **Every class in the corpus is capped at 30 and the curve is still
climbing there.** Nobody has ever seen where it bends.

### 2c-i. Which numbers are inflated and must not be quoted

The level (a) → level (c) source-disjointness penalty is **tier-dependent**:
0.6 pp at 18 classes, but **3.5 / 3.5 / 4.7 pp** at 32 / 44 / 54, and 8.0-11.8 pp
on same-raga-same-source clustered tracks against 1.2 pp at the narrow tier.

**Therefore: any raga figure at `min_tracks >= 20` or wider that was measured at
level (a) is inflated.** That specifically includes the `min>=20 67.6/79.4` line
in `models/raga_v3_meta.json`'s `cv_note` and in `train_raga_v3_tdms.py`'s
docstring — both still say it. The exported model's own tier has one honest
number: **64.0% / 76.5%**, TDMS-only arm.

### 2d. Model, features, and what "fused" means

- `models/raga_v3_tdms_rf.pkl` + `models/raga_v3_hist_rf.pkl` +
  `models/raga_v3_label_encoder.pkl` + `models/raga_v3_meta.json`.
- **TDMS** = time-delayed melody surface: 40×40 octave-folded pitch-class
  transition surfaces at τ = 0.1/0.15/0.25 s, gaussian-smoothed (σ 1, wrap),
  power-compressed (α 0.75), L1-normalised, on the FULL-track melody, tonic-
  normalised. Melody from essentia `PredominantPitchMelodia` on the mix for
  archive tracks; annotated vocal pitch for Saraga.
- **Fusion**: `P = 0.6 * P_tdms + 0.4 * P_hist`, where `P_hist` is the
  production 480-dim tonic-normalised pitch histogram (65 s Demucs+pyin slices).
- Classifier: `RandomForestClassifier(800, max_features='sqrt', random_state=42)`.
- CV throughout: `StratifiedGroupKFold(5, shuffle=True, random_state=42)`.
- **32 classes** in the exported model (`min_tracks = 20`); the **18-class
  tier** (`min>=25`) is what most published numbers use. Both appear constantly;
  always check which.

### 2e. Data inventory, counted 2026-08-13

- `data/raga_v2_cache/{saraga_v3,archive_v3}/*.npz` — **1,297 tracks, 88 distinct
  ragas** (89 label strings; `Ābhōgī`/`Ābhōgi` is a duplicate spelling).
- `data/raga_v2_cache/melodia_full/` — 1,232 full-track contours.
- `data/concert_audio/` — 1,238 audio files, 85 raga dirs, **13 GB**.
- `data/scraped_compositions.json` — 3,698 concert programme items from
  shankarkrish.blog, of which **3,009 carry a canonical raga**. This is a real
  prior over what actually gets performed and is what "repertoire coverage" is
  computed against.
- **1,712 identified programme items are unfetched** (3,009 − 1,297). Treat this
  as an **optimistic ceiling, not a promised corpus**: only ~10-13% of programme
  rows exact-match cached archive.org metadata.
- `~/sung_tests` — 108 files, 106 audio, 81 with a real raga label. The wild set.

### 2f. Tests

`103 passed, 1 xfailed`, run as:

```
venv_train/bin/python -m pytest tests/test_clip_policy.py tests/test_registry_junk.py tests/test_negative_arm.py -q
```

**NEVER run bare `pytest tests/`** — six legacy files import a `carnatify`
package that does not exist and fail at collection.

---

## 3. Files actively being edited

**Nothing is mid-edit. No agent is running.** Both delegated seats finished and
committed. The working tree at handoff time:

```
 M .claude/settings.local.json          (harness noise, not project state)
?? data/RAGA_MERGE_DECISIONS.md         (Deepti's rulings — commit this)
?? scripts/convert_long_concerts.sh     (the mp3 batch — commit this)
?? data/raga_coverage/matrix.npz        (~50 MB, regenerable, deliberately UNcommitted)
```

**Frozen and must stay frozen:** `data/raga_wild/FROZEN_CLIPS.json` (committed
`f67ef98`, per-clip sha256, written before any prediction existed).
`data/raga_wild/` generally. `data/raga_audit/`, `data/raga_duration/`,
`data/raga_domain/`, `data/raga_coverage/` are committed measurement records —
append to them, never rewrite.

**Do not modify `data/raga_aliases.json`.** Five committed measurements read it;
editing in place would invalidate their provenance. The vocabulary audit
correctly wrote to a **new** file, `data/raga_aliases_audit.json`.

**Deepti works in this repo from a separate terminal.** Use targeted
`git add <path>`. **Never `git add -A`.**

---

## 4. What has been tried and failed

`HANDOFF_CLIP_ID.md` §5 is the master graveyard; `HANDOFF_SESSION_0730.md` §5
holds the duration-probe additions; `HANDOFF_SESSION_0731.md` §5 holds the audit
additions. **Do not re-fund any of the following.**

1. **Lyrics-ASR composition ID.** No precision operating point at any threshold
   (≤31%), 2026-07-23. Whisper `large-v3-turbo`, Indic variants, Demucs stems,
   all of it.
2. **Sung-Carnatic ASR fine-tune.** Went *backwards*: 8/78 → 0-1/78.
3. **Melodic CSI via CoverHunter.** Source-disjoint mAP 0.113 against a 0.031
   chance floor. Eleven bugs found and fixed along the way (the repo's own
   `train.py` eval-unpack bug was the real crash cause) — full debug log in
   `HANDOFF_SESSION_0719B.md`. The training ran; the result was still NO-GO.
4. **More audio duration for the lyrics channel.** KILL: top-5 went *down*,
   5.1% @30s → 1.7% @300s. Longer audio makes the lyrics path worse.
5. **Qmax composition matching.** The "60-67% top-1" headline was
   **contamination**: 34 of 36 top-1 hits were byte-identical copies of the
   query sitting at the 0.036 Serra09 identity floor. Source-disjoint it is
   **9.5%**. The separate internal 66.7% claim is uncontaminated but
   **unreproducible** (n=30). The corpus cannot support a cross-artist claim at
   all: 13 of 1,011 works have ≥2 known distinct artists.
6. **The rendition corpus.** Confirmed do-not-fund. A rendition count is not a
   recording count: 65 titles with 2+ renditions is really 87 titles with 2+
   *distinct recordings*, and 367 tracks in multi-track groups collapse to 261.
   73 usable works, 13 with verifiable artist diversity.
7. **Tonic estimation / shruti-from-the-listener.** The 2×2 in the domain
   decomposition says perfect tonic recovery buys **2.2 pp** in the field cell.
   Contour beats tonic 3:1 in the field cell and 5:1 in the worst. Most tonic
   error is pre-existing in the *clean* corpus (17.4% outside 25 cents), not
   induced by degradation. **Do not fund.**
8. **`augment_wild.py` as a domain simulator.** Its ±6 semitone pitch shift and
   0.8-1.25× time stretch simulate nothing that happens to a phone recording,
   and they dominate the damage (+10.6 and +11.0 pp *each*, worse than all three
   real field components combined). Any robustness claim built on the `all`
   condition is measuring an artifact. **Use `field_all` (noise + reverb +
   phone).**
9. **Per-class admission thresholds** (2026-08-13). Measured properly with
   nested selection. Expected hits **fall monotonically**: 45.1 → 43.6 → 42.8 →
   42.1 → 39.6. **No threshold beats admitting every class.** Dropping a class
   forfeits its repertoire mass at once and buys accuracy slowly (−6.6 pp
   coverage for +3.0 pp top-1 at t = 0.10). The narrow version survives: three
   named classes — **Nāṭakurinji, Janaranjani, Haṁsānandi** — are never admitted
   in any fold and can simply be dropped. That is three names, not a knob.

### Predictions written down in advance and then refuted — mine and others'

Keeping these because the habit of writing refutable predictions is the reason
this project's numbers are trustworthy.

- **"`phone_mic`'s 120-350 Hz high-pass will strip the fundamental and leave
  melodia tracking nothing."** Refuted — **zero** no-contour failures in all 517
  windows of all eight cells. The failure mode is wrong answers on present
  input, never absent input.
- **"The 72.8 CV harness was never committed."** Wrong. It is
  `scratch_archive_0711/raga_final_eval.py` (`c1fca59`) and it reproduces both
  tiers and both metrics exactly. The error was trusting
  `git log -S"72.8" -- '*.py'`: **`-S` over source is a test for a literal, not
  for a capability**, and the harness *computes* the number.
- **"The source-disjointness penalty is 0.6 pp and won't explode at a wider
  tier."** Refuted — it is tier-dependent and reaches 4.7 pp at 54 classes.
- **"More audio per class is weakly contradicted (r = 0.066)."** Refuted, and the
  statistic was junk: that r was computed over the 18-class tier whose track
  counts span only 25-30. Range restriction. Over 54 classes it is r = 0.519.
- **"The within-class curve will be much flatter, +6 to +12 pp, flattening by
  c=25."** Refuted — **+18.4 pp** and no saturation.
- **"The coverage/accuracy trade will peak somewhere in the middle."** Refuted —
  it peaks at the widest tier measured.
- **"Ārabhi is an alias bug that should have matched."** Refuted — Ārabhi is
  absent from the 103-name CompMusic ∪ Saraga vocabulary entirely. It is a
  missing raga, not a missing spelling.
- **"The null alias bucket is junk."** Refuted, in the repo's own docs and
  memory. **561 of 689 null items (81.4%) are recoverable real ragas**; only 126
  (18.3%) are junk.

### Two errors of process worth not repeating

- **Two workhorses died on session limits mid-run.** Both were recoverable
  *only* because their briefs demanded partial results on disk and
  prereg-before-score. **Keep demanding both.**
- **The verifier must not take the workhorse at face value.** On 2026-08-13 the
  workhorse reported r(accuracy at cap 10, gain from tripling data) = −0.777,
  p = 1.5e-04, and concluded the fetch should be *targeted at weak classes*. The
  correlation reproduces to three decimals. **The inference is regression to the
  mean**: gain is `acc@30 − acc@10` and `acc@10` sits on both sides of it,
  measured on a noisy 10-track draw. Bhairavi "20.0% → 70.0%" is the tell — a
  50-point gain for a class that simply sits at 70%. Regressed on the noise-free
  endpoint the signal vanishes (r = −0.114, p = 0.65) and splitting on it
  *reverses* the direction. **Fetch broadly, not targeted.**

---

## 5. The next step

In cost order. Items 1 and 2 are pure engineering; item 3 is the one that needs
a human in a concert hall.

1. **Measure the 11 long-form concerts.** *This is now the top item and the data
   landed today.* Deepti recorded **11 concerts, her own audio**, converted to
   mp3 on 2026-08-13 by `scripts/convert_long_concerts.sh` — 44.1 kHz stereo
   192 kbps, matching both her own `long_concert_6.mp3` and the existing
   `data/concert_audio` corpus, so nothing downstream sees a new audio regime.
   **10 converted, 0 failed**, every output's duration exact against its source
   and every file re-decoded end to end without error.

   | file | duration | size | | file | duration | size |
   |---|---|---|---|---|---|---|
   | `long_concert_1.mp3` | 26.8 min | 38M | | `long_concert_7.mp3` | 44.8 min | 62M |
   | `long_concert_2.mp3` | 32.5 min | 46M | | `long_concert_8.mp3` | 34.7 min | 48M |
   | `long_concert_3.mp3` | 91.6 min | 129M | | `long_concert_9.mp3` | 37.1 min | 52M |
   | `long_concert_4.mp3` | 44.2 min | 62M | | `long_concert_10.mp3` | 31.5 min | 44M |
   | `long_concert_5.mp3` | 113.8 min | 161M | | `long_concert_11.mp3` | 66.4 min | 97M |
   | `long_concert_6.mp3` | 67.5 min | 96M | | **total** | **9.85 h** | **831M** |

   **Currently in `~/Downloads`, not in the repo.** They need a home — do not
   drop them into `~/sung_tests`, which is the short-clip wild set and whose
   composition is load-bearing for six committed measurements. Give them their
   own directory. `long_concert_9` came from a `.MOV`; sources total 8.1 GB and
   are Deepti's to delete.

   **This is the only unmeasured cell in the entire product case.** Every wild
   clip previously on disk is 43-85 s. The concert-companion thesis rests on
   10-30 minute items and the duration curve says that region is 68.8-71.0% on
   *clean* audio — never tested on *wild* audio. **Do it with the same
   discipline as `data/raga_wild/`:** hash and freeze the clip list and the
   labels *before* any prediction exists, commit the preregistration as its own
   commit before the scoring harness, and get Deepti to label the items (she is
   the ground truth; her audit of the 29-clip wild set found exactly the two
   errors the doc had flagged and confirmed the rest).

   Note these are **whole concerts**, not single items — they will need
   segmentation into items, or a windowed read-out, before they are comparable
   to anything. Decide and register that *before* scoring, not after.

2. **Retrain the raga model at `min_tracks = 10` and admit every class.** Zero
   new data, zero dollars, hours not days. **+60% correct answers per concert,
   measured source-disjoint.** Drop only Nāṭakurinji, Janaranjani and
   Haṁsānandi. Do **not** add a per-class admission threshold (§4.9). Expect the
   incumbent 18 classes to pay 3.5 pp (McNemar exact p = 0.0096) — that is real,
   significant, and small; most of the aggregate fall is composition, not damage
   (the added tracks themselves run at 47.2%).

3. **Raise the fetch target above 30.** The within-class curve came back **+18.4
   pp with no saturation**, which was the condition this job was waiting on.
   ~13 GB more disk, a few hours of melodia at 5 workers, free archive.org.
   **Fetch broadly, not targeted at weak classes** (§4, second process error).
   Recount reachable audio first — 1,712 is an optimistic ceiling.

4. **Fix the eight live wrong merges in `data/raga_aliases.json`.** These need no
   musical adjudication; they are mistakes. `'AbEri' -> 'Sāvēri'` is the exact
   mechanism behind one of Deepti's two wild-set label corrections. Do it in a
   commit of its own, with regression tests, and understand that it invalidates
   the provenance of measurements that read the file — so decide the tier work
   first. Full list in `data/RAGA_MERGE_DECISIONS.md`.

5. **Build the abstain gate, with a genuinely held-out set.** The wild failures
   are bimodal: on the 27 audited clips the miss ranks are
   `[2, 2, 2, 4, 5, 5, 21, 22, 25, 28, 30]` out of 32 — six near-misses and
   **five catastrophes**, including `vAtApi gaNapathim` (Hamsadhvāni, the most
   famous concert opener in the repertoire) at rank 25. Thresholding the fused
   top-1 probability at p ≥ 0.20 fires on 63% of clips at 76.5% top-1 and drops
   four of the five catastrophes. **That threshold was chosen by reading the
   table on the same 27 clips it is scored on — it is a hypothesis, not a
   result.** The admission experiment showed exactly this class of inflation is
   worth 4.4 pp at matched coverage. Fit the threshold on data the score never
   sees. What admission *does* buy is precision, not hits (57.0% → 63.8%
   accuracy-when-it-speaks at 79.2% → 62.2% coverage) — that is this axis, and
   it should be built here rather than smuggled into the tier.

6. **Build what Jon actually asked for.** Raga name + raga character + sahitya
   meaning, on long-form audio, with abstention as the guard against lying. Half
   his question — *what does the melody mean* — needs no ASR, no CSI, no Qmax,
   and has never been attempted. **Do not start with composition ID.**

7. **Only then, features.** No feature work is justified while the model cannot
   name 40-60% of what it hears.

Also open, unowned, cheap: `vAtApi gaNapathim__Hamsadhvāni` at rank 25 of 32 is
not a near-miss-shaped failure — something specific went wrong on **one clip**
and it is one clip to inspect. And **catalog restriction** in `load_targets`
remains the one untested cheap lever on the lyrics side; deprioritised four
times, still not in the graveyard, honest expectation is precision up and recall
flat.

---

## 6. Pending Deepti — do not decide these for her

1. **Push the branch / open a PR.** 42 commits, none pushed. Her call. Pushes and
   deploys are always hers.
2. **Delete the source `.mp4`/`.MOV` files in `~/Downloads`** after checking the
   mp3s. The conversion script never deletes a source; that is deliberate.
3. **Label the 11 long concerts** — item, raga, and (if segmenting) rough
   timings. Nothing in §5.1 can be scored without this.
4. **Four raga-equivalence rulings**, three answered on 2026-08-13 and recorded
   in `data/RAGA_MERGE_DECISIONS.md`. **Recorded, deliberately NOT applied.**
   One is still open: **Udayaravicandrika / Śuddhadhanyāsi** was asked and not
   answered. It has no threshold consequence, so nothing is blocked.
5. **Nine low-confidence rows, one low-confidence variant and two ambiguous
   rows** in `data/raga_aliases_audit.json` (filter `"confidence": "low"`).
6. **Hindustani imports as product policy**, not musical fact: 31 items
   (Bhīmpalās 8, Durgā 6, Gauḍ Malhār 3, Jhinjhōṭi 3, …), all attached to
   Carnatic artists on Carnatic-vocal concert pages, so repertoire rather than
   noise. Does "concert companion" cover every item on a programme, or only core
   elaborated Carnatic ragas?
7. **Back up `asr_cache_fullhistory/`** — local-only and gitignored. If deleted,
   `DEVICE_MAP.md` becomes unfalsifiable.
8. **Wire the registry junk blocklist** (a load-time merge in `load_targets`).
9. **Do NOT fund:** the rendition corpus, tonic-estimation work, prospective long
   OOC audio, the 28-clip short-OOC sentinel, or anything on the composition
   path.

---

## 7. Guardrails — the discipline that produced these results

This is the part to copy, not the numbers.

- **Preregister, and commit the prereg as its own commit before the scoring
  harness exists.** Every audit in this series did it. Ordering lives in git
  history, not in file mtimes. (The Qmax audit rests on mtimes because it was
  committed late; that is the weakest link in the set.)
- **Gate on reproducing the historical number first, on the exact integer
  counts.** The raga audit returned 377/518 and 439/518 — the *same integers* —
  so every delta afterwards was measured against the original measurement rather
  than an approximation of it. The coverage sweep went further: its default run
  rewrote `data/raga_audit/levels.json` and `git diff` on it came back **empty**,
  proving the parameterisation was behaviour-preserving and not merely
  number-preserving.
- **Fix the interpretation table in the brief before the number exists.**
- **Freeze the tunable that could launder the result**, and say in the brief that
  touching it voids the run rather than improving it.
- **Write predictions down so they can be refuted.** Eight were, this month.
- **Separate "produced no output" from "produced a wrong output"** and never sum
  them into one percentage.
- **The verifier re-derives every headline with its own code.** It has caught a
  wrong premise of its own once and a regression-to-the-mean inference once.
- **Coverage × accuracy, not accuracy.** A companion right 72.8% of the time
  about 39.1% of what it hears is worse than one right 57.0% of the time about
  79.2% of it. Nobody computed this for a month and a half, and it inverted the
  conclusion when they did.
- **Selection on the folds you then score on inflates by ~4.4 pp.** Measured, not
  assumed. Nested selection or an explicit "optimistic bound" label — never a
  quiet in-sample number.

---

## 8. Environment facts worth not rediscovering

- **`venv_train`** py3.11 — demucs, essentia, whisper, rapidfuzz, **pytest**.
  **`venv`** py3.14 — sklearn, librosa, mirdata, scipy, **no pytest**.
  essentia must run in `venv_train`, **fork not spawn**.
- **Never run bare `pytest tests/`.** Run the three named files (§2f).
- **ffmpeg 8.1.2 IS installed** at `/opt/homebrew/bin/ffmpeg`. The "no local
  ffmpeg" lines in `ARCHITECTURE.md`, `HANDOFF_CLIP_ID.md` §3 and
  `augment_wild.py:21` are **stale**.
- `codex` CLI 0.145.0 at `/opt/homebrew/bin/codex`. Non-interactive:
  `codex exec --sandbox workspace-write --skip-git-repo-check "<prompt>"`.
  Give it a brief on disk and tell it to read the brief; do not inline the job.
- **Zsh eats `"` inside `git commit -m`** when the message contains quoted
  phrases. Use `git commit -F -` with a heredoc. Zsh also fails on unmatched
  globs (`ls data/raga_v3*` → "no matches found") — quote or guard them.
- `data/raga_aliases.json`: 958 keys → 274 null. **Never trust registry `ragas`
  metadata without it, and never trust it without `data/raga_aliases_audit.json`.**
- The composition registry contains junk rows — addresses and dates parsed as
  compositions. Never trust registry raga metadata without a raga-vocabulary
  check.
- Melodia runs **~13× realtime**; the domain cells took ~400 s each at 5 workers,
  6× faster than the single-threaded estimate.
- **Billing:** a 30-day no-billing window is in force. Submits are gated on
  `CARNATIFY_BILLING_OK=1`. There is no GEMINI key locally. archive.org is free;
  Colab Pro T4 has been used for GPU work (`colab_coverhunter.py`,
  `colab_duration_probe.py`).
- **Production deploys are Deepti-run** — the permission classifier blocks them
  from an agent seat. Never keep the Space mirror in `/tmp`.
- **Synth clips must never enter `~/sung_tests`.** That directory is the wild
  set and its purity is load-bearing.

### The agent roster and how seats collaborate

- **Verifier seat** (Opus 5) — owns briefs, prereg discipline, and re-derivation
  of every headline. Does not take a workhorse at face value.
- **Workhorse seats** (Opus 5, GPT-5.6 / codex) — execute a brief on disk.
- Seats collaborate **only through files on disk and `AGENT_LOG.md`**, never
  through chat. A brief goes on disk; the agent is told to read the brief.
- Deepti also launches workhorses by hand in a separate terminal. **Assume
  concurrent repo work at all times.**
- Briefs must demand: prereg-before-score, partial results to disk after every
  cell, targeted `git add`, an `AGENT_LOG.md` entry naming refuted predictions,
  and an explicit list of paths the seat must not touch.

---

## 9. The one-line version, if you read nothing else

**The composition path is dead. The raga path works in the field at 59.3% on
60-second clips, wild audio costs nothing, and the binding constraint is that the
model cannot name 40-60% of what a listener hears. Two independent levers are
measured, real, and stack: more classes is free (+60% correct answers per
concert, retrain only), and more audio per class is worth +18.4 pp with no
saturation in sight. Eleven long-form concerts just landed and are the only
unmeasured cell in the entire product case — measure them first, and freeze
before you predict.**
