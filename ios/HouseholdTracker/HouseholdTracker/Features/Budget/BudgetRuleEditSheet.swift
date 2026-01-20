import SwiftUI

struct BudgetRuleEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var viewModel: BudgetViewModel
    let rule: BudgetRule?

    @State private var selectedGiverId: Int?
    @State private var selectedReceiverId: Int?
    @State private var monthlyAmount: String = ""
    @State private var selectedExpenseTypeIds: Set<Int> = []

    private var isEditing: Bool { rule != nil }

    var body: some View {
        NavigationStack {
            Form {
                if !isEditing {
                    Section("Transfer") {
                        Picker("From", selection: $selectedGiverId) {
                            Text("Select member").tag(nil as Int?)
                            ForEach(viewModel.members) { member in
                                Text(member.displayName).tag(member.userId as Int?)
                            }
                        }

                        Picker("To", selection: $selectedReceiverId) {
                            Text("Select member").tag(nil as Int?)
                            ForEach(viewModel.members) { member in
                                Text(member.displayName).tag(member.userId as Int?)
                            }
                        }
                    }
                } else {
                    Section("Transfer") {
                        HStack {
                            Text("From")
                            Spacer()
                            Text(rule?.giverName ?? "")
                                .foregroundStyle(.secondary)
                        }
                        HStack {
                            Text("To")
                            Spacer()
                            Text(rule?.receiverName ?? "")
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Section("Amount") {
                    HStack {
                        Text("$")
                        TextField("Monthly Amount", text: $monthlyAmount)
                            .keyboardType(.decimalPad)
                    }
                }

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
            .navigationTitle(isEditing ? "Edit Budget Rule" : "New Budget Rule")
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
                    monthlyAmount = String(format: "%.2f", rule.monthlyAmount)
                    selectedExpenseTypeIds = Set(rule.expenseTypeIds)
                }
            }
        }
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
            dismiss()
        }
    }
}

#Preview {
    BudgetRuleEditSheet(
        viewModel: BudgetViewModel(),
        rule: nil
    )
}
