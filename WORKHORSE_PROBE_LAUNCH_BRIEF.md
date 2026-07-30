# Workhorse brief — freeze the gate, cut the recall arm, build the Colab runner

Date: 2026-07-29. For the **Opus 5 workhorse**. Follows
`WORKHORSE_NEGATIVE_ARM_REPAIR_BRIEF.md`, which you executed cleanly — T1-T7 all
verified (`identify_clip.py` byte-unchanged, 57 tests green, complement sweep
tiles [0,300) exactly).

**No GPU has been spent. Nothing is committed.** Do not commit, do not push, do
not run the GPU. Respond to Deepti in caveman style; docs and `AGENT_LOG.md` in
normal prose.

---

## 0. What Deepti decided on 2026-07-29 — all three are frozen

1. **Gate: rule A, source-specific.** SAFE requires the exact one-sided 95%
   upper bound below +15pp for the pooled gating stratum **and** for every
   source with n ≥ 20. Operationally: zero new bluffs in free-form (n=25) and
   zero in opening (n=20). `unidentified` (n=4) reports without gating.
2. **`neg030` stays `sahitya`.** Not a definitional edge case after all — her
   note *"has swara in it"* meant swarakalpana, which alternates solfège with
   the composition's sahitya line, call and response. The label was right and
   **the sheet's definition was wrong**. Recorded in
   `DURATION_PROBE_PREREGISTRATION.md` §6.
3. **Recall arm n = 60.** ~11.0 h unique audio ≈ 77 Whisper-hours at the 7-pass
   config plus Demucs; with the negative arm's 39, **≈116 Whisper-hours total**.

Realized negative arm after sheet 2: **gating n = 49** over 49 clusters
(25 free-form, 20 opening, 4 unidentified), 10 `sung_unidentified`,
9 `in-catalog`, 2 `unknown`. Sheet 2 caught `neg053` and `neg020`, whose singing
lived entirely in the 150s sheet 1 never played — 4% of the single-sweep
stratum was contaminated.

`DURATION_PROBE_PREREGISTRATION.md` §6 and §6b are **already updated and frozen
by the verifier seat** — realized counts, rule A, the corrected power table, the
corrected ~90%-power line, and the swaram definition note. Read them; do not
re-derive or re-litigate them.

---

## L1 — make the scorer apply rule A

Today the scorer computes rule A and prints it beside rule B, with **B applied**
(`WORKHORSE_NEGATIVE_ARM_REPAIR_BRIEF.md` T2, your `report_by_source()`). Flip
it.

- Rule A decides `safety_holds`. The pooled bound stays computed and printed
  immediately beside it, explicitly labelled as reported-not-gating.
- Keep the disagreement flag, but reverse its sense: it now fires when the
  pooled bound would have said SAFE and rule A does not. That is the case the
  gate exists for and it should be impossible to miss in the output.
- The n ≥ 20 threshold is a registered constant, not a magic number — name it
  and cite §6b.
- A source with n ≥ 20 that is **missing entirely** from the results must
  suppress, not silently pass. Add it to `validate_negatives()`.
- Tests: rule A fails on one planted bluff in free-form while pooled says SAFE;
  rule A passes only when both gating sources are b=0; a missing gating source
  suppresses.

Expected on real data: with b=0 everywhere, free-form 11.3pp and opening 13.9pp
both clear, pooled 5.9pp clears, verdict SAFE. One bluff anywhere in either
gating source fails the arm. That bar is intended.

## L2 — cut the recall arm at n=60

```
venv_train/bin/python scripts/duration_probe_cut.py --dry-run --n 271
venv_train/bin/python scripts/duration_probe_cut.py --n 60 --arm anchored
```

Run the dry run first and reconcile it against §1 of the pre-registration
(923 / 505 / **271** / 117 / 30) before cutting. If the pool has drifted, stop
and report — do not cut against a changed pool.

After cutting, extend `scripts/stamp_negative_shas.py` (or add its sibling) to
stamp `audio_sha256` over `data/duration_probe/anchored/` too, so the recall arm
gets the same artifact binding the negative arm now has. The recall validity
gate (§5) should check it exactly as §6b does.

## L3 — the Colab runner

Only after L1 and L2. Requirements, all previously established:

- **Resumable.** Colab sessions time out; `colab_coverhunter_rescore.py` has the
  pattern. Assume it will be interrupted at least once.
- Runs `scripts/build_asr_cache_v2.py` over **both**
  `data/duration_probe/anchored/` and `data/duration_probe/negatives/`, because
  `identify_v2` is read-only and never transcribes on a miss.
- Measured local throughput at `large-v3-turbo`, mix-only 4 passes: 30s window →
  256s wall, 300s window → 1500s wall. Local is infeasible; this is why the run
  is on Colab at all.
- The cache is keyed by `audio_sha256`, so it must be written keyed the same way
  the scorer will read it. Verify a round trip on two clips before scaling.
- It must produce, in one artifact Deepti can hand back, everything the scorer
  needs: `--results`, `--negative-results`, and the cache. State plainly in the
  notebook where each file lands.
- **Deepti runs it.** The permission classifier blocks agent-run deploys. Your
  deliverable is a notebook she can execute, not an executed run.

## L4 — small, unambiguous

- Fix the labeling-sheet template in `build_negative_arm.py` and
  `build_negative_complement.py`: bare solfège with no composition line is
  `no-sahitya`; swarakalpana against a sahitya line is `sahitya`. Tanam stays
  `no-sahitya`. This sheet is done, so the fix is for the next one — but if it
  is not fixed now it will be wrong the next time it is generated.
- Add the swaram correction to the graveyard in `HANDOFF_SESSION_0728.md` §5:
  a listening sheet's category definitions must describe the music as performed,
  not as a taxonomy — bare `swaram` under `no-sahitya` was wrong for exactly the
  reason a musician would catch and an engineer would not.

---

## Still pending Deepti, do not decide

- **Prospective long OOC audio.** The only route to measuring OOC abstention at
  length. `~/sung_tests/fetch_manifest.tsv` retains source URLs and durations,
  so this is reacquisition, not discovery — 23 OOC rows have manifest entries,
  9 with a parseable source duration ≥300s and ~13 whose duration column is
  corrupted by a tab in the title. Re-derive that count with a real parser
  before quoting it.
- **The 28-clip short-OOC sentinel** (n=28: 10.1pp at b=0, 15.9pp at b=1). Must
  be pre-registered as non-gating *before* it is built. It cannot speak to 300s.
- **The commit.** Nothing in this line of work is committed.

## Rules of engagement

- `~/sung_tests --cache-v2` is the only scoreboard. The duration probe is a
  declared exception and graduates nothing on its own.
- Do not re-run `build_negative_arm.py` — it re-draws anchors and ids and would
  destroy both sheets of labels.
- Do not touch `identify_clip.py`, `handoff.md` / `HANDOFF.md`, or
  `data/duration_probe/v1_superseded/`.
- Do not loosen the OOC definition, and do not revert rule A to a pooled gate.
- Log what you did in `AGENT_LOG.md` in normal prose when done.
