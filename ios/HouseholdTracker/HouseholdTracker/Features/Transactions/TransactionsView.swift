import SwiftUI

struct TransactionsView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.colorScheme) private var colorScheme
    @State private var viewModel = TransactionsViewModel()
    @State private var showAddSheet = false
    @State private var showFilterSheet = false
    @State private var selectedTransaction: Transaction?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Search Bar (when search is active)
                if viewModel.isSearchActive {
                    StyledSearchBar(
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
                    .padding(.horizontal, Spacing.md)
                    .padding(.vertical, Spacing.sm)
                }

                // Month Selector (hidden when searching)
                if !viewModel.isSearchActive {
                    StyledMonthSelector(
                        month: viewModel.formattedMonth,
                        onPrevious: {
                            HapticManager.selection()
                            viewModel.previousMonth()
                        },
                        onNext: {
                            HapticManager.selection()
                            viewModel.nextMonth()
                        }
                    )
                }

                // Active Filters Summary
                if viewModel.hasActiveFilters {
                    StyledActiveFilters(
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
                    LoadingState(message: "Loading transactions...")
                } else if viewModel.transactions.isEmpty {
                    if viewModel.hasActiveFilters {
                        EmptyState(
                            icon: .alert,
                            title: "No matching transactions",
                            message: "Try adjusting your search or filters to find what you're looking for."
                        )
                    } else {
                        EmptyState(
                            icon: .sleeping,
                            title: "No transactions yet",
                            message: "Start tracking your expenses by adding your first transaction.",
                            actionTitle: "Add Transaction",
                            action: { showAddSheet = true }
                        )
                    }
                } else {
                    ScrollView {
                        LazyVStack(spacing: Spacing.sm) {
                            ForEach(viewModel.transactions) { transaction in
                                Button {
                                    HapticManager.light()
                                    selectedTransaction = transaction
                                } label: {
                                    StyledTransactionRow(transaction: transaction)
                                }
                                .buttonStyle(.plain)
                                .contextMenu {
                                    Button(role: .destructive) {
                                        HapticManager.warning()
                                        Task {
                                            await viewModel.deleteTransaction(transaction.id)
                                        }
                                    } label: {
                                        Label("Delete", systemImage: "trash")
                                    }
                                }
                            }
                        }
                        .padding(.horizontal, Spacing.md)
                        .padding(.vertical, Spacing.sm)
                    }
                    .refreshable {
                        await viewModel.fetchTransactions()
                    }
                }
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle("Transactions")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        HapticManager.buttonTap()
                        if viewModel.isSearchActive {
                            showFilterSheet = true
                        } else {
                            viewModel.isSearchActive = true
                        }
                    } label: {
                        ZStack(alignment: .topTrailing) {
                            Image(systemName: viewModel.isSearchActive ? "line.3.horizontal.decrease.circle" : "magnifyingglass")
                                .foregroundColor(.terracotta500)
                            if viewModel.activeFilterCount > 0 {
                                CountBadge(count: viewModel.activeFilterCount, style: .brand)
                                    .offset(x: 8, y: -8)
                            }
                        }
                    }
                    .accessibilityLabel(viewModel.isSearchActive ? "Filters" : "Search")
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        HapticManager.buttonTap()
                        showAddSheet = true
                    } label: {
                        CatIcon(name: .plus, size: .md, color: .terracotta500)
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

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}


#Preview {
    TransactionsView()
        .environment(AuthManager())
}
