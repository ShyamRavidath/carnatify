# iOS v1 decisions

Settled by Deepti in grilling round 1, 2026-10-11. Change only with her say-so.

| # | Decision | Notes |
|---|---|---|
| 1 | v1 shows **raga candidates + composition candidates**, ranked, never asserted. Lyrics meaning is deferred. | Composition ID is weak (8/78 wild top-1), so UI wording must stay "possible matches". |
| 1a | **Zero runtime AI spend.** Gemini free tier only, if at all. | Consumer subscriptions (Google AI Pro, ChatGPT Pro, Claude Pro) carry no server API credit, and Drive storage is not app hosting. They *can* be used offline: agent sessions on those plans can pre-generate meaning text into the cached catalog, so the app never calls a paid API. Check lyric/translation copyright before shipping any text. |
| 2 | **Native SwiftUI.** | Matches Codex tooling, gstack ios-qa, preflight scanner. |
| 3 | **Existing Apple Developer account** (Deepti's family account). | Project assumes team `M6L74ZB5KS` (the Vote4U team on this Mac) and bundle `com.shyamravidath.carnatify`; confirm. |
| 4 | **No sign-in.** | Account-deletion rule and Sign in with Apple do not apply. |
| 5 | **Free app, no IAP; keep hosting at $0** if possible. | Free HF Space sleeps after idle. Plan: free scheduled keep-warm ping + in-app timeout/retry state + review notes. |
| 6 | **Server deletes audio after scoring.** No storage, playback, or sharing of recordings. | Privacy label: Audio Data collected, not linked, not used for tracking, not retained. |
| 7 | **Raga engine = `/identify-raga`** (audited `raga_runtime`, gate off, `asserted:false`). | Taken as agreed with round 1 ("I agree with your rule"); confirm if not. Legacy `/predict-audio` gave codec-dependent answers. |
| 8 | **iPhone only, iOS 17+.** | Build with the Xcode 27 SDK; gate newer APIs. |
| 9 | **Ship as fast as possible.** | Target: TestFlight first, submission right after review-risk items clear. |

Facts checked while settling these:
- No user audio or user-linked data reaches Gemini; it only turns a composition title into meaning text (`src/carnatify/lyrics/meaning_generator.py`). Guideline 5.1.2(i) is not triggered by v1.
