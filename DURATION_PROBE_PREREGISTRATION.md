# Duration probe — pre-registration

Written 2026-07-26, **before any probe audio is transcribed**. This is the
packet the red-team review (`CODEX_DURATION_PROBE_REVIEW.md`) required before
approving the expensive run. Once GPU is spent, the analysis below is fixed;
changing it afterwards makes the result unreadable.

Status: **items 1, 3, 4, 5, 6, 7, 8 settled. Item 2 pending Deepti** (final n
for the recall arm), and §6 needs her labeling pass before it has a realized n.
Nothing transcribed yet.

**Amended 2026-07-28**, still before any probe audio is transcribed, after
`CODEX_NEGATIVE_ARM_REVIEW.md` rejected the negative arm in full. §1 republishes
the pool counts under repaired title extraction; §6 is replaced wholesale; §8 is
new and freezes the negative decision rule and the rule for combining the two
arms. Nothing in §§2-5 or §7 changed.

---

## 0. The question, correctly scoped

Does listening length materially improve **the lyrics matcher's** in-catalog
retrieval, on long-form `concert_audio` recordings, holding preprocessing,
model, config and anchor constant?

**Scope correction that came out of review.** P1 was motivated by comparing
60-67% full-recording accuracy against 8-13/78 wild-clip accuracy. Those are
**different matchers**: the 60-67% is Qmax, and `ARCHITECTURE.md:72` records
Qmax at **0%** on wild clips. The confound was already logged at
`AGENT_LOG.md:2396` on 2026-07-23 and was repeated anyway. Consequences:

- This probe measures the **lyrics matcher only**.
- **Qmax cannot be probed on this pool at all.** `models/qmax_catalog.npz` is
  built from `concert_audio` melodia, so every window would be same-recording
  leakage. The asset behind the exciting number cannot be tested on the only
  long audio that exists.

## 1. Pool (settled)

`scripts/duration_probe_cut.py`, rebuilt after review.

```
=== POOL CONSTRUCTION (distinct title keys: 923) ===   [republished 2026-07-28]
  matched_but_no_lyrics            505
  RESOLVED                         271
  too_short                        117
  no_registry_match                 30
  5 titles carry a work-family id set; 100 archive clusters over 153 titles
```

**Republished after the title-extraction repair** required by
`HANDOFF_SESSION_0728.md` §7.1 (`NUM_PREFIX` stripped only three digits;
`file_title_raw` is now consulted when the filename is demonstrably not a
title). Delta against the 2026-07-26 counts: distinct keys +1,
`no_registry_match` +1, and **`RESOLVED`, `matched_but_no_lyrics` and
`too_short` all unchanged — not one title entered or left the pool.** Thirteen
id-mangled keys were replaced by real titles, all of which land in
`no_registry_match` because they are negative-arm candidates, not pool members.
Full audit: `data/duration_probe/TITLE_RESOLUTION_AUDIT.md`.

Construction rules, all fixed before the run: strip `_rN` (136 files);
deduplicate candidate rows **by registry id**; accept a title only if its
lyrics-bearing rows agree on the pallavi; expand truth to work-family sibling
ids by **pallavi identity across the whole registry**, guarded by a 25-char
minimum and composer agreement; use the **longest** rendition; do not use
registry raga metadata to disambiguate.

Known and accepted limitations:

- **Catalog-label overlap.** `build_composition_registry.py:80` builds registry
  rows from `models/qmax_catalog_meta.json`, whose titles
  `build_qmax_catalog.py:85` derived from `concert_audio` filenames. These
  recordings' filenames helped create the catalog they resolve against. This
  pool therefore **cannot validate catalog resolution**; it can only measure a
  duration response given resolution.
- **Conditioning on matchability.** The 505 `matched_but_no_lyrics` exclusions
  have zero registry lyric lines and can never be matched by a lyrics matcher
  at any length. Excluding them is the right conditional but raises absolute
  level against the wild set. **The curve's shape is the readable part, not its
  level.**
- Selection-bias check (`scripts/duration_probe_bias.py`, `BIAS_REPORT.md`):
  RESOLVED and `too_short` have the same lyric profile (median 7 lines, 44-47
  pallavi chars), so the >=300s filter does **not** select text-rich works.

## 2. Design (settled except n)

- Durations **30 / 60 / 90 / 180 / 300s**. 90s is mandatory: it is the product
  target (HANDOFF_SESSION_0725 §1) and the first design omitted it.
- **One uniform random anchor per title; all five windows nest from it.** This
  is progressive listening from a single start, which is what the product does.
  Independent per-duration offsets (the first version) estimate a different
  thing — a random excerpt — and let 30s and 300s sample different sections.
  The objection to nesting only ever applied to a **zero** start, because items
  open with alapana, which is lyric-free by definition.
- `--arm prefix` (zero start) is a **named secondary** and cannot move the gate.
- 16 kHz mono WAV for every window, so only length varies.
- `CARNATIFY_ASR_BACKEND=whisper`, `--no-raga --cache-v2`. **The 7-pass product
  config is retained** (4 mix + 3 Demucs stem). Review was explicit that a
  mix-only run is an exploratory mechanism screen and cannot pass or kill P1 for
  the product-default pipeline; the roadmap decision costs far more than the
  compute saved.
- **PENDING: n.** Pool allows up to 271. Measured cost is ~5.0-8.5 s wall per
  second of audio per 4 passes on CPU, so this is a Colab job. At n=60: 11.0 h
  unique audio, ~77 Whisper-hours at 7 passes, plus Demucs.

## 3. Analysis (settled)

`scripts/duration_probe_score.py`, rewritten after review.

- Estimand: `Δ = P(top-5 at 300s) − P(top-5 at 30s)` on **paired** titles.
- Uncertainty from the **discordant pairs** (exact one-sided McNemar/sign test)
  plus a **cluster bootstrap resampling `archive_identifier`**, since titles
  from one concert share artist, hall, mic and era. Titles with no known
  concert are their own cluster.
- The first version's `wilson_se` was the Wald SE of a marginal rate, misnamed,
  and ignored pairing entirely. Removed.
- **Strict monotonicity is not a condition.** Only ~4% of orderings of four
  exchangeable points are monotone by chance, so one dip could veto a real
  effect; and a jump-then-plateau (20/35/35/35) is monotone, passes, and is
  *favourable* evidence anyway. Shape is reported as paired transition tables,
  as a diagnostic, never as a veto.
- Published alongside: per-duration top-1/top-5/precision/coverage, the paired
  **90s → 300s product gap**, and the curve **stratified by lyric-line count**
  (pool selection interacts with it: works with more matchable lines give a
  long window more chances to win the per-entry max).

## 4. Decision rule (settled, three-way)

Boundary: **+15pp** on paired top-5, 30s → 300s.

| condition | verdict |
|---|---|
| 90% CI lower bound ≥ +15pp | **PROMOTE** — duration is a practically useful lever |
| 90% CI upper bound < +15pp | **KILL the ≥15pp claim** — not a useful effect for this matcher on this pool |
| otherwise | **INCONCLUSIVE** — roadmap does not move |

Inconclusive is a real outcome. The first version called every non-pass "P1
DEAD"; a +14pp estimate, a +20pp estimate with one dip, and an interval spanning
-5 to +30 all received the same causal verdict, which the data never licensed.
A kill rules out a *useful duration effect*; it does not diagnose a cause.

## 5. Validity gate (settled) — checked before any number is read

The run is **invalid**, not merely worse, if any of these fail:

- exact bijection between sidecar windows and result rows (no missing, no
  duplicates, no extras);
- **zero ASR cache misses** (`HANDOFF_VERFIER.md:79`: a SCORE with misses is
  invalid);
- identical title sets at every duration (otherwise pairing is broken);
- durations match the registered list;
- window count matches `expected_windows` in the sidecar.

The scorer exits non-zero and refuses to print a decision. `--force` prints
metrics for debugging and still suppresses the verdict.

## 5b. Mixed-hardware deviation and the straddler rule (frozen 2026-07-30)

**Written before any statistic from either arm was read.** At the time of
freezing, this seat had seen only row counts, cache-hit status, and the
transcript text of one already-cached window inspected to determine the
hypothesis schema. No accuracy, bluff count, interval or verdict had been
computed by anyone.

The GPU run spanned at least three sessions on at least two device
configurations: a Colab T4, a later L4-class GPU, and a resumed session whose
GPU is unrecorded (`colab_duration_probe.py` does not stamp the GPU name into
`run_log.json`; the AWS sibling does). Whisper ran fp32 throughout, but Demucs
was patched to CUDA, so both the transcription and the separation path could in
principle differ by device.

**Definition.** A *straddler* is a title (recall arm) or item (negative arm)
whose windows were not all transcribed within a single session on a single
device. A straddler's 30s → 300s contrast is confounded with hardware, which is
precisely the contrast both gates read. The negative arm is believed to be
straddler-free — all 140 windows came off the resumed session — and that belief
must be checked against `run_log.json`, not assumed.

**The device map is authoritative from the run's own records, not from
arithmetic.** `handoff.md` §2.6 asserts both "windows 1-80 came off a T4,
81-259 off the faster GPU" and "`probe0016` is split, d030-d180 on the T4";
`probe0016` is windows 81-85, so these cannot both hold. The reported stopping
point of 259 is also not a multiple of the 10-window checkpoint chunk, so the
straddler set is not derivable from the stop index alone.

### 5b.1 Amendment, 2026-07-30: `run_log.json` does not exist

**Amended before any statistic from either arm was read.** The branch rule below
is unchanged; only the order of operations and the unrecoverable-map fallback
are added, and both are fixed here in advance of running anything.

`colab_duration_probe.py` writes `run_log.json` at L316, *after* step 5/6. Step
5/6 is where the Colab session died (`ModuleNotFoundError: rapidfuzz`), so the
file was never written and is not retrievable from Drive. The run's only
provenance record was scheduled last, which is the same class of defect as the
missing import check and belongs in the graveyard beside it.

Consequently:

1. **The calibration runs first, and the device map is only needed if it
   fails.** If the mix hypotheses are identical, device-invariance is
   established and *no* straddler set is required — the map becomes irrelevant
   rather than merely unavailable. Note the calibration compares laptop CPU
   against GPU, a *wider* hardware gap than T4 against L4, so identity across it
   is the stronger result.
2. **Calibration windows are drawn from `probe0016` and `probe0051`**, the two
   straddler candidates under every version of the account, so no clean title's
   data is consulted whatever the map turns out to be. Prefer the shortest
   windows available.
3. **If the calibration says *differs*, the map must then be established** from
   the surviving records, in this order: the notebook output from both sessions
   (per-chunk prints carry timings, and a chunk's wall time per second of audio
   identifies the device against the measured 1.56 s/s and 0.86 s/s); then
   Google Drive revision history on the checkpointed
   `asr_cache_v2.json`, whose per-chunk rewrites are timestamped revisions.
4. **If the calibration says *differs* and no record establishes the map**, the
   recall arm's 30s → 300s contrast is confounded with hardware in an
   unidentifiable subset of titles. The arm then **cannot support a verdict**:
   the run is reported invalid, which is not a KILL and not an INCONCLUSIVE —
   it is a lost measurement, and the pre-registration says so now rather than
   after the cost is visible. Guessing a straddler set is not permitted.

**Calibration.** Re-transcribe `DEVICE_CAL_N = 3` already-cached windows on the
laptop against a temporary cache path, leaving `data/asr_cache_v2.json`
untouched. Windows are drawn from titles already identified as straddlers, so
that no clean title's data is consulted. Comparison is on the four `source:
'mix'` hypotheses only, verbatim on the `raw` field — the mix passes do not
involve Demucs, so they isolate device-dependence of the transcriber from
device-dependence of the separator. The three `source: 'stem'` hypotheses are
reported alongside but do not decide the branch, because a laptop re-run takes
the unpatched CPU-Demucs path and would differ for that reason rather than for
the reason being tested.

**Branch, frozen in advance:**

| calibration outcome | action |
|---|---|
| all mix hypotheses identical on all 3 windows | device-invariant. Score the arms **as-is at the registered n**; record the mixed-hardware deviation in the log and stop there. |
| any mix hypothesis differs on any window | device-dependent. **Exclude every straddler** identified from `run_log.json`, from both arms, and score at the reduced n. |

No third branch. A partial or ambiguous calibration result — for example, a
window that fails to re-transcribe — is treated as *differs*, the conservative
side, because the alternative is an unexamined confound sitting on the measured
contrast.

**Exclusion is mechanical, not discretionary.** Straddler identity comes from
the device map, never from a title's score. `duration_probe_score.py` gains an
explicit `--exclude-title` / `--exclude-item` mechanism, and the excluded set,
the realized n and the reason are printed in the run's own output. The scorer's
existing `n_titles` and `expected_windows` checks must be reconciled against the
exclusion list rather than bypassed, so that an exclusion cannot be used to hide
a genuinely incomplete run.

**Cost of the reduced-n branch, priced before it is chosen** so that no branch
looks cheaper once a number is visible: each excluded recall title costs 1/60 of
the recall arm. Each excluded negative item would come off its source's gating
count under rule A (§6b), where free-form is n=25 and opening n=20 and the arm
already tolerates zero new bluffs — so a negative-arm exclusion is materially
more expensive than a recall-arm one, and if the negative arm turns out to
contain straddlers, that is a finding to report, not a quantity to quietly
subtract.

**Re-transcribing a straddler onto the laptop to repair it is rejected.** It
would place that title on a third device *and* on the unpatched CPU-Demucs path,
differing from every other title in two ways rather than one — a within-title
confound traded for a between-title confound, at a cost of hours.

## 6. Negative arm (REBUILT 2026-07-28; awaiting Deepti's labels)

The 2026-07-26 arm is superseded in full. Its labels are kept at
`data/duration_probe/v1_superseded/` and must not be reused: they describe
excerpts cut at fixed 15/50/85% positions, while the scored windows were cut
later from an independent random anchor, and 5 of the labeled items overlap
their scored window nowhere at all (`CODEX_NEGATIVE_ARM_REVIEW.md` §4).

`METRIC_CONTRACT.md:30` still requires eligibility to come from the audio by
ear. What changed is *which* question the ear is asked and *what audio* it is
asked about.

**Endpoints only.** 30s and 300s, because that is the contrast the gate reads.
70 items × 2 windows = 6.4 h unique audio ≈ **45 Whisper-hours** at the 7-pass
config — the same bill as the old 35-item × 5-duration arm, for twice the items.

**Windows are cut before labels are collected**, and the labeling audio is drawn
from *inside the selected 300s window*. Only the 300s window needs a label: the
30s window nests at its start, so a lyric-free 300s window is lyric-free at 30s
by construction.

**Two complementary sweeps per item, and an item gates only if both come back
`no-sahitya`.** Each item's `_scan.wav` is 10s every 20s of the scored 300s
window, cut from the window wav itself — 150s of listening at a 50% duty cycle.
Three 20s excerpts covered 20% of the window and could not support "no sahitya
anywhere in it"; **one sweep at 50% duty could not either**, which
`CODEX_NEGATIVE_ARM_REVIEW_R2.md` P0-1 established on 2026-07-29. "Maximum
unheard gap is 10s" is true, but fifteen 10s stretches per window — including
290-300s — were never played, and a single pallavi phrase inside one of them is
enough to make a lyrics matcher answer.

`scripts/build_negative_complement.py` therefore cuts the complement (10-20,
30-40, …, 290-300) from the same window wavs into `_scan2.wav`, and
`LABELING_SHEET_2.md` asks the identical binary question about it. The two
sweeps tile [0, 300) exactly — asserted in code, no gap and no overlap. Combination
rule: `sahitya` on **either** sweep settles the item as sung (singing heard
cannot be un-heard by the other half); `no-sahitya` requires **both**; anything
else — blank, `unusable`, coin-toss, or a sweep never offered — is `unknown`.

The sidecar carries `sweeps_required` and `sweeps_applied`, and the negative
validity gate rejects `applied < required`, so a single-sweep arm cannot print
a safety conclusion.

**Realized outcome, 2026-07-29.** Sheet 2 came back 51/51 labeled. Two items —
`neg053` and `neg020` (labeler's note: *"has some swara and lyrics"*) — carry
singing that lived entirely inside the 150s sheet 1 never played. **The gating
stratum is 49**, from 51, over 49 distinct clusters: 25 free-form, 20 opening,
4 unidentified. Four percent of the single-sweep stratum was contaminated, which
is the P0 realized rather than argued, and it is why the pooled margin dropped
from three tolerable surprises to two.

**A definition correction, recorded because the sheet had it wrong.** Both
sheets list bare `swaram` under `no-sahitya`. In performance that is misleading:
swarakalpana alternates solfège with **the sahitya line of the composition**,
call and response, so a passage a labeler would describe as "has swara in it"
normally contains sung words. Deepti confirmed this on 2026-07-29 when asked to
adjudicate `neg030` (labeled `sahitya`, noted *"has swara in it"*) — the label
was right and the sheet's definition was wrong, so `neg030` stays excluded and
n stays 49. Any future sheet must say that bare solfège with no composition line
is `no-sahitya`, and that swarakalpana against a sahitya line is `sahitya`.
Tanam remains `no-sahitya` and `neg004` / `neg008` are unaffected.

**The ear is asked only what an ear can answer.** The label is binary —
`sahitya` / `no-sahitya`, with `unusable` — and catalog membership is a join
over the registry, never a listening judgment. Asking for `ooc` by ear was a
design error. `unusable`, a coin-toss, and a blank row all become **unknown**
and drop out; none of them is treated as no-sahitya.

**Candidate sources** (`scripts/build_negative_arm.py`), capped at one item per
archive cluster so seven tracks off one lecture-demonstration upload cannot pose
as seven independent works:

| source | items | what it is |
|---|---:|---|
| `free_form_candidate` | 34 | filename names a section (Alapana, RTP, thani) — the whole free-form supply, a census, not a sample |
| `opening_candidate` | 30 | first 300s of a long (≥900s) in-catalog recording, where the alapana lives |
| `unidentified_candidate` | 6 | title resolves to nothing even under the relaxed key — reported, never gating |

The opening source exists because `data/concert_audio` holds only 36 free-form
files, capping the gating stratum at ~34 items, which rules out a +15pp bluff
rise only if at most **one** item bluffs. It is also the most product-relevant
negative available: it is what Jon hears if he opens the app before the kriti
starts. **Anchor choice cannot bias this arm** the way it would bias the recall
arm, because eligibility is decided by adjudicating the very window that is
scored; where a window came from changes the composition of the negative
population, which is described here, and never whether an item's label is right.
Source is reported as a covariate and each source is also reported alone.

**The OOC stratum is empty, and that is a finding.** Of 1,238 recordings, 1,175
resolve exactly, 16 resolve under the relaxed key, 36 are free-form, and the
remaining 11 have no work identity at all — upload ids, shellac catalogue
numbers, `Concert 163`, `xxxx`, `varnam vasantha`. None names a composition, so
none can be verified absent from the catalog, and the registry was itself partly
built from these filenames. An item is `ooc` only via
`data/duration_probe/verified_ooc.json`, a reviewed identity file, which is
empty. **OOC abstention at 300s is unmeasurable from assets on disk** and needs
prospectively acquired audio — pending Deepti.

**Partial labeling is valid.** Sheet order is randomised across sources and
unlabeled rows are unknown, so stopping early yields a smaller experiment rather
than a broken one. Realized n and its consequences are printed by the scorer.

## 6b. Negative decision rule (frozen 2026-07-28)

The old scorer printed negative point rates and nothing else — no interval, no
test, no gate — so a half-transcribed negative run would still have produced a
confident-looking table. All three holes are now closed.

**Validity gate**, checked before any negative number is read. The arm is
invalid, not merely worse, if any of these fail: exact bijection between the
negative sidecar and the result rows; zero ASR cache misses; every window
carrying a stratum; `labels_applied` true; durations matching the registered
list; window count matching `expected_windows`; identical item sets at both
endpoints. **Invalid negative data suppresses the safety conclusion**, exactly
as invalid recall data suppresses the recall verdict.

**Gate holes closed 2026-07-29** (`CODEX_NEGATIVE_ARM_REVIEW_R2.md` P0-4 named
seven ways the gate could still print SAFE on a broken run; each now has a
test in `tests/test_negative_arm.py`):

1. durations are checked against a frozen `DESIGN_DURATIONS = (30, 300)`, not
   merely against whatever the sidecar registers — a 300s-only sidecar used to
   validate, making `short == long`, `b == 0` and printing SAFE at 5.7pp;
2. exactly one sidecar row per `(item, duration)`;
3. an item must carry the same stratum at both endpoints;
4. `n_items`, `seed`, `stratum_counts` and cluster uniqueness within the gating
   stratum are checked against the windows actually present;
5. `cache_v2` must be present and in `{hit, MISS}` — absent or malformed used
   to pass;
6. `composition_confidence` must be present and in
   `{none, low, medium, high}` — `!= 'none'` read a *missing* field as an
   answer, so a run that produced nothing scored `b=0`;
7. every window carries `audio_sha256` (`scripts/stamp_negative_shas.py`) and
   the scorer re-hashes the wavs at read time, so correct filenames holding
   swapped or regenerated audio cannot validate. `--cache-v2` is keyed by the
   same hash, so labels and transcripts bind to one artifact.

Also gated: `sweeps_applied >= sweeps_required` (see §6).

**Per-source gate — RULE A, frozen 2026-07-29 by Deepti.** The pooled bound is
valid but bounds the realized **design mixture** (25 free-form : 20 opening : 4
unidentified), whose weights came from sampling quotas and labeling yield rather
than product prevalence — so a failure concentrated in one source can hide
inside it (3 new bluffs in one place: pooled 15.1pp, free-form alone 28.2pp).
No argument for weighting the mixture exists, so the mixture is not the estimand.

> **SAFE requires the one-sided exact 95% upper bound to fall below the boundary
> for the pooled gating stratum AND for every source with n ≥ 20.**

At the realized n that is free-form (n=25) and opening (n=20); `unidentified`
(n=4) is below the threshold and is reported without gating. In operational
terms the rule is **zero new bluffs in each major source** — one bluff in either
fails it (25: 11.3pp at b=0, 17.6pp at b=1; 20: 13.9pp at b=0, 21.6pp at b=1).

The pooled bound is still computed and printed beside the gate, and disagreement
between the two is flagged loudly, but **the pooled bound no longer decides
anything**. Reverting to a pooled gate is a pre-registration change requiring a
registered argument for the mixture weights; it is not the implementation seat's
to make.

**Estimand.** The change in *answer rate*, 30s → 300s, among windows her ear
confirmed carry no sung words.

**Statistic.** `b` = items that abstain at 30s and answer at 300s. Reverse flips
(`r`) are reported but excluded from the bound, which can only make it stricter.

**Rule.** SAFE if the one-sided exact 95% (Clopper–Pearson) upper bound on `b/n`
is **below +15pp**. Otherwise NOT ESTABLISHED — which does *not* mean bluffing
rose, only that this arm cannot say it did not.

This is an **upper-bound claim, not a detection claim**. The rationale was
originally that detection is out of reach; **that rationale is stale and is
corrected here (2026-07-29)**. It rested on a design needing ~44 items that can
flip, but under the registered no-reverse-flip model the pooled n≈49 has roughly
**90% power** against a true +15pp rise (`CODEX_NEGATIVE_ARM_REVIEW_R2.md`).
Detection is therefore no longer mathematically forced out by sample size. The
upper-bound formulation stays because it is the more useful question — the
product decision needs a rise *ruled out*, not merely *not detected* — but it
is a choice, not a necessity, and the document should not claim otherwise.

What the **realized** n buys (recomputed 2026-07-29 with
`clopper_pearson_upper` after the second sweep cut the stratum from 51 to 49):

| stratum | n | b=0 | b=1 | b=2 | b=3 |
|---|---:|---:|---:|---:|---:|
| pooled (reported, does not gate) | 49 | 5.9pp | 9.3pp | 12.3pp | **15.1pp** |
| free-form (**gates**) | 25 | 11.3pp | **17.6pp** | **23.1pp** | **28.2pp** |
| opening (**gates**) | 20 | 13.9pp | **21.6pp** | **28.3pp** | **34.4pp** |
| unidentified (reported, n < 20) | 4 | **52.7pp** | **75.1pp** | **90.2pp** | **98.7pp** |

(bold = does not rule out +15pp)

Under rule A the arm therefore tolerates **zero** new bluffs in either gating
source. The pooled row is what a mixture gate would have tolerated — two — and
the gap between those two rows is exactly the protection rule A buys.

Only the `no-sahitya` stratum gates. `sung_unidentified` is real product input
but is not proof a work is absent from the catalog, so it is reported as a
sensitivity stratum and never gates.

## 6c. How the two arms combine (frozen 2026-07-28)

They are **not subtractable, and are no longer described as paired.** Recall is
a change in top-5 hit rate among eligible in-catalog works; bluffing is a change
in answer rate among negative queries. Differencing them assumes equal
prevalence of positive and negative queries, equal cost, and that a top-5
retrieval is worth as much as an answer shown to a user. None of those is
registered, and pretending otherwise was the review's §1 objection.

The combination is a **conjunction**:

| recall | safety | verdict |
|---|---|---|
| PROMOTE | SAFE | **PROMOTE as an archive-domain research lever** — longer listening buys recall without a ruled-in *no-sahitya* bluff rise. **Not** product-presentation safety; see the scope note below |
| PROMOTE | not established | **HOLD** — the gain is real but does not authorize showing results to a user |
| KILL | either | **KILL** stands on the recall arm alone |
| INCONCLUSIVE | either | roadmap does not move |

**Scope of a combined PROMOTE (narrowed 2026-07-29).** As first written, row 1
permitted a combined PROMOTE while §7 correctly said the probe cannot license
safe OOC abstention — the document contradicted itself and the scorer followed
the wrong half, printing "without a ruled-in bluff rise" unqualified. Only the
**no-sahitya** stratum gates. OOC abstention at length is **unmeasured**: the
OOC stratum is empty by construction and unmeasurable from assets on disk
(`HANDOFF_SESSION_0729.md` §4), while `METRIC_CONTRACT.md` requires OOC bluffs
to be reported separately. A passing conjunction therefore licenses duration as
a **research** lever on the archive domain, and nothing about what may be shown
to a user.

## 7. What a pass would and would not license (settled)

Would license:

> On uniquely resolved, lyrics-bearing, ≥5-minute `concert_audio` recordings,
> the frozen Whisper lyrics pipeline's in-catalog retrieval improves with longer
> listening from a single random anchor.

Would **not** license: the same gain on wild phone/ambient audio; 90-second
equivalence to five minutes; safe abstention on OOC or no-sahitya audio; or the
claim that duration explains the old 60-67% full-recording result (that was
Qmax). Generalizing to the product needs a prospective long **wild** arm, and
the existing wild set cannot supply it — its maximum clip is 98s, so that means
newly captured long recordings, not re-slicing the scoreboard.
