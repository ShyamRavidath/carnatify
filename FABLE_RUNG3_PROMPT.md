# Fable — Rung 3 (the ASR step-change). One shot, fully specified.

You are the implementer/eval-runner/committer. Read `AGENT_LOG.md` (newest
first: the two Opus entries "Rung 1 landed" and "Rung 2 landed", then Codex's
re-sequenced ladder) and `METRIC_CONTRACT.md` before writing code. Rungs 1 and
2 are already done in-repo by Opus at zero cost to you; the standing baseline
is **comp top-1 8/78, top-5 21/78, OOC 21/28** on `~/sung_tests --cache-v2`.
The catalog coverage floor is fixed, so this experiment is now falsifiable.

## The one question this rung answers
Does a previously-untested Indic acoustic model recover Carnatic sahitya that
Whisper-turbo turns into fluent-English hallucination? 10 of the 12 ASR-usable
auto-fetched truths are ASR-dead today. Nothing else changes.

## Exactly what to build (no more, no less)
- **Model: IndicConformer-600M via its official *native ONNX* path.**
- **CTC decoder only.** No RNNT this rung.
- **Mix audio only.** No stem/Demucs lane, no VAD, no segmentation.
- **No acoustic/catalog rescoring**, no fusion, no threshold changes.
- **Fixed language lanes for every clip**, identical set regardless of the
  clip — **do NOT read the language from the filename truth.** Use the corpus's
  real span: **Telugu, Tamil, Kannada, Hindi** (add Malayalam only if free).
  One raw hypothesis per lane, native script preserved.
- **Write a SEPARATE v2-compatible cache with its own model/config identity**
  (own `config`/`asr_config_id`, own file — e.g. `whisper`→`indic` analog). Do
  NOT mutate or mix into the turbo v2 cache; the eval must be able to run either
  cache cleanly. Follow the existing v2 schema: per-hypothesis
  `{source:'mix', lang, raw, status: 'ok'|'empty'|'error: ...'}`. Keep `error`
  distinct from `empty` — an integration failure is never an ASR-dead clip.
- Pass its **transliterated** hypotheses (`translit_fold` view) through the
  **current** matcher/policy unchanged. Same `assess_variants`, same thresholds.

## Procedure
1. **Smoke test first** on ~4 clips only (2 known ASR-dead, 2 known-live) to
   catch ONNX shape/runtime/tokenizer errors. The smoke result makes **no
   capability claim** — it only proves the integration runs.
2. If it runs, transcribe all 106 clips into the new cache (long run —
   `caffeinate -dims -w <pid>`, lid open; `python -u` if you pipe progress).
3. Evaluate all 106 against the new cache and **quote the verbatim full
   `--cache-v2` SCORE block** into `AGENT_LOG.md`, plus precision-at-coverage
   and the OOC bluff count per `METRIC_CONTRACT.md`. Report the curated-36
   guard — **must stay ≥ 8/36** (it is 9/36).

## Graveyard — do NOT resurrect (measured dead, do not spend tokens here)
Prompted/`kn`-lane Whisper (dasa slice stayed 0/8, top-5 dropped 3→2/8);
prompted-turbo (fluent hallucination defeats the gates); macOS ARM
faster-whisper int8 beam-1 (~1× realtime, garbage); ASR **max-fusion** (5/10
top-5, weak variants inject junk — segment output must generate candidates, not
max-pool raw scores); raga gating/blending; global DTW / melodic n-grams /
Qmax; more answer gates. The **vasista22/IndicWhisper** alternative is valid
ONLY through a CTranslate2/faster-whisper conversion, never the Transformers
pipeline (it failed at `forced_decoder_ids` / stale generation config / silent
CPU — it was never actually evaluated). This rung is IndicConformer native ONNX
— a genuinely untested model family, not a revival.

## Env / ops gotchas (bit us before)
- Everything in **venv_train** (py3.11). **No ffmpeg** — feed the model numpy
  arrays (librosa/essentia load), don't shell to ffmpeg.
- **numpy < 2.5.** macOS uses **fork, not spawn** for the match workers.
- **Cache keys are NFD** (APFS filenames are NFD — this bit the synth strip and
  the manifest; normalize consistently).
- `identify_clip.py` isn't run with `-u`; it buffers behind a pipe.

## Discipline
One-change-one-eval. Only a moved SCORE block on `~/sung_tests --cache-v2`
graduates this rung — reasoning and same-corpus numbers graduate nothing. If
CTC-only shows signal, the NEXT rungs are one variable each (RNNT on the same
mix, then vocal-active segmentation, then stem as an independent lane), chosen
from THIS score — do not bundle them now. Commit is yours; push is Deepti's.
