import SwiftUI

struct TransactionFilterSheet: View {
    @Bindable var viewModel: TransactionsViewModel
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme

    @State private var dateFrom: Date?
    @State private var dateTo: Date?
    @State private var selectedCategory: TransactionCategory?
    @State private var selectedExpenseType: ExpenseType?
    @State private var selectedPaidBy: HouseholdMember?
    @State private var amountMin: String = ""
    @State private var amountMax: String = ""

    @State private var showDateFromPicker = false
    @State private var showDateToPicker = false

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

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    // Date Range Section
                    VStack(spacing: Spacing.md) {
                        Text("Date Range")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(spacing: 0) {
                            // Date From
                            FilterDateRow(
                                icon: .calendar,
                                label: "From",
                                date: dateFrom,
                                isExpanded: showDateFromPicker,
                                onTap: {
                                    HapticManager.selection()
                                    withAnimation(.spring(response: 0.3)) {
                                        showDateFromPicker.toggle()
                                        if showDateFromPicker { showDateToPicker = false }
                                    }
                                },
                                onClear: {
                                    HapticManager.selection()
                                    dateFrom = nil
                                },
                                onDateChange: { dateFrom = $0 }
                            )

                            if showDateFromPicker {
                                DatePicker(
                                    "From Date",
                                    selection: Binding(
                                        get: { dateFrom ?? Date() },
                                        set: { dateFrom = $0 }
                                    ),
                                    displayedComponents: .date
                                )
                                .datePickerStyle(.graphical)
                                .tint(.brandPrimary)
                                .padding(Spacing.sm)
                            }

                            Divider().background(Color.warm200)

                            // Date To
                            FilterDateRow(
                                icon: .calendar,
                                label: "To",
                                date: dateTo,
                                isExpanded: showDateToPicker,
                                onTap: {
                                    HapticManager.selection()
                                    withAnimation(.spring(response: 0.3)) {
                                        showDateToPicker.toggle()
                                        if showDateToPicker { showDateFromPicker = false }
                                    }
                                },
                                onClear: {
                                    HapticManager.selection()
                                    dateTo = nil
                                },
                                onDateChange: { dateTo = $0 }
                            )

                            if showDateToPicker {
                                DatePicker(
                                    "To Date",
                                    selection: Binding(
                                        get: { dateTo ?? Date() },
                                        set: { dateTo = $0 }
                                    ),
                                    displayedComponents: .date
                                )
                                .datePickerStyle(.graphical)
                                .tint(.brandPrimary)
                                .padding(Spacing.sm)
                            }
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Categories Section
                    VStack(spacing: Spacing.md) {
                        Text("Categories")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(spacing: Spacing.sm) {
                            FilterSelectField(
                                icon: .highfive,
                                label: "Category",
                                value: selectedCategory?.name ?? "Any",
                                isSet: selectedCategory != nil,
                                content: {
                                    Button {
                                        HapticManager.selection()
                                        selectedCategory = nil
                                    } label: {
                                        HStack {
                                            Text("Any")
                                            if selectedCategory == nil {
                                                Image(systemName: "checkmark")
                                            }
                                        }
                                    }
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
                                }
                            )

                            if !viewModel.expenseTypes.isEmpty {
                                Divider().background(Color.warm200)

                                FilterSelectField(
                                    icon: .clipboard,
                                    label: "Expense Type",
                                    value: selectedExpenseType?.name ?? "Any",
                                    isSet: selectedExpenseType != nil,
                                    content: {
                                        Button {
                                            HapticManager.selection()
                                            selectedExpenseType = nil
                                        } label: {
                                            HStack {
                                                Text("Any")
                                                if selectedExpenseType == nil {
                                                    Image(systemName: "checkmark")
                                                }
                                            }
                                        }
                                        ForEach(viewModel.expenseTypes) { expenseType in
                                            Button {
                                                HapticManager.selection()
                                                selectedExpenseType = expenseType
                                            } label: {
                                                HStack {
                                                    Text(expenseType.name)
                                                    if selectedExpenseType?.id == expenseType.id {
                                                        Image(systemName: "checkmark")
                                                    }
                                                }
                                            }
                                        }
                                    }
                                )
                            }
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Paid By Section
                    VStack(spacing: Spacing.md) {
                        Text("Paid By")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        FilterSelectField(
                            icon: .happy,
                            label: "Paid By",
                            value: selectedPaidBy?.displayName ?? "Anyone",
                            isSet: selectedPaidBy != nil,
                            content: {
                                Button {
                                    HapticManager.selection()
                                    selectedPaidBy = nil
                                } label: {
                                    HStack {
                                        Text("Anyone")
                                        if selectedPaidBy == nil {
                                            Image(systemName: "checkmark")
                                        }
                                    }
                                }
                                ForEach(viewModel.members) { member in
                                    Button {
                                        HapticManager.selection()
                                        selectedPaidBy = member
                                    } label: {
                                        HStack {
                                            Text(member.displayName)
                                            if selectedPaidBy?.id == member.id {
                                                Image(systemName: "checkmark")
                                            }
                                        }
                                    }
                                }
                            }
                        )
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Amount Range Section
                    VStack(spacing: Spacing.md) {
                        Text("Amount Range (USD)")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(spacing: Spacing.sm) {
                            FilterTextField(
                                icon: .coins,
                                label: "Minimum",
                                placeholder: "0",
                                text: $amountMin
                            )

                            Divider().background(Color.warm200)

                            FilterTextField(
                                icon: .coins,
                                label: "Maximum",
                                placeholder: "Any",
                                text: $amountMax
                            )
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Clear Filters Button
                    if hasAnyFilter {
                        Button {
                            HapticManager.buttonTap()
                            clearAllFilters()
                        } label: {
                            HStack(spacing: Spacing.sm) {
                                CatIcon(name: .trash, size: .sm, color: .danger)
                                Text("Clear All Filters")
                                    .font(.labelLarge)
                                    .foregroundColor(.danger)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(Spacing.md)
                            .background(Color.rose50)
                            .cornerRadius(CornerRadius.large)
                        }
                    }

                    // Apply Button
                    PrimaryButton(
                        title: "Apply Filters",
                        icon: .sparkle,
                        action: {
                            applyFilters()
                            dismiss()
                        }
                    )
                }
                .padding(Spacing.md)
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle("Filters")
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
            .onAppear {
                loadCurrentFilters()
            }
        }
    }

    private var hasAnyFilter: Bool {
        dateFrom != nil || dateTo != nil || selectedCategory != nil ||
        selectedExpenseType != nil || selectedPaidBy != nil ||
        !amountMin.isEmpty || !amountMax.isEmpty
    }

    private func loadCurrentFilters() {
        dateFrom = viewModel.filters.dateFrom
        dateTo = viewModel.filters.dateTo
        selectedCategory = viewModel.filters.category
        selectedExpenseType = viewModel.filters.expenseType
        selectedPaidBy = viewModel.filters.paidBy
        amountMin = viewModel.filters.amountMin.map { String($0) } ?? ""
        amountMax = viewModel.filters.amountMax.map { String($0) } ?? ""
    }

    private func clearAllFilters() {
        dateFrom = nil
        dateTo = nil
        selectedCategory = nil
        selectedExpenseType = nil
        selectedPaidBy = nil
        amountMin = ""
        amountMax = ""
    }

    private func applyFilters() {
        HapticManager.buttonTap()

        viewModel.filters.dateFrom = dateFrom
        viewModel.filters.dateTo = dateTo
        viewModel.filters.category = selectedCategory
        viewModel.filters.expenseType = selectedExpenseType
        viewModel.filters.paidBy = selectedPaidBy
        viewModel.filters.amountMin = Double(amountMin)
        viewModel.filters.amountMax = Double(amountMax)

        // Enable search mode if any filters are set
        viewModel.isSearchActive = viewModel.hasActiveFilters

        Task {
            await viewModel.fetchTransactions()
        }
    }
}

// MARK: - Filter Date Row

private struct FilterDateRow: View {
    let icon: CatIcon.Name
    let label: String
    let date: Date?
    let isExpanded: Bool
    let onTap: () -> Void
    let onClear: () -> Void
    let onDateChange: (Date) -> Void

    @Environment(\.colorScheme) private var colorScheme

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    var body: some View {
        HStack(spacing: Spacing.sm) {
            CatIcon(name: icon, size: .sm, color: .warm400)

            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(label)
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                Text(date.map { $0.formatted(date: .abbreviated, time: .omitted) } ?? "Any")
                    .font(.bodyLarge)
                    .foregroundColor(date == nil ? .textTertiary : textColor)
            }

            Spacer()

            if date != nil {
                Button {
                    onClear()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.warm400)
                }
                .buttonStyle(.plain)
            }

            Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.warm400)
        }
        .contentShape(Rectangle())
        .onTapGesture {
            onTap()
        }
    }
}

// MARK: - Filter Select Field

private struct FilterSelectField<Content: View>: View {
    let icon: CatIcon.Name
    let label: String
    let value: String
    let isSet: Bool
    @ViewBuilder let content: () -> Content

    @Environment(\.colorScheme) private var colorScheme

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    var body: some View {
        HStack(spacing: Spacing.sm) {
            CatIcon(name: icon, size: .sm, color: .warm400)

            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(label)
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                Menu {
                    content()
                } label: {
                    HStack {
                        Text(value)
                            .font(.bodyLarge)
                            .foregroundColor(isSet ? textColor : .textTertiary)
                        Spacer()
                        Image(systemName: "chevron.up.chevron.down")
                            .font(.system(size: 12))
                            .foregroundColor(.warm400)
                    }
                }
            }
        }
    }
}

// MARK: - Filter Text Field

private struct FilterTextField: View {
    let icon: CatIcon.Name
    let label: String
    let placeholder: String
    @Binding var text: String

    @Environment(\.colorScheme) private var colorScheme

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    var body: some View {
        HStack(spacing: Spacing.sm) {
            CatIcon(name: icon, size: .sm, color: .warm400)

            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(label)
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                TextField(placeholder, text: $text)
                    .keyboardType(.decimalPad)
                    .font(.bodyLarge)
                    .foregroundColor(textColor)
            }
        }
    }
}

#Preview {
    TransactionFilterSheet(viewModel: TransactionsViewModel())
}
