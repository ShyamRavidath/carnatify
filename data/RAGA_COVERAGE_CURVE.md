# Raga coverage curve — what does widening the raga tier actually cost?

Executed 2026-08-13 against `WORKHORSE_RAGA_COVERAGE_BRIEF.md`. Read-only: no
retraining of production, nothing under `models/` written, no edit to
`identify_clip.py`, no edit to `data/raga_aliases.json`, no audio in
`~/sung_tests` opened. The readings were registered in
`data/raga_coverage/PREREGISTRATION.md` and **committed as their own commit
(`51065a2`) before the parameterised harness was committed (`93a49ef`) and
before a single fold was scored** — the ordering is in git history, not in file
mtimes.

Everything below is **source-disjoint (level (c))** unless it says otherwise.
**Exactly one thing moved: the tier constant `min_tracks`.** Features, taus,
`nb`, `sigma`, `alpha`, the forest, the splitter, the seed, the read-out and the
level-(c) group construction are byte-identical to
`data/RAGA_CONTAMINATION_AUDIT.md`'s harness.

**Headline: top-1 falls from 72.2% on 18 classes to 57.0% on 54, almost
perfectly log-linearly in class count (−13.8 pp per natural-log unit,
R² = 0.9997). But coverage more than doubles, so expected hits per 100 heard
concert items rises monotonically, 28.2 → 45.1, and does not peak in the middle.
The wide tier is worth 60% more correct answers per concert.**

---

## 0. The reproduction gate — passed on the exact integer counts, twice

Verbatim from `data/raga_coverage/gate_min25_default.log`, the bare default run:

```
REPRODUCTION GATE: level (a) = 72.8% / 84.7% vs recorded 72.8% / 84.7%  ->  EXACT
                   377/518 = 72.780%      439/518 = 84.749%
REPRODUCTION GATE: level (c) = 72.2% / 84.0% vs recorded 72.2% / 84.0%  ->  EXACT
                   374/518 = 72.201%      435/518 = 83.977%
```

Not "within ±0.5 pp" — the **same integer counts** as
`data/RAGA_CONTAMINATION_AUDIT.md` §1 and §3, 377/518 and 439/518 at level (a),
374/518 and 435/518 at level (c). Stronger than that: the default run rewrote
`data/raga_audit/levels.json` and `git diff` on it is **empty**. The
parameterisation is provably behaviour-preserving, not merely
number-preserving — levels (b) 371/518, (c′) 369/518 and the whole exposure
split came back byte-identical too.

### A second gate nobody registered, and it also passed

The sweep produced a check the brief did not ask for. The archived harness
`scratch_archive_0711/raga_final_eval.py` printed **two** recorded tiers:
`min>=25 ragas=18 top1=72.8% top3=84.7%` **and** `min>=20 ragas=32 top1=67.6%
top3=79.4%`. Only the first is the audit's gate. Running the parameterised
harness at `--min-tracks 20` returns level (a) = **558/826 = 67.6%** and
**656/826 = 79.4%**.

That matters more than a repeat of the same check: it verifies `--min-tracks` at
a tier **other than its default** against an independently recorded historical
figure. A parameterisation that silently ignored the argument would pass Gate 1
and fail this one.

---

## 1. n first — the tier inventory, and why the CIs behave the way they do

Registered before scoring, in `data/raga_coverage/PREREGISTRATION.md` §4. Corpus
after the frozen drops: **1,287 tracks with full melody, 87 ragas**. Provenance
gaps: `unresolved_contour = 0`, `unresolved_identifier = 0`.

| tier | classes | tracks | (a) groups | **(c) source groups** | min (c) groups/raga | folds used | majority-class floor | **class-prior floor** |
|---|---|---|---|---|---|---|---|---|
| `min>=25` | 18 | 518 | 518 | **155** | 13 | 5 | 0.0579 | **0.0557** |
| `min>=20` | 32 | 826 | 826 | **185** | 9 | 5 | 0.0363 | **0.0319** |
| `min>=15` | 44 | 1020 | 1020 | **198** | 9 | 5 | 0.0294 | **0.0240** |
| `min>=10` | 54 | 1139 | 1139 | **204** | 7 | 5 | 0.0263 | **0.0203** |

**No raga was dropped at any tier.** The minimum level-(c) group count per raga
is 7, above `n_splits = 5`, so the 5-fold split is valid throughout and all five
folds carry test tracks at every tier. This was registered as a check in advance
precisely so a silently degraded split could not be discovered afterwards.

**Groups grow sublinearly, and severely.** The 621 tracks added between
`min>=25` and `min>=10` bring only **49 new independent sources**: tracks ×2.20,
source groups ×1.32, tracks-per-group 3.3 → 5.6. The registered consequence —
"the confidence intervals will barely narrow as the tier widens" — is confirmed
below. **In the statistical sense this corpus is not 1,139 observations wide at
`min>=10`; it is 204 wide.**

The track counts differ by 1-2 from the brief's §0 table (827/1022/1141 there,
826/1020/1139 here) because the brief counted npz files and the harness applies
its frozen drops (`v.size < 500`, `tonic <= 0`, missing melodia). The harness's
counts are the ones every number here is computed on.

---

## 2. The curve

Level (c), source-disjoint. Uncertainty is a **cluster bootstrap over that
tier's own level-(c) source groups**, 2,000 replicates, `default_rng(42)`,
percentile interval — the method registered in advance and the same one
`data/RAGA_DURATION_CURVE.md` §1 used, because the tracks are not independent.

| tier | classes | tracks | (c) groups | **top-1** | 95% CI (cluster) | 95% CI (Wilson, too narrow) | **top-3** | 95% CI |
|---|---|---|---|---|---|---|---|---|
| `min>=25` | 18 | 518 | 155 | **374/518 = 72.2%** | 66.4 – 78.1% | 68.2 – 75.9% | 435/518 = 84.0% | 79.1 – 88.1% |
| `min>=20` | 32 | 826 | 185 | **529/826 = 64.0%** | 60.0 – 68.3% | 60.7 – 67.2% | 632/826 = 76.5% | 73.1 – 80.0% |
| `min>=15` | 44 | 1020 | 198 | **611/1020 = 59.9%** | 55.8 – 64.4% | 56.9 – 62.9% | 727/1020 = 71.3% | 68.1 – 75.3% |
| `min>=10` | 54 | 1139 | 204 | **649/1139 = 57.0%** | 52.7 – 61.7% | 54.1 – 59.8% | 812/1139 = 71.3% | 68.0 – 75.2% |

### Against the floors, which move faster than the score

The brief is right that the raw curve is uninterpretable on its own: the
class-prior floor falls 2.7× across the grid while top-1 falls 1.27×.

| tier | top-1 | class-prior floor | **top-1 − floor** | **top-1 ÷ floor** |
|---|---|---|---|---|
| `min>=25` | 72.2% | 0.0557 | 66.6 pp | **13.0×** |
| `min>=20` | 64.0% | 0.0319 | 60.9 pp | **20.1×** |
| `min>=15` | 59.9% | 0.0240 | 57.5 pp | **25.0×** |
| `min>=10` | 57.0% | 0.0203 | 54.9 pp | **28.1×** |

**In information terms the wide tier is by far the stronger classifier** — 28.1×
its chance floor against 13.0× — and it is solving a harder problem while doing
it. That is not an argument for shipping it; a listener does not experience
"×floor". It is an argument that the 15.2 pp fall is not a model falling apart.

### The shape: log-linear, and almost exactly so

Fitting top-1 on `ln(classes)` over the four registered tiers:

```
top-1 = 1.1205 − 0.1381 · ln(classes)      R² = 0.9997
residuals: +0.06, −0.16, +0.10, +0.00 pp
```

**−13.8 pp per natural-log unit of class count**, with residuals under a fifth of
a percentage point on all four tiers. The verifier seat's registered claim that
top-1 "falls roughly log-linearly in class count" is not merely right, it is
right to within noise — a doubling of the class count costs **9.6 pp**, wherever
you start. This is a usable extrapolation rule for any tier decision that is not
on the registered grid, and it is the one genuinely predictive object this job
produced.

### Confidence intervals barely narrow — the registered prediction, confirmed

| tier | tracks | (c) groups | cluster CI half-width | Wilson half-width | ratio |
|---|---|---|---|---|---|
| `min>=25` | 518 | 155 | **5.82 pp** | 3.85 pp | 1.51 |
| `min>=20` | 826 | 185 | **4.17 pp** | 3.27 pp | 1.27 |
| `min>=15` | 1020 | 198 | **4.27 pp** | 3.00 pp | 1.42 |
| `min>=10` | 1139 | 204 | **4.51 pp** | 2.87 pp | 1.57 |

Doubling the tracks buys **1.3 pp** of half-width, and the interval *widens*
again from `min>=20` to `min>=10` despite 313 more tracks, because only 19 more
sources came with them. A binomial interval on the track count would have shown a
tidy monotone narrowing (3.85 → 2.87 pp) and would have been wrong. **This is the
concrete cost of a corpus whose growth is in tracks rather than in sources**, and
it is the strongest argument in this document for the "more audio per class"
route: more *sources* per class would narrow every interval on this page.

---

## 3. Expected hits per 100 heard concert items — the product-relevant number

Coverage is the fraction of `data/scraped_compositions.json`'s 3,009
canonical-raga-carrying items whose raga the tier can even emit. Recomputed
independently for this job from the tier's own class lists
(`scripts/raga_coverage_mass.py`) and **reproducing the brief's §0 column
exactly**.

| tier | classes | repertoire coverage | top-1 | **expected top-1 hits / 100 items** | expected top-3 hits / 100 |
|---|---|---|---|---|---|
| `min>=25` | 18 | 39.1% (1176/3009) | 72.2% | **28.2** | 32.8 |
| `min>=20` | 32 | 59.6% (1794/3009) | 64.0% | **38.2** | 45.6 |
| `min>=15` | 44 | 70.9% (2134/3009) | 59.9% | **42.5** | 50.5 |
| `min>=10` | 54 | 79.2% (2383/3009) | 57.0% | **45.1** | 56.5 |

**It is not flat and it does not peak in the middle. It rises monotonically and
peaks at the widest tier measured.** `min>=10` delivers **+60% more correct raga
identifications per concert** than `min>=25` (45.1 vs 28.2), and **+72% on
top-3** (56.5 vs 32.8). The brief's expectation that this column "peaks
somewhere in the middle" is **refuted**; this seat's registered counter-prediction
that it would rise monotonically is confirmed.

The arithmetic behind why it was never close: for `min>=25` to win, `min>=10`
top-1 would have to fall below **35.6%**, and the measured value is 57.0% with a
lower CI bound of 52.7%. **The narrow tier is not on the efficient frontier at
all.** Even `min>=20` — the tier the product already exports — beats it by 35%.

**Three caveats travel with this table and none of them reverses it.** First,
repertoire mass is a prior over *scraped concert programmes*, which is the right
prior for a concert companion but is still a proxy. Second, it prices a miss and
a "raga not in vocabulary" identically at zero, and a listener may not: a wrong
raga name stated confidently is a worse failure than silence, which is exactly
the argument for the abstain gate in `HANDOFF_SESSION_0731.md` §6.3 and not an
argument for a narrow tier. Third, the coverage column is measured on the
*corpus's* label vocabulary; a raga in the tier can still be got wrong, which is
what the top-1 column already prices.

The wild-clip coverage column of the brief's §0 was also recomputed and **does
not reproduce**: the brief quotes 36/62/72/79% over 81 labelled clips, and this
recomputation finds 103 of 106 `~/sung_tests` clips carrying a filename label and
gets 28.2/48.5/56.3/62.1% over that denominator. The disagreement is a
denominator disagreement, it was recorded in the prereg **before** any score, and
it changes nothing here because the expected-hits column is computed on
repertoire mass as the brief specified. The wild labels are in any case unaudited
(`HANDOFF_SESSION_0731.md` §6.1).

---

## 4. Per-class top-1 at the widest tier

`min>=10`, 54 classes, level (c), sorted. `+` marks a class that does not exist
in the `min>=25` tier. `grp` is that class's level-(c) source-group count.

| raga | n | grp | top-1 | top-3 | | raga | n | grp | top-1 | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| `+`Saurāṣtraṁ | 13 | 11 | 92.3% | 92.3% | | `+`Dvijāvanti | 12 | 10 | 58.3% | 58.3% |
| `+`Gauḷa | 15 | 12 | 86.7% | 86.7% | | `+`Hindōḷaṁ | 24 | 20 | 58.3% | 79.2% |
| Tōḍi | 30 | 16 | 86.7% | 90.0% | | `+`Śrīranjani | 21 | 14 | 57.1% | 61.9% |
| Pūrvīkaḷyāṇi | 26 | 17 | 84.6% | 96.2% | | Sāvēri | 30 | 20 | 56.7% | 73.3% |
| `+`Bēgaḍa | 24 | 19 | 83.3% | 100.0% | | `+`Dhanyāsi | 23 | 13 | 56.5% | 56.5% |
| Kalyāṇi | 30 | 13 | 83.3% | 90.0% | | Harikāmbhōji | 29 | 21 | 55.2% | 72.4% |
| `+`Varāḷi | 21 | 15 | 81.0% | 90.5% | | `+`Śuddadhanyāsi | 15 | 10 | 53.3% | 53.3% |
| Mōhanaṁ | 30 | 22 | 80.0% | 86.7% | | `+`Madhyamāvati | 24 | 17 | 50.0% | 62.5% |
| `+`Rītigauḷa | 24 | 22 | 79.2% | 95.8% | | `+`Suraṭi | 18 | 13 | 50.0% | 55.6% |
| Aṭāna | 26 | 21 | 76.9% | 80.8% | | Karaharapriya | 27 | 19 | 48.1% | 70.4% |
| Kāmavardani | 30 | 20 | 73.3% | 83.3% | | `+`Sāma | 21 | 15 | 47.6% | 52.4% |
| Nāṭa | 30 | 22 | 73.3% | 80.0% | | `+`Ābhōgi | 13 | 12 | 46.2% | 76.9% |
| Śankarābharaṇaṁ | 30 | 19 | 73.3% | 83.3% | | `+`Puṇṇāgavarāḷi | 21 | 13 | **38.1%** | 52.4% |
| `+`Māyāmāḷavagauḷa | 11 | 10 | 72.7% | 90.9% | | `+`Kēdāragauḷa | 11 | 11 | **36.4%** | 54.5% |
| Bhairavi | 30 | 21 | 70.0% | 80.0% | | Vasanta | 28 | 21 | **35.7%** | 53.6% |
| Hamsadhvāni | 30 | 24 | 70.0% | 73.3% | | `+`Bṛndāvana sāranga | 12 | 9 | **33.3%** | 66.7% |
| Kamās | 29 | 20 | 69.0% | 89.7% | | `+`Cakravākaṁ | 15 | 12 | **33.3%** | 60.0% |
| Sindhubhairavi | 29 | 21 | 69.0% | 86.2% | | `+`Maṇirangu | 10 | 9 | **30.0%** | 80.0% |
| Ṣanmukhapriya | 29 | 24 | 69.0% | 72.4% | | `+`Jaganmōhini | 18 | 12 | **27.8%** | 55.6% |
| `+`Latāngi | 15 | 13 | 66.7% | 86.7% | | `+`Mukhāri | 15 | 11 | **26.7%** | 66.7% |
| `+`Behāg | 22 | 21 | 63.6% | 81.8% | | `+`Kāṁbhōji | 20 | 9 | **25.0%** | 60.0% |
| `+`Nīlāṁbari | 18 | 15 | 61.1% | 77.8% | | `+`Bilahari | 22 | 20 | **22.7%** | 50.0% |
| `+`Ānandabhairavi | 18 | 12 | 61.1% | 61.1% | | `+`Sahānā | 14 | 10 | **21.4%** | 50.0% |
| Kānaḍa | 25 | 19 | 60.0% | 76.0% | | `+`Jōnpuri | 17 | 12 | **17.6%** | 35.3% |
| `+`Kāpi | 20 | 13 | 60.0% | 70.0% | | `+`Haṁsānandi | 21 | 11 | **14.3%** | 33.3% |
| | | | | | | `+`Sencuruṭṭi | 12 | 7 | **8.3%** | 50.0% |
| | | | | | | `+`Janaranjani | 15 | 10 | **6.7%** | 6.7% |
| | | | | | | `+`Pūrṇacandrika | 15 | 12 | **6.7%** | 46.7% |
| | | | | | | `+`Nāṭakurinji | 11 | 8 | **0.0%** | 18.2% |

**The added classes are not uniformly weak.** Five of the ten best classes at
this tier — Saurāṣtraṁ 92.3%, Gauḷa 86.7%, Bēgaḍa 83.3%, Varāḷi 81.0%, Rītigauḷa
79.2% — are new, and Bēgaḍa is the only class on the whole list with a perfect
top-3. Six added classes beat the incumbent median of 70.0%. **Widening the tier does not mean adding 36
bad classes; it means adding 36 classes with a much wider quality spread than the
18 that were already there.**

### Classes below the class-prior floor — the case for a per-class threshold

The brief asks which classes fall below the class-prior floor (0.0203 at this
tier), because those "would be better dropped than kept". Exactly one does:

- **Nāṭakurinji, 0/11 top-1, 2/11 top-3.** Zero. Eleven tracks across eight
  independent sources and the model never once ranks it first, and ranks it in
  the top three under a fifth of the time. A 54-way classifier that never emits a
  class correctly is strictly worse than one that does not have it: the class
  costs its own 11 tracks *and* whatever it steals from the classes it is
  confused with.

Three more sit in the same neighbourhood — Janaranjani 6.7%, Pūrṇacandrika 6.7%,
Sencuruṭṭi 8.3% — all above the floor but so far below the rest that they are
functionally noise. **The right lever here is per-class, not global.** A global
`min_tracks` cannot separate Saurāṣtraṁ (13 tracks, 92.3%) from Nāṭakurinji (11
tracks, 0.0%); a per-class admission rule fitted on held-out per-class accuracy
can. Dropping the four sub-10% classes would remove 50 near-certain errors from 53
tracks and cost 117 of 3,009 repertoire items, taking coverage from 79.2% to
75.3% — **3.9 pp**, which is more repertoire mass than their track counts suggest
and is the reason this has to be measured rather than assumed. On expected hits
it is roughly a wash; on "how often does it state a raga that is wrong" it is a
clear improvement. **That is the single most actionable thing
in this document**, and it is a follow-on measurement, not a claim: nothing here
was scored with any class dropped.

### The sub-40% tail — the verifier's third prediction, refuted on its own terms

| tier | classes below 40% top-1 | errors they carry | share of all top-1 errors |
|---|---|---|---|
| `min>=25` | 1 (Vasanta) | 18 / 144 | 12.5% |
| `min>=20` | 5 | 79 / 297 | 26.6% |
| `min>=15` | 9 | 135 / 409 | 33.0% |
| `min>=10` | **17** | 212 / 490 | **43.3%** |

The tail is real and it grows exactly as predicted — 1 class at `min>=25`, 17 at
`min>=10`. But the registered operationalisation of "carry most of the loss" was
**more than half of all top-1 errors**, and they carry **43.3%**. The majority of
the damage is spread across the 37 classes *above* 40%, not concentrated in the
tail. Refuted, narrowly, on a criterion fixed before the number existed.

### Vasanta, the registered watch

**35.7% at every single tier** — 10/28, identical at `min>=25`, `min>=20`,
`min>=15` and `min>=10`, and 36.9% at 60 s in the duration curve. Adding 36
competing classes does not cost Vasanta one further track. The registered
prediction ("below 45% at every wider tier") holds, and the invariance is a
stronger statement than the prediction was: **whatever is wrong with Vasanta is
intrinsic to the class, not a function of how much competition it has.**

---

## 5. The crux — do the added classes poison the 18 that were already there?

Paired at the track level on the **518 tracks of the `min>=25` tier**, level (c)
correctness at the narrow tier against level (c) correctness at each wider tier.
McNemar exact, two-sided binomial on the discordant pairs.

| tier | classes | top-1 on those 518 | delta | `b` (right at 25, wrong here) | `c` (wrong at 25, right here) | **McNemar exact p** |
|---|---|---|---|---|---|---|
| `min>=25` | 18 | 374/518 = 72.2% | — | — | — | — |
| `min>=20` | 32 | 361/518 = 69.7% | **−2.5 pp** | 22 | 9 | **0.0295** |
| `min>=15` | 44 | 358/518 = 69.1% | **−3.1 pp** | 28 | 12 | **0.0166** |
| `min>=10` | 54 | 356/518 = 68.7% | **−3.5 pp** | 31 | 13 | **0.0096** |

**The poisoning is real, statistically significant, monotone in tier width — and
small.** Going from 18 classes to 54 costs the incumbent classes **3.5
percentage points, 18 net tracks of 518**, with `p = 0.0096`. The direction and
the significance were registered in advance and are confirmed; the **magnitude
was registered as 5-12 pp and is refuted** — it is 3.5, closer to the "under
2 pp, the added classes are cheap" end of the registered scale than to the "over
15 pp, the narrow tier is protecting the incumbents materially" end.

The registered caveat stands and matters: **the pairing is exact at the track
level but not at the fold level.** `StratifiedGroupKFold` sees a different row
set at each tier, so a track's fold assignment and its training partners differ
between tiers, and some part of the 31 and the 13 is re-randomised fold
membership rather than added classes. The 13 wrong→right flips are the visible
evidence of that noise floor — they cannot be caused by adding competitors. So
**`p = 0.0096` is an upper bound on the evidence, not a clean causal test**, and
the honest reading is "a real effect of roughly 3.5 pp, of which some unknown
minority is fold churn".

### Where the accuracy actually goes

| tier | the incumbent 518 tracks | the added tracks | all tracks |
|---|---|---|---|
| `min>=25` | 374/518 = 72.2% | — | 374/518 = 72.2% |
| `min>=20` | 361/518 = 69.7% | 168/308 = **54.5%** | 529/826 = 64.0% |
| `min>=15` | 358/518 = 69.1% | 253/502 = **50.4%** | 611/1020 = 59.9% |
| `min>=10` | 356/518 = 68.7% | 293/621 = **47.2%** | 649/1139 = 57.0% |

**Most of the 15.2 pp fall is composition, not damage.** The incumbents lose
3.5 pp; the aggregate loses 15.2 pp because 55% of the tracks at `min>=10` are
now classes that score 47.2%. This is the decomposition the brief asked for and
it lands on the cheap side of the brief's own distinction: *"added classes that
only cost their own accuracy are cheap; added classes that poison the existing 18
are not."* They mostly cost their own accuracy.

And 47.2% on the added classes is not a bad number in absolute terms. At
`min>=10` the class-prior floor is 0.0203, so the added classes alone are running
at **23× chance** on a 54-way problem, on unseen sources.

### The contamination audit's "the levels are not distinguishable" is tier-specific

This was not asked for and is the most important incidental finding here.

| tier | level (a) | level (c) | **(a) → (c)** | clustered-track (a)→(c) delta |
|---|---|---|---|---|
| `min>=25` | 377/518 = 72.8% | 374/518 = 72.2% | **−0.6 pp** | −1.2 pp (n=243) |
| `min>=20` | 558/826 = 67.6% | 529/826 = 64.0% | **−3.5 pp** | −8.0 pp (n=386) |
| `min>=15` | 647/1020 = 63.4% | 611/1020 = 59.9% | **−3.5 pp** | −10.8 pp (n=472) |
| `min>=10` | 702/1139 = 61.6% | 649/1139 = 57.0% | **−4.7 pp** | −11.8 pp (n=510) |

`data/RAGA_CONTAMINATION_AUDIT.md` §3 concluded that "the levels are not
distinguishable from each other" — spread 1.6 pp over four levels, about eight
tracks. **That conclusion is true at `min>=25` and false everywhere else.** At
the exported model's own tier, `min>=20`, source-disjointness costs **3.5 pp,
six times as much**, and among tracks sharing a same-raga source cluster it costs
**8.0 pp** against 1.2 pp at the narrow tier — rising to 11.8 pp at `min>=10`.

The mechanism is legible: the narrow tier's 18 classes are the best-sampled ones,
with 155 sources for 518 tracks; the classes added below `min_tracks = 25` are
precisely the ones whose tracks come disproportionately from few uploads, so
filename-level grouping leaks much more on them. **A source-disjoint protocol is
not optional at a wide tier**, and any future number quoted at `min>=20` or wider
that was measured at level (a) is inflated by 3.5-4.7 pp.

This also gives the **exported** model's tier a source-disjoint figure for the
first time. `models/raga_v3_*` is trained at `min_tracks >= 20`, 32 classes, and
its `cv_note` has carried the 18-class `72.8/84.7` (already known to be
mislabelled as to arm). The honest TDMS-only, source-disjoint number for the
exported tier is **64.0% top-1 / 76.5% top-3**.

---

## 6. Where this lands on the fixed interpretation table

The table is fixed on **level (c), top-1, at `min>=10` (54 classes)**:
**57.0% (649/1139, 95% CI 52.7 – 61.7%)**. That is the middle row:

> **top-1 50-60%** — *a real but payable trade; decide on expected
> hits-per-concert-item, not on top-1.*

Decided on expected hits per 100 items, as that row instructs, the trade is not
close: **45.1 against 28.2**, a 60% increase, monotone across the whole grid,
with the peak at the widest tier measured and no evidence of a turn. The CI on
`min>=10` top-1 (52.7 – 61.7%) would have to be wrong by 17 pp at its lower bound
before `min>=25` caught up.

The row's own qualification is the part to carry forward: **"a wrong raga name
shown confidently is a different failure from silence, and the decision then
belongs with an abstain gate, not with this table."** That is unchanged and this
document does not resolve it. What this document does establish is that the
narrow tier is **not** the way to buy that safety — it buys it by refusing to
answer on 61% of the repertoire, silently and unconditionally, including on the
classes it would have got right.

**The verdict on what to do with this belongs to the verifier seat.** This
document states the measurement and the row.

---

## 7. Registered predictions, scored

### The verifier seat's prediction (brief §2.2)

> *top-1 falls roughly log-linearly in class count and lands near 63-65% at
> `min>=15` (44 classes) and 58-61% at `min>=10` (54 classes); the `min>=10` tier
> will show a long tail of classes below 40% that carry most of the loss.*

| part | registered | measured | verdict |
|---|---|---|---|
| shape: log-linear in class count | "roughly" | −13.8 pp per ln-unit, R² = 0.9997, max residual 0.16 pp | **confirmed, and far more exactly than "roughly"** |
| level at `min>=15` | 63-65% | **59.9%** [55.8, 64.4] | **refuted** — 3.1 pp below the band, though the CI still contains it |
| level at `min>=10` | 58-61% | **57.0%** [52.7, 61.7] | **refuted** — 1.0 pp below the band, though the CI still contains it |
| a long tail below 40% exists | yes | 17 classes, up from 1 | **confirmed** |
| the tail carries most of the loss | > 50% of errors (registered operationalisation) | **43.3%** | **refuted** |

The shape was right and the level was consistently ~2-3 pp optimistic. Both level
misses are point-estimate misses that the cluster CIs do not exclude, and both
are recorded as refutations anyway, because the prereg fixed the bands before the
numbers existed and moving them afterwards is exactly the failure mode this
series exists to avoid.

### This seat's own registered predictions (prereg §7.2)

| # | registered | measured | verdict |
|---|---|---|---|
| 1 | CI half-width at `min>=10` no more than ~2 pp narrower than at `min>=25` | 4.51 vs 5.82 pp — 1.31 pp narrower, and *wider* than `min>=20` | **confirmed** |
| 2 | McNemar `b > c`, p < 0.05, net loss **5-12 pp** | b=31, c=13, p=0.0096, net **−3.5 pp** | **direction and significance confirmed; magnitude refuted** — below the band, i.e. the added classes are cheaper than expected |
| 3 | expected hits rises monotonically and peaks at `min>=10`, contradicting the brief's "peaks in the middle" | 28.2 → 38.2 → 42.5 → **45.1** | **confirmed; the brief's expectation is refuted** |
| 4 | Vasanta stays below 45% at every wider tier | 35.7% at all four tiers, exactly | **confirmed** |

---

## 8. Scope — what this does not establish

- **It does not retrain or graduate anything.** Nothing under `models/` was
  written, `identify_clip.py` was not touched, `data/raga_aliases.json` was read
  but never modified, `~/sung_tests` audio was never opened.
  `~/sung_tests --cache-v2` remains the only scoreboard.
- **This is the TDMS-only primary arm**, the configuration that produced the
  historical number, not the fused configuration that is exported
  (`P = 0.6·P_tdms + 0.4·P_hist`). The audit found fusion scores ~1.4 pp higher
  at level (c) on the 18-class tier. Whether fusion's advantage holds, grows or
  shrinks with tier width is **not measured here**.
- **Full-recording only.** `data/RAGA_DURATION_CURVE.md` measured a 11.8 pp
  [8.0, 15.8] cost at 60 s on the 18-class tier. Whether that cost compounds with
  tier width — the two-way interaction — is untested, and a companion working on
  minute-scale audio at 54 classes has **no measurement at all** in this repo.
- **Corpus, not field.** `data/RAGA_WILD_MEASUREMENT.md`'s 55.2% [37.5, 71.6] is
  the only field number and it was measured on the 18-class tier's 29 in-tier
  clips. A wider tier would put more wild clips in scope (62.1% of the labelled
  clips at `min>=10` against 28.2% at `min>=25`, on this document's denominator)
  but nothing here says what the field accuracy on them would be.
- **The level-(c) artist merge is partial** on the archive side, inherited
  unchanged from the audit, so source-disjointness is an upper bound on the truth
  and never a lower one — equally at every tier, so the *comparisons* between
  tiers are unaffected.
- The four tiers were fixed in the brief before any score. No intermediate tier
  was added after seeing the curve; the log-linear fit is offered for
  interpolation and is not a measurement at any unmeasured tier.
- **Nothing here reopens the composition doors.** No number in this document may
  be quoted as evidence about the lyrics-ASR, Qmax or CSI paths in either
  direction.

## 10. Follow-up A — the within-class learning curve: is `r = 0.519` a confound?

Added 2026-08-13 at the verifier seat's request. Registered in
`data/raga_coverage/PREREGISTRATION_FOLLOWUP.md` §A and **committed (`87bfb42`)
before either scoring script existed**. §§1-9 above are unchanged.

### 10.1 Why the cross-class correlation could not settle it

`data/RAGA_CEILING_EVALUATION.md` reports `r(tracks, top-1) = 0.519`
(`p = 5.8e-05`, `n = 54`) across the 54 classes, monotone in bins: 39.9%
(10-14 tracks) → 41.5% (15-19) → 52.6% (20-24) → 68.6% (25-30). It cannot be
read as "audio buys accuracy", because the 25-30 bin is exactly the set
`scratch_archive_0711/dl_deficits30.py` topped up as `PRIORITY_20` /
`SECONDARY_20` / `TOPUP_30` — the popular, canonical, well-recorded ragas. Track
count and "easy to classify" are entangled through popularity, and §4 above
already contains the counterexamples: Saurāṣtraṁ 92.3% on 13 tracks,
Nāṭakurinji 0.0% on 11.

**The within-class test breaks the confound by comparing every class against
itself.** The 54-class tier is held fixed (the class set is computed on full,
uncapped level-(a) counts and never moves), and every class is subsampled to at
most `c` tracks. Each class's tracks are permuted once per seed and cap `c` takes
the first `c`, so `c=10 ⊂ c=15 ⊂ … ⊂ c=30` and the arms are paired by
construction. Three cap seeds (0, 1, 2), all reported.

**Gate A, registered in advance and passed.** No class in the corpus has more
than 30 tracks, so `c = 30` is the whole tier and must reproduce the committed
`min>=10` result exactly. It does, for all three seeds:
`649/1139 = 57.0%` top-1, `812/1139 = 71.3%` top-3, `PASS [True, True, True]`.

### 10.2 The curve

Mean over the three cap seeds, level (c) source-disjoint, `[min-max]` across
seeds. **Read-out (ii), the 18 classes with ≥ 25 tracks, is primary** — the
classifier stays the full 54-way problem at every cell and only the evaluation
set is restricted, because only those classes vary across the whole range.

| cap `c` | tracks | (c) groups | **(ii) restricted-18 top-1** | seed spread | (ii) top-3 | (i) all-54 top-1 |
|---|---|---|---|---|---|---|
| 10 | 540 | 146-152 | **50.4%** [45.0 – 55.6] | 10.6 pp | 66.7% | 46.4% [43.5 – 48.0] |
| 15 | 779 | 174-180 | **57.8%** [54.8 – 61.1] | 6.3 pp | 73.6% | 52.4% [50.2 – 54.4] |
| 20 | 953 | 190-191 | **64.1%** [60.8 – 66.1] | 5.3 pp | 75.6% | 55.4% [54.6 – 55.9] |
| 25 | 1071 | 199-201 | **66.5%** [65.1 – 68.2] | 3.1 pp | 78.4% | 56.4% [55.8 – 56.8] |
| **30** | **1139** | **204** | **68.7%** (all seeds) | 0.0 pp | 79.9% | **57.0%** (all seeds) |

**Total rise `c=10 → c=30`: +18.4 pp on the restricted-18, +10.6 pp on all 54.**

Steps: **+7.4, +6.3, +2.4, +2.2 pp**. Seed spread falls monotonically, 10.6 → 6.3
→ 5.3 → 3.1 → 0.0 pp, exactly as registered — at `c = 10` two thirds of some
classes are thrown away and one draw is genuinely noisy, which is why three seeds
were registered rather than one.

### 10.3 The deceleration is in cap-space, not in track-space

The step sizes shrink, which looks like saturation. It mostly is not. **Each cap
step adds fewer tracks than the last**, because fewer classes are still truncated
— 53 classes are truncated at `c=10` but only 17 at `c=25`. Normalising:

| step | tracks added | rise | **pp per 100 tracks added** |
|---|---|---|---|
| 10 → 15 | +239 | +7.4 pp | **3.10** |
| 15 → 20 | +174 | +6.3 pp | **3.62** |
| 20 → 25 | +118 | +2.4 pp | **2.07** |
| **25 → 30** | **+68** | **+2.2 pp** | **3.25** |

**Per track added, the marginal value at the top of the range is the same as at
the bottom.** There is no saturation signal in this corpus at all: the last 68
tracks bought 3.25 pp per hundred, the first 239 bought 3.10. The apparent
flattening is an artifact of plotting against the cap rather than against the
data actually added.

### 10.4 Per-class slopes — and the finding that inverts the fetch priority

Mean over seeds, restricted-18, sorted by `c=10 → c=30` gain:

| class | c=10 | c=20 | c=25 | c=30 | **10→30** | 25→30 |
|---|---|---|---|---|---|---|
| Bhairavi | 20.0 | 48.3 | 54.7 | 70.0 | **+50.0** | +15.3 |
| Kānaḍa | 20.0 | 46.7 | 62.7 | 60.0 | **+40.0** | −2.7 |
| Ṣanmukhapriya | 36.7 | 65.0 | 66.7 | 69.0 | **+32.3** | +2.3 |
| Karaharapriya | 20.0 | 43.3 | 46.7 | 48.1 | **+28.1** | +1.5 |
| Kāmavardani | 46.7 | 66.7 | 73.3 | 73.3 | **+26.7** | −0.0 |
| Sindhubhairavi | 43.3 | 65.0 | 68.0 | 69.0 | **+25.6** | +1.0 |
| Harikāmbhōji | 30.0 | 48.3 | 48.0 | 55.2 | **+25.2** | +7.2 |
| Kamās | 46.7 | 66.7 | 72.0 | 69.0 | **+22.3** | −3.0 |
| Aṭāna | 60.0 | 71.7 | 73.3 | 76.9 | +16.9 | +3.6 |
| Śankarābharaṇaṁ | 56.7 | 63.3 | 70.7 | 73.3 | +16.7 | +2.7 |
| Pūrvīkaḷyāṇi | 70.0 | 83.3 | 82.7 | 84.6 | +14.6 | +1.9 |
| Tōḍi | 73.3 | 83.3 | 80.0 | 86.7 | +13.3 | +6.7 |
| Nāṭa | 60.0 | 75.0 | 78.7 | 73.3 | +13.3 | −5.3 |
| Vasanta | 30.0 | 33.3 | 30.7 | 35.7 | +5.7 | +5.0 |
| Mōhanaṁ | 76.7 | 86.7 | 80.0 | 80.0 | +3.3 | +0.0 |
| Kalyāṇi | 83.3 | 78.3 | 81.3 | 83.3 | **+0.0** | +2.0 |
| Sāvēri | 60.0 | 55.0 | 56.0 | 56.7 | **−3.3** | +0.7 |
| Hamsadhvāni | 73.3 | 73.3 | 72.0 | 70.0 | **−3.3** | −2.0 |

Three classes have a non-positive `c=10 → c=30` slope, exactly the "at least 3"
registered in advance. **n is not destiny inside a class either.**

**The pattern is the actionable finding, and it inverts what the fetcher did.**
Correlating each class's accuracy at `c = 10` against its gain from tripling its
data: **`r = −0.777`, `p = 1.5e-04`** (Spearman −0.804, `p = 5.8e-05`).

- classes **below** 50% at `c = 10` gain **+28.4 pp** on average;
- classes **above** 50% at `c = 10` gain **+7.9 pp**.

Kalyāṇi, Mōhanaṁ, Hamsadhvāni and Tōḍi are already saturated at 10-15 tracks;
Bhairavi goes 20.0% → 70.0%. **`dl_deficits30.py` topped up the popular classes,
which are precisely the ones with nothing left to gain.** The audio is worth
three to four times as much per track when it is spent on a class the model is
currently bad at.

Vasanta is the exception that proves it is not a rule: weak *and* flat (+5.7 pp
over a tripling), consistent with §4 above and with the duration curve. Vasanta's
problem is not data volume.

### 10.5 Where this lands on the registered decision table

Registered thresholds: "still climbing at `c=30`" requires the `c=25→30` step
≥ 1.5 pp **and** the `c=20→30` step ≥ 3 pp. Measured: **+2.2 pp** and
**+4.6 pp**. Both clear. The row is:

> **still climbing at `c=30`** — *the corpus is under a collection cap that is
> costing real accuracy. The fetch is the best-value job on the board, and the
> fetch target should go above 30.*

**`r = 0.519` is confounded but the conclusion it pointed at survives the
deconfounding.** Within-class, holding popularity and recording quality fixed,
tripling a class's audio is worth **+18.4 pp**, and the marginal track at the
30-track cap is worth as much as the marginal track at 10.

Two qualifications, both registered before the numbers. First, the cap applies to
**every** class at once, so this measures "what happens if the whole corpus
deepens" — which is the fetch decision as it would actually be executed — and not
the pure own-data effect for one class. Second, only 17 of the 18 classes have
more than 25 tracks and only 9 have 30, so the `c=25 → c=30` segment moves less
data than any other and is the least well determined point on the curve. Both are
reasons to treat +2.2 pp as an estimate with real uncertainty, not to discount the
direction.

### 10.6 Predictions, scored

| prediction | registered | measured | verdict |
|---|---|---|---|
| **verifier:** total rise `c=10→30` on read-out (ii) | 6-12 pp | **+18.4 pp** | **refuted** — the within-class curve is *steeper* than the "much flatter" expectation |
| **verifier:** visibly flattening by `c=25`, operationalised as the `25→30` step being under half the `15→20` step | yes | 2.2 vs 6.3/2 = 3.15 → **yes** | **confirmed** in cap-space — but §10.3 shows it is not flattening per track added |
| **this seat:** total rise 13-20 pp | 13-20 pp | **+18.4 pp** | **confirmed** |
| **this seat:** `25→30` step ≥ 1.5 pp, i.e. the curve is not flat at the top | ≥ 1.5 pp | **+2.2 pp** | **confirmed** |
| **this seat:** and therefore the verifier's "visibly flattening" is wrong | — | flattening in cap-space, flat in neither per-track nor decision terms | **refuted as stated** — both readings are true of different x-axes and mine was the sloppier claim |
| **this seat:** all-54 rise smaller than restricted-18 | smaller | +10.6 vs +18.4 pp | **confirmed** |
| **this seat:** ≥ 3 of 18 classes with non-positive slope | ≥ 3 | exactly 3 | **confirmed** |
| **this seat:** seed spread widest at `c=10`, falling monotonically | yes | 10.6 → 6.3 → 5.3 → 3.1 → 0.0 | **confirmed** |

---

## 11. Follow-up B — pricing per-class admission

Registered in `data/raga_coverage/PREREGISTRATION_FOLLOWUP.md` §B, committed
before the scorer existed. §4 above argues that a global `min_tracks` cannot
separate Saurāṣtraṁ (13 tracks, 92.3%) from Nāṭakurinji (11 tracks, 0.0%) and
that the lever is per-class admission. **This prices that argument, and it does
not survive.**

### 11.1 The trap, and how it was avoided

Selecting classes on the same folds you then score on is selection on noise: with
10-30 tracks per class a class's measured top-1 has a standard error of 9-15 pp,
so thresholding keeps whichever classes got lucky. The primary arm is therefore
**nested** — the outer fold assignment is the committed `min>=10` level-(c) split
(computed once, identical at every threshold, so two thresholds cannot differ by
fold churn), and for each outer fold the admitted set comes from an **inner**
5-fold group CV over that fold's *training rows only*. The selection for a fold
never sees the fold.

**Gate B, registered in advance and passed.** At `t = 0` every class is admitted
and both arms must collapse to the plain 54-class tier: `649/1139` top-1 and
`812/1139` top-3. `PASS`.

### 11.2 The result

| `t` | arm | classes admitted | coverage | top-1 | top-3 | **expected hits / 100** |
|---|---|---|---|---|---|---|
| 0.00 | **nested** | 54.0 [54-54] | 79.2% | 649/1139 = 57.0% | 71.3% | **45.1** |
| 0.10 | **nested** | 47.2 [46-49] | 72.6% | 618/1030 = 60.0% | 74.2% | **43.6** |
| 0.20 | **nested** | 44.0 [43-45] | 69.4% | 598/969 = 61.7% | 74.9% | **42.8** |
| 0.30 | **nested** | 41.2 [39-44] | 66.9% | 585/929 = 63.0% | 76.6% | **42.1** |
| 0.40 | **nested** | 37.2 [35-41] | 62.2% | 543/851 = 63.8% | 76.7% | **39.6** |
| 0.10 | *in-sample bound* | 50.0 [50-50] | 75.3% | 59.2% | 73.4% | *44.6* |
| 0.20 | *in-sample bound* | 48.0 [48-48] | 73.7% | 60.5% | 74.3% | *44.6* |
| 0.30 | *in-sample bound* | 43.0 [43-43] | 66.7% | 64.4% | 77.1% | *42.9* |
| 0.40 | *in-sample bound* | 37.0 [37-37] | 62.1% | 68.2% | 79.7% | *42.3* |

**No threshold beats `t = 0`. Per-class admission does not beat the best global
`min_tracks`; it is strictly worse at every threshold tested**, monotonically:
45.1 → 43.6 → 42.8 → 42.1 → 39.6. Compared against the exported model's tier
(`min>=20`, 38.2), only the most aggressive admission is worse.

The mechanism is arithmetic, and it is the same one that killed the narrow tier
in §3: **dropping a class costs its repertoire mass immediately and buys accuracy
only slowly.** At `t = 0.10` the honest arm drops ~7 classes, loses 6.6 pp of
coverage and gains 3.0 pp of top-1 — and 0.726 × 0.600 < 0.792 × 0.570.

This also puts a measured number on §4's estimate that dropping the four sub-10%
classes would be "roughly a wash": measured with honest selection it is **−1.5
expected hits per 100**. Slightly worse than a wash, and §4's wording was
optimistic.

### 11.3 The selection-on-noise effect, isolated

At `t = 0.40` the two arms admit **the same number of classes at the same
coverage** — 37.2 classes / 62.2% nested, 37.0 / 62.1% in-sample — and report:

| arm | classes | coverage | top-1 |
|---|---|---|---|
| nested (honest) | 37.2 | 62.2% | **63.8%** |
| in-sample (bound) | 37.0 | 62.1% | **68.2%** |

**4.4 pp of pure selection-on-noise inflation, at matched coverage and matched
class count.** Anything that picks classes on measured per-class accuracy and
reports that same accuracy is overstating by about that much on this corpus. This
is the deliverable of Job B whichever way the headline landed.

The instability is visible directly. At `t = 0.20` the nested arm ever admits 51
classes, and **15 of them flip in and out across the five outer folds** —
Jōnpuri, Pūrṇacandrika and Sencuruṭṭi are admitted in 1 fold of 5; Cakravākaṁ,
Dvijāvanti, Mukhāri and Śuddadhanyāsi in 4 of 5. The in-sample arm, by
construction, admits an identical set every time and looks perfectly stable. That
apparent stability is the illusion.

### 11.4 What per-class admission *does* buy

It is not worthless — it is just not an expected-hits lever. Along the honest
arm, **accuracy-when-it-speaks rises from 57.0% to 63.8% while coverage falls
79.2% → 62.2%.** That is a precision/coverage trade, and it is the same axis as
the abstain gate in `HANDOFF_SESSION_0731.md` §6.3. Expected hits prices a wrong
answer at zero, not at negative, so it is by construction blind to the thing
admission is actually for.

And the extreme case does work. At `t = 0.10` exactly three classes are **never**
admitted in any of the five folds — **Nāṭakurinji, Janaranjani and Haṁsānandi** —
which are three of the four §4 named as functionally noise. **A per-class rule
identifies the genuinely dead classes stably; it is the marginal decisions, in the
20-40% band, that are noise.** The defensible version of §4's recommendation is
therefore narrow: drop the handful of classes that are stably near-zero out of
sample, and do **not** run a threshold sweep as a tuning knob.

### 11.5 Predictions, scored

| prediction | registered | measured | verdict |
|---|---|---|---|
| honest gain over the best global tier | 0 to +3 hits/100 (hedged: "possibly no threshold beats `t = 0`") | **−1.5 to −5.5** | **refuted** — the band excluded negatives; the hedge covered the outcome but the band is what was registered |
| in-sample arm inflated by ≥ 2 hits/100 at the threshold that maximises it | ≥ 2 | +1.0 at `t=0.10`, +1.8 at `t=0.20`, **+2.7 at `t=0.40`** | **refuted as stated** — the inflation is real but shows up in *top-1* (+4.4 pp at matched coverage), not in expected hits |
| optimum at `t = 0.10` or `0.20` | low but non-zero | **`t = 0`** | **refuted** |
| admitted count varies by ≥ 4 across folds at `t = 0.30` | ≥ 4 | **5** (39-44) | **confirmed** |

---

## 12. What the two follow-ups jointly say

`data/RAGA_CEILING_EVALUATION.md` frames the product constraint as: the model
cannot **name** 40-60% of what a listener hears, and wild audio costs
approximately nothing. Against that frame:

1. **More classes is a real lever and it is cheap.** §3: expected hits rise
   monotonically to 45.1 at 54 classes, and the incumbents pay only 3.5 pp (§5).
2. **More audio per class is *also* a real lever, and the confound did not
   explain it away.** §10: +18.4 pp within-class from 10 to 30 tracks, with the
   marginal track at the cap worth as much as the marginal track at the floor.
   **The fetch is worth doing.**
3. **But spend it on the weak classes, not the popular ones.** §10.4: `r = −0.777`
   between a class's current accuracy and what more audio buys it. This is the
   one place where a scarce-hours decision changes on this evidence.
4. **Per-class admission is not the lever §4 suggested it was.** §11: it loses
   expected hits at every threshold, and selecting on measured per-class accuracy
   inflates the reported number by 4.4 pp. Keep only the narrow version — drop
   classes that are stably near-zero out of sample.

**The verdict on what to fund belongs to the verifier seat.** These sections state
the measurements and the rows they land on.

---

## 9. Artifacts

| file | what |
|---|---|
| `data/raga_coverage/PREREGISTRATION.md` | readings, interpretation table, predictions and analysis choices, committed (`51065a2`) before the harness commit and before any fold |
| `scripts/raga_audit_levels.py` | the audit harness, with `MIN` reachable as `--min-tracks`; default behaviour byte-identical |
| `scripts/raga_coverage_mass.py` | the coverage axis from `data/scraped_compositions.json` and `~/sung_tests` filenames |
| `scripts/raga_coverage_curve.py` | curve, cluster bootstrap, expected hits, per-class table, McNemar — arithmetic only, refits nothing |
| `data/raga_coverage/inventory.json` | pre-score tier inventory: classes, tracks, groups per raga, floors |
| `data/raga_coverage/coverage.json` | repertoire and wild coverage per tier |
| `data/raga_coverage/levels_min{25,20,15,10}.json` | per-tier level (a)/(c) results **with per-track correctness and level-(c) group ids** |
| `data/raga_coverage/curve.json` | every table in this document, machine-readable |
| `data/raga_coverage/*.log` | raw run output, including the reproduction gate verbatim |
| `data/raga_coverage/PREREGISTRATION_FOLLOWUP.md` | Jobs A and B registered and committed (`87bfb42`) before either scorer existed |
| `scripts/raga_coverage_matrix.py` | the feature matrix and level-(c) groups, built once through the gated harness's own `collect`/`build` and cached |
| `scripts/raga_coverage_within_class.py` | Job A — nested per-class subsampling, three cap seeds, Gate A |
| `scripts/raga_coverage_admission.py` | Job B — nested and in-sample admission arms, Gate B |
| `data/raga_coverage/within_class.json`, `admission.json` | every cell of both follow-ups, written after each cell |
