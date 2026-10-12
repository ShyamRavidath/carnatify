import XCTest
@testable import Carnatify

@MainActor
final class ListenModelTests: XCTestCase {
    func testFinishingTooEarlyIsTooShortAndDiscards() async throws {
        let model = ListenModel(service: APIStub(mode: .confident), recorder: StubRecorder())
        model.startListening()
        try await waitUntil { model.phase == .recording }
        model.finishListening()  // elapsed is still under the minimum
        XCTAssertEqual(model.phase, .failed(.tooShort))
    }

    func testFullFlowReachesResultAndComposition() async throws {
        let model = ListenModel(service: APIStub(mode: .confident), recorder: StubRecorder())
        model.startListening()
        try await waitUntil { model.canFinish }   // stub clock runs 20x
        model.finishListening()
        try await waitUntil { if case .result = model.phase { return true } else { return false } }
        model.findComposition()
        try await waitUntil { if case .loaded = model.composition { return true } else { return false } }
        model.reset()
        XCTAssertEqual(model.phase, .idle)
        XCTAssertEqual(model.composition, .notRequested)
    }

    func testServerErrorShowsFailure() async throws {
        let model = ListenModel(service: APIStub(mode: .error), recorder: StubRecorder())
        model.startListening()
        try await waitUntil { model.canFinish }
        model.finishListening()
        try await waitUntil { model.phase == .failed(.serverAsleep) }
    }

    private func waitUntil(timeout: TimeInterval = 5, _ condition: @MainActor () -> Bool) async throws {
        let deadline = Date().addingTimeInterval(timeout)
        while !condition() {
            if Date() > deadline { XCTFail("timed out"); return }
            try await Task.sleep(for: .milliseconds(20))
        }
    }
}
