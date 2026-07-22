# AGENT_LOG — shared channel between Fable (Claude) and Codex (GPT-5.6)

This is the ONLY live channel between the two agents. They cannot see each
other's chat; they coordinate by appending here and re-reading before acting.

## Protocol
- **Append, never rewrite.** Add a new dated entry at the bottom; leave prior
  entries intact so the history is legible to both agents and to Deepti.
- **Entry format:** `## [YYYY-MM-DD HH:MM] <AGENT> — <one-line topic>` then the body.
- **Roles are asymmetric (prevents file collisions):**
  - **Codex** = reviewer/ideator. Read-only on source code. Writes proposals,
    critiques, and questions here (and the initial dump in `CODEX_REVIEW.md`).
  - **Fable** = implementer/vetter. The only agent that edits code, runs the
    eval, and commits. Records decisions + the resulting SCORE block here.
- **Evidence, not claims.** When Fable implements something, it pastes the
  verbatim SCORE block from `~/sung_tests` here. No idea graduates on reasoning
  — only when the scoreboard moves. Same-corpus numbers graduate nothing.
- **Before proposing, check the graveyard** (`REVIEW_BRIEF.md §4`) and
  `OPEN_DECISIONS.md`. Do not resurface measured-dead approaches or items
  parked on Deepti.
- Deepti is the clock and the human gate: she tells each agent when to re-read,
  and approves anything that spends money, deploys, pushes, or overwrites a
  production model.

---

## [2026-07-21] Fable (session predecessor) — channel opened
Review doc package committed @ 9f3161f; session handoff @ 1a15923. Current
wild scoreboard: comp top-1 11/78, top-5 18/78, OOC 24/28, raga 18/85.
Codex was pointed at REVIEW_BRIEF.md — its full review should land in
CODEX_REVIEW.md. First real entry below should be Codex's, or Fable's
evaluation of CODEX_REVIEW.md.

<!-- next entry goes here -->
