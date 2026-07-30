# HANDOFF_SESSION_0729 — duration probe fully staged, awaiting red team then GPU

Written 2026-07-29 for **whoever holds the verifier/orchestrator seat next**.
Supersedes `HANDOFF_SESSION_0728.md` **on the negative arm only**. That file is
still correct on §1 (the goal), §2 (the matcher-identity scope correction), §6
(what a pass licenses), §8 (agent roster) and §9 (discipline), and those
sections are not repeated here.

**Read order:** this file → `DURATION_PROBE_PREREGISTRATION.md` (§1, §6, §6b,
§6c are new or rewritten) → `CODEX_NEGATIVE_ARM_REBUILD_BRIEF.md` →
`data/duration_probe/TITLE_RESOLUTION_AUDIT.md` → `AGENT_LOG.md` entries dated
2026-07-28 02:45 and 2026-07-29 → `HANDOFF_SESSION_0728.md` §§1-2, 5-6, 8-9.

Respond to Deepti in **caveman style** (standing preference); write docs,
commits and AGENT_LOG entries in normal prose. **Never commit or push** — that
is hers. Do not overwrite `handoff.md` / `HANDOFF.md`: on this case-insensitive
filesystem they are one file and belong to the Claude workhorse.

---

## 0. Start here — the state in one paragraph

`HANDOFF_SESSION_0728.md` §7 is **complete**. The negative arm was rebuilt from
scratch, Deepti's labels came back on 2026-07-29, and the whole probe — recall
arm and negative arm — is staged and internally valid. **No GPU has been
spent and nothing is committed.** Two gates remain before the run: the red team
(`CODEX_NEGATIVE_ARM_REBUILD_BRIEF.md`, ready to hand to GPT-5.6, updated with
the realized numbers), then a resumable Colab runner. Do not skip the red team;
it has caught something serious on both previous passes.

One decision is genuinely blocked and is **not** the next seat's to make:
measuring OOC abstention at 300s requires audio that does not exist on disk.
See §4.

---

## 1. What the arm now is

| | value |
|---|---|
| durations | **30s and 300s only** (the contrast the gate reads) |
| items cut | 70 (140 windows) |
| gating stratum, realized | **51 `no-sahitya` items over 51 distinct clusters** |
| sensitivity stratum | 9 `sung_unidentified` (reported, never gates) |
| dropped | 8 `in-catalog`, 2 `unknown` |
| cost | 6.4 h unique audio ≈ **45 Whisper-hours** at the 7-pass config |

Same GPU bill as the rejected 35-item × 5-duration arm, for twice the items and
a valid design.

**What n=51 buys** under the frozen rule (exact one-sided 95% Clopper–Pearson
upper bound on the new-bluff rate): 5.7pp at b=0, 9.0 at b=1, 11.8 at b=2,
**14.5 at b=3**. The arm survives three surprise answers. A free-form-only
design would have survived one — the opening-window source contributed 21 of
the 51 gating items and is what bought that margin.

Yield: 26/34 free-form and 21/30 openings came back no-sahitya.

---

## 2. What changed since 0728, and why (do not silently revert any of it)

### Title extraction (`scripts/duration_probe_titles.py`, new)

`NUM_PREFIX` stripped only 1-3 digits, so seven-digit Jamendo ids survived into
the title. Now: any number of leading digits plus archive track ranges, and
`download_manifest.json`'s `file_title_raw` supplies the title when the filename
is demonstrably not one (a stripped 4+ digit id, `Track 02` / `Concert 163` /
`A` / `xxxx`, or too short).

**Pool delta is ZERO.** 923 distinct keys / 505 / **271** / 117 / 30. The
handoff predicted the count might rise; it did not, and that is reported rather
than assumed. Thirteen id-mangled keys became real titles, all landing in
`no_registry_match` — they are negative candidates, not pool members.

### Two resolution keys, asymmetric on purpose

- **Exact `skey` + a hand-reviewed alias table** (`data/duration_probe/
  title_aliases.json`, currently empty) is the **only** route into truth.
- A relaxed consonant-skeleton key `cskel` (drop vowels; unify voicing d/t b/p
  g/k j/c; unify nasal m/n; collapse gemination; edit distance ≤ 1) may only
  ever **disqualify** an OOC candidate. Over-matching then costs sample size and
  never validity.

Calibration: all three contaminated items the red team named resolve to the ids
it named. False-merge audit published: 388 of 8,058 consulted skeletons collide,
touching 910 of 8,688 rows.

**Anyone proposing to use the relaxed key to create a truth id is proposing a
silent work relabeling. Reject it citing this section.**

### Ordering, and what the ear is asked

Windows are cut **first**; the labeling sweep is cut from **inside the selected
300s window**. Only the 300s window needs a label — the 30s window nests at its
start. Each item got one `_scan.wav`: 10s every 20s of the scored window, 50%
duty, no unheard gap over 10s.

The label is **binary** (`sahitya` / `no-sahitya`, plus `unusable`). Catalog
membership is a join, never a listening judgment. `unusable`, coin-tosses and
blanks all become `unknown`, never no-sahitya.

### Frozen negative rule and combination rule (`DURATION_PROBE_PREREGISTRATION`
§6b, §6c)

Detection at +15pp needs ~44 items that *flip* and no corpus here promises them,
so the rule is an **upper-bound claim**. A negative validity gate now exists
(bijection, cache misses, strata present, `labels_applied`, registered
durations, `expected_windows`, identical item sets at both endpoints) and
invalid negative data **suppresses the safety conclusion**.

The two arms are **not subtractable and are no longer called "paired"**. The
verdict is a **conjunction**: recall PROMOTE with safety unestablished is
**HOLD**, not promote, and does not authorize showing results to a user.

---

## 3. Files (all uncommitted)

**New this session:** `scripts/duration_probe_titles.py`,
`CODEX_NEGATIVE_ARM_REBUILD_BRIEF.md`, `HANDOFF_SESSION_0729.md`,
`data/duration_probe/{TITLE_RESOLUTION_AUDIT.md, title_aliases.json,
verified_ooc.json, v1_superseded/}`.

**Rewritten:** `scripts/build_negative_arm.py`,
`scripts/parse_negative_labels.py`.

**Modified:** `scripts/duration_probe_cut.py` (title extraction delegated;
`cut_negatives` removed — it cut scored windows *after* labels came back),
`scripts/duration_probe_score.py` (negative gate, frozen rule, combined
verdict), `DURATION_PROBE_PREREGISTRATION.md`, `AGENT_LOG.md`.

**Regenerated data:** `data/duration_probe/{pool_report.json,
truth_negatives.json, negatives/*.wav (140), negative_arm/*.wav (70),
negative_arm/LABELING_SHEET.md (filled in), negative_arm/negative_labels.json}`.

**Do not touch:** `handoff.md` / `HANDOFF.md` (workhorse's, same file);
`identify_clip.py` — the probe deliberately edits **nothing** in the scoreboard
path and that property is load-bearing;
`data/duration_probe/v1_superseded/` — Deepti's v1 labels, kept for audit and
**not reusable** (they describe excerpts cut at 15/50/85% while the scored
windows came from an independent anchor).

### The commands

```
# negative arm, already built and labeled — rebuild only if you must
venv_train/bin/python scripts/build_negative_arm.py --dry-run
venv_train/bin/python scripts/parse_negative_labels.py

# recall arm — n still pending Deepti
venv_train/bin/python scripts/duration_probe_cut.py --dry-run --n 271
venv_train/bin/python scripts/duration_probe_cut.py --n 60 --arm anchored

# scoring, after the GPU run
venv_train/bin/python scripts/duration_probe_score.py \
    --results /tmp/probe.json --truth data/duration_probe/truth_anchored.json \
    --negative-results /tmp/neg.json \
    --negative-truth data/duration_probe/truth_negatives.json
```

---

## 4. The OOC stratum is EMPTY, and this is a finding

Of 1,238 recordings in `data/concert_audio`: 1,175 resolve exactly, **16
resolve only under the relaxed key** — these are exactly the items the old arm
was free to call OOC, including all three the red team named plus seven
`melakartalecdems` lecdem tracks — 36 are free-form, and 11 resolve to nothing.

Those 11 are `G C-8-13781 13162o`, `HMV P 5866 G C -8-10152`,
`Melakartha Chakkaram`, `B - Karaharapriya`, `A - Saveri`, `SSI`, `xxxx`,
`varnam vasantha`, `SN 501`, `IMCpresents-In-Memoriam-…`,
`G C-8-13782 13163o`. **Not one names a composition.** They are upload ids,
shellac catalogue numbers, archive slot names, and a genre paired with a raga.
None can be verified absent from a catalog that was itself partly built from
these filenames.

`~/sung_tests` holds 28 reviewed OOC clips but its longest is 84s, so it cannot
supply a 300s endpoint either.

**Therefore OOC abstention at length is unmeasurable from assets on disk.** An
item reaches the `ooc` stratum only through `data/duration_probe/
verified_ooc.json`, a reviewed identity file, which is empty. Measuring it needs
prospectively acquired audio — recordings ≥300s with trustworthy titles
verifiably absent from the registry (film songs, bhajans, Hindustani). Acquiring
a corpus is **Deepti's call**, not the next seat's.

Do not paper over this by loosening the OOC definition. That is precisely the
defect that killed the last arm.

---

## 5. Graveyard additions from this session

Added to the standing graveyard in `HANDOFF_SESSION_0728.md` §5:

1. **Blanket "the manifest title is authoritative".** `file_title_raw` is often
   *worse* than the filename — it carries the raga and composer (`nannubrOvu
   -lalitA`), the file extension, or a slot name (`Track 02`, `Concert 163`).
   The filename is right for 1,222 of 1,238 files. Use the manifest only where
   the filename is demonstrably not a title.
2. **Segment-splitting a raw title without a stopword list.** `01_varnam_
   vasantha` yields the "title" `varnam`; `06_kapi-alapana_ragamalika_…` yields
   `ragamalika`. Genre and form words must be rejected as segments.
3. **Letting a section name resolve to a work.** `Alapana.mp3` matched
   `comp00196` (canonical "Alapana", 19 ragas, no lyrics — already on the junk
   blocklist) and `rAgam tAnam pallavi.mp3` matched `comp06030`. Section names
   are now filtered out of the candidate set entirely.
4. **`str.maketrans('dbgjmz','ptkcns')`** — my own bug, caught by the
   calibration set. It maps d→p and b→t, not d→t and b→p, and silently broke
   one of the three test cases. The correct string is `'tpkcns'`. The lesson is
   the calibration set, not the typo: any new key needs known-answer cases
   before it is trusted.
5. **Believing a "fix" that changes nothing.** The pool delta came back exactly
   zero, which is either a correct no-op or a repair that never took effect. It
   was verified to be the former by diffing the per-key buckets, not by
   inspection.

---

## 6. THE NEXT STEP

1. **Hand `CODEX_NEGATIVE_ARM_REBUILD_BRIEF.md` to GPT-5.6.** Red team only, no
   implementation. Verify every claim it makes before acting — its checkable
   claims have all held so far, but check anyway. The brief already names the
   three things most worth attacking: the opening-window source as a population,
   the upper-bound rule's conservatism and the conjunction's joint error rate,
   and the exclusion-only argument for the relaxed key.

2. **Two labeling details are open and are in the brief.** `neg004` was labeled
   `no-sahitya` with the note *"this is tanam, so it has some characters but no
   actual sahitya"* — consistent with the sheet. `neg030` was labeled `sahitya`
   with the note *"has swara in it"*, but the sheet lists swaram **under
   `no-sahitya`**. It was left as labeled, which only shrinks the gating
   stratum — the safe direction — but whether "swaram alone" is no-sahitya for
   a *lyrics* matcher is a real question, since Whisper transcribes solfège as
   words. Do not reclassify it unilaterally.

3. **Then the Colab runner.** It must be resumable — Colab sessions time out;
   see `colab_coverhunter_rescore.py` for the pattern. It needs
   `scripts/build_asr_cache_v2.py` over both `data/duration_probe/anchored/` and
   `data/duration_probe/negatives/`, because **`identify_v2` is read-only and
   never transcribes on a miss**. Measured local throughput at
   `large-v3-turbo`, mix-only 4 passes: 30s window → 256s wall, 300s window →
   1500s wall. Local is infeasible.

4. **Then hand the GPU run to Deepti.** She runs it; the permission classifier
   blocks agent-run deploys.

---

## 7. Pending Deepti (not the next seat's to decide)

1. **Prospective OOC audio** — see §4. The only route to measuring OOC
   abstention at length.
2. **Final n for the recall arm.** 271 available; n=60 ≈ 11.0 h unique audio ≈
   77 Whisper-hours at 7 passes, plus Demucs. The negative arm adds 45.
3. **`comp06030` "Ragam Thanam Pallavi"** is a section name the live matcher can
   return as a composition and is **not** on
   `data/registry_junk_blocklist.json`. Flagged, not self-adjudicated.
4. Remaining `review:True` flags in the wild-truth manifest (bhajare, Kamakshi
   Ni, Ranga Baro, alapana1/2), the junk-blocklist review rows, and **the
   commit** — nothing in this session or the last is committed.

---

## 8. Environment facts worth not rediscovering

- `venv_train` py3.11. **ffmpeg 8.1.2 is installed** at
  `/opt/homebrew/bin/ffmpeg` (the "no local ffmpeg" line in `ARCHITECTURE.md` is
  stale).
- `--cache-v2` is keyed by **`audio_sha256`**, not filename (`identify_v2`,
  ~L804). The `path.name` collision hazard is in the **legacy** `transcribe()`
  path (~L619) only.
- Window filenames deliberately contain no `__`, so `identify_clip.py` skips
  truth-matching entirely and the scorer joins against the sidecar instead.
- `data/raga_aliases.json` is the raga vocabulary: 684 aliases → 101
  canonicals, with junk keys mapping to null. Never trust registry `ragas`
  metadata without it.
- Scoreboard commands and standing numbers are unchanged; see
  `HANDOFF_SESSION_0725.md` §4.
