import SwiftUI

// MARK: - Styled Text Field
/// Text input with Lucky Ledger styling.

struct StyledTextField: View {
    let placeholder: String
    @Binding var text: String
    var icon: CatIcon.Name?
    var isSecure: Bool = false
    var keyboardType: UIKeyboardType = .default
    var autocapitalization: TextInputAutocapitalization = .sentences
    var errorMessage: String?

    @FocusState private var isFocused: Bool
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            HStack(spacing: Spacing.sm) {
                if let icon = icon {
                    CatIcon(name: icon, size: .md, color: iconColor)
                }

                Group {
                    if isSecure {
                        SecureField(placeholder, text: $text)
                    } else {
                        TextField(placeholder, text: $text)
                    }
                }
                .font(.bodyLarge)
                .foregroundColor(textColor)
                .keyboardType(keyboardType)
                .textInputAutocapitalization(autocapitalization)
                .focused($isFocused)
            }
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
            .background(backgroundColor)
            .cornerRadius(CornerRadius.large)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.large)
                    .stroke(borderColor, lineWidth: isFocused ? 2 : 1)
            )

            if let errorMessage = errorMessage {
                HStack(spacing: Spacing.xxs) {
                    CatIcon(name: .worried, size: .sm, color: .danger)
                    Text(errorMessage)
                        .font(.labelSmall)
                        .foregroundColor(.danger)
                }
            }
        }
    }

    private var iconColor: Color {
        if errorMessage != nil { return .danger }
        if isFocused { return .brandPrimary }
        return .warm500
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundInputDark : .backgroundInput
    }

    private var borderColor: Color {
        if errorMessage != nil { return .borderError }
        if isFocused { return .borderFocused }
        return colorScheme == .dark ? .borderDefaultDark : .borderDefault
    }
}

// MARK: - Amount Input Field
/// Specialized input for currency amounts.

struct AmountInputField: View {
    @Binding var amount: String
    var currencySymbol: String = "$"
    var placeholder: String = "0.00"

    @FocusState private var isFocused: Bool
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.xs) {
            Text(currencySymbol)
                .font(.amountLarge)
                .foregroundColor(.textSecondary)

            TextField(placeholder, text: $amount)
                .font(.amountLarge)
                .foregroundColor(.textPrimary)
                .keyboardType(.decimalPad)
                .focused($isFocused)
                .multilineTextAlignment(.leading)
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.lg)
        .background(backgroundColor)
        .cornerRadius(CornerRadius.xl)
        .overlay(
            RoundedRectangle(cornerRadius: CornerRadius.xl)
                .stroke(borderColor, lineWidth: isFocused ? 2 : 1)
        )
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundInputDark : .backgroundInput
    }

    private var borderColor: Color {
        isFocused
            ? .borderFocused
            : (colorScheme == .dark ? .borderDefaultDark : .borderDefault)
    }
}

// MARK: - Search Field
/// Search input with icon and clear button.

struct SearchField: View {
    @Binding var text: String
    var placeholder: String = "Search..."

    @FocusState private var isFocused: Bool
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.sm) {
            Image(systemName: "magnifyingglass")
                .foregroundColor(isFocused ? .brandPrimary : .warm400)
                .font(.system(size: 16, weight: .medium))

            TextField(placeholder, text: $text)
                .font(.bodyLarge)
                .foregroundColor(textColor)
                .focused($isFocused)

            if !text.isEmpty {
                Button(action: { text = "" }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.warm400)
                        .font(.system(size: 16))
                }
            }
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
        .background(backgroundColor)
        .cornerRadius(CornerRadius.large)
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }
}

// MARK: - Form Label
/// Styled label for form fields.

struct FormLabel: View {
    let text: String
    var isRequired: Bool = false

    var body: some View {
        HStack(spacing: Spacing.xxxs) {
            Text(text)
                .font(.labelMedium)
                .foregroundColor(.textSecondary)

            if isRequired {
                Text("*")
                    .font(.labelMedium)
                    .foregroundColor(.danger)
            }
        }
    }
}

// MARK: - Form Field
/// Complete form field with label and input.

struct FormField: View {
    let label: String
    var isRequired: Bool = false
    let content: AnyView

    init<Content: View>(
        label: String,
        isRequired: Bool = false,
        @ViewBuilder content: () -> Content
    ) {
        self.label = label
        self.isRequired = isRequired
        self.content = AnyView(content())
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            FormLabel(text: label, isRequired: isRequired)
            content
        }
    }
}

// MARK: - Previews

#Preview("Styled Text Fields") {
    VStack(spacing: 16) {
        StyledTextField(
            placeholder: "Enter merchant name",
            text: .constant(""),
            icon: .pencil
        )

        StyledTextField(
            placeholder: "Email address",
            text: .constant("alice@example.com"),
            icon: .envelope
        )

        StyledTextField(
            placeholder: "Password",
            text: .constant(""),
            icon: .lock,
            isSecure: true
        )

        StyledTextField(
            placeholder: "Invalid input",
            text: .constant("bad data"),
            errorMessage: "Please enter a valid value"
        )
    }
    .padding()
}

#Preview("Amount Input") {
    VStack(spacing: 16) {
        AmountInputField(amount: .constant(""))
        AmountInputField(amount: .constant("125.50"))
    }
    .padding()
}

#Preview("Search Field") {
    VStack(spacing: 16) {
        SearchField(text: .constant(""))
        SearchField(text: .constant("Groceries"))
    }
    .padding()
}

#Preview("Form Field") {
    VStack(spacing: 16) {
        FormField(label: "Merchant", isRequired: true) {
            StyledTextField(
                placeholder: "e.g., Whole Foods",
                text: .constant("")
            )
        }

        FormField(label: "Amount", isRequired: true) {
            AmountInputField(amount: .constant(""))
        }
    }
    .padding()
}
