import SwiftUI

struct AddTransactionSheet: View {
    @Bindable var viewModel: TransactionsViewModel
    @Environment(\.dismiss) private var dismiss
    @Environment(AuthManager.self) private var authManager

    @State private var merchant = ""
    @State private var amount = ""
    @State private var selectedDate = Date()
    @State private var selectedCategory: TransactionCategory?
    @State private var selectedExpenseType: ExpenseType?
    @State private var selectedPaidBy: HouseholdMember?
    @State private var notes = ""
    @State private var currency = "USD"

    private let currencies = ["USD", "CAD"]

    var body: some View {
        NavigationStack {
            Form {
                // Amount Section
                Section {
                    HStack {
                        TextField("0.00", text: $amount)
                            .keyboardType(.decimalPad)
                            .font(.title)

                        Picker("Currency", selection: $currency) {
                            ForEach(currencies, id: \.self) { currency in
                                Text(currency).tag(currency)
                            }
                        }
                        .pickerStyle(.menu)
                    }
                } header: {
                    Text("Amount")
                }

                // Details Section
                Section {
                    TextField("Merchant", text: $merchant)

                    DatePicker("Date", selection: $selectedDate, displayedComponents: .date)

                    // Category Picker
                    Picker("Category", selection: $selectedCategory) {
                        Text("Select...").tag(nil as TransactionCategory?)
                        ForEach(viewModel.categories) { category in
                            Text(category.name).tag(category as TransactionCategory?)
                        }
                    }

                    // Expense Type Picker
                    if !viewModel.expenseTypes.isEmpty {
                        Picker("Expense Type", selection: $selectedExpenseType) {
                            Text("None").tag(nil as ExpenseType?)
                            ForEach(viewModel.expenseTypes) { expenseType in
                                Text(expenseType.name).tag(expenseType as ExpenseType?)
                            }
                        }
                    }

                    // Paid By Picker
                    Picker("Paid By", selection: $selectedPaidBy) {
                        Text("Select...").tag(nil as HouseholdMember?)
                        ForEach(viewModel.members) { member in
                            Text(member.displayName).tag(member as HouseholdMember?)
                        }
                    }
                } header: {
                    Text("Details")
                }

                // Notes Section
                Section {
                    TextField("Notes (optional)", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                } header: {
                    Text("Notes")
                }

                // Error Display
                if let error = viewModel.error {
                    Section {
                        Text(error)
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Add Transaction")
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
                            await saveTransaction()
                        }
                    }
                    .disabled(!isFormValid || viewModel.isLoading)
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
    }

    private var isFormValid: Bool {
        guard let amountValue = Double(amount), amountValue > 0 else { return false }
        return !merchant.trimmingCharacters(in: .whitespaces).isEmpty
            && selectedCategory != nil
            && selectedPaidBy != nil
    }

    private func saveTransaction() async {
        guard let amountValue = Double(amount),
              let category = selectedCategory,
              let paidBy = selectedPaidBy else {
            return
        }

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let dateString = formatter.string(from: selectedDate)

        let request = CreateTransactionRequest(
            amount: amountValue,
            currency: currency,
            merchant: merchant.trimmingCharacters(in: .whitespaces),
            category: category.code,
            date: dateString,
            paidByUserId: paidBy.userId,
            expenseTypeId: selectedExpenseType?.id,
            notes: notes.isEmpty ? nil : notes
        )

        if await viewModel.createTransaction(request) {
            dismiss()
        }
    }
}

#Preview {
    AddTransactionSheet(viewModel: TransactionsViewModel())
        .environment(AuthManager())
}
