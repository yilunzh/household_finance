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

    var body: some View {
        NavigationStack {
            List {
                // Current Household Section
                if let householdId = authManager.currentHouseholdId,
                   let household = authManager.households.first(where: { $0.id == householdId }) {
                    Section {
                        HStack {
                            Label(household.name, systemImage: "house")
                            Spacer()
                            if authManager.households.count > 1 {
                                NavigationLink {
                                    HouseholdSwitcherView()
                                } label: {
                                    Text("Switch")
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    } header: {
                        Text("Current Household")
                    }
                }

                // Account Section
                Section {
                    if let user = authManager.currentUser {
                        HStack {
                            Text("Email")
                            Spacer()
                            Text(user.email)
                                .foregroundStyle(.secondary)
                        }

                        if let displayName = user.displayName {
                            HStack {
                                Text("Display Name")
                                Spacer()
                                Text(displayName)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                } header: {
                    Text("Account")
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
            }
            .navigationTitle("Settings")
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
