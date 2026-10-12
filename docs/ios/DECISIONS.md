# iOS v1 decisions

Settled by Deepti in grilling rounds 1 and 2, 2026-10-11. Change only with her say-so.

| # | Decision | Notes |
|---|---|---|
| 1 | v1 shows **raga candidates only**, ranked, never asserted. Composition ID moves to v1.1 (round 2). Lyrics meaning is deferred. | `/identify` took 549 s on a 30 s clip and is weak (8/78 wild top-1). The UI code stays in place behind `AppConfig.compositionEnabled = false`. |
| 1a | **Zero runtime AI spend.** Gemini free tier only, if at all. | Consumer subscriptions (Google AI Pro, ChatGPT Pro, Claude Pro) carry no server API credit, and Drive storage is not app hosting. They *can* be used offline: agent sessions on those plans can pre-generate meaning text into the cached catalog, so the app never calls a paid API. Check lyric/translation copyright before shipping any text. |
| 2 | **Native SwiftUI.** | Matches Codex tooling, gstack ios-qa, preflight scanner. |
| 3 | **Existing Apple Developer account**, the same one Vote4U ships under. | Team `M6L74ZB5KS` is per-account, so it carries over. Bundle `com.shyamravidath.carnatify` OK'd; the App ID and App Store Connect record are not created yet (Phase 2). |
| 4 | **No sign-in.** | Account-deletion rule and Sign in with Apple do not apply. |
| 5 | **Free app, no IAP; hosting at $0.** | Space `shyamravidath/carnatify` (free cpu-basic, sleeps after 48 h idle). `.github/workflows/keep-warm.yml` pings `/health` every 12 h; app has timeout/retry state; review notes explain cold start. |
| 6 | **Server deletes audio after scoring.** No storage, playback, or sharing of recordings. | Privacy label: Audio Data collected, not linked, not used for tracking, not retained. |
| 7 | **Raga engine = `/identify-raga`** (audited `raga_runtime`, gate off, `asserted:false`). | Taken as agreed with round 1 ("I agree with your rule"); confirm if not. Legacy `/predict-audio` gave codec-dependent answers. |
| 8 | **iPhone only, iOS 17+.** | Build with the Xcode 27 SDK; gate newer APIs. |
| 9 | **Ship as fast as possible.** | Target: TestFlight first, submission right after review-risk items clear. |
| 10 | **Bundled "Try a sample" clip** for App Review and users with no music nearby. | Deepti supplies an open-source recording; licence must allow redistribution inside an app (CC0 / CC BY / CC BY-SA; avoid NC/ND). Drop at `ios/Carnatify/Resources/sample-clip.m4a`; button appears automatically. Credit the performer in About if the licence asks. |
| 11 | **Privacy + support pages** live on the Vercel site at `/privacy` and `/support`. | Static pages in `frontend/app/`; support email still a TODO in `frontend/lib/site.ts`. |

Facts checked while settling these:
- No user audio or user-linked data reaches Gemini; it only turns a composition title into meaning text (`src/carnatify/lyrics/meaning_generator.py`). Guideline 5.1.2(i) is not triggered by v1.
