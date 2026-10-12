import Foundation

/// Response of `POST /identify-raga`. Field names are the server's JSON keys
/// (snake_case mapped by `JSONDecoder.carnatify`). The server never asserts an answer:
/// `asserted` is always false and the UI must present candidates as candidates.
struct RagaIdentification: Decodable, Equatable, Sendable {
    struct Candidate: Decodable, Equatable, Sendable, Identifiable {
        let raga: String
        let probability: Double
        let score: Double
        var id: String { raga }
    }

    struct Signals: Decodable, Equatable, Sendable {
        let maxScore: Double
        let margin: Double
        let softmaxMax: Double
    }

    struct Gate: Decodable, Equatable, Sendable {
        let name: String
        let wouldAccept: Bool
    }

    let asserted: Bool
    let answered: Bool
    let reason: String?
    let candidates: [Candidate]
    let signals: Signals?
    let gate: Gate?
    let tonic: Double?
    let voicedS: Double?
    let duration: Double?
}

extension RagaIdentification {
    /// How strongly the UI may word the top candidate. The registered gate is off in
    /// the product, so even `.stronger` is still phrased as a suggestion.
    enum Strength: Equatable { case none, tentative, stronger }

    var strength: Strength {
        guard answered, !candidates.isEmpty else { return .none }
        return gate?.wouldAccept == true ? .stronger : .tentative
    }
}
