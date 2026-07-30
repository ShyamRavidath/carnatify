# HANDOFF_SESSION_0723 — Opus verifier/implementer seat (Rungs 1–5 done)

Written 2026-07-23 for the **incoming Opus session** (Deepti's verifier/
orchestrator/cheap-implementer seat) — a same-role refresh so this session can
`/clear` and continue. Read this, then `AGENT_LOG.md` (newest-first: "Rung 5
re-scored", "Rung 5 pre-diagnostic", Fable's "Rung 5 complete", Codex "Rung 5
spec"), then `METRIC_CONTRACT.md`. Respond in **caveman style** (memory), but
write docs/commits/AGENT_LOG in normal prose.

## 0. Role + budget (governing constraint)
Three agents, Deepti serializes them (pastes one prompt at a time, commits
between — so file collisions are avoided by sequencing):
- **You (Opus, this session/seat) = the free/abundant doer.** Implement all
  cheap/data/hygiene/diagnostic rungs directly in-repo. You did Rungs 1, 2, 4,
  and the Rung-3/Rung-5 diagnostics + manifest corrections.
- **Codex (GPT) = reviewer/ideator, now also a read-only analysis coder.**
  Budget is tightening — give it bounded tasks. Currently assigned the
  work-family duplicate DETECTOR (`CODEX_WORKFAMILY_BRIEF.md`).
- **Fable (Claude) = scarce, ~$13 left.** The only agent that runs the ASR
  model. **Recommend HOLDING it** — see §4. Reserve for a model-run that a free
  agent cannot do, and only once precision (not recall) is the thing it moves.

## 1. Where the numbers stand (corrected manifest, 2026-07-23)
```
config            top-1  top-5  precision@coverage  OOC bluffs  guard
whisper (default) 8/78   21/78  17% @ 44%           7           --
hybrid  (Rung 4)  11/78  25/78  20% @ 52%           10          10/36
hybrid_stem (R5)  13/78  28/78  23% @ 53%           10          10/36
```
Canonical runs (read-only, no ASR):
`[CARNATIFY_ASR_BACKEND=hybrid|hybrid_stem] venv_train/bin/python
identify_clip.py ~/sung_tests --no-raga --cache-v2` ; guard = same on
`~/sung_tests_curated` (floor top-1 ≥ 8/36). **whisper remains the product
default**; hybrid/hybrid_stem are opt-in experimental. 30 tests + 1 xfail green.

## 2. What was built (all committed or on disk)
- **Rung 1** metric honesty: reviewed `data/wild_truth_manifest.json` (clip→work
  id), replaced fuzzy `truth_match`. Build: `build_wild_truth_manifest.py`.
- **Rung 2** lyric coverage: `data/karnatik_link_overrides.json` (load-time
  page links), `data/rung2_coverage_report.md`.
- **Rung 3** (Fable): IndicConformer CTC mix cache `data/asr_cache_indic.json`,
  `scripts/build_asr_cache_indic.py`.
- **Rung 4** (Opus): `CARNATIFY_ASR_BACKEND=hybrid` — Whisper↔Indic arbitration
  (`arbitrate()`, `identify_v2_hybrid()`, q_cov+ordered gate `HYBRID_QCOV_MIN=
  0.250`, `assess_variants(detail=)`, precision@coverage footer).
- **Rung 5** (Fable): `hybrid_stem` — Indic CTC on the Demucs vocal stem
  (`data/asr_cache_indic_stem.json`, builder `--source stem`). Effective-Indic
  selector: mix-passes→mix, elif stem-passes→stem, else mix.
- **Rung 5 re-score** (Opus): 2 verified work-family equivalences added to the
  manifest (akhilAndEswari {comp00173,comp00175}, yEnATi {comp08673,comp01633})
  → hybrid_stem 11→13 top-1, now strictly dominates Rung 4. **Pending Deepti's
  bless of the equivalences** (her gate; all reviewed-flagged).

## 3. PENDING DEEPTI (do not re-propose; she gates)
- **9 manifest `review:True` flags + the junk blocklist** — full checklist given
  to her in chat this session. 4 are score-affecting equivalence-sets
  (akhilAndEswari, yEnATi, sarasijanAba, Madhava); if she rejects any, revise
  the manifest override in `build_wild_truth_manifest.py`, rebuild, re-baseline.
- `data/registry_junk_blocklist_DRAFT.md` (~19+5 rows) — delete on approval, own
  re-score. Does not affect current numbers.
- **Push** all commits (Deepti-run).

## 4. Next rung (highest leverage, FREE) → systematic work-family pass
Registry work-family duplication is the **binding error class** — it caps every
config. Codex is producing `data/workfamily_candidates.json` (see
`CODEX_WORKFAMILY_BRIEF.md`). **Your job when it lands:** verify each candidate
against the bar (identical/near pallavi + same composer + same-or-equivalent
raga; shared karnatik page = near-certain), fold the confirmed ones into
`build_wild_truth_manifest.py` overrides (review-flag them), rebuild, and
re-baseline all three configs once. This precedes any further ASR ablation and
lifts every config — do it before spending Fable.

## 5. Fable queue (HOLD unless Deepti chooses to spend the ~$13)
Pre-approved one-variable ASR ablations, each a model-run = Fable spend:
**RNNT-same-mix** (cheapest; IndicConformer RNNT decoder on the existing mix
cache), then **vocal-active segmentation/VAD**, then more. **Recommendation:
hold.** These buy RECALL; the wall is now PRECISION (23% vs the 85% product bar)
and equivalence (free to fix). Don't spend the last $13 on recall until a
precision lever needs the model. If she insists on spending now, RNNT-mix is the
one to prompt (Codex pre-spec'd its shape in the ladder).

## 6. Discipline (unchanged, bought expensively)
`~/sung_tests --cache-v2` is the ONLY scoreboard; only a moved SCORE graduates.
One-change-one-eval, own verbatim SCORE + precision@coverage + OOC + guard.
Never retune `HYBRID_QCOV_MIN=0.250` after seeing a result. Manifest/registry
changes move ALL configs → re-baseline everything, and verify equivalences
independent of score impact (the implementer-conflict trap). Graveyard
(`REVIEW_BRIEF.md §4`): no max-fusion, raga gating, DTW/Qmax, fitted ranker on
tiny n, new answer gates, prompted/`kn` Whisper. Env: venv_train py3.11,
numpy<2.5, macOS fork-not-spawn, NFD cache keys, no ffmpeg. Demucs CPU-bound/
timeout-prone (`caffeinate -dims`, lid open). Registry has junk rows — never
trust its raga metadata without a vocab check.
