# HANDOFF_SESSION_0719B — wild set 63→106 + CoverHunter on Colab (live)

Written 2026-07-19/20, second session of the day. Audience: incoming agent.
Predecessors, read in this order if cold: HANDOFF_SESSION_0719.md (same
day, part 1 — synth baseline negative results), HANDOFF_SESSION_0718.md,
handoff_vision_and_architecture.md + handoff_state_and_progress.md (repo
root, untracked), HANDOFF_CLIP_ID.md §5 graveyard + §8 gotchas. This file
covers only what changed in this session.

---

## 1. Goal we're working toward

Unchanged: ~60 s wild clip → composition (top-5 UX ok) + raga (honest
confidence) + lyrics/meaning. Interim bar ≥50% top-1 wild; production bar
80–90%. The ONLY scoreboard is the real wild set in `~/sung_tests`.

Zero-cost constraint stands (~30 days from 2026-07-18): no paid APIs, no
billing. **Deepti explicitly DECLINED authorizing the Haiku meanings batch
this session** — the $3.54 submit stays staged and gated on
`CARNATIFY_BILLING_OK=1`; do not re-ask soon.

This session's strategic call (Deepti, Option B): no local 13-h full-stems
synth rerun; local cycles go to growing the real wild set, GPU work goes
to Colab. Both executed — see below.

## 2. Current state of the code

`main @ f7239cd`, **4 commits ahead of origin, NOT pushed** (pushes are
Deepti-run): 2e611ea (synth bootstrap infra), 221cf60, bb3522c, f7239cd.

New commits this session:

- **221cf60 — fetch_sung_tests.sh hardened + wild set entries.**
  - `validate_clip()`: full ffmpeg decode integrity check; ≥58 s duration
    floor (EOF-truncated cuts discarded); volumedetect mean > −45 dB;
    silencedetect (−35 dB / 3 s windows) total ≤ 20 s. Rejects go to
    `~/sung_tests_rejected/` (OUTSIDE the scoreboard dir on purpose) and
    are logged `REJECTED: <reason>` in fetch_manifest.tsv.
  - Diacritic-insensitive title dedupe (`norm_title`/`dup_of`, iconv
    ASCII//TRANSLIT + lowercase + strip non-alnum, compares the
    `<title>__` part of every existing .m4a/.mp3). Without it a rerun
    re-downloads the manually-added mp3 clips under ASCII m4a names and
    duplicates compositions in the scoreboard — it caught 11 such dups
    live. Note: macOS iconv DROPS some chars (ḍ, Ā) instead of folding,
    but both compare sides pass through the same function so it stays
    deterministic; titles in the set are ASCII anyway.
  - +19 new IN entries via ytsearch1, titles spelled from
    data/catalog_titles.txt. Deliberately SKIPPED `manavyAla kimpavadEmi`:
    catalog says raga Khamas, real kriti family is Nalinakanti —
    registry-junk pattern (see memory registry-junk-entries). `Shobillu`
    respelled `sObillu` so dedupe matches the two existing clips.
  - HANDOFF_SESSION_0719.md committed here too.
- **bb3522c — prepare_coverhunter_data.py UNTRACKED** (Deepti decision:
  Colab GPU workflow lives outside main codebase). File still on disk and
  in history at 2e611ea. Gitignored.
- **f7239cd — gitignore /coverhunter_data.zip + /colab_coverhunter.py.**

Untracked-but-important on disk (do not delete):

- `colab_coverhunter.py` — THE Colab runner, heavily debugged this
  session (see §4). Gitignored by Deepti's out-of-codebase policy; it is
  the only copy besides whatever is uploaded in the Colab session.
- `coverhunter_data.zip` (890 MB, repo root) — the 704-clip CSI dataset
  zipped for Drive; already uploaded to Drive, local copy disposable.
- `prepare_coverhunter_data.py` — untracked by decision, keep.
- `HANDOFF_VERFIER.md` — appeared mid-session, NOT created by this agent,
  never inspected. Look before committing anything blanket.
- Still-undecided: `data/whisper_transcripts_turbo.json` mutated by the
  0719a synth evals (~90 synth/control entries). Commit-or-strip decision
  still open before the next real-eval commit.
- Pre-existing leftovers: carnatic_varnam_1.1*, data/cnn_extra_audio/,
  data/whisper_transcripts_fw_int8.json, the two consolidated handoff
  docs, data/synth_control/ (now gitignored).

**Wild set: 63 → 106 clips** (78 in-catalog + 28 OOC) after the hardened
fetch run: 43 new clips saved, all passed validation (0 rejects), 11 dup
skips, 2 fetch failures (meenakshi memudam dead watch URL; Kadhal Rojave
search). Caveats: new clips are cut at the 35%-of-duration point, NOT
ear-checked; `rAma nannu brOvara` landed on Mandolin U. Shrinivas
(instrumental — ASR path dead by design, raga-only value; candidate for
replacement); `bhAvayAmi raghurAmam` is Ragamalika truth. **The frozen-63
scoreboard numbers (8/36 top-1, OOC 23/27) are NOT comparable to any
future 106-clip run — a re-baseline eval is required before the next
fix-measure cycle.** Memory wild-test-set-status updated accordingly.

## 3. Files actively being edited

None mid-edit locally. `colab_coverhunter.py` is stable as of the last
patch (repo-bug auto-fix baked in) but is the live experiment — expect to
edit it again when training finishes or dies in a new way.

## 4. Everything tried that failed (this session)

Local:

1. (Inherited context, do not redo) `--fast` synth suite scores measure
   the no-stems floor, not augmentation damage — demucs is load-bearing.
   See HANDOFF_SESSION_0719.md §4.

Colab / CoverHunter (github.com/Liu-Feng-deeplearning/CoverHunter,
unmaintained) — chronological failure log, each now auto-handled by
`colab_coverhunter.py`:

2. **Config-patch miss → FileNotFoundError data/covers80/full.txt.**
   First config patch set only train_path/dev_path/test_path. Real keys:
   `train_sample_path` (loaded at startup) and the `covers80:` block
   (query_path/ref_path = in-training eval set) — every covers80 path
   must be repointed; `test_path` is not even a real key. Also
   `chunk_s` must track `chunk_frame`: chunk_s = chunk_frame[0] × 0.04
   hop × mean_size(3) → [900,675,450] ⇒ 108.
3. **typeguard 4.x (Colab default) rejects the repo's
   `ConformerEncoder(global_cmvn=None)`** (written for typeguard 2.x).
   Fix: `pip install typeguard==2.13.3`.
4. **utt-based train/dev split silently produced an EMPTY dev set**
   ("Input dataset items: 0" in the loader log) — tools.extract_csi_features
   REWRITES utt ids. Split must key on the `song` field, which passes
   through extraction intact. Same val song list ⇒ still
   composition-disjoint. Script now asserts dev > 0.
5. **Repo bug, the big one: `tools/train.py` unpacks 2 values from
   `eval_for_map_with_feat(...)` which returns 3 (map, hit_rate, rank1)
   → ValueError at the END of every first eval epoch.** Every "mystery
   crash" traced back to this: training never survived past epoch 1, so
   all mAP numbers to date are 1-epoch noise. Script now patches the
   call sites right after clone (adds `, _rank1`).
6. **Colab VM death wipes /content** — lost a ~2 h CQT extraction and the
   original train log. Everything now Drive-cached:
   `MyDrive/carnatify/{coverhunter_data.zip, coverhunter_feat.zip,
   coverhunter_ckpt/, train.log}`. Feature restore ≈ 1 min.
7. **Terminal watch-loop with a typo'd cp path silently synced nothing**
   (`.../carnatify/content/drive/...`, missing space) — and separately,
   grepping a dead process's log showed the same mAP line for an hour
   ("watching a corpse"). Babysitting is now INSIDE the script:
   subprocess train, 10-min ckpt sync + fresh mAP print, last-40-lines
   dump with returncode decode (−9 ⇒ OOM killer hint) on death.
8. **Buffered subprocess stdout lost on abrupt death** — one run died
   leaving zero output after the run marker; likely the same unpack crash
   (or OOM) with its output stuck in the stdio buffer. Train now runs
   `python -u`.
9. **`unzip` without `-o` died on the overwrite prompt** (step 3 pre-writes
   dataset.txt into the same dir the feature cache restores into; no
   stdin in notebook). Both unzips now `-q -o`.
10. **Reconnected runtime came up CPU-only** → `assert
    torch.cuda.is_available()`. Every new session: Runtime > Change
    runtime type > T4 (High-RAM if offered), verify `!nvidia-smi`.
    Runtime switch = new VM = re-upload colab_coverhunter.py.
11. **My own resume bug:** script didn't restore `pt_model/` from Drive,
    so each rerun restarted training from scratch (mAP kept "resetting"
    to ~0.05). Now restores before training.

## 5. Next step

**Immediate (blocked on Colab run in flight):** training relaunched with
ALL of §4 fixed — first run expected to survive past epoch 1. Deepti
watches the 10-min sync lines.

- mAP climbing across evals → let it run to plateau (~5 flat evals),
  interrupt, checkpoints auto-synced to Drive.
- Death → the script prints the true traceback now; debug from there.
- Reference points: 1-epoch evals scored mAP 0.047–0.078, hit@1
  0.08–0.14 vs ~0.036 chance (28 multi-version dev songs) — above chance
  at epoch 1. Judgment bar from 0719a discussion: mAP 0.3–0.5 from these
  704 mostly-synthetic clips justifies scaling the synth pipeline hard.
  covers80's ~0.85 is NOT the anchor (way more real data).

**After training (in order):**

1. Eval the trained embedding as a MATCHER: embed the 106 wild clips +
   catalog renditions, nearest-neighbor by song, compare against the
   DSP/DTW matcher on the same clips. This is the actual go/no-go for
   the CoverHunter path. `tools.eval_testset <model_dir> <query> <ref>`;
   checkpoints in Drive coverhunter_ckpt/carnatify/pt_model.
2. Re-baseline the 106-clip wild set with the CURRENT local pipeline
   (`venv_train/bin/python identify_clip.py ~/sung_tests`, ~minutes with
   --no-raga, ~1 h with raga) — required before any new fix-measure
   cycle, and independent of Colab.
3. Standing zero-cost queue: deploy staged backend + confirm-button
   frontend (Deepti sign-off + Deepti-run deploy); score calibration /
   margin analysis against existing eval logs (motivated by the
   hallucination-defeats-gates finding); karnatik fuzzy title matching
   to ground more batch prompts.
4. Billing NOT authorized — do not submit the meanings batch.

**Carried-over pending Deepti items:** push the 4 commits; Kurai Onrum +
Paluke Bangaramayena ear-checks; raga model swap sign-off; transcript
cache commit-or-strip; inspect mystery HANDOFF_VERFIER.md; consider
replacing the instrumental rAma nannu clip.

Ops reminders that bit again this session: closing the MacBook lid
suspends background work (`caffeinate -i`); Colab tab must stay open
unless Background Execution is on; zsh eats `===` unquoted.
