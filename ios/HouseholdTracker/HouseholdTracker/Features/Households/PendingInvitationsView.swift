import SwiftUI

struct PendingInvitationsView: View {
    @Environment(AuthManager.self) private var authManager

    @State private var invitations: [Invitation] = []
    @State private var isLoading = false
    @State private var showingInviteSheet = false

    var body: some View {
        Group {
            if isLoading {
                ProgressView("Loading...")
            } else if invitations.isEmpty {
                ContentUnavailableView {
                    Label("No Pending Invitations", systemImage: "envelope.badge")
                } description: {
                    Text("Invite someone to join your household.")
                } actions: {
                    Button("Send Invitation") {
                        showingInviteSheet = true
                    }
                    .buttonStyle(.borderedProminent)
                }
            } else {
                List {
                    ForEach(invitations) { invitation in
                        InvitationRow(
                            invitation: invitation,
                            onCancel: {
                                await cancelInvitation(invitation)
                            }
                        )
                    }
                }
            }
        }
        .navigationTitle("Pending Invitations")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showingInviteSheet = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showingInviteSheet) {
            NavigationStack {
                InviteMemberView()
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Cancel") {
                                showingInviteSheet = false
                            }
                        }
                    }
            }
        }
        .task {
            await loadInvitations()
        }
        .refreshable {
            await loadInvitations()
        }
    }

    private func loadInvitations() async {
        guard let householdId = authManager.currentHouseholdId else { return }
        isLoading = true
        invitations = await authManager.fetchPendingInvitations(householdId: householdId)
        isLoading = false
    }

    private func cancelInvitation(_ invitation: Invitation) async {
        if await authManager.cancelInvitation(invitationId: invitation.id) {
            invitations.removeAll { $0.id == invitation.id }
        }
    }
}

// MARK: - Invitation Row

struct InvitationRow: View {
    let invitation: Invitation
    let onCancel: () async -> Void

    @State private var isCanceling = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(invitation.email)
                        .font(.headline)

                    Text("Sent \(formattedDate)")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Text("Expires \(expirationDate)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Button(role: .destructive) {
                    Task {
                        isCanceling = true
                        await onCancel()
                        isCanceling = false
                    }
                } label: {
                    if isCanceling {
                        ProgressView()
                    } else {
                        Text("Cancel")
                    }
                }
                .buttonStyle(.bordered)
                .disabled(isCanceling)
            }
        }
        .padding(.vertical, 4)
    }

    private var formattedDate: String {
        // Parse ISO date and format nicely
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: invitation.createdAt) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .medium
            displayFormatter.timeStyle = .short
            return displayFormatter.string(from: date)
        }
        return invitation.createdAt
    }

    private var expirationDate: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: invitation.expiresAt) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .medium
            return displayFormatter.string(from: date)
        }
        return invitation.expiresAt
    }
}

#Preview {
    PendingInvitationsView()
        .environment(AuthManager())
}
