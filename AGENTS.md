# Carnatify: instructions for Codex and other agents

Claude Code reads `CLAUDE.md`; Codex reads this file. Both point at the same docs.

## Read first, in order
1. `docs/ios/AGENT_DEVELOPMENT_GUIDE.md`: how iOS work is done here (commands, gates, rules).
2. `docs/ios/DECISIONS.md`: owner decisions. Do not reopen them without Deepti.
3. `docs/ios/PLAN.md`: phase checklist and what is still open.
4. `docs/ios/BACKEND_READINESS.md`: backend contract, measured behaviour, known gaps.
5. `HANDOFF.md` top section: ML/backend state. Its rules on prereg, frozen data and labels apply.

## Hard rules
- Never assert a raga or composition. The server returns `asserted: false`; UI copy says "possible".
- Audio is deleted after scoring. Never log, persist, or upload user audio, transcripts with IPs, or device identifiers.
- No paid services and no runtime AI spend without Deepti's say-so.
- `data/long_concerts/LABELS.tsv` and `.claude/settings.local.json` are Deepti's. Never edit them.
- Pushes, deploys, TestFlight uploads and App Review submissions are Deepti's actions. Stop at commit.
- Use targeted `git add`; other agents may be working in this checkout.
- Python tests: `venv_train/bin/python -m pytest`. iOS tests: see the guide.

## Agent skills
Issue tracker is local markdown under `.scratch/` (see `docs/agents/issue-tracker.md`).
