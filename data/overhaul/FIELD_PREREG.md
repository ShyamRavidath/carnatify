# Preregistration: the reference candidate on Deepti's labelled concert items

Registered 2026-09-10 by the tech-lead seat. **Committed before the harness
is touched.** Small diagnostic, not a release test; n is six.

## 0. What is fixed

- Model: reference candidate `context180_recovered_experiment/training/raga.joblib`
  (`f594584402cb2ae35532612e673c194661706fcdfe4b69bbecc69b6d50316e2b`).
- Gate: `margin >= 0.16277227656365623`, the registered point from
  `ABSTAIN_GATE.md`. Reported, not tuned. It is off in the product by rule.
- Labels: `data/architecture_audit/label_intervals.json`, derived from
  `data/long_concerts/LABELS.tsv` at SHA256 `a0d137ea…` (verified unchanged
  today). Six primary high-confidence items: c1_1 Śankarābharaṇaṁ (two
  intervals around the tani; the longer one is used), c2_1 Tōḍi, c2_2
  Hindōḷaṁ, c2_3 Dhēnukā, c3_1 Ānandabhairavi, c3_2 Varāḷi. Two non-primary
  rows (c3_3 Hamīr kaḷyaṇi, approximate end; c3_4 Kalānidhi, no confidence)
  are reported beside, never in the primary line.
- Query: one centered 180-second window per item, `plan_queries` unchanged.
- Frozen-hash check on all three concert files before any query.
- Frontend: `mixed_tonic_query_melodia_v1`, default profile, same as the
  dev evaluation. Queries are cached under `data/overhaul/cache/concerts/queries`.

## 1. Vocabulary

Dhēnukā is out of vocabulary (the handoff says so; the harness checks against
the actual 69 classes). Kalānidhi is expected out of vocabulary. Every other
primary item is expected in vocabulary. The in-vocabulary denominator is
therefore expected to be 5; report it as counted.

## 2. Read-outs

- Top-1 and top-3, in-vocabulary items only (expected 5).
- OOV items: count, and what the model said, and whether the gate abstained.
- Gate decision per item, and the four-way table: accepted-correct,
  accepted-wrong, abstained-correct, abstained-wrong.
- Per-item duration beside every row. Three concerts; **no confidence interval
  is reported** because n_clusters = 3 cannot support one.
- Comparator: the historical best on these same six queries is 4/6 for the
  `combined` model and 3/6 for the previous guarded candidates (HANDOFF.md §9).
  The reference candidate has never been run on them.

## 3. Predictions

- **P1.** Reference candidate gets at least 3 of 5 in-vocabulary items top-1.
- **P2.** c1_1 Śankarābharaṇaṁ is still wrong. Every prior model failed it
  (the handoff's recurring "low-confidence Bēgaḍa" on concert 1).
- **P3.** The gate abstains on Dhēnukā (c2_3).
- **P4.** The gate accepts at most 3 of the 6 primary items.

## 4. What a failure means

- P1 fails: the dev gain did not transfer to phone-recorded field audio; say so
  in HANDOFF.md, and the field remains the binding number, not the dev set.
- P3 fails: the registered gate passes a real OOV field item; that is the kind
  of failure the product must never show, and it is reported first.

## 5. Not in scope

No automatic boundaries. No new labels. No model change. The six items were
inspected by earlier agents and are not fresh.
