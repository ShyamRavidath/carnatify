import XCTest

/// Drives the real UI with the DEBUG stub service and fake microphone.
@MainActor
final class SmokeTests: XCTestCase {
    override func setUp() async throws { continueAfterFailure = false }

    private func launch(_ stub: String) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-stubResult", stub, "-stubRecorder", "YES"]
        app.launch()
        return app
    }

    func testListenToResults() {
        let app = launch("confident")
        app.buttons["listenButton"].tap()
        XCTAssertTrue(app.descendants(matching: .any)["recordingIndicator"].waitForExistence(timeout: 5))
        let finish = app.buttons["finishButton"]
        XCTAssertTrue(finish.waitForExistence(timeout: 5))
        let enabled = NSPredicate(format: "isEnabled == true")
        expectation(for: enabled, evaluatedWith: finish)
        waitForExpectations(timeout: 5)
        finish.tap()
        XCTAssertTrue(app.staticTexts["Hindōḷaṁ"].waitForExistence(timeout: 10))
        // v1 is raga-only (AppConfig.compositionEnabled == false).
        XCTAssertFalse(app.buttons["findCompositionButton"].exists)
    }

    func testServerFailureOffersRetry() {
        let app = launch("error")
        app.buttons["listenButton"].tap()
        let finish = app.buttons["finishButton"]
        XCTAssertTrue(finish.waitForExistence(timeout: 5))
        expectation(for: NSPredicate(format: "isEnabled == true"), evaluatedWith: finish)
        waitForExpectations(timeout: 5)
        finish.tap()
        XCTAssertTrue(app.buttons["retryButton"].waitForExistence(timeout: 10))
    }
}
