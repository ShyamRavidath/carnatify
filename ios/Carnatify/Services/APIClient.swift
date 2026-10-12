import Foundation

/// The two backend calls the app makes. Implementations must not retain audio.
protocol IdentificationService: Sendable {
    func identifyRaga(clip: URL) async throws -> RagaIdentification
    func identifyComposition(clip: URL) async throws -> CompositionIdentification
}

struct APIClient: IdentificationService {
    let baseURL: URL
    var session: URLSession = .shared

    func identifyRaga(clip: URL) async throws -> RagaIdentification {
        try await upload(clip, path: "identify-raga", timeout: 180)
    }

    /// Lyrics-first matching runs speech recognition and vocal separation on the server
    /// and can take minutes on the free CPU host.
    func identifyComposition(clip: URL) async throws -> CompositionIdentification {
        try await upload(clip, path: "identify", query: [URLQueryItem(name: "fast", value: "true")], timeout: 900)
    }

    private func upload<T: Decodable>(_ clip: URL, path: String, query: [URLQueryItem] = [],
                                      timeout: TimeInterval) async throws -> T {
        var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        if !query.isEmpty { components.queryItems = query }
        var request = URLRequest(url: components.url!, timeoutInterval: timeout)
        request.httpMethod = "POST"
        let form = try MultipartForm(fileURL: clip, fieldName: "file", mimeType: "audio/m4a")
        request.setValue(form.contentType, forHTTPHeaderField: "Content-Type")

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.upload(for: request, from: form.body)
        } catch let error as URLError where error.code == .timedOut {
            throw APIError.serverAsleep
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw APIError.network(error.localizedDescription)
        }
        guard let http = response as? HTTPURLResponse else { throw APIError.network("No HTTP response") }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.from(status: http.statusCode, body: data)
        }
        do {
            return try JSONDecoder.carnatify.decode(T.self, from: data)
        } catch {
            throw APIError.decoding
        }
    }
}

/// Minimal multipart/form-data body with one file part.
struct MultipartForm {
    let boundary = "carnatify-\(UUID().uuidString)"
    let body: Data

    var contentType: String { "multipart/form-data; boundary=\(boundary)" }

    init(fileURL: URL, fieldName: String, mimeType: String) throws {
        let fileData = try Data(contentsOf: fileURL)
        var body = Data()
        body.append(Data("--\(boundary)\r\n".utf8))
        body.append(Data("Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(fileURL.lastPathComponent)\"\r\n".utf8))
        body.append(Data("Content-Type: \(mimeType)\r\n\r\n".utf8))
        body.append(fileData)
        body.append(Data("\r\n--\(boundary)--\r\n".utf8))
        self.body = body
    }
}
