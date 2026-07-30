# Red-team brief — rebuilt negative arm (round 2)

Date: 2026-07-28, **labels added 2026-07-29**. For GPT-5.6, red team only, cold
read, **attack this**.

You reviewed the first negative arm and killed it
(`CODEX_NEGATIVE_ARM_REVIEW.md`). Every finding in that review was verified and
acted on. This is the rebuild. **No GPU has been spent.** Nothing is committed.

Your job is to find what is still wrong before ~45 Whisper-hours of negative arm
and up to ~77 of recall arm are burned. Assume the rebuild is wrong somewhere;
your last two cold reads each found something serious.

---

## What to read, in order

1. `DURATION_PROBE_PREREGISTRATION.md` — §1 (republished pool), §6 (arm
   rebuilt), **§6b (frozen negative decision rule)**, **§6c (how the arms
   combine)**. §§2-5 and §7 are unchanged and were already accepted.
2. `data/duration_probe/TITLE_RESOLUTION_AUDIT.md` — the false-merge audit you
   asked for.
3. `scripts/duration_probe_titles.py` — new; all title extraction and
   resolution.
4. `scripts/build_negative_arm.py` — rewritten.
5. `scripts/parse_negative_labels.py` — rewritten.
6. `scripts/duration_probe_score.py` — negative validity gate, negative
   decision rule, combined verdict.
7. `AGENT_LOG.md` entry dated 2026-07-28 02:45.

`data/duration_probe/v1_superseded/` holds the old arm and Deepti's v1 labels,
kept for audit and explicitly not reusable.

## What changed, claim by claim

| your finding | what was done |
|---|---|
| `NUM_PREFIX` stripped only 1-3 digits | any number of digits, plus archive track ranges; `file_title_raw` used when the filename is demonstrably not a title |
| 3/12 "OOC" items were in-catalog | a relaxed consonant-skeleton key now disqualifies them; all three resolve to the ids you named |
| 12 OOC items came from 3 archive sources | one item per archive cluster, enforced |
| OOC inferred from failed filename lookup | OOC now requires `data/duration_probe/verified_ooc.json`; everything else is `sung_unidentified`, non-gating |
| no-sahitya arm was 18, not 23 | `unusable`, coin-tosses and blanks are all `unknown`; only an unambiguous label counts |
| labels described audio never scored | windows cut first; the labeling sweep is cut from inside the scored 300s window |
| 3 sparse excerpts cannot support "no sahitya in 300s" | one sweep, 10s every 20s, 50% duty, max unheard gap 10s |
| n=35 underpowered | 70 items; gating stratum up to ~64 candidates |
| scorer had no negative gate or rule | validity gate + frozen exact upper-bound rule added |
| arms described as "paired" | retired; combination is an explicit conjunction |
| spend negative compute on 30/300 first | endpoints only |

## The realized arm (labels came back 2026-07-29)

Deepti labeled 69 of 70 rows. `scripts/parse_negative_labels.py` output,
verbatim:

```
sheet rows with a label: 69/70

=== per-item strata ===
  no-sahitya             51
  sung_unidentified       9
  in-catalog              8
  unknown                 2

=== stratum vs why it was sampled (blinding held while labeling) ===
  free_form_candidate      no-sahitya=26  sung_unidentified=7  unknown=1
  opening_candidate        in-catalog=8   no-sahitya=21       unknown=1
  unidentified_candidate   no-sahitya=4   sung_unidentified=2

GATING STRATUM (no-sahitya): 51 items over 51 clusters
NON-GATING (sensitivity): 9 items (sung_unidentified)
```

**n = 51, one item per cluster, no cluster repeated.** What that buys under the
§6b rule:

| new bluffs `b` | one-sided exact 95% UB | rules out +15pp |
|---:|---:|---|
| 0 | 5.7pp | yes |
| 1 | 9.0pp | yes |
| 2 | 11.8pp | yes |
| 3 | 14.5pp | yes |

So the arm survives up to three surprise answers, versus one for the 34-item
free-form-only design. The opening-window source is what bought that: it
contributed 21 of the 51 gating items.

Two labeling details worth your attention, neither silently reclassified:

- **`neg004`** — she wrote `no-sahitya` with the note *"this is tanam, so it has
  some characters but no actual sahitya"*. That matches the sheet's definition.
- **`neg030`** — she wrote `sahitya` with the note *"has swara in it"*. The
  sheet lists swaram **under `no-sahitya`**. Either the item also carried
  sahitya, or she overrode the definition. It was left as labeled, which
  excludes it from the gating stratum and can only shrink `n` — the safe
  direction — but it is a definitional inconsistency, and if there are others
  like it the stratum boundary is fuzzier than the sheet claims. Worth deciding
  whether "swaram alone" is really no-sahitya for a *lyrics* matcher, given
  Whisper will transcribe solfège syllables as words.

The 7 `free_form_candidate` items she heard singing in are almost all RTP files
— her notes say so (*"might be a RTP"*, *"Pretty sure this is a RTP"*). An RTP
contains a sung pallavi line by definition, so this is expected, and the code
correctly refuses to call them OOC.

## The three claims most worth attacking

**1. The opening-window source.** 30 of the 70 items are the first 300s of long
in-catalog recordings, added because `data/concert_audio` holds only 36
free-form files. The pre-registration argues anchor choice cannot bias this arm,
because eligibility is settled by adjudicating the very window that is scored.
Is that argument sound? Does mixing "opening of a known work" with "standalone
alapana file" create a population whose bluff rate means something different —
and if so, does pooling them into one gating stratum smuggle in an assumption?

**2. The upper-bound rule.** §6b claims detection at +15pp is unreachable here
and an exact one-sided 95% Clopper–Pearson upper bound on new bluffs is the
right substitute, ignoring reverse flips as conservative. Check the arithmetic
against your own §1 thresholds. Then check the *logic*: is a bound on `b/n`
really conservative for the estimand "change in answer rate", given that
ignoring `r` biases the point estimate upward but says nothing about the true
change? Is the conjunction in §6c the right way to pair an upper bound against a
lower bound, or does it have a joint-error-rate problem nobody has priced?

**3. The relaxed key, used only to disqualify.** `cskel` collides 388 of 8,058
consulted skeletons, touching 910 of 8,688 registry rows. The argument is that
exclusion-only use makes over-matching cost sample size and never validity. Is
that airtight? Consider what happens if the collisions are not independent of
the property being measured — e.g. if short-titled works are both more likely to
collide *and* more likely to be genuinely absent from the catalog.

## Also worth checking

- The pool delta is reported as **zero** (RESOLVED 271 → 271). Verify that.
  A repair that changes nothing is either a correct no-op or a repair that did
  not take effect.
- `data/duration_probe/verified_ooc.json` asserts OOC truth is unobtainable from
  assets on disk. Is that too quick? `~/sung_tests` holds 28 reviewed OOC clips,
  max 84s. Is there a design that uses them without a 300s endpoint?
- Partial labeling is declared valid because sheet order is randomised and
  blanks are unknown. She labeled 69/70, so the question is now narrow — but
  the 2 `unknown` items (one blank, one `unusable`) are not missing at random
  if difficulty correlates with anything. Does dropping 2 of 62 matter?
- **73% of the free-form census and 70% of the opening candidates came back
  no-sahitya.** Is a stratum that mixes those two at 26:21 one population? If
  the bluff rate genuinely differs by source, the pooled upper bound is still a
  valid bound on the pooled rate — but is the pooled rate the thing the product
  decision needs?
- The sweep is 50% duty with 10s gaps. What length of sung passage can hide in
  that, and does the guarantee stated in the sheet match the arithmetic?
- `scripts/duration_probe_score.py:validate_negatives` — is anything missing
  that could let a broken run print a safety conclusion?

## Rules of engagement

- Red team only. Do not implement, do not edit files.
- Every claim you make will be verified against the code and the scoreboard
  before anyone acts on it. Your checkable claims have all held so far; they
  will still be checked.
- `~/sung_tests --cache-v2` is the only scoreboard. The duration probe is a
  declared exception and graduates nothing on its own.
- If the right answer is "this is still not worth 45 Whisper-hours", say so and
  say what the cheapest sufficient design is instead.
