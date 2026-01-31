import Foundation
import Observation

@Observable
final class AuthManager: Sendable {
    // Test mode flag - set by HouseholdTrackerApp when MAESTRO_TEST env var is detected
    nonisolated(unsafe) static var isTestMode = false
    private static let testCredentials = (
        email: "demo_alice@example.com",
        password: "password123"
    )

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

        // TEST MODE: Auto-login with test credentials when running Maestro tests
        if Self.isTestMode && !isAuthenticated {
            _ = await login(
                email: Self.testCredentials.email,
                password: Self.testCredentials.password
            )
            return
        }

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
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
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
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
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
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    func clearError() {
        error = nil
    }

    // MARK: - Profile Management

    @MainActor
    func updateProfile(name: String) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let body = ["name": name]
            let response: UserProfileResponse = try await network.request(
                endpoint: Endpoints.userProfile,
                method: .put,
                body: body,
                requiresAuth: true
            )
            currentUser = response.user
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    @MainActor
    func changePassword(currentPassword: String, newPassword: String) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let body = [
                "current_password": currentPassword,
                "new_password": newPassword
            ]
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.userPassword,
                method: .put,
                body: body,
                requiresAuth: true
            )
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    @MainActor
    func requestEmailChange(newEmail: String, password: String) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let body = [
                "new_email": newEmail,
                "password": password
            ]
            let _: EmailChangeResponse = try await network.request(
                endpoint: Endpoints.userEmailRequest,
                method: .post,
                body: body,
                requiresAuth: true
            )
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    @MainActor
    func cancelEmailChange() async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.userEmailCancel,
                method: .post,
                requiresAuth: true
            )
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    @MainActor
    func deleteAccount(password: String) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let body = [
                "password": password,
                "confirm": "DELETE"
            ]
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.userDelete,
                method: .delete,
                body: body,
                requiresAuth: true
            )
            // Clear local state after successful deletion
            isAuthenticated = false
            currentUser = nil
            households = []
            currentHouseholdId = nil
            UserDefaults.standard.removeObject(forKey: "currentHouseholdId")
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    func forgotPassword(email: String) async -> Bool {
        do {
            let body = ["email": email]
            let _: ForgotPasswordResponse = try await network.request(
                endpoint: Endpoints.forgotPassword,
                method: .post,
                body: body,
                requiresAuth: false
            )
            return true
        } catch {
            return false
        }
    }

    // MARK: - Invitation Management

    @MainActor
    func sendInvitation(householdId: Int, email: String) async -> SendInvitationResult? {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let body = ["email": email]
            let response: SendInvitationResponse = try await network.request(
                endpoint: Endpoints.householdInvitations(householdId),
                method: .post,
                body: body,
                requiresAuth: true
            )
            return SendInvitationResult(
                invitation: response.invitation,
                inviteUrl: response.inviteUrl,
                deepLinkUrl: response.deepLinkUrl,
                emailSent: response.emailSent
            )
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return nil
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return nil
        }
    }

    @MainActor
    func fetchPendingInvitations(householdId: Int) async -> [Invitation] {
        do {
            let response: InvitationsListResponse = try await network.request(
                endpoint: Endpoints.householdInvitations(householdId),
                requiresAuth: true
            )
            return response.invitations
        } catch {
            return []
        }
    }

    @MainActor
    func cancelInvitation(invitationId: Int) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.cancelInvitation(invitationId),
                method: .delete,
                requiresAuth: true
            )
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    @MainActor
    func getInvitationDetails(token: String) async -> InvitationDetails? {
        do {
            let response: InvitationDetailsResponse = try await network.request(
                endpoint: Endpoints.invitation(token),
                requiresAuth: false
            )
            return InvitationDetails(
                invitation: response.invitation,
                household: response.household,
                inviter: response.inviter
            )
        } catch {
            return nil
        }
    }

    @MainActor
    func acceptInvitation(token: String, displayName: String? = nil) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            var body: [String: String] = [:]
            if let name = displayName, !name.isEmpty {
                body["display_name"] = name
            }

            let response: AcceptInvitationResponse = try await network.request(
                endpoint: Endpoints.acceptInvitation(token),
                method: .post,
                body: body.isEmpty ? nil : body,
                requiresAuth: true
            )

            // Add the new household to the list
            let newHousehold = UserHousehold(
                id: response.household.id,
                name: response.household.name,
                role: response.household.role,
                displayName: response.household.displayName,
                joinedAt: response.household.createdAt
            )
            households.append(newHousehold)

            // Switch to the new household
            selectHousehold(newHousehold.id)

            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }
}

// MARK: - Response Types

private struct UserProfileResponse: Codable {
    let user: User
}

private struct EmailChangeResponse: Codable {
    let success: Bool
    let message: String
}

private struct ForgotPasswordResponse: Codable {
    let success: Bool
    let message: String
}

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

// MARK: - Invitation Response Types

struct Invitation: Codable, Identifiable {
    let id: Int
    let email: String
    let status: String
    let expiresAt: String
    let createdAt: String
    let invitedBy: InvitationUser?
    let household: InvitationHousehold?

    enum CodingKeys: String, CodingKey {
        case id, email, status
        case expiresAt = "expires_at"
        case createdAt = "created_at"
        case invitedBy = "invited_by"
        case household
    }
}

struct InvitationUser: Codable {
    let id: Int
    let name: String
    let email: String?
}

struct InvitationHousehold: Codable {
    let id: Int
    let name: String
}

struct SendInvitationResult {
    let invitation: Invitation
    let inviteUrl: String
    let deepLinkUrl: String
    let emailSent: Bool
}

private struct SendInvitationResponse: Codable {
    let invitation: Invitation
    let inviteUrl: String
    let deepLinkUrl: String
    let emailSent: Bool

    enum CodingKeys: String, CodingKey {
        case invitation
        case inviteUrl = "invite_url"
        case deepLinkUrl = "deep_link_url"
        case emailSent = "email_sent"
    }
}

private struct InvitationsListResponse: Codable {
    let invitations: [Invitation]
}

struct InvitationDetails {
    let invitation: InvitationBasic
    let household: InvitationHousehold?
    let inviter: InvitationUser?
}

struct InvitationBasic: Codable {
    let id: Int
    let email: String
    let expiresAt: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, email
        case expiresAt = "expires_at"
        case createdAt = "created_at"
    }
}

private struct InvitationDetailsResponse: Codable {
    let invitation: InvitationBasic
    let household: InvitationHousehold?
    let inviter: InvitationUser?
}

private struct AcceptInvitationResponse: Codable {
    let success: Bool
    let household: HouseholdApiItem
}
