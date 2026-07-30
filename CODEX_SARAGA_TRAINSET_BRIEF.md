# CODEX BRIEF — Saraga → sung-Carnatic ASR training-set data-prep

You are Codex (GPT), the bounded read-only analysis coder on the Carnatify
project. This is a fresh session: orient yourself, then do exactly the scoped
job below. Nothing here runs a model, GPU, or ASR — it is pure metadata
alignment writing a training manifest and a feasibility report.

## Orient first (read, in order)
1. `AGENT_LOG.md` — newest entries. Note especially the `[2026-07-23] Opus —
   DIAGNOSTIC` entry: two diagnostics proved the lyrics-ASR pipeline has **no
   shippable precision operating point** (≤31% at any gate; cross-channel
   agreement ≤43% on noise). The ASR **front-end** is the ceiling. This brief is
   the prerequisite for the only lever with headroom: a **sung-Carnatic-adapted
   ASR fine-tune**. Your job builds its training data.
2. `HANDOFF_SESSION_0723.md` — roles, discipline, the graveyard.

## Why this job
A sung-Carnatic ASR fine-tune needs `(audio-segment → lyric-text)` pairs. Saraga
has the sung audio but **no lyric transcripts**. We reconstruct weak alignments:
Saraga's per-track structural section timestamps + our existing lyric corpus,
matched by the composition each track performs.

## Inputs (all already on disk; read-only)
- **Saraga corpus:** `saraga1.5_carnatic/<concert>/<track>/`. Each track has,
  named `<Artist> - <Track>.<ext>`:
  - `.json` — metadata. Fields you need: `title`, `work` (list of
    `{title, mbid}` — the canonical composition, e.g. `"Amba Kamakshi"`),
    `raaga` (list of `{name}`), `form` (list of `{name}`, e.g. `"Kriti"`,
    `"Rāgam Tānam Pallavi"`, `"Ālāpana"`, `"Thani Āvarthanam"`, `"Thillana"`,
    `"Virutham"`), `taala`, `length` (milliseconds).
  - `.sections-manual.txt` — lines of `start_sec \t 1 \t end_sec \t label`.
    Labels seen: `vocal_alap`, `pallavi`, `anupallavi`, `charanams`, etc. The
    middle `1` is an annotation-level marker — ignore it. (`.sections-manual-p.txt`
    is the same with pretty/diacritic labels; use the plain one for logic.)
  - `.mp3` — full ensemble mix (voice + violin + mridangam). Do NOT decode or
    separate audio in this job; the manifest only references path + timestamps.
- **Composition registry:** `data/composition_registry.json` — rows with `id`,
  `canonical`, `composers`, `ragas`, `karnatik_pages` (list of page ids).
- **Lyric corpus:** `data/karnatik_lyrics.json` — rows with `page` and `lyrics`
  (plain text with section headers like `pallavi:` / `anupallavi:` /
  `caranam:` / `charanam:`; see how `scripts/detect_workfamily_dupes.py`
  parses sections and `first_pallavi()` for the header regex — reuse that logic,
  do not reinvent a divergent parser).
- **Link overrides:** `data/karnatik_link_overrides.json` (`{"links": {id: [page,…]}}`).
- **Normalizer:** import `skey` from `identify_clip.py` for title matching —
  the SAME folded-key matcher the manifest builder uses. Do not invent another.

## The task
Write `scripts/build_saraga_asr_trainset.py` (runnable as
`venv_train/bin/python scripts/build_saraga_asr_trainset.py`) that:

1. **Walk every Saraga track.** Parse its `.json`.
2. **Keep only lyrical forms.** Include tracks whose `form` denotes fixed
   sahitya (`Kriti`, `Kīrtana`, `Varnam`, `Padam`, `Javali`, `Devarnama`,
   `Tiruppugazh`, and similar). **Exclude** `Ālāpana`, `Rāgam Tānam Pallavi`,
   `Thani Āvarthanam`, `Thillana` (solkattu, not sahitya), and anything with no
   fixed lyric. Record excluded counts by form in the report.
3. **Match track → registry composition.** Use `work[].title` first (fall back
   to `title`), via `skey`. Require the registry row's raga to be consistent
   with the track's `raaga` (spelling-folded compare; reuse the raga-alias
   approach from `detect_workfamily_dupes.py` if helpful). Resolve the row's
   lyric text through `karnatik_pages` + link overrides → `karnatik_lyrics.json`.
   A track with no confident lyric-bearing match is skipped (counted, listed).
4. **Align sections to lyric text.** For each section span in
   `.sections-manual.txt`:
   - Skip `vocal_alap` / alapana-type / purely-instrumental spans.
   - Map `pallavi`/`anupallavi`/`charanam(s)` spans to that section's text
     parsed from the composition's lyrics. If a label is plural/ambiguous
     (`charanams` covering many verses over many minutes), assign the
     concatenated charanam text but **tag it low-confidence**.
5. **Chunk to ≤30 s windows** (Whisper's frame). For a section span, emit
   consecutive ≤30 s `(start,end)` windows. Attach the section's lyric text to
   each window (acceptable for short repetitive pallavi/anupallavi; that is why
   charanam is tagged low-confidence). Do not fabricate sub-alignment you don't
   have.
6. **Emit two files:**
   - `data/saraga_asr_trainset.json` — list of segment objects:
     `{track_rel_path, audio_rel_path, start_sec, end_sec, section_label,
       text, work_title, registry_id, raga, form, confidence}` where
     `confidence ∈ {"high","low"}` (pallavi/anupallavi = high, charanam = low).
   - `data/saraga_asr_trainset_report.md` — feasibility numbers so Deepti can
     decide if there is enough signal to justify GPU time BEFORE any training:
     total Saraga tracks; kept vs excluded by form; matched-to-lyrics count;
     segment counts and **total audio minutes** split by confidence
     (high = pallavi/anupallavi only; low = charanam); a list of high-value
     unmatched tracks (lyrical form but no registry/lyric match) so we can fill
     gaps later.

## Constraints (hard)
- **Read-only** on Saraga, registry, lyrics, overrides. Never edit the registry,
  `data/wild_truth_manifest.json`, the matcher, or any cache.
- **No audio decode, no Demucs, no ASR, no GPU, no model, no network.** Durations
  come from the `.json` `length` field and section timestamps only.
- Reuse `identify_clip.skey` and the lyric/section parsing from
  `detect_workfamily_dupes.py`; do not fork divergent normalizers.
- Validate the script compiles and runs end-to-end; report the actual numbers it
  produced. No commit, no push (Deepti's).
- If the honest feasibility numbers are weak (e.g. only a few matched tracks or a
  few minutes of high-confidence audio), **say so plainly in the report** — a
  negative result is a valid, useful outcome here, not a failure to hide.

## Acceptance
`data/saraga_asr_trainset.json` + `data/saraga_asr_trainset_report.md` exist, the
script is deterministic and read-only, and the report states matched-track count
and total aligned minutes by confidence. Append a dated AGENT_LOG entry
`## [YYYY-MM-DD] Codex — Saraga ASR trainset prep` with the headline numbers and
your honest read on whether the aligned data looks sufficient to fine-tune on.
