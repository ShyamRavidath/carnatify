# OPEN DECISIONS — waiting on Deepti

Written 2026-07-20. These are blocked on a human, not on work. An incoming
reviewing agent should NOT propose these as if they were undiscovered — they
are known and parked on a decision. Update or delete lines as they resolve.

## Blocked on Deepti — action

1. **Push 5 unpushed commits.** `main` is 5 ahead of `origin` (2e611ea →
   bcb89be). Pushes are Deepti-run (agent pushes blocked). Nothing new should
   be committed on top without deciding this first.
2. **Deploy the staged backend + confirm-button frontend.** `/identify` +
   `/feedback` are built and staged, not deployed. Precondition: create the
   private HF feedback dataset BEFORE go-live (Space disk is ephemeral).
   Deploys are Deepti-run. This is the flywheel — everything data-hungry
   downstream is gated on it.
3. **Raga model swap sign-off.** `models/raga_classifier.pkl` (production,
   40.5%) must not be overwritten without explicit approval.
4. **Meanings batch — stays UNSUBMITTED.** ~$3.54 Claude Haiku batch, gated on
   `CARNATIFY_BILLING_OK=1`. Deepti explicitly declined 2026-07-19. Do not
   re-ask soon; do not propose as a next step.

## Blocked on Deepti — musical judgment (agent must not resolve silently)

5. **Kurai Onrum Illai** raga label — registry says Rāgamālika; her 60 s window
   may be the Sindhubhairavi section. Needs her ear.
6. **Paluke Bangaramayena** raga label — registry says Ānandabhairavi. Needs
   her ear. (For both: registry raga metadata was deliberately NOT trusted over
   her labels — devaranama ragas vary by rendition.)
7. **`rAma nannu brOvara` clip** — it is Mandolin U. Shrinivas (instrumental,
   ASR-dead by design, raga-only value). Keep as a raga-only test case, or
   replace with a sung rendition? Her call.

## Parked by the agent — decide when convenient

8. **Transcript cache commit-or-strip.** `data/whisper_transcripts_turbo.json`
   is tracked and now holds real 106-clip entries (good) mixed with ~90
   synth/control entries from the 0719a evals (should not ship). The synth
   entries are filename-identifiable. Strip them before the next scoreboard
   commit or the eval cache ships poisoned.
9. **`composition_evaluator.py` deletion.** Zero references in the repo; the
   one genuinely safe removal. Deepti said "fix that later" (2026-07-20) —
   left annotated as DEAD for now.
10. **Legacy backend endpoints.** Two endpoints in `backend/main.py` still
    serve the old ~16% DTW matcher via `carnatify.ml.composition_matcher`.
    Retiring them is the precondition for deleting the melody-path graveyard
    modules (they ship because `build_space.sh` copies all of `src/`).

## Resolved recently (for context, do not redo)

- Wild set re-baselined on 106 clips (2026-07-20): comp top-1 11/78,
  OOC 24/28. No code regression. See memory `wild-test-set-status`.
- Dead/legacy `src/carnatify/ml/` modules annotated with STATUS banners;
  `ARCHITECTURE.md` written.
- `HANDOFF_VERFIER.md` rewritten from a (stale) state ledger into a
  verification protocol.
