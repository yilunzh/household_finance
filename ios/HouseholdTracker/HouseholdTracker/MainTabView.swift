import SwiftUI

struct MainTabView: View {
    @Environment(AuthManager.self) private var authManager

    var body: some View {
        TabView {
            TransactionsView()
                .tabItem {
                    Label("Transactions", systemImage: "list.bullet.rectangle")
                }

            ReconciliationView()
                .tabItem {
                    Label("Summary", systemImage: "chart.pie")
                }

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
        }
    }
}

struct SettingsView: View {
    @Environment(AuthManager.self) private var authManager
    @State private var showingEditName = false
    @State private var showingChangePassword = false
    @State private var showingChangeEmail = false
    @State private var showingDeleteAccount = false
    @State private var showingInviteMember = false
    @State private var showingPendingInvitations = false

    var body: some View {
        NavigationStack {
            List {
                // Current Household Section
                if let householdId = authManager.currentHouseholdId,
                   let household = authManager.households.first(where: { $0.id == householdId }) {
                    Section {
                        NavigationLink {
                            HouseholdSettingsView()
                        } label: {
                            HStack {
                                Label(household.name, systemImage: "house")
                                Spacer()
                                Text("Settings")
                                    .foregroundStyle(.secondary)
                            }
                        }

                        if authManager.households.count > 1 {
                            NavigationLink {
                                HouseholdSwitcherView()
                            } label: {
                                Label("Switch Household", systemImage: "arrow.left.arrow.right")
                            }
                        }
                    } header: {
                        Text("Current Household")
                    }

                    // Invitations Section
                    Section {
                        Button {
                            showingInviteMember = true
                        } label: {
                            Label("Invite Member", systemImage: "person.badge.plus")
                        }

                        Button {
                            showingPendingInvitations = true
                        } label: {
                            Label("Pending Invitations", systemImage: "envelope.badge")
                        }
                    } header: {
                        Text("Invitations")
                    }
                }

                // Account Section
                Section {
                    if let user = authManager.currentUser {
                        Button {
                            showingEditName = true
                        } label: {
                            HStack {
                                Text("Name")
                                Spacer()
                                Text(user.name)
                                    .foregroundStyle(.secondary)
                                Image(systemName: "chevron.right")
                                    .font(.footnote)
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .foregroundStyle(.primary)

                        HStack {
                            Text("Email")
                            Spacer()
                            Text(user.email)
                                .foregroundStyle(.secondary)
                        }
                    }
                } header: {
                    Text("Account")
                }

                // Security Section
                Section {
                    Button {
                        showingChangePassword = true
                    } label: {
                        Label("Change Password", systemImage: "lock")
                    }

                    Button {
                        showingChangeEmail = true
                    } label: {
                        Label("Change Email", systemImage: "envelope")
                    }
                } header: {
                    Text("Security")
                }

                // Actions Section
                Section {
                    Button(role: .destructive) {
                        Task {
                            await authManager.logout()
                        }
                    } label: {
                        Label("Log Out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }

                // Danger Zone
                Section {
                    Button(role: .destructive) {
                        showingDeleteAccount = true
                    } label: {
                        Label("Delete Account", systemImage: "trash")
                    }
                } footer: {
                    Text("This will permanently delete your account and all associated data.")
                }
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $showingEditName) {
                EditNameSheet()
            }
            .sheet(isPresented: $showingChangePassword) {
                ChangePasswordSheet()
            }
            .sheet(isPresented: $showingChangeEmail) {
                ChangeEmailSheet()
            }
            .sheet(isPresented: $showingDeleteAccount) {
                DeleteAccountSheet()
            }
            .sheet(isPresented: $showingInviteMember) {
                InviteMemberView()
            }
            .sheet(isPresented: $showingPendingInvitations) {
                PendingInvitationsView()
            }
        }
    }
}

// MARK: - Edit Name Sheet

struct EditNameSheet: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var isSaving = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Display Name", text: $name)
                        .textContentType(.name)
                        .autocorrectionDisabled()
                } footer: {
                    Text("This name will be displayed throughout the app.")
                }
            }
            .navigationTitle("Edit Name")
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
                            isSaving = true
                            if await authManager.updateProfile(name: name) {
                                dismiss()
                            }
                            isSaving = false
                        }
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty || isSaving)
                }
            }
            .onAppear {
                name = authManager.currentUser?.name ?? ""
            }
            .alert("Error", isPresented: .constant(authManager.error != nil)) {
                Button("OK") {
                    authManager.clearError()
                }
            } message: {
                Text(authManager.error ?? "")
            }
        }
    }
}

// MARK: - Change Password Sheet

struct ChangePasswordSheet: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss
    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var isSaving = false
    @State private var showSuccess = false

    private var canSave: Bool {
        !currentPassword.isEmpty &&
        newPassword.count >= 8 &&
        newPassword == confirmPassword
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    SecureField("Current Password", text: $currentPassword)
                        .textContentType(.password)
                }

                Section {
                    SecureField("New Password", text: $newPassword)
                        .textContentType(.newPassword)
                    SecureField("Confirm New Password", text: $confirmPassword)
                        .textContentType(.newPassword)
                } footer: {
                    Text("Password must be at least 8 characters.")
                }
            }
            .navigationTitle("Change Password")
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
                            isSaving = true
                            if await authManager.changePassword(
                                currentPassword: currentPassword,
                                newPassword: newPassword
                            ) {
                                showSuccess = true
                            }
                            isSaving = false
                        }
                    }
                    .disabled(!canSave || isSaving)
                }
            }
            .alert("Error", isPresented: .constant(authManager.error != nil)) {
                Button("OK") {
                    authManager.clearError()
                }
            } message: {
                Text(authManager.error ?? "")
            }
            .alert("Success", isPresented: $showSuccess) {
                Button("OK") {
                    dismiss()
                }
            } message: {
                Text("Your password has been changed.")
            }
        }
    }
}

// MARK: - Change Email Sheet

struct ChangeEmailSheet: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss
    @State private var newEmail = ""
    @State private var password = ""
    @State private var isSaving = false
    @State private var showSuccess = false

    private var canSave: Bool {
        !newEmail.isEmpty &&
        newEmail.contains("@") &&
        !password.isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("New Email", text: $newEmail)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                } footer: {
                    Text("A verification email will be sent to this address.")
                }

                Section {
                    SecureField("Current Password", text: $password)
                        .textContentType(.password)
                } footer: {
                    Text("Enter your current password to confirm this change.")
                }
            }
            .navigationTitle("Change Email")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Send Verification") {
                        Task {
                            isSaving = true
                            if await authManager.requestEmailChange(
                                newEmail: newEmail,
                                password: password
                            ) {
                                showSuccess = true
                            }
                            isSaving = false
                        }
                    }
                    .disabled(!canSave || isSaving)
                }
            }
            .alert("Error", isPresented: .constant(authManager.error != nil)) {
                Button("OK") {
                    authManager.clearError()
                }
            } message: {
                Text(authManager.error ?? "")
            }
            .alert("Verification Sent", isPresented: $showSuccess) {
                Button("OK") {
                    dismiss()
                }
            } message: {
                Text("Please check your email and click the verification link to complete the change.")
            }
        }
    }
}

// MARK: - Delete Account Sheet

struct DeleteAccountSheet: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss
    @State private var password = ""
    @State private var confirmText = ""
    @State private var isDeleting = false

    private var canDelete: Bool {
        !password.isEmpty && confirmText == "DELETE"
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("This action cannot be undone. All your data will be permanently deleted.")
                        .foregroundStyle(.secondary)
                }

                Section {
                    SecureField("Current Password", text: $password)
                        .textContentType(.password)
                }

                Section {
                    TextField("Type DELETE to confirm", text: $confirmText)
                        .autocapitalization(.allCharacters)
                        .autocorrectionDisabled()
                } footer: {
                    Text("Type DELETE in all caps to confirm account deletion.")
                }

                Section {
                    Button(role: .destructive) {
                        Task {
                            isDeleting = true
                            if await authManager.deleteAccount(password: password) {
                                dismiss()
                            }
                            isDeleting = false
                        }
                    } label: {
                        HStack {
                            Spacer()
                            if isDeleting {
                                ProgressView()
                            } else {
                                Text("Delete My Account")
                            }
                            Spacer()
                        }
                    }
                    .disabled(!canDelete || isDeleting)
                }
            }
            .navigationTitle("Delete Account")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .alert("Error", isPresented: .constant(authManager.error != nil)) {
                Button("OK") {
                    authManager.clearError()
                }
            } message: {
                Text(authManager.error ?? "")
            }
        }
    }
}

struct HouseholdSwitcherView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        List {
            ForEach(authManager.households) { household in
                Button {
                    authManager.selectHousehold(household.id)
                    dismiss()
                } label: {
                    HStack {
                        Text(household.name)
                            .foregroundStyle(.primary)

                        Spacer()

                        if household.id == authManager.currentHouseholdId {
                            Image(systemName: "checkmark")
                                .foregroundStyle(.blue)
                        }
                    }
                }
            }
        }
        .navigationTitle("Switch Household")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    MainTabView()
        .environment(AuthManager())
}
