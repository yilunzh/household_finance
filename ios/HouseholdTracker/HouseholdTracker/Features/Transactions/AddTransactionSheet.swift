import SwiftUI

struct AddTransactionSheet: View {
    @Bindable var viewModel: TransactionsViewModel
    @Environment(\.dismiss) private var dismiss
    @Environment(AuthManager.self) private var authManager
    @Environment(\.colorScheme) private var colorScheme

    @State private var merchant = ""
    @State private var amount = ""
    @State private var selectedDate = Date()
    @State private var selectedCategory: TransactionCategory?
    @State private var selectedExpenseType: ExpenseType?
    @State private var selectedPaidBy: HouseholdMember?
    @State private var notes = ""
    @State private var currency = "USD"

    // Auto-categorization state
    @State private var isAutoDetected = false
    @State private var autoCategorizeTask: Task<Void, Never>?

    private let currencies = ["USD", "CAD"]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    // Amount Card - Featured at top
                    VStack(spacing: Spacing.md) {
                        Text("Amount")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        HStack(spacing: Spacing.md) {
                            // Currency selector
                            Menu {
                                ForEach(currencies, id: \.self) { curr in
                                    Button {
                                        HapticManager.selection()
                                        currency = curr
                                    } label: {
                                        HStack {
                                            Text(curr)
                                            if currency == curr {
                                                Image(systemName: "checkmark")
                                            }
                                        }
                                    }
                                }
                            } label: {
                                HStack(spacing: Spacing.xxs) {
                                    Text(currency)
                                        .font(.labelLarge)
                                        .foregroundColor(.brandPrimary)
                                    Image(systemName: "chevron.down")
                                        .font(.system(size: 12, weight: .semibold))
                                        .foregroundColor(.brandPrimary)
                                }
                                .padding(.horizontal, Spacing.sm)
                                .padding(.vertical, Spacing.xs)
                                .background(Color.terracotta100)
                                .cornerRadius(CornerRadius.medium)
                            }

                            // Amount input
                            TextField("0.00", text: $amount)
                                .keyboardType(.decimalPad)
                                .font(.amountLarge)
                                .foregroundColor(textColor)
                                .multilineTextAlignment(.trailing)
                                .onChange(of: amount) { _, newValue in
                                    let sanitized = sanitizeAmountInput(newValue)
                                    if sanitized != newValue {
                                        amount = sanitized
                                    }
                                }
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Details Card
                    VStack(spacing: Spacing.md) {
                        Text("Details")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(spacing: Spacing.sm) {
                            // Merchant
                            StyledFormField(
                                icon: .ledger,
                                label: "Merchant",
                                content: {
                                    TextField("Where did you spend?", text: $merchant)
                                        .font(.bodyLarge)
                                        .foregroundColor(textColor)
                                        .onChange(of: merchant) { _, newValue in
                                            triggerAutoCategorize(merchant: newValue)
                                        }
                                }
                            )

                            Divider().background(Color.warm200)

                            // Date
                            StyledFormField(
                                icon: .calendar,
                                label: "Date",
                                content: {
                                    HStack {
                                        DatePicker("", selection: $selectedDate, displayedComponents: .date)
                                            .labelsHidden()
                                            .tint(.brandPrimary)
                                        Spacer()
                                    }
                                }
                            )

                            Divider().background(Color.warm200)

                            // Category
                            StyledFormField(
                                icon: .highfive,
                                label: "Category",
                                content: {
                                    Menu {
                                        ForEach(viewModel.categories) { category in
                                            Button {
                                                HapticManager.selection()
                                                selectedCategory = category
                                            } label: {
                                                HStack {
                                                    Text(category.name)
                                                    if selectedCategory?.id == category.id {
                                                        Image(systemName: "checkmark")
                                                    }
                                                }
                                            }
                                        }
                                    } label: {
                                        HStack {
                                            Text(selectedCategory?.name ?? "Select...")
                                                .font(.bodyLarge)
                                                .foregroundColor(selectedCategory == nil ? .textTertiary : textColor)
                                            Spacer()
                                            Image(systemName: "chevron.up.chevron.down")
                                                .font(.system(size: 12))
                                                .foregroundColor(.warm400)
                                        }
                                    }
                                }
                            )

                            // Expense Type (if available)
                            if !viewModel.expenseTypes.isEmpty {
                                Divider().background(Color.warm200)

                                StyledFormField(
                                    icon: .clipboard,
                                    label: "Expense Type",
                                    content: {
                                        Menu {
                                            Button {
                                                HapticManager.selection()
                                                selectedExpenseType = nil
                                                isAutoDetected = false
                                                selectedCategory = viewModel.categories.first { $0.code == "SHARED" }
                                            } label: {
                                                HStack {
                                                    Text("None")
                                                    if selectedExpenseType == nil {
                                                        Image(systemName: "checkmark")
                                                    }
                                                }
                                            }
                                            ForEach(viewModel.expenseTypes) { expenseType in
                                                Button {
                                                    HapticManager.selection()
                                                    selectedExpenseType = expenseType
                                                    isAutoDetected = false
                                                    Task { await updateCategoryFromServer(expenseTypeId: expenseType.id) }
                                                } label: {
                                                    HStack {
                                                        Text(expenseType.name)
                                                        if selectedExpenseType?.id == expenseType.id {
                                                            Image(systemName: "checkmark")
                                                        }
                                                    }
                                                }
                                            }
                                        } label: {
                                            HStack {
                                                Text(selectedExpenseType?.name ?? "None")
                                                    .font(.bodyLarge)
                                                    .foregroundColor(selectedExpenseType == nil ? .textTertiary : textColor)

                                                if isAutoDetected && selectedExpenseType != nil {
                                                    Text("Auto")
                                                        .font(.labelSmall)
                                                        .foregroundColor(.success)
                                                        .padding(.horizontal, Spacing.xs)
                                                        .padding(.vertical, Spacing.xxxs)
                                                        .background(Color.successLight)
                                                        .cornerRadius(CornerRadius.small)
                                                }

                                                Spacer()
                                                Image(systemName: "chevron.up.chevron.down")
                                                    .font(.system(size: 12))
                                                    .foregroundColor(.warm400)
                                            }
                                        }
                                    }
                                )
                            }

                            Divider().background(Color.warm200)

                            // Paid By
                            StyledFormField(
                                icon: .happy,
                                label: "Paid By",
                                content: {
                                    Menu {
                                        ForEach(viewModel.members) { member in
                                            Button {
                                                HapticManager.selection()
                                                selectedPaidBy = member
                                                if let et = selectedExpenseType {
                                                    Task { await updateCategoryFromServer(expenseTypeId: et.id, paidByOverride: member) }
                                                }
                                            } label: {
                                                HStack {
                                                    Text(member.displayName)
                                                    if selectedPaidBy?.id == member.id {
                                                        Image(systemName: "checkmark")
                                                    }
                                                }
                                            }
                                        }
                                    } label: {
                                        HStack {
                                            Text(selectedPaidBy?.displayName ?? "Select...")
                                                .font(.bodyLarge)
                                                .foregroundColor(selectedPaidBy == nil ? .textTertiary : textColor)
                                            Spacer()
                                            Image(systemName: "chevron.up.chevron.down")
                                                .font(.system(size: 12))
                                                .foregroundColor(.warm400)
                                        }
                                    }
                                }
                            )
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Notes Card
                    VStack(spacing: Spacing.md) {
                        Text("Notes")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        HStack(alignment: .top, spacing: Spacing.sm) {
                            CatIcon(name: .pencil, size: .sm, color: .warm400)
                                .padding(.top, Spacing.xxs)

                            TextField("Add notes (optional)", text: $notes, axis: .vertical)
                                .font(.bodyLarge)
                                .foregroundColor(textColor)
                                .lineLimit(3...6)
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Error Display
                    if let error = viewModel.error {
                        HStack(spacing: Spacing.sm) {
                            CatIcon(name: .worried, size: .sm, color: .danger)
                            Text(error)
                                .font(.labelMedium)
                                .foregroundColor(.danger)
                        }
                        .padding(Spacing.md)
                        .frame(maxWidth: .infinity)
                        .background(Color.rose50)
                        .cornerRadius(CornerRadius.medium)
                    }

                    // Save Button
                    PrimaryButton(
                        title: "Add Transaction",
                        icon: .plus,
                        action: {
                            Task {
                                await saveTransaction()
                            }
                        },
                        isLoading: viewModel.isLoading,
                        isDisabled: !isFormValid
                    )
                }
                .padding(Spacing.md)
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle("Add Transaction")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button {
                        HapticManager.buttonTap()
                        dismiss()
                    } label: {
                        Text("Cancel")
                            .foregroundColor(.brandPrimary)
                    }
                }
            }
            .interactiveDismissDisabled(viewModel.isLoading)
        }
        .onAppear {
            // Default to current user as paid by
            if let currentUserId = authManager.currentUser?.id {
                selectedPaidBy = viewModel.members.first { $0.userId == currentUserId }
            }

            // Default category to SHARED
            selectedCategory = viewModel.categories.first { $0.code == "SHARED" }
        }
        .onChange(of: viewModel.members) { _, newMembers in
            // Members may load after sheet appears — set default paid-by when they arrive
            if selectedPaidBy == nil, let currentUserId = authManager.currentUser?.id {
                selectedPaidBy = newMembers.first { $0.userId == currentUserId }
                // If expense type was already auto-detected, re-fetch category with paid-by
                if let et = selectedExpenseType, isAutoDetected {
                    Task { await updateCategoryFromServer(expenseTypeId: et.id) }
                }
            }
        }
        .onDisappear {
            autoCategorizeTask?.cancel()
        }
    }

    // MARK: - Computed Properties

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }

    private var isFormValid: Bool {
        guard let amountValue = Double(amount), amountValue > 0 else { return false }
        return !merchant.trimmingCharacters(in: .whitespaces).isEmpty
            && selectedCategory != nil
            && selectedPaidBy != nil
    }

    /// Sanitizes amount input to allow only valid currency format
    private func sanitizeAmountInput(_ input: String) -> String {
        // Filter to only digits and decimal point
        var sanitized = input.filter { $0.isNumber || $0 == "." }

        // Ensure only one decimal point
        if let firstDecimal = sanitized.firstIndex(of: ".") {
            let afterDecimal = sanitized.index(after: firstDecimal)
            if afterDecimal < sanitized.endIndex {
                sanitized = String(sanitized[..<afterDecimal]) +
                            sanitized[afterDecimal...].filter { $0 != "." }
            }
        }

        // Limit to 2 decimal places
        if let decimalIndex = sanitized.firstIndex(of: ".") {
            let afterDecimal = sanitized.index(after: decimalIndex)
            if afterDecimal < sanitized.endIndex {
                let decimalPart = sanitized[afterDecimal...]
                if decimalPart.count > 2 {
                    let endIndex = sanitized.index(decimalIndex, offsetBy: 3)
                    sanitized = String(sanitized[..<endIndex])
                }
            }
        }

        // Remove leading zeros (but keep "0" or "0.xx")
        while sanitized.hasPrefix("0") && sanitized.count > 1 && !sanitized.hasPrefix("0.") {
            sanitized.removeFirst()
        }

        return sanitized
    }

    // MARK: - Auto-Categorization

    private func triggerAutoCategorize(merchant: String) {
        autoCategorizeTask?.cancel()

        // Don't override manual selection
        if selectedExpenseType != nil && !isAutoDetected {
            return
        }

        autoCategorizeTask = Task {
            try? await Task.sleep(nanoseconds: 500_000_000)  // 500ms debounce
            guard !Task.isCancelled else { return }

            if let response = await viewModel.fetchAutoCategorySuggestion(
                merchant: merchant,
                paidByUserId: selectedPaidBy?.userId
            ) {
                guard !Task.isCancelled else { return }
                await MainActor.run {
                    if selectedExpenseType == nil || isAutoDetected {
                        selectedExpenseType = response.expenseType
                        isAutoDetected = true
                        HapticManager.light()

                        // Set category from response
                        if let categoryCode = response.category {
                            selectedCategory = viewModel.categories.first { $0.code == categoryCode }
                        }

                        // If paid_by is now available and we got an expense type,
                        // re-fetch to get budget-rule-derived category
                        if let paidBy = selectedPaidBy, let et = response.expenseType {
                            Task { await updateCategoryFromServer(expenseTypeId: et.id, paidByOverride: paidBy) }
                        }
                    }
                }
            } else {
                print("[AutoCat] No suggestion returned")
            }
        }
    }

    // MARK: - Budget Category Lookup

    private func updateCategoryFromServer(expenseTypeId: Int, paidByOverride: HouseholdMember? = nil) async {
        // paidByUserId is optional — server defaults to JWT user when nil
        let paidByUserId = (paidByOverride ?? selectedPaidBy)?.userId
        if let response = await viewModel.fetchAutoCategorySuggestion(
            expenseTypeId: expenseTypeId,
            paidByUserId: paidByUserId
        ), let categoryCode = response.category {
            await MainActor.run {
                selectedCategory = viewModel.categories.first { $0.code == categoryCode }
            }
        }
    }

    // MARK: - Actions

    private func saveTransaction() async {
        guard let amountValue = Double(amount),
              let category = selectedCategory,
              let paidBy = selectedPaidBy else {
            return
        }

        HapticManager.buttonTap()

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let dateString = formatter.string(from: selectedDate)

        let request = CreateTransactionRequest(
            amount: amountValue,
            currency: currency,
            merchant: merchant.trimmingCharacters(in: .whitespaces),
            category: category.code,
            date: dateString,
            paidBy: paidBy.userId,
            expenseTypeId: selectedExpenseType?.id,
            notes: notes.isEmpty ? nil : notes
        )

        if await viewModel.createTransaction(request) {
            HapticManager.success()
            dismiss()
        } else {
            HapticManager.error()
        }
    }
}

// MARK: - Styled Form Field

struct StyledFormField<Content: View>: View {
    let icon: CatIcon.Name
    let label: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        HStack(spacing: Spacing.sm) {
            CatIcon(name: icon, size: .sm, color: .warm400)

            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(label)
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                content()
            }
        }
    }
}

#Preview {
    AddTransactionSheet(viewModel: TransactionsViewModel())
        .environment(AuthManager())
}
