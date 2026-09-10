# Field diagnostic: reference candidate on Deepti's six labelled items

Prereg: `FIELD_PREREG.md` (`a4269c6`, committed first). Harness:
`scripts/evaluate_labeled_intervals.py --models context180 --gate …/gate.json --window-s 180`.
Output: `context180_recovered_experiment/field180.json`. Run 2026-09-10.
Frozen-hash gate passed on all three concerts; LABELS.tsv unchanged (`a0d137ea…`).

| item | concert | truth | in vocab | top-3 | margin | gate | top-1 |
|---|---|---|---|---|---|---|---|
| c1_1 | 1 | Śankarābharaṇaṁ | yes | Dēvagāndhāri, Kalyāṇi, Nāṭa | 0.009 | abstain | **wrong** |
| c2_1 | 2 | Tōḍi | yes | Cakravākaṁ, Dhanyāsi, Amṛtavarṣiṇi | 0.019 | abstain | **wrong** |
| c2_2 | 2 | Hindōḷaṁ | yes | Hindōḷaṁ, Nāṭa, Āhiri | 0.179 | **accept** | correct |
| c2_3 | 2 | Dhēnukā | **no** | Māyāmāḷavagauḷa, Nāṭa, Varāḷi | 0.154 | abstain | OOV |
| c3_1 | 3 | Ānandabhairavi | yes | Ānandabhairavi, Śrī, Bṛndāvana sāranga | 0.043 | abstain | correct |
| c3_2 | 3 | Varāḷi | yes | Varāḷi, Bṛndāvana sāranga, Ṣanmukhapriya | 0.291 | **accept** | correct |

Every query is 180 s, centred in the longest labelled interval.

## Read-outs

- In-vocabulary top-1: **3/5**. Top-3: 3/5 (the two misses are not in the top three).
- OOV: 1 item (Dhēnukā). The model said Māyāmāḷavagauḷa; the gate abstained,
  with 0.009 of margin to spare.
- Gate four-way table: accepted-correct 2, accepted-wrong 0, abstained-correct 1,
  abstained-wrong 2. Accepted precision 2/2, coverage 2/6.
- No confidence interval: three concerts.
- Comparator, same six queries, earlier models: `combined` 4/6, guarded
  candidates 3/6 (HANDOFF.md §9). The reference candidate is 3/6 on the same
  denominator. **No field improvement over the previous guarded candidates.**

## Predictions

- P1 (≥ 3/5 known): held, at the bound.
- P2 (Śankarābharaṇaṁ still wrong): held. Now Dēvagāndhāri rather than the
  historical Bēgaḍa; still not close.
- P3 (gate abstains on Dhēnukā): held, narrowly. A threshold 0.01 lower would
  have passed a real OOV field item. This is exactly the failure mode the
  dev bar was set to exclude, and it is why the gate stays off.
- P4 (gate accepts ≤ 3): held, 2.

## What it means

The +7.9 pp grouped CV gain and +5 dev recordings did not show up on phone
audio from the target setting. Two of five known items are wrong with near-zero
margin, which is the model saying it does not know, and the gate correctly
declines them. The honest product state for this recording set is: two
confident, correct answers out of six items, and silence on the rest. That is
better than the previous gate, which would have confidently answered wrong.

Three concerts labelled out of eleven. The other eight are the cheapest way to
make this number mean something.
