import SwiftUI

struct BankImportCategorizeView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @Bindable var viewModel: BankImportViewModel

    @State private var currentIndex = 0

    private var itemsToReview: [ExtractedTransaction] {
        viewModel.needsAttentionTransactions
    }

    private var currentTransaction: ExtractedTransaction? {
        guard currentIndex < itemsToReview.count else { return nil }
        return itemsToReview[currentIndex]
    }

    var body: some View {
        NavigationStack {
            ZStack {
                backgroundColor.ignoresSafeArea()

                if itemsToReview.isEmpty {
                    // All done!
                    AllReviewedView(onDone: { dismiss() })
                } else if let transaction = currentTransaction {
                    VStack(spacing: 0) {
                        // Progress
                        ProgressHeader(
                            current: currentIndex + 1,
                            total: itemsToReview.count
                        )

                        ScrollView {
                            VStack(spacing: Spacing.lg) {
                                // Transaction card
                                TransactionReviewCard(
                                    transaction: transaction,
                                    expenseTypes: viewModel.expenseTypes,
                                    categories: viewModel.categories,
                                    onUpdate: { update in
                                        Task {
                                            if await viewModel.updateTransaction(transaction, update: update) {
                                                HapticManager.light()
                                            }
                                        }
                                    }
                                )

                                // Original text (for OCR issues)
                                if let rawText = transaction.rawText, !rawText.isEmpty {
                                    RawTextCard(text: rawText)
                                }
                            }
                            .padding(Spacing.md)
                        }

                        // Navigation buttons
                        ReviewNavigationBar(
                            canGoBack: currentIndex > 0,
                            canGoForward: currentIndex < itemsToReview.count - 1,
                            isLast: currentIndex == itemsToReview.count - 1,
                            onBack: { currentIndex -= 1 },
                            onNext: {
                                if currentIndex < itemsToReview.count - 1 {
                                    currentIndex += 1
                                } else {
                                    dismiss()
                                }
                            },
                            onSkip: {
                                Task {
                                    let update = UpdateExtractedTransactionRequest(isSelected: false)
                                    if await viewModel.updateTransaction(transaction, update: update) {
                                        // Move to next or dismiss if at end
                                        if currentIndex >= itemsToReview.count - 1 {
                                            // Reload to get updated list
                                            if itemsToReview.count <= 1 {
                                                dismiss()
                                            }
                                        }
                                    }
                                }
                            }
                        )
                    }
                }
            }
            .navigationTitle("Review Items")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(.brandPrimary)
                }
            }
        }
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

// MARK: - Progress Header

struct ProgressHeader: View {
    let current: Int
    let total: Int

    var body: some View {
        VStack(spacing: Spacing.xs) {
            ProgressView(value: Double(current), total: Double(total))
                .tint(.terracotta500)

            Text("\(current) of \(total)")
                .font(.labelSmall)
                .foregroundColor(.textTertiary)
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
        .background(Color.backgroundSecondary)
    }
}

// MARK: - All Reviewed View

struct AllReviewedView: View {
    let onDone: () -> Void

    var body: some View {
        VStack(spacing: Spacing.lg) {
            ZStack {
                Circle()
                    .fill(Color.sage100)
                    .frame(width: 120, height: 120)

                CatIcon(name: .happy, size: .xl, color: .sage500)
            }

            Text("All Done!")
                .font(.displayMedium)
                .foregroundColor(.textPrimary)

            Text("All items have been reviewed.\nYou're ready to import.")
                .font(.bodyMedium)
                .foregroundColor(.textSecondary)
                .multilineTextAlignment(.center)

            PrimaryButton(
                title: "Continue",
                icon: .sparkle,
                action: onDone
            )
            .padding(.horizontal, Spacing.xl)
        }
        .padding(Spacing.xl)
    }
}

// MARK: - Transaction Review Card

struct TransactionReviewCard: View {
    let transaction: ExtractedTransaction
    let expenseTypes: [ExpenseType]
    let categories: [TransactionCategory]
    let onUpdate: (UpdateExtractedTransactionRequest) -> Void

    @Environment(\.colorScheme) private var colorScheme
    @State private var merchant: String = ""
    @State private var amount: String = ""
    @State private var selectedDate: Date = Date()
    @State private var selectedExpenseTypeId: Int?
    @State private var selectedSplitCategory: String = "SHARED"

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            // Flags
            if !transaction.flags.isEmpty {
                HStack(spacing: Spacing.xs) {
                    ForEach(transaction.flags.filter { $0.value }.map { $0.key }, id: \.self) { flag in
                        ReviewFlagBadge(flags: [flag: true])
                    }
                }
            }

            // Merchant
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text("Merchant")
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                TextField("Merchant name", text: $merchant)
                    .font(.bodyLarge)
                    .foregroundColor(textColor)
                    .padding(Spacing.sm)
                    .background(Color.backgroundInput)
                    .cornerRadius(CornerRadius.medium)
                    .onChange(of: merchant) { _, newValue in
                        if newValue != transaction.merchant {
                            onUpdate(UpdateExtractedTransactionRequest(merchant: newValue))
                        }
                    }
            }

            // Amount
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text("Amount")
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                HStack {
                    Text(transaction.currency)
                        .font(.labelMedium)
                        .foregroundColor(.textSecondary)
                        .padding(.horizontal, Spacing.sm)
                        .padding(.vertical, Spacing.xs)
                        .background(Color.terracotta100)
                        .cornerRadius(CornerRadius.small)

                    TextField("0.00", text: $amount)
                        .keyboardType(.decimalPad)
                        .font(.amountMedium)
                        .foregroundColor(textColor)
                        .onChange(of: amount) { _, newValue in
                            if let value = Double(newValue), value != transaction.amount {
                                onUpdate(UpdateExtractedTransactionRequest(amount: value))
                            }
                        }
                }
                .padding(Spacing.sm)
                .background(Color.backgroundInput)
                .cornerRadius(CornerRadius.medium)
            }

            // Date
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text("Date")
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                DatePicker("", selection: $selectedDate, displayedComponents: .date)
                    .labelsHidden()
                    .tint(.brandPrimary)
                    .onChange(of: selectedDate) { _, newValue in
                        let formatter = DateFormatter()
                        formatter.dateFormat = "yyyy-MM-dd"
                        let dateString = formatter.string(from: newValue)
                        if dateString != transaction.date {
                            onUpdate(UpdateExtractedTransactionRequest(date: dateString))
                        }
                    }
            }

            Divider()

            // Expense Type
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text("Expense Type")
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                Menu {
                    Button {
                        selectedExpenseTypeId = nil
                        onUpdate(UpdateExtractedTransactionRequest(expenseTypeId: nil))
                    } label: {
                        HStack {
                            Text("None")
                            if selectedExpenseTypeId == nil {
                                Image(systemName: "checkmark")
                            }
                        }
                    }

                    ForEach(expenseTypes) { type in
                        Button {
                            selectedExpenseTypeId = type.id
                            onUpdate(UpdateExtractedTransactionRequest(expenseTypeId: type.id))
                        } label: {
                            HStack {
                                Text(type.name)
                                if selectedExpenseTypeId == type.id {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                    }
                } label: {
                    HStack {
                        Text(selectedExpenseTypeName ?? "Select...")
                            .font(.bodyLarge)
                            .foregroundColor(selectedExpenseTypeId == nil ? .textTertiary : textColor)

                        Spacer()

                        Image(systemName: "chevron.up.chevron.down")
                            .font(.system(size: 12))
                            .foregroundColor(.warm400)
                    }
                    .padding(Spacing.sm)
                    .background(Color.backgroundInput)
                    .cornerRadius(CornerRadius.medium)
                }
            }

            // Split Category
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text("Split Category")
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                Menu {
                    ForEach(categories) { category in
                        Button {
                            selectedSplitCategory = category.code
                            onUpdate(UpdateExtractedTransactionRequest(splitCategory: category.code))
                        } label: {
                            HStack {
                                Text(category.name)
                                if selectedSplitCategory == category.code {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                    }
                } label: {
                    HStack {
                        Text(selectedCategoryName)
                            .font(.bodyLarge)
                            .foregroundColor(textColor)

                        Spacer()

                        Image(systemName: "chevron.up.chevron.down")
                            .font(.system(size: 12))
                            .foregroundColor(.warm400)
                    }
                    .padding(Spacing.sm)
                    .background(Color.backgroundInput)
                    .cornerRadius(CornerRadius.medium)
                }
            }
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
        .onAppear {
            merchant = transaction.merchant
            amount = String(format: "%.2f", transaction.amount)
            selectedExpenseTypeId = transaction.expenseTypeId
            selectedSplitCategory = transaction.splitCategory

            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            if let date = formatter.date(from: transaction.date) {
                selectedDate = date
            }
        }
    }

    private var selectedExpenseTypeName: String? {
        guard let id = selectedExpenseTypeId else { return nil }
        return expenseTypes.first(where: { $0.id == id })?.name
    }

    private var selectedCategoryName: String {
        categories.first(where: { $0.code == selectedSplitCategory })?.name ?? selectedSplitCategory
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundCard
    }
}

// MARK: - Raw Text Card

struct RawTextCard: View {
    let text: String
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                CatIcon(name: .pencil, size: .sm, color: .textTertiary)
                Text("Original Text")
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)
            }

            Text(text)
                .font(.bodySmall)
                .foregroundColor(.textSecondary)
                .padding(Spacing.sm)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.warm100)
                .cornerRadius(CornerRadius.medium)
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundCard
    }
}

// MARK: - Navigation Bar

struct ReviewNavigationBar: View {
    let canGoBack: Bool
    let canGoForward: Bool
    let isLast: Bool
    let onBack: () -> Void
    let onNext: () -> Void
    let onSkip: () -> Void

    var body: some View {
        VStack(spacing: Spacing.sm) {
            Divider()

            HStack(spacing: Spacing.md) {
                // Back button
                Button(action: onBack) {
                    HStack(spacing: Spacing.xs) {
                        Image(systemName: "chevron.left")
                        Text("Back")
                    }
                    .font(.labelMedium)
                    .foregroundColor(canGoBack ? .brandPrimary : .textTertiary)
                }
                .disabled(!canGoBack)

                Spacer()

                // Skip button
                Button(action: onSkip) {
                    Text("Skip")
                        .font(.labelMedium)
                        .foregroundColor(.textSecondary)
                }

                // Next button
                Button(action: onNext) {
                    HStack(spacing: Spacing.xs) {
                        Text(isLast ? "Done" : "Next")
                        if !isLast {
                            Image(systemName: "chevron.right")
                        }
                    }
                    .font(.labelLarge)
                    .foregroundColor(.white)
                    .padding(.horizontal, Spacing.lg)
                    .padding(.vertical, Spacing.sm)
                    .background(Color.terracotta500)
                    .cornerRadius(CornerRadius.medium)
                }
            }
            .padding(.horizontal, Spacing.md)
            .padding(.bottom, Spacing.md)
        }
        .background(Color.backgroundCard)
    }
}

// MARK: - Flag Badge

private struct ReviewFlagBadge: View {
    let flags: [String: Bool]

    var body: some View {
        HStack(spacing: Spacing.xxs) {
            Image(systemName: iconName)
                .font(.system(size: 10))

            Text(displayText)
                .font(.labelSmall)
        }
        .foregroundColor(flagColor)
        .padding(.horizontal, Spacing.xs)
        .padding(.vertical, Spacing.xxxs)
        .background(flagColor.opacity(0.15))
        .cornerRadius(CornerRadius.small)
    }

    private var iconName: String {
        if flags["ocr_failure"] == true { return "exclamationmark.triangle" }
        if flags["low_confidence"] == true { return "questionmark.circle" }
        if flags["uncertain_category"] == true { return "tag" }
        if flags["potential_duplicate"] == true { return "doc.on.doc" }
        return "exclamationmark.circle"
    }

    private var displayText: String {
        if flags["ocr_failure"] == true { return "OCR Issue" }
        if flags["low_confidence"] == true { return "Low Confidence" }
        if flags["uncertain_category"] == true { return "Uncategorized" }
        if flags["potential_duplicate"] == true { return "Duplicate?" }
        return "Review"
    }

    private var flagColor: Color {
        if flags["ocr_failure"] == true { return .rose500 }
        if flags["potential_duplicate"] == true { return .amber500 }
        return .amber500
    }
}

#Preview {
    BankImportCategorizeView(viewModel: BankImportViewModel())
}
