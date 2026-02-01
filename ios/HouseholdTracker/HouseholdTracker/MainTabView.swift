import SwiftUI

struct MainTabView: View {
    @Environment(AuthManager.self) private var authManager
    @State private var selectedTab: CustomTabBar.Tab = .transactions

    var body: some View {
        TabBarContainer(selectedTab: $selectedTab) {
            Group {
                switch selectedTab {
                case .transactions:
                    TransactionsView()
                case .reconciliation:
                    ReconciliationView()
                case .budget:
                    BudgetView()
                case .settings:
                    SettingsView()
                }
            }
            .padding(.bottom, Layout.tabBarHeight) // Account for custom tab bar
        }
    }
}

struct SettingsView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.colorScheme) private var colorScheme
    @State private var showingEditName = false
    @State private var showingDeleteAccount = false
    @State private var membersViewModel = HouseholdSettingsViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    // Profile Card
                    if let user = authManager.currentUser {
                        CardContainer(hasGradient: true) {
                            HStack(spacing: Spacing.md) {
                                // Avatar
                                Circle()
                                    .fill(Color.terracotta100)
                                    .frame(width: 56, height: 56)
                                    .overlay(
                                        CatIcon(name: .silhouette, size: .lg, color: .terracotta500)
                                    )

                                VStack(alignment: .leading, spacing: Spacing.xxs) {
                                    Text(user.name)
                                        .font(.displaySmall)
                                        .foregroundColor(.textPrimary)
                                    Text(user.email)
                                        .font(.bodySmall)
                                        .foregroundColor(.textSecondary)
                                }

                                Spacer()

                                Button {
                                    showingEditName = true
                                } label: {
                                    CatIcon(name: .pencil, size: .md, color: .terracotta500)
                                }
                            }
                        }
                        .padding(.horizontal, Spacing.md)
                    }

                    // Household Section
                    if let householdId = authManager.currentHouseholdId,
                       let household = authManager.households.first(where: { $0.id == householdId }) {
                        SectionCard(title: "Household") {
                            SectionRow {
                                NavigationLink {
                                    HouseholdSettingsView()
                                } label: {
                                    SettingsRowContent(
                                        icon: .house,
                                        title: household.name,
                                        showChevron: true,
                                        iconTint: .terracotta500
                                    )
                                }
                                .buttonStyle(.plain)
                            }

                            SectionRow {
                                NavigationLink {
                                    MemberListView(viewModel: membersViewModel)
                                } label: {
                                    SettingsRowContent(
                                        icon: .group,
                                        title: "Members",
                                        showChevron: true,
                                        iconTint: .terracotta500
                                    )
                                }
                                .buttonStyle(.plain)
                            }

                            if authManager.households.count > 1 {
                                SectionRow(showDivider: false) {
                                    NavigationLink {
                                        HouseholdSwitcherView()
                                    } label: {
                                        SettingsRowContent(
                                            icon: .sparkle,
                                            title: "Switch Household",
                                            showChevron: true,
                                            iconTint: .terracotta500
                                        )
                                    }
                                    .buttonStyle(.plain)
                                }
                            } else {
                                SectionRow(showDivider: false) {
                                    NavigationLink {
                                        CreateHouseholdView()
                                    } label: {
                                        SettingsRowContent(
                                            icon: .sparkle,
                                            title: "Create New Household",
                                            showChevron: true,
                                            iconTint: .terracotta500
                                        )
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                        .padding(.horizontal, Spacing.md)

                        // Invitations Section
                        SectionCard(title: "Invitations") {
                            SectionRow {
                                NavigationLink {
                                    InviteMemberView()
                                } label: {
                                    SettingsRowContent(
                                        icon: .envelope,
                                        title: "Invite Member",
                                        showChevron: true,
                                        iconTint: .terracotta500
                                    )
                                }
                                .buttonStyle(.plain)
                            }

                            SectionRow(showDivider: false) {
                                NavigationLink {
                                    PendingInvitationsView()
                                } label: {
                                    SettingsRowContent(
                                        icon: .clock,
                                        title: "Pending Invitations",
                                        showChevron: true,
                                        iconTint: .terracotta500
                                    )
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.horizontal, Spacing.md)

                        // Configuration Section
                        SectionCard(title: "Configuration") {
                            SectionRow {
                                NavigationLink {
                                    ExpenseTypesView()
                                } label: {
                                    SettingsRowContent(
                                        icon: .folder,
                                        title: "Expense Types",
                                        showChevron: true,
                                        iconTint: .terracotta500
                                    )
                                }
                                .buttonStyle(.plain)
                            }

                            SectionRow {
                                NavigationLink {
                                    AutoCategoryRulesView()
                                } label: {
                                    SettingsRowContent(
                                        icon: .lightbulb,
                                        title: "Auto-Category Rules",
                                        showChevron: true,
                                        iconTint: .terracotta500
                                    )
                                }
                                .buttonStyle(.plain)
                            }

                            SectionRow {
                                NavigationLink {
                                    ExportView()
                                } label: {
                                    SettingsRowContent(
                                        icon: .download,
                                        title: "Export Data",
                                        showChevron: true,
                                        iconTint: .terracotta500
                                    )
                                }
                                .buttonStyle(.plain)
                            }

                            SectionRow(showDivider: false) {
                                NavigationLink {
                                    BankImportSessionsView()
                                } label: {
                                    SettingsRowContent(
                                        icon: .sparkle,
                                        title: "Bank Import",
                                        showChevron: true,
                                        iconTint: .terracotta500
                                    )
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.horizontal, Spacing.md)
                    }

                    // Security Section
                    SectionCard(title: "Security") {
                        SectionRow {
                            NavigationLink {
                                ChangePasswordView()
                            } label: {
                                SettingsRowContent(
                                    icon: .lock,
                                    title: "Change Password",
                                    showChevron: true,
                                    iconTint: .terracotta500
                                )
                            }
                            .buttonStyle(.plain)
                        }

                        SectionRow(showDivider: false) {
                            NavigationLink {
                                ChangeEmailView()
                            } label: {
                                SettingsRowContent(
                                    icon: .envelope,
                                    title: "Change Email",
                                    showChevron: true,
                                    iconTint: .terracotta500
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.horizontal, Spacing.md)

                    // Log Out Button
                    Button {
                        HapticManager.warning()
                        Task {
                            await authManager.logout()
                        }
                    } label: {
                        HStack(spacing: Spacing.sm) {
                            CatIcon(name: .wave, size: .md, color: .rose500)
                            Text("Log Out")
                                .font(.labelLarge)
                                .foregroundColor(.rose500)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, Spacing.sm)
                        .background(Color.rose100)
                        .cornerRadius(CornerRadius.large)
                    }
                    .padding(.horizontal, Spacing.md)

                    // Delete Account
                    Button {
                        showingDeleteAccount = true
                    } label: {
                        Text("Delete Account")
                            .font(.labelMedium)
                            .foregroundColor(.textTertiary)
                    }
                    .padding(.top, Spacing.sm)

                    // Footer
                    VStack(spacing: Spacing.xs) {
                        CatIcon(name: .heart, size: .md, color: .terracotta400)
                        Text("Made with love for families")
                            .font(.caption)
                            .foregroundColor(.textTertiary)
                    }
                    .padding(.vertical, Spacing.lg)
                }
                .padding(.top, Spacing.md)
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .sheet(isPresented: $showingEditName) {
                EditNameSheet()
            }
            .sheet(isPresented: $showingDeleteAccount) {
                DeleteAccountSheet()
            }
        }
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

// MARK: - Settings Row Content
struct SettingsRowContent: View {
    let icon: CatIcon.Name
    let title: String
    var showChevron: Bool = true
    var iconTint: Color? = nil  // Optional override for semantic coloring

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.sm) {
            CatIcon(name: icon, size: .md, color: iconTint ?? defaultIconColor)
            Text(title)
                .font(.bodyLarge)
                .foregroundColor(textColor)
            Spacer()
            if showChevron {
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(.textTertiary)
            }
        }
    }

    private var defaultIconColor: Color {
        colorScheme == .dark ? .warm400 : .warm600
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }
}

// MARK: - Create Household View
struct CreateHouseholdView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme

    @State private var name = ""
    @State private var isCreating = false

    var body: some View {
        ScrollView {
            VStack(spacing: Spacing.lg) {
                // Icon
                CatIcon(name: .sparkle, size: .xl, color: .terracotta500)
                    .padding(.top, Spacing.lg)

                // Form
                VStack(alignment: .leading, spacing: Spacing.sm) {
                    FormField(label: "Household Name", isRequired: true) {
                        StyledTextField(
                            placeholder: "e.g., Smith Family",
                            text: $name,
                            icon: .house
                        )
                    }

                    Text("Give your household a name, like \"Home\" or \"Smith Family\"")
                        .font(.caption)
                        .foregroundColor(.textTertiary)
                }
                .padding(.horizontal, Spacing.lg)

                Spacer(minLength: Spacing.xxl)

                // Action Button
                PrimaryButton(
                    title: isCreating ? "Creating..." : "Create Household",
                    icon: .sparkle,
                    action: createHousehold,
                    isDisabled: name.trimmingCharacters(in: .whitespaces).isEmpty || isCreating
                )
                .padding(.horizontal, Spacing.lg)
                .padding(.bottom, Spacing.lg)
            }
            .frame(maxWidth: .infinity)
        }
        .background(backgroundColor.ignoresSafeArea())
        .navigationTitle("New Household")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Error", isPresented: .constant(authManager.error != nil)) {
            Button("OK") {
                authManager.clearError()
            }
        } message: {
            Text(authManager.error ?? "")
        }
    }

    private func createHousehold() {
        Task {
            isCreating = true
            if await authManager.createHousehold(name: name) {
                HapticManager.success()
                dismiss()
            } else {
                HapticManager.error()
            }
            isCreating = false
        }
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
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

// MARK: - Change Password View

struct ChangePasswordView: View {
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

            Section {
                Button {
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
                } label: {
                    HStack {
                        Spacer()
                        if isSaving {
                            ProgressView()
                        } else {
                            Text("Save")
                        }
                        Spacer()
                    }
                }
                .disabled(!canSave || isSaving)
            }
        }
        .navigationTitle("Change Password")
        .navigationBarTitleDisplayMode(.inline)
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

// MARK: - Change Email View

struct ChangeEmailView: View {
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

            Section {
                Button {
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
                } label: {
                    HStack {
                        Spacer()
                        if isSaving {
                            ProgressView()
                        } else {
                            Text("Send Verification")
                        }
                        Spacer()
                    }
                }
                .disabled(!canSave || isSaving)
            }
        }
        .navigationTitle("Change Email")
        .navigationBarTitleDisplayMode(.inline)
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
