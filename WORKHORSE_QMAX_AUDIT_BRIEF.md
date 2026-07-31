# Workhorse brief — audit the 60-67% Qmax number for same-recording contamination

Date: 2026-07-30. For the **Opus 5 workhorse**. Read-only measurement, no
training, no GPU. Nothing to commit until the verifier has read the result.

## Why this is the next thing

`HANDOFF_CLIP_ID.md:45` records **"Composition, full-recording cross-artist:
60-67% top-1 (Qmax)"**. After the duration probe's KILL, that is the **last
surviving positive result in the repository**, and the 2026-07-25 design doc's
whole "input contract, not model quality" thesis rests on it: the argument is
that the pipeline family already works on full recordings and only collapses at
30-60s.

It has never had the audit that destroyed the comparable number next door.
CoverHunter's headline dev mAP was **0.327**; a source-disjoint re-score put it
at **0.113** against a 0.031 chance floor. Roughly two thirds of it was
same-recording contamination. Qmax was evaluated in the same era, on the same
corpus, by the same hands, and `HANDOFF_CLIP_ID.md:107` already flags that its
short-clip sibling benchmark was "artist/recording-family flattered".

So the question is narrow and answerable: **how much of 60-67% survives when a
query can never be scored against its own recording, its own artist, or its own
archive upload?**

## What to do

Assets all exist: `models/qmax_catalog.npz` (1,421 tracks, 3,465 chroma
windows), `models/qmax_catalog_meta.json`, `build_qmax_catalog.py`,
`evaluate_composition_qmax.py`, `evaluate_composition_external.py`.

1. **Reconstruct exactly what the original evaluation did.** Read
   `evaluate_composition_qmax.py` and report, in plain terms, what was in the
   query set, what was in the reference set, and whether anything prevented a
   query from matching its own recording or another track off the same upload.
   Quote the code. If the original protocol cannot be determined from the repo,
   say so — that is itself the finding, and it means 60-67% should stop being
   quoted at all.
2. **Re-score at three increasing levels of disjointness**, reporting each:
   - **(a) as-originally-run**, to reproduce the 60-67% baseline and confirm the
     harness still works;
   - **(b) recording-disjoint** — a query is never scored against its own track;
   - **(c) source-disjoint** — a query is never scored against any track sharing
     its `archive_identifier` (the cluster key already used by the duration
     probe), and, where artist is recoverable from the manifest, not against the
     same artist either.
3. **Report the chance floor for each level**, computed the way
   `colab_coverhunter_rescore.py` does it — mean positives per query divided by
   references, averaged **over clips, not over songs**. The log records that
   getting this wrong once printed 0.006 instead of 0.031. Reproduce the
   arithmetic explicitly.
4. **Report n at every level.** Source-disjointness will shrink the evaluable
   set, possibly a lot — only 65 of 1,118 titles have 2+ renditions. If level
   (c) leaves too few queries to mean anything, that is the headline finding and
   must be stated as such rather than buried under a percentage.

Write it up in `data/QMAX_CONTAMINATION_AUDIT.md`: protocol quoted from code,
the three numbers with their n and their chance floors, and a one-paragraph
verdict.

## Interpretation, fixed in advance so it is not chosen after the number

| level (c) result | what it means |
|---|---|
| holds near 60-67% | the melodic channel genuinely identifies compositions across renditions on full recordings. The input-contract thesis survives, and the question becomes how to get that signal out of shorter clips. |
| lands in the 20-40% band | real but weak signal, the CoverHunter story again. Not a product on its own; would need the rendition corpus before it could become one. |
| collapses toward the chance floor | the last positive number was contamination. Every model-side door is then closed, and the honest next move is scope and demand, not another model. |
| n too small to say | the corpus cannot answer the question. Report that plainly; do not fill the gap with the contaminated number. |

## Rules of engagement

- Read-only. Do not retrain, do not rebuild the catalog, do not touch
  `identify_clip.py`.
- `~/sung_tests --cache-v2` remains the only scoreboard; this audit is a
  measurement of a historical claim, and it graduates nothing.
- Do not tune the protocol until the number improves. One protocol per level,
  chosen before running, exactly as the duration probe did it.
- If the harness has bit-rotted (py3.14 `venv` vs py3.11 `venv_train`, essentia
  under fork-not-spawn — see `HANDOFF_CLIP_ID.md` ops traps), report the cost of
  repair before spending it.
- Log the result in `AGENT_LOG.md` in normal prose; leave the verdict to the
  verifier seat.
