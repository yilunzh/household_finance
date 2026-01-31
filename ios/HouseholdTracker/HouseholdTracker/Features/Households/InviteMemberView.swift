import SwiftUI

struct InviteMemberView: View {
    @Environment(AuthManager.self) private var authManager

    @State private var email = ""
    @State private var showingResult = false
    @State private var inviteResult: SendInvitationResult?

    var body: some View {
        Form {
            Section {
                TextField("Email address", text: $email)
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .autocapitalization(.none)
                    .autocorrectionDisabled()
            } footer: {
                Text("Enter the email address of the person you want to invite to your household.")
            }

            if let error = authManager.error {
                Section {
                    Text(error)
                        .foregroundStyle(.red)
                }
            }

            Section {
                Button {
                    Task {
                        await sendInvitation()
                    }
                } label: {
                    HStack {
                        Spacer()
                        if authManager.isLoading {
                            ProgressView()
                        } else {
                            Text("Send Invitation")
                        }
                        Spacer()
                    }
                }
                .disabled(!isValidEmail || authManager.isLoading)
            }
        }
        .navigationTitle("Invite Member")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showingResult) {
            if let result = inviteResult {
                InvitationSentSheet(result: result)
            }
        }
    }

    private var isValidEmail: Bool {
        !email.isEmpty && email.contains("@") && email.contains(".")
    }

    private func sendInvitation() async {
        guard let householdId = authManager.currentHouseholdId else { return }

        if let result = await authManager.sendInvitation(householdId: householdId, email: email) {
            inviteResult = result
            showingResult = true
        }
    }
}

// MARK: - Invitation Sent Sheet

struct InvitationSentSheet: View {
    @Environment(\.dismiss) private var dismiss
    let result: SendInvitationResult

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Image(systemName: result.emailSent ? "envelope.badge.fill" : "link")
                    .font(.system(size: 60))
                    .foregroundStyle(.green)

                Text("Invitation Sent")
                    .font(.title)
                    .fontWeight(.bold)

                Text("An invitation has been sent to **\(result.invitation.email)**.")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)

                if !result.emailSent {
                    Text("Email could not be sent. Share the link below instead.")
                        .font(.caption)
                        .foregroundStyle(.orange)
                        .multilineTextAlignment(.center)
                }

                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("Share Link")
                        .font(.headline)

                    Text(result.inviteUrl)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                ShareLink(item: result.inviteUrl) {
                    HStack {
                        Image(systemName: "square.and.arrow.up")
                        Text("Share Invitation Link")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)

                Spacer()
            }
            .padding()
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}

#Preview {
    InviteMemberView()
        .environment(AuthManager())
}
