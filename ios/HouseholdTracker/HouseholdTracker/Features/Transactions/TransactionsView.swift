import SwiftUI

struct TransactionsView: View {
    @Environment(AuthManager.self) private var authManager
    @State private var viewModel = TransactionsViewModel()
    @State private var showAddSheet = false
    @State private var showFilterSheet = false
    @State private var selectedTransaction: Transaction?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Search Bar (when search is active)
                if viewModel.isSearchActive {
                    SearchBarView(
                        searchText: $viewModel.searchText,
                        onSearch: {
                            Task {
                                await viewModel.fetchTransactions()
                            }
                        },
                        onCancel: {
                            viewModel.clearSearchAndFilters()
                            Task {
                                await viewModel.fetchTransactions()
                            }
                        }
                    )
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                    .background(Color(.systemBackground))
                }

                // Month Selector (hidden when searching)
                if !viewModel.isSearchActive {
                    MonthSelectorView(
                        month: viewModel.formattedMonth,
                        onPrevious: { viewModel.previousMonth() },
                        onNext: { viewModel.nextMonth() }
                    )
                }

                // Active Filters Summary
                if viewModel.hasActiveFilters {
                    ActiveFiltersView(
                        filterCount: viewModel.activeFilterCount,
                        onClear: {
                            viewModel.clearSearchAndFilters()
                            Task {
                                await viewModel.fetchTransactions()
                            }
                        }
                    )
                }

                // Transactions List
                if viewModel.isLoading && viewModel.transactions.isEmpty {
                    Spacer()
                    ProgressView()
                    Spacer()
                } else if viewModel.transactions.isEmpty {
                    Spacer()
                    VStack(spacing: 12) {
                        Image(systemName: viewModel.hasActiveFilters ? "magnifyingglass" : "tray")
                            .font(.system(size: 48))
                            .foregroundStyle(.secondary)

                        Text(viewModel.hasActiveFilters ? "No matching transactions" : "No transactions")
                            .font(.headline)
                            .foregroundStyle(.secondary)

                        Text(viewModel.hasActiveFilters ? "Try adjusting your filters" : "Tap + to add your first expense")
                            .font(.subheadline)
                            .foregroundStyle(.tertiary)
                    }
                    Spacer()
                } else {
                    List {
                        ForEach(viewModel.transactions) { transaction in
                            Button {
                                selectedTransaction = transaction
                            } label: {
                                TransactionRowView(transaction: transaction)
                            }
                            .buttonStyle(.plain)
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button(role: .destructive) {
                                    Task {
                                        await viewModel.deleteTransaction(transaction.id)
                                    }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                    .listStyle(.plain)
                    .refreshable {
                        await viewModel.fetchTransactions()
                    }
                }
            }
            .navigationTitle("Transactions")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        if viewModel.isSearchActive {
                            showFilterSheet = true
                        } else {
                            viewModel.isSearchActive = true
                        }
                    } label: {
                        ZStack(alignment: .topTrailing) {
                            Image(systemName: viewModel.isSearchActive ? "line.3.horizontal.decrease.circle" : "magnifyingglass")
                            if viewModel.activeFilterCount > 0 {
                                Text("\(viewModel.activeFilterCount)")
                                    .font(.caption2)
                                    .fontWeight(.bold)
                                    .foregroundStyle(.white)
                                    .padding(4)
                                    .background(Color.accentColor)
                                    .clipShape(Circle())
                                    .offset(x: 8, y: -8)
                            }
                        }
                    }
                    .accessibilityLabel(viewModel.isSearchActive ? "Filters" : "Search")
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showAddSheet = true
                    } label: {
                        Image(systemName: "plus")
                    }
                    .accessibilityLabel("Add Transaction")
                }
            }
            .sheet(isPresented: $showAddSheet) {
                AddTransactionSheet(viewModel: viewModel)
            }
            .sheet(isPresented: $showFilterSheet) {
                TransactionFilterSheet(viewModel: viewModel)
            }
            .sheet(item: $selectedTransaction) { transaction in
                TransactionDetailView(
                    transaction: transaction,
                    viewModel: viewModel,
                    onUpdate: { updatedTransaction in
                        viewModel.updateTransactionInList(updatedTransaction)
                    }
                )
            }
            .task {
                if let householdId = authManager.currentHouseholdId {
                    await viewModel.fetchMembers(householdId: householdId)
                }
                await viewModel.fetchConfig()
                await viewModel.fetchTransactions()
            }
            .alert("Error", isPresented: .init(
                get: { viewModel.error != nil },
                set: { if !$0 { viewModel.clearError() } }
            )) {
                Button("OK") { viewModel.clearError() }
            } message: {
                Text(viewModel.error ?? "")
            }
        }
    }
}

// MARK: - Search Bar View

struct SearchBarView: View {
    @Binding var searchText: String
    let onSearch: () -> Void
    let onCancel: () -> Void

    var body: some View {
        HStack {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)

                TextField("Search transactions...", text: $searchText)
                    .textFieldStyle(.plain)
                    .submitLabel(.search)
                    .onSubmit {
                        onSearch()
                    }

                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                        onSearch()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .padding(8)
            .background(Color(.systemGray6))
            .cornerRadius(10)

            Button("Cancel") {
                onCancel()
            }
        }
    }
}

// MARK: - Active Filters View

struct ActiveFiltersView: View {
    let filterCount: Int
    let onClear: () -> Void

    var body: some View {
        HStack {
            Image(systemName: "line.3.horizontal.decrease.circle.fill")
                .foregroundStyle(Color.accentColor)

            Text("\(filterCount) filter\(filterCount == 1 ? "" : "s") active")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Spacer()

            Button("Clear") {
                onClear()
            }
            .font(.subheadline)
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(.systemGray6))
    }
}

struct MonthSelectorView: View {
    let month: String
    let onPrevious: () -> Void
    let onNext: () -> Void

    var body: some View {
        HStack {
            Button(action: onPrevious) {
                Image(systemName: "chevron.left")
                    .font(.title3)
            }

            Spacer()

            Text(month)
                .font(.headline)

            Spacer()

            Button(action: onNext) {
                Image(systemName: "chevron.right")
                    .font(.title3)
            }
        }
        .padding()
        .background(Color(.systemBackground))
    }
}

struct TransactionRowView: View {
    let transaction: Transaction

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(transaction.merchant)
                    .font(.headline)

                HStack(spacing: 8) {
                    if let expenseTypeName = transaction.expenseTypeName {
                        Text(expenseTypeName)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Text(formattedDate)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                HStack(spacing: 4) {
                    if transaction.receiptUrl != nil {
                        Image(systemName: "paperclip")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Text(formattedAmount)
                        .font(.headline)
                        .foregroundStyle(amountColor)
                }

                if let paidByName = transaction.paidByName {
                    Text("Paid by \(paidByName)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private var formattedAmount: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = transaction.currency
        return formatter.string(from: NSNumber(value: transaction.amount)) ?? "$\(transaction.amount)"
    }

    private var formattedDate: String {
        // Input: "2024-01-15"
        let inputFormatter = DateFormatter()
        inputFormatter.dateFormat = "yyyy-MM-dd"

        let outputFormatter = DateFormatter()
        outputFormatter.dateFormat = "MMM d"

        if let date = inputFormatter.date(from: transaction.date) {
            return outputFormatter.string(from: date)
        }
        return transaction.date
    }

    private var amountColor: Color {
        switch transaction.category {
        case "PERSONAL_ME", "PERSONAL_WIFE":
            return .secondary
        default:
            return .primary
        }
    }
}

#Preview {
    TransactionsView()
        .environment(AuthManager())
}
