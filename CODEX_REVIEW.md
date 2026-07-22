# Carnatify live matcher review

**Reviewed:** 2026-07-21  
**Scope:** `identify_clip.py`, the staged `/identify` integration, the 106-clip
wild evaluation set in `~/sung_tests`, goal framing, and new work on the ASR
and text-matcher bottlenecks.

## Executive conclusion

The current 80–90% composition top-1 goal is not a credible product promise
for arbitrary 60-second wild windows. Some windows contain no
composition-identifying evidence (alapana, thani, an instrumental passage, or
silence/noise), so the target is partly ill-posed even before model quality is
considered. On the current system, the nominal “high confidence” tier is only
8/16 correct.

The product should use **precision at coverage** as its primary composition
metric, while continuing to publish overall in-catalog top-1/top-5 and OOC
rejection so abstention cannot game the result. A reasonable long-term product
bar is at least 85% precision among answered clips, followed by deliberate
coverage expansion. The suggested 35% coverage is still an aspiration rather
than a description of the current system: today the matcher answers 40/106
queries and only 11 of those answers are correct.

The largest immediate code defect is not the choice of ASR model. Native Tamil,
Telugu, and Devanagari ASR output is erased by `fold()` before it can be
matched. The largest matcher defect is that the score is structurally capable
of assigning high confidence to generic repeated words: the same transcript
token can satisfy several catalog tokens and contribute its repetition bonus
several times. The staged API also does not run exactly the policy scored by
the root evaluation script.

The best next direction is therefore:

1. make ASR output and evaluation trustworthy (Unicode, versioned cache,
   per-language/per-segment hypotheses, shared policy code);
2. improve candidate generation through catalog-constrained CTC scoring and
   ASR-to-ASR reference retrieval;
3. replace the many-to-one token heuristic with aligned, multi-segment
   evidence;
4. calibrate abstention only after candidate generation improves, validating
   prospectively on new wild clips.

No recommendation below uses an approach in the graveyard or an action blocked
in `OPEN_DECISIONS.md`.

## What was verified

### Repository state

The review read, in order, `REVIEW_BRIEF.md`, `ARCHITECTURE.md`, section 4 of
`handoff_state_and_progress.md`, `HANDOFF_VERFIER.md`, and
`OPEN_DECISIONS.md`. Claims were then checked against the current files and
commands rather than accepted from the handoffs.

At review time:

- `identify_clip.py` was 646 lines, not the roughly 1,500 stated in two docs.
- The branch was six commits ahead of `origin/main`, not five as stated in
  `OPEN_DECISIONS.md`.
- The worktree was already dirty in the two transcript caches and unrelated
  pre-existing paths. This review did not alter them.
- The wild set contained 106 clips: 78 in-catalog and 28 OOC.
- All 106 clips had stem transcript-cache entries.
- `data/composition_registry.json` contained 8,688 raw rows; `load_targets()`
  produced 8,679 matchable entries after filtering.
- Root `identify_clip.py` and `backend/identify_clip.py` were different files.
  The Space assembly script overwrites the backend copy, which makes local
  behavior dependent on whether assembly has been run.
- The live matcher files passed `py_compile`, but no test under `tests/` or
  `test_*.py` references `identify_clip.py`.

### Fresh scoreboard

The following was reproduced with:

```bash
venv_train/bin/python identify_clip.py ~/sung_tests --no-raga
```

The score block is quoted verbatim as required by `HANDOFF_VERFIER.md`:

```text
===== SCORE over 78 in-catalog + 28 OOC clips =====
composition top-1 11/78  top-5 18/78
OOC reject  24/28  (bluffs: 4)
raga        top-1 0/85  top-3 0/85  (clips with known raga truth)
raga via catalog backfill 8/36 (on clips with confident composition)
```

The raga zeros are not a raga result: they are an evaluation-output bug caused
by printing a raga denominator even when `--no-raga` disables inference. The
full 1.1 GB RF path was not rerun during this review. The 18/85 top-1 and 21/85
top-3 raga figures therefore remain the user-supplied/recent-full-run baseline,
not an independently reproduced result from this review session.

### Derived policy diagnostics

Running the current policy over the current cached transcripts produced:

| Tier | Answers | Correct top-1 | Correct top-5 | OOC bluffs |
|---|---:|---:|---:|---:|
| high | 16 | 8 | 11 | 1 |
| medium | 24 | 3 | 7 | 3 |
| low | 0 | 0 | 0 | 0 |
| none | 0 answers among 66 abstentions | — | — | 0 |

Overall, the system answered 40/106 clips, with 11/40 correct top-1. On the 42
auto-fetched in-catalog clips it answered 15, with 3 top-1 and 6 top-5 hits.

These figures have two important implications:

1. The current confidence labels are not confidence estimates. “High” is only
   8/16 correct, and “medium” is 3/24.
2. A perfect reranker restricted to the current top five could improve the
   auto-fetched conversion only from 3/15 to 6/15. Nine of the fifteen need
   improved ASR or candidate generation; reranking alone cannot recover them.

## Code review

### P0 — native-script hypotheses are erased before matching

[`fold()`](identify_clip.py#L80) normalizes diacritics and then retains only
ASCII `a-z0-9` and spaces. `_whisper_multi()` calls it on every raw Whisper
hypothesis before comparing variants. Consequently:

```text
'வாதாபி கணபதிம் பஜே' -> '  '
'వాతాపి గణపతిం భజే' -> '  '
'वातापि गणपतिं भजे' -> '  '
'vAtApi gaNapatim bhajE' -> 'vatapi ganapatim bhaje'
```

Any genuinely useful native Tamil, Telugu, or Devanagari output can be reduced
to whitespace and rejected. Because `_whisper_multi()` compares string length
after folding, whitespace can also participate in the “longest” selection
before the later non-space length gate rejects it.

This is particularly serious because the pipeline explicitly forces `ta`,
`te`, and `hi`. It will also invalidate an IndicConformer/IndicWhisper test if
native output is sent through the same fold.

**Required change:** preserve the raw Unicode hypothesis; identify its script;
transliterate deterministically to the matcher’s common representation; store
raw and transliterated forms together. Folding must be a matching view, never a
destructive storage format.

### P0 — the staged API and the scoreboard execute different policies

Root [`identify()`](identify_clip.py#L483) applies `_max_token_run()` and rejects
four consecutive identical tokens. The duplicated policy in
[`backend/clip_identify.py`](backend/clip_identify.py#L106) does not import or
apply that gate. The backend original-audio ASR also defaults to
`(None, "ta", "te")`, whereas the root original-audio pass additionally tries
Hindi.

The mismatch was reproduced directly through the staged wrapper:

```text
rama rama rama rama
  -> high: rArA AtmA rAmA (1.751)

satish satish satish satish
  -> medium: nee sATi (0.801)
```

Both are loops the root policy is intended to reject. The staged endpoint also
uses a different raga pipeline and does not apply the root script’s catalog
backfill behavior.

**Required change:** factor transcript sanitization, usability checks, variant
selection, confidence assignment, and response construction into one importable
function. Both CLI evaluation and `/identify` must call that function. Add a
contract test that feeds the same variants to both entry points and asserts an
identical composition response.

### P1 — the score can manufacture high confidence from generic repetition

[`_best_map()`](identify_clip.py#L247) independently assigns each catalog token
its best transcript token. There is no one-to-one constraint, so the same query
token can satisfy multiple similar catalog tokens. In
[`_score_ktoks()`](identify_clip.py#L263), that same token’s frequency is then
used for each title-token repetition bonus.

The final composition score is also the maximum across all title variants and
up to 60 lyric lines per entry, across thousands of entries. There is no
multiple-opportunity correction for entries with more lines or variants.

A direct smoke test demonstrates the failure shape:

```text
transcript: rama rama
top result: rArA AtmA rAmA
score: 1.451
```

That transcript passes the root minimum-length, repetition, and loop gates and
would be labeled high confidence because the margin is also large. Other
generic repeated tokens such as `raja raja` similarly produce scores above
1.0.

The score is unbounded because repetition bonuses accumulate, so 0.35, 0.5,
and 0.65 are not probability-like thresholds. In the current wild set every
answered clip already scores at least 0.5; the 0.35 abstention threshold and
the “low” confidence tier are functionally inactive.

**Required change:** use one-to-one weighted alignment between transcript and
catalog tokens/phonemes; normalize by distinct matched information; and
aggregate independent evidence rather than repeated use of the same token.
Entry score should account for the number of searchable variants/lines.

### P1 — “longest transcript wins” is anti-robust under hallucination

[`_whisper_multi()`](identify_clip.py#L353) retains only the longest folded
hypothesis. It discards:

- the language setting that generated each output;
- raw native script;
- segment boundaries and timestamps;
- token/segment likelihoods;
- competing hypotheses that might contain a short correct phrase;
- whether an exception or a genuinely empty decode produced no output.

This system’s own failure log says degraded audio creates fluent, confident
hallucinations. Length is therefore particularly unsafe: hallucinations are
often longer than the small amount of correctly decoded sahitya.

The fix is **not** the failed max-fusion approach. Preserve each source and
segment independently, retrieve candidates per hypothesis, and combine
composition-level evidence only after per-source calibration or independent
segment agreement.

### P1 — the transcript cache can silently invalidate the only scoreboard

[`transcribe()`](identify_clip.py#L370) and
[`transcribe_stem()`](identify_clip.py#L383) key caches only by basename. A key
does not include:

- an audio content hash;
- model identity or revision;
- language list;
- decoding parameters;
- source-separation model/configuration;
- code/schema version.

Replacing audio under the same filename or changing an ASR experiment can
therefore continue using old transcripts while presenting the result as a new
evaluation. This is especially dangerous because `~/sung_tests` is the only
accepted scoreboard. Cache writes also rewrite the JSON files in place, so an
interrupted or concurrent write can corrupt them.

**Required change:** derive a cache key from the audio hash plus complete ASR
configuration and preprocessing identity. Write atomically through a temporary
file and rename. Evaluation should support a read-only-cache mode and report
cache hits, misses, and configuration mismatches before scoring.

### P1 — the ASR-versus-matcher failure split is not identifiable today

The current decomposition calls a clip “ASR ok” when a transcript passes
minimum length, repeated-token, and loop gates. That is not evidence that the
transcript contains composition-identifying sahitya.

Among the twelve answered-but-wrong auto-fetched clips are outputs such as:

- `rAma nee`: `100 sembl killing 10ation 11ation...`
- `chakkani rAja`: a fluent English hallucination about being drunk and prison;
- `nagumomu ganaleni`: an English sequence about teenagers, children, and
  women;
- `Ehi annapUrNE`: a generic English sequence repeatedly containing “lord.”

These are counted as matcher misses only because repeated hallucinated words
pass the gates. Thus “64% ASR bottleneck” is a lower bound on ASR-related
failure, and “20% matcher conversion” mixes real matching failures with queries
for which the matcher received no useful evidence.

**Required evaluation change:** label each transcript, without looking at the
prediction, as one of:

1. no vocal/sahitya evidence in the audio window;
2. vocal evidence but ASR empty or hallucinated;
3. ASR contains identifying sahitya, true work absent from candidates;
4. true work in candidates but incorrectly ranked;
5. correct.

Deepti should adjudicate whether a window actually contains sahitya or a
recognizable composed passage; the agent should not infer that from filename
metadata alone.

### P1 — near-duplicate work rows distort top five and confidence margins

The registry contains independently ranked rows with closely related titles,
including `krSNa bArO`/`bArO krishNayya` and several forms of
`sarasija nAbha murArE` and `sri subramanyaya`. Some may be aliases of the same
underlying work and some may be genuinely distinct compositions; that is a
musical judgment and must not be resolved automatically.

Nevertheless, computing a margin between rank 1 and a rank-2 alias of the same
work understates confidence, while allowing several aliases to occupy the top
five reduces useful candidate diversity.

**Required change:** add a reviewed work-family identifier to the registry.
Collapse only verified families for result display and margin calculation.
Keep the raw source rows for provenance.

### P1 — raga inference retains a documented anti-informative selection rule

[`raga_top5()`](identify_clip.py#L435) generates twelve tonic rotations and
chooses the one whose RF prediction has the highest class probability. The
failure log says this confidence-based tonic selection is anti-informative on
wild clips because it follows class priors, and that twelve-rotation voting did
not solve it. The live function nevertheless retains that rule.

Catalog backfill also returns registry raga strings without applying the
documented raga-vocabulary validation, despite known address/date junk in the
registry.

This review does not recommend overwriting either production raga model. The
safe code-level change is to avoid presenting RF maximum probability as
evidence of tonic correctness and validate catalog raga values before display.

### P2 — the evaluation harness reports a fake raga result under `--no-raga`

[`main()`](identify_clip.py#L638) increments the known-raga denominator from
filenames even when no raga inference was requested, then prints zero hits. A
verifier following the documented fast composition command receives an
apparently real `0/85` result.

**Required change:** print `raga skipped (--no-raga)` and omit raga
denominators entirely when inference is disabled.

### P2 — broad exception swallowing hides integration failures

`_whisper_multi()` catches every exception and does nothing. Past Indic-ASR
attempts failed because of integration problems rather than model quality;
this pattern makes the same class of error look like an ASR-dead clip.

Exceptions should be recorded per language/model in structured diagnostics.
A source should be called “empty” only when decoding succeeded and returned no
usable symbols.

### P2 — unconstrained CPU parallelism is unsafe in the server path

`rapidfuzz.process.cdist(..., workers=-1)` uses all cores for each match. Under
multiple server requests this can oversubscribe the two-vCPU Space even though
Whisper itself is locked. Matcher concurrency should use a bounded executor or
an explicit worker count appropriate to deployment.

## Is 80% top-1 reachable?

### Arbitrary windows: no defensible basis

An arbitrary window can contain only alapana, thani, tuning, applause, or a
generic improvisational passage. In those cases the composition may not be
identifiable even to a knowledgeable human. Treating every such window as a
mandatory composition prediction creates an irreducible error floor and
rewards bluffing.

The current evidence is also far from the target:

- overall composition: 11/78 top-1;
- current answered precision: 11/40;
- nominal high tier: 8/16;
- auto-fetched arbitrary windows: 3/42 top-1;
- auto-fetched clips passing current gates: 3/15 top-1, 6/15 top-5.

No score/margin threshold tested on the current outputs creates an 85%-precise
nontrivial tier. Even the existing high tier is only 50% precise, with a 95%
Wilson interval of roughly 28–72% because it contains only sixteen examples.

### What the literature does and does not support

The closest large-scale query-by-singing/humming work does not establish an
80% top-1 result in a comparable setting. Amatov et al. trained on hundreds of
hours and evaluated against a 90,000-song internal collection. Their strongest
reported result for singing queries was 58.6% top-3, while stronger public
figures were top-10 on substantially easier humming-to-MIDI benchmarks:

- [A Semi-Supervised Deep Learning Approach to Dataset Collection for
  Query-by-Humming Task, ISMIR 2023](https://archives.ismir.net/ismir2023/paper/000077.pdf)

Vaglio et al. showed that noisy lyrics transcription can be powerful for cover
retrieval: a lyrics channel with about 62% WER achieved useful full-track
retrieval, and a lyrics/tonal system reached high MAP on vocal tracks. However,
the dataset was full-recording Western popular music, more than 92% detected as
English, the metric was MAP rather than arbitrary-window top-1, and the authors
explicitly called for non-Western evaluation. Their lyrics channel was nearly
zero on instrumentals:

- [The Words Remain the Same: Cover Detection with Lyrics Transcription,
  ISMIR 2021](https://archives.ismir.net/ismir2021/paper/000089.pdf)

This literature supports noisy-text retrieval and clip-type routing. It does
not validate 80–90% top-1 for arbitrary Carnatic concert windows.

### Recommended metric contract

Publish all of the following on the frozen wild set:

1. **Precision–coverage curve over all queries.** Every answered OOC clip is a
   false answer. Coverage denominator includes OOC and no-sahitya windows.
2. **Overall in-catalog top-1 and top-5.** This prevents an abstain-heavy system
   from appearing better without finding more compositions.
3. **OOC false-answer rate.** Keep it separate and visible.
4. **Eligibility-stratified outcomes.** Sahitya, composed instrumental,
   alapana, thani, and unusable/noisy. These are diagnostic strata, not a way
   to remove hard clips from the overall result.
5. **Assisted recovery.** For a routed abstention, measure whether one prompt
   to capture a sung pallavi produces a correct answer on the next attempt.

Keep “80% top-1” only as a long-term stretch goal for composition-eligible sung
clips, potentially after one guided retry. The near-term product objective
should be to attain at least 85% answered precision at any honest, nontrivial
coverage, then increase coverage without lowering precision.

## Proposals for the ASR bottleneck

### 1. Fix Unicode and retain all hypotheses before comparing models

This is prerequisite plumbing, not an experiment:

- preserve raw text from each language and source;
- transliterate native Indic scripts into one matcher representation;
- retain language, source (`mix`/`stem`), segment times, decoding status, and
  model/config identity;
- never choose a hypothesis by length before matching;
- keep raw output in the cache so normalization can be improved without
  rerunning ASR.

The resulting schema should be versioned. A compact example:

```json
{
  "audio_sha256": "...",
  "asr_config": "indicconformer600m-rnnt-v1",
  "hypotheses": [
    {
      "source": "stem",
      "language": "te",
      "start_s": 14.2,
      "end_s": 31.8,
      "raw": "...",
      "transliterated": "...",
      "status": "ok"
    }
  ]
}
```

### 2. Test IndicConformer through its native hybrid interface

The incumbent plan correctly identifies IndicConformer-600M as untested, but
the implementation route should be updated. The official model is a hybrid
CTC/RNNT ONNX model supporting 22 Indian languages, including Kannada, Tamil,
Telugu, and Sanskrit. Its current interface directly exposes CTC and RNNT
decoding:

- [AI4Bharat IndicConformer collection](https://huggingface.co/collections/ai4bharat/indicconformer)
- [IndicConformer-600M model implementation](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual/blob/main/model_onnx.py)

Do not force this model through ctranslate2. Use the native ONNX path for
IndicConformer; reserve ctranslate2 for converted Whisper checkpoints. Run CTC
and RNNT as separate hypotheses for `ta`, `te`, `kn`, and `sa`, preserving
native output. Colab Pro provides the available zero-additional-cost GPU path.

**Decision rule:** it only advances if the complete 106-clip wild scoreboard
improves. The 42-clip auto-fetched slice is useful for diagnosis, not for the
go/no-go decision.

### 3. Vocal-activity segmentation with independent decoding

Use RMS on the separated vocal stem to derive vocal-active intervals. Decode
overlapping 15–30 second groups with `condition_on_previous_text=False`, on
both the mix and stem, while retaining segment boundaries. Do not concatenate
everything into one long string before matching.

This is directly supported by recent Whisper lyrics-transcription work: using
source separation as a vocal activity detector to choose boundaries improved
long-form WER and reduced hallucination insertions compared with Whisper’s
native segmentation:

- [Exploiting Music Source Separation for Automatic Lyrics Transcription with
  Whisper](https://arxiv.org/abs/2506.15514)

The same paper also found that separation artifacts can trigger
hallucinations, which argues for keeping mix and stem hypotheses independent
rather than trusting the stem universally.

### 4. Catalog-constrained CTC line scoring

Full free-form transcription is a harder problem than Carnatify actually
needs to solve. Once a broad candidate set exists, the question is whether the
audio supports one of the known lyric-line phoneme sequences.

IndicConformer’s ONNX implementation computes frame-level CTC log
probabilities before greedy decoding. Expose those probabilities and calculate
CTC forced-alignment likelihood for candidate catalog lines in the relevant
scripts/phoneme representation. This can recover a correct composition even
when the best free-form string is wrong, as long as the acoustic posterior
retains the right symbols.

Suggested two-stage flow:

1. retrieve 50–100 candidate works from all unconstrained ASR hypotheses;
2. CTC-score their title/pallavi/line pronunciations against each vocal-active
   segment;
3. aggregate distinct segment/line evidence by work;
4. calibrate an abstention score on wild examples.

This is catalog-constrained acoustic rescoring, not prompted Whisper. It avoids
the already measured prompted-turbo hallucination failure.

### 5. ASR-conditioned reference retrieval

The repo already has roughly 1,238 catalog recordings covering about 1,102
compositions. Transcribe their vocal-active segments using the same ASR
configuration used at query time and build a composition-labeled index of the
noisy outputs. Query transcript segments can then retrieve reference transcript
segments rather than clean Romanized catalog text.

The mechanism is shared systematic ASR error: two renditions of the same
sahitya may be misheard similarly even when neither resembles the canonical
Romanization closely. Vaglio et al. demonstrated that matching noisy singing
transcriptions can remain useful at high WER, including for non-English pairs
where the recognizer produced similarly wrong text.

This proposal is distinct from the failed character-ngram Jaccard experiment:
the reference side is ASR output from real rendition audio, queries and
references are segmented identically, and retrieval aggregates evidence by
verified composition. It is also unrelated to the dead melody/Qmax path.

Coverage will initially be limited to compositions with recordings. Treat it
as an additional lyrics candidate source with an escape hatch, not a mandatory
filter over the 8,688-entry registry.

## Proposals for the matcher’s low conversion

### 1. Replace independent fuzzy hits with injective alignment

For each transcript segment and catalog line:

- construct phonetic tokens or short syllabic units;
- weight catalog units by corpus information content;
- compute a maximum-weight bipartite/monotonic alignment;
- allow insertions and deletions, but do not let one transcript token satisfy
  multiple catalog tokens;
- normalize by distinct matched information, not raw token count;
- cap or remove repetition bonus unless repetitions occur in separate temporal
  spans.

This directly removes the `rama rama` exploit while retaining fuzzy tolerance
for ASR spelling drift.

### 2. Aggregate independent segment-to-line evidence by composition

The present matcher takes a maximum over all lines. Replace that with a robust
composition score based on non-overlapping evidence, for example:

- strongest rare-span match;
- plus a discounted second match from a different segment or lyric line;
- plus agreement from an independent ASR source;
- minus a correction for the work’s number of indexed variants/lines.

One generic accidental line match should not beat two moderate, ordered matches
to different lines of the same composition.

### 3. Separate candidate recall from reranking in the scoreboard

For every clip whose transcript contains identifying sahitya, record:

- true work rank before reranking;
- candidate recall at 5, 20, 50, and 100;
- whether a clean title, lyric line, CTC score, or noisy-reference segment
  retrieved it;
- final top-1 and abstention decision.

This makes the 20% conversion wall actionable. On the present auto-fetched
slice, three of fifteen are top-1 and six are top-5, so only three errors are
currently rerankable within the displayed list.

### 4. Collapse only reviewed work families before ranking and confidence

Add explicit work IDs after Deepti reviews suspected duplicate/alias groups.
Aggregate candidates to work ID before computing top-1/top-5 and margins. Do
not silently merge based only on fuzzy title similarity or registry raga.

### 5. Calibrate selective prediction, not heuristic confidence labels

After candidate recall improves, fit a deliberately small calibrator using
features such as:

- aligned rare-information mass;
- number of distinct supporting segments and lines;
- mix/stem and CTC/RNNT agreement;
- title-versus-full-line source;
- family-collapsed top-1/top-2 margin;
- number of searchable variants for the winning work;
- null/OOC score percentile.

Logistic or isotonic calibration is preferable to a learned neural reranker at
the current data size. Calibration should produce an estimated correctness
probability used to draw a precision–coverage curve.

The current 106 clips have already influenced repeated design choices, so they
are a development/regression set, not an unbiased final test. Grouped
cross-validation on them may diagnose overfitting but cannot green-light a
change. Use prospective evaluation: score each newly acquired wild clip once
with a frozen model before adding it to development. No same-source crop or
same-recording sibling may enter the reference index for that evaluation.

## Recommended experiment order

All work below is local/Colab and zero-additional-cost. None requires a push,
deploy, paid API, production-model overwrite, or resolution of an item in
`OPEN_DECISIONS.md`.

### Phase 0 — correctness and observability

1. Make CLI and backend call the same policy implementation.
2. Preserve native Unicode and add deterministic transliteration.
3. Version cache entries by audio hash and complete ASR configuration.
4. Preserve per-language/per-source/per-segment hypotheses and failures.
5. Make `--no-raga` print `raga skipped`.
6. Add focused unit/contract tests for the five items above and the
   `rama rama` false-confidence regression.

This phase should not be claimed as an accuracy improvement unless the full
wild score actually changes.

### Phase 1 — matcher-only tests on existing audio/transcripts

1. Implement injective token/phoneme alignment without changing ASR.
2. Add multi-segment evidence aggregation where segment output is available.
3. Add reviewed work-family collapse for evaluation/display.
4. Run the complete 106-clip wild scoreboard and report candidate recall as
   well as top-1/top-5/OOC.

Stop or revert a variant if it does not improve the wild score or meaningfully
improve precision–coverage without reducing overall top-1.

### Phase 2 — ASR tests

1. RMS-VAD segment decoding on current Whisper mix and stem audio.
2. IndicConformer CTC and RNNT through the official ONNX path with native
   scripts preserved.
3. Catalog-constrained CTC rescoring.
4. Evaluate each addition separately before testing a combined selector.

Do not pool maximum scores across weak variants. A source contributes only
through independent evidence features or a selector calibrated on wild data.

### Phase 3 — noisy-reference catalog channel

1. Transcribe vocal-active segments of existing catalog recordings.
2. Build a source-recording-aware transcript index.
3. Ensure wild queries never retrieve a crop/sibling of their own source
   recording during evaluation.
4. Measure incremental candidate recall and top-1 on the 106 wild clips.

### Phase 4 — selective calibration and prospective validation

1. Freeze the candidate generator and matcher.
2. Fit the simplest adequate correctness calibrator.
3. Publish the full risk/precision–coverage curve.
4. Choose an operating threshold for at least 85% precision only if supported
   by prospective wild clips, not by resubstitution on the current set.

## Explicitly excluded recommendations

This review does **not** recommend:

- global DTW, subsequence DTW, Smith–Waterman, melodic n-grams, or contour
  matching;
- Qmax on wild short clips;
- raga-gating or raga-probability blending into composition matching;
- building on estimated tonic;
- another from-scratch raga CNN or more same-track segments;
- tala detection;
- adding Kannada to the existing Whisper language list as a standalone fix;
- prompted Whisper-turbo;
- faster-whisper int8 on macOS ARM as an accuracy/speed assumption;
- max-fusion pooling across ASR variants;
- another stack of heuristic hallucination gates;
- paid API calls, the declined meanings batch, a deploy, a push, or a
  production raga-model overwrite;
- treating the contaminated CoverHunter metric or any same-corpus result as a
  green light.

## Bottom line

The project does not currently have an 80% model hiding behind one bad
threshold. It has three coupled problems:

1. ASR evidence is frequently absent, hallucinated, or destroyed by ASCII-only
   normalization;
2. the matcher can create high scores from generic repetition and retrieves
   the true work in its top five for only 6/15 currently answered auto-fetched
   clips;
3. confidence labels are uncalibrated and the repeatedly used wild set is now
   a development set.

The most defensible product is selective: answer when multiple independent
pieces of sahitya evidence support one reviewed work, otherwise explain why
the window is not answerable and ask for a sung passage. The most promising
technical route is likewise evidence-focused: native-script ASR, vocal-active
segments, catalog-constrained CTC scoring, noisy-reference transcript
retrieval, one-to-one alignment, and prospective calibration.
