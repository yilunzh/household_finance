import SwiftUI

struct SplitRuleEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @Bindable var viewModel: BudgetViewModel
    let rule: SplitRule?

    @State private var member1Percent: Double = 50
    @State private var isDefault: Bool = false
    @State private var selectedExpenseTypeIds: Set<Int> = []

    private var isEditing: Bool { rule != nil }
    private var member2Percent: Int { 100 - Int(member1Percent) }

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
                    // Split Percentage Section
                    VStack(spacing: Spacing.md) {
                        Text("Split Percentage")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(spacing: Spacing.md) {
                            // Member 1
                            HStack(spacing: Spacing.sm) {
                                CatIcon(name: .happy, size: .sm, color: .brandPrimary)
                                Text(memberName(index: 0))
                                    .font(.bodyLarge)
                                    .foregroundColor(textColor)
                                Spacer()
                                Text("\(Int(member1Percent))%")
                                    .font(.amountMedium)
                                    .foregroundColor(.brandPrimary)
                                    .monospacedDigit()
                            }

                            // Slider
                            Slider(value: $member1Percent, in: 0...100, step: 5) { _ in
                                HapticManager.selection()
                            }
                            .tint(.brandPrimary)

                            // Member 2
                            HStack(spacing: Spacing.sm) {
                                CatIcon(name: .highfive, size: .sm, color: .sage600)
                                Text(memberName(index: 1))
                                    .font(.bodyLarge)
                                    .foregroundColor(textColor)
                                Spacer()
                                Text("\(member2Percent)%")
                                    .font(.amountMedium)
                                    .foregroundColor(.sage600)
                                    .monospacedDigit()
                            }

                            // Visual Split Bar
                            GeometryReader { geometry in
                                HStack(spacing: 2) {
                                    RoundedRectangle(cornerRadius: CornerRadius.small)
                                        .fill(Color.brandPrimary)
                                        .frame(width: geometry.size.width * (member1Percent / 100))

                                    RoundedRectangle(cornerRadius: CornerRadius.small)
                                        .fill(Color.sage400)
                                }
                            }
                            .frame(height: 8)
                        }
                        .padding(Spacing.md)
                        .background(cardBackground)
                        .cornerRadius(CornerRadius.large)
                        .subtleShadow()
                    }

                    // Default Rule Toggle (only for new rules)
                    if !isEditing {
                        VStack(spacing: Spacing.md) {
                            Text("Options")
                                .font(.labelMedium)
                                .foregroundColor(.textSecondary)
                                .frame(maxWidth: .infinity, alignment: .leading)

                            VStack(spacing: Spacing.sm) {
                                HStack(spacing: Spacing.sm) {
                                    CatIcon(name: .sparkle, size: .sm, color: .warm400)

                                    VStack(alignment: .leading, spacing: Spacing.xxxs) {
                                        Text("Default Rule")
                                            .font(.bodyLarge)
                                            .foregroundColor(textColor)
                                        Text("Applies to expense types not covered by other rules")
                                            .font(.labelSmall)
                                            .foregroundColor(.textTertiary)
                                    }

                                    Spacer()

                                    Toggle("", isOn: $isDefault)
                                        .tint(.brandPrimary)
                                        .labelsHidden()
                                        .onChange(of: isDefault) { _, _ in
                                            HapticManager.selection()
                                        }
                                }
                            }
                            .padding(Spacing.md)
                            .background(cardBackground)
                            .cornerRadius(CornerRadius.large)
                            .subtleShadow()
                        }
                    }

                    // Expense Types Section (only if not default)
                    if !isDefault {
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
                    }

                    // Default Rule Info (for editing)
                    if let rule = rule, rule.isDefault {
                        HStack(spacing: Spacing.sm) {
                            CatIcon(name: .sparkle, size: .sm, color: .brandPrimary)
                            Text("This is the default split rule")
                                .font(.labelMedium)
                                .foregroundColor(.brandPrimary)
                        }
                        .padding(Spacing.md)
                        .frame(maxWidth: .infinity)
                        .background(Color.terracotta100)
                        .cornerRadius(CornerRadius.medium)
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
            .navigationTitle(isEditing ? "Edit Split Rule" : "New Split Rule")
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
                    member1Percent = Double(rule.member1Percent)
                    isDefault = rule.isDefault
                    if let ids = rule.expenseTypeIds {
                        selectedExpenseTypeIds = Set(ids)
                    }
                }
            }
        }
    }

    private func memberName(index: Int) -> String {
        guard viewModel.members.count > index else {
            return "Member \(index + 1)"
        }
        return viewModel.members[index].displayName
    }

    private var isValid: Bool {
        if isEditing || isDefault {
            return true // Default rules don't need expense types
        }
        return !selectedExpenseTypeIds.isEmpty
    }

    private func save() async {
        HapticManager.buttonTap()

        let success: Bool
        if let rule = rule {
            success = await viewModel.updateSplitRule(
                rule.id,
                member1Percent: Int(member1Percent),
                member2Percent: member2Percent,
                expenseTypeIds: Array(selectedExpenseTypeIds)
            )
        } else {
            success = await viewModel.createSplitRule(
                member1Percent: Int(member1Percent),
                member2Percent: member2Percent,
                isDefault: isDefault,
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

#Preview {
    SplitRuleEditSheet(
        viewModel: BudgetViewModel(),
        rule: nil
    )
}
