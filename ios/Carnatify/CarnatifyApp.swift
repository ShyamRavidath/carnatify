import SwiftUI

@main
struct CarnatifyApp: App {
    var body: some Scene {
        WindowGroup {
            ListenView(model: ListenModel(service: AppConfig.makeService(),
                                          recorder: AppConfig.makeRecorder()))
        }
    }
}
