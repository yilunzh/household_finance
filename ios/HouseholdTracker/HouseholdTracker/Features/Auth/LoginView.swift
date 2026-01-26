import SwiftUI

struct LoginView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.colorScheme) private var colorScheme

    @State private var email = ""
    @State private var password = ""
    @State private var isRegistering = false
    @State private var displayName = ""
    @State private var showingForgotPassword = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.xxl) {
                    // Logo and Title
                    VStack(spacing: Spacing.lg) {
                        // Kawaii Cat Logo - Hero size for login screen
                        CatIcon(name: .happy, size: .hero, color: .terracotta500)
                            .modifier(GentleBounceModifier())

                        VStack(spacing: Spacing.xs) {
                            Text("Lucky Ledger")
                                .font(.system(size: 36, weight: .bold, design: .rounded))
                                .foregroundColor(colorScheme == .dark ? .textPrimaryDark : .textPrimary)

                            Text("Track household expenses together")
                                .font(.bodyMedium)
                                .foregroundColor(colorScheme == .dark ? .textSecondaryDark : .textSecondary)
                        }
                    }
                    .padding(.top, Spacing.xxl)

                    // Form Card
                    CardContainer {
                        VStack(spacing: Spacing.md) {
                            if isRegistering {
                                FormField(label: "Display Name") {
                                    StyledTextField(
                                        placeholder: "Your name",
                                        text: $displayName,
                                        icon: .silhouette,
                                        autocapitalization: .words
                                    )
                                }
                            }

                            FormField(label: "Email", isRequired: true) {
                                StyledTextField(
                                    placeholder: "your@email.com",
                                    text: $email,
                                    icon: .envelope,
                                    keyboardType: .emailAddress,
                                    autocapitalization: .never,
                                    accessibilityId: "email-field"
                                )
                            }

                            FormField(label: "Password", isRequired: true) {
                                StyledTextField(
                                    placeholder: isRegistering ? "Create a password" : "Your password",
                                    text: $password,
                                    icon: .lock,
                                    isSecure: true,
                                    errorMessage: passwordError,
                                    accessibilityId: "password-field"
                                )
                            }

                            if !isRegistering {
                                HStack {
                                    Spacer()
                                    Button {
                                        showingForgotPassword = true
                                    } label: {
                                        Text("Forgot Password?")
                                            .font(.labelSmall)
                                            .foregroundColor(.textLink)
                                    }
                                }
                            }

                            if let error = authManager.error {
                                HStack(spacing: Spacing.xs) {
                                    CatIcon(name: .worried, size: .sm, color: .danger)
                                    Text(error)
                                        .font(.labelSmall)
                                        .foregroundColor(.danger)
                                }
                                .padding(Spacing.sm)
                                .frame(maxWidth: .infinity)
                                .background(Color.dangerLight)
                                .cornerRadius(CornerRadius.medium)
                            }

                            PrimaryButton(
                                title: isRegistering ? "Create Account" : "Log In",
                                icon: isRegistering ? .sparkle : nil,
                                action: {
                                    Task {
                                        await performAuth()
                                    }
                                },
                                isLoading: authManager.isLoading,
                                isDisabled: !isFormValid
                            )
                            .padding(.top, Spacing.xs)

                            // Helper text when form is invalid
                            if !isFormValid && !authManager.isLoading {
                                Text(formValidationMessage)
                                    .font(.labelSmall)
                                    .foregroundColor(.textTertiary)
                                    .padding(.top, Spacing.xxs)
                            }
                        }
                    }
                    .padding(.horizontal, Spacing.lg)

                    // Toggle between login and register
                    Button {
                        withAnimation(.spring(response: 0.3)) {
                            isRegistering.toggle()
                            authManager.clearError()
                        }
                    } label: {
                        HStack(spacing: Spacing.xxs) {
                            Text(isRegistering ? "Already have an account?" : "Don't have an account?")
                                .foregroundColor(.textSecondary)
                            Text(isRegistering ? "Log in" : "Sign up")
                                .fontWeight(.semibold)
                                .foregroundColor(.textLink)
                        }
                        .font(.bodyMedium)
                    }

                    Spacer(minLength: Spacing.xxxl)
                }
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationBarHidden(true)
            .sheet(isPresented: $showingForgotPassword) {
                ForgotPasswordSheet(prefillEmail: email)
            }
        }
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }

    private var isFormValid: Bool {
        !email.isEmpty && !password.isEmpty && password.count >= 6 &&
        (!isRegistering || !displayName.isEmpty || displayName.isEmpty) // Name is optional
    }

    private var formValidationMessage: String {
        if email.isEmpty {
            return "Enter your email address"
        }
        if password.isEmpty {
            return "Enter your password"
        }
        if password.count < 6 {
            return "Password must be at least 6 characters"
        }
        return ""
    }

    private var passwordError: String? {
        if !password.isEmpty && password.count < 6 {
            return "Password must be at least 6 characters"
        }
        return nil
    }

    private func performAuth() async {
        HapticManager.buttonTap()
        if isRegistering {
            let success = await authManager.register(
                email: email,
                password: password,
                displayName: displayName.isEmpty ? nil : displayName
            )
            if success {
                HapticManager.success()
            } else {
                HapticManager.error()
            }
        } else {
            let success = await authManager.login(email: email, password: password)
            if success {
                HapticManager.success()
            } else {
                HapticManager.error()
            }
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
