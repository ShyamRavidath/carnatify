# Workhorse brief — device map, calibration, exclusion mechanism, then score

Date: 2026-07-30. For the **Opus 5 workhorse**. Follows your
`WORKHORSE_PROBE_LAUNCH_BRIEF.md` execution and the open decision at the end of
your 2026-07-30 `AGENT_LOG.md` entry.

**Do not run `duration_probe_score.py` until C4.** Nothing is committed; the GPU
run is complete and no further GPU spend is authorized. Respond to Deepti in
caveman style; docs and `AGENT_LOG.md` in normal prose.

---

## 0. The A/B/C question is not answerable as posed — two corrections

You raised `probe0016` and held scoring, which was right. Two things are wrong
with the framing, both verified here before this brief was written.

**There is at least a second straddler.** Chunking is `sorted(windows.items())`
in chunks of 10 (`colab_duration_probe.py:199,260`). Under that order window 256
is `probe0051d030a`, window 259 is `probe0051d180a`, window 260 is
`probe0051d300a`. The run reported stopping at 259/300, so `probe0051` splits
across the interruption exactly as `probe0016` splits across the T4/L4 boundary
— four windows one device, `d300` another, same endpoint. Worse, in fact: the
resumed session's GPU was never recorded.

**The device map is not actually known.** `handoff.md` §2.6 asserts both
"windows 1-80 (`probe0000`-`probe0015`) came off a Colab T4; windows 81-259 off
the faster GPU" and "`probe0016` is split: d030/d060/d090/d180 on the T4".
`probe0016` is windows 81-85; if 81-259 were the faster GPU it never split.
Additionally the checkpoint chunk is 10 windows and the cache is written after
each chunk, so a clean stop lands on a multiple of 10 — **259 does not**.
Something (a failed window, a mid-chunk death) does not fit the simple story,
so the straddler set is not derivable from the stop index.

Fix §2.6 in `handoff.md` once C1 gives you the real map. Do not propagate the
current text.

## 0b. The decision Deepti made, and the rule already frozen

Deepti chose **map → calibrate → branch**. The branch rule is already written
into `DURATION_PROBE_PREREGISTRATION.md` **§5b** by the verifier seat, before
any statistic was read. **Read §5b first and implement it exactly.** Do not
re-derive it, do not add a third branch, and do not adjust it once a
calibration result is visible — the whole value of the section is that it was
fixed in advance.

Summary of what §5b binds you to: three windows, mix hypotheses only, verbatim
on `raw`; all identical → score as-is at registered n; any difference → exclude
every straddler and score at reduced n; ambiguous or failed → treated as
*differs*; re-transcribing a straddler to repair it is rejected.

---

## C1 — SUPERSEDED: `run_log.json` does not exist. Calibrate first.

**Read `DURATION_PROBE_PREREGISTRATION.md` §5b.1**, the amendment that replaces
this step.

`colab_duration_probe.py` writes `run_log.json` at L316, *after* step 5/6 — and
step 5/6 is where the session died on `rapidfuzz`. The file was never written.
It is not in Drive, and Deepti did not miss it.

The order is therefore inverted: **run the calibration (C3) first.** If the mix
hypotheses are identical, device-invariance is established and no straddler set
is needed at all — the map becomes irrelevant rather than unavailable, and you
score at the registered n. Laptop CPU against GPU is a *wider* gap than T4
against L4, so identity across it is the stronger result.

**Update: the session-3 map is already established, by the verifier seat.**
Deepti's Colab tab was still open. Read `data/duration_probe/DEVICE_MAP.md` and
its evidence file `data/duration_probe/notebook_session3_output.txt` — do not
re-derive them, and do not delete either.

What they settle:

- **The negative arm is straddler-free.** All 140 windows ran in one session on
  an A100. §5b's belief is now checked. This was the case with no slack under
  rule A, and it came out clean.
- **`probe0051` is a confirmed straddler**, observed not inferred: the session
  opened at `259/300 already cached` and its first transcription was
  `probe0051d300a.wav`.
- `probe0052`-`probe0059` are entirely on the A100 — not straddlers. Their
  device differs from titles 0-50, but that is between-title variation against a
  within-title estimand and does not confound the contrast.

What remains open is **only** whether `probe0016` straddles, which needs the
session-1 or session-2 notebook output, or Drive revision history on the
checkpointed `asr_cache_v2.json`. Recomputed throughputs — A100 0.497 s/s
anchored and 0.450 s/s negatives, against §2.6's T4 1.56 and intermediate 0.86 —
are separated by 1.8x and 3.2x, so either earlier notebook's per-chunk timings
would resolve it unambiguously. Ask Deepti whether those tabs survive; do not
chase it unless the calibration says *differs*.

**Also treat as a live hazard:** the executed notebook is *not* the file on
disk. The run used chunks of 5 while `colab_duration_probe.py:72` says
`CHUNK = 10`. Reasoning about the earlier sessions from the repo copy is unsafe.
Reconciling that file with what actually ran is worth doing before it is quoted
again — but it is not a prerequisite for scoring.

If the calibration differs and no record establishes the map, §5b.1 already
fixes the outcome: the recall arm cannot support a verdict and the run is
reported **invalid** — not KILL, not INCONCLUSIVE, a lost measurement. Do not
guess a straddler set, and do not soften this because of what it cost.

Add to the graveyard while you are here: a long unattended runner must write its
provenance record **incrementally, from the first chunk**, never at the end. The
same session lost its audit trail and its inference step to failures scheduled
after 27 GPU-hours of work had already been done.

## C2 — the exclusion mechanism, written before the calibration runs

Build this **first**, while the calibration answer is still unknown, so the code
cannot be shaped to it. The scorer today has no way to drop a title: `validate()`
checks `n_titles` and `expected_windows` (L192-195, L263) and `validate_negatives()`
checks the same (L498-501), and nothing removes a unit.

- Add `--exclude-title` (recall) and `--exclude-item` (negative), repeatable,
  taking ids.
- Excluded units are removed from *every* readout — pairing, transitions, the
  per-source gating counts under rule A (§6b), and the unknown-item sensitivity.
- `n_titles` / `expected_windows` / `gating_source_counts` must be **reconciled
  against** the exclusion list, not bypassed. An exclusion must never be able to
  mask a genuinely incomplete run: excluding a unit whose windows are absent
  anyway is still an invalid run.
- The run's output prints the excluded set, the reason string, and the realized
  n, above the verdict.
- Under rule A, an exclusion that drops a gating source below `SOURCE_MIN_N = 20`
  changes what the conjunction is quantified over. Suppress with an explicit
  message rather than silently gating on fewer sources — that is the same hole
  your `_verify_gating_sources()` closed for missing sources.
- Tests: exclusion changes n and the bound as expected; excluding an absent unit
  still fails validation; a source dropped below the threshold suppresses.

## C3 — run the calibration exactly as §5b specifies

**This step now runs first — see C1 and §5b.1.**

- `DEVICE_CAL_N = 3` windows, drawn from **`probe0016` and `probe0051`**, the
  two straddler candidates under every version of the account, so no clean
  title's data is consulted whatever the map turns out to be. Prefer the
  shortest windows available — three 30s/60s windows, not the 300s ones.
- Temporary cache path. `data/asr_cache_v2.json` must be byte-identical
  afterwards — verify with a hash, and take a copy before you start. You
  established this pattern in L3; reuse it.
- Compare the four `source: 'mix'` hypotheses verbatim on `raw`. The cache
  stores hypotheses as a repr string with `source` in `{mix, stem}`; parse it,
  do not regex it. Report the three `stem` hypotheses alongside as information
  only — a laptop re-run takes the unpatched CPU-Demucs path, so a stem
  difference is expected and decides nothing.
- Write `data/duration_probe/DEVICE_CALIBRATION.md`: the windows chosen, both
  hypothesis sets in full, a per-pass identical/differs verdict, and the branch
  §5b therefore selects. Publish the diffs even when identical — "identical" is
  a claim that should be checkable by someone who does not trust you.

Budget note so nobody is surprised: at the measured local rate a 30s window is
~256s wall for the mix passes alone, so prefer short windows and expect roughly
an hour unattended for three.

## C4 — then score, once

Only after C1-C3 are on disk and the branch is determined by §5b rather than by
preference:

```
venv_train/bin/python scripts/duration_probe_score.py \
    --results /tmp/probe_results.json \
    --truth data/duration_probe/truth_anchored.json \
    --negative-results /tmp/negative_results.json \
    --negative-truth data/duration_probe/truth_negatives.json \
    [--exclude-title ... --exclude-item ...]
```

Copy the output **verbatim** into `AGENT_LOG.md` with: the exact command, cache
validity, sample counts, the exclusion set and its justification, the interval,
and the decision. Alongside it record the mixed-hardware deviation, the
Demucs-on-CUDA deviation, the fp32 note, and the unknown-item sensitivity under
rule A (from your own L1 finding: the two `unknown` items push free-form to
1/26 → 17.0pp and opening to 1/21 → 20.7pp, which rule A does not survive —
that is a property of the frozen design and must be printed, not discovered
afterwards).

Report the verdict as it comes out. If it is KILL or INCONCLUSIVE, that is the
result; do not go looking for a variant that reads better, and do not re-run the
scorer with different exclusions to see what happens. One scoring run.

---

## Not yours, still pending Deepti

Prospective long OOC audio; the 28-clip short-OOC sentinel (must be
pre-registered as non-gating before it is built); wiring the registry junk
blocklist; and **the commit** — nothing in this entire line of work is
committed.

## Rules of engagement

- `~/sung_tests --cache-v2` is the only scoreboard. The duration probe is a
  declared exception and graduates nothing on its own.
- Do not re-run `build_negative_arm.py` or `duration_probe_cut.py` — both
  re-draw anchors and would invalidate the cache binding and the labels.
- Do not edit `identify_clip.py`, `handoff.md` beyond §2.6, or
  `data/duration_probe/v1_superseded/`.
- No further GPU spend is authorized.
