# HANDOFF 2026-07-18: 63-clip baseline frozen, three fixes queued and measurable

Written 2026-07-18 after the 2026-07-17 session. Audience: next agent, whose
task is: **make the queued fixes** (§6), verifying every claim against tool
output before reporting it. Supersedes the eval/clip sections of
`HANDOFF_SESSION_0712.md`; the §5 graveyard + §8 gotchas of
`HANDOFF_CLIP_ID.md` still fully apply. Strategy doc: `BRAINSTORM_COMPANY.md`.

Standing Deepti preferences: caveman response mode (see memory/skill);
free-of-cost infra only; she can validate musically. **Wild-clip eval is the
ONLY scoreboard** — no same-corpus benchmark may green-light anything. The
63-clip set is now FROZEN as baseline; tuning is finally allowed (the old
"don't tune on 10" gate is satisfied), but every change must be re-scored
against it and kept/reverted on evidence.

## 1. The goal

SoundHound-for-Carnatic as a potential company. Clip in → composition
(headline, top-5 UX acceptable) + raga (secondary, honest confidence) +
lyrics/meaning. Target ≥50% top-1 on wild ~60s clips. Registry + feedback
flywheel is the moat; models replaceable. Deploy (staged, §7) follows the
fixes.

## 2. The frozen eval set and baseline scoreboard

`~/sung_tests/` = **63 clips: 36 in-catalog + 27 OOC** (out-of-catalog,
must-abstain, `__OOC` filename suffix). Filename truth:
`<title>__<raga>.<ext>`, optional `__OOC` after raga; raga `NA` = raga truth
unknown (skipped in raga scoring). One `__` separator only.

Baseline (2026-07-17 evening run, CPU, matcher v2, v3 registry @ commit
49c0119 — full output was verified in-session from the eval's own printout):

| metric | result |
|---|---|
| composition top-1 | 8/36 |
| composition top-5 | 13/36 |
| OOC reject | 21/27 (6 bluffs) |
| raga top-1 / top-3 | 9/43 / 12/43 (known-raga clips only) |
| raga via catalog backfill | 6/22 |

Sub-slice that matters: **8 v3-registry-only clips (mostly Kannada
devaranamas): 0/8 top-1, 3/8 top-5** (top-5 hits: Baro Krishnayya, Madhura
Madhura, Varuvai Varuvai). This is the open "was the 4x registry expansion
worth it" question — currently the answer looks like "no", but see fix #1.

Reproduce the scoreboard (all ASR cached → minutes):
`venv_train/bin/python identify_clip.py ~/sung_tests --no-raga`
(drop `--no-raga` for the full raga numbers; loads the 1.1 GB RF, slower).
The script prints per-clip TRUTH lines and a final SCORE block — always
quote that block, never recompute by hand.

## 3. Current state of the code (all committed + pushed, main @ 49c0119)

- `identify_clip.py` — single source of matcher truth. This session added
  OOC eval scoring (in `main()` only): `__OOC` suffix → correct answer is
  abstain (`composition_confidence == 'none'`), answered OOC = bluff; raga
  `NA` → clip excluded from raga denominators. Matcher/identify path
  untouched this session.
- `fetch_sung_tests.sh` — now actually works (see §5 for the three bugs it
  had). `bash fetch_sung_tests.sh OOC` fetches only OOC entries; downloads
  are duration-aware (cut from 35% of video length); every download logs
  video title/URL/window to `~/sung_tests/fetch_manifest.tsv`. Verified
  in-session: 22/24 OOC entries downloaded, all exactly 60.0s, mean volume
  -9 to -27 dB, no ≥5s silences. 2 entries died on YouTube 403 (Margazhi
  Thingal, Kadhal Rojave) — skipped, not worth chasing.
- `data/catalog_titles.txt` — regenerated: 8,688 grep-able lines from the
  v3 registry (was stale 2.2k AND squashed to one line). Grep this BEFORE
  hunting new clips.
- `data/v3_only_titles.txt` — 6,239 compositions present only in the v3
  registry (clip-hunt reference).
- Transcript caches `data/whisper_transcripts_turbo.json` (original) and
  `..._turbo_stems.json` (demucs stem) hold all 63 clips, keyed by filename.
- Registry: `data/composition_registry.json`, 8,688 entries ("v3"). v1
  (2.2k) retrievable via `git show feac4b6:data/composition_registry.json`.

## 4. Files actively being edited

None. Working tree clean for this work, everything pushed. (Untracked
leftovers in repo root — carnatic_varnam zip/dir, `data/cnn_extra_audio/`,
`data/whisper_transcripts_fw_int8.json` — predate this work; leave them.)

## 5. Everything tried that FAILED (this session)

1. **Deepti's first OOC hunt**: 7 of her 10 hand-picked "out-of-catalog"
   clips were actually IN the 8.7k registry (Bho Shambho, Kaddanuvariki,
   Kamakshi Ni, Kurai Onrum, Ma Janaki, Paluke, Sarvam Brahmamayam).
   Root cause: catalog_titles.txt was stale + unreadable. Rule now: grep
   the regenerated file (or the registry JSON) before declaring anything
   OOC.
2. **fetch_sung_tests.sh had never worked** — three stacked bugs, all fixed
   and verified: (a) `mktemp` pre-created the temp file so yt-dlp skipped
   with "has already been downloaded", leaving 0 bytes for ffmpeg; (b)
   macOS `mktemp` doesn't substitute mid-name `XXXXXX` (needs trailing X's)
   so every entry shared one literal temp path; (c) ffmpeg/yt-dlp without
   `-nostdin`/`</dev/null` ate the heredoc feeding the `while read` loop,
   truncating following titles ("Payoji Maine" → "ayoji Maine"). If clips
   ever come out title-truncated again, it's (c).
3. **Single-file eval runs miss the transcript cache**: cache keys are NFD
   (macOS filenames); a shell-typed NFC path silently re-runs ASR
   (`path.name in cache` is naive, `identify_clip.py:358`). Folder runs are
   safe (iterdir returns NFD). Cost us a 10-minute stray ASR run before
   being caught. Don't "fix" by hand-normalizing in one call site; if it
   matters, fold keys at both read and write.
4. **zsh `=word` expansion**: `echo ====` / `echo ===BLUFFS===` inside the
   Bash tool aborts the whole compound command with "=== not found". Quote
   any argument starting with `=`. Bit us twice.
5. **YouTube 403s** on 2 of 24 yt-dlp downloads — transient/entry-specific;
   retried once, still 403, dropped.
6. Historical graveyard (pooling, prompted turbo, faster-whisper-on-ARM,
   vasista22 transformers pipeline, RF tonic voting): `HANDOFF_SESSION_0712.md`
   §5 — do not re-try without new evidence.

## 6. The fixes to make (queued, in payoff order) — THE NEXT AGENT'S TASK

Protocol for each: one change → rerun the 63-clip eval → quote the SCORE
block → keep iff in-catalog top-1 does NOT drop below 8/36 AND the targeted
metric improves. Revert otherwise. Report numbers only from actual eval
output.

**Fix 1 — add Kannada to whisper language lists.** The 0/8 on dasa-kriti
clips has a prime suspect: `_whisper_multi` langs are `(None,'ta','te','hi')`
for original audio and `(None,'ta','te')` for stems
(`identify_clip.py:339-353,388`) — **no `'kn'`**, and 7/8 of those clips are
Kannada. Add `'kn'` to both lists. CRITICAL CACHE DETAIL: the caches store
only the final best text per filename, so cached clips will NOT pick up the
new language — delete the cache entries for the 8 v3-only clips (both cache
files; match keys by filename, mind NFD) and let ASR re-run on them
(~8 clips × few min CPU each, run in background). Re-running the whole set
is unnecessary; other clips' cached transcripts are unaffected by a language
list change. Success = v3-only slice improves above 0/8 top-1 (or the
hypothesis dies — report either way; n=8, so even +2 is signal).

**Fix 2 — hallucination-loop detector.** 4 of 6 OOC bluffs are whisper
loops that satisfy the rep≥2 usability gate: "satish satish satish…"
(Katrin Mozhi), "again and again again…" (Munbe Vaa), "bane bane bane…"
(Maithreem Bhajata), "love you love you…" (Samayaniki). Real sung
repetition is phrase-level and interleaved ("brahmamayam sarvam brahmamayam
briyere sarvam…" — Sarvam Brahmamayam's real transcript, which is a
top-1 HIT — study it in the turbo cache before choosing a threshold).
Discriminator to try first: a run of the SAME token ≥4-5 times consecutively
→ variant unusable (or strip the run and rescore). Implement in
`identify_clip.py` near the usability gate (`identify_clip.py:487-498`),
NOT as stoplist growth. Success = OOC reject ≥25/27 with in-catalog top-1
still ≥8/36. Watch specifically that Sarvam Brahmamayam, sObillu, vAtApi
stay top-1.

**Fix 3 — junk-magnet registry entry.** "pAdi madi nadi" caught two
different garbage transcripts (Brahmam Okate, Katrin Mozhi) at identical
score 1.151. Inspect that entry in `data/composition_registry.json` (and
its lyrics source): if it's a parse artifact (see memory: registry has
address/date rows parsed as compositions), purge it via
`build_composition_registry.py` (fix the builder, not the JSON by hand) —
and while in there, sweep for siblings (entries whose "raga" fails a
raga-vocabulary check, e.g. "Sept 13, 1997"). If it's a real composition,
leave it and note that fix 2 likely already starves it (both its catches
were garbage transcripts).

**Recorded, NOT queued — do not attempt without a plan:** Om Jai Jagdish
Hare was transcribed CORRECTLY ("om jai jagdish… tum puran parmaatma…")
and the matcher still matched "pAhirAmadhoothA" at 1.201, confidence
medium. This is a genuine matcher false-positive on a real transcript — the
hardest bluff class. No cheap gate fixes it; a real fix probably needs
score calibration / margin analysis across the OOC set. Flag it in the
report; don't burn the session on it.

**After all fixes: rerun the FULL eval (with raga), update the scoreboard
in the memory file `wild-test-set-status`, commit + push code and caches
with the new SCORE block in the commit message.**

## 7. After the fixes (not this task, but the trajectory)

1. Deploy on Deepti's sign-off: `bash backend/build_space.sh`, secrets per
   `DEPLOY.md` §1d, create the private HF feedback dataset BEFORE go-live,
   one uvicorn+curl smoke test. Deploys are Deepti-run (permission
   classifier blocks agent deploys).
2. Frontend confirm-button UI → feedback flywheel = the real clip source.
3. Drone-presence detection (needs Deepti's with/without-tanbura pairs).
4. IndicWhisper retry via ctranslate2 on Colab GPU for ASR-dead clips
   (Bhuvini Dasudane, Paluke Bangaramayena, sister nagumOmu).

## 8. Gotchas (new this session — older ones in HANDOFF_CLIP_ID.md §8 still bite)

- Deepti ear-checks still PENDING on two relabels: Kurai Onrum Illai
  (labeled Rāgamālika from registry; her 60s window may be the
  Sindhubhairavi section) and Paluke Bangaramayena (Ānandabhairavi).
  Registry raga metadata was deliberately NOT trusted over her labels for
  the devaranama clips — those ragas legitimately vary by rendition.
- "Katrin Mozhi__NA__OOC.m4a" was fetched from a video titled just "Mozhi"
  — may be a different song from that film. Irrelevant for OOC scoring
  (any film song must-abstain), but don't cite its title as ground truth.
- Eval iterates alphabetically and prints per-clip; to watch a long run,
  `tail -f` the task output grepping `TRUTH|SCORE|Traceback` — and grep
  the FINAL block for `composition top|OOC reject|raga`, the per-clip
  filter alone misses the summary lines.
- Background Bash tasks outlive the nominal 600s timeout cap (both multi-
  hour eval runs completed); don't restructure work around that cap, but
  don't rely on it being documented behavior either.
- The raga clip RF (`models/raga_clip_rf.pkl`, 1.1 GB) is gitignored;
  rebuild with `venv_train/bin/python train_raga_clip_model.py` if missing.
- Truth filenames: exactly one `__` before the raga; `__OOC` only as a
  trailing marker. Leading/trailing spaces in title or raga break truth
  parsing silently (two of Deepti's manual files had them — fixed by
  rename, watch for it in new batches).
