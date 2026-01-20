import SwiftUI

@main
struct HouseholdTrackerApp: App {
    @State private var authManager = AuthManager()
    @State private var pendingInviteToken: String?

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(authManager)
                .onOpenURL { url in
                    handleDeepLink(url)
                }
                .sheet(item: $pendingInviteToken) { token in
                    AcceptInvitationView(token: token)
                        .environment(authManager)
                }
        }
    }

    private func handleDeepLink(_ url: URL) {
        // Handle householdtracker://invite/<token>
        guard url.scheme == "householdtracker" else { return }

        let pathComponents = url.pathComponents
        if url.host == "invite" && pathComponents.count >= 2 {
            // Format: householdtracker://invite/<token>
            let token = pathComponents[1]
            pendingInviteToken = token
        } else if pathComponents.count >= 3 && pathComponents[1] == "invite" {
            // Format: householdtracker:///invite/<token>
            let token = pathComponents[2]
            pendingInviteToken = token
        }
    }
}

// Make String identifiable for sheet binding
extension String: @retroactive Identifiable {
    public var id: String { self }
}
