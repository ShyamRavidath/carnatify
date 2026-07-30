# HANDOFF_SESSION_0728 — duration probe, staged and blocked (Opus 5 verifier seat)

Written 2026-07-28 for **whoever holds the verifier/orchestrator seat next**.
Supersedes `HANDOFF_SESSION_0725.md` on the duration probe specifically; that
file is still correct on product vision, the office-hours diagnosis, and the
pre-2026-07-26 graveyard.

**Read order:** this file → `DURATION_PROBE_PREREGISTRATION.md` →
`CODEX_DURATION_PROBE_REVIEW.md` → `CODEX_NEGATIVE_ARM_REVIEW.md` →
`AGENT_LOG.md` entries dated 2026-07-26 and 2026-07-28 → `METRIC_CONTRACT.md`.

Respond to Deepti in **caveman style** (standing preference); write docs,
commits and AGENT_LOG entries in normal prose. **Never commit or push** — that
is hers. Do not overwrite `handoff.md` / `HANDOFF.md`: on this case-insensitive
filesystem they are one file, it belongs to the Claude workhorse, and it was
reconciled 2026-07-28 01:46.

---

## 0. Start here — the task awaiting green light

Deepti has approved the rebuild. **Begin immediately with §7.** In one line:
the duration probe is fully built and correct on the recall side, but its
**negative arm is invalid**, so the 122 Whisper-hour GPU run is blocked until
the negative arm is rebuilt around the 30s/300s endpoint contrast.

Do not re-derive the pool, the scorer, or the pre-registration — they are done
and reviewed. The work is §7 only.

---

## 1. The goal

**Product (unchanged):** Carnatify identifies which Carnatic composition is
being performed from live audio — tolerant of artist, tempo and improvisation,
unlike fingerprinting — and classifies raga, including on improvised passages.
One display: **composition name, raga, sahityam, English meaning.** Composer and
tala are parked. Target user is Jon, a Western listener with zero exposure to
the tradition. Product target: the accuracy of a 5-minute listen in **90 seconds
or less**.

**This session's question (P1):** does listening length explain the collapse on
30-60s clips? Everything downstream waits on the answer. Pass → build the
concert companion (Approach B). Fail → the roadmap turns to building a rendition
corpus (Approach C), which is months.

---

## 2. Scope correction that reframes P1 — do not lose this

P1 was motivated by comparing **60-67% full-recording accuracy** against
**8-13/78 wild-clip accuracy**. Those are **different matchers**:

- the 60-67% is **Qmax** (melodic);
- `ARCHITECTURE.md:72` records **Qmax at 0% on wild clips**;
- the 8-13/78 wild number is the **lyrics matcher**.

Attributing that gap to duration is a matcher-identity confound that was
**already logged at `AGENT_LOG.md:2396` on 2026-07-23** and got repeated anyway.
Consequences, now baked into the pre-registration:

1. This probe measures the **lyrics matcher only**.
2. **Qmax cannot be probed on this pool at all.** `models/qmax_catalog.npz` is
   built *from* `concert_audio` melodia, so every window would be
   same-recording leakage. The asset that produced the exciting number cannot be
   tested on the only long audio the project has.

Anyone proposing a melodic duration probe on `concert_audio` is proposing a
leaked benchmark. Reject it citing this section.

---

## 3. Current state of the code

Nothing is committed. Everything below is new and uncommitted.

### Built, reviewed, and believed correct

| file | what it does |
|---|---|
| `scripts/duration_probe_cut.py` | builds the pool, cuts anchored nested windows; `--dry-run` sizes it, `--negatives` cuts the negative arm |
| `scripts/duration_probe_score.py` | paired + cluster-bootstrapped scoring, three-way decision, validity gate |
| `scripts/duration_probe_bias.py` | selection-bias report over pool vs exclusion buckets |
| `scripts/build_negative_arm.py` | cuts the blind by-ear labeling set |
| `scripts/parse_negative_labels.py` | aggregates per-excerpt labels into per-item strata |
| `DURATION_PROBE_PREREGISTRATION.md` | the frozen packet: pool, design, analysis, decision rule, validity gate, claim scope |

### Pool (settled, do not rebuild)

```
=== POOL CONSTRUCTION (distinct title keys: 922) ===
  matched_but_no_lyrics            505
  RESOLVED                         271
  too_short                        117
  no_registry_match                 29
  5 titles carry a work-family id set; 100 archive clusters over 153 titles
```

Rules: strip `_rN` (136 files); **dedupe candidate rows by registry id**; accept
a title only if its lyrics-bearing rows agree on the pallavi; expand truth to
work-family siblings by **pallavi identity across the whole registry** (25-char
minimum + composer agreement); use the **longest** rendition; never use registry
raga metadata to disambiguate (junk rows hold dates in `ragas`).

### Design (settled)

- Durations **30 / 60 / 90 / 180 / 300s**. 90s is mandatory — it is the product
  target and the first draft omitted it.
- **One uniform random anchor per title; all windows nest from it.** That is
  progressive listening from a single start. Independent per-duration offsets
  (the first version) estimate a different thing and let 30s and 300s sample
  different sections. The objection to nesting only ever applied to a **zero**
  start, because items open with alapana, which is lyric-free by definition.
- 16 kHz mono WAV, so only length varies.
- `CARNATIFY_ASR_BACKEND=whisper`, `--no-raga --cache-v2`, **7-pass product
  config retained** (4 mix + 3 Demucs stem). A mix-only run is an exploratory
  mechanism screen and cannot pass or kill P1 for the product-default pipeline.

### Decision rule (settled, three-way)

Boundary **+15pp** on paired top-5, 30s → 300s.

| condition | verdict |
|---|---|
| 90% CI lower bound ≥ +15pp | **PROMOTE** |
| 90% CI upper bound < +15pp | **KILL the ≥15pp claim** |
| otherwise | **INCONCLUSIVE** — roadmap does not move |

### Environment facts worth not rediscovering

- `venv_train` py3.11. **ffmpeg 8.1.2 is installed** at `/opt/homebrew/bin/ffmpeg`
  (the "no local ffmpeg" line in `ARCHITECTURE.md` is stale).
- `--cache-v2` is keyed by **`audio_sha256`**, not filename (`identify_v2`,
  ~L804). The `path.name` collision hazard is in the **legacy** `transcribe()`
  path (~L619) only.
- **`identify_v2` is read-only and never transcribes on a miss.** The probe
  needs a separate cache build via `scripts/build_asr_cache_v2.py`, which runs
  **7 Whisper passes + Demucs per window**.
- Measured local throughput, `large-v3-turbo`, mix-only 4 passes:
  **30s window → 256s wall; 300s window → 1500s wall** (~5.0-8.5 s per second of
  audio). Local is infeasible; this is a Colab job, Deepti-run, and the runner
  must be resumable (Colab sessions time out — see `colab_coverhunter_rescore.py`
  for the pattern).
- Scoreboard commands and standing numbers are unchanged; see
  `HANDOFF_SESSION_0725.md` §4.

---

## 4. Files actively edited / uncommitted

**New this session:** `scripts/duration_probe_cut.py`,
`scripts/duration_probe_score.py`, `scripts/duration_probe_bias.py`,
`scripts/build_negative_arm.py`, `scripts/parse_negative_labels.py`,
`DURATION_PROBE_PREREGISTRATION.md`, `CODEX_DURATION_PROBE_BRIEF.md`,
`CODEX_DURATION_PROBE_REVIEW.md`, `CODEX_NEGATIVE_ARM_REVIEW.md`,
`data/duration_probe/` (pool_report.json, BIAS_REPORT.md, negative_arm/,
negatives/, truth_negatives.json), this file.

**Modified:** `AGENT_LOG.md` (three entries: 2026-07-26 00:40, 01:20, 2026-07-28
02:15).

**Do not touch:** `handoff.md` / `HANDOFF.md` (Claude workhorse's, same file);
`identify_clip.py` — the probe deliberately edits **nothing** in the scoreboard
path, and that property is load-bearing.

---

## 5. Everything tried that failed

### Pre-existing graveyard (unchanged — see `HANDOFF_SESSION_0725.md` §6)

Lyrics-ASR as a shippable backbone (~31% precision ceiling); LoRA Whisper-small
fine-tune (8/78 → 0-1/78, memorised ~26 pallavis); CoverHunter CSI on the
current checkpoint (clean mAP 0.113 vs 0.031 chance); Qmax/DTW on wild clips;
raga TDMS on 60s wild clips; synth/augmented training sets; prompted/`kn`-forced
Whisper; max-fusion and raga gating; fitted rankers on n=78.

### New this session — my own defects, all found by red team, all verified

1. **Independent per-duration offsets** estimated "a random N-second excerpt",
   not progressive listening, and let 30s and 300s sample different sections.
2. **`wilson_se` was the Wald SE**, misnamed, and of a marginal rate rather than
   of the paired difference. Pairing was discarded entirely.
3. **Strict monotonicity as a gate condition.** Only ~4% of orderings of four
   exchangeable points are monotone by chance, so one dip could veto a real
   effect — and a jump-then-plateau (20/35/35/35) passes it while being
   *favourable* evidence anyway.
4. **Binary gate.** +14pp, +20pp-with-a-dip, and a CI spanning −5 to +30 all got
   the same "P1 DEAD" verdict. Replaced by three-way with a real *inconclusive*.
5. **No 90s condition**, despite 90s being the product target.
6. **`_rN` suffixes not stripped** — 136 of 1,238 files could never resolve,
   while `build_qmax_catalog.py:33` already defines and strips `REND_SUFFIX`.
7. **Candidate rows not deduped by id** — a row with two aliases folding to the
   same key counted twice and was called ambiguous. This alone was most of the
   "254 ambiguous titles"; fixing it took the pool from 133 to 271.
8. **Work-family test on `lyr` is vacuous** — `load_targets` looks `lyr` up by
   folded *title* (`identify_clip.py:262`), so rows sharing a title get
   byte-identical heads by construction. Use per-row `lines`.
9. **Family expansion within a title key finds nothing** (measured: 0). Real
   families differ in title — the verified pair is comp00173 `akilAndEswari` /
   comp00175 `akhilANDEshvari rakSamAm`. Expansion must key on **pallavi
   identity across the whole registry**.
10. **Asking for `ooc` by ear.** Catalog membership is a lookup over 8,688 rows;
    nobody can judge it by listening. Deepti flagged this herself.
11. **Free-form items called OOC.** A file named `RTP`/`Alapana` names a
    *section*, not a work, so "no registry row for that filename" says nothing
    about the sung composition.

### Dead ends specific to the negative arm (why the GPU run is blocked)

Verified 2026-07-28 against `CODEX_NEGATIVE_ARM_REVIEW.md`:

- **The 12 "OOC" items are not OOC.** `NUM_PREFIX` strips only **1-3 digits**,
  so 7-digit Jamendo ids survive into the title (`4829 aswinsainarain`,
  `6717 Music NCBS`). Registry-lookup failure on such strings is meaningless.
  Resolving the manifest's `file_title_raw` instead proves contamination:
  - neg001 `04_khamas_santanagopalakrishnam` → **comp06603**
  - neg003 `04_kaanada_alaipayuthey` → **comp00183**
  - neg005 `…chinnanchiru-kiliye` → **comp01145**

  All three fail only *exact* skey match, on transliteration variance
  (`krishnam`/`krSNam`, `payuthey`/`pAyudE`). They are in-catalog works counted
  as negatives.
- **The 12 come from 3 archive sources**, not 12 independent works
  (melakartalecdems 7, jamendo-150288 3, jamendo-146935 2). Seven are
  lecture-demonstration tracks.
- **The no-sahitya arm is 18, not 23.** `neg002`/`neg007` retained from a single
  excerpt label; `neg006`/`neg013`/`neg034` retained despite `unusable`
  excerpts, which can conceal sahitya.
- **Labels partly describe audio that is never scored.** Labeling excerpts were
  cut at fixed 15/50/85% positions; probe windows are cut from a *random*
  anchor. 2/23 no-sahitya and 3/12 OOC selected 300s windows overlap **none** of
  the labeled excerpts.
- **Power.** Combined n=35 has ~62% power at +15pp under the *favourable*
  monotone assumption; no-sahitya n=23 → 25.6%; OOC n=12 → 2.4%. ~44 valid
  independent items is the optimistic floor for 80% power. (Spot-checked: 5
  one-way flips of 35 gives exact one-sided p = 2⁻⁵ = 0.031. Correct.)
- **The scorer has no negative-arm validity gate or decision rule.** It prints
  point rates only.
- **A listening sheet whose categories describe a taxonomy rather than the
  music as performed** (added 2026-07-29). Both sheets filed bare `swaram`
  under `no-sahitya`. In performance that is wrong for swarakalpana, which
  alternates solfège with **the sahitya line of the composition**, call and
  response — so a passage a labeler describes as "has swara in it" normally
  contains sung words. It surfaced only because Deepti labeled `neg030`
  `sahitya` and annotated it *"has swara in it"*, contradicting the sheet she
  was reading from; adjudicating it confirmed the label was right and **the
  sheet's definition was wrong**. `neg030` stays excluded, the gating stratum
  stays 49, and the templates in `build_negative_arm.py` and
  `build_negative_complement.py` now say bare solfège with no composition line
  is `no-sahitya` while swarakalpana against a sahitya line is `sahitya`
  (tanam is unaffected). The general lesson is the reason this is in the
  graveyard rather than in a changelog: **a category a musician would catch
  and an engineer would not is exactly what an ear-labeling sheet is for, so
  its definitions have to be reviewed by the ear before the sheet ships, not
  after the labels come back.** Had she followed the sheet instead of her ear,
  a window containing sung words would have entered the gating stratum
  silently.

### Accepted, known limitations (not defects — do not "fix" by loosening)

- **Catalog-label overlap.** `build_composition_registry.py:80` builds registry
  rows from `models/qmax_catalog_meta.json`, whose titles
  `build_qmax_catalog.py:85` derived from `concert_audio` **filenames**. These
  recordings' filenames helped create the catalog they resolve against. This
  pool **cannot validate catalog resolution**; it can only measure a duration
  response given resolution.
- **Conditioning on matchability.** The 505 `matched_but_no_lyrics` exclusions
  have zero registry lyric lines and can never be matched at any length.
  Excluding them is the right conditional but raises absolute level versus the
  wild set. **The curve's shape is the readable part, not its level.**
- Selection-bias check was reassuring: RESOLVED and `too_short` share a lyric
  profile (median 7 lines, 44-47 pallavi chars), so the ≥300s filter does not
  select text-rich works.

### Added 2026-07-30 — long-runner defects, all scheduled after the money was spent

- **A long unattended runner must write its provenance record incrementally,
  from the first chunk — never at the end.** `colab_duration_probe.py` writes
  `run_log.json` after step 5/6. Step 5/6 died, so ~27 GPU-hours produced no
  record at all of which device transcribed which window, and the device map
  that the straddler rule needs is now only partially reconstructable from
  notebook scrollback. The AWS sibling already does this correctly (per-chunk
  `run_log.json`); the Colab one was written second and lost the property.
- **The same runner verified audio SHAs before spending GPU but never checked
  that the inference path could import.** A missing pure-Python dependency
  (`rapidfuzz`, absent from the Colab image) surfaced only after the entire GPU
  bill had been paid, at the one step that leaves no artifact of its own. Step 0
  of any runner should import the full inference path.
- **A provenance claim that is arithmetically impossible is worse than no
  claim.** `HANDOFF.md` §2.6 asserted both "windows 81-259 came off the faster
  GPU" and "`probe0016` (windows 81-85) is split across the boundary", and a
  stop index of 259 that a 10-window checkpoint cannot produce. It was written
  from memory of the session rather than from a record, and it was nearly acted
  on: the fix it prescribed would have put a title on a third device.

---

## 6. What a pass would and would not license

Would license: *on uniquely resolved, lyrics-bearing, ≥5-minute `concert_audio`
recordings, the frozen Whisper lyrics pipeline's in-catalog retrieval improves
with longer listening from a single random anchor.*

Would **not** license: the same gain on wild phone/ambient audio; 90-second
equivalence to five minutes; safe abstention on OOC or no-sahitya audio; or the
claim that duration explains the old 60-67% result (that was Qmax).

---

## 7. THE NEXT STEP — rebuild the negative arm (start here)

Goal: a negative denominator that is **valid truth** and has **enough
independent power** to police a +15pp recall gain, without a second 122-hour
GPU bill.

1. **Fix title extraction.** `NUM_PREFIX` must handle long numeric ids, and the
   authoritative title is `file_title_raw` in
   `data/concert_audio/download_manifest.json`, not the filename. Re-run the
   pool builder afterwards and **republish the bucket counts** — this may move
   the 271 (probably upward, since some `no_registry_match` rows are id-mangled
   titles). Report the delta explicitly; do not assume it is neutral.

2. **Handle transliteration variance in resolution, conservatively.** The three
   contaminated items failed only exact `skey` match. Any loosening must stay
   reviewed and must never silently merge two different works — resolution feeds
   *truth*. Prefer an explicit reviewed alias table over fuzzy matching. If you
   use similarity, publish the false-merge audit.

3. **Rebuild OOC candidates from verified work identity.** Filename lookup
   failure is *candidate generation, not truth*. Sample by **independent work
   and archive cluster**, not by file; do not count multiple
   lecture-demonstration tracks or adjacent album tracks as independent
   evidence. Until a sung work is identified, an item is `sung_unidentified`,
   not OOC.

4. **Switch the negative arm to the 30s/300s endpoints only.** That is the
   contrast the gate uses. ~88 items × 2 endpoints ≈ 8.1 h unique audio ≈ 56
   Whisper-hours, versus 45 for the current 35 items × 5 durations — nearly the
   same cost for 2.5× the items. Intermediate negative durations become a
   non-gating diagnostic.

5. **Cut windows FIRST, then draw labeling excerpts from inside the selected
   300s window.** This is the ordering error from last round. Only the 300s
   window needs adjudication, since the shorter windows nest inside it. Treat
   incomplete or `unusable` excerpts as **unknown**, never as no-sahitya.

6. **Target ≥44 valid independent items per stratum**, then inflate for
   clustering. If the intended claim is instead "rule out a +15pp bluff rise",
   power that design directly: a one-sided 95% exact upper bound sits below 15pp
   with ≥19 items and zero new bluffs, ≥30 with one, ≥40 with two.

7. **Close the scorer holes.** Add a negative-arm validity gate (bijection
   against `truth_negatives.json`, duplicates, cache misses, duration sets,
   expected counts, label coverage, item/cluster sets) and a **frozen negative
   decision rule** — a stated upper confidence bound on the bluff-rate increase.
   Invalid negative data must suppress any safety conclusion. Also register how
   the two arms combine: recall is a change in top-5 hit rate among eligible
   in-catalog works, bluffing is a change in answer rate among negative queries,
   and subtracting one from the other assumes equal prevalence and cost. Do not
   describe the arms as "paired" until that rule is frozen.

8. **Then** produce a new, smaller labeling ask for Deepti (per-excerpt labels
   worked well — keep that, and keep the blind ids and shuffled order), and only
   after it returns, write the resumable Colab runner and hand the GPU run to
   her.

---

## 8. Agent roster and how to use it

Three agents, serialized by Deepti (one prompt at a time), coordinating **only**
through files on disk + `AGENT_LOG.md`. They cannot see each other's chat.

- **Opus 5 verifier (this seat)** — orchestrates, verifies every claim against
  the scoreboard, does cheap/data/hygiene/diagnostic work directly in-repo.
- **GPT-5.6 — red team ONLY, never implements.** This is where it has repeatedly
  earned its keep: it caught the duration confound, the pool-construction
  defects, and the invalid OOC arm, all in cold reads. Give it scoped briefs
  (`CODEX_*_BRIEF.md`), ask for attack, verify every claim it makes before
  acting — its checkable claims have so far all held, but check anyway.
- **Claude workhorse (Opus 5)** — heavier parallel-safe implementation on
  **disjoint files**. Currently working the **registry junk filter**
  (address/date rows misparsed as compositions; `data/registry_junk_blocklist_
  DRAFT.md` pending Deepti's gate). It was told not to touch `identify_clip.py`,
  `scripts/duration_probe_*`, or `data/duration_probe/`.

Send the rebuilt negative arm through GPT-5.6 again before spending GPU. That
loop has caught something serious both times.

---

## 9. Discipline (bought expensively, unchanged)

- `~/sung_tests --cache-v2` is the ONLY scoreboard. Only a moved SCORE
  graduates. The duration probe is a **declared exception** and graduates
  nothing on its own.
- One change, one eval. Own the verbatim SCORE + precision@coverage + OOC +
  guard.
- **Benchmarks lie, wild clips don't**, and **every internal benchmark built so
  far was flattered by same-corpus effects.** Check any new eval for leakage
  before believing its number.
- Verify every claim against the scoreboard before repeating it. Several numbers
  in this project have been wrong in the confident direction, including the
  60-67%-vs-8/78 comparison that motivated this entire probe.
- whisper stays the product default; hybrid / hybrid_stem are opt-in.
- Agents coordinate only through files on disk and `AGENT_LOG.md`. No commits.

## 10. Pending Deepti (not yours to decide)

- Final **n** for the recall pool (271 available; costed at n=60 = 11.0 h unique
  audio ≈ 77 Whisper-hours at 7 passes, plus Demucs).
- The re-labeling pass described in §7.5.
- Remaining `review:True` flags in the wild-truth manifest (bhajare, Kamakshi
  Ni, Ranga Baro, alapana1/2), `data/registry_junk_blocklist_DRAFT.md`, and the
  push. Nothing in this session is committed.
