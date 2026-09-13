# The two near-zero-margin field failures, diagnosed

Prereg: `FIELD_FAILURE_PREREG.md` (`a3dbee3`, committed first). Harness:
`scripts/diagnose_field_failures.py`. Output:
`context180_recovered_experiment/field_failures.json`. Run 2026-09-13.
Reference candidate, registered gate reported, nothing tuned.

## c1_1 Śankarābharaṇaṁ (concert 1, 2–755 s)

| sweep | result |
|---|---|
| position, 20 windows of 180 s every 30 s | truth top-1 in **5/20**, top-3 in 11/20, gate accepted 0 |
| duration at centre, 60 / 120 / 180 s | Dēvagāndhāri, Dēvagāndhāri, Dēvagāndhāri; margin 0.167 / 0.094 / 0.009 |
| tonic candidates 0 / +5 / +7 semitones | Dēvagāndhāri / Aṭāna / Rītigauḷa; none rescues |
| tonic estimate across the 20 windows | **138.8 Hz in every window, 0 cents spread** |

Top-1 per window in order: Bēgaḍa ×4, Śankarābharaṇaṁ ×3, Dēvagāndhāri ×3,
Kalyāṇi, Dēvagāndhāri, Behāg ×3, Bilahari, Śankarābharaṇaṁ, Bēgaḍa,
Śankarābharaṇaṁ, Bilahari. **Every wrong answer but Kalyāṇi is a janya of
Śankarābharaṇaṁ** (Bēgaḍa, Dēvagāndhāri, Behāg, Bilahari share its notes), and
Kalyāṇi differs by one note.

## c2_1 Tōḍi (concert 2, 12–422 s)

| sweep | result |
|---|---|
| position, 8 windows | truth top-1 in **0/8**, top-3 in 3/8, gate accepted 0 |
| duration at centre | Pūrṇacandrika / Cakravākaṁ / Cakravākaṁ; margin ≤ 0.045 |
| tonic candidates | Cakravākaṁ / Hamsadhvāni / Nādanāmakriya; none rescues |
| tonic across windows | 139.6 Hz in 7/8; one window at 210.5 Hz (a fifth up) |

Top-1 per window: Sāvēri ×2, Nādanāmakriya, Dhanyāsi, Sāvēri,
Māyāmāḷavagauḷa, Cakravākaṁ, Māyāmāḷavagauḷa. **Every answer shares Tōḍi's
Sa R1 M1 P D1 skeleton**; what differs is Ga (G2 vs G3) and Ni (N2 vs N3), the
two notes Tōḍi's gamaka bends most.

## Predictions

- P1 (c1_1 truth in fewer than half the windows): held, 5/20.
- **P2 (tonic disagreement > 50 cents in ≥ a quarter of windows) refuted.** The
  tonic is rock-stable on both items: 0/20 and 1/8. The handoff's tonic
  instability finding was on archive training audio, not on these phone
  recordings.
- P3 (tonic candidates do not rescue): held, as predicted.
- **P4 (Tōḍi in top-3 for at least half the windows) refuted**: 3/8.

## What it means

Both failures are the same failure: **right parent scale, wrong raga within
it.** The tonic is correct, the query position barely matters, longer context
does not help, and the model's confusions are all within the mela family.
A pitch-distribution feature (TDMS is a transition histogram) sees the
scale; it does not see the characteristic phrases that separate a janya
from its parent, or Tōḍi's oscillated Ga from Māyāmāḷavagauḷa's plain one,
on a phone recording. This is consistent with the dev OOV false accepts
(janya → parent) and with Deepti's own ruling that some janya/parent pairs
are practically inseparable.

Implications, none of them acted on here:

- A tonic-consistency check across adjacent concert windows would have
  caught nothing on these two items; not worth building on this evidence.
- The concert pipeline's fixed grid is not the problem.
- The next model-side lever, if any, is phrase-level (sequence) evidence
  within a mela, not more classes, more duration, or a different tonic. The
  September temporal CNN (44% vs 67% kernel on one fold) is the only
  attempt at that so far and it was underpowered, not disproven.
- A product answer of "Śankarābharaṇaṁ family" would have been right on
  c1_1 in essentially every window. Whether a family-level answer is worth
  showing is a product decision for Deepti.
