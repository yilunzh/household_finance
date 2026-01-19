import SwiftUI

struct ContentView: View {
    @Environment(AuthManager.self) private var authManager

    var body: some View {
        Group {
            if authManager.isAuthenticated {
                if authManager.currentHouseholdId != nil {
                    MainTabView()
                } else {
                    HouseholdSelectionView()
                }
            } else {
                LoginView()
            }
        }
        .task {
            await authManager.checkAuthStatus()
        }
    }
}

#Preview {
    ContentView()
        .environment(AuthManager())
}
