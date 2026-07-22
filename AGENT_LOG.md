# AGENT_LOG — shared channel between Fable (Claude) and Codex (GPT-5.6)

This is the ONLY live channel between the two agents. They cannot see each
other's chat; they coordinate by appending here and re-reading before acting.

## Protocol
- **Append, never rewrite.** Add a new dated entry at the bottom; leave prior
  entries intact so the history is legible to both agents and to Deepti.
- **Entry format:** `## [YYYY-MM-DD HH:MM] <AGENT> — <one-line topic>` then the body.
- **Roles are asymmetric (prevents file collisions):**
  - **Codex** = reviewer/ideator. Read-only on source code. Writes proposals,
    critiques, and questions here (and the initial dump in `CODEX_REVIEW.md`).
  - **Fable** = implementer/vetter. The only agent that edits code, runs the
    eval, and commits. Records decisions + the resulting SCORE block here.
- **Evidence, not claims.** When Fable implements something, it pastes the
  verbatim SCORE block from `~/sung_tests` here. No idea graduates on reasoning
  — only when the scoreboard moves. Same-corpus numbers graduate nothing.
- **Before proposing, check the graveyard** (`REVIEW_BRIEF.md §4`) and
  `OPEN_DECISIONS.md`. Do not resurface measured-dead approaches or items
  parked on Deepti.
- Deepti is the clock and the human gate: she tells each agent when to re-read,
  and approves anything that spends money, deploys, pushes, or overwrites a
  production model.

---

## [2026-07-21] Fable (session predecessor) — channel opened
Review doc package committed @ 9f3161f; session handoff @ 1a15923. Current
wild scoreboard: comp top-1 11/78, top-5 18/78, OOC 24/28, raga 18/85.
Codex was pointed at REVIEW_BRIEF.md — its full review should land in
CODEX_REVIEW.md. First real entry below should be Codex's, or Fable's
evaluation of CODEX_REVIEW.md.

## [2026-07-21 19:30] Fable — CODEX_REVIEW.md vetted: code claims verified, proposals clear the graveyard

Read CODEX_REVIEW.md in full and spot-checked every code-level claim against
the current source. Verdict: **the review is accurate and graveyard-clean.**

### Claims verified in source (all confirmed)

- **P0 fold() erases native scripts** — `identify_clip.py:80-83` keeps only
  ASCII `[a-z0-9 ]` after NFKD strip; `_whisper_multi()` (line 362) folds every
  hypothesis *before* the longest-wins comparison. Forced `ta`/`te`/`hi`
  decodes can reduce to whitespace exactly as described.
- **P0 backend policy divergence** — `backend/clip_identify.py` has no
  `_max_token_run` gate (grep: zero hits) and its `transcribe_multi` defaults
  to `(None, "ta", "te")` — no `hi` — while root `identify()` (line 508)
  applies the loop gate and includes `hi`. Two different policies, confirmed.
- **P1 many-to-one scoring exploit** — `_best_map()` (line 247) assigns each
  catalog token its best transcript token with no injectivity constraint;
  `_score_ktoks()` (line 290) adds `freq_bonus` per catalog title-token from
  the same transcript token's frequency. The `rama rama` failure shape is real.
- **P1 longest-transcript-wins** — line 362-364, confirmed; discards language,
  segments, likelihoods, and competing hypotheses.
- **P1 cache keyed by basename only** — `transcribe()`/`transcribe_stem()`
  (lines 370-399): no audio hash, no model/config identity, non-atomic
  in-place `write_text`. Confirmed.
- **P2 `--no-raga` fake 0/85** — `main()` prints the raga line unconditionally
  (line 638); denominator accumulates from filenames regardless of inference.
- **P2 silent `except Exception: pass`** in `_whisper_multi` (line 365) and
  **P2 `workers=-1`** in `_best_map` (line 256). Both confirmed.
- File is 646 lines as Codex states; REVIEW_BRIEF §8's "~1,500 lines" is stale.

### Graveyard / OPEN_DECISIONS cross-check

Every proposal checked against REVIEW_BRIEF §4 and OPEN_DECISIONS.md: no
resurrections, no blocked actions. The "Explicitly excluded" list matches the
graveyard. One clarification worth recording: the graveyard line "retry ONLY
via ctranslate2" applies to the **vasista22 Whisper finetunes**; Codex's
native-ONNX route for IndicConformer is a different model family and does not
violate it — the distinction (ctranslate2 for converted Whisper checkpoints,
native ONNX for IndicConformer) is correct.

### Notes / minor caveats

- Codex's tier diagnostics (high 8/16, medium 3/24, answered 40/106) are
  derived from cached transcripts; I did not independently rerun them. They
  are consistent with the verbatim SCORE block, which matches the 2026-07-20
  baseline minus the known `--no-raga` display bug.
- The metric-contract reframe (precision-at-coverage primary, overall
  top-1/top-5 + OOC always co-published so abstention can't game it) is a
  genuine improvement over both the raw 80-90% goal and the naive 35%-coverage
  framing. Endorse.
- Phase 0 item 1 (single shared policy function) touches `backend/` — local
  refactor only; deploy remains Deepti-run per OPEN_DECISIONS #2.

### Recommendation to Deepti

Accept the phase ordering. Phase 0 (correctness/observability: shared policy,
Unicode preservation + transliteration, versioned atomic cache, per-source
hypotheses, `--no-raga` honesty, regression tests incl. `rama rama`) is pure
defect-fixing, zero-cost, and prerequisite to trusting any later ASR
experiment. I am ready to implement Phase 0 on your go; per protocol it will
only be claimed as an improvement if the full 106-clip wild score moves.

## [2026-07-21 20:00] Deepti (via predecessor Claude) — Phase 0 GREENLIT with guardrails

Reviewed Fable's vetting. Phase 0 approved. Guardrails for the implementer:
1. **One-change-one-eval** (HANDOFF_0718 §6). The three behavior-changers
   (fold/Unicode, one-to-one scoring, shared policy) get SEPARATE evals against
   the 106 set; the original curated 36 clips (=8/36) are the regression guard —
   must not drop. Hygiene fixes (--no-raga honesty, silent-except, workers,
   tests incl. rama rama) apply freely, no eval. Do NOT bundle all six.
2. **Cache re-version** = the expensive step, collides with OPEN_DECISIONS #8.
   Check first whether fold() fix needs re-ASR (raw vs post-strip cache). Use
   the forced re-ASR to strip synth/control entries (#8). Run caffeinated, lid
   open (`caffeinate -dims -w <pid>`).
3. Backend refactor local only — deploy stays Deepti-run (#2).
Metric reframe (precision-at-coverage, co-published with top-1/top-5/OOC)
ACCEPTED — write it into METRIC_CONTRACT.md as the standing scoreboard format.
Session handoff HANDOFF_SESSION_0721.md updated (§0.5) to capture all of this.

Fable: proceed on Phase 0 per these guardrails. Quote each SCORE block here.

## [2026-07-21 21:15] Fable — Phase 0 underway: hygiene landed, evals 1+2 done, re-ASR running

### Hygiene (no eval per guardrails; tests green)
`--no-raga` now prints `raga skipped (--no-raga)` (fake 0/85 gone); ASR
exceptions surfaced per-language to stderr instead of silent `pass`; cache
writes atomic (temp+rename); matcher workers bounded via
`CARNATIFY_MATCH_WORKERS` (backend defaults 2). New
`tests/test_clip_policy.py`: 10 passed, 1 xfail (the still-open generic-
repetition answerability case). One find: the stale `backend/identify_clip.py`
build-copy can shadow the root module on sys.path — tests now pin root first.

### Eval 1 — shared policy (behavior-changer, expect no change): PASS
Root `identify()` and backend `identify_from_variants()` now both call the new
`identify_clip.assess_variants()` — one policy (loop gate, langs incl. `hi`,
catalog backfill now also in the API path). Contract test asserts identity.

```text
===== SCORE over 78 in-catalog + 28 OOC clips =====
composition top-1 11/78  top-5 18/78
OOC reject  24/28  (bluffs: 4)
raga        skipped (--no-raga)
raga via catalog backfill 8/36 (on clips with confident composition)
```
Guard (curated dir): `composition top-1 8/36  top-5 12/36`, `OOC reject 4/5`.
Byte-identical to baseline. The scoreboard now scores what the API serves.

### Eval 2 — one-to-one scoring (behavior-changer): PASS, graduates
Occurrence-injective token assignment (transcript occurrence usable once;
joined bigram spends both parts), matched weight = min(kt IDF, transcript-
token IDF), repetition bonus once per distinct transcript token. Legacy
kill-switch: `CARNATIFY_LEGACY_SCORING=1`.

```text
===== SCORE over 78 in-catalog + 28 OOC clips =====
composition top-1 12/78  top-5 19/78
OOC reject  24/28  (bluffs: 4)
raga        skipped (--no-raga)
raga via catalog backfill 9/36 (on clips with confident composition)
```
Guard: `composition top-1 8/36  top-5 12/36`, `OOC reject 4/5` — holds.
Per-clip diff vs eval 1: `raghuvamsa` becomes top-1 correct; wrong "high"
answers `Ramabhi Rama` and `rAma ninnu nera` (generic rama-titles — the
exploit class) demoted to medium. Precision at coverage 28%→30% at equal 38%
coverage. Exploit smoke: `rama rama` 1.451→0.921, `raja raja` 1.222→0.949;
genuine matches essentially unmoved (`vatapi…` −0.007, `nagumomu` 0).

### Also done
- **OPEN_DECISIONS #8 executed**: legacy transcript caches stripped 200→106
  and 120→106 entries (81+1 synth/control removed, NFC/NFD duplicate keys
  merged — beware: APFS filenames are NFD, several real clips masqueraded as
  strippable until normalization).
- **METRIC_CONTRACT.md written** — precision-at-coverage primary (>=85% bar),
  always co-published with in-catalog top-1/top-5, OOC bluffs, eligibility
  strata (Deepti-adjudicated), assisted recovery; curated-36 guard and
  prospective-validation rules codified.
- **v2 ASR cache builder running** (caffeinated): full re-ASR of 106 clips,
  raw native-script hypotheses per language/source with segments + status,
  keyed sha256+config, atomic incremental writes. fold/Unicode eval fires on
  completion (`identify_clip.py --cache-v2`; fold-only diagnostic via
  `CARNATIFY_V2_FOLD_ONLY=1`).

## [2026-07-22] Fable — Phase 0 complete: eval 3 (fold/Unicode) split verdict, new baseline set

Re-ASR builder finished: 106/106 clips, 17.3 h caffeinated, 0 error
hypotheses, **585 hypotheses contain native Indic script that the old
`fold()` erased entirely**. v2 cache (`data/asr_cache_v2.json`) is
sha256+config-keyed, raw-preserving, atomic; eval is read-only against it
and reports hit/miss (a SCORE with misses is invalid).

### Eval 3a — re-ASR, fold (ASCII) view: ACCEPTED, new baseline

```text
===== SCORE over 78 in-catalog + 28 OOC clips =====
composition top-1 14/78  top-5 23/78
OOC reject  21/28  (bluffs: 7)
raga        skipped (--no-raga)
raga via catalog backfill 13/40 (on clips with confident composition)
v2 cache: 106 hits, 0 misses
```
Guard: `composition top-1 9/36  top-5 15/36`, `OOC reject 3/5`,
41 hits 0 misses — above the 8/36 bar. Precision-at-coverage 30% @ 44%
(was 30% @ 38%): same precision, more coverage, +2 top-1, +4 top-5.

### Eval 3b — re-ASR + transliterated view: REJECTED as default, parked as channel

```text
===== SCORE over 78 in-catalog + 28 OOC clips =====
composition top-1 14/78  top-5 29/78
OOC reject  2/28  (bluffs: 26)
raga        skipped (--no-raga)
raga via catalog backfill 10/64 (on clips with confident composition)
v2 cache: 106 hits, 0 misses
```
Candidate recall explodes (top-5 19->29/78, coverage 85%) but answered
precision collapses 30%->16%: the recovered native evidence is REAL on OOC
clips too (e.g. `Achyutam Keshavam` decodes to its true bhajan lyrics in
Devanagari), and the uncalibrated thresholds answer everything. Per the
metric contract this cannot ship as default. It is now opt-in
(`CARNATIFY_V2_TRANSLIT=1`), explicitly NOT graveyarded: it is the
candidate-generation channel whose value Phase 4 calibration is meant to
unlock — exactly Codex's sequencing ("calibrate abstention only after
candidate generation improves").

**For Codex — observations worth your next pass:**
1. The 26 bluffs are heavily the Devanagari/Hindi channel (OOC set is
   bhajan/film-heavy; in-catalog is ta/te/sa kritis). A script- or
   language-aware evidence feature seems more promising than a global
   threshold, but I did NOT slice-tune on the dev set — flagging, not
   fitting.
2. Tamil transliteration (sanscript HK) voices consonants
   (`vAdhAbhi ghanabhadhim`); `soft()` absorbs some. ISO-15919 vs HK worth
   a look before the CTC-scoring work fixes representation anyway.
3. Re-ASR alone (same fold view, fresh whisper run) moved top-1 12->14 —
   transcript nondeterminism is nontrivial; supports your versioned-cache
   point and prospective-eval discipline.

### Phase 0 closeout

All six items landed: shared policy (eval 1, no change, contract-tested);
one-to-one scoring (eval 2, +1/+1, graduates); Unicode/cache re-version
(eval 3a accepted / 3b parked); `--no-raga` honesty; structured ASR errors;
atomic versioned cache + tests (10 pass, 1 xfail). OPEN_DECISIONS #8
executed (synth strip). METRIC_CONTRACT.md written; new baseline recorded
there. HANDOFF_VERFIER.md §3.2 updated: canonical scoreboard command now
includes `--cache-v2`. Nothing committed (push decision #1 still parked on
Deepti). Legacy filename-keyed caches remain for the no-flag path but are
deprecated.

<!-- next entry goes here -->
