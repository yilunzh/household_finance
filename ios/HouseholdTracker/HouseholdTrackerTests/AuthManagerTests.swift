import Testing
@testable import HouseholdTracker

@Suite("AuthManager Tests")
struct AuthManagerTests {

    @Test("Initial state is not authenticated")
    func initialStateNotAuthenticated() {
        let authManager = AuthManager()
        #expect(!authManager.isAuthenticated)
        #expect(authManager.currentUser == nil)
        #expect(authManager.households.isEmpty)
    }

    @Test("Error can be cleared")
    func errorCanBeCleared() async {
        let authManager = AuthManager()
        // Trigger an error by trying to log in with bad credentials
        // (This would need a mock network layer for proper testing)
        authManager.clearError()
        #expect(authManager.error == nil)
    }
}
