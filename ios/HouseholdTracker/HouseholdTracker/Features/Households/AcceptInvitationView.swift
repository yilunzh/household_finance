import SwiftUI

struct AcceptInvitationView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss

    let token: String
    @State private var details: InvitationDetails?
    @State private var displayName = ""
    @State private var isLoading = true
    @State private var error: String?
    @State private var showSuccess = false

    var body: some View {
        NavigationStack {
            Group {
                if isLoading {
                    ProgressView("Loading invitation...")
                } else if let error = error {
                    ContentUnavailableView {
                        Label("Invalid Invitation", systemImage: "exclamationmark.triangle")
                    } description: {
                        Text(error)
                    } actions: {
                        Button("Close") {
                            dismiss()
                        }
                        .buttonStyle(.borderedProminent)
                    }
                } else if let details = details {
                    Form {
                        Section {
                            VStack(spacing: 12) {
                                Image(systemName: "house.fill")
                                    .font(.system(size: 50))
                                    .foregroundStyle(.blue)

                                Text("Join \(details.household?.name ?? "Household")")
                                    .font(.title2)
                                    .fontWeight(.bold)

                                if let inviter = details.inviter {
                                    Text("**\(inviter.name)** invited you to join their household.")
                                        .foregroundStyle(.secondary)
                                        .multilineTextAlignment(.center)
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical)
                        }

                        Section {
                            TextField("Your display name", text: $displayName)
                                .textContentType(.name)
                        } footer: {
                            Text("This is how other household members will see your name.")
                        }

                        if let authError = authManager.error {
                            Section {
                                Text(authError)
                                    .foregroundStyle(.red)
                            }
                        }

                        Section {
                            Button {
                                Task {
                                    await acceptInvitation()
                                }
                            } label: {
                                HStack {
                                    Spacer()
                                    if authManager.isLoading {
                                        ProgressView()
                                    } else {
                                        Text("Join Household")
                                    }
                                    Spacer()
                                }
                            }
                            .disabled(authManager.isLoading)
                        }
                    }
                }
            }
            .navigationTitle("Invitation")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .task {
                await loadInvitation()
            }
            .alert("Welcome!", isPresented: $showSuccess) {
                Button("OK") {
                    dismiss()
                }
            } message: {
                Text("You have successfully joined the household.")
            }
        }
    }

    private func loadInvitation() async {
        isLoading = true
        if let result = await authManager.getInvitationDetails(token: token) {
            details = result
            // Default display name to user's name
            displayName = authManager.currentUser?.name ?? ""
        } else {
            error = "This invitation is invalid or has expired."
        }
        isLoading = false
    }

    private func acceptInvitation() async {
        let name = displayName.isEmpty ? nil : displayName
        if await authManager.acceptInvitation(token: token, displayName: name) {
            showSuccess = true
        }
    }
}

#Preview {
    AcceptInvitationView(token: "test-token")
        .environment(AuthManager())
}
