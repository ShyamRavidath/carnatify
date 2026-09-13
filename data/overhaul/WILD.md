# Frozen wild clips against the reference candidate

Prereg: `WILD_PREREG.md` (`f51a14c`, committed first). Harness:
`scripts/evaluate_wild_clips.py`. Output: `context180_recovered_experiment/wild27.json`.
Run 2026-09-13. All 29 frozen clips re-hashed and unchanged. Whole clip,
default profile, `identify_raga`, registered gate reported. The 12 m4a clips
were decoded once through FFmpeg to float PCM because libsndfile cannot open
them; the frozen SHA256 stays the query identity.

## Primary read-out, 27 in-vocabulary clips

| | reference candidate (69 classes) | `raga_v3` fused, 2026-07-31 (32 classes) |
|---|---|---|
| top-1 | **16/27 = 59.3%** [40.7, 75.5] | 16/27 = 59.3% |
| top-3 | **20/27 = 74.1%** [55.3, 86.8] | 20/27 (tier-restricted) |

Identical integers, on a harder answer space (69 classes against 32) with no
tier restriction. Not the same 16 clips, though: the candidate newly gets
Kaddanuvariki, Thaye Yashoda, sarasijanAba (all Tōḍi), yArO ivar yArO and
loses others. Per-clip table in `wild27.json`.

OOV rows (reported, never counted): Yamunākalyāṇi → Behāg, abstained;
Ābhēri → Ānandabhairavi, abstained.

## Gate on wild clips

| accepted | correct | precision | OOV accepted |
|---|---|---|---|
| 11/27 | 8 | **72.7%** | 0/2 |

Accepted-wrong, all with comfortable margin: Ninnukori Yunnanura (Mōhanaṁ →
Hindōḷaṁ, margin 0.416, the most confident wrong answer in any set so far),
Jagadanandakaraka (Nāṭa → Bṛndāvana sāranga, 0.195), bhajare (Kalyāṇi →
Śankarābharaṇaṁ, 0.183).

## Predictions

- P1 (50–70%): held, 59.3%.
- P2 (vAtApi gaNapathim still wrong): held. Sencuruṭṭi, Sahānā, Kuntalavarāḷi;
  Hamsadhvāni not in the top three.
- **P3 refuted on precision**: accepted 11 ≤ 13, but 72.7% < 80%. This is the
  third set on which the gate's accepted precision lands under its bar
  (dev 82.9%, wild 72.7%; field 2/2 is too small to count).
- P4 (top-3 ≥ 70%): held, 74.1%.

## Reading

- Short wild clips: the candidate is exactly as good as the July model, not
  better. Combined with `FIELD.md`, the +7.9 pp grouped CV gain has now
  failed to appear on two independent phone-audio sets. The gain is real on
  archive/reference audio and does not transfer; that is the finding.
- The gate is worse on wild audio than on dev. A margin of 0.4 on a wrong
  answer (Mōhanaṁ heard as Hindōḷaṁ, both pentatonic) means margin alone is
  not a safe signal on short phone clips. Any product point chosen from the
  dev curve should be checked against this table too, and it will look worse.
- Nothing here changes the reference candidate or the gate's status (off).
