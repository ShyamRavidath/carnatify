# Red-team review — rebuilt negative arm, round 2 (GPT-5.6)

Date: 2026-07-29. Response to `CODEX_NEGATIVE_ARM_REBUILD_BRIEF.md`.

**Provenance:** the brief did not name an output file, so this review existed
only in the Codex session transcript
(`~/.codex/sessions/2026/07/28/rollout-2026-07-28T01-47-23-*.jsonl`, final
assistant message). It is reproduced verbatim below, unedited. Codex made no
repository changes, as instructed.

Verified independently before acting (see `WORKHORSE_NEGATIVE_ARM_REPAIR_BRIEF.md`
§0): the sweep gap arithmetic, the absence of per-source reporting in the
scorer, the 26/21/4 gating composition, and the named validator holes. One claim
did **not** reproduce — see that file.

---

Verdict: **do not spend the 45 negative Whisper-hours as staged.** The rebuild is much stronger, and its core upper-bound arithmetic is sound, but four pre-GPU defects remain.

## P0 findings

1. The labels still do not cover the scored audio

The sweep in [build_negative_arm.py](/Users/shyamravidath/carnatify/scripts/build_negative_arm.py:216) covers:

- 0–10s, 20–30s, …, 280–290s;
- fifteen unseen 10-second gaps, including 290–300s.

The “maximum unheard gap is 10s” claim is arithmetically correct. The stronger claim that the ear “confirmed [the window] carries no sung words” is not.

Any sung passage up to 10 seconds can be missed completely. A slightly longer phrase can be represented by only a fragment, potentially too short to recognize. That matters specifically for a lyrics matcher: one short pallavi phrase in an unheard gap can be enough to produce an answer.

Cheapest repair: listen to a complementary scan containing the omitted 150 seconds for the 51 current no-sahitya items. Maximum additional listening is 127.5 minutes, with no GPU. Only items negative across both halves should gate.

2. The pooled SAFE target is an arbitrary design mixture

The gating n=51 consists of:

- 26 free-form windows;
- 21 opening windows;
- 4 unidentified-source windows.

The opening argument is only half-right. Adjudicating the exact window prevents anchor choice from corrupting an individual label, but it does not make the sources one population. Their 26:21:4 weights arose from sampling quotas and labeling yield, not from product prevalence.

The preregistration promises that each source is reported separately at [DURATION_PROBE_PREREGISTRATION.md](/Users/shyamravidath/carnatify/DURATION_PROBE_PREREGISTRATION.md:207). The scorer does not do that: it groups only by `stratum`.

This can conceal a large source-specific failure. If all three new bluffs occur in one source:

- pooled: 3/51, upper bound 14.5%, declared SAFE;
- free-form: 3/26, upper bound 27.2%;
- opening: 3/21, upper bound 32.9%.

The pooled bound is valid only for this design-weighted mixture. It does not establish safety for either source or for an unspecified product population.

Before inference, either:

- freeze product-relevant source weights; or
- require source-specific safety as a conjunction.

With current n, each major source can rule out +15pp only if it observes zero new bluffs.

3. “Combined PROMOTE” still lacks OOC safety

The conjunction’s mathematics is reasonable, but its product interpretation is not. Only no-sahitya gates; OOC remains unmeasured. Yet the scorer prints:

> PROMOTE. Longer listening buys in-catalog recall without a ruled-in bluff rise.

That should say “without a ruled-in no-sahitya bluff rise.” `METRIC_CONTRACT.md` still requires OOC bluffs separately.

The document is internally inconsistent:

- §6c permits combined PROMOTE;
- §7 correctly says the probe cannot license safe OOC abstention;
- the HOLD row implies only a failed no-sahitya arm prevents user-facing authorization.

A successful current conjunction can promote duration as an archive-domain research lever. It cannot promote product presentation safety.

4. The negative validity gate can still print SAFE on a broken run

Concrete holes in [validate_negatives()](/Users/shyamravidath/carnatify/scripts/duration_probe_score.py:386):

- It trusts whatever durations the sidecar registers. A sidecar containing only 300s passes; then `short == long`, `b == 0`, and n=51 would print SAFE with a 5.7% upper bound.
- It does not require exactly one row per item-duration. I confirmed duplicate item-duration metadata passes validation.
- It does not require the same stratum for an item at both endpoints.
- It does not validate `n_items`, `stratum_counts`, cluster uniqueness, seed, or the frozen `{30,300}` design.
- It rejects only explicit `cache_v2 == "MISS"`. A missing or malformed cache field passes.
- It does not validate result schema. Missing `composition_confidence` is treated as answered because `None != "none"`; if missing at both endpoints, this creates `b=0` and can falsely print SAFE.
- It does not bind labeled audio to inference audio with a SHA. Correct filenames containing swapped or regenerated audio can validate.

These should be closed before packaging the run.

## Statistical challenges that survive red-teaming

The n=51 arithmetic is correct:

| b | one-sided 95% upper bound |
|---:|---:|
| 0 | 5.705% |
| 1 | 8.967% |
| 2 | 11.835% |
| 3 | 14.508% |
| 4 | 17.056% |

Ignoring reverse flips is genuinely conservative for the registered net-change estimand:

\[
\Delta_{\text{answer}} = P(0\to1)-P(1\to0) \le P(0\to1).
\]

Therefore, a valid upper bound on `b/n` is also an upper bound on the net change. That part should stay.

The conjunction also does not inherently require a multiplicity penalty. It is an intersection-union decision: PROMOTE requires both component nulls to be rejected. If each component test is valid at one-sided 5%, the combined false-PROMOTE rate is at most 5%, regardless of dependence. Simultaneous coverage of both displayed intervals is only guaranteed at 90%, but the conjunction itself does not inflate to 10%.

One rationale is stale: detection is no longer “unreachable.” Under the favorable no-reverse-flip model, n=51 has about 89.8% power to detect a true +15pp rise. The upper-bound formulation is still the more useful safety question, but it is no longer mathematically forced by sample size.

## Additional issues

- `neg030` is not automatically a safe exclusion. If it contains only swaram, it meets the registered no-sahitya definition. Solfège is plausibly a high-bluff input for Whisper, so excluding it can bias safety downward—not merely shrink n. Resolve this definition before seeing predictions.
- The two unknowns are informative missingness, not random loss. One is unusable; the blank is in row 42 and labeling continued afterward. If both were true no-sahitya/new-bluff cases, observed `b=2` would become 4/53, whose upper bound is 16.4% rather than SAFE. Report a worst-case unknown sensitivity.
- The sidecar has 51 unique cluster strings, but 17 are synthetic `solo:<path>` clusters caused by absent manifest identifiers. That proves no repeated string, not 51 independently verified archives.
- Relaxed matching is safe for the specificity of retained OOC cases, but not for completeness or the assertion that OOC is absent. False collisions can systematically exclude short or vowel-heavy genuine OOC titles. The current relaxed-only list contains obvious false matches such as `B - Harikambhoji` and several Melakartha lecture tracks.
- The claim that OOC requires wholly new discovery is too strong. `~/sung_tests/fetch_manifest.tsv` retains source URLs and source durations; at least 14 reviewed OOC sources appear to exceed 300 seconds. They would require reacquisition, but their identities and acquisition paths already exist.
- The 28 existing OOC clips can cheaply support a nested 30s→full-clip, 43–84s sensitivity arm. At n=28, zero new bluffs gives a 10.2% upper bound; one gives 15.9%. This cannot establish 300s safety, but it is a useful product-90s sentinel and can reuse existing full-clip caches.

The positive-pool no-op is real: I independently reproduced 923 distinct keys, 505 no-lyrics, 271 resolved, 117 too short, and 30 unmatched. The title repair changed keys without changing positive membership.

## Cheapest sufficient next design

Before GPU:

1. Listen to the complementary 150 seconds for the 51 provisional no-sahitya windows.
2. Resolve `neg030` and audit whether any other `sahitya` exclusions were actually swaram/tanam.
3. Freeze either source-specific gates or explicit mixture weights.
4. Add worst-case handling for the two unknowns.
5. Close the concrete validator holes above.
6. Add the cheap 28-clip short-OOC sensitivity arm.

If the goal remains only the no-sahitya research gate, transcribe the final gating items only. At n=51 that is approximately **33 Whisper-hours**, not 45; the 19 in-catalog, sung-unidentified, and unknown items do not affect the registered safety verdict.

If a product-facing combined verdict is required, defer that verdict until a long verified OOC arm exists. The available source manifest provides a practical starting point.

No source or documentation files were edited. One caveat: the ostensibly read-only `duration_probe_cut.py --dry-run` command regenerated the already-untracked `data/duration_probe/pool_report.json`; the script’s dry-run mode has that side effect.