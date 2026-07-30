# Workhorse brief — pre-GPU repair of the negative arm (round 2)

Date: 2026-07-29. For the **Opus 5 workhorse** (implementation seat).
Red team: `CODEX_NEGATIVE_ARM_REVIEW_R2.md` (GPT-5.6, verdict: *do not spend the
45 negative Whisper-hours as staged*).

**No GPU has been spent. Nothing in this line of work is committed.** Do not
commit, do not push, do not run the GPU — those are Deepti's. Respond to her in
caveman style; write code, docs and `AGENT_LOG.md` entries in normal prose.

**Read order:** this file → `CODEX_NEGATIVE_ARM_REVIEW_R2.md` →
`HANDOFF_SESSION_0729.md` → `DURATION_PROBE_PREREGISTRATION.md` §§1, 6, 6b, 6c,
7 → `scripts/build_negative_arm.py`, `scripts/parse_negative_labels.py`,
`scripts/duration_probe_score.py` → `HANDOFF_SESSION_0728.md` §§1-2, 5-6, 8-9.

---

## 0. What was verified before this brief was written

Do not take the review on faith; neither did I. Checked against the code and the
staged data:

| review claim | status |
|---|---|
| sweep is 10s every 20s → fifteen unheard 10s gaps, incl. 290-300s | **holds** — `build_negative_arm.py:222`, `SCAN_EVERY=20`, `SCAN_LEN=10` |
| scorer has no per-source readout | **holds** — zero occurrences of `source` in `scripts/duration_probe_score.py`; `negative_transitions()` (L442) groups on `stratum` alone |
| gating n=51 is 26 free-form + 21 opening + 4 unidentified | **holds** — recomputed from `negative_labels.json` |
| the 2 unknowns are `neg027` (`unusable`, free-form) and `neg062` (blank, opening) | **holds** |
| validity gate holes (durations, per-item duplicates, stratum agreement, cache field, result schema, no SHA binding) | **holds** — `validate_negatives()`, L386-438 |
| pool no-op is real (923/505/271/117/30) | **holds** — codex reproduced it independently |
| `~/sung_tests` retains source URLs and durations | **holds** — `fetch_manifest.tsv`, e.g. `417s @145s` |
| "at least 14 reviewed OOC sources exceed 300s" | **does NOT reproduce as stated.** 28 OOC clips on disk, 23 have manifest rows, of which **9** carry a parseable source duration ≥300s. The other ~13 have title text spilled into the duration column (tab in the title). The underlying point — the sources are reacquirable from retained URLs — stands; the count does not. Re-derive it with a real parser before anyone quotes it. |

`CODEX_NEGATIVE_ARM_REVIEW_R2.md` also records that codex's one ostensibly
read-only command, `duration_probe_cut.py --dry-run`, rewrote the untracked
`data/duration_probe/pool_report.json`. That is a real defect — see T7.

---

## 1. The hard constraint: do NOT re-run `build_negative_arm.py`

`build_negative_arm.py` re-cuts every window, re-draws anchors from
`rng.uniform`, re-assigns `negNNN` ids and re-shuffles the sheet. Deepti's 69
labels are keyed to the current ids. **Re-running it destroys the labeling
work.** Every task below operates on the audio and sidecars already on disk:

```
data/duration_probe/negatives/*.wav              140 windows (70 items x 30s,300s)
data/duration_probe/negative_arm/*_scan.wav      70 sweeps
data/duration_probe/negative_arm/LABELING_SHEET.md   filled in, 69/70
data/duration_probe/negative_arm/_mapping.json
data/duration_probe/negative_arm/negative_labels.json
data/duration_probe/truth_negatives.json         sidecar, strata stamped
```

Also do not touch: `identify_clip.py` (the probe edits nothing in the scoreboard
path and that property is load-bearing); `handoff.md` / `HANDOFF.md` (same file
on this filesystem, belongs to the Claude workhorse);
`data/duration_probe/v1_superseded/`.

---

## T1 — complementary sweep. **Do this first; it unblocks Deepti.**

The label says "no sung words in this 300s window" but the ear heard only
0-10, 20-30, … 280-290. Fifteen 10-second stretches were never played, and a
single pallavi phrase in one of them is enough to make a lyrics matcher answer.
The gating stratum is therefore not yet established.

Build the complement and re-ask, using audio already on disk.

**New script** `scripts/build_negative_complement.py`:

- Input: the 51 items whose stratum is currently `no-sahitya` in
  `data/duration_probe/negative_arm/negative_labels.json`. Nothing else.
- For each, read the existing `data/duration_probe/negatives/<item>d300.wav` —
  **do not re-cut from the mp3**, the point is that the ear hears exactly the
  audio the pipeline will be given.
- Snippets at offset 10, every 20: `10-20, 30-40, …, 290-300`. Fifteen × 10s =
  150s per item. Union with the original sweep must be exactly `[0, 300)` with
  no gap and no overlap — assert this in the script, do not eyeball it.
- Write `data/duration_probe/negative_arm/complement/<item>_scan2.wav`, a
  `LABELING_SHEET_2.md` in the same format and vocabulary as sheet 1, and a
  `_mapping2.json`. Re-shuffle with a **new seed** so sheet-1 order carries no
  information into sheet 2, and keep ids blind.
- Sheet preamble must say plainly what changed and why: sheet 1 covered half the
  window, this is the other half, same binary question, same "stop as soon as
  you hear singing" rule, same treatment of blanks. ~2 hours of listening at
  worst; most rows end in seconds.

**Then `scripts/parse_negative_labels.py`:**

- Read both sheets. Gating requires `no-sahitya` on **both** sweeps. `sahitya`
  on either sweep → `sahitya`. Anything else (blank, `unusable`, disagreement,
  sheet-2 row missing) → `unknown`.
- Record `labels_given_1` and `labels_given_2` separately per item; do not
  collapse them into one list.
- Stamp `sweeps_required` and `sweeps_applied` into `truth_negatives.json`.
- If sheet 2 is absent entirely, the parser must **not** silently reproduce
  today's 51-item gating stratum. Fail loudly, or stamp every gating candidate
  as `unknown`. Choose one and say which in the docstring.

**Scorer:** `validate_negatives()` must reject a sidecar whose
`sweeps_applied < sweeps_required`. A single-sweep arm must not be able to print
a safety conclusion.

**Acceptance:** 51 `_scan2.wav` files, each 150s ± 1s; the coverage assertion
passes; sheet 2 has 51 rows; parser round-trips a hand-made fixture covering all
four label combinations; scorer suppresses on a single-sweep sidecar.

Expect the gating stratum to **shrink**. That is the correct direction and is
not a reason to soften the rule.

---

## T2 — per-source readout, and a source-specific gate

`n=51` is 26 free-form + 21 opening + 4 unidentified. Those weights came from
sampling quotas and labeling yield, not from any product prevalence. The pooled
Clopper–Pearson bound is a valid bound **on that design mixture and nothing
else**. If all new bluffs land in one source, pooled reads 3/51 → 14.5pp →
SAFE, while free-form alone is 3/26 → 27.2pp and opening alone 3/21 → 32.9pp.

`DURATION_PROBE_PREREGISTRATION.md:207` already promises "each source is also
reported alone". The scorer does not do it. Implement the promise.

- `candidate_kind` is already stamped on every sidecar window
  (`build_negative_arm.py:405`), so **no re-cut is needed** to get this.
- Generalise `negative_transitions()` to group on `(stratum, candidate_kind)`
  as well as `stratum`, and print the gating stratum broken out by source: n, b,
  r, and the exact one-sided 95% upper bound for each.
- Print each source's `power_table` too, so the reader sees what that n can
  and cannot rule out before seeing b.

**The gate itself is a pre-registration change and is not yours to freeze.**
Implement the readout, print both candidate rules side by side, and flag the
choice for Deepti:

- *(recommended)* **source-specific conjunction** — SAFE requires the upper
  bound below +15pp for the pooled stratum *and* for each source with n ≥ 20.
  At b=0 that is ~10.9pp on n=26 and ~13.3pp on n=21, both clearing; at b=1 in
  either source it fails. In plain terms: zero new bluffs in each major source.
  Strict, but it is the only reading that means anything without registered
  weights.
- **frozen mixture weights** — keep the pooled bound, but register *why* 26:21:4
  is the right weighting. Nobody has an argument for that, which is why it is
  the second option.

Codex is right that the pooled bound is not wrong, only narrow: it bounds the
mixture, and the mixture is an artifact of how sampling went.

---

## T3 — close the validity gate

`validate_negatives()` (`scripts/duration_probe_score.py:386`) can currently
print SAFE on a broken run. Each of these is a concrete hole; close all of them
and add a unit test per hole in `tests/`.

1. **Durations are trusted from the sidecar.** A sidecar registering only 300s
   passes, then `short == long`, `b == 0`, and n=51 prints SAFE at 5.7pp. Add a
   frozen `DESIGN_DURATIONS = (30, 300)` and require an exact match.
2. **No one-row-per-(item, duration) check.** Duplicate item-duration metadata
   validates today. The existing check catches duplicate *result stems* only.
3. **No stratum-agreement check.** An item may carry different strata at its two
   endpoints.
4. **`n_items`, `stratum_counts`, `seed`, and cluster uniqueness within the
   gating stratum are never validated** against the windows actually present.
5. **Only `cache_v2 == "MISS"` is rejected** (L416). A missing, `None`, or
   malformed cache field passes. Require the field present and in a known-good
   vocabulary.
6. **Result schema is unvalidated.** `res.get('composition_confidence') != 'none'`
   (L450) treats a *missing* field as an answer. Missing at both endpoints gives
   `b=0` and can print SAFE off a run that produced nothing. Require the field
   present and in the known confidence vocabulary on every row.
7. **Labeled audio is not bound to inference audio.** Correct filenames holding
   swapped or regenerated audio validate. Fix without re-cutting: add a one-off
   `scripts/stamp_negative_shas.py` that hashes the existing
   `data/duration_probe/negatives/*.wav`, stamps `audio_sha256` per window into
   `truth_negatives.json`, and *never* writes audio. Have the scorer re-verify
   at read time. Note `--cache-v2` is already keyed by `audio_sha256`
   (`identify_v2`, ~L804), so the two agree by construction.

---

## T4 — stop the verdict overclaiming

`duration_probe_score.py:362` prints:

> PROMOTE. Longer listening buys in-catalog recall without a ruled-in bluff rise.

Only the **no-sahitya** stratum gates. OOC abstention is unmeasured and, per
`HANDOFF_SESSION_0729.md` §4, unmeasurable from assets on disk. `METRIC_CONTRACT.md`
requires OOC bluffs separately.

- Narrow the string to "*no-sahitya* bluff rise", and print an explicit line
  that OOC abstention at length is unmeasured and this verdict does not
  authorize showing results to a user.
- `DURATION_PROBE_PREREGISTRATION.md` §6c row 1 needs the same narrowing. As
  written, §6c permits a combined PROMOTE while §7 correctly says the probe
  cannot license safe OOC abstention — the document contradicts itself and the
  scorer follows the wrong half.
- What a passing conjunction licenses is a **research** lever on the archive
  domain, not product-presentation safety. Say so in both places.

Leave the statistics alone. Codex checked the n=51 arithmetic (5.705 / 8.967 /
11.835 / 14.508 / 17.056), confirmed that ignoring reverse flips is genuinely
conservative for the net-change estimand since `Δ = P(0→1) − P(1→0) ≤ P(0→1)`,
and confirmed the conjunction is an intersection-union decision needing no
multiplicity penalty. One rationale in §6b **is** stale and should be corrected:
detection is no longer "unreachable" — under the no-reverse-flip model n=51 has
~90% power against a true +15pp rise. The upper-bound framing is still the more
useful question; it is just no longer *forced* by sample size, and the document
should stop claiming it is.

---

## T5 — worst-case handling for the two unknowns

`neg027` (free-form, `unusable`) and `neg062` (opening, blank, row 42 with
labeling continuing afterwards) are **informative missingness**, not random
loss. Print, next to the headline bound, the worst case in which both were true
no-sahitya items that bluffed: `b+2 / n+2`. At today's numbers 2/51 → 4/53,
whose upper bound is ~16.4pp and does **not** clear +15pp. The headline stays
the observed bound; the worst case is reported beside it, never buried.

---

## T6 — pending Deepti, do not decide these yourself

1. **`neg030`.** Labeled `sahitya` with the note *"has swara in it"*, while the
   sheet lists swaram under `no-sahitya`. Codex's point is sharper than the
   handoff's: excluding it is **not** automatically safe. If it is swaram-only
   it meets the registered definition, and solfège is plausibly a *high*-bluff
   input for Whisper — so dropping it biases the safety estimate downward rather
   than merely shrinking n. Resolve the definition before anyone sees a
   prediction. Same audit for any other `sahitya` row whose note says tanam or
   swaram (`neg004` is already consistent and needs nothing).
2. **The gate choice in T2** — source-specific conjunction vs. registered
   mixture weights.
3. **Prospective long OOC audio** (`HANDOFF_SESSION_0729.md` §4). Codex is right
   that "wholly new discovery" overstates it: `~/sung_tests/fetch_manifest.tsv`
   retains source URLs and durations, so reacquisition is a re-download, not a
   hunt. See §0 for the count correction.
4. **The 28-clip short-OOC sentinel** — a nested 30s → full-clip (43-84s) arm
   over the existing reviewed OOC clips, reusing existing caches. At n=28, b=0
   gives 10.1pp and b=1 15.9pp (recomputed with the repo's own
   `clopper_pearson_upper`; the review said 10.2). This **cannot** speak to 300s and must be
   pre-registered as a non-gating sentinel if it is run at all. Do not build it
   until it is registered; do not let it drift into the gate.
5. **The commit.** Nothing in this line of work is committed.

---

## T7 — small, unambiguous fixes

- `duration_probe_cut.py --dry-run` writes `data/duration_probe/pool_report.json`.
  A dry run must write nothing; gate the write on `not args.dry_run` and print
  the report to stdout instead.
- Publish the 16 relaxed-key-only resolutions in
  `data/duration_probe/TITLE_RESOLUTION_AUDIT.md` with a one-line human verdict
  each. Codex flags `B - Harikambhoji` and several Melakartha lecdem tracks as
  obvious false matches. Exclusion-only use means these cost sample size and
  never validity, so this is documentation, not a code change — but the
  completeness caveat should be written down rather than left implied.
- Recompute the GPU bill for the arm the probe actually reads. The 8
  `in-catalog` items feed no registered readout. Transcribing 51 gating + 9
  `sung_unidentified` + 2 `unknown` = 62 items × 330s ≈ 5.7 h unique audio ≈ 40
  Whisper-hours at the 7-pass config, against 45 for all 70. Keeping the 2
  unknowns lets T5's worst case be *observed* rather than assumed, which is
  worth their cost. Print the realized number; do not hard-code it.

---

## Order of work

T1 first and alone — it is the long pole, because it gates ~2 hours of Deepti's
listening and everything downstream waits on the labels. Ship it, hand her the
sheet, then do T3 → T2 → T4 → T5 → T7 while she listens.

The Colab runner is **after** all of this, not now. When it comes: it must be
resumable (`colab_coverhunter_rescore.py` has the pattern), and it needs
`scripts/build_asr_cache_v2.py` over both `data/duration_probe/anchored/` and
`data/duration_probe/negatives/`, because `identify_v2` is read-only and never
transcribes on a miss. Measured local throughput at `large-v3-turbo`, mix-only
4 passes: 30s window → 256s wall, 300s window → 1500s wall. Local is infeasible.

## Rules of engagement

- Implementation seat. You may edit the probe scripts and the pre-registration,
  except where a task says a choice is Deepti's — those get flagged, not decided.
- `~/sung_tests --cache-v2` is the only scoreboard. The duration probe is a
  declared exception and graduates nothing on its own.
- Do not loosen the OOC definition. That is the defect that killed the first arm.
- Log what you did in `AGENT_LOG.md` in normal prose when you are done.
