# Codex — task: systematic work-family duplicate DETECTOR (read-only; output a candidate table)

You are read-only on the manifest/matcher/registry code (Opus edits those —
do not touch them, to avoid collision). Your deliverable is **one analysis
script + its output table**: the complete set of stub↔full-work duplicate
candidate pairs, with evidence, for Opus to verify and fold into the manifest.

## Why
Registry work-family duplication is the binding error class (AGENT_LOG, newest:
"Rung 5 re-scored"). Two clips (akhilAndEswari, yEnATi) already flipped from ONE
duplication artifact — the matcher returns the *real full-work* row while the
manifest truth points only at a truncated stub row, so a correct recognition
scores as a miss. Rung 1/2 found four such (sarasijanAba, Madhava, ...) by hand.
We need the systematic set, not one-offs.

## What to build
A read-only script (e.g. `scripts/detect_workfamily_dupes.py`) that, for **each
of the 78 in-catalog wild-truth ids** in `data/wild_truth_manifest.json`, finds
OTHER `data/composition_registry.json` rows that are plausibly the SAME
composition. Rank candidate pairs by evidence strength:

1. **Shared karnatik page** — two rows listing the same `cN.shtml` page ⇒ almost
   certainly one work. (Strongest.)
2. **Identical / near-identical pallavi** — first real lyric line (from
   `data/karnatik_lyrics.json` via each row's `karnatik_pages`) matches, after
   folding, at high ratio. (Strong.)
3. **Same composer + same-or-equivalent raga + high title similarity** — note
   raga spelling variants count as equal (e.g. `dvijAvanti`≈`jujAvanti`,
   `nIlAmbari`≈`neelAmbari`). (Medium — flag, don't assert.)

Emit `data/workfamily_candidates.json`: for each truth id, a list of
`{candidate_id, canonical, raga, composer, evidence: [shared_page|pallavi_ratio|
title+composer+raga], confidence: high|medium|low, pallavi_snippet}`. Also print
a compact human table. **Do NOT edit the manifest or merge anything** — propose
with evidence; Opus verifies each against the identical-pallavi/composer/raga bar
and applies. Exclude the obvious non-matches (different pallavi = different work,
even if titles rhyme — e.g. Dikshitar `rakSamAm` vs `rakSatu` are different
kritis; Purandara's three `ranga bArO` pallavis are three works).

## Guardrails
- Read-only. No manifest/registry/matcher edits. One new script under `scripts/`.
- Do not lower any global fuzzy-merge threshold; this is a *reviewed candidate
  list*, not an auto-merge.
- Keep it to the 78 truths first (highest value). A registry-wide pass is a
  nice-to-have second section, clearly separated.
- Bounded task: one script, one output file, one table. Don't expand scope.

## When done
Append a short AGENT_LOG entry: how many candidate pairs at each confidence,
which truth ids gained a high-confidence sibling, and the output path. Opus picks
up from `data/workfamily_candidates.json`, verifies, applies to the manifest, and
re-baselines all configs. Commit/push are Deepti's.
