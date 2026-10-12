import AVFoundation

/// Microphone capture abstraction so UI and tests can use a fake.
@MainActor
protocol ClipRecording: AnyObject {
    var isRecording: Bool { get }
    var currentTime: TimeInterval { get }
    func requestPermission() async -> Bool
    func start() throws
    /// 0...1 for the level meter.
    func normalizedLevel() -> Float
    /// Stops and returns the finished file, or nil if nothing was recorded.
    func stop() -> URL?
    /// Stops if needed and deletes the file.
    func discard()
}

/// Records AAC-LC `.m4a`, 44.1 kHz mono, 64 kbps: about 1.5 MB for 180 s, well under the
/// server's 30 MB limit, and the format the backend was verified against (2026-10-11).
@MainActor
final class AudioRecorder: ClipRecording {
    private var recorder: AVAudioRecorder?
    private var fileURL: URL?

    var isRecording: Bool { recorder?.isRecording ?? false }
    var currentTime: TimeInterval { recorder?.currentTime ?? 0 }

    func requestPermission() async -> Bool {
        switch AVAudioApplication.shared.recordPermission {
        case .granted: return true
        case .denied: return false
        default: return await AVAudioApplication.requestRecordPermission()
        }
    }

    func start() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .default)
        try session.setActive(true)
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("clip-\(UUID().uuidString).m4a")
        let settings: [String: Any] = [
            AVFormatIDKey: kAudioFormatMPEG4AAC,
            AVSampleRateKey: 44_100,
            AVNumberOfChannelsKey: 1,
            AVEncoderBitRateKey: 64_000,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
        ]
        let recorder = try AVAudioRecorder(url: url, settings: settings)
        recorder.isMeteringEnabled = true
        guard recorder.record(forDuration: AppConfig.maximumClipSeconds) else {
            throw RecorderError.couldNotStart
        }
        self.recorder = recorder
        self.fileURL = url
    }

    func normalizedLevel() -> Float {
        guard let recorder, recorder.isRecording else { return 0 }
        recorder.updateMeters()
        let db = recorder.averagePower(forChannel: 0)  // -160...0
        return max(0, min(1, (db + 50) / 50))
    }

    func stop() -> URL? {
        recorder?.stop()
        recorder = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        return fileURL
    }

    func discard() {
        _ = stop()
        if let fileURL { try? FileManager.default.removeItem(at: fileURL) }
        fileURL = nil
    }

    enum RecorderError: Error { case couldNotStart }
}
