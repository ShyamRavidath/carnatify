import SwiftUI

struct ListenView: View {
    @State private var model: ListenModel
    @State private var showingAbout = false

    init(model: ListenModel) {
        _model = State(initialValue: model)
    }

    var body: some View {
        NavigationStack {
            content
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .navigationTitle("Carnatify")
                .toolbar {
                    Button("About", systemImage: "info.circle") { showingAbout = true }
                        .accessibilityIdentifier("aboutButton")
                }
                .sheet(isPresented: $showingAbout) { AboutView() }
        }
    }

    private var trySample: (() -> Void)? {
        guard model.hasSample else { return nil }
        return { model.analyzeSample() }
    }

    private var findComposition: (() -> Void)? {
        guard model.compositionEnabled else { return nil }
        return { model.findComposition() }
    }

    @ViewBuilder
    private var content: some View {
        switch model.phase {
        case .idle:
            IdlePrompt(start: model.startListening, trySample: trySample)
        case .permissionDenied:
            PermissionDeniedView(retry: model.reset)
        case .recording:
            RecordingView(elapsed: model.elapsed, level: model.level, canFinish: model.canFinish,
                          finish: model.finishListening, cancel: model.cancelListening)
        case .analyzing:
            ProgressView("Listening closely…")
                .accessibilityIdentifier("analyzing")
        case .result(let result):
            ResultsView(result: result, composition: model.composition,
                        findComposition: findComposition,
                        done: model.reset)
        case .failed(let error):
            FailureView(message: error.userMessage, retry: model.reset)
        }
    }
}

private struct IdlePrompt: View {
    let start: () -> Void
    let trySample: (() -> Void)?

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Image(systemName: "music.note")
                .font(.system(size: 64))
                .foregroundStyle(.tint)
                .accessibilityHidden(true)
            Text("Hear a Carnatic piece and wonder what raga it is?")
                .font(.title2.weight(.semibold))
                .multilineTextAlignment(.center)
            Text("Hold your phone toward the music. A few minutes of listening gives the best suggestions.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
            Spacer()
            Button(action: start) {
                Label("Listen", systemImage: "mic.fill")
                    .font(.title3.weight(.semibold))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .accessibilityIdentifier("listenButton")
            if let trySample {
                Button("No music nearby? Try a sample", action: trySample)
                    .accessibilityIdentifier("trySampleButton")
            }
        }
    }
}

private struct RecordingView: View {
    let elapsed: TimeInterval
    let level: Float
    let canFinish: Bool
    let finish: () -> Void
    let cancel: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Label("Recording", systemImage: "record.circle")
                .font(.headline)
                .foregroundStyle(.red)
                .symbolEffect(.pulse)
                .accessibilityIdentifier("recordingIndicator")
            Text(Duration.seconds(elapsed), format: .time(pattern: .minuteSecond))
                .font(.system(size: 56, weight: .light, design: .rounded).monospacedDigit())
                .accessibilityLabel("Recorded \(Int(elapsed)) seconds")
            ProgressView(value: min(elapsed, AppConfig.recommendedClipSeconds),
                         total: AppConfig.recommendedClipSeconds)
                .accessibilityLabel("Progress toward a full three-minute clip")
            LevelMeter(level: level)
            Text(hint)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Spacer()
            Button(action: finish) {
                Text("Done listening").frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(!canFinish)
            .accessibilityIdentifier("finishButton")
            Button("Cancel", role: .cancel, action: cancel)
                .accessibilityIdentifier("cancelButton")
        }
    }

    private var hint: String {
        if elapsed < AppConfig.minimumClipSeconds { return "Keep listening…" }
        if elapsed < 60 { return "You can stop now, but suggestions get much better with more music." }
        return "Great. Three minutes gives the best results; stop whenever you like."
    }
}

private struct LevelMeter: View {
    let level: Float

    var body: some View {
        GeometryReader { proxy in
            Capsule().fill(.quaternary)
                .overlay(alignment: .leading) {
                    Capsule().fill(.tint)
                        .frame(width: proxy.size.width * CGFloat(level))
                }
        }
        .frame(height: 8)
        .animation(.linear(duration: 0.1), value: level)
        .accessibilityHidden(true)
    }
}

private struct PermissionDeniedView: View {
    let retry: () -> Void
    @Environment(\.openURL) private var openURL

    var body: some View {
        ContentUnavailableView {
            Label("Microphone is off", systemImage: "mic.slash")
        } description: {
            Text("Carnatify needs the microphone to hear the music. You can turn it on in Settings.")
        } actions: {
            Button("Open Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) { openURL(url) }
            }
            .buttonStyle(.borderedProminent)
            Button("Back", action: retry)
        }
    }
}

private struct FailureView: View {
    let message: String
    let retry: () -> Void

    var body: some View {
        ContentUnavailableView {
            Label("Couldn't get suggestions", systemImage: "exclamationmark.triangle")
        } description: {
            Text(message)
        } actions: {
            Button("Try again", action: retry)
                .buttonStyle(.borderedProminent)
                .accessibilityIdentifier("retryButton")
        }
    }
}

#if DEBUG
#Preview("Idle") {
    ListenView(model: ListenModel(service: APIStub(mode: .confident), recorder: StubRecorder()))
}
#endif
