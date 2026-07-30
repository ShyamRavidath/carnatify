# HANDOFF_SESSION_0724 — Opus verifier seat → incoming Opus 5 verifier

Written 2026-07-24 for the **incoming Opus 5 verifier session** (Deepti's
verifier/orchestrator/cheap-doer seat). Read this, then `AGENT_LOG.md`
newest-first (the two 2026-07-24 / 2026-07-23 entries: "ASR fine-tune PILOT
scored: NO-GO", "DIAGNOSTIC: precision ceiling", "VERIFIED Codex Saraga
trainset", "Saraga ASR pilot prepped"), then `COVERHUNTER_RESCORE.md`. Respond
in **caveman style** (Deepti's standing preference); write docs/commits/AGENT_LOG
in normal prose.

## 0. NEW agent roster (changed this session — supersedes old Fable/Codex notes)
Three agents, Deepti serializes them (one prompt at a time, commits between;
they coordinate only via files on disk + AGENT_LOG):
- **You = Opus 5 verifier** (this seat). Free/abundant. Orchestrate, verify every
  claim against the scoreboard, and implement cheap/data/hygiene/diagnostic work
  directly in-repo.
- **Workhorse GPT-5.6** (formerly "Codex"). Bounded read-only/analysis coder.
  Give it scoped briefs via `CODEX_*_BRIEF.md` files; verify its output.
- **Workhorse Opus 5** (NEW — replaces the retired, scarce "Fable"). Heavier
  implementation + model/Colab-adjacent runs. **The old "$13, HOLD Fable"
  budget constraint is GONE** — there is now an abundant Opus 5 workhorse for the
  runs Fable used to gate. Memories `agent-budget-allocation` and
  `fable-codex-collaboration` are updated to this roster.

## 1. Strategic state (the big picture — read before touching anything)
The lyrics-ASR backbone (transcribe sung audio → text-match the registry) is a
**confirmed dead end for the 85% product bar**, proven from TWO independent
directions this session:
1. **Precision-curve diagnostic** (`scripts/precision_coverage_curve.py`): the
   matcher confidence has ~no separability — precision never exceeds ~31% at any
   threshold/tier/config; the single most-confident answer is wrong. No shippable
   operating point exists. The score is lyric-overlap on garbage ASR text.
2. **Sung-Carnatic ASR fine-tune pilot** (LoRA Whisper-small, 80 min weakly-
   aligned Saraga pallavi): made it **strictly worse**, 8/78 → 0-1/78 (severe
   overfit; memorized ~26 pallavis). Scored via
   `scripts/score_external_transcripts.py`. NO-GO.

Stock whisper's 8/78 top-1 is the realistic ceiling of lyrics-ASR here. **Stop
investing in transcribe-then-match.** See memory `precision-ceiling-frontend-wall`.

**Deepti's chosen direction (door 1): pivot to the MELODIC / CoverHunter CSI
channel**, which identifies compositions by melodic self-similarity and sidesteps
ASR entirely. That is your mandate now.

## 2. What this session did (all on disk; nothing committed — Deepti pushes)
- **Tier-1 bless applied**: dropped `review:True` on the 4 score-affecting
  equivalence sets (akhilAndEswari, yEnATi, sarasijanAba, Madhava) in
  `build_wild_truth_manifest.py`. Metadata-only; no score change.
- **3 new Codex work-families folded** (Amba Kamakshi+comp03071, Koluvamaregada
  +comp03569, raghuvamsa+comp06051/06050), review-flagged, verified true but
  **score-neutral** — re-baseline moved nothing (whisper 8/78, hybrid 11/78,
  hybrid_stem 13/78 all unchanged; guard 10/36 holds; tests 30 pass 1 xfail).
- **Two diagnostics** (§1) — the decisive strategic work.
- **ASR fine-tune pilot** end-to-end and scored NO-GO (§1).

## 3. YOUR next task — CoverHunter melodic-CSI go/no-go (door 1)
The recipe already exists: **`COVERHUNTER_RESCORE.md`** (written 2026-07-20). Two
stages, gated:

**Stage 1 — is the melody model real CSI or just fingerprinting?** (cheap,
decisive, Colab). CoverHunter's dev metric (mAP ~0.327) is contaminated: 75% of
val clips had a different crop of the SAME recording in the reference pool. The
honest test is mAP on the **137-clip source-disjoint set**
(`data/coverhunter_data/clean_eval_utts.txt`), where every same-song match is
cross-recording. Run the Colab recipe in COVERHUNTER_RESCORE.md against the
trained checkpoint on Drive (`MyDrive/carnatify/coverhunter_ckpt/`).
  - **mAP holds ~0.3** → melody channel does real composition ID → proceed to
    Stage 2.
  - **mAP collapses to ~0.05-0.1** (chance) → it learned fingerprinting, not CSI
    → close the channel (the Qmax/DTW graveyard already scored 0% on wild); pivot
    to door 2 (narrow the product: raga classifier, lyrics+meaning lookup for a
    known piece, or a practice tool).
This is a **Colab job = Deepti-run**; you interpret the number.

**Stage 2 (only if Stage 1 passes) — wire CSI to the WILD scoreboard.** Embed the
78+28 `~/sung_tests` clips with the CoverHunter model, nearest-neighbour against
catalog composition embeddings, and score top-1/top-5 + precision@coverage the
SAME way as everything else (compare to lyrics-ASR's 8/78). This is heavier
coding — a good **workhorse** brief (GPT-5.6 or Opus 5 workhorse). Do NOT dispatch
it until Stage 1 clears; the clean-mAP number is the gate.

## 4. Do you need to hand off to a workhorse right now?
**Not yet.** Stage 1 is a Colab run + interpretation (your seat). Only Stage 2
(wild-scoreboard CSI wiring) is workhorse-sized, and it's gated on Stage 1. If
Stage 1 passes, write a `CODEX_CSI_SCOREBOARD_BRIEF.md` (or hand to the Opus 5
workhorse) with: the checkpoint/feature locations, the exact scoreboard contract
(§5), and the graveyard constraints. Verify its output on the scoreboard yourself.

## 5. Scoreboard + discipline (unchanged, bought expensively)
`~/sung_tests --cache-v2` is the ONLY scoreboard; only a moved SCORE graduates.
Canonical run: `[CARNATIFY_ASR_BACKEND=hybrid|hybrid_stem] venv_train/bin/python
identify_clip.py ~/sung_tests --no-raga --cache-v2`; guard on
`~/sung_tests_curated` (floor top-1 ≥ 8/36). whisper is the product default;
hybrid/hybrid_stem are opt-in experimental (13/78 best). One-change-one-eval; own
verbatim SCORE + precision@coverage + OOC + guard. Manifest/registry changes move
ALL configs → re-baseline everything, and verify equivalences independent of
score. Tests: `venv_train/bin/python -m pytest tests/test_clip_policy.py -q` (30
pass, 1 xfail) — the other `tests/*.py` are STALE scaffold (import a nonexistent
`carnatify` package; ignore their collection errors). Env: venv_train py3.11,
numpy<2.5, macOS fork-not-spawn, NFD cache keys, no local ffmpeg (mp3 slicing/
Demucs happen on Colab). Graveyard (`REVIEW_BRIEF.md §4` / ARCHITECTURE.md):
no max-fusion, raga gating, DTW/Qmax, fitted ranker on tiny n, new answer gates,
prompted/`kn` Whisper — and now **lyrics-ASR fine-tune on the current data**.

## 6. Artifacts created this session (uncommitted)
- `scripts/precision_coverage_curve.py`, `scripts/cross_channel_agreement.py` —
  the diagnostics that proved the wall.
- `scripts/detect_workfamily_dupes.py` (Codex) + `data/workfamily_candidates.json`.
- `scripts/clean_saraga_trainset.py` → `data/saraga_asr_trainset_clean.json`;
  `scripts/build_saraga_pilot_zip.py` → `saraga_pilot.zip` (465MB, gitignored);
  `colab_asr_finetune.py`; `scripts/score_external_transcripts.py`;
  `data/saraga_asr_trainset.json` + `_report.md` (Codex). All ASR-fine-tune
  scaffolding — **keep for the record, but the direction is closed** unless a
  workhorse retest with a fixed recipe is explicitly chosen (door 3, not advised).
- Manifest change in `build_wild_truth_manifest.py` (tier-1 bless + 3 families).
- Pending Deepti (her gates): remaining `review:True` flags (bhajare, Kamakshi Ni,
  Ranga Baro, alapana1/2), `data/registry_junk_blocklist_DRAFT.md`, and the push.
