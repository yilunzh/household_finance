import SwiftUI

// MARK: - Styled Search Bar
/// Full search bar with search and cancel actions.

struct StyledSearchBar: View {
    @Binding var searchText: String
    let onSearch: () -> Void
    let onCancel: () -> Void

    @FocusState private var isFocused: Bool
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.sm) {
            // Search input
            HStack(spacing: Spacing.sm) {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(isFocused ? .brandPrimary : .warm400)
                    .font(.system(size: 16, weight: .medium))

                TextField("Search transactions...", text: $searchText)
                    .font(.bodyLarge)
                    .foregroundColor(textColor)
                    .submitLabel(.search)
                    .focused($isFocused)
                    .onSubmit {
                        HapticManager.buttonTap()
                        onSearch()
                    }

                if !searchText.isEmpty {
                    Button {
                        HapticManager.light()
                        searchText = ""
                        onSearch()
                    } label: {
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

            // Cancel button
            Button {
                HapticManager.buttonTap()
                onCancel()
            } label: {
                Text("Cancel")
                    .font(.labelLarge)
                    .foregroundColor(.brandPrimary)
            }
        }
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }
}

// MARK: - Styled Month Selector
/// Month navigation with previous/next buttons.

struct StyledMonthSelector: View {
    let month: String
    let onPrevious: () -> Void
    let onNext: () -> Void

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack {
            Button(action: onPrevious) {
                Image(systemName: "chevron.left")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundColor(.brandPrimary)
            }
            .frame(width: 44, height: 44)

            Spacer()

            Text(month)
                .font(.displaySmall)
                .foregroundColor(textColor)

            Spacer()

            Button(action: onNext) {
                Image(systemName: "chevron.right")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundColor(.brandPrimary)
            }
            .frame(width: 44, height: 44)
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }
}

// MARK: - Styled Active Filters
/// Shows active filter count with clear button.

struct StyledActiveFilters: View {
    let filterCount: Int
    let onClear: () -> Void

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.sm) {
            CatIcon(name: .gear, size: .sm, color: .brandPrimary)

            Text("\(filterCount) filter\(filterCount == 1 ? "" : "s") active")
                .font(.labelMedium)
                .foregroundColor(.textSecondary)

            Spacer()

            Button {
                HapticManager.buttonTap()
                onClear()
            } label: {
                HStack(spacing: Spacing.xxs) {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .semibold))
                    Text("Clear")
                        .font(.labelMedium)
                }
                .foregroundColor(.brandPrimary)
                .padding(.horizontal, Spacing.sm)
                .padding(.vertical, Spacing.xxs)
                .background(Color.terracotta100)
                .cornerRadius(CornerRadius.medium)
            }
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
        .background(backgroundColor)
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .cream100
    }
}

// MARK: - Styled Transaction Row
/// Transaction row with brand styling.

struct StyledTransactionRow: View {
    let transaction: Transaction

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            // Expense type icon circle
            ZStack {
                Circle()
                    .fill(categoryColor.opacity(0.15))
                    .frame(width: 44, height: 44)

                CatIcon(name: expenseTypeIcon, size: .md, color: categoryColor)
            }

            // Transaction details
            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(transaction.merchant)
                    .font(.labelLarge)
                    .foregroundColor(textColor)
                    .lineLimit(1)

                HStack(spacing: Spacing.xs) {
                    Text(transaction.expenseTypeName ?? "Other")
                        .font(.labelSmall)
                        .foregroundColor(.textTertiary)

                    Text(formattedDate)
                        .font(.labelSmall)
                        .foregroundColor(.textTertiary)
                }
            }

            Spacer()

            // Amount and paid by
            VStack(alignment: .trailing, spacing: Spacing.xxxs) {
                HStack(spacing: Spacing.xxs) {
                    if transaction.receiptUrl != nil {
                        Image(systemName: "paperclip")
                            .font(.system(size: 12))
                            .foregroundColor(.warm400)
                    }

                    Text(formattedAmount)
                        .font(.amountMedium)
                        .foregroundColor(amountColor)
                }

                if let paidByName = transaction.paidByName {
                    Text("Paid by \(paidByName)")
                        .font(.labelSmall)
                        .foregroundColor(.textSecondary)
                }
            }
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
    }

    // MARK: - Computed Properties

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    private var categoryColor: Color {
        switch transaction.category {
        case "PERSONAL_ME", "PERSONAL_WIFE":
            return .sage500
        case "SHARED":
            return .brandPrimary
        default:
            return .warm500
        }
    }

    private var categoryIcon: CatIcon.Name {
        switch transaction.category {
        case "PERSONAL_ME":
            return .happy
        case "PERSONAL_WIFE":
            return .wave
        case "SHARED":
            return .highfive
        default:
            return .coins
        }
    }

    /// Maps expense types to semantic cat icons for visual differentiation
    private var expenseTypeIcon: CatIcon.Name {
        guard let expenseType = transaction.expenseTypeName?.lowercased() else {
            return categoryIcon
        }
        switch expenseType {
        case let t where t.contains("grocer"):
            return .coins
        case let t where t.contains("food") || t.contains("drink") || t.contains("dining") || t.contains("restaurant"):
            return .happy
        case let t where t.contains("travel") || t.contains("vacation"):
            return .rocket
        case let t where t.contains("entertainment") || t.contains("fun"):
            return .celebrate
        case let t where t.contains("gas") || t.contains("fuel"):
            return .rocket
        case let t where t.contains("bill") || t.contains("utilit"):
            return .lightbulb
        case let t where t.contains("health") || t.contains("medical"):
            return .heart
        case let t where t.contains("home") || t.contains("house"):
            return .house
        default:
            return categoryIcon
        }
    }

    private var amountColor: Color {
        switch transaction.category {
        case "PERSONAL_ME", "PERSONAL_WIFE":
            return .sage600
        default:
            return colorScheme == .dark ? .textPrimaryDark : .textPrimary
        }
    }

    private var formattedAmount: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = transaction.currency
        return formatter.string(from: NSNumber(value: transaction.amount)) ?? "$\(transaction.amount)"
    }

    private var formattedDate: String {
        let inputFormatter = DateFormatter()
        inputFormatter.dateFormat = "yyyy-MM-dd"

        let outputFormatter = DateFormatter()
        outputFormatter.dateFormat = "MMM d"

        if let date = inputFormatter.date(from: transaction.date) {
            return outputFormatter.string(from: date)
        }
        return transaction.date
    }
}

// MARK: - Previews

#Preview("Search Bar") {
    VStack(spacing: 16) {
        StyledSearchBar(
            searchText: .constant(""),
            onSearch: {},
            onCancel: {}
        )
        StyledSearchBar(
            searchText: .constant("Groceries"),
            onSearch: {},
            onCancel: {}
        )
    }
    .padding()
}

#Preview("Month Selector") {
    StyledMonthSelector(
        month: "January 2024",
        onPrevious: {},
        onNext: {}
    )
}

#Preview("Active Filters") {
    VStack(spacing: 16) {
        StyledActiveFilters(filterCount: 1, onClear: {})
        StyledActiveFilters(filterCount: 3, onClear: {})
    }
}
