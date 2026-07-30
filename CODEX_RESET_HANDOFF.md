# CODEX_RESET_HANDOFF — pre-reset close-out (send this, then clear Codex)

Deepti is about to reset your context. Before that, flush anything that lives
only in your working memory so nothing is lost. This is a wind-down prompt, not
a new task — do NOT start new code.

Do these, in order:

1. **Confirm deliverables are on disk.** Verify these exist and are complete:
   - `scripts/detect_workfamily_dupes.py`
   - `data/workfamily_candidates.json`
   - your AGENT_LOG entry `## [2026-07-23] Codex — systematic wild-truth
     work-family candidate detector complete`
   If anything is missing or half-written, say so explicitly — do not fix it now.

2. **Dump residual knowledge to AGENT_LOG.** Append ONE new dated entry titled
   `## [2026-07-23] Codex — pre-reset handoff notes` capturing anything a fresh
   Codex could not reconstruct from the files alone:
   - Any design decisions / rejected approaches behind the work-family detector
     not already written in the script docstring or the prior log entry.
   - Your read on the **30 low-confidence** candidate pairs in
     `data/workfamily_candidates.json`: which you believe are genuine
     truncation-families vs. traps, and why. (Opus verified the 3 high pairs and
     found them true-but-score-neutral; the low tier is still unreviewed.)
   - Any half-formed next ideas you had queued, so they are not lost.
   Keep it to what only you know. Do not restate the file contents.

3. **State completion.** End with a one-line "safe to reset" confirmation.

No commits, no pushes, no manifest/registry/matcher edits, no new scripts.
After you reply, Deepti clears you and launches a fresh Codex with a new brief.
