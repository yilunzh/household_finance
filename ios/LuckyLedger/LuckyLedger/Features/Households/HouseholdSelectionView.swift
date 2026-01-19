import SwiftUI

struct HouseholdSelectionView: View {
    @Environment(AuthManager.self) private var authManager

    @State private var showCreateSheet = false
    @State private var newHouseholdName = ""

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                if authManager.households.isEmpty {
                    // No households - prompt to create
                    VStack(spacing: 16) {
                        Image(systemName: "house")
                            .font(.system(size: 60))
                            .foregroundStyle(.secondary)

                        Text("No Household Yet")
                            .font(.title2)
                            .fontWeight(.semibold)

                        Text("Create a household to start tracking expenses with your family or roommates.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal)

                        Button("Create Household") {
                            showCreateSheet = true
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                    }
                    .padding()
                } else {
                    // Show list of households
                    List {
                        Section {
                            ForEach(authManager.households) { household in
                                Button {
                                    authManager.selectHousehold(household.id)
                                } label: {
                                    HStack {
                                        VStack(alignment: .leading) {
                                            Text(household.name)
                                                .font(.headline)
                                                .foregroundStyle(.primary)

                                            Text(household.role.capitalized)
                                                .font(.caption)
                                                .foregroundStyle(.secondary)
                                        }

                                        Spacer()

                                        Image(systemName: "chevron.right")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                        } header: {
                            Text("Select a Household")
                        }

                        Section {
                            Button {
                                showCreateSheet = true
                            } label: {
                                Label("Create New Household", systemImage: "plus.circle")
                            }
                        }
                    }
                }
            }
            .navigationTitle("Households")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        Task {
                            await authManager.logout()
                        }
                    } label: {
                        Text("Logout")
                    }
                }
            }
            .sheet(isPresented: $showCreateSheet) {
                CreateHouseholdSheet(name: $newHouseholdName) {
                    Task {
                        if await authManager.createHousehold(name: newHouseholdName) {
                            showCreateSheet = false
                            newHouseholdName = ""
                        }
                    }
                }
            }
        }
    }
}

struct CreateHouseholdSheet: View {
    @Binding var name: String
    let onCreate: () -> Void

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Household Name", text: $name)
                } footer: {
                    Text("Give your household a name, like \"Home\" or \"Smith Family\"")
                }
            }
            .navigationTitle("New Household")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        onCreate()
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
        .presentationDetents([.medium])
    }
}

#Preview {
    HouseholdSelectionView()
        .environment(AuthManager())
}
