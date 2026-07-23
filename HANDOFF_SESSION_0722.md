# HANDOFF_SESSION_0722 — Opus verifier/orchestrator, now also implementer of the cheap rungs

Written 2026-07-22 for the **incoming Opus session** (Claude Code, Deepti's
verifier/orchestrator seat). This is a same-role refresh: you are the human's
thinking partner, you vet the Fable↔Codex loop against the graveyard, and — new
this session — you **implement the cheap/data/hygiene rungs yourself, in-repo,
to conserve Fable's credits.** Read this, then start Rung 1 (see §4).

Read cold in this order: this file → `AGENT_LOG.md` (the two newest entries:
Fable's 10/1/1 decomposition and Codex's re-sequenced ladder) →
`HANDOFF_SESSION_0721.md` §0/§0.5/§4/§5 → `METRIC_CONTRACT.md` →
`REVIEW_BRIEF.md §4` (graveyard) → `OPEN_DECISIONS.md`. Memory files
`agent-budget-allocation`, `fable-codex-collaboration`, `wild-test-set-status`,
`registry-junk-entries` are loaded via MEMORY.md.

Respond in **caveman style** (per memory `caveman-mode-always` /
`.claude/skills/caveman/SKILL.md`) — but write docs, commit messages, and
AGENT_LOG entries in normal prose.

## 0. THE GREEN LIGHT (already given by Deepti)

You are cleared to **edit code directly in this repo** to implement the cheap
rungs, at zero Fable cost. Collision rule (Fable is normally the sole editor):
**edit only while Fable is idle** (it is — it's holstered until the ASR rung),
**log every change in `AGENT_LOG.md`** like Fable does, and follow the same
**one-change-one-eval + graveyard discipline**. The immediate task is §4.

## 1. Budget reality — the governing constraint (NEW, do not forget)

Three agents, very different budgets (memory `agent-budget-allocation`):
- **Fable = Claude API credits, DEPLETING.** Also the protocol's only
  code-editor/eval-runner/committer. Reserve it for the single most brutal task
  (the ASR step-change), handed over **fully specified, one shot** — no
  clarifying rounds. Every Fable prompt burns tokens Deepti cannot refill.
- **Codex (GPT-5.6) = abundant, long access.** Read-only reviewer/ideator.
  Front-load all design/spec here.
- **You (Opus, this session) = available, full repo tools.** Absorb the
  cheap/data/hygiene/diagnostic rungs directly. This is the main lever for
  conserving Fable — two full rungs land without touching its credits.

## 2. Current state (verified 2026-07-22)

- **Branch `main`, HEAD `71f477d`, only 1 commit ahead of origin** (Deepti has
  been pushing as we go; push is Deepti-run — OPEN_DECISIONS #1). `71f477d`
  (M1) is the sole unpushed commit.
- **Phase 0 committed** as 6 per-item commits `ed7963d`..`9f9acb2` (unicode,
  scoring, shared policy, v2 cache, synth-strip, hygiene) + docs commits.
  Tests: **10 passed, 1 xfailed** (`tests/test_clip_policy.py`).
- **Blessed baseline** (eval 3a, the standing scoreboard):
  `comp top-1 14/78, top-5 23/78, OOC reject 21/28 (bluffs 7)`,
  curated-36 guard `9/36` (floor is 8/36 — must not regress),
  raga-via-catalog-backfill `13/40`, v2 cache 106 hits 0 misses.
- **M1 (`71f477d`) committed**: `_line_variants()` keeps section/page/line
  order (pallavi lines protected from the 60-line cap); `match_lyrics()` scores
  three channels (title / pallavi / other) and exposes alignment evidence via
  `detail=True`. Ranking is still plain max — **pallavi is a feature only, no
  ranking change** — so M1 held the byte-baseline exactly (correct, expected).
- **Fable's 10/1/1 recall decomposition** (in AGENT_LOG) on the 22 ASR-usable
  auto-fetched clips: truth in top-100 only 10/22; 12 truths absent. Buckets:
  - **(a) ASR-dead: 10** — 9 fluent English hallucination (truth ≈0); 1
    (`raghuvamsa`) is svara/chittaswaram, no sahitya exists → non-sahitya clip.
  - **(b) catalog-missing: 1** (`yEnATi mOmu`) — real repeated sahitya
    recovered mix+stem, but truth row has **zero linked lyric lines**, ranked
    8,673/8,679 at 0.0 while lyric-rich wrong rows scored >1.2. **5 of the 12
    truth rows have lines=0** — a catalog coverage gap that caps even perfect ASR.
  - **(c) M2-recoverable: 1** (`entara`) — one Telugu segment ranks truth #5.
  - Bonus finds: `truth_match` matched **70 registry rows** for the generic
    title "rAma nee" (scoreboard slightly flatters itself); ~5–8 real junk rows
    registry-wide (the "V V Mohalla" top-1 was an empty query at 0.0 — cosmetic).

## 3. The accepted ladder (Codex re-sequence, AGENT_LOG @ latest entry — VETTED CLEAN)

Order and ownership:
1. **Rung 1 — exact work-ID truth manifest + corrected re-baseline** → **YOU**
2. **Rung 2 — reviewed lyric-link overrides + registry rebuild + SCORE** → **YOU**
3. **Rung 3 — IndicConformer native-ONNX, CTC-only/mix-only + SCORE** → **Fable**
   (the one brutal task; or you attempt local ONNX prep first to spare credits)
4. **Rung 4 — next ASR ablation chosen from that SCORE** → Fable
5. **Rung 5 — scoped sahitya-segment M2 (~1 clip)** → later
M3 / SCES / ISO-15919 representation stay **parked** (not enough candidate
evidence; not the bottleneck 10/1/1 exposed). Do NOT tune SCES or any script
threshold on the 26 known transliteration bluffs.

## 4. YOUR IMMEDIATE TASK — Rung 1 (start here)

Goal: replace evaluator-time fuzzy `truth_match` with a reviewed one-to-one
truth manifest, so the scoreboard stops flattering itself, then re-baseline.

Spec (from Codex Rung 0):
1. Build a reviewed **wild-truth manifest**: clip basename → canonical registry
   work ID (or a small set of explicitly-equivalent work IDs). Resolve
   "rAma nee" to its actual full work in the registry/work-family data.
2. Change prediction scoring to **compare IDs**, not run bidirectional
   `partial_ratio >= 90` against the filename on every row.
3. **Do NOT lower the registry's global fuzzy-merge threshold** — short generic
   titles are exactly where global fuzzy merge is unsafe. Use reviewed explicit
   aliases/work IDs only.
4. Add a **regression test**: the chosen "rAma nee" truth accepts its real work
   and rejects the dozens of unrelated registry rows.
5. Re-run the full 106-clip scoreboard **with matcher outputs otherwise
   unchanged**; quote the verbatim corrected SCORE block into AGENT_LOG. That
   becomes the corrected baseline. Keep the old `14/78, 23/78, OOC 21/28` block
   in the log as historical, not directly comparable (annotate the metric fix).
6. In the same packet, list the ~10 exact suspected junk rows/pages with
   provenance + keep/drop reason — **for Deepti to review, do NOT auto-remove**
   (Fable found ~half of 18 heuristic flags are legit titles). The blocklist
   cleanup, if approved, is behavior-changing → its own full SCORE.

Then **Rung 2** (also yours): audit all 78 in-catalog truth work IDs, emit a
coverage table (linked pages, pallavi/other line counts, source title,
unresolved status); for each zero-line sahitya truth, link local karnatik pages
via a small reviewed override file (`work_id → page IDs`) — e.g. `yEnATi mOmu`
→ local `c1736.shtml` ("EnATi nOmu phalamO", soft-sim 83.9, below merge
threshold). Acceptance = data integrity (every zero-line truth linked or
explicitly marked `lyrics_missing` with evidence). Rebuild registry, run full
SCORE. This precedes ASR so the acoustic experiment is falsifiable.

## 5. Blocked on / routed to Deepti (do not re-propose as new)

- **Push** the unpushed commit(s) — Deepti-run (OPEN_DECISIONS #1).
- **Junk-row blocklist review** — she is the registry gate; you draft, she approves.
- **`raghuvamsa` stratum label** — musical judgment. Codex's ruling (accepted):
  it stays an **overall composition miss** (dropping hard in-catalog clips would
  game the metric, contra METRIC_CONTRACT), but is **excluded from the
  lyrics-ASR denominator**. She labels it from the audio as a new stratum
  "composed non-sahitya (svara/chittaswaram)".
- Everything else parked in OPEN_DECISIONS.md (deploy, raga-model swap, paid
  meanings, ear-checks) — unchanged.

## 6. Discipline (bought expensively — do not relearn)

- **`~/sung_tests` (106 clips, `--cache-v2`) is the ONLY scoreboard.** Nothing
  graduates on reasoning or same-corpus numbers — only a moved SCORE block.
  Canonical run (HANDOFF_VERFIER §3.2):
  `caffeinate -i venv_train/bin/python identify_clip.py ~/sung_tests --no-raga --cache-v2`
  (read-only against the cached v2 hypotheses — fast, no ASR).
- **One-change-one-eval.** Each behavior/metric change is a separate commit +
  its own verbatim SCORE. Curated-36 guard `must not drop below 8/36` (now 9/36).
- **Check every idea against the graveyard** (REVIEW_BRIEF §4,
  handoff_state_and_progress §4) and OPEN_DECISIONS before acting. Dead: global
  DTW, melodic n-grams/Smith-Waterman/subseq DTW, Qmax, raga gating/blending,
  tonic features, ASR max-fusion, char n-gram Jaccard, global vowel-squash
  phonetic, plain title IDF, more answer gates, prompted-whisper. ASR retry
  ONLY via CTranslate2 (vasista22 Whisper) or native ONNX (IndicConformer).
- Co-publish precision-at-coverage WITH top-1/top-5 + OOC (METRIC_CONTRACT).

## 7. Ops gotchas

- `identify_clip.py` is not run with `-u`; buffers behind a pipe. Use
  `python -u` if piping and tracking progress.
- Long runs (re-ASR): `caffeinate -dims -w <pid>`, lid open — `caffeinate -i`
  does NOT block lid-close sleep.
- Env: matcher/ASR/eval in **venv_train** (py3.11). No ffmpeg; librosa/essentia,
  feed whisper numpy arrays. macOS fork not spawn. numpy<2.5. Cache keys NFD
  (APFS filenames are NFD — bit the synth strip).
- Registry has junk rows (addresses/dates) — never trust its raga metadata
  without a vocab check.

## 8. Where the leverage is (payoff-ordered, post-decomposition)

The matcher ladder is NOT the lever — M1 proved recall is the wall. Levers now:
1. **Catalog lyrics-coverage** (Rung 2) — cheapest ceiling-lifter, precondition
   for any ASR win (5/12 truths blind). Yours.
2. **ASR step-change** (Rung 3) — 10/12 clips ASR-dead. Biggest but brutal. Fable.
3. Metric honesty (Rung 1) — not a capability gain but unflatters the board. Yours.
4. M2 (~1 clip), M3 (parked), SCES/ISO (parked).
