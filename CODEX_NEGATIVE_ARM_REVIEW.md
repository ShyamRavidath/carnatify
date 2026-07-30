# Negative-arm red-team review

Date: 2026-07-28  
Scope: negative arm only; review performed before duration-probe inference

## Verdict

**Do not spend the 122 Whisper-hours on the staged experiment yet.**

The nominal 23 no-sahitya + 12 OOC arm is too weak to provide a
decision-quality counterweight to the +15 percentage-point recall gate. More
importantly, the nominal counts are not presently valid truth counts:

- the current scorer prints negative point rates but has no negative-arm
  confidence interval, hypothesis test, safety boundary, or validity gate;
- the 12 alleged OOC items are inferred from failed filename-to-registry
  matching, not from verified identities of the works being sung;
- at least 3 of those 12 have source metadata naming works that are already in
  the registry;
- the 12 OOC rows come from only 3 archive sources;
- five retained no-sahitya rows do not have three certainly no-sahitya excerpt
  labels; and
- the three labeling excerpts are not the actual nested probe windows. Five of
  the selected 300-second windows do not overlap any labeled excerpt.

Adding items is warranted, but only after repairing truth construction and
locking a statistical safety rule. Simply running the current sampler again
would multiply the same labeling and clustering defects.

## 1. What bluff increase is detectable?

### What the current analysis can detect

Formally, **nothing**: `report_negatives()` in
`scripts/duration_probe_score.py` only prints the answered count at each
duration. It does not compute paired transitions, uncertainty, power, or a
negative decision. Its final statement that equal increases in hits and bluffs
are not a product improvement is qualitative, not an implemented gate.

The calculations below show what a reasonable paired analysis could detect.
They use an exact one-sided McNemar/sign test at alpha 0.05. That is the
one-sided error rate corresponding to the lower edge of a two-sided 90%
interval. They also make the **best possible assumption for power**: duration
can create new bluffs but never remove an existing bluff. Any 300-second
bluff-to-abstention transitions make power worse.

| arm | n | one item | smallest significant observed rise if there are no reverse flips | power if the true rise is +15pp | rise needed for 80% power |
|---|---:|---:|---:|---:|---:|
| combined | 35 | 2.86pp | 5/35 = 14.3pp (p = 0.03125) | 61.9% | 18.5pp |
| no-sahitya | 23 | 4.35pp | 5/23 = 21.7pp | 25.6% | 27.5pp |
| OOC | 12 | 8.33pp | 5/12 = 41.7pp | 2.4% | 49.7pp |

The distinction between an observed threshold and power matters. Five clean
one-way flips happen to cross the exact-test threshold, so a realized 14.3pp
rise in the combined arm can be called nonzero. But when the population effect
really is +15pp, this experiment misses it about 38% of the time even in the
favorable monotone case.

The favorable assumption is not guaranteed. At n=35:

- with a 2pp reverse-flip probability and a net +15pp change, power falls to
  51.6% and the 80%-power minimum detectable net change rises to 22.1pp;
- with a 5pp reverse-flip probability, power falls to 41.7% and the 80%-power
  minimum rises to 26.0pp.

A one-sided alpha of 0.10 makes the combined arm look just adequate (79.1%
power at +15pp; 80%-power minimum 15.2pp), but that is a looser rule than the
alpha-0.05 lower-bound logic used by the recall gate. It also does not rescue
the two required strata.

### Is that enough to pair against the +15pp recall gate?

**No.**

First, the combined arm is underpowered at the effect size that defines the
recall decision, and the separately reported OOC stratum is effectively
incapable of detecting it.

Second, the two effects are not arithmetically interchangeable:

- recall is a change in **top-five hit rate among eligible in-catalog works**;
- bluffing is a change in **answer rate among negative queries**.

Subtracting one percentage-point change from the other assumes equal positive
and negative query prevalence, equal costs, and that a top-five retrieval has
the same product value as an answer shown to the user. None of those assumptions
is registered. A product comparison needs either:

1. a separate negative safety condition, such as an upper confidence bound on
   the bluff-rate increase; or
2. a prevalence- and cost-weighted utility estimand using compatible output
   events.

The negative arm should not be described as “paired against” the recall gate
until one of those rules is frozen.

For perspective, under the same favorable monotone model, 44 independent
negative items are the minimum that gives at least 80% power to detect a true
+15pp combined rise at one-sided alpha 0.05. That is a floor, not a recommended
final n: clustering, reverse flips, and separate-stratum reporting all raise the
requirement.

If the intended safety claim is instead “rule out a bluff increase of 15pp,” a
one-sided 95% exact upper bound is below 15pp only with:

- at least 19 items and zero new bluffs;
- at least 30 items if one new bluff is observed; or
- at least 40 items if two new bluffs are observed.

The OOC n=12 arm cannot rule out +15pp even if it observes zero new bluffs; its
one-sided 95% upper bound is about 22.1%.

## 2. The OOC denominator is not valid

`scripts/parse_negative_labels.py` correctly recognizes that catalog membership
cannot be judged by ear. It does not, however, establish the missing fact:
**which composition is actually being sung**.

For an `absent_from_registry` candidate, the parser currently declares OOC when:

1. any excerpt sounds sahitya-bearing; and
2. `title_from_filename` does not exactly resolve to the registry.

That only works if the filename is a trustworthy composition title. It is not
for this sample. `duration_probe_cut.py` strips only a one-to-three-digit
prefix. Seven-digit Jamendo identifiers therefore become strings such as
`4830 aswinsainarain` and `6717 Music NCBS`, which naturally fail registry
lookup.

The download manifest supplies direct counterexamples:

| item | source title in manifest | registry evidence |
|---|---|---|
| `neg001` | `04_khamas_santanagopalakrishnam` | registry contains `santAna gOpAlakrSNam` |
| `neg003` | `04_kaanada_alaipayuthey` | registry contains `alai pAyudE` |
| `neg005` | `06_kapi-alapana_ragamalika_chinnanchiru-kiliye` | registry contains variants including `chinnam ciru kiLiyE` |

Thus at least 3/12 nominal OOC items are demonstrably contaminated by
in-catalog works. The remaining filenames do not establish OOC truth either:
seven are “Melakartha Chakkaram” lecture-demonstration tracks, and the other
Jamendo titles are generic uploader/album-derived names. Absence of those
strings from the registry is not absence of the sung work.

The nominal 12 are also only three source clusters:

- 7 from `melakartalecdems`;
- 3 from `jamendo-150288`;
- 2 from `jamendo-146935`.

Treating them as 12 independent OOC works overstates both sample size and
domain diversity. The negative scorer has no cluster-aware inference.

**Required correction:** identify the actual sung work from trustworthy source
metadata or manual adjudication, then join that identity to the registry. Until
then, all 12 belong in `sung_unidentified`/unknown, not OOC.

## 3. Are the two `sung_unidentified` exclusions correct?

**Correct for the clean OOC denominator; incomplete for the product
denominator.**

The parser is right not to turn the two RTP filenames into OOC truth. “RTP”
names a performance section, not a work, so audible pallavi sahitya plus no
registry row for the string `RTP` cannot prove that the sung material is absent
from the catalog.

Including the two as OOC would bias the clean OOC denominator. Silently
discarding them from every reported negative result creates the opposite
problem: an “adjudicable cases only” denominator that omits exactly the
ambiguous sung inputs a product must handle.

They should therefore:

- remain excluded from the primary clean OOC estimate;
- remain visible as a separate unknown-catalog sung stratum;
- receive their own answer/abstention results as a sensitivity analysis; and
- be moved into OOC or in-catalog only if the pallavi/work can be identified.

Numerically, two cases are not negligible here. Relative to 37 potentially
usable negative recordings, their duration transitions can move a combined
rate difference by as much as 2/37 = 5.4pp. They are also two similar RTP items,
so they should not be treated as two fully independent confirmations.

The same caution must be applied to the nominal 12 OOC items. Excluding only
the two free-form cases while trusting malformed “absent from registry”
filenames is inconsistent.

## 4. The no-sahitya truth is also weaker than 23

The parser's “conservative” aggregation does not match its claim.

- It does not require exactly three excerpt labels. `neg002` and `neg007` are
  retained as no-sahitya from one label each.
- It treats `unusable` as if it could not conceal sahitya. `neg006`, `neg013`,
  and `neg034` are retained as no-sahitya despite one or more unusable
  excerpts.
- Its `certain` flag means only that each supplied token has one option. It does
  not mean all three excerpts were supplied or usable.

Only 18/23 retained no-sahitya items have exactly three labels that are each
unambiguously `no-sahitya`. Even that is excerpt-level evidence, not selected
window truth.

The labeling excerpts were centered at 15%, 50%, and 85% of each recording.
The duration windows were later cut from a random anchor. Comparing the
sidecars shows:

- 2/23 selected no-sahitya 300-second windows overlap none of the labeled
  excerpts;
- 3/12 selected OOC 300-second windows overlap none;
- many other 300-second windows overlap only one 20-second excerpt.

Three sparse samples cannot establish that an intervening 300-second interval
contains no sahitya. The claim that whole-recording status is “measured” is too
strong. The exact selected 300-second window should be adjudicated; because the
shorter windows are nested within it, labels can then be assigned to the
actual endpoint windows rather than inferred from unrelated locations.

Eligibility may also change with duration. A 30-second prefix can be
no-sahitya while its 300-second parent reaches sung material. Recording-level
strata hide that transition, even though `METRIC_CONTRACT.md` defines
eligibility from the audio presented to the system.

## 5. What to do before GPU spend

1. **Freeze a negative estimand and decision rule.** Use paired 30-to-300
   transitions with a stated confidence level. Decide whether the gate detects
   harmful increases, rules out an unacceptable increase, or estimates a
   weighted product utility.

2. **Repair truth before increasing n.** Re-adjudicate the exact selected
   windows. Treat incomplete or unusable excerpts as unknown. Verify actual
   work identity for OOC; filename lookup failure is candidate generation, not
   truth.

3. **Replace and diversify the OOC arm.** Sample by independent work and
   archive/concert, not by file. Do not count multiple lecture-demonstration
   tracks or adjacent album tracks as independent OOC evidence. Prospective
   known-identity OOC recordings are preferable.

4. **Increase valid independent n.** For a combined detection gate, 44 is the
   optimistic minimum for 80% power at +15pp. If no-sahitya and OOC must each
   detect that change, target at least 44 valid independent items **per
   stratum**, then inflate for clustering. If the goal is an upper-bound safety
   claim, power that design directly instead.

5. **Spend negative compute on the gating contrast first.** The inferential
   question is 30s versus 300s. Five windows cost 660 audio-seconds per item;
   the two endpoints cost 330. For example, 88 items at the two endpoints are
   about 8.1 hours of unique audio, or 56.5 seven-pass Whisper-hours—only about
   11.6 Whisper-hours more than the current 35-item, five-duration negative
   arm. Intermediate negative durations can remain a non-gating diagnostic if
   budget permits.

6. **Close the scorer validity hole.** Validate negative results against
   `truth_negatives.json`, including exact row/sidecar bijection, duplicates,
   cache misses, duration sets, expected counts, label coverage, and item/cluster
   sets. Invalid negative data must suppress any safety conclusion.

## Bottom line

The two RTP exclusions are defensible for a clean OOC estimate, but they expose
a rule that must also disqualify the nominal 12 OOC items until their sung works
are identified. The present arm has neither valid OOC truth nor enough
independent power to police a +15pp harm. Repair and enlarge the negative arm,
preferably around the 30/300 endpoint contrast, before committing the combined
122 Whisper-hour run.
