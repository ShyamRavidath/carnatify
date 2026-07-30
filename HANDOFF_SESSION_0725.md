# HANDOFF_SESSION_0725 — the pivot session (Opus 5 verifier seat)

Written 2026-07-25 for **whoever holds the verifier/orchestrator seat next**.
Supersedes `HANDOFF_SESSION_0724.md` on strategy; that file is still correct on
roster, scoreboard discipline, and the graveyard.

Read order: this file → `AGENT_LOG.md` newest-first → the design doc at
`~/.gstack/projects/ShyamRavidath-carnatify/shyamravidath-main-design-20260725-200117.md`
→ `HANDOFF_CLIP_ID.md` §5 (graveyard) and §8 (gotchas).

Respond to Deepti in **caveman style** (standing preference); write docs, commits,
and AGENT_LOG entries in normal prose. Never commit or push — that is hers.

---

## 0. What changed today, in one paragraph

Door 1 (melodic CoverHunter CSI) was put through its own go/no-go gate and did
not clear it: clean source-disjoint mAP **0.113** against a 0.031 chance floor,
versus the ~0.30 bar the recipe set. That closed the last identification channel
that could have been fixed without new data. Rather than narrow the product,
Deepti ran a full `/office-hours` startup diagnostic, and the session produced a
different diagnosis than "the models are bad": **every measured failure is on
30-60 second clips, and the same pipeline scores 60-72% on full recordings.**
The plan is now to test whether listening length is the actual constraint, then
build a concert companion that ships to a real named user. The product vision is
unchanged. The input contract is what moved.

---

## 1. The goal we are working toward

**Product goal (unchanged, restated by Deepti this session):** Carnatify is a
Carnatic music identification and enrichment app. It (a) identifies which
composition is being performed from live audio, tolerant of artist, tempo, and
improvisation — unlike exact-fingerprint approaches like Shazam — and (b)
classifies the raga, including on improvised passages where no fixed composition
exists. Both feed one display: **composition name, raga, sahityam, English
meaning.** Composer and tala are parked.

**Product target set this session:** reach the accuracy of a 5-minute listen in
**90 seconds or less**. Long-listening is how the system earns accuracy today,
not the shipping UX.

**User:** Jon — a real person, a Western listener with zero exposure to the
tradition, named after being pushed for specificity. Every design argument now
gets settled against Jon rather than against Deepti's own taste (she is a trained
Carnatic musician and therefore the least representative user of a beginner tool).

**Non-goals for now:** notation-first features (that serves a different user, the
beginner student), tala and composer prediction, native iOS, App Store, accounts,
any paid infrastructure.

**Secondary goal that shapes tradeoffs:** this is a passion project and evidence
for college admissions. That argues for shipping to real users early — a working
link that people use beats a polished unpublished app with better numbers.

---

## 2. Strategic state — what is dead, what is alive

### Dead, with measurements (do not reopen without new data)

1. **Lyrics-ASR as a shippable backbone.** Matcher precision never exceeds ~31% at
   any threshold, tier, or config (`scripts/precision_coverage_curve.py`). There is
   no operating point where the app can claim confidence.
2. **Fine-tuning sung-Carnatic ASR on the current data.** LoRA Whisper-small on 80
   min of weakly-aligned Saraga pallavi made it strictly worse: 8/78 → 0-1/78,
   memorized ~26 pallavis, emitted their tokens for unrelated audio.
3. **The current CoverHunter checkpoint as a CSI engine.** Clean source-disjoint
   mAP 0.113, hit_rate 0.161, chance 0.031 (3.6x chance, real but weak). The
   contaminated dev number was 0.327; roughly two thirds of it was same-recording
   leakage.

### Alive

1. **Full-recording performance.** Composition cross-artist 60-67% top-1 (Qmax),
   raga 72.8% top-1 / 84.7% top-3 (18 ragas, grouped CV, leak-free). Same music,
   same pipeline family, radically better numbers. This is the strongest asset the
   project has and it has never been exploited product-side.
2. **The duration hypothesis (P1, explicitly a hypothesis, not a premise).** Input
   length is the *leading* candidate explanation for the collapse. Codex attacked
   this correctly in a cold read: full recordings and wild clips differ in
   duration AND recording quality AND segmentation AND catalog distribution, so
   duration is confounded. It must be tested with everything else held constant.
3. **The data lever.** Deepti will not run a user-recording retraining loop right
   now, but **will collect data available on the internet**. That distinction is
   about dependence on users she does not have, and it is reasonable. The
   CoverHunter model's weak mAP has two *recorded* causes — the cumulative-speed
   augmentation bug and same-recording contamination — not a proven data shortage.
   (Correction, caught in adversarial review: the "28 songs with 2+ distinct
   recordings" figure is the **validation** subset, `COVERHUNTER_RESCORE.md:22`,
   not the training set. The training composition is not established. Do not
   repeat the "starved model" claim as fact.) Separately, `data/concert_audio/`
   holds 65 titles with 2+ renditions, so a cheap retrain on existing data should
   be costed before any three-month scrape.
4. **Uncertainty as a product surface.** Deepti endorsed a ranked top-5 with
   honest confidence over a single authoritative answer, while still wanting the
   numbers up. This lowers the shipping bar without lowering the engineering bar.

---

## 3. What this session actually did

1. **CoverHunter Stage-1 clean re-score, executed and interpreted.** New
   `colab_coverhunter_rescore.py` (inference only). Result and both defects found
   are logged in `AGENT_LOG.md` under 2026-07-24.
2. **Two defects found while building that eval, both real:**
   - `extract_csi_features` applies speed augmentation **cumulatively**
     (`sp_0.8-X` → `sp_0.9-sp_0.8-X` → …), so **no clip exists at natural playback
     rate**; effective factors span only 0.72-0.95 and the no-op 1.0 pass emits a
     duplicate. ~40% of the augmentation budget was wasted and the intended
     0.8-1.2 range was never realized. Any retrain must fix this first.
   - My own first chance-floor formula averaged (s-1) over songs instead of over
     clips, printing 0.006 instead of 0.031. Fixed in the script with a comment.
3. **A full `/office-hours` startup diagnostic** (six forcing questions, premise
   challenge, Codex cold read, four alternatives). Output: the design doc named
   at the top of this file. Approved by Deepti with one revision (the 90-second
   target).
4. **Fable's exit handoff** landed at `HANDOFF_WORKHORSE_FABLE_TO_OPUS5.md`
   (uncommitted). Read it before touching the hybrid/Indic lanes.

---

## 4. Current state of the code

**What runs today, and how:**

```bash
# the only scoreboard that counts
venv_train/bin/python identify_clip.py ~/sung_tests --no-raga --cache-v2
CARNATIFY_ASR_BACKEND=hybrid      venv_train/bin/python identify_clip.py ~/sung_tests --no-raga --cache-v2
CARNATIFY_ASR_BACKEND=hybrid_stem venv_train/bin/python identify_clip.py ~/sung_tests --no-raga --cache-v2

# guard (floor: top-1 >= 8/36)
venv_train/bin/python identify_clip.py ~/sung_tests_curated --no-raga --cache-v2

# tests (30 pass, 1 xfail). Other tests/*.py are STALE scaffold that import a
# nonexistent `carnatify` package — ignore their collection errors.
venv_train/bin/python -m pytest tests/test_clip_policy.py -q
```

**Standing numbers:** whisper 8/78 top-1 (product default), hybrid 11/78,
hybrid_stem 13/78 (both opt-in experimental), guard 10/36, OOC 24/28.

**Scoreboard facts measured today:** `~/sung_tests` is n=106 clips, **min 43s,
median 60s, max 98s**. This matters: the duration probe *cannot* be run past ~90s
on existing data. Filenames carry ground truth as `<title>__<raga>[__OOC].ext`.

**Environment:** venv_train py3.11, numpy<2.5, macOS fork-not-spawn, NFD cache
keys. **`ffmpeg 8.1.2` IS installed** at `/opt/homebrew/bin/ffmpeg`, verified
2026-07-25 — the "no local ffmpeg" line in `ARCHITECTURE.md` and
`HANDOFF_SESSION_0724.md` §5 is stale and inflated the cost of anything involving
audio slicing. Demucs on CPU is still slow enough to prefer Colab. Colab Pro is
available; all GPU work is Deepti-run. No paid infrastructure.

**Deployed:** the Hugging Face Space still serves the legacy endpoints
(`backend/main.py` ~L173, ~L366) at ~16% composition / ~40.5% raga. It has not
been updated to the current pipeline and is not part of the current plan.

---

## 5. Files actively edited / uncommitted state

Nothing is committed; Deepti pushes. `git status` at handoff time:

**Modified:** `.claude/settings.local.json`, `.gitignore`, `AGENT_LOG.md`,
`build_wild_truth_manifest.py` (tier-1 bless + 3 work-families, metadata-only,
score-neutral), `data/wild_truth_manifest.json`.

**New, mine this session:**
- `colab_coverhunter_rescore.py` — Stage-1 clean re-score runner. Self-contained,
  resumable, auto-remounts Drive on `Errno 107`, copies only the latest checkpoint
  pair, and selects one line per recording from the cumulative aug chains.

**New, prior sessions (all uncommitted):** `scripts/precision_coverage_curve.py`,
`scripts/cross_channel_agreement.py`, `scripts/score_external_transcripts.py`,
`scripts/clean_saraga_trainset.py`, `scripts/build_saraga_pilot_zip.py`,
`scripts/build_saraga_asr_trainset.py`, `scripts/detect_workfamily_dupes.py`,
`colab_asr_finetune.py`, `data/saraga_asr_trainset*.json`,
`data/workfamily_candidates.json`, `data/whisper_transcripts_fw_int8.json`,
several `CODEX_*_BRIEF.md` / `FABLE_*_PROMPT.md`, `HANDOFF_SESSION_0723.md`,
`HANDOFF_SESSION_0724.md`, `HANDOFF_WORKHORSE_FABLE_TO_OPUS5.md`, `CLAUDE.md`.

**Load-bearing vs disposable:** the ASR-fine-tune scaffolding
(`colab_asr_finetune.py`, `saraga_asr_trainset*`, `build_saraga_pilot_zip.py`) is
**closed direction, keep for the record only**. `saraga_pilot.zip` (465 MB) is
gitignored and can be deleted. `precision_coverage_curve.py` and
`score_external_transcripts.py` are the diagnostics that proved the wall and
should be committed.

**Pending Deepti's gates:** remaining `review:True` flags (bhajare, Kamakshi Ni,
Ranga Baro, alapana1/2), `data/registry_junk_blocklist_DRAFT.md`, and the push.

---

## 6. Everything tried that failed (consolidated graveyard)

Do not re-run any of these without new data or a stated reason the conditions
changed. Full detail in `REVIEW_BRIEF.md` §4, `ARCHITECTURE.md`, and
`HANDOFF_CLIP_ID.md` §5.

| attempt | result | why it failed |
|---|---|---|
| Qmax / DTW melodic matching on wild clips | 0/8-10 | 30-60s of an improvised rendition carries too little melodic evidence |
| Raga TDMS classifier on 60s wild clips | 0/10 top-1, 1/10 top-3 | domain mismatch: trained on clean full tracks |
| Real-audio Saraga raga retrain (Demucs+pyin) | 5% CV | data sparsity |
| Synth/augmented wild training set | 0/80 top-1 | pitch shift + codec destroys the signal it was meant to teach |
| Prompted / `kn`-forced Whisper decoding | no gain | language forcing does not survive sung, gamaka-heavy audio |
| Max-fusion, raga gating, new answer gates | no gain, some regressions | fusing two weak channels on tiny n |
| Fitted ranker on tiny n | overfit | 78 scored clips cannot support a learned ranker |
| IndicConformer-600M CTC lane alone (Rung 3) | did not graduate | see `HANDOFF_WORKHORSE_FABLE_TO_OPUS5.md` |
| LoRA Whisper-small fine-tune (Rung: ASR pilot) | 8/78 → 0-1/78 | 80 min of single-artist weakly-aligned audio teaches memorization |
| CoverHunter CSI, current checkpoint | clean mAP 0.113 | cumulative-speed aug bug (nothing at natural rate) + same-recording contamination in the dev metric |

Two meta-lessons that cost the most to learn, from `HANDOFF_CLIP_ID.md`:
**benchmarks lie, wild clips don't**, and **every internal benchmark built so far
was flattered by same-corpus effects.** Any new eval must be checked for leakage
before its number is believed. The CoverHunter dev mAP of 0.327 is the most recent
example: 75% of val clips had a different crop of the same recording in the
reference pool.

---

## 7. The next step

**Approach A — the duration probe. Do this before anything is built.**

Goal: settle whether listening length is the constraint, with everything else held
constant. Method:

1. **The audio already exists on disk.** `data/concert_audio/` — 1,238 recordings,
   composition identity in the path (`<raga>/<title>[_rN].mp3`), 1,118 distinct
   titles, **65 titles with 2+ renditions (185 files)**, sampled median duration
   417s with 29/40 over five minutes. Verified 2026-07-25. An earlier draft of this
   handoff called long audio "the one real blocker"; that was wrong, and it would
   have cost a week of unnecessary collection. Use the 65 multi-rendition titles.
2. For each item, cut windows at **30s / 1min / 3min / 5min**, preprocessing
   identical across windows, locally with `ffmpeg`. **Randomise the start offset
   and report prefix-anchored and random-offset windows separately.** A fixed start
   makes the 30s window a strict prefix of the 5-min window, and items usually open
   with alapana, which is lyric-free by definition — so under a fixed start the 30s
   condition is the worst possible window for a lyrics matcher by construction and
   a rising curve would prove nothing. Write each window to a **distinct basename**:
   `identify_clip.py:619` caches transcripts keyed by `path.name`, so identical
   names silently serve the 30s result for the 5-min query.
3. Score with **`CARNATIFY_ASR_BACKEND=whisper` only** (product default,
   one-change-one-eval), publishing **all five `METRIC_CONTRACT.md` numbers
   together** at each duration — precision@coverage, in-catalog top-1 and top-5,
   OOC bluff rate, eligibility strata. Reuse `identify_clip.py` and
   `scripts/score_external_transcripts.py`. Lyrics channel only for now: it matches
   transcripts against the text registry, so `concert_audio` carries no audio-leak
   risk. A *melodic* probe on the same files would be same-recording leakage if
   they fed `models/qmax_catalog.npz` — check first.
4. **Pre-register the gate before looking at the plot.** Promote P1 only if both:
   (a) ≥15pp absolute gain in in-catalog top-5 from 30s to 5min, and (b) monotone
   non-decreasing across all four durations. At n=65 the binomial SE is ~±6pp, so
   anything smaller is noise. Then:
   - **gate passes** → P1 promoted. Progressive listening is justified; move to
     Approach B and start closing the 5-min → 90s gap.
   - **gate fails** → P1 is dead and it is the fourth measured wall. The cause is
     domain shift or weak representations, and the roadmap turns to the corpus.
   This probe is a **declared exception** to the frozen-scoreboard rule: it runs on
   different audio, and its numbers never graduate anything on their own.
5. On the same data, answer open question 6: **which** 90 seconds carry the most
   evidence? A window containing the pallavi should beat an arbitrary one. If it
   does, segment-aware window selection closes part of the gap for free and is the
   cheapest lever available.

**Approach B — the concert companion** (only after A returns): web app, one
"Start listening" button, progressive top-5 that visibly re-ranks, candidate pages
with raga + sahityam + English meaning, "none of these" correction capture, manual
search as a guaranteed-useful fallback, admin view plotting accuracy vs listening
duration. Free hosting, no Apple fee, distributed as a link. Filter the known
registry junk (address/date rows parsed as compositions) before any user sees a
search box.

**Approach C — the rendition corpus** (150-200 compositions × 5-10 cross-artist
renditions, retrain with the augmentation bug fixed) stays queued behind B's
evidence. It has the highest ceiling and the longest delay to any user.

**Deepti's assignment from the office-hours session, which outranks all code:**
take Jon to one Carnatic concert, watch him without helping, and write down every
question he asks out loud and the moment he loses the thread.

---

## 8. Discipline (unchanged, bought expensively)

- `~/sung_tests --cache-v2` is the ONLY scoreboard. Only a moved SCORE graduates.
- One change, one eval. Own the verbatim SCORE + precision@coverage + OOC + guard.
- Manifest/registry changes move ALL configs → re-baseline everything, and verify
  equivalences independently of score.
- whisper stays the product default; hybrid / hybrid_stem are opt-in experimental.
- Verify every claim against the scoreboard before repeating it. Several numbers in
  this project have been wrong in the confident direction, including two of mine
  today (the chance floor, and "one afternoon on data you already have").
- Agents coordinate only through files on disk and `AGENT_LOG.md`. No commits.
