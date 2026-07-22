# HANDOFF_SESSION_0721 — honest re-baseline, doc package, and the Fable↔Codex loop

Written 2026-07-21, **updated same day after the Codex review completed**.
Audience: **Fable** (the incoming Claude agent), working alongside **Codex
(GPT-5.6)**. Predecessors, read cold in this order: HANDOFF_SESSION_0719B.md
(CoverHunter Colab), HANDOFF_SESSION_0719.md, HANDOFF_SESSION_0718.md, then the
consolidated `handoff_state_and_progress.md` + `handoff_vision_and_architecture.md`.
This file covers what changed and how the two-agent collaboration works.

**IF YOU ARE RESUMING MID-STREAM: the review is DONE and vetted; the active
task is implementing Phase 0. Jump to §0.5.** Read §0 for the protocol, but do
not re-run the review — it already happened.

---

## 0. FABLE — START HERE (the Fable↔Codex protocol)

You and Codex are two separate CLIs on the same repo. **You cannot see each
other's chat, ever.** You collaborate only through files on disk + git. That
is the entire mechanism; internalize it.

**The shared channel is `AGENT_LOG.md`** (append-only; roles are asymmetric —
Codex reviews/proposes read-only on code, Fable is the only one that edits
code / runs eval / commits). Codex's full review is in **`CODEX_REVIEW.md`**
(31 KB, already written); Fable's vetting of it is the 2026-07-21 19:30 entry
in `AGENT_LOG.md`. The review is complete — see §0.5 for the outcome. Do not
re-run it or invent findings; everything is on disk.

**How to evaluate Codex's proposals (this is your core job, not rubber-stamping):**
- Check every proposal against the **graveyard table in REVIEW_BRIEF.md §4**
  and the failure log in `handoff_state_and_progress.md §4`. A strong cold
  model *will* confidently re-propose DTW on pitch contours, raga-gating,
  prompted-whisper, or "just add a language to whisper" — all measured dead.
  Catch these; cite the measured number when you reject one.
- Check against `OPEN_DECISIONS.md` — do not let it re-propose things already
  parked on Deepti (deploy, the meanings batch, ear-checks).
- **The only scoreboard is `~/sung_tests`.** No idea graduates on reasoning
  alone; it graduates when the SCORE block moves. Same-corpus numbers
  green-light nothing — this rule was bought expensively (see §4 below).

**The loop:** Codex writes to disk → you read, evaluate, implement the ideas
that survive → you write decisions/results back to `AGENT_LOG.md` → Codex reads
that on its next pass. Keep the loop on disk.
When you implement something, run the eval and quote the SCORE block in the
log so Codex sees real evidence, not claims.

Deepti wants you two working in harmony. Harmony here = disciplined file-based
exchange + the wild-eval as the shared source of truth. She is the domain
authority (Carnatic musician) and the human in the loop for anything musical,
any spend, any deploy, any push.

## 0.5 REVIEW OUTCOME + PHASE 0 (the active task, greenlit by Deepti)

The Codex review is complete, and Fable verified every code-level claim against
source (line numbers in the `AGENT_LOG.md` 19:30 entry — all confirmed). It is
graveyard-clean: no dead approach resurrected, no OPEN_DECISIONS item touched.
One recorded nuance: the graveyard's "retry ONLY via ctranslate2" applies to
the **vasista22 Whisper finetunes**; Codex's native-**ONNX** route for
IndicConformer is a different model family and does not conflict.

**Verified defects (in `identify_clip.py`, 646 lines — REVIEW_BRIEF §8's
"~1,500" is stale; fix that):**
- **P0 `fold()` erases native scripts** (`identify_clip.py:80-83`): keeps only
  ASCII after NFKD, and `_whisper_multi` folds every hypothesis *before*
  longest-wins (line 362), so forced `ta`/`te`/`hi` decodes reduce to
  whitespace before matching. **Worst single defect — has been silently
  suppressing the exact Indic-script transcripts the ASR work aims to recover.**
- **P0 backend policy divergence**: `backend/clip_identify.py` lacks the
  `_max_token_run` loop gate and the `hi` language — the staged `/identify`
  runs a *different* policy than the scoreboard (`rama rama rama rama` gets
  "high" through the backend).
- **P1 many-to-one scoring exploit** (`_best_map` line 247, `_score_ktoks`
  line 290): no injectivity constraint + per-token repetition bonus → score
  unbounded, `rama rama` scores 1.451, thresholds are not probability-like.
- **P1 longest-transcript-wins** (line 362): discards language, segments,
  likelihoods, competing hypotheses.
- **P1 cache keyed by basename only** (lines 370-399): no audio hash, no
  model/config identity, non-atomic `write_text` → poisonable.
- **P2**: `--no-raga` prints fake `0/85` (line 638, the display bug already
  known); silent `except Exception: pass` (line 365); `workers=-1` unsafe on a
  2-vCPU Space (line 256).

**Strategic reframe — ACCEPTED:** primary metric becomes **precision at
coverage** (target ≥85% precision among *answered* clips), **always
co-published with overall top-1/top-5 + OOC** so abstention can't game it.
Motivating evidence: the current "high confidence" tier is only 8/16 correct —
the labels are not confidence. This must become the standing scoreboard format
(write it into `METRIC_CONTRACT.md` — does not exist yet).

**Phase 0 = correctness/observability, greenlit. Deepti's guardrails:**
1. **One-change-one-eval discipline applies (HANDOFF_0718 §6).** Three items
   change matcher/policy behavior and must each be evaluated *separately*
   against the 106 set, with the **original curated 36 clips as the regression
   guard** (they reproduce 8/36 — must not drop): (a) `fold()` Unicode
   preserve + transliterate, (b) one-to-one / bounded scoring, (c) the single
   shared policy function (backend adopts root's gate + `hi`). The rest
   (`--no-raga` honesty, silent-except, `workers`, regression tests incl.
   `rama rama`) are pure hygiene — apply freely, no eval needed. **Do not
   bundle all six into one commit — attribution is lost.**
2. **The cache re-version is the expensive step and collides with
   OPEN_DECISIONS #8.** Versioning the key invalidates the cache → forces a
   full 106-clip re-ASR (~6 h). First check whether the `fold()` fix even needs
   re-ASR (does the cache store *raw* whisper output, or already-ASCII-stripped
   text? if post-strip, the native script is already gone and re-ASR is
   forced). Use that same re-ASR to **strip the synth/control entries** (#8) so
   the versioned cache ships clean. Run it `caffeinate -dims -w <pid>`, lid open.
3. **Backend refactor is local only** — deploy stays Deepti-run (OPEN_DECISIONS #2).

Phase ordering after Phase 0 (Codex's, accepted): matcher alignment → ASR
experiments (VAD segments, IndicConformer via native ONNX, catalog-constrained
CTC) → calibration. All zero-cost, local/Colab. Detail in `CODEX_REVIEW.md`.

## 1. Goal (unchanged)

~60 s wild clip → composition (headline, top-5 UX ok) + raga (secondary,
honest confidence) + lyrics/meaning. Stated bar: 80–90% top-1. **Current: 14%.**
Read REVIEW_BRIEF.md §2 and §5 for the honest gap analysis and the
precision-at-coverage reframe — that reframe is open question #1 for the
review and may be the most important strategic decision on the table.

## 2. What this session did

- **Re-baselined the wild set on all 106 clips** (previous scoreboard was on
  the retired 63). Full run, raga included. SCORE block verbatim:
  ```
  ===== SCORE over 78 in-catalog + 28 OOC clips =====
  composition top-1 11/78  top-5 18/78
  OOC reject  24/28  (bluffs: 4)
  raga        top-1 18/85  top-3 21/85  (clips with known raga truth)
  raga via catalog backfill 8/36 (on clips with confident composition)
  ```
  **No code regression** — the original 36 curated clips reproduce the
  2026-07-18 baseline exactly (8/36 top-1, 23/27 OOC). The aggregate drop
  (22%→14%) is entirely set composition: auto-fetched clips are **64%
  ASR-dead** vs the ~1/3 the strategy docs assumed. Raga top-3 barely exceeds
  top-1 (21 vs 18) — when wrong, the true raga usually is not even top-3;
  wild-clip posteriors collapse, so reranking won't help, the lever is
  tonic/drone on the input. Full analysis in memory `wild-test-set-status`.
- **Wrote the review doc package** (all committed @ 9f3161f): `REVIEW_BRIEF.md`,
  `ARCHITECTURE.md`, `OPEN_DECISIONS.md`, `COVERHUNTER_RESCORE.md`, and rewrote
  `HANDOFF_VERFIER.md` from a stale state-ledger into a verification protocol.
  Tracked the two consolidated 0718 handoff docs.
- **Annotated the dead code** so the repo (and the graphify graph) stops lying:
  STATUS banners (GRAVEYARD / LEGACY / DEAD / CLOSED / LIVE) on 8
  `src/carnatify/ml/` modules + 42 symbols, each with its measured number and
  the live replacement. **Nothing deleted** — the graveyard melody modules
  (`dtw_matcher`, `contour_preprocessor`, `composition_matcher`) are
  transitively load-bearing for the deployed legacy endpoints in
  `backend/main.py`, and `build_space.sh` ships all of `src/`. See
  ARCHITECTURE.md.
- **Built a code graph** with graphify (`graphify-out/`, gitignored,
  regenerate with `graphify update . --no-cluster && graphify cluster-only .
  --no-label` — both LLM-free). Caveat baked into ARCHITECTURE.md: it is a
  navigation aid, not authority — `graphify query` does NOT surface the STATUS
  banners (BFS returns node names only); `graphify explain <symbol>` does, and
  reading the file always does. Do not let it lead you into the graveyard.

## 3. Current state of the code

`main @ b5b400a` (+ this handoff update), **8+ commits ahead of origin, NOT
pushed** (pushes are Deepti-run — OPEN_DECISIONS #1). No Phase 0 code edits made
yet as of this writing — Fable had not started implementing. Live matcher is
`identify_clip.py` (repo root, standalone, imports nothing from
`src/carnatify/`; 646 lines). Everything composition- or tala-related in
`src/carnatify/ml/` is legacy or graveyard — trust the STATUS banners.

Review/loop artifacts on disk (all committed except where noted): `CODEX_REVIEW.md`
(31 KB, Codex's full review), `AGENT_LOG.md` (the shared channel), and the doc
package (`REVIEW_BRIEF`, `ARCHITECTURE`, `OPEN_DECISIONS`, `COVERHUNTER_RESCORE`,
`HANDOFF_VERFIER`). `METRIC_CONTRACT.md` is the one accepted artifact NOT yet
written — Phase 0 should create it.

**Intentionally uncommitted, on disk (do NOT blind-commit):**
- `data/whisper_transcripts_turbo.json` / `_stems.json` — hold the valuable
  new 106-clip real transcripts (6 h of CPU) **mixed with ~90 synth/control
  junk entries** from the 0719a evals. OPEN_DECISIONS #8: strip the synth
  entries (filename-identifiable) BEFORE committing, or the eval cache ships
  poisoned. The real transcripts are safe on disk meanwhile.
- Pre-existing leftovers (`carnatic_varnam_1.1*`, `data/cnn_extra_audio/`,
  `data/whisper_transcripts_fw_int8.json`, `.claude/settings.local.json`,
  `.agents/skills/caveman/`) — untracked since before this session, leave them.

## 4. The rules that were bought expensively (do not relearn)

- **Wild eval (`~/sung_tests`, 106 clips) is the only scoreboard.** Qmax scored
  63–67% same-corpus and 0% wild. A "55% e2e" number was recording-family
  flattered. Even this session's curated-22% was flattered vs auto-fetched-7%.
  Curation is a leak too.
- **Eval-set construction is part of the rule, not just eval results.** The
  CoverHunter CSI run hit dev hit_rate 1.0 — but 75% of val clips had a
  different crop of the *same source recording* in the ref pool, so it measured
  near-fingerprinting. Clean re-score recipe: `COVERHUNTER_RESCORE.md` (137
  source-disjoint clips exist; it's a Colab job — the checkpoint/features are on
  Drive). Ask before believing any metric: *what is the cheapest way to get
  this number that isn't the capability we want?*
- **Degraded audio → confident whisper hallucination that defeats the gates.**
  No confidence signal in this system is trustworthy without calibration. The
  fix is score calibration, not more gates (the gates were tried; bluffs
  adapted around each).

## 5. Where the measured leverage is (payoff-ordered)

Grounded in the 64%-ASR-dead / 20%-matcher-conversion decomposition:

1. **ASR step change** — biggest measured lever. IndicConformer-600M and
   IndicWhisper via **ctranslate2** (never actually evaluated here — the three
   prior attempts were transformers-pipeline integration failures, NOT model
   verdicts). Plus GPU large-v3 on stems. Even perfect ASR → ~25–35%, because:
2. **Matcher conversion** — only 3/15 clips convert where ASR works. Untouched
   wall. Pallavi-line phonetic index; match whisper segment-alternatives, not
   the single final string; learned reranking.
3. **Clip-type router** — a large share of clips have no sahitya (alapana,
   thani, instrumental) and currently count as composition failures. Route them
   to raga-only. Fixes both the scoreboard's honesty and the UX.
4. **Score calibration / margin analysis** — converts the system to
   precision-first (the Definition-B reframe). Fixes the hardest bluff class
   (correct transcript, wrong match — Om Jai → pAhirAmadhoothA @1.201).
5. **Flywheel** (deploy staged backend + confirm UI) — the only source of the
   labeled wild clips that everything data-hungry above eventually needs.
   Deepti sign-off + Deepti-run deploy; private HF feedback dataset first.
6. Whisper fine-tuned on Carnatic sahitya via forced alignment (gated on #5).
7. CSI melody channel — only for no-lyrics clips, only if the clean re-score
   (COVERHUNTER_RESCORE.md) comes back alive.

## 6. Blocked on Deepti (see OPEN_DECISIONS.md — do not re-propose as "new")

Push the 6 commits; deploy the staged flywheel; raga model swap sign-off;
meanings batch stays UNSUBMITTED (she declined, gated on CARNATIFY_BILLING_OK=1);
Kurai Onrum + Paluke ear-checks; `rAma nannu brOvara` instrumental clip;
transcript-cache strip (#8); `composition_evaluator.py` deletion (she said
"later"); retire legacy backend endpoints before deleting graveyard modules.

## 7. Ops gotchas that bit this session

- **`identify_clip.py` is not run with `-u`** and buffers ~1 h behind through a
  pipe — track long-eval progress by transcript-cache key counts, not the log
  tail. Run it `python -u` if you pipe it.
- **`caffeinate -i` does NOT block lid-close or system sleep** — a Mac sleep
  suspended a 5 h eval mid-run (it resumed on wake, nothing lost, but hours of
  wall-clock gone). Use `caffeinate -dims -w <pid>` for long runs and keep the
  lid open.
- Env: two venvs, matcher/ASR/eval all in **venv_train** (py3.11). No ffmpeg —
  librosa/essentia, feed whisper numpy arrays. macOS fork not spawn. numpy<2.5.
- Registry has junk rows (addresses/dates) — never trust its raga metadata
  without a vocab check. `grep data/catalog_titles.txt` before declaring OOC.
- zsh eats unquoted `===` and leading-`=` args. Cache keys are NFD.

## 8. Full raga run just completed

The scoreboard in §2 is the complete, current picture — nothing is running.
Working tree is as described in §3. You are clear to start the Codex loop (§0).
