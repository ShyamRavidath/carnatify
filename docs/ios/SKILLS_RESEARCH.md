# iOS Tooling + App Store Risk Research (2026-10-11)

Scope: what agent tooling to add for shipping Carnatify to the App Store fast, split between
Claude Code (app logic, backend, review) and Codex (Xcode build/test/App Store config).
Star counts and push dates are from `gh api` on 2026-10-11. Nothing was installed.
"UNVERIFIED" marks anything not confirmed against a primary source.

## 0. What is already on this machine (local inspection)

Machine has **Xcode 27.0 (27A266a)**. `asc` and `fastlane` are **not installed**.

**Claude Code (`~/.claude/skills`, plugins):**
| Item | Covers | Notes |
|---|---|---|
| app-store-preflight-skills (truongduy2611, 1.4k stars, last push 2026-05-29) | Rejection-pattern checklists by app type (all_apps, ai_apps, social_ugc, kids...), metadata, privacy manifest, entitlements | **Needs the `asc` CLI, which is not installed.** No audio/mic-specific checklist; use `all_apps.md` + `ai_apps.md` |
| gstack ios-qa / ios-fix / ios-design-review / ios-sync / ios-clean | Live **real-iPhone** QA over USB via an embedded DebugBridge/StateServer, vision loop | SwiftUI only. Adds `#if DEBUG` SPM package; `ios-clean` removes it before release |
| app-icon | Icon generation | **Expo-only** |
| aso-audit, apple-search-ads | Post-launch listing/ads | Not needed to ship |
| plugins: codex@openai-codex, mattpocock-skills | Codex bridge, general TS skills | No iOS content |
No SwiftUI, Swift-concurrency, Xcode-build, or simulator tooling is wired into Claude Code yet.

**Codex (`~/.codex`) already has a full native-iOS stack:**
- MCP: `xcodebuild` (`npx -y xcodebuildmcp@2.7.0 mcp`, enabled), `xcode` (`xcrun mcpbridge`, Apple's
  Xcode agent bridge), `ios-simulator` (ios-simulator-mcp@2.1.0, **disabled**; its screenshot dir points at
  `~/voting-finder/ios`, from another project).
- Plugin `build-ios-apps@openai-curated` (enabled, OpenAI-curated): ios-debugger-agent (XcodeBuildMCP-backed),
  ios-simulator-browser, ios-ettrace-performance, ios-memgraph-leaks, ios-app-intents, swiftui-* (4).
- Skills in `~/.codex/skills`: swiftui-pro (Paul Hudson), swiftui-expert-skill (AvdLee),
  swift-concurrency-expert, swiftui-liquid-glass, swiftui-performance-audit, swiftui-ui-patterns, swiftui-view-refactor.
- `~/.codex/AGENTS.md` exists but is empty (0 bytes).

**Takeaway:** Codex needs almost nothing. The gaps are on the Claude Code side (SwiftUI/concurrency
guidance so its Swift code matches what Codex expects) plus the `asc` CLI, which both agents can use.

## 1. Candidates (verified to exist)

### Apple / Anthropic / OpenAI official
| Name | Source | What it does | Install | Signal | Duplicate? |
|---|---|---|---|---|---|
| **Xcode agent bridge** (`xcrun mcpbridge`) | Apple; [docs](https://developer.apple.com/documentation/xcode/giving-agentic-coding-tools-access-to-xcode), WWDC26 ["Xcode, agents, and you"](https://developer.apple.com/videos/play/wwdc2026/259/) | Exposes Xcode's own tools to external agents: build, tests, SwiftUI preview rendering, Apple doc search, project settings. Added in Xcode 26.3, expanded in Xcode 27 | `claude mcp add --transport stdio xcode -- xcrun mcpbridge` (command per [swiftjectivec](https://swiftjectivec.com/Agentic-Coding-Codex-Claude-Code-in-Xcode/); same pattern as Codex's config) | Ships with Xcode, nothing to install | Codex has it; Claude Code does not |
| Xcode built-in Claude Agent / Codex | Apple (Xcode 26.3+, Settings > Intelligence) | Runs Claude or Codex *inside* Xcode with the tools above | Xcode settings | Official | Different way to work, not a skill |
| **swift-lsp** | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) `plugins/swift-lsp` (37.7k stars, pushed 2026-10-11) | Swift language server (sourcekit-lsp) diagnostics for Claude Code | `claude plugin install swift-lsp@claude-plugins-official` | Anthropic-managed | No |
| **expo** plugin | [expo/skills](https://github.com/expo/skills) (2.8k stars, pushed 2026-10-07) | 24 skills (expo-router, eas-app-stores, eas-workflows, expo-ui, upgrade...) plus the remote Expo MCP server (docs and EAS access) | `claude plugin install expo@claude-plugins-official` then `/mcp` to sign in to Expo; Codex: `codex plugin add expo@openai-curated` | Official Expo, listed in Anthropic's directory | Only matters if you pick Expo |
| build-ios-apps | OpenAI curated ([openai/plugins](https://github.com/openai/plugins), 7.4k stars) | See section 0 | already enabled in Codex | Official OpenAI | Already installed (Codex) |

### Community (well maintained)
| Name | Source | What it does | Install (Claude Code) | Signal | Duplicate? |
|---|---|---|---|---|---|
| **asc CLI** | [rorkai/App-Store-Connect-CLI](https://github.com/rorkai/App-Store-Connect-CLI) (old URL rudrankriyam/... redirects) | Scriptable App Store Connect API client: builds, TestFlight, metadata, submissions, signing | `brew install asc` | 7.8k stars, pushed 2026-10-12. Unofficial, not affiliated with Apple | **Required by the preflight skill you already have** |
| **asc skills** | [rorkai/app-store-connect-cli-skills](https://github.com/rorkai/app-store-connect-cli-skills) | 25 skills: asc-release-flow, asc-submission-health, asc-testflight-orchestration, asc-signing-setup, asc-metadata-sync, asc-xcode-build, asc-shots-pipeline, asc-whats-new-writer... | `claude plugin marketplace add rorkai/app-store-connect-cli-skills` then `claude plugin install asc@rorkai`. Codex: `npx skills add rorkai/app-store-connect-cli-skills --agent codex` | 1.1k stars, pushed 2026-10-05 | `asc-aso-audit` and `asc-apple-ads` overlap aso-audit / apple-search-ads |
| **XcodeBuildMCP, now called MobileBuildMCP** | [getsentry/MobileBuildMCP](https://github.com/getsentry/MobileBuildMCP) (renamed from cameroncooke/XcodeBuildMCP, then getsentry/XcodeBuildMCP) | MCP + CLI: simulator/device build, run, test, logs, UI automation, screenshots | `claude mcp add MobileBuildMCP -- npx -y mobilebuildmcp@2.7.1 mcp` (npm `mobilebuildmcp` 2.7.1; old `xcodebuildmcp` package stopped at 2.7.0, 2026-07-23) | 6.5k stars, pushed 2026-10-09, run by Sentry. **Sends Sentry error telemetry by default**; opt-out is in its privacy doc | Codex has it (old package name). Overlaps the Xcode bridge for builds; better for simulator UI automation |
| **swiftui-pro** (Paul Hudson) | [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill) | SwiftUI review aimed at common LLM mistakes (deprecated APIs, accessibility, performance) | `/plugin marketplace add twostraws/SwiftUI-Agent-Skill` then `/plugin install swiftui-pro@swiftui-agent-skill` | 5.8k stars, pushed 2026-10-07 | Codex has it |
| swiftui-expert-skill (Antoine van der Lee) | [AvdLee/SwiftUI-Agent-Skill](https://github.com/AvdLee/SwiftUI-Agent-Skill) | Broad SwiftUI guidance: state, @Observable, layout, Liquid Glass, Instruments | `/plugin marketplace add AvdLee/SwiftUI-Agent-Skill` then `/plugin install swiftui-expert@swiftui-expert-skill` | 3.7k stars, pushed 2026-10-06 | Codex has it; overlaps swiftui-pro, so install one |
| **Swift Concurrency skill** (AvdLee) | [AvdLee/Swift-Concurrency-Agent-Skill](https://github.com/AvdLee/Swift-Concurrency-Agent-Skill) | Swift 6 strict concurrency: Sendable, actors, @MainActor, migration | `/plugin marketplace add AvdLee/Swift-Concurrency-Agent-Skill` then `/plugin install swift-concurrency@swift-concurrency-agent-skill` | 1.7k stars, pushed 2026-09-14 | Codex has a different one (swift-concurrency-expert) |
| ios-simulator-mcp | [joshuayoes/ios-simulator-mcp](https://github.com/joshuayoes/ios-simulator-mcp) | Simulator tap/type/swipe/screenshot/a11y tree | `claude mcp add ios-simulator -- npx -y ios-simulator-mcp@2.1.0` | 2.2k stars, pushed 2026-08-13 | Covered by MobileBuildMCP UI automation; disabled in Codex |
| ios-simulator-skill | [conorluddy/ios-simulator-skill](https://github.com/conorluddy/ios-simulator-skill) | Script-based simulator control skill | `/plugin marketplace add conorluddy/ios-simulator-skill` | 1.3k stars, pushed 2026-10-06 | Overlaps the above |
| apple-skills | [rshankras/claude-code-apple-skills](https://github.com/rshankras/claude-code-apple-skills) (in Anthropic's plugin directory cache) | 23 category skills: privacy manifests, privacy policy/ToS generation, rejection handling, HIG, release checklist | `/plugin marketplace add rshankras/claude-code-apple-skills` then `/plugin install apple-skills@indie-apple-stack` | 790 stars, pushed 2026-07-24; tracks `main` unpinned | Overlaps preflight + aso-audit. Its **privacy-policy and privacy-manifest** skills are the parts that aren't duplicated |
| Swift-Agent-Skills index | [twostraws/Swift-Agent-Skills](https://github.com/twostraws/Swift-Agent-Skills) | Curated directory, not a skill | none | 2.8k stars | Use to look things up |
| fastlane | [fastlane/fastlane](https://github.com/fastlane/fastlane) (42k stars, pushed 2026-10-10) | Classic Ruby release automation (match, gym, deliver, pilot) | `brew install fastlane` | Mature | **Skip:** asc + Xcode cloud signing cover a single-app indie ship with less setup (Ruby toolchain) |

Not recommended or not verified: Dimillian/Skills (4k stars, last push 2026-03-29, gone stale; its best
skills are already in OpenAI's build-ios-apps). The "Swift FocusEngine Pro", "Mobile Design System" and
similar entries in the plugin directory were not checked, so they are not recommended. One blog says Xcode 27
ships Gemini/GPT agents and an "Agent Client Protocol" (aimadetools.com); Apple's pages don't confirm it, so treat it as UNVERIFIED.

## 2. App Store rejection risk: mic-recording to server-side ML identification

Guidelines: https://developer.apple.com/app-store/review/guidelines/ (anchors below confirmed on the live page).

**[5.1.1 Data Collection and Storage](https://developer.apple.com/app-store/review/guidelines/#5.1.1)** (highest risk)
- (ii) Purpose string. `NSMicrophoneUsageDescription` ([doc](https://developer.apple.com/documentation/bundleresources/information-property-list/nsmicrophoneusagedescription))
  must "clearly and completely describe" the use. If the key is missing, the app crashes on first record.
  Vague strings ("needs mic access") get rejected. Suggested text: *"Carnatify records a short clip
  of the music around you and sends it to our server to identify the raga and composition. Clips are
  not shared and are deleted after analysis."* (Only claim deletion if the backend actually deletes them; check
  `/predict-audio` and `/feedback` storage before writing this.)
- Ask for mic permission when the user first taps Record, not at launch. If they deny, show a
  path to Settings and a non-mic feature (browse ragas/lyrics) so the app still works.
- (i) Privacy policy URL is required **both** in App Store Connect and inside the app. It must
  say what is collected, how it is used, how long it is kept, and how to request deletion.
- (iii) Data minimization: record only the clip length the model needs.
- (v) Accounts: "If your app doesn't include significant account-based features, let people use it
  without a login." **Ship v1 with no accounts.** Then the
  [account-deletion rule](https://developer.apple.com/support/offering-account-deletion-in-your-app/) does not apply.

**[5.1.2 Data Use and Sharing](https://developer.apple.com/app-store/review/guidelines/#5.1.2)**
- (i) "You must clearly disclose where personal data will be shared with third parties, **including
  with third-party AI**, and obtain explicit permission before doing so." The backend calls **Gemini**
  (`GEMINI_API_KEY` in backend/main.py) to generate meanings. If any user audio or user-linked data reaches
  Gemini, you need an explicit consent screen. If Gemini only sees lyric text from the catalog, say so in
  the privacy policy anyway. The HF Spaces host acts as a data processor; name it in the policy.

**[2.5.14](https://developer.apple.com/app-store/review/guidelines/#2.5.14)**: recording requires explicit consent and
"a clear visual and/or audible indication when recording." Use an obvious in-app recording state, in addition to
the system's orange dot.

**[2.5.4 Background services](https://developer.apple.com/app-store/review/guidelines/#2.5.4)**: only for their intended purposes.
Do **not** add `UIBackgroundModes: audio` in v1. Recording whole concerts in the background is a
legitimate use, but it draws review questions and reviewers will test it. Foreground-only clip capture is the low-risk choice.

**[4.2 Minimum Functionality](https://developer.apple.com/app-store/review/guidelines/#4.2)**: "elevate it beyond a repackaged
website." A WKWebView around the Streamlit/web UI is the classic way to get rejected here. A native recorder, a results card,
local history, and a browsable raga/composition/lyrics library make the app clearly more than a wrapper.

**[2.1 App Completeness](https://developer.apple.com/app-store/review/guidelines/#2.1)**: "turn on your back-end service!"
- Backend is a **HF Space on CPU Basic**. Per [HF docs](https://huggingface.co/docs/hub/spaces-gpus#sleep-time), it
  **sleeps after 48h idle**, and a cold start during review means timeouts, which reviewers treat as a broken app. Keep it warm
  (scheduled `/health` ping) or move to a host that never sleeps for the review window. Handle timeouts in the UI ("Waking up the server...").
- The reviewer will not be at a Carnatic concert. Add a **"Try a sample" button with a bundled clip**
  and explain in App Review Notes how to test (play any Carnatic recording near the phone).
- Low-confidence or wrong results are fine. Error screens and spinners that never finish are not. Show "not sure" states.

**[2.3 Accurate Metadata](https://developer.apple.com/app-store/review/guidelines/#2.3)**: don't advertise accuracy you
don't have (measured composition top-1 on the wild set is low). Don't use other brands in the name or keywords
(e.g. "Shazam for Carnatic"), per 2.3.7 and [5.2.1](https://developer.apple.com/app-store/review/guidelines/#5.2.1).

**Copyright ([5.2.1](https://developer.apple.com/app-store/review/guidelines/#5.2.1), [5.2.3](https://developer.apple.com/app-store/review/guidelines/#5.2.3))**:
identifying ambient audio, the way Shazam does, is accepted. Risk goes up if the app **stores, plays back, exports or shares** recordings.
Don't do that in v1. Also check that `lyrics.db` content is cleared: old kritis are generally public domain, but
modern compositions and *translations* can be under copyright (UNVERIFIED per-item; this is a legal judgment). Venue
recording bans are the user's responsibility. Mention them in the ToS.

**AI disclosure**: no guideline requires labeling generated text, but mark the Gemini meanings as "AI-generated
translation" (it builds trust and helps with 5.1.2 and 2.3). The ML identification itself is not generative AI.
The preflight skill's `ai_apps.md` checklist applies.

**Privacy nutrition labels** ([App Privacy Details](https://developer.apple.com/app-store/app-privacy-details/)):
declare **User Content > Audio Data** (Apple's own example is voice recordings), "not linked to user" if
there are no accounts or device IDs, no tracking. Add Diagnostics if you ship crash reporting, and
"Other User Content" or Usage Data if `/feedback` sends free text.

**Privacy manifest** ([PrivacyInfo.xcprivacy](https://developer.apple.com/documentation/bundleresources/privacy-manifest-files)):
required if the app or any SDK uses [required-reason APIs](https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api).
UserDefaults alone triggers it (reason `CA92.1`). Uploads missing it are rejected at App Store Connect upload.

**Age rating ([2.3.6](https://developer.apple.com/app-store/review/guidelines/#2.3.6))**: answer the new questionnaire
(4+/9+/13+/16+/18+; [values](https://developer.apple.com/help/app-store-connect/reference/age-ratings-values-and-definitions/)).
With no UGC, no web browser and no chat, expect 4+. If feedback text is ever shown to other users, it becomes
[1.2 UGC](https://developer.apple.com/app-store/review/guidelines/#1.2) and needs filtering, reporting and blocking. Avoid that in v1.

**Small items that save a round-trip**: set `ITSAppUsesNonExemptEncryption = NO` (HTTPS only), so export compliance
doesn't block TestFlight. Use ATS-compliant HTTPS (hf.space is HTTPS). Provide a support URL.

## 3. Ranked top 5 to install (Claude Code side)

1. **asc CLI + asc skills.** Unlocks the preflight skill you already have, and lets either agent drive TestFlight and submission.
   `brew install asc`
   `claude plugin marketplace add rorkai/app-store-connect-cli-skills && claude plugin install asc@rorkai`
   (Codex: `npx skills add rorkai/app-store-connect-cli-skills --agent codex`.) Auth needs an ASC API key, which Deepti creates.
2. **Xcode agent bridge (Apple, nothing to install).** Lets Claude Code build, run tests, render previews and search Apple docs
   in the same Xcode project Codex uses: `claude mcp add --transport stdio xcode -- xcrun mcpbridge`
   (Xcode must be running with the project open. Exact flags UNVERIFIED against Apple's page, which renders client-side.)
3. **swiftui-pro (Paul Hudson).** Same SwiftUI rules Codex already follows, so both agents write the same style.
   `/plugin marketplace add twostraws/SwiftUI-Agent-Skill` then `/plugin install swiftui-pro@swiftui-agent-skill`
4. **Swift Concurrency skill (AvdLee).** Xcode 27 / Swift 6 strict-concurrency errors are the most common build blocker
   in audio code (AVAudioRecorder delegates, @MainActor UI updates).
   `/plugin marketplace add AvdLee/Swift-Concurrency-Agent-Skill` then `/plugin install swift-concurrency@swift-concurrency-agent-skill`
5. **swift-lsp (Anthropic official).** Real compiler diagnostics while Claude edits Swift.
   `claude plugin install swift-lsp@claude-plugins-official`
   *If Expo is chosen instead:* replace 3-5 with `claude plugin install expo@claude-plugins-official` (plus
   `codex plugin add expo@openai-curated`).

Optional: MobileBuildMCP for Claude only if Claude also needs simulator UI automation
(`claude mcp add MobileBuildMCP -- npx -y mobilebuildmcp@2.7.1 mcp`; consider bumping Codex's pinned
`xcodebuildmcp@2.7.0` to `mobilebuildmcp@2.7.1`). Skip fastlane, a second SwiftUI skill, and the simulator skills.

## 4. SwiftUI-native vs Expo: what the tooling favors

**The tooling clearly favors SwiftUI-native** for this setup:
- Codex is already configured for native: XcodeBuildMCP, Apple's Xcode bridge, the OpenAI build-ios-apps plugin, and 7 SwiftUI/concurrency skills.
  Apple's own agent tooling (Xcode 26.3/27) is built around Xcode projects and SwiftUI previews.
- gstack ios-qa/ios-fix/ios-design-review only work with SwiftUI. app-store-preflight scans Xcode projects.
- The app is small: AVAudioRecorder, multipart upload, a results view, and a local library. That's a few
  SwiftUI screens, with no cross-platform payoff for v1. Native also makes the mic permission, privacy
  manifest and entitlements simple, because there are no third-party RN SDKs that each need their own manifest.
- Expo's real advantage is EAS cloud build/submit without Xcode, and Android later. Here Xcode 27 is
  already installed and Codex owns Xcode, so that advantage mostly disappears. Pick Expo only if Android at launch is a hard requirement.

Sources: GitHub API (repo stats, READMEs); Apple Review Guidelines (fetched 2026-10-11);
[WWDC26 session 259](https://developer.apple.com/videos/play/wwdc2026/259/);
[InfoQ on Xcode 26.3](https://infoq.com/news/2026/02/xcode-26-3-agentic-coding);
[Expo agents docs](https://docs.expo.dev/agents/claude); [HF Spaces sleep](https://huggingface.co/docs/hub/spaces-gpus);
age-rating deadline coverage ([9to5mac](https://9to5mac.com/?p=1011484), secondary source).
