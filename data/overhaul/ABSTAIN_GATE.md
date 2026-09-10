# Abstain gate: result

Harness: `scripts/abstain_gate.py`. Prereg: `ABSTAIN_GATE_PREREG.md` (`dac195e`,
committed first). Output: `context180_recovered_experiment/abstain_gate.json`.
Run 2026-09-10 on the reference candidate (`f5945844…`). 25 leave-class-bin-out
refits on the fixed group folds; 17,735 scored windows (14,188 known, 3,547
simulated OOV). Gates 1 and 2 pass (dev cache reproduces 102/139).

## Selection on the pool (never sees dev)

| signal | threshold | coverage | precision | OOV false accept | cross-fit precision |
|---|---|---|---|---|---|
| `max_score` | 0.392 | 44.9% | 85.2% | 15.0% | 85.3% |
| **`margin`** | **0.163** | **47.3%** | **87.3%** | **15.0%** | **87.2%** |
| `softmax_max` (current signal, T = 0.066) | 0.720 | 46.9% | 86.6% | 15.0% | 86.5% |

Chosen: `margin` ≥ 0.163 (top-1 minus top-2 raw ridge score). Selection
optimism is under 0.1 pp on every signal (P4 held).

## Dev, applied once (184 queries, 17 artist clusters)

| gate | accepted | coverage | precision | 95% cluster CI | OOV accepted / 45 |
|---|---|---|---|---|---|
| current bundle gate | 145 | 78.8% | 65.5% | [57.5, 71.6] | **29** (64.4%) |
| **new margin gate** | **70** | **38.0%** | **82.9%** | [75.0, 92.7] | **7** (15.6%) |
| new gate, 176 single-raga | 69 | 39.2% | 84.1% | [75.5, 92.9] | 6 / 37 (16.2%) |

**Bar (precision ≥ 85%, OOV-FA ≤ 15%, ≥ 20 accepted): FAILS, narrowly, on both
terms.** Per the prereg the gate does not ship as an answer. The product path
in step 6 shows ranked candidates as candidates and never asserts.

## Predictions

- P1 held, narrowly: margin 47.3% vs softmax 46.9% coverage at the bar. The
  softmax signal was not the main problem; never having seen an OOV example was.
- P2 held: 47.3% ≥ 40%.
- **P3 refuted**: dev precision landed at 82.9%, under 85%, while OOV-FA was
  15.6%, at the bottom of the predicted band. I expected OOV to be the hard
  term; both were.
- P4 held.

## What the errors look like (post hoc, not a selection input)

The 7 accepted OOV queries are mostly parent/janya or near-synonym pairs:
Mandāri → Kāmavardani, Kumudakriyā → Kāmavardani, Gamakakriyā →
Pūrvīkaḷyāṇi, Tillāng → Bṛndāvana sāranga, Mārgahindōḷaṁ → Tōḍi,
Sārāmati → Sindhubhairavi, and one Rāgamālika → Behāg. The 5 accepted wrong
known answers are ordinary confusions (Rītigauḷa → Suraṭi, Kānaḍa → Behāg,
Ābhōgi → Śrīranjani, Tōḍi → Vasanta, Behāg → Kamās). A product display of
"closest known raga" would be defensible for the OOV group; it is still not an
identification and is not counted as one here.

## The trade-off curve (dev, `margin`), for Deepti's choice, not mine

| threshold | accepted | coverage | precision | OOV-FA |
|---|---|---|---|---|
| 0.107 | 92 | 50% | 80.4% | 24.4% |
| 0.163 (chosen) | 70 | 38% | 82.9% | 15.6% |
| 0.204 | 55 | 30% | 85.5% | 8.9% |
| 0.250 | 46 | 25% | 89.1% | 4.4% |
| 0.331 | 28 | 15% | 89.3% | 2.2% |

Any point read off this table is tuned on the dev set and must be labelled as
such if used. The registered point is 0.163.

## What changed for the product

From "answers 79% of the time, wrong 35% of the time, and swallows two thirds
of unknown ragas" to "answers 38% of the time, wrong 17% of the time, and
passes one in six unknown ragas". The bar was set at 85/15 and the gate landed
at 83/16. It stays off by rule; the numbers are published.
