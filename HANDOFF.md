# Carnatify workhorse handoff

Last reconciled: **2026-07-30**, by the Opus 5 workhorse after executing
`WORKHORSE_DEVICE_CALIBRATION_BRIEF.md` and scoring the duration probe.
Repository: `/Users/shyamravidath/carnatify`
Branch: **`probe/duration-and-negative-arm`** · HEAD `22b4d58` · **not pushed**
`main` is at `1ba3e1f`; `identify_clip.py` has **zero diff against `main`**.

This is the current operational handoff for the **workhorse / implementation
seat**. Older handoff documents remain useful as history; their status sections
are not authoritative — in particular the previous version of this file asserted
a device map that turned out to be arithmetically impossible, and acting on it
would have corrupted the probe. The durable experiment ledger is `AGENT_LOG.md`:
append exact outcomes there rather than paraphrasing them from memory.

**What changed in this rewrite.** The previous version described a GPU run
stopped part way, with 259/300 recall windows transcribed and the negative arm
not started. All of that is now finished. **The duration probe is complete,
scored exactly once, and the verdict is KILL.** The mixed-hardware confound that
blocked scoring was resolved from Google Drive revision history. Everything is
committed. The graveyard in §4 is preserved and extended.

---

## 1. The goal

Carnatify should identify a Carnatic composition from a live performance despite
changes in artist, key, tempo, accompaniment and improvisation, and present
title, raga, sahitya and English meaning.

Product concept: a concert companion for Jon, a Western listener with no prior
Carnatic knowledge — progressively update a top-five list, offer candidate detail
pages, offer "none of these", and **never present a weak guess as a confident
identification**. The product bar is ~85% precision on what it chooses to show.
**The pipeline has never met it, and as of this session every model-side lever
that was on the table has been measured and closed.**

### Where the project actually stands: four doors closed, all measured

| door | verdict | evidence |
|---|---|---|
| lyrics-ASR precision gate | no operating point at any threshold (≤31%) | `scripts/precision_coverage_curve.py`, 2026-07-23 |
| sung-Carnatic ASR fine-tune | **strictly worse** — 8/78 → 0-1/78, val WER >100%, memorised ~26 pallavis | `colab_asr_finetune.py`, 2026-07-24 |
| melodic CSI (CoverHunter) | **NO-GO** — source-disjoint mAP 0.113 vs 0.031 chance; the 0.327 headline was ~two-thirds contamination | 2026-07-24 |
| **listening longer (duration)** | **KILL** — top-5 5.1% @30s → 1.7% @300s, delta −3.4pp, 90% CI [−8.9, **+1.8**] | this session, §2.2 |

**What still works, and should not be lost in the gloom:** OOC rejection is the
pipeline's strongest behaviour (24/28 on the wild set). Full-recording raga is
72.8% top-1 / 84.7% top-3 under grouped CV, leak-free. Those are real results.

**Scope corrections that must not be re-litigated:**

- The 60-67% full-recording result belongs to **Qmax**; the 8-13/78 wild-clip
  result belongs to the **lyrics matcher**. Comparing them was a matcher-identity
  confound.
- **Qmax cannot be evaluated on `data/concert_audio`** — `models/qmax_catalog.npz`
  was built from those recordings; it would be same-recording leakage.
- The duration KILL establishes only an **archive-domain lyrics-matcher** result.
  Not wild-phone performance, not OOC safety at length.
- The lyrics-ASR backbone is a confirmed dead end for the 85% bar, proven from
  two directions (precision curve ≤31% anywhere; LoRA fine-tune 8/78 → 0-1/78).

---

## 2. Current state of the code

### 2.1 Production pipeline — unchanged and deliberately untouched

`identify_clip.py` is the single source of truth for inference. Nothing in this
entire line of work edits it, including the Colab and AWS runners, which patch
module attributes at runtime instead. `git diff --stat identify_clip.py` against
`main` is **empty** and was verified empty at every step.

Product default: Whisper `large-v3-turbo`, cache v2, 4 mix passes + 3 Demucs stem
passes. `hybrid` / `hybrid_stem` are **experimental** and must not silently
replace the default.

**Wild scoreboard, 106 clips (78 in-catalog + 28 OOC) — unchanged this session:**

| backend | top-1 | top-5 | OOC reject | precision @ coverage |
|---|---|---|---|---|
| `whisper` (product default) | **8/78** | 21/78 | 21/28 (7 bluffs) | 17% @ 44% |
| `hybrid` | 11/78 | 25/78 | — | 20% @ 52% |
| `hybrid_stem` (best experimental) | 13/78 | 28/78 | — | 23% @ 53% |

Guard: `~/sung_tests_curated`, floor 8/36 (hybrid_stem reached 10/36). Canonical
command:

```bash
[CARNATIFY_ASR_BACKEND=hybrid|hybrid_stem] \
  venv_train/bin/python identify_clip.py ~/sung_tests --no-raga --cache-v2
```

`--cache-v2` **never transcribes on a miss**; any scored run containing a cache
miss is invalid. Cache keys are `sha256(audio)[:24] + ':' + config_id`.

`METRIC_CONTRACT.md` requires: precision-at-coverage as the primary
presentation-safety metric, in-catalog top-1/top-5, **OOC bluff rate reported
separately**, eligibility strata, assisted recovery, and no product green light
from a same-corpus benchmark.

### 2.2 Duration probe — COMPLETE, scored once, verdict KILL

440 windows transcribed (300 recall + 140 negative), merged into
`data/asr_cache_v2.json` (546 entries = 106 pre-existing + 440). Both arms
inferred with **zero cache misses**. Scored exactly once. Full verbatim block in
`AGENT_LOG.md` under the 2026-07-30 scoring entry — quote it from there, never
recompute a number by hand.

**Recall: KILL.** 30s → 300s paired top-5 contrast **−3.4pp**, 90%
cluster-bootstrap CI **[−8.9, +1.8]** over 52 archive clusters, exact one-sided
p=0.9375, n=59 titles. The upper bound is far below the +15pp boundary. The point
estimate is negative and the shape is monotone downward past 90s. Top-5 peaks at
**90s (5/59)** and falls to **1/59 at 300s**. Coverage rises 29% → 42% while
precision falls 12% → 4%: longer windows make the matcher answer more and be
right less.

**Safety: NOT ESTABLISHED — and that is underpower, not a rise.** The gating
stratum shows b=4 new bluffs against r=4 recovered, **net exactly +0.0pp** on
n=49. Rule A bounds b alone, and 2/25 free-form → 23.1pp, 2/20 opening → 28.3pp,
both above the boundary. **Never quote this as "longer listening bluffs more."**
Design number for any future negative arm: clearing +15pp needs n≥30 at b=1,
**n≥40 at b=2**, n≥50 at b=3 — roughly **double** the realized per-source n of 25
and 20.

Unknown-item sensitivity, printed before the fact as registered: the two
`unknown` items push free-form to 3/26 → 27.2pp and opening to 3/21 → 32.9pp, NOT
safe. Both the observed bound and this sensitivity belong in any quoted result.

**Scope.** This answers the registered question — no, listening longer does not
materially improve the current lyrics matcher — for *uniquely resolved,
lyrics-bearing, ≥300s `concert_audio`* only. It graduates nothing. The OOC
stratum is empty by construction and OOC abstention at length remains unmeasured.

### 2.3 The device map — established, and the old one was wrong

Three GPUs touched the run. The confound is real: **transcripts are
device-dependent** (§4). `data/duration_probe/DEVICE_MAP.md` is authoritative.

| session | device | checkpoints | windows | measured |
|---|---|---|---|---|
| 1 | T4 | V1-V8, chunks of **10** | 1-80 (`probe0000`-`probe0015`) | ~1.55 s/s |
| 2 | L4-class | V9-V42, chunks of 5 | 81-259 | ~0.80 s/s |
| 3 | A100-SXM4-40GB | V44-Current | 260-300 + all 140 negatives | ~0.46 s/s |

Recovered from all 82 Google Drive revisions of the checkpointed cache: contents
give the entry set at each checkpoint, timestamps give wall time between them,
audio seconds come from the filenames. The three recovered rates reproduce the
independently recorded 1.56 / 0.86 / 0.497 s/s to two significant figures.

**Exactly one straddler: `probe0051` = `sujanajivana`**, excluded, recall n=59.
**`probe0016` is NOT a straddler** — the previous handoff claimed it was, and
that claim is refuted: session 1 wrote per chunk at `CHUNK = 10`, its final state
is n=80 with no `probe0016` window present, so all five of its windows were
transcribed after the device change. No negative item straddles.

`asr_cache_fullhistory/` (253MB, 82 revisions) is **local-only and gitignored,
and the device map cannot be re-derived without it.** Do not delete it.

### 2.4 The scorer and its exclusion mechanism

`scripts/duration_probe_score.py` applies **rule A** (§6b): SAFE requires the
one-sided exact 95% upper bound below the boundary for **every source with
n ≥ 20**. The pooled bound is computed and printed beside it labelled REPORTED,
NOT GATING.

New this session — `--exclude-title` / `--exclude-item` (repeatable) plus a
mandatory `--exclude-reason`:

- The **full arm validates first**, then units are dropped, then the reduced
  sidecar is **re-validated against bookkeeping recomputed by subtraction**
  (`n_titles`, `n_items`, `expected_windows`, `stratum_counts`,
  `gating_source_counts`). Nothing is bypassed, and an exclusion cannot make an
  incomplete run validate.
- Rule A is quantified over the sources the design **registered**. An exclusion
  that pushes a registered source below `SOURCE_MIN_N = 20` **suppresses** with
  an explicit message.
- `resolve_recall_units()` accepts either a title key or a `probeNNNN` window id,
  because `DEVICE_MAP.md` speaks in window ids and the sidecar is keyed by title.

### 2.5 Registry hygiene (separate lane, complete, unwired)

`scripts/registry_junk_filter.py` + `data/registry_junk_blocklist.json`: 52
flagged rows (19 `drop`, 33 `review`) behind a hard evidence gate. A/B'd on the
wild set: top-1/top-5/OOC all unchanged, answered 47 → 46 — it deletes exactly one
wrong answer. Deepti-gated; wiring it is a load-time merge in `load_targets`,
never a registry rebuild (ids are assigned by enumeration order).

### 2.6 Tests

```bash
venv_train/bin/python -m pytest tests/test_clip_policy.py \
    tests/test_registry_junk.py tests/test_negative_arm.py -q
# 103 passed, 1 xfailed
```

Never run bare `pytest tests/` — `test_audio.py`, `test_composition.py`,
`test_lyrics.py`, `test_pipeline.py`, `test_raga.py` and `test_tala.py` import a
`carnatify` package that does not exist and fail at collection.

---

## 3. Files actively being edited

**Nothing is mid-edit. The working tree is clean apart from
`.claude/settings.local.json` (gitignored).** Everything from this lane is
committed on `probe/duration-and-negative-arm` — 7 commits, not pushed, and
`identify_clip.py` has zero diff against `main`.

~4GB stayed out of history via `.gitignore`: probe wavs (regenerable from
`duration_probe_cut.py`), `asr_cache_fullhistory/` (253MB), the varnam corpus.
The ~1.1MB that **cannot** be regenerated — sidecars, both labeling sheets,
`DEVICE_MAP.md`, `DEVICE_CALIBRATION.md`, the session-3 notebook output — is
committed.

**Written this session (all committed):**

- `scripts/duration_probe_device_cal.py` — the §5b device calibration
- `data/duration_probe/DEVICE_CALIBRATION.md`, `DEVICE_MAP.md`
- `scripts/duration_probe_score.py` — exclusion mechanism, `n_titles` check,
  rule-A suppression on a shrunken source, `probeNNNN` resolution
- `tests/test_negative_arm.py` — 48 → 56 tests

**Two briefs are written and unstarted:**

- **`WORKHORSE_QMAX_AUDIT_BRIEF.md`** — the next job, see §5.
- `WORKHORSE_DEVICE_CALIBRATION_BRIEF.md` — complete, kept for audit.

**Do not touch:**

- `identify_clip.py` — nothing in this lane edits the scoreboard path
- `data/duration_probe/v1_superseded/` — audit trail, not reusable
- `asr_cache_fullhistory/` — the only source of the device map
- `scripts/build_negative_arm.py` at **runtime** — re-running it re-draws every
  anchor, re-assigns every `negNNN` id and re-shuffles the sheet, destroying both
  sheets of labels. Editing its template strings is safe; executing it is not.
- `scripts/duration_probe_cut.py` at runtime — same hazard, re-draws anchors and
  breaks the cache binding.
- `CODEX_*_REVIEW*.md` — review artifacts, read-only

---

## 4. What has been tried and failed

`HANDOFF_CLIP_ID.md` §5 is the master graveyard. Everything here stays dead
absent genuinely new evidence.

### Lyrics / ASR identification

- Never exceeded ~31% precision at any threshold, tier or configuration.
- Confidence scores do not separate correct from incorrect (true/bluff score
  medians 1.28 / 1.25, interleaved down the whole ranking).
- Cross-channel agreement peaks at ~43% precision on 7 clips — whisper and indic
  errors are **correlated**.
- Max fusion, raga gating, extra answer gates, prompted/forced Whisper variants:
  no useful gain. A ranker fitted on the 78-clip eval set overfit.
- Character n-grams, vowel squashing, title-IDF weighting, DTW/Qmax fusion: dead.
- Indic CTC translit as a **default**: 8% precision @ 91% coverage, 27/28 OOC
  bluffs.

### ASR fine-tuning

- Whisper-small LoRA on ~80 min of weak Saraga supervision collapsed 8/78 →
  **0-1/78**, memorizing ~26 pallavis.

### CoverHunter / learned audio retrieval

- Source-disjoint CSI eval: mAP 0.113, hit rate 0.161, chance ≈0.031. The earlier
  0.327 was inflated by ~2/3 leakage.

### Qmax / contour matching

- Valid 60-67% only in its original full-recording context, and **untestable on
  `concert_audio`** (leakage). On wild 30-60s clips: **0%**. **This number has
  never had a source-disjoint audit — that is the next job (§5).**

### Raga and tala

- TDMS raga: 72.8% top-1 on full tracks, **0/10** on wild short clips.
- Tala: 16.5% → 32.9%, both below a 72% majority-class baseline.

### Duration

- **Ruled out, not merely undetected.** Do not propose "just give it more audio"
  again without new evidence. The curve peaks at 90s and declines.

### Experiment-design failures (expensive, all repeated at least once)

- Independent per-duration offsets measured *a random excerpt*, not the value of
  more listening. Fixed by nesting from one anchor.
- Strict monotonicity + binary promote/kill was statistically invalid; replaced by
  the three-way CI rule.
- **Asking a listener to label "out of catalog" by ear was a category error.**
  Catalog membership is a lookup over 8,688 rows.
- **A single 50%-duty listening sweep does not establish "no lyrics here."** The
  complement caught singing in 2 of 51 items — 4% contamination — all of it inside
  the 150s the first sweep never played.
- **A labeling sheet's categories must describe the music as performed, not a
  taxonomy.** The sheet filed bare `swaram` under `no-sahitya`; in performance
  swarakalpana alternates solfège with the composition's sahitya line. Caught only
  because the musician labelled against the sheet she was reading. **Have the ear
  review the category definitions before the sheet ships.**
- `str.maketrans('dbgjmz','ptkcns')` maps d→p and b→t. The lesson is the
  calibration set, not the typo.

### Long-runner / provenance failures, new this session

- **Estimate GPU cost from the decoder, not from model size.** openai-whisper at
  fp32 runs ~5× realtime on a T4, not ~10×, and 7 passes multiply it. Predicted
  10-20 h, measured ~27 h on a T4.
- **A long unattended runner must write provenance incrementally, from the first
  chunk — never at the end.** `colab_duration_probe.py` writes `run_log.json`
  after step 5/6; step 5/6 crashed, so ~27 GPU-hours produced no device record at
  all. The map was only recoverable from Drive revision history.
- **It must also import-check its full inference path in step 0.** The same runner
  verified audio SHAs before spending GPU but never checked that `rapidfuzz`
  imports, losing step 5/6 after the entire bill was paid.
- **Transcripts are device-dependent.** Laptop-CPU vs GPU differed on 7 of 12 mix
  passes, several completely. Where the model has real evidence it is invariant;
  where it hallucinates, small numeric differences cascade — and those garbage
  passes reach the matcher, because `variants_from_v2()` is longest-wins per
  source. Any multi-session GPU run must keep each unit's windows on one device,
  or exclude the straddlers.
- **A provenance claim that is arithmetically impossible is worse than none.**
  The previous §2.6 asserted "windows 81-259 on the faster GPU" *and*
  "`probe0016` (windows 81-85) is split across that boundary". It was written
  from memory, not from a record, and its prescribed fix would have put a title
  on a third device.
- **The executed notebook was not the file on disk** — chunks of 5 versus
  `colab_duration_probe.py:72`'s `CHUNK = 10`. Reconcile the runner with what
  actually ran before quoting it again.

### Deployment

The deployed Hugging Face Space still exposes legacy behavior (~16% composition,
40.5% raga historically). It does **not** represent the current local pipeline.

---

## 5. The next step

**Execute `WORKHORSE_QMAX_AUDIT_BRIEF.md`.** Read-only, no GPU, no training.

After the duration KILL, the **60-67% full-recording Qmax top-1**
(`HANDOFF_CLIP_ID.md:45`) is the **last surviving positive result in the
repository**, and the 2026-07-25 design doc's "input contract, not model quality"
thesis rests entirely on it. It has never had the audit that destroyed the
comparable number next door: CoverHunter's headline dev mAP was 0.327, and a
source-disjoint re-score put it at 0.113 against a 0.031 chance floor. Qmax was
evaluated in the same era, on the same corpus, by the same hands, and
`HANDOFF_CLIP_ID.md:107` already flags that its short-clip sibling was
"artist/recording-family flattered".

The narrow question: **how much of 60-67% survives when a query can never be
scored against its own recording, its own artist, or its own archive upload?**

Assets all exist — `models/qmax_catalog.npz` (1,421 tracks, 3,465 chroma
windows), `models/qmax_catalog_meta.json`, `build_qmax_catalog.py`,
`evaluate_composition_qmax.py`, `evaluate_composition_external.py`.

1. **Reconstruct what the original evaluation did**, quoting the code. If the
   protocol cannot be determined from the repo, that is itself the finding, and
   60-67% should stop being quoted at all.
2. **Re-score at three levels:** (a) as-originally-run, to reproduce the baseline
   and confirm the harness works; (b) recording-disjoint; (c) source-disjoint on
   `archive_identifier`, plus artist where recoverable.
3. **Report the chance floor at each level**, computed as
   `colab_coverhunter_rescore.py` does it — mean positives per query divided by
   references, averaged **over clips, not over songs**. Getting this wrong once
   printed 0.006 instead of 0.031.
4. **Report n at every level.** Only 65 of 1,118 titles have 2+ renditions, so
   source-disjointness may shrink the evaluable set to nothing. If it does, that
   is the headline, not a footnote under a percentage.

Write it up in `data/QMAX_CONTAMINATION_AUDIT.md`. The interpretation table is
**fixed in advance in the brief** — read it before running anything, and do not
choose a reading after seeing the number.

---

## 6. Pending Deepti — do not decide these

1. **Push the branch.** `probe/duration-and-negative-arm`, 7 commits, unpushed.
2. **Prospective long OOC audio** — the only route to measuring OOC abstention at
   length. `~/sung_tests/fetch_manifest.tsv` retains source URLs and durations, so
   this is reacquisition rather than discovery; 9 reviewed OOC sources carry a
   parseable source duration ≥300s.
3. **The 28-clip short-OOC sentinel** — nested 30s → full-clip (43-84s) over
   existing reviewed OOC clips, reusing existing caches. n=28 gives 10.1pp at b=0,
   15.9pp at b=1. It **cannot** speak to 300s and must be pre-registered as
   non-gating before it is built.
4. **The registry junk blocklist** — 19 `drop` + 33 `review` rows, unwired.
   `comp01994` is the one `drop` row with real recall cost. `comp06030` "Ragam
   Thanam Pallavi", a section name the live matcher can return as a composition,
   is not on the blocklist.

---

## 7. Guardrails

- **Do not commit or push without being asked.** Deepti owns repository history.
  Do not reset, clean or revert the working tree.
- Do not change the product default from `whisper`.
- Do not run Qmax against `data/concert_audio` (leakage).
- Do not re-run `build_negative_arm.py` or `duration_probe_cut.py` (§3).
- Do not loosen the OOC definition. That defect killed the v1 negative arm.
- Do not revert rule A to a pooled gate — that is a pre-registration change
  requiring a registered argument for the mixture weights.
- **Do not change anything that feeds `asr_config_id()`** — model, `fp16`,
  language lanes, separation. It is the cache key, so a change silently
  invalidates every window already paid for. This is why Whisper runs fp32 even on
  a GPU and why that is not a bug to fix.
- Do not retune a threshold, or choose an interpretation, after seeing a SCORE.
- **Pre-register the reading before running the measurement.** Both surviving
  good results in this lane came from doing that; every discredited number came
  from not doing it.
- **Flag, never self-adjudicate, a truth change that favors your own result.**
- Preserve exact metric definitions and keep lyrics-matcher, Qmax, hybrid and
  hybrid-stem numbers distinct.
- Respond to Deepti in caveman style; write docs, commits and `AGENT_LOG.md`
  entries in normal prose.

---

## 8. Environment facts worth not rediscovering

- `venv_train` is py3.11. **ffmpeg 8.1.2 is installed** at
  `/opt/homebrew/bin/ffmpeg` (the "no local ffmpeg" line in `ARCHITECTURE.md` is
  stale).
- `--cache-v2` is keyed by **`audio_sha256`**, not filename. The `path.name`
  collision hazard is in the **legacy** `transcribe()` path only.
- Cache keys contain nothing machine-specific, so a half-finished GPU run travels
  between boxes. Symlinked staging directories hash to the same key as the real
  file, which is how chunked resumption works.
- Demucs is pinned to CPU inside `identify_clip.py:644`. Runners patch
  `demucs.apply.apply_model` instead of editing the file, because identify_clip
  imports that symbol *inside* the function.
- The v2 cache's `hypotheses` field is a **real JSON list of dicts**, not a repr
  string. Read it structurally.
- Probe window filenames deliberately contain no `__`, so `identify_clip.py`
  skips truth-matching and the scorer joins against the sidecar instead.
- APFS filenames are **NFD**; JSON/manifest keys are NFC. A clip that "isn't in
  the manifest" is almost always Unicode normalization.
- macOS uses **fork**, not spawn; the matcher's worker pool depends on it. Tests
  set `CARNATIFY_MATCH_WORKERS=2`.
- `identify_clip.py` buffers behind pipes — use `python -u` for long evals, and
  background + `caffeinate -i` for anything over ~10 min.
- `backend/` holds a deploy-time **copy** of `identify_clip.py` that can shadow
  the root module; tests must insert root first on `sys.path`.
- `data/raga_aliases.json` maps 684 aliases → 101 canonicals with junk keys
  mapping to null. A `None` value means "not one of the model classes", **not**
  "not a raga".
- Rebuilding the composition registry reshuffles every `comp#####` id and breaks
  `data/wild_truth_manifest.json`. Merge at load time instead.
