# HANDOFF_SESSION_0721 — honest re-baseline, doc package, and the Fable↔Codex loop

Written 2026-07-21. Audience: **Fable** (the incoming Claude agent), who will
work alongside **Codex (GPT-5.6)** on this project. Predecessors, read cold in
this order: HANDOFF_SESSION_0719B.md (CoverHunter Colab), HANDOFF_SESSION_0719.md,
HANDOFF_SESSION_0718.md, then the consolidated `handoff_state_and_progress.md`
+ `handoff_vision_and_architecture.md`. This file covers only what changed and
how the two-agent collaboration works.

---

## 0. FABLE — START HERE (the Fable↔Codex protocol)

You and Codex are two separate CLIs on the same repo. **You cannot see each
other's chat, ever.** You collaborate only through files on disk + git. That
is the entire mechanism; internalize it.

**Step 0, before anything else: read `CODEX_REVIEW.md`** (repo root). Codex was
pointed at `REVIEW_BRIEF.md` and asked for (1) a code review of
`identify_clip.py`, (2) whether the 80% top-1 goal is reachable vs a
precision-at-coverage reframe, (3) ideas on the ASR bottleneck and the matcher.
Its findings should be in that file. **If `CODEX_REVIEW.md` does not exist yet,
ask Deepti to have Codex write it** — do not proceed on a guess about what
Codex said, and do not invent its findings.

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
that survive → you write decisions/results back to a shared file (suggest
`DECISION_LOG.md`) → Codex reads that on its next pass. Keep the loop on disk.
When you implement something, run the eval and quote the SCORE block in the
log so Codex sees real evidence, not claims.

Deepti wants you two working in harmony. Harmony here = disciplined file-based
exchange + the wild-eval as the shared source of truth. She is the domain
authority (Carnatic musician) and the human in the loop for anything musical,
any spend, any deploy, any push.

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

`main @ 9f3161f`, **6 commits ahead of origin, NOT pushed** (pushes are
Deepti-run — OPEN_DECISIONS #1). Live matcher is `identify_clip.py` (repo root,
standalone, imports nothing from `src/carnatify/`). Everything composition- or
tala-related in `src/carnatify/ml/` is legacy or graveyard — trust the STATUS
banners.

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
