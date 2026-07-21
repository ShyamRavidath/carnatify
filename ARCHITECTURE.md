# ARCHITECTURE — what is live, what is legacy, what is dead

Written 2026-07-20. **Read this before trusting the code graph or the
directory layout.** This repo contains three generations of the composition
matcher living side by side. Structure alone will mislead you: the dead code
is larger, better organized, and more conventionally packaged than the live
code, which is one 1,500-line script at the repo root.

If a query or a code graph points you at `src/carnatify/ml/composition_matcher.py`
or `dtw_matcher.py` as "how composition matching works", it is pointing at the
graveyard. Every module in `src/carnatify/ml/` now carries a `STATUS:` banner
in its docstring — read it first.

---

## The live pipeline

**`identify_clip.py` (repo root) is the single source of matcher truth.**
It is standalone: it imports nothing from `src/carnatify/`.

```
audio (~60 s wild clip)
  -> dual ASR: whisper large-v3-turbo on original audio (langs None/ta/te/hi)
               + on demucs htdemucs vocal stem (None/ta/te)
               cached in data/whisper_transcripts_turbo{,_stems}.json
  -> matcher: IDF-weighted token coverage + pallavi-repetition bonus
              + order bonus, over registry title variants AND karnatik
              lyric-line pseudo-variants
  -> usability gates: stoplist, min chars, repetition, max-token-run
  -> policy v2: best usable variant, prefer stem within 0.15, abstain < 0.35
  -> top-5 + confidence tier (high / medium / low / none)
  -> raga: melodia -> tonic -> TDMS -> clip RF, always low-confidence;
           a confident composition match backfills raga from the registry
           instead (measurably better)
```

Run it:
```bash
venv_train/bin/python identify_clip.py <file-or-folder> [--json] [--no-raga] [--fast]
```
Folder mode is the regression suite — it prints per-clip `TRUTH` lines and a
final `SCORE` block. **Quote that block verbatim; never recompute by hand.**

The only scoreboard is the wild clip set in `~/sung_tests`. No same-corpus
benchmark green-lights anything — that rule was bought with several months of
flattered numbers.

## The legacy pipeline (still deployed, do not extend)

`backend/main.py` serves two generations at once:

| Path | Code | Status |
|---|---|---|
| `/identify`, `/feedback` | `backend/clip_identify.py` -> `identify_clip.py` | current, staged for deploy |
| legacy endpoints (`main.py` ~L173, ~L366) | `carnatify.ml.composition_matcher.match_composition` + `carnatify.ml.raga_classifier.predict_raga` | live in the deployed Space, ~16% composition / ~40.5% raga |

`backend/build_space.sh` does `cp -r "$ROOT/src"` — **the entire `src/` tree
ships to production**, graveyard included. That is why the dead melody-path
modules cannot simply be deleted: `composition_matcher` imports
`contour_preprocessor`, and the legacy endpoints import `composition_matcher`.
Retire the legacy endpoints first, then delete.

## The graveyard (measured, not suspected)

Each of these was built, measured, and beaten. The numbers are why they are
dead; do not re-derive them.

| Module / approach | Measured | Verdict |
|---|---|---|
| `dtw_matcher`, `contour_preprocessor` (DTW / contour melody matching) | 16-20% same-corpus, **0% on wild 60 s clips** | dead; structural variation + gamaka defeat it |
| melodic n-grams, Smith-Waterman, subsequence DTW | <=10% | dead |
| Qmax cover-song (`build_qmax_catalog.py`, `models/qmax_catalog.npz`) | 63-67% full-recording, **0% on wild clips** | still valid for full-recording mode ONLY |
| `composition_matcher` (L2-500pt, shipped) | ~16% | superseded by `identify_clip.py` |
| `composition_evaluator` | n/a | zero references; safe to delete |
| `tala_analyzer`, `tala_detector`, `tala_validator` | 16.5% vs 72% majority baseline | workstream closed |
| `RagaClassifier` CNN on tonic-rolled log-CQT | val pinned at chance for 60 epochs | memorizes per recording; the wall is tracks-per-raga, not epochs |

The full failure log with root causes is `handoff_state_and_progress.md`
section 4 and `HANDOFF_CLIP_ID.md` section 5. Read it before proposing
anything melody-based.

## Data assets (the actual moat)

These outlive every model in this repo:

- `data/composition_registry.json` — 8,688 canonical entries + aliases + ragas
- `data/karnatik_lyrics.json` — lyric pages driving line-level matching
- `data/lyrics.db` — 3,252 titles, meanings imported from karnatik
- `data/catalog_titles.txt` — grep this **before** declaring anything
  out-of-catalog (7 of 10 hand-picked "OOC" clips were actually in the registry)
- `~/sung_tests/` — 106 validated wild clips with filename ground truth
  (`<title>__<raga>[__OOC].<ext>`); the hardest data class to obtain
- `data/concert_audio/` — ~1,238 recordings, 1,102 compositions, 68 with
  multiple renditions

Caveat: the registry contains junk rows (addresses, dates parsed as
compositions). Never trust registry raga metadata without a raga-vocabulary
check.

## Environments

Two venvs, not interchangeable:

- `venv` (py3.14) — sklearn, librosa, mirdata, anthropic
- `venv_train` (py3.11) — demucs, whisper, essentia, rapidfuzz

**Matcher, ASR, and eval all run in `venv_train`.** No ffmpeg on the machine:
load audio via librosa/essentia, feed whisper numpy arrays, never file paths.
macOS multiprocessing uses fork, not spawn. Pin numpy<2.5.

## Code graph

`graphify-out/` holds an AST-derived code graph (`graph.json`,
`GRAPH_REPORT.md`). It is a **navigation aid, not an authority**: it ranks
structural connectivity and has no concept of "this was tried and failed."
The `STATUS:` banners in each module and this file are what carry that
knowledge. Regenerate with:

```bash
graphify update . --no-cluster && graphify cluster-only . --no-label
```
Both flags keep it LLM-free (community naming would call a paid API).
