import SwiftUI

struct AboutView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("How it works") {
                    Text("Carnatify listens to a recording of Carnatic music and suggests which raga it might be, ranked from most to least likely.")
                    if AppConfig.compositionEnabled {
                        Text("It can also try to match the lyrics to a known composition.")
                    }
                    Text("Suggestions can be wrong, especially for short or noisy clips and for ragas that share the same notes.")
                }
                Section("Your privacy") {
                    Text("Audio is recorded only while you are listening. The clip is sent to the Carnatify server, analysed, and deleted. Carnatify has no accounts and does not track you.")
                    Link("Privacy policy", destination: AppConfig.privacyPolicyURL)
                    Link("Support", destination: AppConfig.supportURL)
                }
                Section {
                    LabeledContent("Version", value: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "–")
                }
            }
            .navigationTitle("About")
            .toolbar {
                Button("Done") { dismiss() }
            }
        }
    }
}
