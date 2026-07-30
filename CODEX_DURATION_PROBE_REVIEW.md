# Red-team review — duration probe

Date: 2026-07-25  
Scope: read-only review before any duration-probe audio is transcribed. I did
not run ASR, edit either probe script, or modify any probe/source data.

## Verdict

**Do not transcribe the full probe as currently built.**

The idea is sound in its narrow form: use the same recording and frozen
pipeline at several durations, keep the probe outside the frozen scoreboard,
and pre-register the decision before seeing results. The implementation does
not yet realize that design. There are two pool-construction defects, the
primary arm samples different musical material at every duration, the scorer
does not use the pairing, and the binary gate calls every non-pass “P1 dead”
even when the experiment is merely inconclusive.

After correction, this can affordably estimate a duration response **for the
frozen Whisper lyrics pipeline on long-form `concert_audio` recordings**. It
cannot by itself establish the product claim for wild phone audio, cannot
answer the stated 90-second question without a 90-second condition, and cannot
justify a progressive-answer product without a separately adjudicated
out-of-catalog/no-sahitya safety arm.

The existing `data/duration_probe/truth_random.json` is only an eight-window,
two-title cut; it contains no ASR result. It is useful evidence of the design
problem: one title's four offsets are 5.7, 200.3, 453.6, and 110.0 seconds
(`data/duration_probe/truth_random.json:12-62`). I treated that as a cut-format
check, not probe data.

## Assumptions made explicit

1. P1 means a **practically useful causal effect of listening duration on the
   frozen product pipeline**, not proof that musical evidence rather than
   Whisper internals is the mechanism. The brief sets 15 percentage points as
   the useful effect (`scripts/duration_probe_score.py:12-15`).
2. “Progressive listening” means a user starts once and the system accumulates
   30, 60, 90, … seconds from that same start. The current product target is
   five-minute accuracy in at most 90 seconds
   (`HANDOFF_SESSION_0725.md:41-43`).
3. An inconclusive result is not a failure. Sending the roadmap into a
   months-long corpus effort requires evidence that rules out a useful duration
   effect, not merely failure to prove one.
4. Registry work IDs are not automatically work-family-complete. This project
   has already verified same-kriti duplicate IDs
   (`AGENT_LOG.md:1948-1968`) and therefore a single registry ID is not always
   complete truth.
5. Archive items or concerts, not filenames, are the independent sampling
   units when several tracks come from the same source. The download manifest
   retains `archive_identifier` (`data/concert_audio/download_manifest.json:2-9`).

## Findings ranked by whether they change what gets run

### P0 — Pool construction does not implement “one normalized title”

Two independent defects make the reported 133-title pool unreliable.

First, rendition suffixes are not stripped. The corpus convention is
`<title>[_rN].mp3` (`HANDOFF_SESSION_0725.md:232-235`), and the older catalog
builder explicitly defines and removes `_r\d+`
(`build_qmax_catalog.py:32-33`, `build_qmax_catalog.py:78-85`). The probe removes
only a leading number/punctuation prefix from `p.stem`
(`scripts/duration_probe_cut.py:98-103`). A read-only inventory found **136 of
1,238 MP3s** named with `_rN`; their keys therefore contain `r2`, `r3`, etc.,
and cannot represent the underlying composition key. This disproportionately
drops the very multi-rendition material that the handoff identified as useful.

Second, `by_key` stores a row once for every canonical/alias spelling
(`scripts/duration_probe_cut.py:91-97`) and later tests `len(lyric_rows) == 1`
(`scripts/duration_probe_cut.py:105-109`). If one registry row has two aliases
that fold to the same `skey`, that same row appears twice and is labeled
ambiguous. The criterion is list-entry uniqueness, not unique registry-ID
uniqueness.

There is also a truth hole in the opposite direction: the filter counts only
rows with `has_lyrics` (`scripts/duration_probe_cut.py:105-115`). A title can
match exactly one lyric-bearing row **and** one different lyrics-missing row;
the code accepts it and declares the lyric row to be truth. Yet the live matcher
loads every registry row, not only lyric-bearing rows
(`identify_clip.py:281-296`). “Exactly one lyrics-bearing row” is therefore not
the same as “exactly one composition.”

**Run consequence:** stop. Recompute the pool only after (1) using the corpus's
existing rendition normalization, (2) deduplicating candidate rows by ID, and
(3) reviewing or excluding title keys that still map to any conflicting work.
Truth should include verified equivalent sibling IDs rather than one arbitrary
row. Publish the bucket counts again; do not assume 133/79 survives.

### P0 — The gate is a noisy binary classifier, not a valid decision rule

The four observations per title are paired, but the scorer discards title-level
pairs into four marginal lists (`scripts/duration_probe_score.py:55-94`). Its
`wilson_se` is actually the ordinary single-binomial Wald standard error,
`sqrt(p(1-p)/n)`, not Wilson and not the standard error of the paired
difference (`scripts/duration_probe_score.py:36-41`). The displayed ±5-6
percentage points cannot be used to judge the uncertainty of the 30→300
contrast. That uncertainty is determined by the counts that flip wrong→right
and right→wrong within the same titles.

At n=60, 15 percentage points is nine net hits. Nine gains and zero losses is
very different evidence from 20 gains and 11 losses, although the current gate
calls both +15pp. A one-sided exact McNemar/sign test can test equality from the
gain/loss counts; a paired risk-difference interval is needed for the 15pp
practical threshold. Treating the four durations as independent binomials would
throw away the recording-difficulty pairing and usually overstate uncertainty;
treating tracks from one archive item as independent would understate it.

Strict observed monotonicity is not a defensible second condition. With equal
true rates and four exchangeable, continuously estimated points, only one of
the 4! orderings is monotone—about 4.2% before ties. Pairing changes that exact
number, but not the fact that a one-hit intermediate dip can veto a real
endpoint effect. At a true endpoint effect of exactly 15pp, the observed
endpoint condition has only about 50% power before the monotonicity veto; the
false-death probability is therefore already about 50% and condition (b) makes
it worse. Exact power cannot be computed without the paired discordance rates.

Condition (b) also does **not** do what its rationale claims. A curve that jumps
once and flattens—20, 35, 35, 35—is monotone and passes
(`scripts/duration_probe_score.py:107-116`). A jump by 60 or 90 seconds followed
by a plateau would actually be favorable product evidence, not a reason to
reject P1.

Most seriously, every gate failure prints “P1 DEAD” and attributes the result
to domain shift or weak representations
(`scripts/duration_probe_score.py:116-122`). A +14pp estimate, a +20pp estimate
with one intermediate dip, a cache-incomplete run, and a confidence interval
spanning -5 to +30 all receive the same causal verdict. The data do not license
that.

**Decision rule I would defend:** define
`Δ = P(top5 at 300s) - P(top5 at 30s)` on paired titles. Pre-register a
cluster-aware paired risk-difference confidence interval, resampling
`archive_identifier` where provenance exists. Use a three-way decision:

- promote the **practically useful ≥15pp** claim only if the one-sided 95% lower
  bound is at least +15pp;
- kill that claim only if the one-sided 95% upper bound is below +15pp;
- otherwise report **inconclusive** and do not pivot the roadmap.

Under a valid interval, false promotion when the true effect is below the
15pp boundary and false killing when it is at or above the boundary are each
bounded at approximately 5% in their respective one-sided tests. The price is
an inconclusive region, which is honest. If the team instead wants an action
rule with more power, it must explicitly define an indifference band (for
example “≤5pp negligible, ≥15pp useful”) and accept results between the two;
silently equating non-significance with death is not acceptable.

At n=60-79 and rates away from 0/1, an illustrative paired-difference standard
error is still roughly 6-8pp unless within-title correlation is very strong.
A one-sided margin is then roughly 10-13pp. An observed gain near +15pp will
probably be inconclusive; a gain far above it or near zero can be decisive.
Thus this n can detect a large wall/lever, but it cannot support the promised
forced binary answer at the boundary.

Intermediate durations should be reported with paired transition tables and
simultaneous intervals as shape diagnostics. They should not be exact-order
vetoes.

### P0 — Independent offsets do not hold musical material constant

The primary arm draws a new offset independently for each duration
(`scripts/duration_probe_cut.py:168-175`). That estimates the marginal accuracy
of an independently drawn random N-second excerpt. It does **not** estimate
progressive listening from one user start, and it does not hold section content
constant within a title.

The existing two-title sidecar makes the problem concrete. For
`ETi janmamidi hA`, the 30s excerpt begins at 5.7s, the 60s at 200.3s, the 180s
at 453.6s, and the 300s at 110.0s
(`data/duration_probe/truth_random.json:12-62`). The short excerpt can contain
pallavi while the long excerpt contains alapana/svaras, or vice versa. A
wrong→right transition then combines duration and section identity.

The objection to nesting correctly rejects a **zero-start** prefix: the track
opening may be systematically alapana-heavy
(`scripts/duration_probe_cut.py:29-36`). It does not reject a common,
uniformly-random start per title followed by nested durations. The implemented
`prefix` arm always starts at 0 (`scripts/duration_probe_cut.py:171-175`); it is
not a shared-random-anchor control. The design therefore has neither the clean
progressive estimand nor a same-content contrast.

Longer windows having a higher chance to contain pallavi is not itself a
confound if the product estimand is “what benefit does listening longer from
one arbitrary start provide?” It is a legitimate mechanism of duration. The
problem is drawing a different start for every dose, which needlessly adds
section-sampling variance and breaks the user journey being proposed.

**Run consequence:** choose and name the estimand before cutting the full set.
For progressive listening, the primary comparison needs one random anchor per
title and nested 30/60/90/180/300-second prefixes from that anchor. Keep
zero-start and independent-random-window results, if run at all, as separately
named sensitivity arms; neither should be allowed to overwrite the primary
gate.

### P0 — OOC/no-sahitya safety is mandatory for the roadmap decision

The metric contract makes precision at coverage primary and keeps OOC bluffs
visible (`METRIC_CONTRACT.md:20-34`). The current scorer admits it has no OOC
denominator (`scripts/duration_probe_score.py:17-21`,
`scripts/duration_probe_score.py:100-101`) but still promotes P1 and directs the
team to the companion app on in-catalog top-5 alone
(`scripts/duration_probe_score.py:116-118`).

Longer input can increase true top-5 and false answers simultaneously. This is
especially plausible here because Whisper processes the entire array
(`identify_clip.py:577-598`), the policy requires repeated tokens
(`identify_clip.py:1082-1095`), and a longer transcript creates more
opportunities both for real repeated sahitya and hallucinated overlap. An
in-catalog top-5 gain alone says nothing about whether progressive results are
safe to show.

The 53 skipped form/title keys are not automatically an OOC gold set.
`NON_COMP` includes `mangalam`, `tillana`, `viruttam`, and `sloka`
(`scripts/duration_probe_cut.py:64-67`), several of which can contain fixed
text. The metric contract requires eligibility strata to be assigned from the
audio by Deepti's ear, not filenames (`METRIC_CONTRACT.md:30-34`). An alapana or
thani is a no-sahitya negative; a composed work absent from the registry is a
different OOC negative. Both matter and should remain separate.

**Run consequence:** the in-catalog curve may be run as a scientific recall
probe, but its gate cannot authorize the product roadmap until a manually
adjudicated negative arm is scored at the same durations. Include genuine OOC
compositions and no-sahitya strata (alapana, thani, unusable/noisy); do not call
all 53 skipped filenames negative by construction. Pre-register the tolerated
change in bluff rate and publish precision/coverage with top-1/top-5.

### P1 — The experiment omits the stated 90-second product condition

The cut is 30/60/180/300 seconds (`scripts/duration_probe_cut.py:58-62`), while
the product target is five-minute accuracy in 90 seconds or less
(`HANDOFF_SESSION_0725.md:41-43`). A 60→180 bracket does not measure 90 seconds,
and the current 30→300 gate does not quantify the gap the next phase is supposed
to close.

There are two distinct questions:

1. Does 300 seconds materially beat 30 seconds? That is the P1 endpoint.
2. How far is 90 seconds from 300 seconds? That is the product gap.

The current run answers only the first. Add 90 seconds before transcription
(preferably replacing a less decision-relevant intermediate duration if cost
must stay fixed), and report the paired 90→300 gap without pretending that P1
passing means the gap is already closed.

### P1 — A positive curve licenses only an archive-domain claim

The pool consists of project-collected archive concert recordings, while the
frozen failures are 43-98s wild clips (`HANDOFF_SESSION_0725.md:143-148`). The
project's own cold review records that recording quality, segmentation, and
catalog distribution differ alongside duration
(`HANDOFF_SESSION_0725.md:81-85`).

A passing result would license:

> On uniquely resolved, lyrics-bearing, ≥5-minute `concert_audio` recordings,
> the frozen Whisper lyrics pipeline's in-catalog retrieval improves with
> longer listening under the specified window-start policy.

It would **not** license:

- the same gain on phone/ambient/noisy concert audio;
- 90-second equivalence to five minutes;
- safe abstention on OOC or no-sahitya audio;
- the claim that duration explains the old 60-67% full-recording result.

That last number came from Qmax, while the probe uses the lyrics matcher; the
project log already identifies that matcher-identity confound
(`AGENT_LOG.md:2396-2401`). The new probe can establish a duration effect for
the lyrics pipeline, but cannot retroactively turn Qmax's full-recording score
into evidence about Whisper.

A small prospective long wild-phone arm is required before product
generalization. The existing wild set cannot supply the 300s endpoint—its
maximum is 98s (`HANDOFF_SESSION_0725.md:143-148`)—so this requires newly
captured long recordings, not re-slicing the current scoreboard.

### P1 — There is catalog-label overlap, but not direct acoustic leakage in the selected path

The provenance is mixed and should be stated precisely.

**Direct overlap exists:** `build_qmax_catalog.py` builds archive entries from
the full-melodia cache and copies their filename-derived title into Qmax
metadata (`build_qmax_catalog.py:78-92`). The composition registry then ingests
those Qmax titles and raga labels (`build_composition_registry.py:76-90`).
Finally, the live matcher loads registry canonical names and aliases as target
variants (`identify_clip.py:281-295`). Thus the probe recordings' own project
labels helped create the catalog against which they are evaluated. This makes
the probe unsuitable for validating catalog resolution and contributes to the
severe pool-selection bias.

**The IDF overlap is transductive, not acoustic:** IDF is recomputed over all
loaded title and lyric-line tokens (`identify_clip.py:329-347`), including
probe works. It has seen catalog text, not these windows or their ASR output.
That is normal for retrieval against a fixed product catalog, but it means this
is not a prospective unseen-catalog test.

**No repo-level acoustic leakage was found in the selected scoring path:** the
probe invokes stock `large-v3-turbo` through `_whisper_hyps`
(`identify_clip.py:577-592`) and `identify_v2` reads only its versioned cache
before lyric assessment (`identify_clip.py:801-817`). The failed local ASR
fine-tune used weak Saraga data, not `concert_audio`
(`HANDOFF_SESSION_0725.md:64-69`). Qmax contains these recordings directly, but
Qmax is not called by the `whisper --no-raga --cache-v2` path. Any future
melodic or raga arm on this pool would be contaminated.

**Unknown external exposure remains:** a stock Whisper checkpoint may have seen
public Archive.org material during pretraining; the repository cannot establish
source-disjointness. I found no evidence that probe outcomes shaped the current
0.35 answer threshold or 0.15 stem preference; those frozen policy values are
documented in the live pipeline (`ARCHITECTURE.md:21-31`) and were evaluated on
the wild regression set.

The correct writeup is therefore “catalog-label overlap, no demonstrated local
ASR-audio leakage,” not “clean” and not “leaked.”

### P1 — The surviving pool is selected for exactly the property that can amplify a duration curve

Only 133 of 1,049 title keys resolve, and only 79 survive the ≥300s constraint
(`CODEX_DURATION_PROBE_BRIEF.md:56-70`). Even after fixing the two construction
bugs, exact unique lyric resolution selects well-documented works with local
text, and the duration threshold selects long performances. These can have
more verses, more distinct high-IDF lyric lines, and more extended non-lyrical
sections than excluded works.

This bias need not inflate all durations equally. The matcher takes a maximum
over title and lyric-line variants (`identify_clip.py:480-536`), capped at 60
lines per entry (`identify_clip.py:163-167`, `identify_clip.py:187-220`).
Works with many matchable sections have more opportunities for a long window
to capture at least one distinctive line; short/repetitive works can saturate
early. Pool selection can therefore change the curve shape, not merely its
intercept.

The recording choice is also not random. For every title key the code selects
`items[0]` after a path sort (`scripts/duration_probe_cut.py:98-110`). It then
checks only that rendition's duration (`scripts/duration_probe_cut.py:110-113`);
a short lexicographically first rendition can exclude a title even when another
rendition is long enough. Multiple sampled titles can also share one archive
concert, violating title-level independence.

**Cheap pre-run checks:** compare included versus every exclusion bucket on
source duration, rendition count, registry `n_tracks`, lyric line/token count,
lyric IDF mass, title length, composer/raga, and archive identifier. Within the
resolved pool, publish duration curves stratified by lyric length and source
cluster. The download manifest already records archive identifiers, so this
does not require guessing source groups (`download_targeted_deficits.py:290-299`).
A small hand-review of ambiguous high-value titles is more defensible than
assuming the 87% exclusion is ignorable.

### P1 — Dropping the stem lane changes the treatment and can change the curve

The default Whisper configuration is four mix passes plus three Demucs-stem
passes (`identify_clip.py:665-672`; `scripts/build_asr_cache_v2.py:46-60`).
The policy preferentially selects a stem variant whenever it is within 0.15 of
the best score (`identify_clip.py:1094-1102`). The stem-winning fraction can
therefore change with duration. Demucs is applied to the whole cut window
(`identify_clip.py:631-647`), so short-window boundary effects and long-window
chunk handling are also potential duration interactions.

At n=60 the windows contain 9.5 hours of unique audio
(`scripts/duration_probe_cut.py:156-159`). Full default inference represents
66.5 Whisper audio-hours (9.5 × 7) plus 9.5 hours passed through Demucs; n=79 is
12.5 unique hours, 87.5 Whisper audio-hours, plus Demucs. The cut script's
message saying “~4 whisper passes per window” is inconsistent with the actual
seven-pass builder (`scripts/duration_probe_cut.py:195-196`;
`scripts/build_asr_cache_v2.py:48-55`).

A mix-only run can be an explicitly exploratory mechanism screen. It cannot
pass or kill P1 for the product-default pipeline. A mix-only failure does not
show the stem-inclusive pipeline has no duration effect; a mix-only pass does
not show the default pipeline is safe. Because the roadmap decision is much
more expensive than this probe, retain the stem lane for the gate rather than
save compute by changing the evaluated product.

Also keep the cache configuration distinct if any exploratory lane is run:
the code explicitly requires configuration identity to change with model,
languages, or separation (`identify_clip.py:660-672`).

### P1 — Whisper and policy length effects are part of the total treatment, but block the proposed causal story

The code sends the whole waveform to Whisper
(`identify_clip.py:577-598`). The installed Whisper implementation advances
through fixed `N_FRAMES` mel windows
(`venv_train/lib/python3.11/site-packages/whisper/transcribe.py:270-295`) and,
by default, retains prior output tokens as the next decode prompt
(`venv_train/lib/python3.11/site-packages/whisper/transcribe.py:47-47`,
`venv_train/lib/python3.11/site-packages/whisper/transcribe.py:499-505`).
Longer arrays therefore create more internal decoding and conditioning
opportunities. The cache records raw text and segment times
(`scripts/build_asr_cache_v2.py:1-7`), so this can be diagnosed.

The matcher does not accumulate independent evidence across multiple lyric
lines. It scores each title/line and takes the maximum per entry
(`identify_clip.py:480-536`), then requires repetition and a fixed answer score
(`identify_clip.py:1082-1103`). A rising curve can therefore arise from:

- increased probability of including any sahitya/pallavi;
- Whisper's own long-input segmentation or hallucination behavior;
- repetition becoming observable in a longer transcript;
- more chances for one line to win the max;
- the stem/mix variant selector changing its winner.

All are genuine duration effects of the frozen pipeline, so none invalidates a
product-level total-effect estimate. They do invalidate the stronger conclusion
“the representation already works and only musical evidence quantity was
missing.” Report, by duration, ASR status/segment count, usable-transcript rate,
transcript token count, answer coverage, winning mix/stem lane, winning
title/pallavi/other channel, and wrong→right/right→wrong pairs. Without those
diagnostics, the curve cannot name its mechanism.

### P1 — The scorer can silently evaluate an incomplete or mutable experiment

The scorer warns about result rows absent from the sidecar, but never checks the
reverse: sidecar windows absent from results
(`scripts/duration_probe_score.py:55-67`). It does not require one result per
window, equal title sets at every duration, all four registered durations, or
zero cut failures. A missing result simply shrinks that duration's denominator.
Duplicate result rows can enlarge it.

Cache misses are counted and printed but still enter as ordinary wrong answers
(`scripts/duration_probe_score.py:79-98`). The verification protocol is
unambiguous: “a SCORE with misses is invalid”
(`HANDOFF_VERFIER.md:79-83`). The gate should abort, not interpret, on any
missing cache entry or incomplete paired title.

The supposedly fixed design is also runtime-mutable. `--gate-pp` can change the
15pp threshold (`scripts/duration_probe_score.py:44-49`), and the cut accepts
arbitrary duration lists (`scripts/duration_probe_cut.py:136-148`). The scorer
will evaluate any two endpoints and print “P1 DEAD/PROMOTED”
(`scripts/duration_probe_score.py:103-122`). Pre-registration requires the
invocation and sidecar design to be validated and recorded, not merely a
default value that can be changed after results exist.

**Run consequence:** before reading a plot, require an exact manifest/results
bijection, zero cache misses, identical title/source sets at every duration,
the registered seed/arm/durations/gate, and paired transition output. Any
failure makes the run invalid rather than a zero.

## What is sound and should be preserved

- The probe does not edit the frozen scoreboard and uses a separate truth
  sidecar (`scripts/duration_probe_cut.py:16-22`).
- Audio-hash plus full-config cache keys avoid the old filename-cache collision
  (`identify_clip.py:742-751`).
- Cutting every condition to 16 kHz mono PCM standardizes format
  (`scripts/duration_probe_cut.py:122-128`).
- Keeping the product-default Whisper backend as the only primary model honors
  one-change-one-eval (`HANDOFF_SESSION_0725.md:247-254`).
- A seed, declared primary arm, and pre-result review are the right
  anti-rationalization discipline.
- Refusing to use junk registry raga metadata automatically is prudent
  (`scripts/duration_probe_cut.py:80-90`).

These strengths are worth retaining. They do not repair the pool, estimand,
gate, or missing safety denominator.

## Required pre-transcription decision packet

I would approve the expensive run only after a revised pre-registration states,
in one place:

1. corrected pool counts after suffix normalization, registry-ID
   deduplication, conflicting-work review, and work-family truth expansion;
2. a common-random-anchor progressive arm containing 30, 60, **90**, 180, and
   300 seconds, with any zero-prefix/independent-offset arms explicitly
   secondary;
3. the paired, archive-cluster-aware effect estimator and three-way
   promote/kill/inconclusive rule;
4. exact expected window/result counts, zero-cache-miss abort criteria, and
   immutable seed/durations/gate recorded in the sidecar;
5. an adjudicated negative arm separating true OOC compositions from
   no-sahitya/unusable audio, plus the allowed bluff-rate change;
6. confirmation that the seven-pass mix+stem product configuration is retained,
   or a statement that a cheaper mix-only run is exploratory and cannot gate
   P1;
7. the narrow claim the archive-domain result may support and the prospective
   wild-long-audio check needed before product generalization.

Until then, the current experiment can generate a persuasive-looking curve but
cannot safely decide the roadmap.
