import SwiftUI

struct BudgetRuleEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @Bindable var viewModel: BudgetViewModel
    let rule: BudgetRule?

    @State private var selectedGiverId: Int?
    @State private var selectedReceiverId: Int?
    @State private var monthlyAmount: String = ""
    @State private var selectedExpenseTypeIds: Set<Int> = []

    private var isEditing: Bool { rule != nil }

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
                    // Transfer Section
                    VStack(spacing: Spacing.md) {
                        Text("Transfer")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(spacing: Spacing.sm) {
                            if !isEditing {
                                // Editable member pickers
                                BudgetFormField(
                                    icon: .happy,
                                    label: "From",
                                    content: {
                                        Menu {
                                            Button {
                                                HapticManager.selection()
                                                selectedGiverId = nil
                                            } label: {
                                                HStack {
                                                    Text("Select member")
                                                    if selectedGiverId == nil {
                                                        Image(systemName: "checkmark")
                                                    }
                                                }
                                            }
                                            ForEach(viewModel.members) { member in
                                                Button {
                                                    HapticManager.selection()
                                                    selectedGiverId = member.userId
                                                } label: {
                                                    HStack {
                                                        Text(member.displayName)
                                                        if selectedGiverId == member.userId {
                                                            Image(systemName: "checkmark")
                                                        }
                                                    }
                                                }
                                            }
                                        } label: {
                                            HStack {
                                                Text(giverName)
                                                    .font(.bodyLarge)
                                                    .foregroundColor(selectedGiverId == nil ? .textTertiary : textColor)
                                                Spacer()
                                                Image(systemName: "chevron.up.chevron.down")
                                                    .font(.system(size: 12))
                                                    .foregroundColor(.warm400)
                                            }
                                        }
                                    }
                                )

                                Divider().background(Color.warm200)

                                BudgetFormField(
                                    icon: .highfive,
                                    label: "To",
                                    content: {
                                        Menu {
                                            Button {
                                                HapticManager.selection()
                                                selectedReceiverId = nil
                                            } label: {
                                                HStack {
                                                    Text("Select member")
                                                    if selectedReceiverId == nil {
                                                        Image(systemName: "checkmark")
                                                    }
                                                }
                                            }
                                            ForEach(viewModel.members) { member in
                                                Button {
                                                    HapticManager.selection()
                                                    selectedReceiverId = member.userId
                                                } label: {
                                                    HStack {
                                                        Text(member.displayName)
                                                        if selectedReceiverId == member.userId {
                                                            Image(systemName: "checkmark")
                                                        }
                                                    }
                                                }
                                            }
                                        } label: {
                                            HStack {
                                                Text(receiverName)
                                                    .font(.bodyLarge)
                                                    .foregroundColor(selectedReceiverId == nil ? .textTertiary : textColor)
                                                Spacer()
                                                Image(systemName: "chevron.up.chevron.down")
                                                    .font(.system(size: 12))
                                                    .foregroundColor(.warm400)
                                            }
                                        }
                                    }
                                )
                            } else {
                                // Read-only display
                                BudgetDisplayRow(icon: .happy, label: "From", value: rule?.giverName ?? "")
                                Divider().background(Color.warm200)
                                BudgetDisplayRow(icon: .highfive, label: "To", value: rule?.receiverName ?? "")
                            }
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Amount Section
                    VStack(spacing: Spacing.md) {
                        Text("Amount")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        HStack(spacing: Spacing.md) {
                            Text("$")
                                .font(.amountLarge)
                                .foregroundColor(.brandPrimary)

                            TextField("0.00", text: $monthlyAmount)
                                .keyboardType(.decimalPad)
                                .font(.amountLarge)
                                .foregroundColor(textColor)
                                .multilineTextAlignment(.trailing)
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Expense Types Section
                    VStack(spacing: Spacing.md) {
                        Text("Expense Types")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(spacing: 0) {
                            if viewModel.expenseTypes.isEmpty {
                                HStack(spacing: Spacing.sm) {
                                    CatIcon(name: .sleeping, size: .md, color: .warm400)
                                    Text("No expense types available")
                                        .font(.bodyMedium)
                                        .foregroundColor(.textTertiary)
                                }
                                .padding(Spacing.lg)
                            } else {
                                ForEach(Array(viewModel.expenseTypes.enumerated()), id: \.element.id) { index, expenseType in
                                    if index > 0 {
                                        Divider().background(Color.warm200)
                                    }

                                    Button {
                                        HapticManager.selection()
                                        if selectedExpenseTypeIds.contains(expenseType.id) {
                                            selectedExpenseTypeIds.remove(expenseType.id)
                                        } else {
                                            selectedExpenseTypeIds.insert(expenseType.id)
                                        }
                                    } label: {
                                        HStack(spacing: Spacing.sm) {
                                            CatIcon(name: .clipboard, size: .sm, color: .warm400)
                                            Text(expenseType.name)
                                                .font(.bodyLarge)
                                                .foregroundColor(textColor)
                                            Spacer()
                                            if selectedExpenseTypeIds.contains(expenseType.id) {
                                                Image(systemName: "checkmark.circle.fill")
                                                    .foregroundColor(.brandPrimary)
                                            } else {
                                                Image(systemName: "circle")
                                                    .foregroundColor(.warm300)
                                            }
                                        }
                                        .padding(.vertical, Spacing.sm)
                                    }
                                }
                            }
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
                        title: isEditing ? "Save Changes" : "Create Rule",
                        icon: .sparkle,
                        action: {
                            Task {
                                await save()
                            }
                        },
                        isLoading: viewModel.isSaving,
                        isDisabled: !isValid
                    )
                }
                .padding(Spacing.md)
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle(isEditing ? "Edit Budget Rule" : "New Budget Rule")
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
                if let rule = rule {
                    monthlyAmount = String(format: "%.2f", rule.monthlyAmount)
                    selectedExpenseTypeIds = Set(rule.expenseTypeIds)
                }
            }
        }
    }

    private var giverName: String {
        if let id = selectedGiverId {
            return viewModel.members.first { $0.userId == id }?.displayName ?? "Select member"
        }
        return "Select member"
    }

    private var receiverName: String {
        if let id = selectedReceiverId {
            return viewModel.members.first { $0.userId == id }?.displayName ?? "Select member"
        }
        return "Select member"
    }

    private var isValid: Bool {
        if isEditing {
            return !monthlyAmount.isEmpty &&
                   Double(monthlyAmount) != nil &&
                   !selectedExpenseTypeIds.isEmpty
        } else {
            return selectedGiverId != nil &&
                   selectedReceiverId != nil &&
                   selectedGiverId != selectedReceiverId &&
                   !monthlyAmount.isEmpty &&
                   Double(monthlyAmount) != nil &&
                   !selectedExpenseTypeIds.isEmpty
        }
    }

    private func save() async {
        guard let amount = Double(monthlyAmount) else { return }

        HapticManager.buttonTap()

        let success: Bool
        if let rule = rule {
            success = await viewModel.updateBudgetRule(
                rule.id,
                monthlyAmount: amount,
                expenseTypeIds: Array(selectedExpenseTypeIds)
            )
        } else {
            guard let giverId = selectedGiverId,
                  let receiverId = selectedReceiverId else { return }
            success = await viewModel.createBudgetRule(
                giverUserId: giverId,
                receiverUserId: receiverId,
                monthlyAmount: amount,
                expenseTypeIds: Array(selectedExpenseTypeIds)
            )
        }

        if success {
            HapticManager.success()
            dismiss()
        } else {
            HapticManager.error()
        }
    }
}

// MARK: - Budget Form Field

private struct BudgetFormField<Content: View>: View {
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

// MARK: - Budget Display Row

private struct BudgetDisplayRow: View {
    let icon: CatIcon.Name
    let label: String
    let value: String

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

                Text(value)
                    .font(.bodyLarge)
                    .foregroundColor(textColor)
            }

            Spacer()
        }
    }
}

#Preview {
    BudgetRuleEditSheet(
        viewModel: BudgetViewModel(),
        rule: nil
    )
}
