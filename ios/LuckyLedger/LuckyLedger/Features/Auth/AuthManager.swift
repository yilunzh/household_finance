import Foundation
import Observation

@Observable
final class AuthManager: Sendable {
    private(set) var isAuthenticated = false
    private(set) var currentUser: User?
    private(set) var households: [UserHousehold] = []
    private(set) var currentHouseholdId: Int?

    private(set) var isLoading = false
    private(set) var error: String?

    private let network = NetworkManager.shared

    // MARK: - Auth Status

    @MainActor
    func checkAuthStatus() async {
        isLoading = true
        defer { isLoading = false }

        let hasSession = await network.hasValidSession()
        if hasSession {
            do {
                // Fetch current user info
                let response: UserMeResponse = try await network.request(
                    endpoint: Endpoints.userMe,
                    requiresAuth: true
                )
                currentUser = response.user
                isAuthenticated = true

                // Fetch households
                await fetchHouseholds()

                // Restore household selection if available
                if let savedHouseholdId = UserDefaults.standard.object(forKey: "currentHouseholdId") as? Int,
                   households.contains(where: { $0.id == savedHouseholdId }) {
                    selectHousehold(savedHouseholdId)
                } else if let firstHousehold = households.first {
                    selectHousehold(firstHousehold.id)
                }
            } catch {
                // Session invalid, clear auth state
                isAuthenticated = false
                currentUser = nil
            }
        }
    }

    // MARK: - Login

    @MainActor
    func login(email: String, password: String) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let response = try await network.login(email: email, password: password)
            currentUser = response.user
            households = response.households
            isAuthenticated = true

            // Auto-select first household if available
            if let firstHousehold = households.first {
                selectHousehold(firstHousehold.id)
            }

            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    // MARK: - Register

    @MainActor
    func register(email: String, password: String, displayName: String?) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let response = try await network.register(email: email, password: password, displayName: displayName)
            currentUser = response.user
            households = response.households
            isAuthenticated = true
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    // MARK: - Logout

    @MainActor
    func logout() async {
        await network.logout()
        isAuthenticated = false
        currentUser = nil
        households = []
        currentHouseholdId = nil
        UserDefaults.standard.removeObject(forKey: "currentHouseholdId")
    }

    // MARK: - Household Management

    @MainActor
    func fetchHouseholds() async {
        do {
            let response: HouseholdsApiResponse = try await network.request(
                endpoint: Endpoints.households,
                requiresAuth: true
            )
            // Convert API response to UserHousehold
            households = response.households.map { h in
                UserHousehold(
                    id: h.id,
                    name: h.name,
                    role: h.role,
                    displayName: h.displayName,
                    joinedAt: h.createdAt  // API returns created_at, use as joined_at
                )
            }
        } catch {
            // Silently fail - households list might just be empty
        }
    }

    @MainActor
    func selectHousehold(_ id: Int) {
        currentHouseholdId = id
        UserDefaults.standard.set(id, forKey: "currentHouseholdId")
        Task {
            await network.setHouseholdId(id)
        }
    }

    @MainActor
    func createHousehold(name: String) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let body = ["name": name]
            let response: CreateHouseholdResponse = try await network.request(
                endpoint: Endpoints.households,
                method: .post,
                body: body,
                requiresAuth: true
            )
            let newHousehold = UserHousehold(
                id: response.household.id,
                name: response.household.name,
                role: response.household.role,
                displayName: response.household.displayName,
                joinedAt: response.household.createdAt
            )
            households.append(newHousehold)
            selectHousehold(newHousehold.id)
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func clearError() {
        error = nil
    }
}

// MARK: - Response Types

private struct UserMeResponse: Codable {
    let user: User
}

// Response from GET /households
private struct HouseholdsApiResponse: Codable {
    let households: [HouseholdApiItem]
}

private struct HouseholdApiItem: Codable {
    let id: Int
    let name: String
    let role: String
    let displayName: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case role
        case displayName = "display_name"
        case createdAt = "created_at"
    }
}

// Response from POST /households
private struct CreateHouseholdResponse: Codable {
    let household: HouseholdApiItem
}
