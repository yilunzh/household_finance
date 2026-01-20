import SwiftUI

struct TransactionFilterSheet: View {
    @Bindable var viewModel: TransactionsViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var dateFrom: Date?
    @State private var dateTo: Date?
    @State private var selectedCategory: TransactionCategory?
    @State private var selectedExpenseType: ExpenseType?
    @State private var selectedPaidBy: HouseholdMember?
    @State private var amountMin: String = ""
    @State private var amountMax: String = ""

    @State private var showDateFromPicker = false
    @State private var showDateToPicker = false

    var body: some View {
        NavigationStack {
            Form {
                // Date Range Section
                Section {
                    // Date From
                    HStack {
                        Text("From")
                        Spacer()
                        if let date = dateFrom {
                            Text(date, style: .date)
                                .foregroundStyle(.secondary)
                            Button {
                                dateFrom = nil
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.secondary)
                            }
                            .buttonStyle(.plain)
                        } else {
                            Text("Any")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .contentShape(Rectangle())
                    .onTapGesture {
                        showDateFromPicker.toggle()
                    }

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
                    }

                    // Date To
                    HStack {
                        Text("To")
                        Spacer()
                        if let date = dateTo {
                            Text(date, style: .date)
                                .foregroundStyle(.secondary)
                            Button {
                                dateTo = nil
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.secondary)
                            }
                            .buttonStyle(.plain)
                        } else {
                            Text("Any")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .contentShape(Rectangle())
                    .onTapGesture {
                        showDateToPicker.toggle()
                    }

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
                    }
                } header: {
                    Text("Date Range")
                }

                // Category & Expense Type Section
                Section {
                    Picker("Category", selection: $selectedCategory) {
                        Text("Any").tag(nil as TransactionCategory?)
                        ForEach(viewModel.categories) { category in
                            Text(category.name).tag(category as TransactionCategory?)
                        }
                    }

                    if !viewModel.expenseTypes.isEmpty {
                        Picker("Expense Type", selection: $selectedExpenseType) {
                            Text("Any").tag(nil as ExpenseType?)
                            ForEach(viewModel.expenseTypes) { expenseType in
                                Text(expenseType.name).tag(expenseType as ExpenseType?)
                            }
                        }
                    }
                } header: {
                    Text("Categories")
                }

                // Paid By Section
                Section {
                    Picker("Paid By", selection: $selectedPaidBy) {
                        Text("Anyone").tag(nil as HouseholdMember?)
                        ForEach(viewModel.members) { member in
                            Text(member.displayName).tag(member as HouseholdMember?)
                        }
                    }
                } header: {
                    Text("Paid By")
                }

                // Amount Range Section
                Section {
                    HStack {
                        Text("Min")
                        Spacer()
                        TextField("0", text: $amountMin)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 100)
                    }

                    HStack {
                        Text("Max")
                        Spacer()
                        TextField("Any", text: $amountMax)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 100)
                    }
                } header: {
                    Text("Amount Range (USD)")
                }

                // Clear Filters Button
                if hasAnyFilter {
                    Section {
                        Button(role: .destructive) {
                            clearAllFilters()
                        } label: {
                            HStack {
                                Spacer()
                                Text("Clear All Filters")
                                Spacer()
                            }
                        }
                    }
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Apply") {
                        applyFilters()
                        dismiss()
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

#Preview {
    TransactionFilterSheet(viewModel: TransactionsViewModel())
}
