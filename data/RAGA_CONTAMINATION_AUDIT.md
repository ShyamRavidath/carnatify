# Raga contamination audit — how much of 72.8% / 84.7% survives disjointness

Executed 2026-07-30 against `WORKHORSE_RAGA_AUDIT_BRIEF.md`. Read-only: no
retraining of production, nothing under `models/` written, no edit to
`identify_clip.py`. The readings were registered in
`data/raga_audit/PREREGISTRATION.md` and **committed** (`ec3578d`, addendum
`b21a687`) before the first fold was scored — the ordering is in git history,
not in file mtimes.

Started by the Opus 5 workhorse, which reached the addendum and the fusion arm
before terminating on a session limit. The primary arm and this write-up were
completed from the workhorse's own committed scripts by the verifier seat.

**Headline: 72.8% → 72.2%. The raga number is not contaminated.**

---

## 1. The reproduction gate — passed exactly, and the brief was wrong about why

The brief asserted that the CV harness which produced 72.8% / 84.7% was never
committed, on the strength of `git log --all -S"72.8" -- '*.py'` returning only
the commit that added the docstring note. **That inference was wrong.** The
search finds files that *hardcode* the string; the harness *computes* it.

`scratch_archive_0711/raga_final_eval.py` (commit `c1fca59`) is the harness. Run
verbatim it prints both recorded tiers, both metrics, exact:

```
final multi-tau     min>=20 ragas=32 top1=67.6% top3=79.4%
final multi-tau     min>=25 ragas=18 top1=72.8% top3=84.7%
```

`scripts/raga_audit_levels.py` is that harness with **exactly one thing
changed** — the `groups=` argument handed to `cv.split`. Feature code, tier,
forest (`RandomForestClassifier(800, 'sqrt', random_state=42)`), splitter
(`StratifiedGroupKFold(5, shuffle=True, random_state=42)`) and per-track
posterior read-out are byte-faithful. Level (a) returns:

```
REPRODUCTION GATE: level (a) = 72.8% / 84.7% vs recorded 72.8% / 84.7%  ->  EXACT
                   377/518 = 72.780%      439/518 = 84.749%
```

Not "within ±2pp" — the same integer counts. Every delta below is therefore
measured off a baseline that is the original measurement, not an approximation
of it. This is the guarantee the Qmax internal arm could not offer.

### Side finding: the exported model's `cv_note` is mislabelled

The harness is **multi-tau TDMS alone, one feature row per track, no histogram
fusion**. But `train_raga_v3_tdms.py` and `models/raga_v3_meta.json` attach
`'grouped 5-fold track-level 2026-07-08: min>=25 72.8/84.7'` to the *fused*
exported model (`P = 0.6*P_tdms + 0.4*P_hist`). A TDMS-only score is stapled to
a fusion model. The direction is harmless — fusion scores higher, not lower —
but the label is wrong and should be corrected in both files.

---

## 2. Two arms, because two things are worth knowing

| arm | what it is | why it is here |
|---|---|---|
| **primary** | multi-tau TDMS only, `raga_final_eval.py` config | the configuration that produced the quoted number |
| **fusion** | `P = 0.6*P_tdms + 0.4*P_hist`, 3 augmented rows/track | the configuration actually exported as `models/raga_v3_*` |

Both were scored at the same four levels off the same tier. The originally
registered arm was the fusion one; the primary arm was registered in the
addendum once the archived harness was found. Both are reported in full, as the
prereg requires.

## 3. The four levels

One feature matrix per arm, built once. The levels differ **only** in the
`groups` vector. Tier frozen at `min_tracks >= 25` on level-(a) track counts —
**18 ragas, 518 tracks, and not re-tuned at any level**.

- **(a)** `groups = track_id` — as originally run.
- **(b)** `groups = contour sha1` for archive tracks (byte-identical copies
  collapsed); Saraga keeps track_id.
- **(c)** `groups = archive item` for archive tracks, `concert folder` for
  Saraga, with known shared artists merged across items.
- **(c′)** registered sensitivity: (c) with identifiers collapsed into fuzzy
  families (`rapidfuzz.fuzz.ratio >= 85`).

### Primary arm — TDMS only, the historical configuration

| level | groups | ragas | top-1 | top-3 |
|---|---|---|---|---|
| **(a)** as-originally-run | 518 | 18 | **377/518 = 72.8%** | 439/518 = 84.7% |
| **(b)** recording-disjoint | 507 | 18 | 371/518 = 71.6% | 433/518 = 83.6% |
| **(c)** source-disjoint | **155** | 18 | **374/518 = 72.2%** | 435/518 = 84.0% |
| (c′) identifier-family | 150 | 18 | 369/518 = 71.2% | 428/518 = 82.6% |

### Fusion arm — the exported model, track-level read-out

| level | groups | top-1 | top-3 |
|---|---|---|---|
| (a) as-originally-run | 518 | 392/518 = 75.7% | 436/518 = 84.2% |
| (b) recording-disjoint | 507 | 383/518 = 73.9% | 436/518 = 84.2% |
| **(c)** source-disjoint | 155 | **381/518 = 73.6%** | 433/518 = 83.6% |
| (c′) identifier-family | 150 | 378/518 = 73.0% | 436/518 = 84.2% |

**Level (a) → (c) is −0.6pp on the primary arm and −2.1pp on the fusion arm.**
All four levels of the primary arm sit inside 71.2-72.8%, a spread of 1.6pp,
which on n = 518 is about eight tracks. **The levels are not distinguishable
from each other.** As in the Qmax audit, (c) scoring above (b) is not a matcher
effect — coarser grouping changes fold composition, and at this n a 0.6pp
difference is three tracks.

The coarsening is not cosmetic: **518 independent units become 155**, a 3.3×
reduction, and the minimum groups per raga falls from 25 to 13 — still enough
for a 5-fold split, and **no raga was dropped at any level**.

### Chance floors

Recomputed per level over the surviving label distribution; identical at all
four because the tier and the tracks never change, only the grouping:

```
majority-class rate      = 0.0579
class-prior expectation  = 0.0557
```

Level (c) primary at 72.2% is **~13× the class-prior floor**.

---

## 4. The mechanism the brief flagged, tested directly

The brief predicted that the damage would come not from the 97 byte-identical
copies but from the **251 tracks sitting in a same-raga cluster inside a single
archive item** — one upload's alapana and its kriti in that raga, same
performance, same singer, same tonic, same recording chain, split across folds
by a filename-level group key.

Splitting the tier by exposure (243 of the 518 tier tracks are in such a
cluster):

| subset | n | (a) top-1 | (c) top-1 | delta |
|---|---|---|---|---|
| **clustered** — in a same-raga same-source cluster | 243 | 71.2% | 70.0% | **−1.2pp** |
| **solo** — no same-raga same-source sibling | 275 | 74.2% | 74.2% | **+0.0pp** |

The prediction was right about the exposure and wrong about the consequence.
The clustered tracks were indeed the only ones that could be inflated, and they
were inflated by **1.2 percentage points — three tracks.** The solo tracks do
not move at all, which is the expected null and confirms the masking is doing
something rather than nothing.

Track-level churn between (a) and (c) on the primary arm: **11 tracks lost, 8
gained, net −3.** That is the whole effect.

---

## 5. Per-raga at level (c) — registered secondary, non-gating

| raga | n | (a) top-1 | (c) top-1 | (c) top-3 |
|---|---|---|---|---|
| Pūrvīkaḷyāṇi | 26 | 92.3% | 96.2% | 96.2% |
| Kalyāṇi | 30 | 83.3% | 83.3% | 90.0% |
| Mōhanaṁ | 30 | 83.3% | 83.3% | 90.0% |
| Tōḍi | 30 | 83.3% | 83.3% | 90.0% |
| Aṭāna | 26 | 76.9% | 80.8% | 88.5% |
| Kāmavardani | 30 | 83.3% | 80.0% | 90.0% |
| Nāṭa | 30 | 76.7% | 76.7% | 83.3% |
| Sindhubhairavi | 29 | 79.3% | 75.9% | 86.2% |
| Śankarābharaṇaṁ | 30 | 73.3% | 73.3% | 80.0% |
| Kamās | 29 | 75.9% | 72.4% | 86.2% |
| Ṣanmukhapriya | 29 | 72.4% | 72.4% | 82.8% |
| Hamsadhvāni | 30 | 70.0% | 70.0% | 76.7% |
| Harikāmbhōji | 29 | 62.1% | 65.5% | 75.9% |
| Kānaḍa | 25 | 60.0% | 64.0% | 92.0% |
| Bhairavi | 30 | 73.3% | 63.3% | 80.0% |
| Sāvēri | 30 | 63.3% | 63.3% | 90.0% |
| Karaharapriya | 27 | 55.6% | 59.3% | 81.5% |
| **Vasanta** | 28 | 42.9% | **35.7%** | 53.6% |

Fourteen of eighteen ragas hold at or above 63% top-1 source-disjoint, and
thirteen clear 80% top-3. **Vasanta is the one genuine weak class** — 35.7%
top-1, 53.6% top-3, both far below every other raga and below where its n
should put it. Anything that surfaces per-raga confidence should know this.

---

## 6. Verdict

**Against the interpretation table fixed in advance in the brief, level (c)
lands squarely in the top row — "≥ 65%: raga genuinely generalizes to unseen
sources".** The primary arm reproduces the historical 72.8% / 84.7% exactly and
then loses 0.6 percentage points when 518 independent units are collapsed into
155 source-disjoint ones; the fusion arm loses 2.1. The mechanism the brief
identified as the likely leak — 21.5% of archive tracks sharing a raga with a
sibling from the same upload — is real in count and worth 1.2pp, three tracks,
when it is closed. **This is the opposite outcome to the Qmax audit**, where the
same treatment took 60.0% to 9.5% because 34 of 36 hits were byte-identical
copies; here the entire level-(a)→(c) churn is 11 tracks lost against 8 gained.
Full-recording raga is a real, source-disjoint, leak-free result at roughly 13×
the class-prior floor, and it is now the only such result in the repository.

Two things must travel with that sentence. **First, this is full-recording
raga and nothing else.** `handoff.md:279` already records the same TDMS raga
path at **0/10 on wild short clips**, so surviving contamination is not the same
as surviving the domain gap, and the domain gap is the wall that closed every
other door. Second, the artist merge at level (c) is **partial** — the Qmax
audit established that artist is recoverable for only a minority of archive
tracks, so same-artist leakage across two differently-named uploads is reduced,
not eliminated. The (c′) sensitivity exists precisely because identifier
spellings fragment, and it moves the number by a further 1.0pp, which bounds how
much that residue can plausibly be worth.

**Scope.** This measures full-recording raga classification on the 18-raga
`min_tracks >= 25` tier only. It graduates nothing, it does not touch
`~/sung_tests --cache-v2` (still the only scoreboard), and it says nothing about
raga on 30-60s wild clips.

---

## 7. Artifacts

| file | what |
|---|---|
| `data/raga_audit/PREREGISTRATION.md` | readings registered and committed before the first fold |
| `scripts/raga_audit_protocol.py` | group vectors, tier, per-level n and floors |
| `scripts/raga_audit_families.py` | identifier fuzzy families for (c′) |
| `scripts/raga_audit_repro.py` | reproduction check of the rebuilt harness |
| `scripts/raga_audit_levels.py` | **primary arm** — the archived harness at four levels |
| `scripts/raga_audit_score.py` | fusion arm at four levels |
| `data/raga_audit/levels.json` | primary-arm results, per-raga, exposure split, flips |
| `data/raga_audit/results.json` | fusion-arm results |
| `data/raga_audit/protocol.json` | group counts, survivors, floors per level |
| `data/raga_audit/*.log` | raw run output, including the verbatim archived-harness runs |
