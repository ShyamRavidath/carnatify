import Foundation

/// Single place for environment configuration.
///
/// DEBUG launch arguments (QA only, never in Release):
///   -apiBaseURL <url>                      point at a local/staging backend
///   -stubResult confident|uncertain|error|slow   use `APIStub` instead of the network
///   -stubRecorder                          fake microphone (Simulator / UI tests)
enum AppConfig {
    /// Production backend: HF Space `shyamravidath/carnatify` (deploy: backend/deploy_space.sh).
    static let productionBaseURL = URL(string: "https://shyamravidath-carnatify.hf.space")!

    static let privacyPolicyURL = URL(string: "https://carnatify.vercel.app/privacy")!
    static let supportURL = URL(string: "https://carnatify.vercel.app/support")!

    /// Shortest clip the raga route accepts (server rejects < 10 s).
    static let minimumClipSeconds: TimeInterval = 15
    /// The model is trained on 180 s windows; shorter clips are much less reliable.
    static let recommendedClipSeconds: TimeInterval = 180
    static let maximumClipSeconds: TimeInterval = 180

    /// Composition ID (`/identify`) takes minutes per clip on the free Space, so v1 ships
    /// raga-only (docs/ios/DECISIONS.md D8). Flip to true for v1.1 once it is fast enough.
    static let compositionEnabled = false

    /// Bundled demo recording for App Review and first-run users. Drop a rights-cleared
    /// ~3 min clip at `Carnatify/Resources/sample-clip.m4a` and the "Try a sample" button
    /// appears; without the file the button stays hidden.
    static var sampleClipURL: URL? {
        Bundle.main.url(forResource: "sample-clip", withExtension: "m4a")
    }

    static var baseURL: URL {
        #if DEBUG
        if let raw = UserDefaults.standard.string(forKey: "apiBaseURL"), let url = URL(string: raw) {
            return url
        }
        #endif
        return productionBaseURL
    }

    static func makeService() -> IdentificationService {
        #if DEBUG
        if let mode = UserDefaults.standard.string(forKey: "stubResult") {
            return APIStub(mode: APIStub.Mode(rawValue: mode) ?? .confident)
        }
        #endif
        return APIClient(baseURL: baseURL)
    }

    static func makeRecorder() -> ClipRecording {
        #if DEBUG
        if UserDefaults.standard.bool(forKey: "stubRecorder") {
            return StubRecorder()
        }
        #endif
        return AudioRecorder()
    }
}
