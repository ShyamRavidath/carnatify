import Foundation
import Observation

@MainActor
@Observable
final class ListenModel {
    enum Phase: Equatable {
        case idle
        case permissionDenied
        case recording
        case analyzing
        case result(RagaIdentification)
        case failed(APIError)
    }

    enum CompositionPhase: Equatable {
        case notRequested
        case loading
        case loaded(CompositionIdentification)
        case failed(APIError)
    }

    private(set) var phase: Phase = .idle
    private(set) var composition: CompositionPhase = .notRequested
    private(set) var elapsed: TimeInterval = 0
    private(set) var level: Float = 0

    private let service: IdentificationService
    private let recorder: ClipRecording
    private let sampleClip: URL?
    let compositionEnabled: Bool
    private var meterTask: Task<Void, Never>?
    private var workTask: Task<Void, Never>?
    /// Kept only until the result arrives (or, with composition on, until the user leaves
    /// the result so the composition step can reuse it).
    private var clipURL: URL?

    init(service: IdentificationService, recorder: ClipRecording,
         sampleClip: URL? = AppConfig.sampleClipURL,
         compositionEnabled: Bool = AppConfig.compositionEnabled) {
        self.service = service
        self.recorder = recorder
        self.sampleClip = sampleClip
        self.compositionEnabled = compositionEnabled
    }

    var canFinish: Bool { phase == .recording && elapsed >= AppConfig.minimumClipSeconds }
    var hasSample: Bool { sampleClip != nil }

    /// Sends the bundled sample instead of a recording. A copy is analyzed so the
    /// usual clip cleanup never touches the bundle.
    func analyzeSample() {
        guard let sampleClip, phase == .idle else { return }
        clearState()
        let copy = FileManager.default.temporaryDirectory
            .appendingPathComponent("sample-\(UUID().uuidString).m4a")
        do {
            try FileManager.default.copyItem(at: sampleClip, to: copy)
        } catch {
            phase = .failed(.network("Could not open the sample recording."))
            return
        }
        clipURL = copy
        analyze(copy)
    }

    func startListening() {
        guard phase != .recording, phase != .analyzing else { return }
        workTask = Task {
            guard await recorder.requestPermission() else {
                phase = .permissionDenied
                return
            }
            do {
                clearState()
                try recorder.start()
                phase = .recording
                startMeter()
            } catch {
                phase = .failed(.network("Could not start the microphone."))
            }
        }
    }

    /// Stops recording and sends the clip for raga identification.
    func finishListening() {
        guard phase == .recording else { return }
        meterTask?.cancel()
        guard elapsed >= AppConfig.minimumClipSeconds, let url = recorder.stop() else {
            recorder.discard()
            phase = .failed(.tooShort)
            return
        }
        clipURL = url
        analyze(url)
    }

    func cancelListening() {
        meterTask?.cancel()
        workTask?.cancel()
        recorder.discard()
        reset()
    }

    func findComposition() {
        guard compositionEnabled, case .result = phase, let clipURL, composition != .loading else { return }
        composition = .loading
        workTask = Task {
            do {
                composition = .loaded(try await service.identifyComposition(clip: clipURL))
            } catch let error as APIError {
                composition = .failed(error)
            } catch {
                composition = .notRequested
            }
        }
    }

    /// Back to the start; deletes the local clip.
    func reset() {
        workTask?.cancel()
        clearState()
    }

    private func clearState() {
        deleteClip()
        phase = .idle
        composition = .notRequested
        elapsed = 0
        level = 0
    }

    // MARK: - Private

    private func analyze(_ url: URL) {
        phase = .analyzing
        workTask = Task {
            do {
                let result = try await service.identifyRaga(clip: url)
                phase = .result(result)
                if !compositionEnabled { deleteClip() }
            } catch let error as APIError {
                phase = .failed(error)
                deleteClip()
            } catch {
                deleteClip()
            }
        }
    }

    private func startMeter() {
        meterTask = Task {
            while !Task.isCancelled {
                elapsed = recorder.currentTime
                level = recorder.normalizedLevel()
                if !recorder.isRecording, phase == .recording {
                    // Hit the maximum length; the recorder stopped itself.
                    elapsed = max(elapsed, AppConfig.maximumClipSeconds)
                    finishListening()
                    return
                }
                try? await Task.sleep(for: .milliseconds(100))
            }
        }
    }

    private func deleteClip() {
        if let clipURL { try? FileManager.default.removeItem(at: clipURL) }
        clipURL = nil
    }
}
