# HANDOFF_SESSION_0731 — four audits, three reversals, and the first real field measurement running

Written 2026-07-31 for **whoever holds the verifier seat next — that is you.**
Supersedes `HANDOFF_SESSION_0730.md`, which is still correct on its §5
(graveyard additions) and §8 (environment facts).

**Why this filename and not `handoff.md`:** on this case-insensitive filesystem
`handoff.md` and `HANDOFF.md` are one file, it belongs to the Claude *workhorse*
seat, and it is committed with the workhorse's own content. Overwriting it would
destroy a committed record. Deepti asked for a verifier handoff capturing the
five sections below; this file is it, and §2 of `handoff.md` has been amended in
place rather than replaced.

Respond to Deepti in **caveman style** (standing preference). Write docs,
commits and `AGENT_LOG.md` in normal prose.

**Read order:** this file → `AGENT_LOG.md` entries dated 2026-07-30 and 07-31 →
the four audit docs in §3 → `HANDOFF_CLIP_ID.md` §5 (the graveyard) →
`HANDOFF_SESSION_0730.md` §5, §8.

---

## 1. The goal

An app that identifies what is being performed in a live Carnatic concert and
explains it. Deepti is a Carnatic musician; the framing since 2026-07-25 is a
**concert companion** — the listener is present for a 10-30 minute item, so the
30-second Shazam contract was inherited, never required.

**Demand is no longer zero.** Jon — the one named real user, a Western listener
with no Carnatic exposure — was confused at a concert and, **unprompted, reached
for an AI assistant to identify the piece. It failed**, mostly with refusals
("I cannot help with this request"). He asked **two** questions:

1. *what is the song being sung* — composition ID, and every door there is shut;
2. *what does the melody mean* — raga character plus sahitya meaning, which
   needs **no ASR, no CSI, no Qmax**, and which the repo has never attempted.

The refusal failure mode narrows the moat to **audio → symbol**; the explanation
layer on top is commodity, which is a cost advantage. Every handoff before this
one says "demand evidence is zero" — **that line is stale.**

## 2. State: the composition doors are shut, and the raga pessimism was wrong

| door | verdict | evidence |
|---|---|---|
| lyrics-ASR precision gate | no operating point at any threshold (≤31%) | 2026-07-23 |
| sung-Carnatic ASR fine-tune | strictly worse, 8/78 → 0-1/78 | 2026-07-24 |
| melodic CSI (CoverHunter) | NO-GO, source-disjoint mAP 0.113 vs 0.031 chance | 2026-07-24 |
| duration (lyrics channel) | KILL, top-5 5.1% @30s → 1.7% @300s | 2026-07-30 |
| **Qmax composition "60-67%"** | **RETRACTED — 9.5% source-disjoint** | this session |
| **raga "72.8% leak-free"** | **HELD — 72.2% source-disjoint** | this session |
| **"raga dies on short clips"** | **mostly false — 60.4% @60s, 52.5% @30s** | this session |
| **"raga dies on wild audio"** | **never measured on audio it could answer** | this session |

Four numbers were audited in two days. **One fell, three moved the other way.**
The composition side is genuinely closed. The raga pessimism was built on
figures that had never been checked, and every one of them has now moved toward
"fine".

**What still works:** OOC rejection, 24/28 on the wild set — the pipeline's
strongest behaviour. Full-recording raga, now audited.

## 3. Current state of the code

Branch **`probe/duration-and-negative-arm`**, **23 commits, NOT PUSHED**.
`identify_clip.py` has zero diff vs `main` — nothing in this series touched the
production path. `103 passed, 1 xfailed` on the three runnable test files.

Four audits, each with its preregistration committed **before** the scoring
harness and before any fold was scored:

| doc | what it established |
|---|---|
| `data/QMAX_CONTAMINATION_AUDIT.md` | 60.0% → **9.5%** source-disjoint; 34 of 36 top-1 hits were byte-identical copies of the query at the 0.036 Serra09 identity floor. Internal 66.7% is a separate, uncontaminated, **unreproducible** n=30 claim. Corpus cannot support a cross-artist claim at all — 13 of 1,011 works have ≥2 known distinct artists. |
| `data/RAGA_CONTAMINATION_AUDIT.md` | 72.8/84.7 reproduces **exactly** (377/518, 439/518) and holds at **72.2%/84.0%** source-disjoint while independent units collapse 518 → 155. The same-raga-same-upload clusters the brief predicted would carry the damage cost **1.2pp, three tracks**. Vasanta is the one weak class (35.7%). |
| `data/RAGA_DURATION_CURVE.md` | 52.5% @30s → 60.4% @60s → 63.8% @120s → 68.8% @300s → 71.0% @600s → 72.2% full. Knee bracketed in (120s, 300s]. Top-3 decays far more gently: 84.0% → 77.1% @60s. |
| `data/RAGA_DOMAIN_DECOMPOSITION.md` | Field-realistic degradation costs **7.5pp, not 44**. Phone chain +0.4pp, room +2.1pp, pink noise +2.7pp — each CI touching or crossing zero. Pitch shift alone +10.6pp and time stretch alone +11.0pp, **each worse than all three field components combined**. The 2×2 kills the tonic hypothesis: contour beats tonic 3:1 in the field cell, 5:1 in the worst. §9: only **29 of 106** wild clips name a raga the model can emit, so P(0/10) ≈ 14%. |

Supporting artifacts: `scripts/qmax_*`, `scripts/raga_audit_*`,
`scripts/raga_duration_*`, `scripts/raga_domain_*`,
`data/qmax_audit/provenance.json` (track → archive item → artist, 1,232 of 1,232
resolved).

Docs corrected in `f2ec130`: `ARCHITECTURE.md` (Qmax verdict flipped to dead),
`HANDOFF_CLIP_ID.md`, `HANDOFF_SESSION_0725.md`, `handoff.md`, a staleness
banner on `CODEX_DURATION_PROBE_BRIEF.md`, and the mislabelled `cv_note` in
`train_raga_v3_tdms.py` / `models/raga_v3_meta.json` (72.8/84.7 is a **TDMS-only**
score that was stapled to the *fused* exported model, which is 75.7/84.2).

## 4. Files being edited right now

**A workhorse is running** on `WORKHORSE_RAGA_WILD_BRIEF.md`. It will create
`data/raga_wild/PREREGISTRATION.md`, `scripts/raga_wild_*.py`,
`data/RAGA_WILD_MEASUREMENT.md`, and append to `AGENT_LOG.md`. **Do not edit
those files or `AGENT_LOG.md` until it lands.**

`data/raga_wild/FROZEN_CLIPS.json` is **frozen and committed** (`f67ef98`) with
per-clip sha256, written before any prediction existed. Selection is closed.

Nothing else is mid-edit. Deepti also works in this repo from a **separate
terminal** — prefer targeted `git add <path>`, never `git add -A`.

## 5. What was tried and failed

`HANDOFF_CLIP_ID.md` §5 is the master graveyard; `HANDOFF_SESSION_0730.md` §5
holds the duration-probe additions. New this session, including my own errors:

1. **"The 72.8 CV harness was never committed."** I asserted this in
   `WORKHORSE_RAGA_AUDIT_BRIEF.md` on the strength of
   `git log --all -S"72.8" -- '*.py'`. **Wrong.** That search finds files which
   *hardcode* a literal; the harness *computes* it.
   `scratch_archive_0711/raga_final_eval.py` (`c1fca59`) is the harness and
   reproduces both tiers and both metrics exactly. It appeared in my own grep
   output and I did not follow it. **`-S` over source is a test for a literal,
   not for a capability.**
2. **"`phone_mic`'s 120-350 Hz high-pass will strip the fundamental and leave
   melodia tracking nothing."** Registered in advance in
   `WORKHORSE_RAGA_DOMAIN_BRIEF.md`. **Refuted** — zero no-contour failures in
   all 517 windows of all eight cells. The failure is wrong answers on present
   input. Good that it was written down first.
3. **The shruti-from-the-listener idea.** I proposed it as the cheap fix if the
   tonic turned out to be the problem. The 2×2 says perfect tonic recovery buys
   **2.2pp** in the field cell. **Do not fund tonic-estimation work.** Most
   tonic error is pre-existing in the *clean* corpus (17.4% outside 25 cents),
   not induced by degradation.
4. **`augment_wild.py` as a domain simulator.** Its ±6 semitone pitch shift and
   0.8-1.25× time stretch simulate nothing that happens to a phone recording,
   and they dominate the damage. Any future robustness claim built on the `all`
   condition is measuring an artifact. **Use `field_all` (noise + reverb +
   phone) instead.**
5. **Quoting "60-67% top-1 (Qmax)" as one range.** Two different corpora,
   channels and catalog sizes welded into one number; the external half was
   contamination and the internal half is unreproducible.
6. **Assuming a rendition count is a recording count.** 65 titles with 2+
   renditions is really 87 titles with 2+ *distinct recordings*; 367 tracks in
   multi-track groups collapse to 261. The rendition corpus is **confirmed
   do-not-fund** — 73 usable works, 13 with verifiable artist diversity.
7. **Two workhorses died on session limits mid-run.** Both were recoverable
   because the briefs demanded partial results on disk and prereg-before-score.
   The verifier seat finished both from their own committed scripts. **Keep
   demanding both.**

## 6. The next step

1. **Read the wild measurement when it lands** and verify it independently —
   re-derive at least one headline figure with your own code, as was done for
   every audit in this series. Then apply the fixed table in
   `WORKHORSE_RAGA_WILD_BRIEF.md`: ≥40% means the simulation was valid and raga
   survives the field; 20-40% means an unmodelled field factor, look at the
   demucs arm first; <20% means raga joins the closed doors.
2. **Get Deepti to read the 29 label rows.** The wild raga labels have never
   been audited and some clips were auto-fetched. It is 29 lines and it converts
   the result from provisional to solid. **This is the single highest
   value-per-minute action available.**
3. **If raga survives: build the thing Jon asked for.** Raga name + raga
   character + sahitya meaning, on long-form audio, with OOC rejection as the
   guard against lying. The explanation layer is text and commodity. **Do not
   start with composition ID.**
4. **Catalog restriction** — still the one untested cheap lever on the lyrics
   side (load-time restriction in `load_targets` plus a re-score). Deprioritized
   twice, still not in the graveyard, honest expectation is precision up and
   recall flat.
5. **Push the branch.** 23 commits sitting local. Deepti's call.

## 7. Pending Deepti

1. **Push the branch / open a PR** — 23 commits, none pushed.
2. **Verify the 29 wild raga labels** (see §6.2).
3. `asr_cache_fullhistory/` is local-only and gitignored; if deleted,
   `DEVICE_MAP.md` becomes unfalsifiable. Back it up outside the repo.
4. Wiring the registry junk blocklist (a load-time merge in `load_targets`).
5. **Do NOT fund:** the rendition corpus, tonic-estimation work, prospective
   long OOC audio, or the 28-clip short-OOC sentinel.

## 8. Discipline that produced these results — keep it

- **Preregister, and commit the prereg as its own commit before the scoring
  harness exists.** Every audit here did this. The Qmax audit's ordering rests
  on file mtimes because it was committed late; that is the weakest link in the
  set.
- **Gate on reproducing the historical number first.** The raga audit returned
  the same *integer counts* (377/518, 439/518), so every delta was measured off
  the original measurement rather than an approximation.
- **Fix the interpretation table in the brief, before the number exists.**
- **Freeze the tunable that could launder the result** and say in the brief that
  it is forbidden — the raga tier, the clip list, the augmentation parameters.
- **Write predictions down so they can be refuted.** Two of mine were, cleanly.
- **Separate "produced no output" from "produced a wrong output"** and never sum
  them into one percentage.
- **The verifier does not take the workhorse at face value.** Re-derive a
  headline number with your own code every time. It has caught a wrong premise
  of mine once already.

## 9. Environment facts worth not rediscovering

- `venv_train` py3.11 (demucs, essentia, whisper, rapidfuzz, **pytest**);
  `venv` py3.14 (sklearn, librosa, mirdata, **no pytest**). essentia must run in
  `venv_train`, fork not spawn.
- Never run bare `pytest tests/` — six legacy files import a `carnatify` package
  that does not exist and fail at collection. Run
  `tests/test_clip_policy.py tests/test_registry_junk.py tests/test_negative_arm.py`.
- **ffmpeg 8.1.2 IS installed** at `/opt/homebrew/bin/ffmpeg`. The "no local
  ffmpeg" lines in `ARCHITECTURE.md`, `HANDOFF_CLIP_ID.md` §3 and
  `augment_wild.py:21` are stale.
- `handoff.md` and `HANDOFF.md` are **one file** on this filesystem; git tracks
  both paths, so committing one leaves the other showing as modified.
- `data/raga_aliases.json`: 684 aliases → 101 canonicals, junk keys → null.
  Never trust registry `ragas` metadata without it.
- Melodia runs ~13× realtime; the domain cells took ~400 s each at 5 workers,
  6× faster than the single-threaded estimate.
- Zsh eats `"` inside `git commit -m` when the message contains quoted phrases —
  use `git commit -F -` with a heredoc.
