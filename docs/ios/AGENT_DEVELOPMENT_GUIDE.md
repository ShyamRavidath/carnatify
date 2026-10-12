# Carnatify iOS: agent operating guide

Written 2026-10-11, adapted from the Vote4U guide (`~/voting-finder/ios/AGENT_DEVELOPMENT_GUIDE.md`)
and its tooling inventory (`~/voting-finder/docs/AGENT_TOOLING_INVENTORY.md`). Those two remain the
reference for every installed skill, plugin and MCP on this Mac and their smoke tests; this file
says how they apply to Carnatify. A recipe here is a proposal unless marked **run**.

## 1. Establish the checkout before editing

```bash
git status --short
git branch --show-current
git log -1 --format='%h %s'
git worktree list
rg -n 'IPHONEOS_DEPLOYMENT_TARGET|SWIFT_VERSION|TARGETED_DEVICE_FAMILY|DEVELOPMENT_TEAM' ios/Carnatify.xcodeproj/project.pbxproj
xcodebuild -version
xcrun simctl list runtimes
```

**Run 2026-10-11:** Xcode 27.0 (27A266a), Swift 6.4, runtimes iOS 17.5 and iOS 27.0.
Simulator discovery failing under a sandbox is not proof that runtimes are missing.

## 2. Project contract

| Item | Setting |
| --- | --- |
| Project / scheme | `ios/Carnatify.xcodeproj`, shared scheme `Carnatify` |
| Targets | `Carnatify` (app), `CarnatifyTests` (unit), `CarnatifyUITests` (UI) |
| Bundle IDs | `com.shyamravidath.carnatify`, `.tests`, `.uitests` |
| Team | `M6L74ZB5KS` (assumed: same account as Vote4U; owner to confirm) |
| Deployment target | iOS 17.0, iPhone only, portrait |
| Swift | language mode 5.0, `SWIFT_STRICT_CONCURRENCY = complete` (build is warning-free) |
| Dependencies | Apple frameworks only (SwiftUI, AVFoundation, Observation) |
| Sources | file-system synchronized groups: new files in the folders are picked up automatically |
| Backend | FastAPI `backend/main.py`, hosted on a Hugging Face Space |

Do not raise the deployment target, switch language mode, add packages, or introduce a paid
service because a skill defaults to it.

### Product rules (every screen)
- Results are suggestions. Never assert; `strength == .stronger` still reads as a suggestion.
- Ask for the microphone on the first tap of Listen, never at launch. Show a visible recording state.
- No background audio, no accounts, no analytics SDKs, no tracking.
- The app deletes its local clip when the user leaves the result; the server deletes it after scoring.
- `APIStub` and `StubRecorder` exist only under `#if DEBUG`. DEBUG screenshots are QA evidence, never marketing.

### Code map
| Area | Files |
| --- | --- |
| Entry / DI | `Carnatify/CarnatifyApp.swift`, `Config/AppConfig.swift` (base URL, clip lengths, DEBUG args) |
| Transport | `Services/APIClient.swift` (multipart, timeouts, error mapping), `Models/APIError.swift` |
| Contracts | `Models/RagaIdentification.swift`, `Models/CompositionIdentification.swift` |
| Recording | `Services/AudioRecorder.swift` (AAC-LC m4a, 44.1 kHz mono, 64 kbps, 180 s cap) |
| Flow state | `Features/Listen/ListenModel.swift` (`@Observable @MainActor`) |
| Screens | `Features/Listen/ListenView.swift`, `Features/Results/ResultsView.swift`, `Features/About/AboutView.swift` |
| Privacy | `Carnatify/PrivacyInfo.xcprivacy`, mic string in build settings |
| Tests | `CarnatifyTests/` (decoding against real captured JSON in `Fixtures/`, model flow), `CarnatifyUITests/SmokeTests.swift` |

DEBUG launch arguments: `-stubResult confident|uncertain|error|slow`, `-stubRecorder YES`,
`-apiBaseURL http://127.0.0.1:7860`.

## 3. Which tool for what

| Need | Tool | Note |
| --- | --- | --- |
| SwiftUI implementation | `swiftui-expert-skill` (Codex skills; Claude: install `swiftui-pro`) | Keep iOS 17 APIs; ignore iOS 26 defaults and Liquid Glass unless asked |
| Concurrency diagnostics | `swift-concurrency-expert` / AvdLee skill | Smallest correct fix; no unjustified `@unchecked Sendable` |
| Build / simulator | XcodeBuildMCP (Codex, pinned 2.7.0) or shell `xcodebuild` | One build owner at a time; dedicated DerivedData |
| Xcode docs / diagnostics | Xcode MCP `xcrun mcpbridge` | Discovery calls first |
| Live-device QA | gstack `/ios-qa`, `/ios-design-review` | Optional DebugBridge; ask owner first; prove Release exclusion |
| Rejection scan | `app-store-preflight-skills` | Needs `asc` for metadata; source scan works offline. Heuristic, not a guarantee |
| Store listing | `aso-audit` | After the listing draft exists |
| Icon | not `app-icon` (Expo-only, billed) | Use the native asset catalog |
| Planning / review | gstack `plan-eng-review`, `review`, `cso`; Pocock `grilling`, `tdd`, `diagnosing-bugs` | Reviews never authorise deploys |

gstack ship/land skills may merge or deploy: stop at commit; the owner pushes.

## 4. Build and test

Small build loop (**run** 2026-10-11, succeeded, zero Swift warnings):
```bash
xcodebuild -project ios/Carnatify.xcodeproj -scheme Carnatify \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /private/tmp/carnatify-agent-build build
```

Acceptance tests on a fresh, dedicated Simulator (so other agents' Simulators are untouched),
deployment-era runtime first, then modern (**run** on 17.5: 9 unit + 2 UI tests, all passed):
```bash
SIM=$(xcrun simctl create carnatify-agent-175 com.apple.CoreSimulator.SimDeviceType.iPhone-15-Pro \
      com.apple.CoreSimulator.SimRuntime.iOS-17-5)
xcodebuild -project ios/Carnatify.xcodeproj -scheme Carnatify -destination "id=$SIM" \
  -derivedDataPath /private/tmp/carnatify-agent-tests-175 test
xcrun simctl delete "$SIM"
```
Repeat with `iPhone-17` / `iOS-27-0` before release. Read executed counts; a skip is not a pass.

Backend: `venv_train/bin/python -m pytest -q` (517+ tests). Run when touching `backend/` or the contract.

Visual check: install the built app, launch with stub args, `xcrun simctl io "$SIM" screenshot`,
then actually open the image. Check light/dark and the largest accessibility text size.

## 5. Behaviour matrix

| Area | Verify |
| --- | --- |
| Permission | first-tap prompt; deny then Settings link; revoke in Settings while app is backgrounded |
| Recording | indicator visible; Done disabled under 15 s; auto-finish at 180 s; Cancel deletes the clip; phone call interruption |
| Network | success; 415/422/429/503 mapped to friendly copy; airplane mode; slow server (`-stubResult slow`) |
| Results | strong vs tentative copy; empty candidates; composition loading/loaded/none/failed; Listen again resets |
| Visual / a11y | small and large phones; dark mode; AX5 text; VoiceOver order on results |

## 6. Release procedure (owner-gated)

1. Backend fixes from `BACKEND_READINESS.md` deployed and the Space answering `/health`.
2. Native tests on 17.5 and 27.0; Release build; confirm no DEBUG stub symbols in the Release binary.
3. Privacy: manifest, nutrition label (Audio Data, not linked, app functionality), privacy policy URL live.
4. Physical iPhone: permission flow, a real 3-minute recording, results, offline state.
5. Archive with a unique build number; Deepti uploads to TestFlight and submits. Agents never submit.

Apple's [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) are the
source of truth; preflight skills are heuristics.

## 7. Completion report

```text
Outcome: behaviour and material changes.
Checkout: branch, commit, dirty files excluded, build settings touched.
Tools: skills read; tools used; unavailable tools and fallback.
Validation: exact command, device/runtime, executed/pass/fail/skip counts.
Evidence: screenshots, logs.
Limits: unperformed checks, gates not reached.
Delivery: commit; owner actions still needed.
```
