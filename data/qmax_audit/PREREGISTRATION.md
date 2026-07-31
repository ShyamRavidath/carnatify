# Qmax contamination audit — readings registered before any score exists

Written 2026-07-30 while `scripts/qmax_audit_matrix.py` was still computing its
first row. No Qmax distance from this audit had been read at the time of
writing; everything below is derivable from set membership alone, and the file
is committed alongside the result so the ordering is checkable.

The interpretation table itself is not restated here — it is fixed in
`WORKHORSE_QMAX_AUDIT_BRIEF.md` and is not to be modified.

## The three levels, as the brief fixed them

Each level is a mask over the *same* distance matrix. The distances are
computed once and never recomputed, so no level can be tuned by re-running.

- **(a) as-originally-run.** Reference `j` is scoreable for query `i` iff
  `j != i`. This is exactly `evaluate_composition_external.py`'s
  `if j == i: continue` and nothing else.
- **(b) recording-disjoint.** (a), plus: `j` is excluded if its melodia contour
  is byte-identical to `i`'s. Justification, established before scoring: the
  corpus stores 110 redundant copies of recordings under `_rN` filenames, and
  `work_key()` strips `_r\d+$`, so those copies are counted as separate
  renditions of the same work. A check for *near*-identical contours (length
  within 0.5%, ≥90% of voiced frames agreeing within 5 cents) over all 128
  positive pairs found zero pairs that were near-identical without being
  byte-identical, so the exact test is not merely a weaker version of the
  intended one — on this corpus it is the same test.
- **(c) source-disjoint.** (b), plus: `j` is excluded if it shares `i`'s
  `archive_identifier`, or shares `i`'s artist where artist is known.

## Registered readings

1. **Denominator.** Each level is scored over its *evaluable* queries only —
   those retaining at least one true positive after masking. A query with no
   surviving positive cannot be ranked correctly by any method, so counting it
   as a miss measures corpus depth, not the matcher. Both numbers will be
   printed: top-1 over evaluable n, and, in parentheses, top-1 over all 60 as a
   lower bound. **The evaluable-n figure is the registered headline.**
2. **Chance floor.** Mean over *clips* of (positives surviving the mask /
   references surviving the mask), as `colab_coverhunter_rescore.py` computes
   it. Averaging over works instead is the error that once printed 0.006 for
   0.031.
3. **n is reported before the percentage, at every level**, and if level (c)
   leaves too few evaluable queries the n is the finding.

## Registered sensitivity, non-gating

Artist is recoverable for only 26 of the 60 queries, and for some archive items
the recovered "artist" is a source-page title rather than a performer. Two
distinct identifiers can therefore be one upload: `78RPM-Chittor-V-Nagaiah` and
`78RPM-ChittoorVNagaiah` are the same recordings under two spellings.

**(c′) identifier-family disjoint** is registered here as a *sensitivity on
level (c)*, not as a replacement for it: two identifiers are one family when
their folded forms score `rapidfuzz.fuzz.ratio >= 85`. If (c) and (c′) disagree
materially, both are reported and the lower one is treated as the honest
number. This is declared now, before any distance has been read, precisely so
that it cannot be introduced later as the reading that rescues a result.

## What this audit cannot do

- `evaluate_composition_qmax.py` — the internal Saraga arm, the 66.7% half of
  "60-67%" — **cannot be re-run**: it reads `comp_pitch_cache/` and
  `melodia_cache/`, and neither directory exists. What is scored instead is a
  named reconstruction from the committed `models/qmax_catalog.npz`, differing
  in three declared ways (single pyin-vocal channel rather than the
  min-ensemble; `W_REF` 800 zero-padded rather than 1000 unpadded; `MIN_CHROMA`
  200 rather than 30). Its absolute value is **not** a reproduction of 66.7%
  and must never be quoted as one. Only its level-to-level *delta* is
  interpreted.
- Nothing here speaks to wild 30-60s clips. `ARCHITECTURE.md:72` already
  records Qmax at 0% there, and this audit does not revisit it.
