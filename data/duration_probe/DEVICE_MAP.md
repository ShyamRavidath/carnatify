# Device map — duration probe GPU run

Status 2026-07-30: **FULLY ESTABLISHED** — see "RESOLVED 2026-07-30" below,
which supersedes the "Unresolved" section. The text between here and there is
the earlier, partial state, kept because the calibration branch was chosen while
it was all that was known.

~~Partially established. The final session is fully resolved from its notebook
output; the T4 → intermediate-GPU boundary inside windows 1-259 is not.~~

Evidence: `data/duration_probe/notebook_session3_output.txt` (verbatim stdout of
the final session, saved from the still-open tab because `run_log.json` was
never written — `colab_duration_probe.py` writes it at L316, after the step 5/6
that crashed). Throughput figures for the two earlier devices come from
`handoff.md` §2.6.

## Sessions

| session | device | windows | evidence |
|---|---|---|---|
| 1 | Colab T4 | anchored 1 - ~80/84 | §2.6 only; boundary unresolved |
| 2 | intermediate GPU ("L4-class") | anchored ~81/85 - 259 | §2.6 only; boundary unresolved |
| 3 | **NVIDIA A100-SXM4-40GB**, torch 2.11.0+cu128 | anchored 260-300, **all 140 negatives** | notebook output, verbatim |

Measured throughput, wall seconds per second of audio, all 7 passes plus Demucs:

| device | s/s | source |
|---|---:|---|
| T4 | 1.56 | §2.6 |
| intermediate | 0.86 | §2.6 |
| **A100** | **0.497** (anchored), **0.450** (negatives) | recomputed here from the chunk timings |

The three rates are separated by 1.8x and 3.2x, so per-chunk timings in the two
earlier notebooks would identify their device boundary unambiguously **if those
tabs still exist**. That is the only remaining route to resolving `probe0016`.

## Established

- **`probe0051` is a straddler.** The session opened with `anchored: 259/300
  already cached, 41 to go` and its first transcription was
  `probe0051d300a.wav`. So `d030/d060/d090/d180` came from session 2 and `d300`
  from the A100 — the 30s → 300s contrast crosses devices. This is observed, not
  inferred from the stop index.
- **The negative arm is straddler-free.** `negatives: 0/140 already cached, 140
  to go`, and all 140 ran to `negatives: fully cached` inside this one session
  on the A100. §5b recorded this as a *belief* to be checked; it is now checked
  and true. This was the expensive case: under rule A (§6b) the gating sources
  are free-form n=25 and opening n=20 with zero tolerance for new bluffs, so a
  negative-arm exclusion had no slack to absorb it.
- **`probe0052`-`probe0059` (8 titles, 40 windows) ran entirely on the A100.**
  Each is internally consistent, so none is a straddler. They do sit on a
  different device from titles `probe0000`-`probe0050`, but that is *between*-title
  device variation and the estimand is a *within*-title contrast, so it does not
  confound the measurement. Recorded as a deviation, not a defect.

## Unresolved

- **Whether `probe0016` is a straddler.** §2.6 asserts both "windows 1-80 came
  off a T4, 81-259 off the faster GPU" and "`probe0016` is split, d030-d180 on
  the T4". `probe0016` is windows 81-85, so these cannot both hold, and session
  3's output says nothing about a boundary that far back. Resolving it needs the
  session-1 or session-2 notebook output, or Google Drive revision history on
  the checkpointed `asr_cache_v2.json`.
- Under §5b.1 this only matters on the *differs* branch of the device
  calibration. If the calibration comes back identical, no straddler set is
  needed and `probe0016` never has to be resolved.

## RESOLVED 2026-07-30 (workhorse) — Drive revision history recovered

Status is now **fully established**, by §5b.1(3) route (b). Deepti pulled all 82
revisions of the checkpointed `asr_cache_v2.json` — contents into
`asr_cache_fullhistory/` at repo root, timestamps from the Drive UI. Contents
give the exact entry set at each checkpoint; timestamps give the wall time
between them; audio seconds come from the window filenames. Together they yield
throughput per checkpoint, which separates the three devices.

(Filename indices descend with age — `(81)` is oldest — while Drive's "Version
N" ascends, so `Version k` is file `(82-k)` and `Current` is the bare file.)

### The three sessions, read off the record

| session | device | checkpoints | wall clock | windows | measured s/s |
|---|---|---|---|---|---|
| 1 | T4 | V1-V8, chunks of **10** | Wed 14:27 - 18:26 | 1-80 (`probe0000`-`probe0015`) | 1.36-1.73, **~1.55** |
| 2 | intermediate (L4-class) | V9-V42, chunks of **5** | Wed 18:40 - 23:40 | 81-259 (`probe0016`-`probe0050`, + `probe0051` d030-d180) | 0.55-1.00, **~0.80** |
| 3 | A100-SXM4-40GB | V44-Current, chunks of 5 | Wed 23:58 - Thu 03:40 | 260-300 + all 140 negatives | 0.31-0.55, **~0.46** |

The three measured rates reproduce the independently recorded 1.56 / 0.86 /
0.497 to two significant figures. That agreement is the check that the method
works, and it was not tuned to produce it.

**V43 (Wed 23:48) is the session-3 restart marker:** n=259, delta **zero** — the
resumed session mounting Drive and re-uploading the inherited cache unchanged
before transcribing anything.

### `probe0016` is NOT a straddler — §2.6's claim is refuted

Session 1 wrote in chunks of ten, and every one of its eight checkpoints lands
exactly on a two-title boundary (`probe0001d300a`, `probe0003d300a`, …,
`probe0015d300a`). Eight exact landings is not a retention artifact, so session
1's writes are per-chunk with `CHUNK = 10`.

Its final state is **n=80: titles `probe0000`-`probe0015` complete, no
`probe0016` window present**. Any successor session recomputes `pending()` from
that cache and therefore begins at window 81, `probe0016d030a`. **All five
`probe0016` windows were transcribed after the device change**, in session 2.
The device boundary falls on a title boundary and splits nothing.

The reading in which `probe0016` *would* straddle — that the 18:40 checkpoint
(n=84) is a session-1 write — is excluded: a `+4` write is impossible under
`CHUNK = 10`.

This also removes the contradiction §2.6 could never satisfy. "Windows 1-80 on
the T4" is **correct**; "`probe0016` split across that boundary" is **wrong**,
and the two were never compatible.

### The straddler set is exactly one unit

- **`probe0051` — title key `sujanajivana`.** d030/d060/d090/d180 in session 2
  (L4), d300 in session 3 (A100). Its 30s → 300s contrast, which is what the
  gate reads, crosses devices.
- **No other recall title straddles.** The only two device changes are at window
  80/81 (a title boundary) and window 259/260 (mid-`probe0051`).
- **No negative item straddles** — all 140 in session 3, already established.

Recall arm scores at **n = 59**. §5b.1(4) does not apply: the map is
established, so no straddler set has to be guessed.

### Two anomalies, recorded rather than smoothed

1. **Session 2's checkpoints sit one window below the chunk boundary.** With
   `pending` starting at window 81 and `CHUNK = 5`, boundaries should be n=85,
   90, …, 260; observed are 84, 89, …, 259 — consistently one short, each
   landing on a `d180a` window with the chunk's long `d300` window still to
   come. Session 3 shows no such offset (its first checkpoint, n=264 ending
   `probe0052d180a`, matches its notebook print exactly). The cause is not
   established. It does not touch the map: what matters is the *inherited* state
   at each device change, and those are n=80 and n=259, both read directly.
2. **Versions 69-73 are out of order** in the negatives region — n runs 375 →
   395 → 390 → 385 → 375 → 400. Consistent with the duplicates Deepti warned
   about. Immaterial: the whole negative arm is inside session 3 regardless of
   how those five are ordered.

## Two discrepancies worth not losing

1. **The executed notebook is not the file on disk.** The run processed windows
   in chunks of **5** (`[1/5] … [anchored 5/41]`), while
   `colab_duration_probe.py:72` reads `CHUNK = 10`. Whatever ran in Colab was
   edited relative to the repo copy. The notebook output is therefore the
   authority on what happened, and reasoning about the earlier sessions from the
   on-disk script is unsafe. (The sorted-window ordering *is* confirmed by the
   observed sequence.)
2. **259 is not chunk-aligned**, at either 5 or 10. A session that stopped on a
   checkpoint boundary should have. This is a loose end about how session 2
   ended, and it is now moot for the map — the boundary is established by
   session 3's own "already cached" count and its contiguous to-do list, not by
   arithmetic on the stop index.
