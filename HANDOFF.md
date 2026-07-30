# Carnatify workhorse handoff

Last reconciled: **2026-07-30** (rewritten by the Opus 5 workhorse after
executing `WORKHORSE_PROBE_LAUNCH_BRIEF.md` and running the GPU job until Colab
credits ran out)
Repository: `/Users/shyamravidath/carnatify` · Branch: `main`
HEAD: `1ba3e1f` · `origin/main` observed at `62f9be9` (local is ahead)

This is the current operational handoff for the **workhorse / implementation
seat**. Older handoff documents remain useful as history; their status sections
are not authoritative. The durable experiment ledger is `AGENT_LOG.md` — append
exact outcomes there rather than paraphrasing them from memory.

**What changed in this rewrite.** The 2026-07-29 version described a probe that
was designed but not launched. Since then the whole launch brief was executed
(rule A applied, recall arm cut, Colab runner built) and **the GPU run started
and stopped part way**: 259 of 300 recall windows are transcribed and the
negative arm has not begun. §2.6 is new and is the only part of this document
that is time-critical. The graveyard in §4 is preserved and extended.

---

## 1. The goal

Carnatify should identify a Carnatic composition from a live performance
despite changes in artist, key, tempo, accompaniment and improvisation, and
present title, raga, sahitya and English meaning.

Product concept: a concert companion for Jon, a Western listener with no prior
Carnatic knowledge — progressively update a top-five list, offer candidate
detail pages, offer "none of these", and **never present a weak guess as a
confident identification**. The product bar is ~85% precision on what it
chooses to show; the pipeline has never met it.

**The immediate research question is narrower:**

> Does listening *longer* materially improve the current **lyrics matcher** on
> long-form concert audio?

That is the duration probe. Its gate is a paired **top-five** contrast from
**30s → 300s** with a **+15pp** boundary and a three-way verdict
(PROMOTE / KILL / INCONCLUSIVE). 90s → 300s is reported as the *product gap*,
not as the gate. The safety arm is a separate conjunction, gated under **rule A**
(§2.4).

**Scope corrections that must not be re-litigated:**

- The 60-67% full-recording result belongs to **Qmax**; the 8-13/78 wild-clip
  result belongs to the **lyrics matcher**. Comparing them was a
  matcher-identity confound.
- **Qmax cannot be evaluated on `data/concert_audio`** — `models/qmax_catalog.npz`
  was built from those recordings; it would be same-recording leakage.
- Even a positive duration result establishes only an **archive-domain
  lyrics-matcher curve**. Not wild-phone performance, not OOC safety, not
  "90s equals five minutes".
- The lyrics-ASR backbone is a confirmed dead end for the 85% bar, proven from
  two directions (precision curve ≤31% anywhere; LoRA fine-tune 8/78 → 0-1/78).
  The strategic pivot is the melodic/CoverHunter channel. The duration probe is
  a *diagnostic* on the ASR lane, not a revival of it.

---

## 2. Current state of the code

### 2.1 Production pipeline — unchanged and deliberately untouched

`identify_clip.py` is the single source of truth for inference. Everything in
this line of work edits **nothing** in it, including the Colab and AWS runners,
which patch module attributes at runtime instead. `git diff --stat
identify_clip.py` must stay empty and was verified empty at every step.

Product default: Whisper `large-v3-turbo`, cache v2, 4 mix passes + 3 Demucs
stem passes. `hybrid` / `hybrid_stem` are **experimental** and must not
silently replace the default.

**Wild scoreboard, 106 clips (78 in-catalog + 28 OOC):**

| backend | top-1 | top-5 | OOC reject | precision @ coverage |
|---|---|---|---|---|
| `whisper` (product default) | **8/78** | 21/78 | 21/28 (7 bluffs) | 17% @ 44% |
| `hybrid` | 11/78 | 25/78 | — | 20% @ 52% |
| `hybrid_stem` (best experimental) | 13/78 | 28/78 | — | 23% @ 53% |

Guard: `~/sung_tests_curated`, floor 8/36 (hybrid_stem reached 10/36).
Canonical command:

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

### 2.2 Duration probe — recall arm: **cut**

`scripts/duration_probe_cut.py --n 60 --arm anchored`, 2026-07-29. Dry run at
`--n 271` first reconciled exactly with pre-registration §1 (923 distinct title
keys / 505 matched-but-no-lyrics / **271 RESOLVED** / 117 too short / 30 no
registry match), so the pool has not drifted.

**300 windows, zero cut failures**, 11.0 h unique audio, in
`data/duration_probe/anchored/` with sidecar `truth_anchored.json`. Verified: 60
distinct titles × exactly 5 windows (30/60/90/180/300s), identical title sets at
every duration, one anchor per title, bijection with the sidecar, none empty, all
16 kHz mono. Nesting checked at sample level — the 30s window is an exact PCM
prefix of the 300s window. (A byte-level check on the files fails only because
ffmpeg WAV headers differ in length; the samples are identical.)

All 300 windows carry `audio_sha256` (`scripts/stamp_negative_shas.py --arm
anchored`), and the recall validity gate re-hashes them at read time exactly as
the negative gate does.

### 2.3 Duration probe — negative arm: labeled, staged, **not yet transcribed**

140 WAVs (70 items × 30s and 300s) in `data/duration_probe/negatives/`, sidecar
`truth_negatives.json`, both sweeps labeled and parsed.

| stratum | count | role |
|---|---:|---|
| `no-sahitya` | **49** | the only gating stratum |
| `sung_unidentified` | 10 | sensitivity, never gates |
| `in-catalog` | 9 | feeds no readout, but must still be transcribed (§2.6) |
| `unknown` | 2 | worst-case sensitivity |

Gating stratum by source: free-form 25, opening 20, unidentified 4, over 49
distinct clusters. Sheet 2 caught `neg053` and `neg020`, whose singing lived
entirely in the 150s sheet 1 never played — 4% of the single-sweep stratum was
contaminated.

**The OOC stratum is empty, and that is a finding, not a sampling failure.** Of
1,238 `concert_audio` recordings not one of the 11 unresolvable names a
composition, and the registry was itself partly built from these filenames.
**OOC abstention at 300s is unmeasurable from assets on disk.** Do not paper
over this by loosening the OOC definition — that is the defect that killed the
v1 arm.

### 2.4 The gate: rule A, applied

`DURATION_PROBE_PREREGISTRATION.md` §6b, frozen by Deepti 2026-07-29 and now
**applied by the scorer** (it previously computed rule A and applied the pooled
rule):

> SAFE requires the one-sided exact 95% upper bound below +15pp for **every
> source with n ≥ 20**.

Operationally: zero new bluffs in free-form (n=25, 11.3pp at b=0, 17.6pp at b=1)
and zero in opening (n=20, 13.9pp / 21.6pp). `unidentified` (n=4) reports
without gating. The pooled bound (5.9pp at b=0 on n=49) is still computed and
printed, labelled REPORTED, NOT GATING. The disagreement flag now fires when the
pooled bound *would* have passed a run rule A refuses — the case the gate exists
for.

`validate_negatives()` additionally refuses a run where a registered gating
source has gone missing, from the sidecar or from the results
(`gating_source_counts`, stamped by `parse_negative_labels.py`). Rule A is a
conjunction over whatever sources come back, so a lost source would otherwise
have dropped out silently and the survivors would have granted a SAFE the design
never authorised.

**Open finding for Deepti, not decided here.** The unknown-item sensitivity is
now also reported under the applied gate, and **it does not survive it**. The
two `unknown` items are one free-form and one opening, so the worst case moves
each gating source to b=1: free-form 1/26 → 17.0pp, opening 1/21 → 20.7pp, NOT
safe — where the pooled worst case (2/51 → 11.8pp) reads "still safe". Rule A
has no margin for the two unlabelable items. This is a property of the frozen
design, not a defect, and both numbers belong in any quoted result.

### 2.5 The runners

- `scripts/build_probe_colab_bundle.py` — verifies every window against its
  sidecar, then packs `probe_code.zip` (9 MB), `probe_anchored.zip` (1.27 GB),
  `probe_negatives.zip` (0.74 GB) into `~/carnatify_probe_bundle`. **Already
  built and verified; the zips are on disk and were uploaded to Drive.** WAVs
  ship as bytes because re-cutting elsewhere changes the hash, misses the cache,
  and breaks the label↔audio binding.
- `colab_duration_probe.py` — resumable Colab runner. Verifies SHAs before
  spending GPU, transcribes in symlinked chunks through
  `scripts/build_asr_cache_v2.py`, checkpoints the cache to Drive after every
  chunk, then runs `identify_clip` over both arms and refuses on any cache miss.
- `aws_duration_probe.py` — same loop for an EC2 GPU box: no Drive, S3
  checkpointing, per-chunk `run_log.json` (so an interrupted session still
  leaves a truthful record), and it stamps which windows came off which GPU.
- `scripts/merge_asr_cache_v2.py` — merges the returned cache into
  `data/asr_cache_v2.json`, refusing any key that exists in both with different
  content.

### 2.6 GPU RUN — **COMPLETE** (superseded, read this first)

**Corrected 2026-07-30, later the same day.** The table below described a
mid-session state that no longer holds. Deepti resumed the same notebook and it
ran to `anchored: fully cached` and `negatives: fully cached`. **All 440 windows
are transcribed and merged into `data/asr_cache_v2.json` (546 entries = 106
pre-existing + 300 + 140). No further GPU spend is required, and §5 below —
"finish the run on AWS" — is moot.**

The Colab session did end in an error, but not for want of GPU: step 5/6 died on
`ModuleNotFoundError: No module named 'rapidfuzz'`, a lyrics-matcher dependency
absent from the Colab image. Step 5/6 is `identify_clip --cache-v2`, which never
transcribes, so it was finished on the laptop instead. Both arms are inferred:
recall 300 rows / 0 cache misses; negative arm rows recorded in `AGENT_LOG.md`.

Superseded snapshot, kept for the audit trail:

| arm | cached | remaining |
|---|---:|---|
| recall (`anchored`) | ~~259 / 300~~ → 300/300 | — |
| negative (`negatives`) | ~~0 / 140~~ → 140/140 | — |

The Drive checkpoint `MyDrive/carnatify/duration_probe/out/asr_cache_v2.json` is
the whole GPU spend and has been merged locally. Keep a copy anyway.

Measured throughput, wall time per second of audio, all 7 passes plus Demucs:
**T4 1.56 s/s**, the later GPU (L4-class) **0.86 s/s**. So the honest total bill
is ~27 h on a T4 and ~15 h on an L4 — my original 10-20 h estimate assumed
openai-whisper decoded faster than it does at fp32.

**Mixed hardware — the device map IS now established** (resolved 2026-07-30 from
all 82 Google Drive revisions of the checkpoint; see
`data/duration_probe/DEVICE_MAP.md`). Three devices: T4 windows 1-80, L4-class
81-259, A100 260-300 plus all 140 negatives. **`probe0051` is the only straddler
and was excluded; `probe0016` is NOT one — that claim is refuted.** The probe has
been scored: recall **KILL**, safety NOT ESTABLISHED. The paragraph below records
why the earlier text could not be trusted, and is kept for the audit trail.

~~The device map is NOT established.~~ The earlier text here asserted both "windows 1-80 (`probe0000`-`probe0015`) came off a Colab T4,
81-259 off the faster GPU" and "`probe0016` is split, d030-d180 on the T4".
`probe0016` is windows 81-85, so those two claims cannot both be true. The
checkpoint chunk is 10 windows and the cache is written after each chunk, so a
clean stop lands on a multiple of 10 — and 259 does not. **The straddler set is
therefore not derivable from the stop index, and none of the old numbers should
be propagated.** Under `sorted(windows.items())` chunking, `probe0051` splits
across the 259 interruption exactly as `probe0016` splits across the device
boundary, so there are at least two candidates.

`colab_duration_probe.py` writes `run_log.json` at L316, *after* step 5/6 — the
step that died on `rapidfuzz`. **The file was never written and is not in
Drive.** The run's only provenance record was scheduled last. The notebook
output from both sessions is now the primary record; preserve it.

**The prescribed fix — drop the four `probe0016` cache entries and let them
re-transcribe — is rejected** (`DURATION_PROBE_PREREGISTRATION.md` §5b). It was
correct while the job still had a GPU; re-transcribing now happens on the laptop
and would put those windows on a third device *and* on the unpatched CPU-Demucs
path, trading a within-title confound for a worse between-title one.

What replaces it is frozen in pre-registration **§5b / §5b.1**: a 3-window
device calibration on the laptop, drawn from `probe0016` and `probe0051`, mix
hypotheses compared verbatim; identical → score as-is at the registered n;
differs → establish the map from surviving records and exclude every straddler;
differs with no recoverable map → the recall arm is reported **invalid**, a lost
measurement rather than a KILL. `scripts/duration_probe_device_cal.py` runs it
and writes `data/duration_probe/DEVICE_CALIBRATION.md`.

Measured throughput (below) remains the only quantitative device evidence, and
is what a map would have to be reconstructed from.

### 2.7 The GPU bill is 122 whisper-hours, not 116

`parse_negative_labels.py` bills 61 items (5.6 h, ~39 whisper-hours) because the
9 `in-catalog` negatives feed no registered readout. **They must still be
transcribed**: `validate_negatives` demands an exact bijection between the
negative sidecar and the result rows, so a run that skips them is invalid rather
than cheaper. The parser now prints both numbers.

### 2.8 Registry hygiene (separate lane, complete, unwired)

`scripts/registry_junk_filter.py` + `data/registry_junk_blocklist.json`: 52
flagged rows (19 `drop`, 33 `review`) behind a hard evidence gate. A/B'd on the
wild set: top-1/top-5/OOC all unchanged, answered 47 → 46 — it deletes exactly
one wrong answer. Deepti-gated; wiring it is a load-time merge in `load_targets`,
never a registry rebuild (ids are assigned by enumeration order).

### 2.9 Tests

```bash
venv_train/bin/python -m pytest tests/test_clip_policy.py \
    tests/test_registry_junk.py tests/test_negative_arm.py -q
# 95 passed, 1 xfailed
```

Never run bare `pytest tests/` — `test_audio.py`, `test_composition.py`,
`test_lyrics.py`, `test_pipeline.py`, `test_raga.py` and `test_tala.py` import a
`carnatify` package that does not exist and fail at collection.

---

## 3. Files actively being edited

**Written this session (all new, all untracked):**

- `colab_duration_probe.py`, `aws_duration_probe.py` — the two runners
- `scripts/build_probe_colab_bundle.py` — bundle packer + SHA verifier
- `scripts/merge_asr_cache_v2.py` — conflict-refusing cache merge
- `data/duration_probe/anchored/` — 300 recall windows
- `data/duration_probe/truth_anchored.json` — recall sidecar, SHA-stamped

**Modified this session:**

- `scripts/duration_probe_score.py` — rule A applied, pooled demoted to
  reported-not-gating, missing-gating-source suppression, per-source unknown
  sensitivity, shared `_verify_audio()` extended to the recall arm
- `scripts/parse_negative_labels.py` — stamps `gating_source_counts`, prints the
  bijection-inclusive GPU bill
- `scripts/stamp_negative_shas.py` — `--arm {negatives,anchored,prefix}`
- `scripts/build_negative_arm.py`, `scripts/build_negative_complement.py` —
  labeling-sheet swaram definition corrected (templates only; neither re-run)
- `tests/test_negative_arm.py` — 40 → 48 tests
- `HANDOFF_SESSION_0728.md` §5 — swaram lesson added to the graveyard
- `AGENT_LOG.md` — appended

**Do not touch:**

- `identify_clip.py` — the probe edits nothing in the scoreboard path
- `data/duration_probe/v1_superseded/` — audit trail, not reusable
- `scripts/build_negative_arm.py` at **runtime** — re-running it re-draws every
  anchor, re-assigns every `negNNN` id and re-shuffles the sheet, destroying
  both sheets of labels. Editing its template strings is safe; executing it is
  not.
- `CODEX_*_REVIEW*.md` — review artifacts, read-only

---

## 4. What has been tried and failed

The canonical graveyard is `REVIEW_BRIEF.md` §4 and `HANDOFF_CLIP_ID.md` §5.
Everything here stays dead absent genuinely new evidence.

### Lyrics / ASR identification

- Never exceeded ~31% precision at any threshold, tier or configuration.
- Confidence scores do not separate correct from incorrect (true/bluff score
  medians 1.28 / 1.25, interleaved down the whole ranking).
- Cross-channel agreement peaks at ~43% precision on 7 clips — whisper and
  indic errors are **correlated**.
- Max fusion, raga gating, extra answer gates, prompted/forced Whisper variants:
  no useful gain. A ranker fitted on the 78-clip eval set overfit.
- Character n-grams, vowel squashing, title-IDF weighting, DTW/Qmax fusion:
  dead ends.
- Indic CTC translit as a **default**: 8% precision @ 91% coverage, 27/28 OOC
  bluffs. Same failure class as the parked whisper-translit "3b" channel.

### ASR fine-tuning

- Whisper-small LoRA on ~80 min of weak Saraga supervision collapsed 8/78 →
  **0-1/78**, memorizing ~26 pallavis.

### CoverHunter / learned audio retrieval

- Source-disjoint CSI eval: mAP 0.113, hit rate 0.161, chance ≈0.031. The
  earlier 0.327 was inflated by ~2/3 leakage.

### Qmax / contour matching

- Valid 60-67% only in its original full-recording context, and **untestable on
  `concert_audio`** (leakage). On wild 30-60s clips: **0%**.

### Raga and tala

- TDMS raga: 72.8% top-1 on full tracks, **0/10** on wild short clips.
- Tala: 16.5% → 32.9%, both below a 72% majority-class baseline.

### Duration-probe designs rejected or repaired

- Failing to strip `_rN` and to deduplicate by registry id shrank the pool to
  79/133 instead of 271.
- Independent per-duration offsets measured *a random excerpt*, not the value of
  more listening. Now nested from one anchor.
- Strict monotonicity + binary promote/kill was statistically invalid; replaced
  by the three-way CI rule.
- **Asking a listener to label "out of catalog" by ear was a category error.**
  Catalog membership is a lookup over 8,688 rows.
- **v1 negative arm, rejected in full:** excerpts cut at fixed 15/50/85% while
  scored windows came from an independent anchor; also inferred OOC from failed
  filename lookups, so ≥3 of 12 nominal OOC items were verified in-catalog.
- **One sweep at 50% duty was also not enough** (round 2), and sheet 2 proved it
  empirically: 2 of 51 items had singing only in the unheard half.
- **A listening sheet whose categories describe a taxonomy rather than the music
  as performed.** Both sheets filed bare `swaram` under `no-sahitya`, which is
  wrong for swarakalpana — solfège alternating with the composition's sahitya
  line. Caught only because Deepti labelled `neg030` against the sheet she was
  reading from. Templates fixed for the next sheet.
- `str.maketrans('dbgjmz','ptkcns')` maps d→p and b→t. The lesson is the
  calibration set, not the typo.
- A dry run that writes: `duration_probe_cut.py --dry-run` regenerated
  `pool_report.json`. Fixed 2026-07-29.

### Duration-probe *execution* failures, new this session

- **Estimating GPU cost from model size rather than from the decoder.**
  openai-whisper's reference implementation at fp32 runs ~5× realtime on a T4,
  not the ~10× assumed, and 7 passes multiply it. Predicted 10-20 h, measured
  ~27 h on a T4. Always quote wall-seconds per audio-second measured on the
  actual box.
- **Checkpointing at 10 windows was too coarse.** A Colab interruption cost up
  to 35 min of GPU. CHUNK=5 (one recall title) makes an interruption cost ≤10
  min and lands checkpoints on title boundaries, which also keeps a title's five
  windows on one device.
- **A cache checkpoint copied mid-chunk split a title across GPUs.**
  `probe0016` now has four windows from a T4 and one from an L4. Cheap to fix
  (§2.6) but it is exactly where a device difference would hide, since the gate
  is a within-title 30→300 contrast.
- **Colab interrupts idle sessions.** The KeyboardInterrupt that killed the run
  at window 259 was not a bug in anything; the tab has to stay awake. On a real
  box this is `tmux`.

### Deployment

The deployed Hugging Face Space still exposes legacy behavior (~16% composition,
40.5% raga historically). It does **not** represent the current local pipeline.

---

## 5. The next step

**Finish the GPU run on AWS.** Deepti has $200 of free credits, so the remaining
~7 h costs nothing out of pocket, and the job is already resumable from the
Drive checkpoint.

1. **Protect the checkpoint.** Download
   `MyDrive/carnatify/duration_probe/out/asr_cache_v2.json` (~259 entries) to the
   laptop and keep a copy. It is the whole GPU spend so far.
2. **Quota first — it is the long pole.**
   `aws service-quotas get-service-quota --service-code ec2 --quota-code
   L-DB2E81BA --region us-east-1`. If `Value: 0`, request 8 vCPUs for "Running
   On-Demand G and VT instances" before doing anything else.
3. **Push the payload to S3 while waiting** (S3 needs no quota):
   the three zips from `~/carnatify_probe_bundle` and the cache checkpoint.
4. **Launch** g6.xlarge (L4) or g5.xlarge (A10G), Deep Learning OSS Nvidia
   PyTorch AMI, 100 GB gp3, SSH from one IP. `pip install -q openai-whisper
   demucs librosa soundfile`, `apt-get install -y ffmpeg unzip`.
5. **Run under tmux:**

```bash
python aws_duration_probe.py --root ~/probe --bundles ~/probe --chunk 5 \
    --s3-checkpoint s3://<bucket>/checkpoint \
    --prior-hardware 'Colab: T4 windows 1-80, L4 windows 81-259'
```

   It must print `inherited cache: 259 entries` and then
   `anchored: 259/300 already cached`. If it says 0, stop — the checkpoint did
   not land, and a second full run is being paid for.
6. **Drop the four `probe0016` entries** (§2.6) so no title straddles two GPUs.
7. **Terminate the instance** when it prints the scorer commands. Stopping still
   bills EBS.
8. **Merge and score on the laptop:**

```bash
venv_train/bin/python scripts/merge_asr_cache_v2.py \
  /tmp/probe_handback/asr_cache_v2.json

venv_train/bin/python scripts/duration_probe_score.py \
  --results /tmp/probe_handback/probe_results.json \
  --truth data/duration_probe/truth_anchored.json \
  --negative-results /tmp/probe_handback/negative_results.json \
  --negative-truth data/duration_probe/truth_negatives.json
```

Copy the scorer output **verbatim** into `AGENT_LOG.md` with the exact command,
cache validity, sample counts, exclusions, interval and decision, and record
beside it the two GPUs, the Demucs-on-CUDA deviation, and the unknown-item
sensitivity from §2.4. **Never recompute a friendlier statistic after seeing the
data.**

---

## 6. Pending Deepti — do not decide these

1. **The unknown-item sensitivity under rule A** (§2.4). It fails where the
   pooled sensitivity passes. Nothing to fix; it needs to be *decided* how the
   result is stated if the observed b=0 holds.
2. **Prospective long OOC audio** — the only route to measuring OOC abstention
   at length. `~/sung_tests/fetch_manifest.tsv` retains source URLs and
   durations, so this is reacquisition rather than discovery; 9 reviewed OOC
   sources carry a parseable source duration ≥300s.
3. **The 28-clip short-OOC sentinel** — nested 30s → full-clip (43-84s) over
   existing reviewed OOC clips, reusing existing caches. n=28 gives 10.1pp at
   b=0, 15.9pp at b=1. It **cannot** speak to 300s and must be pre-registered as
   non-gating before it is built.
4. **The registry junk blocklist** — 19 `drop` + 33 `review` rows, unwired.
   `comp01994` is the one `drop` row with real recall cost. `comp06030` "Ragam
   Thanam Pallavi", a section name the live matcher can return as a composition,
   is not on the blocklist.
5. **The commit.** Nothing in this line of work is committed. That is now a lot
   of untracked work, including 2 GB of cut audio that is deliberately not
   committable — decide what is tracked before the tree gets harder to read.

---

## 7. Guardrails

- **Do not commit or push.** Deepti owns repository history. Do not reset, clean
  or revert the dirty worktree.
- Do not change the product default from `whisper`.
- Do not run Qmax against `data/concert_audio`.
- Do not re-run `scripts/build_negative_arm.py` (§3).
- Do not loosen the OOC definition. That defect killed the v1 arm.
- Do not revert rule A to a pooled gate — that is a pre-registration change
  requiring a registered argument for the mixture weights.
- **Do not change anything that feeds `asr_config_id()`** — model, `fp16`,
  language lanes, separation. It is the cache key, so a change silently
  invalidates every window already paid for. This is why Whisper runs fp32 even
  on a GPU and why that is not a bug to fix.
- Do not retune a threshold after seeing a SCORE.
- Do not treat a duration-probe pass as wild-phone readiness, or as
  authorization to show results to a user. Only the `no-sahitya` stratum gates;
  OOC abstention at length is unmeasured.
- **Flag, never self-adjudicate, a truth change that favors your own result.**
- Preserve exact metric definitions and keep lyrics-matcher, Qmax, hybrid and
  hybrid-stem numbers distinct.
- Respond to Deepti in caveman style; write docs, commits and `AGENT_LOG.md`
  entries in normal prose.

---

## 8. Environment facts worth not rediscovering

- `venv_train` is py3.11. **ffmpeg 8.1.2 is installed** at
  `/opt/homebrew/bin/ffmpeg` (the "no local ffmpeg" line in `ARCHITECTURE.md`
  is stale).
- `--cache-v2` is keyed by **`audio_sha256`**, not filename. The `path.name`
  collision hazard is in the **legacy** `transcribe()` path only.
- Cache keys contain nothing machine-specific, so a half-finished GPU run
  travels between boxes. Symlinked staging directories hash to the same key as
  the real file, which is how chunked resumption works.
- Demucs is pinned to CPU inside `identify_clip.py:644`. Both runners patch
  `demucs.apply.apply_model` instead of editing the file, because identify_clip
  imports that symbol *inside* the function.
- Probe window filenames deliberately contain no `__`, so `identify_clip.py`
  skips truth-matching and the scorer joins against the sidecar instead.
- APFS filenames are **NFD**; JSON/manifest keys are NFC. A clip that "isn't in
  the manifest" is almost always Unicode normalization.
- macOS uses **fork**, not spawn; the matcher's worker pool depends on it.
  Tests set `CARNATIFY_MATCH_WORKERS=2`.
- `identify_clip.py` buffers behind pipes — use `python -u` for long evals, and
  `run_in_background` + `caffeinate -i` for anything over ~10 min.
- `backend/` holds a deploy-time **copy** of `identify_clip.py` that can shadow
  the root module; tests must insert root first on `sys.path`.
- `data/raga_aliases.json` maps 684 aliases → 101 canonicals with junk keys
  mapping to null. A `None` value means "not one of the model classes", **not**
  "not a raga".
- Rebuilding the composition registry reshuffles every `comp#####` id and breaks
  `data/wild_truth_manifest.json`. Merge at load time instead.
