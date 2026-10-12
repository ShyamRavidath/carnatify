# Carnatify iOS: ship plan

Started 2026-10-11. Owner: Deepti. Builders: Claude Code (core + backend + Swift scaffolding),
Codex (Xcode build/test, signing, App Store Connect, submission).
Decisions are recorded in `docs/ios/DECISIONS.md` as the grilling rounds settle them.

## Phase 0: prep (now, while LABELS.tsv is finished)
- [x] Tests green on the working branch (517 passed, 1 xfailed, 2026-10-11).
- [x] Labels-to-intervals converter, so field scoring is one command when labels land.
- [x] Pocock skills configured (`.scratch/` tracker).
- [x] iOS skill research: `docs/ios/SKILLS_RESEARCH.md`.
- [x] Backend readiness audit: `docs/ios/BACKEND_READINESS.md`.
- [~] Feature scoping (grilling): round 1 settled; round 2 open -> `docs/ios/DECISIONS.md` -> spec in `.scratch/ios-v1/spec.md`.
- [~] Backend fixes: byte-sniffed upload formats, no server paths in responses, no IP in persisted logs, raga candidate copied into the Space build (done, tested). Still open: always-on host / keep-warm, `/identify` async jobs or drop from v1, error envelope, `/v1` prefix, upload size check before full read.
- [ ] Stable versioned API contract (`/v1/...`) + OpenAPI JSON checked in for the Swift client.

## Phase 1: core app (Claude-heavy)
- [x] Xcode project skeleton, SwiftUI, record -> upload -> results flow (11 tests green on iOS 17.5).
- [x] Mic permission flow + purpose string; recording UI with level meter and a length guide.
- [x] Results screen: ranked candidates shown as candidates, never asserted.
- [x] Error, offline and slow-server states (review testers hit these).
- [ ] Privacy policy page + support URL (app links to carnatify.vercel.app/privacy and /support; pages not written yet) (hosted, linked from app and listing).

## Phase 2: hardening + submission (Codex-heavy)
- [ ] Simulator + device testing, gstack `/ios-qa`.
- [ ] `PrivacyInfo.xcprivacy`, privacy nutrition labels, age rating.
- [ ] `app-store-preflight-skills` scan; fix every finding.
- [ ] Always-on backend for review (no cold start), review notes explaining how to test.
- [ ] TestFlight, then submission.

## Blocking facts to settle early
- Apple Developer Program enrollment: who enrolls and pays, and under whose name the app is sold.
- Backend hosting that stays awake during App Review.

## Still open in Phase 1
- [ ] App icon (asset catalog has an empty 1024 slot).
- [ ] Sample clip for App Review ("Try a sample"), pending a clip with clear rights.
- [ ] Confirm the live Space URL in `AppConfig.productionBaseURL`.
- [ ] Run tests on iOS 27.0 too.
