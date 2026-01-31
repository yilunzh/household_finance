import SwiftUI

struct MemberListView: View {
    @Bindable var viewModel: HouseholdSettingsViewModel
    @Environment(AuthManager.self) private var authManager

    @State private var selectedMember: HouseholdMember?
    @State private var showEditDisplayName = false
    @State private var showRemoveConfirmation = false
    @State private var memberToRemove: HouseholdMember?

    var body: some View {
        List {
            ForEach(viewModel.members) { member in
                MemberRow(
                    member: member,
                    isCurrentUser: isCurrentUser(member),
                    canEdit: canEdit(member),
                    canRemove: canRemove(member),
                    onEdit: {
                        selectedMember = member
                        showEditDisplayName = true
                    },
                    onRemove: {
                        memberToRemove = member
                        showRemoveConfirmation = true
                    }
                )
            }
        }
        .navigationTitle("Members")
        .navigationBarTitleDisplayMode(.inline)
        .accessibleBackButton("back-members")
        .sheet(isPresented: $showEditDisplayName) {
            if let member = selectedMember {
                EditMemberSheet(
                    viewModel: viewModel,
                    member: member
                )
            }
        }
        .alert("Remove Member?", isPresented: $showRemoveConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Remove", role: .destructive) {
                if let member = memberToRemove {
                    Task {
                        await viewModel.removeMember(userId: member.userId)
                    }
                }
            }
        } message: {
            if let member = memberToRemove {
                Text("Are you sure you want to remove \"\(member.displayName)\" from this household? They will lose access to all transactions.")
            }
        }
        .alert("Error", isPresented: .init(
            get: { viewModel.error != nil },
            set: { if !$0 { viewModel.clearError() } }
        )) {
            Button("OK") { viewModel.clearError() }
        } message: {
            Text(viewModel.error ?? "")
        }
        .task {
            // Load data if not already loaded
            if viewModel.members.isEmpty, let householdId = authManager.currentHouseholdId {
                await viewModel.loadHousehold(householdId: householdId)
            }
        }
        .refreshable {
            if let householdId = authManager.currentHouseholdId {
                await viewModel.loadHousehold(householdId: householdId)
            }
        }
    }

    private func isCurrentUser(_ member: HouseholdMember) -> Bool {
        guard let currentUserId = getCurrentUserId() else { return false }
        return member.userId == currentUserId
    }

    private func canEdit(_ member: HouseholdMember) -> Bool {
        // Can edit own display name, or owner can edit anyone
        isCurrentUser(member) || viewModel.isOwner
    }

    private func canRemove(_ member: HouseholdMember) -> Bool {
        // Only owners can remove, and cannot remove themselves or other owners
        viewModel.isOwner && !isCurrentUser(member) && !member.isOwner
    }

    private func getCurrentUserId() -> Int? {
        if let data = UserDefaults.standard.data(forKey: "currentUser"),
           let user = try? JSONDecoder().decode(User.self, from: data) {
            return user.id
        }
        return nil
    }
}

// MARK: - Member Row

struct MemberRow: View {
    let member: HouseholdMember
    let isCurrentUser: Bool
    let canEdit: Bool
    let canRemove: Bool
    let onEdit: () -> Void
    let onRemove: () -> Void

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(member.displayName)
                        .font(.headline)

                    if isCurrentUser {
                        Text("(You)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                HStack(spacing: 8) {
                    if member.isOwner {
                        Label("Owner", systemImage: "crown")
                            .font(.caption)
                            .foregroundStyle(.orange)
                    } else {
                        Text("Member")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    if let email = member.email {
                        Text(email)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Spacer()

            if canEdit || canRemove {
                Menu {
                    if canEdit {
                        Button {
                            onEdit()
                        } label: {
                            Label("Edit Display Name", systemImage: "pencil")
                        }
                    }

                    if canRemove {
                        Button(role: .destructive) {
                            onRemove()
                        } label: {
                            Label("Remove from Household", systemImage: "person.badge.minus")
                        }
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Edit Member Sheet

struct EditMemberSheet: View {
    @Bindable var viewModel: HouseholdSettingsViewModel
    let member: HouseholdMember
    @Environment(\.dismiss) private var dismiss
    @State private var displayName = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Display Name", text: $displayName)
                        .autocorrectionDisabled()
                } footer: {
                    Text("This is how the member's name appears in this household.")
                }

                if let email = member.email {
                    Section {
                        LabeledContent("Email", value: email)
                    }
                }
            }
            .navigationTitle("Edit Member")
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
                            if await viewModel.updateMemberDisplayName(
                                userId: member.userId,
                                newDisplayName: displayName
                            ) {
                                dismiss()
                            }
                        }
                    }
                    .disabled(displayName.trimmingCharacters(in: .whitespaces).isEmpty || viewModel.isSaving)
                }
            }
            .onAppear {
                displayName = member.displayName
            }
        }
        .presentationDetents([.medium])
    }
}

#Preview {
    NavigationStack {
        MemberListView(viewModel: HouseholdSettingsViewModel())
    }
    .environment(AuthManager())
}
