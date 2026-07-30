# GPT-5.6 — red-team brief: the duration probe and its pre-registered gate

You are the **red team**. Read-only on code. **Do not write code, do not
implement, do not propose a replacement design unless you have first shown the
current one is broken.** Your deliverable is an attack.

Deliverable: write your findings to `CODEX_DURATION_PROBE_REVIEW.md` in the
repo root. Nothing you produce reaches another agent except through that file —
the CLIs cannot see each other's chat, so state every assumption explicitly.

**Attack this before any audio is transcribed.** Once the data exists, a bad
gate is unfalsifiable: whoever reads the plot will rationalise whichever way it
came out. You caught the duration confound in this project once already, in a
cold read. Same job, one level deeper.

---

## 1. Why this probe exists

Carnatify identifies which Carnatic composition is being performed from live
audio (tolerant of artist, tempo, improvisation — not fingerprinting), and
classifies raga. Three approaches are **measured dead** — do not propose any of
them, and treat a design that quietly depends on one as a finding:

| dead approach | measurement |
|---|---|
| lyrics-ASR as shippable backbone | precision never exceeds ~31% at any threshold/tier/config |
| fine-tuning sung-Carnatic ASR on current data | LoRA Whisper-small: 8/78 → 0-1/78, memorised ~26 pallavis |
| CoverHunter checkpoint as CSI engine | clean source-disjoint mAP 0.113 vs 0.031 chance (dev 0.327 was ~2/3 same-recording leakage) |

Fuller graveyard: `HANDOFF_SESSION_0725.md` §6, `REVIEW_BRIEF.md` §4,
`HANDOFF_CLIP_ID.md` §5. Two meta-lessons, both bought expensively:
**benchmarks lie, wild clips don't**, and **every internal benchmark built so
far was flattered by same-corpus effects.**

The live observation: **every measured failure is on 30-60s clips, and the same
pipeline family scores 60-67% composition top-1 and 72.8% raga top-1 on full
recordings.** Hypothesis P1 is that **listening length** is the binding
constraint. It is explicitly a hypothesis, not a premise. You already noted in a
prior cold read that full recordings and wild clips differ in duration AND
recording quality AND segmentation AND catalog distribution, so duration is
confounded — this probe is the attempt to hold everything else constant.

Everything downstream waits on the answer. Gate passes → build the concert
companion app. Gate fails → P1 is the fourth measured wall and the roadmap turns
to building a rendition corpus, which is months.

---

## 2. The design as built

Read `scripts/duration_probe_cut.py` and `scripts/duration_probe_score.py`
in full. Both have long docstrings stating the reasoning; attack the reasoning,
not just the code. Summary:

**Pool.** `data/concert_audio/` — 1,238 mp3s, path form `<raga>/<title>.mp3`.
Titles are normalised (leading digits stripped) and folded with
`identify_clip.skey`, then matched against `data/composition_registry.json`
(8,688 rows). A title enters the pool only if it matches **exactly one
lyrics-bearing** registry row. Measured outcome over 1,049 distinct title keys:

```
resolved_unique_lyrics     133      <- the pool
ambiguous_multi_lyrics     254      <- dropped (work-family vs distinct works
                                       is reviewed judgment, not guessable)
matched_but_no_lyrics      388      <- dropped
no_registry_match          158
ambiguous_no_lyrics        116
skipped_non_composition     53      <- alapana/RTP/thani/tillana/etc
```

Of the 133, **79 are ≥300s** and can carry all four windows. Median source
duration 646s, min 301s, max 3,516s. Registry raga metadata is deliberately NOT
used to disambiguate: the registry contains junk rows whose `ragas` field holds
dates (`comp00000` is a street address with raga "Sept 13, 1997").

**Windows.** 30s / 60s / 180s / 300s, cut with ffmpeg to 16 kHz mono WAV so
preprocessing is byte-identical across durations and only length varies.

**Arms.** Primary arm draws a **random start offset independently per (item,
duration)**, seeded. Reasoning: a fixed start makes the 30s window a strict
prefix of the 300s window, and concert items open with alapana, which is
lyric-free by definition — so under a prefix start the 30s condition is the
worst possible window for a lyrics matcher *by construction*, and a rising curve
would prove nothing. A `prefix` arm exists for the anchored comparison.

**Scoring.** `CARNATIFY_ASR_BACKEND=whisper` only (product default,
one-change-one-eval). `identify_clip.py --json --no-raga --cache-v2`, joined
against the cut script's truth sidecar by a separate scorer. Nothing in the
scoreboard path is edited. Reports per duration: in-catalog top-1, top-5,
precision among answered, coverage, binomial SE.

**Declared exception.** This runs on different audio from the frozen scoreboard
(`~/sung_tests`, n=106) and **graduates nothing on its own**. It answers one
question: does the curve rise with listening length.

**The pre-registered gate.** Promote P1 only if BOTH:
(a) **≥15pp absolute gain in in-catalog top-5** from 30s to 300s, and
(b) **monotone non-decreasing** top-5 across all four durations.
At n=60 the binomial SE is ~±6.4pp; at n=79, ~±5.6pp.

---

## 3. What to attack — be specific, cite the number or the line

1. **The gate itself.** Is ≥15pp + monotone the right rule? Condition (b) is the
   part I most suspect: with four points at SE ±6pp, monotonicity is a
   ~coin-flip-ish requirement even under a genuinely rising effect, so a real
   effect could fail (b) by noise alone — but dropping (b) admits a curve that
   jumps once and flattens, which is a different finding. Give the decision rule
   you would actually defend, and state its false-pass and false-fail behaviour
   at this n. If you propose a test, say what it assumes and where those
   assumptions break here (the four windows come from the same 60-79 recordings,
   so the durations are **paired, not independent samples** — does the current
   analysis exploit or violate that?).

2. **Residual confounds inside the probe.** The point of the design is to hold
   everything constant but length. What is still varying? Candidates worth
   checking rather than asserting: independent random offsets mean the 30s and
   300s windows sample different *material* from the same recording, not just
   different amounts; longer windows have a higher chance of containing the
   pallavi at all; ASR behaviour may itself be length-dependent (segment
   handling, VAD, hallucination on long silence) in ways that are a property of
   Whisper rather than of evidence available.

3. **Leakage.** State whether anything in this pool could have shaped the
   registry, the matcher's thresholds, or the IDF statistics it scores with.
   `data/concert_audio/` is a project-collected corpus, and the standing lesson
   is that every internal benchmark so far was flattered by same-corpus effects.
   Assume nothing is clean; check `models/qmax_catalog*` provenance and whether
   the lyrics/IDF side has ever seen these recordings or their titles.

4. **Pool validity.** 133/1,049 title keys survive resolution — an 87% drop. Is
   the surviving 133 a biased subset in a way that matters? Plausible mechanism:
   titles resolving to exactly one lyrics-bearing row may be systematically the
   well-documented, famous, longer-lyric works, which are also the easiest to
   match — inflating every duration equally (harmless for the curve shape) or
   interacting with duration (not harmless). Say which, and how you would check
   it cheaply.

5. **Generalisation to the actual question.** The product question is "can 90
   seconds do what 5 minutes does". This probe measures full-length concert
   recordings, whereas the failures being explained are on `~/sung_tests` wild
   clips — phone recordings, ambient noise, variable mic. If the curve rises
   here, what exactly transfers, and what does not? Name the claim this probe
   would license and the claim it would not.

6. **The missing number.** The pool has no out-of-catalog items, so the
   METRIC_CONTRACT **OOC bluff rate is not measurable** here (the scorer prints
   `n/a` rather than dropping it). Longer windows plausibly raise both hit rate
   *and* bluff rate. Does the gate mean anything without it, or must a
   lyric-free arm (alapana/thani/RTP windows — 53 such files were identified and
   skipped) be cut and scored before the gate can be read at all? This is the
   question I most expect you to escalate.

7. **Cost, and what it forces.** `identify_v2` is read-only and never
   transcribes on a miss, so the probe needs a separate cache build via
   `scripts/build_asr_cache_v2.py`, which runs **7 Whisper passes per window**
   (4 language passes on mix, 3 on the Demucs vocal stem) plus Demucs itself.

   Measured on this machine (Apple silicon CPU, `whisper large-v3-turbo`,
   **mix-only, 4 passes**, i.e. already excluding the stem lane):

   ```
   30s window : 4 passes in  256s   (8.5 s wall per s audio)
   300s window: 4 passes in 1500s   (5.0 s wall per s audio)
   ```

   That is ~51 min per title for the four windows, so **n=60 is ~51 hours
   mix-only**, and roughly double plus Demucs at the full product config. The
   300s window alone is 49% of the cost; the 180s and 300s windows together are
   81%. Local execution is out; this is a GPU job on Colab Pro, which is
   Deepti-run and session-limited, so the runner must be resumable.

   Given that, evaluate the cost cuts as a set, not one at a time: (i) drop the
   Demucs stem lane; (ii) reduce n; (iii) reduce the four language passes
   (auto/ta/te/hi, combined longest-wins) to fewer; (iv) switch to
   faster-whisper int8, for which there is project precedent in
   `data/whisper_transcripts_fw_int8.json`. Each moves the probe further from
   the product default. Which of these preserve the **shape** of the duration
   curve even though they move its absolute level, and which could plausibly
   interact with duration itself and so corrupt the shape? Specifically: does
   the stem lane interact with duration (Demucs separation quality varying with
   input length)? Do multi-language passes help more at long durations than
   short, given more audio gives language ID more to work with? Rank the cuts by
   cost saved per unit of validity lost, and name any you consider
   disqualifying.

---

8. **A cheaper and possibly sharper variant — judge it against the above.**
   The v2 cache stores **per-segment timestamps** alongside the raw hypotheses
   (see the `scripts/build_asr_cache_v2.py` docstring). So a second design is
   available: transcribe **only the 300s window**, then reconstruct "what the
   matcher would see given the first N seconds" by truncating that transcript at
   segment boundaries, and score each truncation. Roughly half the GPU cost, and
   it cleanly separates two mechanisms the audio-cut design confounds:

   - **matcher-side evidence accumulation** — does more transcript text help the
     registry match? (what truncation measures)
   - **ASR-side length effects** — does Whisper transcribe a 30s file worse than
     the first 30s of a 300s file? (what truncation holds constant, and what
     the audio-cut design measures on top)

   If the truncation curve is flat but the audio-cut curve rises, the gain is an
   ASR artifact of short files, not evidence accumulation — and that distinction
   changes the product design completely: one says "listen longer", the other
   says "buffer and re-transcribe". Is running truncation **first**, as a cheap
   screen before spending on the audio cut, the better sequencing? Or does
   truncation answer a question so different that it cannot screen anything?
   State which of the two you would run given a fixed GPU budget, and why.

## 4. Rules

- **No code.** Prose, numbers, and file/line citations only.
- Every claim cites a measured number or a specific line. This project has
  repeatedly been wrong in the confident direction — including a chance-floor
  formula that averaged over the wrong axis and printed 0.006 instead of 0.031.
- If the design is sound, **say so plainly** and rank the residual risks. A
  rubber-stamp is worthless, but so is manufactured doubt.
- **Rank your findings by whether they change what gets run.** A flaw that
  changes the gate or forces the OOC arm outranks a flaw that only adds a
  caveat to the writeup.
- If you conclude the probe cannot answer P1 at any affordable n, say that
  outright and say what would. That is a legitimate and useful verdict.
