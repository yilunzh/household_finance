import SwiftUI

struct LoginView: View {
    @Environment(AuthManager.self) private var authManager

    @State private var email = ""
    @State private var password = ""
    @State private var isRegistering = false
    @State private var displayName = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 32) {
                    // Logo and Title
                    VStack(spacing: 16) {
                        Image(systemName: "dollarsign.circle.fill")
                            .font(.system(size: 80))
                            .foregroundStyle(.green)

                        Text("Lucky Ledger")
                            .font(.largeTitle)
                            .fontWeight(.bold)

                        Text("Track household expenses together")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.top, 60)

                    // Form
                    VStack(spacing: 16) {
                        if isRegistering {
                            TextField("Display Name", text: $displayName)
                                .textFieldStyle(.roundedBorder)
                                .textContentType(.name)
                                .autocorrectionDisabled()
                        }

                        TextField("Email", text: $email)
                            .textFieldStyle(.roundedBorder)
                            .textContentType(.emailAddress)
                            .keyboardType(.emailAddress)
                            .autocapitalization(.none)
                            .autocorrectionDisabled()

                        SecureField("Password", text: $password)
                            .textFieldStyle(.roundedBorder)
                            .textContentType(isRegistering ? .newPassword : .password)

                        if let error = authManager.error {
                            Text(error)
                                .font(.caption)
                                .foregroundStyle(.red)
                                .multilineTextAlignment(.center)
                        }

                        Button {
                            Task {
                                await performAuth()
                            }
                        } label: {
                            if authManager.isLoading {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Text(isRegistering ? "Create Account" : "Log In")
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .disabled(!isFormValid || authManager.isLoading)
                    }
                    .padding(.horizontal, 32)

                    // Toggle between login and register
                    Button {
                        withAnimation {
                            isRegistering.toggle()
                            authManager.clearError()
                        }
                    } label: {
                        if isRegistering {
                            Text("Already have an account? **Log in**")
                        } else {
                            Text("Don't have an account? **Sign up**")
                        }
                    }
                    .font(.subheadline)

                    Spacer()
                }
            }
            .navigationBarHidden(true)
        }
    }

    private var isFormValid: Bool {
        !email.isEmpty && !password.isEmpty && password.count >= 6
    }

    private func performAuth() async {
        if isRegistering {
            _ = await authManager.register(
                email: email,
                password: password,
                displayName: displayName.isEmpty ? nil : displayName
            )
        } else {
            _ = await authManager.login(email: email, password: password)
        }
    }
}

#Preview {
    LoginView()
        .environment(AuthManager())
}
