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
- [x] Feature scoping (grilling): rounds 1 and 2 settled -> `docs/ios/DECISIONS.md`. v1 is raga-only.
- [~] Backend fixes: byte-sniffed upload formats, no server paths in responses, no IP in persisted logs, raga candidate copied into the Space build (done, tested). Keep-warm Action added (`.github/workflows/keep-warm.yml`, live once pushed); `/identify` dropped from v1. Deferred past v1: error envelope, `/v1` prefix, upload size check before full read.
- [ ] (post-v1) Stable versioned API contract (`/v1/...`) + OpenAPI JSON checked in for the Swift client.
- [x] Space `shyamravidath/carnatify` redeployed 2026-10-11 with `backend/deploy_space.sh`; `/health` ok; live `/identify-raga` verified (see BACKEND_READINESS.md, "Live check").

## Phase 1: core app (Claude-heavy)
- [x] Xcode project skeleton, SwiftUI, record -> upload -> results flow (15 tests green on iOS 17.5 and iOS 27.0).
- [x] Mic permission flow + purpose string; recording UI with level meter and a length guide.
- [x] Results screen: ranked candidates shown as candidates, never asserted.
- [x] Error, offline and slow-server states (review testers hit these).
- [x] Privacy policy + support pages written (`frontend/app/privacy`, `frontend/app/support`). Deepti deploys to Vercel; support email ravidath@gmail.com.
- [x] Composition hidden behind `AppConfig.compositionEnabled = false`; About copy matches.
- [x] "Try a sample" flow; button appears when `ios/Carnatify/Resources/sample-clip.m4a` exists.

## Phase 2: hardening + submission (Codex-heavy)

**Codex: start here.** Core app and backend are done and live. Your queue, in order:
1. Build + run on Simulator against the live server (`-apiBaseURL` not needed; production URL is set). Record a real clip by playing `data/long_concerts/audio/long_concert_2.mp3` from 16:00 near the Mac mic, Expect Hindōḷaṁ top-1.
2. App icon: 1024x1024 in `Assets.xcassets/AppIcon` (no alpha). Ask Deepti for art direction or propose one.
3. Register App ID `com.shyamravidath.carnatify` and create the App Store Connect record (team `M6L74ZB5KS`, `asc` CLI). Deepti approves any account action.
4. Privacy nutrition label: Audio Data, collected, not linked, not tracking, app functionality. Age rating questionnaire. Category: Music.
5. Screenshots (6.9" and 6.5" iPhone) from Simulator: idle, recording, results.
6. Run `app-store-preflight-skills`; fix every finding.
7. Review notes draft: what the app does; v1 has no bundled sample, so tell the reviewer to play a public Carnatic recording (pick a stable YouTube link of a well-known Hindolam or Bhairavi kriti, ask Deepti to approve it) near the phone for 1-3 min; first request may take up to a minute if the server was idle.
8. Archive + TestFlight upload is Deepti's action: prepare the exact commands and stop.
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
- [ ] (post-launch update) Sample clip file: Deepti picks an open-licence recording (CC0 / CC BY / CC BY-SA); trim to ~180 s, AAC m4a.
- [x] Live Space URL confirmed in `AppConfig.productionBaseURL`.
- [x] Tests run on iOS 27.0 too.
