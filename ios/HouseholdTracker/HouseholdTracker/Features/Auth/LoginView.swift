import SwiftUI

struct LoginView: View {
    @Environment(AuthManager.self) private var authManager

    @State private var email = ""
    @State private var password = ""
    @State private var isRegistering = false
    @State private var displayName = ""
    @State private var showingForgotPassword = false

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

                        if !isRegistering {
                            HStack {
                                Spacer()
                                Button("Forgot Password?") {
                                    showingForgotPassword = true
                                }
                                .font(.caption)
                            }
                        }

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
            .sheet(isPresented: $showingForgotPassword) {
                ForgotPasswordSheet(prefillEmail: email)
            }
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

// MARK: - Forgot Password Sheet

struct ForgotPasswordSheet: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss
    @State private var email: String
    @State private var isSending = false
    @State private var showSuccess = false

    init(prefillEmail: String = "") {
        _email = State(initialValue: prefillEmail)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                } footer: {
                    Text("Enter your email address and we'll send you a link to reset your password.")
                }

                Section {
                    Button {
                        Task {
                            isSending = true
                            _ = await authManager.forgotPassword(email: email)
                            showSuccess = true
                            isSending = false
                        }
                    } label: {
                        HStack {
                            Spacer()
                            if isSending {
                                ProgressView()
                            } else {
                                Text("Send Reset Link")
                            }
                            Spacer()
                        }
                    }
                    .disabled(email.isEmpty || !email.contains("@") || isSending)
                }
            }
            .navigationTitle("Forgot Password")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .alert("Email Sent", isPresented: $showSuccess) {
                Button("OK") {
                    dismiss()
                }
            } message: {
                Text("If an account with this email exists, you will receive a password reset link shortly.")
            }
        }
    }
}

#Preview {
    LoginView()
        .environment(AuthManager())
}
