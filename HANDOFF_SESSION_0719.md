# HANDOFF_SESSION_0719 — zero-cost synthetic bootstrap + SYNTH baseline

Written 2026-07-19. Audience: incoming agent. Predecessors:
`handoff_vision_and_architecture.md` + `handoff_state_and_progress.md`
(consolidated strategy/state, repo root), HANDOFF_SESSION_0718.md, and the
committed HANDOFF_*.md set. This file covers only what changed this session.

---

## 1. Goal we're working toward

Unchanged: ~60 s wild clip → composition (top-5 UX ok) + raga (honest
confidence) + lyrics/meaning. Interim bar ≥50% top-1 wild; production bar
80–90%. Wild-clip eval (`~/sung_tests`, frozen 63) is the ONLY scoreboard.

**Session constraint (new, ~30 days from 2026-07-18): zero cost.** No paid
APIs, no billing, no live user uploads expected. Anything billed is staged
but gated — `CARNATIFY_BILLING_OK=1` env var, set only by Deepti. See memory
`zero-cost-pivot-0718`.

## 2. Current state of the code

`main @ 2e611ea` (local, NOT pushed — pushes are Deepti-run), clean tree
except pre-existing untracked leftovers (carnatic_varnam_1.1*,
data/cnn_extra_audio/, data/whisper_transcripts_fw_int8.json, the two
handoff_*.md consolidated docs) plus new untracked `data/synth_control/`
(10 clean control crops, disposable) and mutated committed transcript cache
(`data/whisper_transcripts_turbo.json` grew ~90 synth/control entries during
eval — decide: commit or strip before next real-eval commit).

New in 2e611ea:

- **`augment_wild.py`** — synthetic clip generator from
  `data/concert_audio/<raga>/<title>[_rN].mp3` (1,238 files, 1,102 comps,
  68 with 2–6 renditions). Chain: 20–60 s crop, ±6 st pitch, 0.8–1.25x
  stretch, synthetic reverb, pink noise 8–25 dB, phone bandpass + resample +
  mu-law (NO ffmpeg on machine → no true codec re-encode). Outputs:
  `data/synth_suite/` (80 clips, `<title>__<raga>.wav`, Rāgamālika→NA) and
  `data/synth_train/` (500 clips + manifest.jsonl with per-clip params).
  Audio gitignored, manifests committed.
- **`generate_meanings_batch.py`** — staged Claude Haiku 4.5 Message
  Batches pipeline (runs in `venv`, py3.14, anthropic 0.112.0 — NOT
  venv_train). Stages: import-karnatik / build (both zero-cost, ALREADY
  RUN) / submit (gated) / status / fetch. Results of the free stages:
  272 human meanings + 666 sahitya texts imported from
  data/karnatik_lyrics.json into lyrics.db (meanings 8→280 titles; new
  `meaning_source` column); 2,972 requests staged in
  `data/meanings_batch/requests.json`, offline estimate **~$3.54**.
- **`prepare_coverhunter_data.py`** — CSI training dataset builder (RUN):
  `data/coverhunter_data/` = 704 clips (500 augmented + 204 real
  renditions), 16 kHz wav (gitignored), full/train/val.jsonl +
  song_id_map.json (committed). Train/val disjoint by composition, val has
  28 songs with ≥2 versions. 24 clips run 61–75 s (stretch overran crop;
  augment_wild now trims to 60 s — data left as-is, trainers chunk).

Matcher/pipeline (`identify_clip.py`), registry, web stack: untouched.

## 3. Files actively being edited

None mid-edit. All three new scripts committed and working. Open decision
(Deepti's) drives the next edit, see §5.

## 4. Tried and failed / negative results (this session)

1. **SYNTH suite under `--fast` is NOT a composition-robustness probe.**
   80-clip run: comp 0/80 top-1 AND top-5, 72/80 ASR-dead. Control run of
   10 CLEAN un-augmented crops of the same sources: ALSO 0/10, 10/10
   ASR-dead. So the zero is the floor of `--fast` (no demucs) on
   accompanied concert audio, not augmentation damage. **Demucs stems are
   load-bearing** — whisper-turbo-CPU on unseparated Carnatic mixes ≈ 0
   regardless of degradation. Don't rerun --fast expecting different.
2. **Raga augmentation damage isolated (real finding):** clean crops 6/10
   raga top-1 vs augmented 12/77 (~60%→~16%). Pitch shift + codec destroys
   the tonic/TDMS path, quantified.
3. **Augmented audio defeats the usability gates:** clean junk transcripts
   were gated (0 predictions); augmented audio pushed whisper into fluent
   hallucination — 8 predictions, all wrong compositions, 7 at high/medium
   confidence (SCORE line "backfill 0/7"). Same family as graveyard #6
   (prompted-whisper hallucination). Reinforces: score calibration >
   more gates.
4. **13/80 suite titles are unmatchable by name** (archive junk like
   "HMV P 5866...", track-number prefixes) — truth ceiling ≈ 67/80. Any
   future suite scoring must account for this.
5. Small bugs found+fixed in augment_wild: casefold title grouping
   (1,118→1,102 comps), Rāgamālika as raga truth (→NA), time-stretch
   pushing clips past 60 s.
6. Ops re-confirmations: zsh eats `===` in compound commands (quote it);
   mpg123 resync warnings on damaged mp3s are benign; closing the MacBook
   lid SUSPENDS background evals (resumes on wake — tell Deepti to
   `caffeinate -i` for overnight runs).
7. karnatik→lyrics.db title match rate is modest (~940/3,252 via
   normalized-exact); fuzzy matching would ground more of the 2,580
   title-only batch prompts. Improvable, not blocking.

SCORE blocks verbatim (stress signal ONLY — same-corpus, green-lights
nothing, never merged into ~/sung_tests):

```
SYNTH 80 (augmented, --fast): comp top-1 0/80 top-5 0/80 | raga 12/77 top-3 15/77 | backfill 0/7
CONTROL 10 (clean,   --fast): comp top-1 0/10 top-5 0/10 | raga 6/10  top-3 6/10
```

## 5. Next step

**Blocked on one Deepti decision (asked, unanswered):**

- **Option A:** rerun 80-clip SYNTH suite through FULL pipeline (stems) —
  ~8–13 h CPU overnight, lid open/caffeinate. Yields true augmentation
  delta for composition ID.
- **Option B (recommended by this session):** skip A locally; fold the
  suite into the future Colab/GPU eval where demucs costs minutes, and
  spend local cycles growing the REAL wild set via `fetch_sung_tests.sh`.

Independent of A/B, the queue from handoff_state_and_progress.md §5 stands,
zero-cost items first:

1. Deploy staged backend + confirm-button frontend (flywheel) — Deepti
   sign-off + Deepti-run deploy; free.
2. Grow real wild eval set 63→200+ (fetch script + Deepti recordings) —
   free, and unlike the synth suite it moves the actual scoreboard.
3. CoverHunter training on Colab Pro using `data/coverhunter_data/`
   (704 clips ready; adapt full.jsonl to the repo's exact data_process
   schema after cloning it on Colab).
4. Score calibration / margin analysis — now doubly motivated by failure
   #3 above; can be developed free against existing eval logs.
5. When billing approved: `CARNATIFY_BILLING_OK=1 venv/bin/python
   generate_meanings_batch.py submit` (~$3.54), then `status`/`fetch`,
   then Deepti verification queue.

Pending human checks carried over: Kurai Onrum Illai + Paluke
Bangaramayena ear-checks; raga model swap sign-off; push of 2e611ea.
