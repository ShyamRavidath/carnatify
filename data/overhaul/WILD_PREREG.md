# Preregistration: the frozen wild clips against the reference candidate

Registered 2026-09-13. Committed before the harness. The 27-clip wild number
(59.3%, `data/RAGA_WILD_MEASUREMENT.md`) is an 18-class-tier, 32-class-model,
`raga_v3` figure from 2026-07-31. The reference candidate has never been run
on these clips.

## 0. What is fixed

- Clips: `data/raga_wild/FROZEN_CLIPS.json`, 29 clips in `~/sung_tests`,
  re-hashed on disk before scoring; a mismatch is a blocker.
- Truth: the frozen `raga_canonical`, corrected by Deepti's 2026-08-13 audit
  (`scripts/raga_wild_relabel.py` CORRECTIONS): Maithreem Bhajata is
  Yamunākalyāṇi, nagumomu ganaleni is Ābhēri. Both are outside the 69-class
  vocabulary and are reported as OOV rows, never as misses. Denominator for
  the primary read-out: **27**, the same 27 as the August number.
- Model: `context180` from the registry; gate `margin_v1_context180`
  reported, not tuned. Query: the **whole clip** (43–85 s, all under the 180 s
  contract bound), default profile, `identify_raga`, cache under
  `data/overhaul/cache/wild/queries`. Whole clip is the registered
  best-available window from the August prereg; nothing is re-selected.
- Fold for correctness: `normalize_ragas.fold`, same as everywhere else.

## 1. Read-outs

- Top-1 and top-3 over 27; Wilson 95% interval, as the August table did
  (clips are treated as independent there; they are different performances).
- Gate: accepted count, accepted precision, and what it did on the two OOV
  clips (Ābhēri may reasonably score as Karṇāṭaka dēvagāndhāri; Deepti ruled
  those practically inseparable, and it is still reported as OOV here).
- Per-clip table with duration, truth, top-3, margin, tonic.
- Comparator, same 27 clips, whole clip, mix arm: `raga_v3` fused 16/27
  top-1, 20/27 top-3 tier-restricted.

## 2. Predictions

- **P1.** Top-1 between 50% and 70% (14–19 of 27). The 69-class model has a
  harder answer space than the 32-class one but 180 s training context and
  cleaner supervision; I expect roughly a wash with the 59.3%.
- **P2.** `vAtApi gaNapathim` (Hamsadhvāni), the rank-25 catastrophe in
  August, is still not top-1.
- **P3.** The gate accepts at most half the clips, and accepted precision is
  at least 80%.
- **P4.** Top-3 at least 70% (19+ of 27).

## 3. What it means

Wild clips are 43–85 s phone recordings of famous kritis; they are the
short-clip end of the product, not the concert-companion regime. A result
near 59% says the candidate is not worse on short wild audio; it does not
speak to 10–30 minute items. P3 failing on precision would be a third
independent strike against the gate's transfer.

## 4. Not in scope

`FROZEN_CLIPS.json` is not edited. No 60 s window arm, no demucs arm. No
retuning of anything on these clips.
