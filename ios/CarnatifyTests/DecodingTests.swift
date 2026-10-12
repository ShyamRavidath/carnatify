import XCTest
@testable import Carnatify

/// Decodes real server responses captured 2026-10-11 (server paths scrubbed).
final class DecodingTests: XCTestCase {
    private func fixture(_ name: String) throws -> Data {
        let url = try XCTUnwrap(Bundle(for: Self.self).url(forResource: name, withExtension: "json"))
        return try Data(contentsOf: url)
    }

    func testConfidentRagaResponse() throws {
        let r = try JSONDecoder.carnatify.decode(RagaIdentification.self, from: fixture("identify_raga_confident"))
        XCTAssertFalse(r.asserted)
        XCTAssertTrue(r.answered)
        XCTAssertEqual(r.candidates.first?.raga, "Hindōḷaṁ")
        XCTAssertEqual(r.candidates.count, 5)
        XCTAssertEqual(r.gate?.wouldAccept, true)
        XCTAssertEqual(r.strength, .stronger)
        XCTAssertEqual(r.duration, 180)
        XCTAssertNotNil(r.signals?.margin)
    }

    func testUncertainRagaResponseIsTentative() throws {
        let r = try JSONDecoder.carnatify.decode(RagaIdentification.self, from: fixture("identify_raga_uncertain"))
        XCTAssertEqual(r.gate?.wouldAccept, false)
        XCTAssertEqual(r.strength, .tentative)
        XCTAssertFalse(r.candidates[0].raga.isEmpty)
    }

    func testMissingGateIsTentativeNotStronger() throws {
        let json = #"{"asserted":false,"answered":true,"reason":null,"candidates":[{"raga":"Tōḍi","probability":0.9,"score":0.5}],"signals":null,"gate":null,"tonic":null,"voiced_s":null,"duration":null}"#
        let r = try JSONDecoder.carnatify.decode(RagaIdentification.self, from: Data(json.utf8))
        XCTAssertEqual(r.strength, .tentative)
    }

    func testNoLyricsCompositionResponse() throws {
        let r = try JSONDecoder.carnatify.decode(CompositionIdentification.self, from: fixture("identify_no_lyrics"))
        XCTAssertEqual(r.clipType, "no_lyrics")
        XCTAssertEqual(r.compositionConfidence, "none")
        XCTAssertTrue(r.compositions.isEmpty)
        XCTAssertNotNil(r.message)
    }

    func testErrorShapes() throws {
        XCTAssertEqual(APIError.from(status: 415, body: try fixture("error_415")),
                       .unsupportedAudio("Unsupported audio content-type: audio/x-caf."))
        XCTAssertEqual(APIError.from(status: 422, body: Data(#"{"detail":"need at least 10 seconds of audio"}"#.utf8)), .tooShort)
        XCTAssertEqual(APIError.from(status: 429, body: Data(#"{"error":"Rate limit exceeded: 4 per 1 minute"}"#.utf8)), .rateLimited)
        XCTAssertEqual(APIError.message(in: Data(#"{"detail":[{"msg":"Field required"}]}"#.utf8)), "Field required")
        XCTAssertEqual(APIError.from(status: 503, body: Data("<html>".utf8)), .serverAsleep)
    }

    func testMultipartBodyCarriesFileFieldAndAudioType() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("t.m4a")
        try Data([1, 2, 3]).write(to: url)
        let form = try MultipartForm(fileURL: url, fieldName: "file", mimeType: "audio/m4a")
        let text = String(decoding: form.body, as: UTF8.self)
        XCTAssertTrue(text.contains(#"name="file"; filename="t.m4a""#))
        XCTAssertTrue(text.contains("Content-Type: audio/m4a"))
        XCTAssertTrue(form.contentType.hasPrefix("multipart/form-data; boundary="))
    }
}
