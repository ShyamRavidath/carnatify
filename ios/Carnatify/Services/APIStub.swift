#if DEBUG
import Foundation

/// QA-only fixtures, selected with `-stubResult`. Never compiled into Release.
/// Payloads mirror real server responses captured 2026-10-11.
struct APIStub: IdentificationService {
    enum Mode: String { case confident, uncertain, error, slow }
    let mode: Mode

    func identifyRaga(clip: URL) async throws -> RagaIdentification {
        switch mode {
        case .error: throw APIError.serverAsleep
        case .slow: try await Task.sleep(for: .seconds(5))
        default: break
        }
        return try JSONDecoder.carnatify.decode(RagaIdentification.self, from: Data(json(confident: mode != .uncertain).utf8))
    }

    func identifyComposition(clip: URL) async throws -> CompositionIdentification {
        try await Task.sleep(for: .seconds(1))
        let body = mode == .uncertain
            ? #"{"query_id":"stub","compositions":[],"composition_confidence":"none","clip_type":"no_lyrics","message":"Couldn't hear clear lyrics."}"#
            : #"{"query_id":"stub","compositions":[{"title":"Sāmagāna lōlanē","score":0.81,"ragas":["Hindōḷaṁ"]},{"title":"Māmava mīnākṣi","score":0.42,"ragas":["Varāḷi"]}],"composition_confidence":"medium","clip_type":"sung","message":null}"#
        return try JSONDecoder.carnatify.decode(CompositionIdentification.self, from: Data(body.utf8))
    }

    private func json(confident: Bool) -> String {
        let top = confident ? ("Hindōḷaṁ", 0.995, true) : ("Latāngi", 0.22, false)
        return """
        {"asserted":false,"answered":true,"reason":null,
         "candidates":[{"raga":"\(top.0)","probability":\(top.1),"score":0.64},
                       {"raga":"Mōhanaṁ","probability":0.06,"score":0.15},
                       {"raga":"Rītigauḷa","probability":0.04,"score":0.13}],
         "signals":{"max_score":0.64,"margin":\(confident ? 0.51 : 0.08),"softmax_max":\(top.1)},
         "gate":{"name":"margin_v1_context180","would_accept":\(top.2)},
         "tonic":138.8,"voiced_s":150.0,"duration":180.0}
        """
    }
}

/// Fake microphone for Simulator and UI tests (`-stubRecorder`).
@MainActor
final class StubRecorder: ClipRecording {
    private(set) var isRecording = false
    private var started: Date?
    var currentTime: TimeInterval { started.map { Date().timeIntervalSince($0) * 20 } ?? 0 }

    func requestPermission() async -> Bool { true }
    func start() throws { isRecording = true; started = Date() }
    func normalizedLevel() -> Float { isRecording ? Float.random(in: 0.2...0.8) : 0 }
    func stop() -> URL? {
        isRecording = false
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("stub.m4a")
        try? Data(count: 1024).write(to: url)
        return url
    }
    func discard() { isRecording = false; started = nil }
}
#endif
