import SwiftUI

struct HouseholdSettingsView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss

    @State private var viewModel = HouseholdSettingsViewModel()
    @State private var showRenameSheet = false
    @State private var showLeaveConfirmation = false

    var body: some View {
        List {
            // Household Info Section
            Section {
                Button {
                    showRenameSheet = true
                } label: {
                    HStack {
                        Text("Name")
                        Spacer()
                        Text(viewModel.householdName)
                            .foregroundStyle(.secondary)
                        if viewModel.isOwner {
                            Image(systemName: "chevron.right")
                                .font(.footnote)
                                .foregroundStyle(.tertiary)
                        }
                    }
                }
                .foregroundStyle(.primary)
                .disabled(!viewModel.isOwner)
            } header: {
                Text("Household")
            } footer: {
                if !viewModel.isOwner {
                    Text("Only owners can rename the household.")
                }
            }

            // Members Section
            Section {
                NavigationLink {
                    MemberListView(viewModel: viewModel)
                } label: {
                    HStack {
                        Label("Members", systemImage: "person.2")
                            .foregroundStyle(Color.terracotta500)
                        Spacer()
                        Text("\(viewModel.members.count)")
                            .foregroundStyle(.secondary)
                    }
                }
            }

            // Leave Household Section
            if viewModel.canLeave {
                Section {
                    Button(role: .destructive) {
                        showLeaveConfirmation = true
                    } label: {
                        Label("Leave Household", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                } footer: {
                    Text("You will lose access to all transactions in this household.")
                }
            } else if viewModel.isOwner && viewModel.members.count > 1 {
                Section {
                    Text("Owners cannot leave while other members exist. Remove all members first or transfer ownership.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("Household Settings")
        .navigationBarTitleDisplayMode(.inline)
        .accessibleBackButton("back-household-settings")
        .task {
            if let householdId = authManager.currentHouseholdId {
                await viewModel.loadHousehold(householdId: householdId)
            }
        }
        .refreshable {
            if let householdId = authManager.currentHouseholdId {
                await viewModel.loadHousehold(householdId: householdId)
            }
        }
        .sheet(isPresented: $showRenameSheet) {
            RenameHouseholdSheet(viewModel: viewModel)
        }
        .alert("Leave Household?", isPresented: $showLeaveConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Leave", role: .destructive) {
                Task {
                    if await viewModel.leaveHousehold() {
                        await authManager.fetchHouseholds()
                        dismiss()
                    }
                }
            }
        } message: {
            Text("Are you sure you want to leave \"\(viewModel.householdName)\"? This action cannot be undone.")
        }
        .alert("Error", isPresented: .init(
            get: { viewModel.error != nil },
            set: { if !$0 { viewModel.clearError() } }
        )) {
            Button("OK") { viewModel.clearError() }
        } message: {
            Text(viewModel.error ?? "")
        }
    }
}

// MARK: - Rename Household Sheet

struct RenameHouseholdSheet: View {
    @Bindable var viewModel: HouseholdSettingsViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var newName = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Household Name", text: $newName)
                        .autocorrectionDisabled()
                } footer: {
                    Text("Give your household a name, like \"Home\" or \"Smith Family\"")
                }
            }
            .navigationTitle("Rename Household")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            if await viewModel.renameHousehold(newName: newName) {
                                dismiss()
                            }
                        }
                    }
                    .disabled(newName.trimmingCharacters(in: .whitespaces).isEmpty || viewModel.isSaving)
                }
            }
            .onAppear {
                newName = viewModel.householdName
            }
        }
        .presentationDetents([.medium])
    }
}

// MARK: - View Model

@Observable
class HouseholdSettingsViewModel {
    var householdId: Int?
    var householdName: String = ""
    var members: [HouseholdMember] = []
    var currentUserRole: String = "member"
    var error: String?
    var isSaving = false
    var isLoading = false

    private let network = NetworkManager.shared

    var isOwner: Bool {
        currentUserRole == "owner"
    }

    var canLeave: Bool {
        // Non-owners can always leave
        // Owners can only leave if they're the only member
        !isOwner || members.count == 1
    }

    func loadHousehold(householdId: Int) async {
        self.householdId = householdId
        isLoading = true
        defer { isLoading = false }

        do {
            let response: HouseholdDetailResponse = try await network.request(
                endpoint: Endpoints.household(householdId),
                method: .get,
                requiresAuth: true
            )
            householdName = response.household.name
            members = response.members

            // Find current user's role
            if let currentUserId = await getCurrentUserId() {
                if let member = members.first(where: { $0.userId == currentUserId }) {
                    currentUserRole = member.role
                }
            }
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
        }
    }

    func renameHousehold(newName: String) async -> Bool {
        guard let householdId = householdId else { return false }

        isSaving = true
        defer { isSaving = false }

        do {
            let body = ["name": newName.trimmingCharacters(in: .whitespaces)]
            let response: HouseholdResponse = try await network.request(
                endpoint: Endpoints.household(householdId),
                method: .put,
                body: body,
                requiresAuth: true
            )
            householdName = response.household.name
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

    func updateMemberDisplayName(userId: Int, newDisplayName: String) async -> Bool {
        guard let householdId = householdId else { return false }

        isSaving = true
        defer { isSaving = false }

        do {
            let body = ["display_name": newDisplayName.trimmingCharacters(in: .whitespaces)]
            let response: MemberResponse = try await network.request(
                endpoint: Endpoints.householdMember(householdId, userId: userId),
                method: .put,
                body: body,
                requiresAuth: true
            )

            // Update the member in our list
            if let index = members.firstIndex(where: { $0.userId == userId }) {
                members[index] = response.member
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

    func removeMember(userId: Int) async -> Bool {
        guard let householdId = householdId else { return false }

        isSaving = true
        defer { isSaving = false }

        do {
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.householdMember(householdId, userId: userId),
                method: .delete,
                requiresAuth: true
            )

            // Remove the member from our list
            members.removeAll { $0.userId == userId }
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

    func leaveHousehold() async -> Bool {
        guard let householdId = householdId else { return false }

        isSaving = true
        defer { isSaving = false }

        do {
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.leaveHousehold(householdId),
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

    func clearError() {
        error = nil
    }

    private func getCurrentUserId() async -> Int? {
        // Try to get current user ID from stored user info
        if let data = UserDefaults.standard.data(forKey: "currentUser"),
           let user = try? JSONDecoder().decode(User.self, from: data) {
            return user.id
        }
        return nil
    }
}

#Preview {
    NavigationStack {
        HouseholdSettingsView()
    }
    .environment(AuthManager())
}
