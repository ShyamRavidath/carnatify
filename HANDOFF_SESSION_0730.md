# HANDOFF_SESSION_0730 — duration probe scored (KILL), everything committed, four doors closed

Written 2026-07-30 for **whoever holds the verifier/orchestrator seat next**.
Supersedes `HANDOFF_SESSION_0729.md` in full. `HANDOFF_SESSION_0728.md` is still
correct on §5 (graveyard) and §8-9 (roster, discipline).

Written at Deepti's request as the verifier handoff. It is deliberately **not**
`handoff.md` / `HANDOFF.md` — on this case-insensitive filesystem those are one
file, they belong to the Claude workhorse seat, and that file is now committed
with the workhorse's own §2.6. Overwriting it would destroy a committed record.

Respond to Deepti in **caveman style** (standing preference); write docs,
commits and `AGENT_LOG.md` entries in normal prose.

**Read order:** this file → `AGENT_LOG.md` entries dated 2026-07-30 →
`DURATION_PROBE_PREREGISTRATION.md` §5b/§5b.1/§6b → `HANDOFF_CLIP_ID.md` §5
(the graveyard — the most important file in the repo) → `HANDOFF_SESSION_0728.md`
§§5, 8-9.

---

## 1. The goal

An app that identifies a Carnatic **composition** from a short clip of a live
performance, and reports its raga. Deepti is a Carnatic musician; the honest
product framing as of 2026-07-25 is a **concert companion** — the listener is
present for a 10-30 minute item, so the 30-second contract was inherited from
Shazam and was never a requirement.

One named real user: **Jon**, a Western listener with zero exposure. **Demand
evidence is zero** and has been recorded as zero since 2026-07-25. That has not
changed and is now arguably the binding constraint.

## 2. State: four doors closed, all measured

| door | verdict | evidence |
|---|---|---|
| lyrics-ASR precision gate | no operating point at any threshold (≤31%) | `scripts/precision_coverage_curve.py`, 2026-07-23 |
| sung-Carnatic ASR fine-tune | **strictly worse** — 8/78 → 0-1/78, val WER >100%, memorised ~26 pallavis | `colab_asr_finetune.py`, 2026-07-24 |
| melodic CSI (CoverHunter) | **NO-GO** — source-disjoint mAP 0.113 vs 0.031 chance; headline 0.327 was two-thirds contamination | 2026-07-24 |
| **duration** | **KILL** — top-5 5.1% @30s → 1.7% @300s, delta −3.4pp, 90% CI [−8.9, **+1.8**] | this session |

The duration KILL is the strongest-evidenced result in the repo: pre-registered,
three red-team passes, scored exactly once.

**The negative arm returned NOT ESTABLISHED, and that is underpower, not a
rise** — b=4, r=4, net exactly +0.0pp on n=49. Never quote it as "longer
listening bluffs more". Design number for any future negative arm: clearing
+15pp needs n≥30 at b=1, **n≥40 at b=2**, n≥50 at b=3 — roughly **double** the
realized per-source n of 25 and 20.

**What still works:** OOC rejection (24/28 on the wild set) is the pipeline's
strongest behaviour. Full-recording raga is 72.8% top-1 / 84.7% top-3, grouped
CV, leak-free. Those are real.

## 3. Everything is committed — a first in six sessions

Branch **`probe/duration-and-negative-arm`**, 7 commits, **not pushed**.
`identify_clip.py` has zero diff vs `main`; the probe never touched the
scoreboard path. `103 passed, 1 xfailed`.

~4GB stayed out of history via `.gitignore`: probe wavs (regenerable), the 82
Drive cache revisions (`asr_cache_fullhistory/`, 253MB — **local-only, and the
device map cannot be re-derived without it**), the varnam corpus. The 1.1MB that
cannot be regenerated — sidecars, both labeling sheets, `DEVICE_MAP.md`,
`DEVICE_CALIBRATION.md`, the notebook output — is committed.

## 4. Files being edited

Nothing mid-edit. Two briefs are written and unstarted:

- **`WORKHORSE_QMAX_AUDIT_BRIEF.md`** — the next job, see §6.
- `WORKHORSE_DEVICE_CALIBRATION_BRIEF.md` — complete, kept for audit.

## 5. What was tried and failed — additions from this session

`HANDOFF_CLIP_ID.md` §5 remains the master graveyard. New entries:

1. **Duration as a lever.** Ruled out, not merely undetected. Do not propose
   "just give it more audio" again without new evidence.
2. **A single 50%-duty listening sweep does not establish "no lyrics here".**
   The complement caught singing in 2 of 51 items — 4% contamination — all of it
   inside the 150s the first sweep never played.
3. **A labeling sheet's categories must describe the music as performed.** The
   sheet filed bare `swaram` under `no-sahitya`; in performance swarakalpana
   alternates solfège with the composition's sahitya line. Caught only because
   the musician labelled against the sheet she was reading. **Have the ear
   review the category definitions before the sheet ships.**
4. **A long unattended runner must write provenance incrementally and
   import-check its full inference path in step 0.** `colab_duration_probe.py`
   verified audio hashes before spending GPU but not that `rapidfuzz` imports,
   losing step 5/6 after ~27 GPU-hours — and it writes `run_log.json` last, so
   the crash took the device map with it. The map was only recovered from Drive
   revision history.
5. **Transcripts are device-dependent.** Laptop-CPU vs GPU differs on 7 of 12
   mix passes, several completely. Any multi-session GPU run must keep each
   unit's windows on one device, or exclude the straddlers.
6. **The executed notebook was not the file on disk** (chunks of 5 vs
   `CHUNK = 10`). `colab_duration_probe.py` still needs reconciling with what
   actually ran before it is quoted again.

## 6. THE NEXT STEP

1. **Hand `WORKHORSE_QMAX_AUDIT_BRIEF.md` to the workhorse.** The 60-67%
   full-recording Qmax number is the last surviving positive result and the
   foundation of the input-contract thesis, and it has never had the
   source-disjoint audit that took CoverHunter from 0.327 to 0.113. Read-only,
   no GPU, interpretation fixed in advance in the brief.

2. **Then the catalog-restriction experiment — the one untested cheap lever.**
   Every failure on record was measured against an **open** catalog: 1,118
   distinct titles, 8,688 registry rows. Nobody has ever measured the pipeline
   against a *restricted* repertoire. Both external reviewers independently
   recommended starting at 150-250 compositions, and the broken quantity is
   **precision** (≤31%), which is exactly what a smaller candidate pool should
   move. This is a load-time restriction in `load_targets` plus a re-score on
   `~/sung_tests` — hours, not weeks. It is **not** in the graveyard; the
   registry junk blocklist removed 52 junk rows, which is a different
   experiment. Honest expectation: precision up, recall roughly flat — it cannot
   create signal where the ASR produced none (2 of 8 clips yield no usable
   transcript; 64% of auto-fetched clips are ASR-dead).

3. **The rendition corpus is the real long pole, and must not be funded until
   1-2 report.** The binding data fact: **65 of 1,118 titles have 2+
   renditions** (185 files). Any cross-rendition method — Qmax, CoverHunter, a
   contrastive embedding — needs roughly 150-250 compositions × 8-15 genuine
   renditions. That is a data-acquisition project, and the 3.6x-chance
   CoverHunter signal was not strong enough to fund it on its own.

4. **Demand evidence.** Still zero. Take Jon to a concert and watch without
   helping. It also produces long-form audio as a by-product.

## 7. Pending Deepti

1. **Push the branch / open a PR** — 7 commits sitting local.
2. **`asr_cache_fullhistory/` is local-only and gitignored.** If it is deleted,
   `DEVICE_MAP.md` becomes unfalsifiable. Back it up outside the repo.
3. Wiring the registry junk blocklist (a load-time merge in `load_targets`).
4. **Do NOT fund** prospective long OOC audio or the 28-clip short-OOC sentinel.
   Both existed to shore up a safety arm for a lever now ruled out.

## 8. Environment facts worth not rediscovering

- `venv_train` py3.11 (demucs, essentia, whisper, rapidfuzz); `venv` py3.14
  (sklearn, librosa, mirdata). essentia must run in `venv_train`, fork not spawn.
- **ffmpeg 8.1.2 IS installed** at `/opt/homebrew/bin/ffmpeg`. The "no local
  ffmpeg" line in `ARCHITECTURE.md` and `HANDOFF_CLIP_ID.md` §3 is stale and has
  been inflating the cost of audio-slicing tasks with a needless Colab hop.
- `--cache-v2` is keyed by `audio_sha256`, not filename (`identify_v2`, ~L804).
  The `path.name` collision hazard is in the legacy `transcribe()` path only.
- `data/raga_aliases.json`: 684 aliases → 101 canonicals, junk keys → null.
  Never trust registry `ragas` metadata without it.
- Never run bare `pytest tests/` — six legacy files import a `carnatify`
  package that does not exist and fail at collection. Run
  `tests/test_clip_policy.py tests/test_registry_junk.py tests/test_negative_arm.py`.
