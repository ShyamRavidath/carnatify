# Off-tier fetch check (August §6-E), against the 69-class reference vocabulary

Script: `scripts/raga_fetch_offtier.py`. Output: `data/raga_tier/fetch_recount_offtier.json`.
Run 2026-09-13. Entirely offline against the 6,692 cached archive.org mp3
listings; no download, no audio, no model. Same attribution rules as
`raga_fetch_recount.py` (own-label through the alias map, or title-join to a
single-raga composition), so the count is an upper bound on candidate
recordings, not trained tracks.

## A matcher bug, found and excluded

The fetchers' vowel-folded matcher maps the **tala word "Adi"** onto the raga
**Pāḍi**: 93 of the first run's "reachable Pāḍi" files were `… - Adi.mp3`.
Tala words are now excluded in this script. The August in-tier recount was
not affected (Pāḍi is off-tier), but `download_targeted_deficits.py` still has
the bug and would fetch tala-named files as Pāḍi if run for that class.

## Result

| | count |
|---|---|
| off-vocabulary ragas with any reachable audio | 21 |
| off-vocabulary reachable (raga, title) pairs | 79 (August said 185; 93 were the Pāḍi bug, the rest are ragas that have since been admitted) |
| off-vocabulary ragas that would reach the admission line (5) | 10 real (plus `ragamalika`, excluded, and Sarasvatī manōhari, already on disk with 5 but not in the model) |

Would cross admission with a fetch:

| raga | on disk | reachable | total |
|---|---|---|---|
| Ranjani | 1 | 15 | 16 |
| Simhēndra madhyamaṁ | 0 | 10 | 10 |
| Kathanakutūhalaṁ | 2 | 5 | 7 |
| Mandāri | 2 | 5 | 7 |
| Rasikapriya | 2 | 4 | 6 |
| Śudda sāvēri | 1 | 5 | 6 |
| Dhanaśrī | 2 | 3 | 5 |
| Kalāvati | 1 | 4 | 5 |
| Sindhumandāri | 0 | 5 | 5 |
| Yamuna kalyāṇi | 0 | 5 | 5 |

Thin in-vocabulary classes (under 10 training tracks) with reachable audio:
16 of 20, but almost all with one or two recordings. Only Pūrṇacandrika (+6),
Saurāṣtraṁ (+4), Dvijāvanti / Janaranjani / Kuntalavarāḷi / Mānḍu /
Śuddadhanyāsi (+2) would move a class meaningfully.

## Reading

- The vocabulary lever is small but not zero: about **ten ragas** could enter
  at the five-track line, two of them (Ranjani, Simhēndra madhyamaṁ) with
  double-digit support. Mandāri and Yamuna kalyāṇi are both ragas that already
  cost us: Mandāri was a gate false-accept on dev, Yamunākalyāṇi is one of the
  two OOV wild clips.
- Five-track classes are the ones with the worst per-class swings in the
  verdict (Kuntalavarāḷi −20 pp on n=5). Admitting ten such classes buys
  coverage, not accuracy, and the gate's OOV behaviour would need re-measuring.
- Sarasvatī manōhari has 5 recordings on disk and is not in the model:
  worth checking why the admission pass dropped it (duplicate or conflicting
  labels are the usual reason) before fetching anything.
- No fetch was performed. archive.org is free; the cost is Melodia time and
  a retrain plus a re-run of the verdict and gate harnesses. Deepti's call.
