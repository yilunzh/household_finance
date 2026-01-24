import SwiftUI

struct SplitRuleEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var viewModel: BudgetViewModel
    let rule: SplitRule?

    @State private var member1Percent: Double = 50
    @State private var isDefault: Bool = false
    @State private var selectedExpenseTypeIds: Set<Int> = []

    private var isEditing: Bool { rule != nil }
    private var member2Percent: Int { 100 - Int(member1Percent) }

    var body: some View {
        NavigationStack {
            Form {
                Section("Split Percentage") {
                    VStack(spacing: 16) {
                        HStack {
                            Text(memberName(index: 0))
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Spacer()
                            Text("\(Int(member1Percent))%")
                                .font(.headline)
                                .monospacedDigit()
                        }

                        Slider(value: $member1Percent, in: 0...100, step: 5)
                            .tint(.blue)

                        HStack {
                            Text(memberName(index: 1))
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Spacer()
                            Text("\(member2Percent)%")
                                .font(.headline)
                                .monospacedDigit()
                        }
                    }
                    .padding(.vertical, 8)
                }

                if !isEditing {
                    Section {
                        Toggle("Default Rule", isOn: $isDefault)
                    } footer: {
                        Text("Default rule applies to all expense types not covered by other rules.")
                    }
                }

                if !isDefault {
                    Section("Expense Types") {
                        if viewModel.expenseTypes.isEmpty {
                            Text("No expense types available")
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(viewModel.expenseTypes) { expenseType in
                                Button {
                                    if selectedExpenseTypeIds.contains(expenseType.id) {
                                        selectedExpenseTypeIds.remove(expenseType.id)
                                    } else {
                                        selectedExpenseTypeIds.insert(expenseType.id)
                                    }
                                } label: {
                                    HStack {
                                        Text(expenseType.name)
                                            .foregroundStyle(.primary)
                                        Spacer()
                                        if selectedExpenseTypeIds.contains(expenseType.id) {
                                            Image(systemName: "checkmark")
                                                .foregroundStyle(.blue)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                if let rule = rule, rule.isDefault {
                    Section {
                        HStack {
                            Image(systemName: "info.circle")
                                .foregroundStyle(.blue)
                            Text("This is the default rule")
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .navigationTitle(isEditing ? "Edit Split Rule" : "New Split Rule")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await save()
                        }
                    }
                    .disabled(!isValid || viewModel.isSaving)
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
            dismiss()
        }
    }
}

#Preview {
    SplitRuleEditSheet(
        viewModel: BudgetViewModel(),
        rule: nil
    )
}
