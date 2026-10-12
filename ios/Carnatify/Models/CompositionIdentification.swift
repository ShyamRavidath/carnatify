import Foundation

/// Response of `POST /identify` (lyrics-first composition match).
struct CompositionIdentification: Decodable, Equatable, Sendable {
    struct Match: Decodable, Equatable, Sendable, Identifiable {
        let title: String
        let score: Double
        let ragas: [String]?
        var id: String { title }
    }

    let queryId: String?
    let compositions: [Match]
    /// "high" | "medium" | "low" | "none"
    let compositionConfidence: String
    /// "sung" | "no_lyrics"
    let clipType: String
    let message: String?
}
