# Blind runs over all 11 frozen concerts

Run 2026-09-13, `scripts/concert_pipeline.py --model context180 --gate …/gate.json --window-s 180`,
one file per concert under `context180_recovered_experiment/blind_concerts/`.
The model saw no labels. **Nothing here is scored**: the only concerts with
labels are 1, 2 and 3, and those items were already inspected. When Deepti's
rows for concerts 4–11 land, `scripts/evaluate_labeled_intervals.py` scores
them from the cached queries in seconds.

| concert | min | 180 s windows | gate accepted | accepted top-1 (for orientation only, not truth) |
|---|---|---|---|---|
| 1 | 27 | 53 | 5 | Kāpi 5 |
| 2 | 33 | 65 | 38 | Hindōḷaṁ 33, Māyāmāḷavagauḷa 5 |
| 3 | 92 | 183 | 79 | Varāḷi 47, Kalyāṇi 10, Dēvagāndhāri 7, Sindhubhairavi 7 |
| 4 | 44 | 88 | 14 | Sindhubhairavi 13 |
| 5 | 114 | 227 | 98 | Ānandabhairavi 36, Kāṁbhōji 21, Kalyāṇi 18, Māyāmāḷavagauḷa 14 |
| 6 | 68 | 135 | 80 | Kalyāṇi 40, Sāvēri 14, Gauḷa 13, Nāṭa 12 |
| 7 | 45 | 89 | 30 | Mōhanaṁ 29 |
| 8 | 35 | 69 | 17 | Śankarābharaṇaṁ 17 |
| 9 | 37 | 74 | 6 | Āhiri 3, Jaganmōhini 3 |
| 10 | 32 | 63 | 17 | Tōḍi 7, Māyāmāḷavagauḷa 6, Nādanāmakriya 4 |
| 11 | 66 | 132 | 54 | Nāṭa 13, Sindhubhairavi 13, Kalyāṇi 13, Sāvēri 9 |

1,178 windows, 438 accepted by the registered gate (37%, matching the dev
coverage of 38%). All 1,178 windows produced a candidate; no extraction
failures.

## The one labelled thing worth saying now (concert 2)

Deepti's rows: Tōḍi 0:12–7:02, "nothing + alapana", Hindōḷaṁ kriti 15:14–28:38,
Dhēnukā 29:15–end. The blind timeline says Hindōḷaṁ from about 6:00,
accepted from 7:00, with margin rising to **0.91 during 12:00–15:00**: that
is the alapana. The model's most confident stretch of the whole day is a raga
alapana, which is exactly the setting the companion is for. Two consequences:

- **Label alapana as its own row with the raga.** Under the current template
  the alapana falls in an unscored gap; it is scorable raga evidence, and the
  best-case evidence at that.
- Dhēnukā (OOV) is accepted as Māyāmāḷavagauḷa from 28:30 to the end with
  margin 0.2. Third confirmation that the gate passes close-relative OOV
  ragas; the bar stays failed.

The concert 1 (Śankarābharaṇaṁ) and concert 3 (Varāḷi, Ānandabhairavi)
timelines agree with `FIELD.md`: Varāḷi and Ānandabhairavi are found and
held; Śankarābharaṇaṁ is heard as Kāpi / its janyas and never accepted.
