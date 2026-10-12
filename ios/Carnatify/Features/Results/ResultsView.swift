import SwiftUI

/// Ranked suggestions. Copy never asserts: the backend's `asserted` is always false
/// and its confidence gate is off in the product (see docs/ios/DECISIONS.md).
struct ResultsView: View {
    let result: RagaIdentification
    let composition: ListenModel.CompositionPhase
    let findComposition: () -> Void
    let done: () -> Void

    var body: some View {
        List {
            Section {
                if result.candidates.isEmpty {
                    Text(result.reason ?? "Not enough clear melody to suggest a raga. Try a longer clip.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(Array(result.candidates.prefix(3).enumerated()), id: \.element.id) { rank, candidate in
                        CandidateRow(rank: rank + 1, name: candidate.raga,
                                     isLead: rank == 0 && result.strength == .stronger)
                    }
                }
            } header: {
                Text("Possible ragas")
            } footer: {
                Text(footer)
            }
            .accessibilityIdentifier("ragaSection")

            Section("Composition") {
                CompositionSection(phase: composition, find: findComposition)
            }

            Section {
                Button("Listen again", action: done)
                    .accessibilityIdentifier("listenAgainButton")
            }
        }
        .listStyle(.insetGrouped)
    }

    private var footer: String {
        switch result.strength {
        case .stronger: return "The first suggestion stands out clearly from the rest. It is still a suggestion, not a certainty."
        case .tentative: return "These are close calls. Listening longer usually helps."
        case .none: return ""
        }
    }
}

private struct CandidateRow: View {
    let rank: Int
    let name: String
    let isLead: Bool

    var body: some View {
        HStack(spacing: 12) {
            Text("\(rank)")
                .font(.headline.monospacedDigit())
                .foregroundStyle(.secondary)
                .frame(width: 24)
            Text(name)
                .font(isLead ? .title3.weight(.semibold) : .body)
            Spacer()
            if isLead {
                Image(systemName: "star.fill")
                    .foregroundStyle(.tint)
                    .accessibilityLabel("Strongest suggestion")
            }
        }
        .accessibilityElement(children: .combine)
    }
}

private struct CompositionSection: View {
    let phase: ListenModel.CompositionPhase
    let find: () -> Void

    var body: some View {
        switch phase {
        case .notRequested:
            VStack(alignment: .leading, spacing: 8) {
                Text("Matching the lyrics to a known composition takes longer, sometimes a few minutes.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                Button("Find the composition", action: find)
                    .accessibilityIdentifier("findCompositionButton")
            }
        case .loading:
            HStack {
                ProgressView()
                Text("Listening for lyrics…").foregroundStyle(.secondary)
            }
        case .loaded(let found):
            if found.compositions.isEmpty {
                Text(found.message ?? "No composition matched. Try a clip with clear singing, ideally the opening line.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(found.compositions.prefix(5)) { match in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(match.title)
                        if let ragas = match.ragas, !ragas.isEmpty {
                            Text(ragas.joined(separator: ", "))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .accessibilityElement(children: .combine)
                }
                if let message = found.message {
                    Text(message).font(.caption).foregroundStyle(.secondary)
                }
            }
        case .failed(let error):
            VStack(alignment: .leading, spacing: 8) {
                Text(error.userMessage).foregroundStyle(.secondary)
                Button("Try again", action: find)
            }
        }
    }
}
