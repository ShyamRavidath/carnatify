import Foundation

/// User-facing failure. The backend has three error body shapes:
/// `{detail: "text"}`, pydantic `{detail: [{msg: ...}]}`, and slowapi `{error: "..."}`.
enum APIError: Error, Equatable, Sendable {
    case tooShort
    case rateLimited
    case serverAsleep
    case unsupportedAudio(String)
    case server(status: Int, message: String)
    case network(String)
    case decoding

    static func from(status: Int, body: Data) -> APIError {
        let message = Self.message(in: body) ?? HTTPURLResponse.localizedString(forStatusCode: status)
        switch status {
        case 429: return .rateLimited
        case 415: return .unsupportedAudio(message)
        case 422 where message.contains("seconds"): return .tooShort
        case 502, 503, 504: return .serverAsleep
        default: return .server(status: status, message: message)
        }
    }

    static func message(in body: Data) -> String? {
        guard let obj = try? JSONSerialization.jsonObject(with: body) as? [String: Any] else { return nil }
        if let text = obj["detail"] as? String { return text }
        if let list = obj["detail"] as? [[String: Any]], let first = list.first?["msg"] as? String { return first }
        return obj["error"] as? String
    }

    var userMessage: String {
        switch self {
        case .tooShort:
            return "That clip was too short. Listen for at least 15 seconds, ideally a few minutes."
        case .rateLimited:
            return "Too many tries in a row. Wait a minute and try again."
        case .serverAsleep:
            return "The Carnatify server is waking up. Try again in about a minute."
        case .unsupportedAudio:
            return "The recording could not be read. Please try recording again."
        case .server(_, let message):
            return "Something went wrong on the server (\(message))."
        case .network:
            return "Could not reach Carnatify. Check your connection and try again."
        case .decoding:
            return "The server sent a reply this version of the app does not understand. Please update the app."
        }
    }
}

extension JSONDecoder {
    static var carnatify: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }
}
