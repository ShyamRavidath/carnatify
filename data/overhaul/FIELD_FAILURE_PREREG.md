# Preregistration: the two near-zero-margin field failures

Registered 2026-09-13. Committed before the harness. Diagnostic on two items;
no model change, no threshold change, no new labels.

## 0. What is being diagnosed

`FIELD.md`: c1_1 Śankarābharaṇaṁ (concert 1, 2–755 s) scored Dēvagāndhāri with
margin 0.009; c2_1 Tōḍi (concert 2, 12–422 s) scored Cakravākaṁ with margin
0.019. Both are in vocabulary with large training support (Śankarābharaṇaṁ,
Tōḍi are among the best-supported classes). One centred 180 s query each.

## 1. Fixed protocol

- Model: reference candidate `context180` from the registry; gate
  `margin_v1_context180` reported, not tuned.
- Sweep A, position: 180 s queries starting every 30 s from the interval start
  while the query fits inside the labelled interval. c1_1: 20 windows; c2_1: 8.
- Sweep B, duration: at the centred position, durations 60 / 120 / 180 s.
- Sweep C, tonic: at the centred 180 s position, rescore with the tonic
  candidates at 0 / +5 / +7 semitones (`tonic_candidates`, the fixed set the
  earlier tonic-mixture diagnostic used). This tests whether a Sa/Pa or Sa/Ma
  confusion explains the miss; it is not a proposal to search tonics at
  inference.
- Every query goes through `identify_raga`, cached under
  `data/overhaul/cache/concerts/queries`; frozen-hash check first.
- Read-outs per window: top-3, margin, tonic estimate, voiced seconds. Per
  item: fraction of windows with truth at top-1 and in top-3; tonic spread in
  cents across windows (mod octave); best duration.

## 2. Predictions

- **P1.** c1_1: truth is top-1 in fewer than half the 20 position windows. This
  is a model failure on this recording, not a bad query position.
- **P2.** Tonic estimates across windows of at least one item disagree by more
  than 50 cents (mod octave) in at least a quarter of windows. The handoff's
  24-recording diagnostic found six of 24 with fifth-related disagreement.
- **P3.** Sweep C does **not** rescue either item: no tonic candidate makes the
  truth top-1 with margin above the gate. Predicted false that it helps.
- **P4.** c2_1 Tōḍi: truth is in the top-3 of at least half the position
  windows. Tōḍi is the best-represented class in the wild set and the corpus;
  the centred window may be alapana-heavy or percussion-heavy.

## 3. What a result means

- P1 false (position rescues c1_1): query placement inside an item matters
  and the concert pipeline's fixed grid should be reconsidered.
- P2 true: tonic instability on phone audio is a real front-end issue on the
  target setting, separate from the classifier. It would justify a tonic
  consistency check across adjacent windows in the concert pipeline (cheap),
  not a learned tonic model (already measured negative).
- P3 true (tonic rescues): the miss is a tonic error; report as such.

## 4. Not in scope

Any change to the model, gate, or query grid. Any other item.
