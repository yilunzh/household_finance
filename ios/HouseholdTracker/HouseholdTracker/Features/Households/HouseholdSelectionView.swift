import SwiftUI

struct HouseholdSelectionView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.colorScheme) private var colorScheme

    @State private var showCreateSheet = false
    @State private var newHouseholdName = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    if authManager.households.isEmpty {
                        // No households - prompt to create
                        EmptyState(
                            icon: .house,
                            title: "No Household Yet",
                            message: "Create a household to start tracking expenses with your family or roommates.",
                            actionTitle: "Create Household",
                            action: { showCreateSheet = true }
                        )
                    } else {
                        // Header
                        VStack(spacing: Spacing.xs) {
                            CatIcon(name: .house, size: .xl, color: .terracotta500)
                            Text("Select a Household")
                                .font(.displaySmall)
                                .foregroundColor(.textPrimary)
                        }
                        .padding(.top, Spacing.lg)

                        // Household List
                        VStack(spacing: Spacing.sm) {
                            ForEach(authManager.households) { household in
                                Button {
                                    HapticManager.buttonTap()
                                    authManager.selectHousehold(household.id)
                                } label: {
                                    CardContainer {
                                        HStack(spacing: Spacing.md) {
                                            Circle()
                                                .fill(Color.terracotta100)
                                                .frame(width: 48, height: 48)
                                                .overlay(
                                                    CatIcon(name: .house, size: .md, color: .terracotta500)
                                                )

                                            VStack(alignment: .leading, spacing: Spacing.xxs) {
                                                Text(household.name)
                                                    .font(.labelLarge)
                                                    .foregroundColor(.textPrimary)

                                                HStack(spacing: Spacing.xs) {
                                                    if household.role == "owner" {
                                                        Badge(text: "Owner", icon: .crown, style: .default)
                                                    } else {
                                                        Badge(text: "Member", style: .neutral)
                                                    }
                                                }
                                            }

                                            Spacer()

                                            Image(systemName: "chevron.right")
                                                .font(.caption)
                                                .foregroundColor(.textTertiary)
                                        }
                                    }
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.horizontal, Spacing.md)

                        // Create New Button
                        Button {
                            showCreateSheet = true
                        } label: {
                            HStack(spacing: Spacing.sm) {
                                CatIcon(name: .sparkle, size: .md, color: .terracotta500)
                                Text("Create New Household")
                                    .font(.labelLarge)
                                    .foregroundColor(.terracotta500)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, Spacing.sm)
                            .background(Color.terracotta100)
                            .cornerRadius(CornerRadius.large)
                        }
                        .padding(.horizontal, Spacing.md)
                        .padding(.top, Spacing.sm)
                    }
                }
                .padding(.bottom, Spacing.xxl)
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle("Households")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        HapticManager.warning()
                        Task {
                            await authManager.logout()
                        }
                    } label: {
                        HStack(spacing: Spacing.xxs) {
                            CatIcon(name: .wave, size: .sm, color: .rose500)
                            Text("Logout")
                                .font(.labelMedium)
                                .foregroundColor(.rose500)
                        }
                    }
                }
            }
            .sheet(isPresented: $showCreateSheet) {
                CreateHouseholdSheet(name: $newHouseholdName) {
                    Task {
                        if await authManager.createHousehold(name: newHouseholdName) {
                            HapticManager.success()
                            showCreateSheet = false
                            newHouseholdName = ""
                        } else {
                            HapticManager.error()
                        }
                    }
                }
            }
        }
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

struct CreateHouseholdSheet: View {
    @Binding var name: String
    let onCreate: () -> Void

    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        NavigationStack {
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

                Spacer()

                // Action Button
                PrimaryButton(
                    title: "Create Household",
                    icon: .sparkle,
                    action: onCreate,
                    isDisabled: name.trimmingCharacters(in: .whitespaces).isEmpty
                )
                .padding(.horizontal, Spacing.lg)
                .padding(.bottom, Spacing.lg)
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle("New Household")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.textSecondary)
                }
            }
        }
        .presentationDetents([.medium])
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

#Preview {
    HouseholdSelectionView()
        .environment(AuthManager())
}
