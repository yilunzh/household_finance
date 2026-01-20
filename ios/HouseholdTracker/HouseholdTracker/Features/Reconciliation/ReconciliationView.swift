import SwiftUI

struct ReconciliationView: View {
    @State private var viewModel = ReconciliationViewModel()
    @State private var showSettleConfirmation = false
    @State private var showUnsettleConfirmation = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Month Selector
                MonthSelectorView(
                    month: viewModel.formattedMonth,
                    onPrevious: { viewModel.previousMonth() },
                    onNext: { viewModel.nextMonth() }
                )

                if viewModel.isLoading && viewModel.reconciliation == nil {
                    Spacer()
                    ProgressView()
                    Spacer()
                } else if let reconciliation = viewModel.reconciliation {
                    ScrollView {
                        VStack(spacing: 20) {
                            // Settlement Banner
                            if reconciliation.isSettled {
                                SettledBannerView(settlement: reconciliation.settlement)
                            }

                            // Summary Card
                            SummaryCardView(summary: reconciliation.summary)

                            // Category Breakdown
                            if !reconciliation.summary.breakdown.isEmpty {
                                BreakdownCardView(breakdown: reconciliation.summary.breakdown)
                            }

                            // Budget Status
                            if let budgetStatus = reconciliation.budgetStatus, !budgetStatus.isEmpty {
                                BudgetStatusCardView(budgets: budgetStatus)
                            }

                            // Settlement Button
                            if !reconciliation.isSettled {
                                Button {
                                    showSettleConfirmation = true
                                } label: {
                                    Label("Mark as Settled", systemImage: "checkmark.circle")
                                        .frame(maxWidth: .infinity)
                                }
                                .buttonStyle(.borderedProminent)
                                .padding(.horizontal)
                            } else {
                                Button(role: .destructive) {
                                    showUnsettleConfirmation = true
                                } label: {
                                    Label("Unsettle Month", systemImage: "arrow.uturn.backward")
                                        .frame(maxWidth: .infinity)
                                }
                                .buttonStyle(.bordered)
                                .padding(.horizontal)
                            }

                            Spacer(minLength: 32)
                        }
                        .padding(.top)
                    }
                    .refreshable {
                        await viewModel.fetchReconciliation()
                    }
                } else {
                    Spacer()
                    VStack(spacing: 12) {
                        Image(systemName: "chart.pie")
                            .font(.system(size: 48))
                            .foregroundStyle(.secondary)

                        Text("No data available")
                            .font(.headline)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
            }
            .navigationTitle("Summary")
            .task {
                await viewModel.fetchReconciliation()
            }
            .alert("Error", isPresented: .init(
                get: { viewModel.error != nil },
                set: { if !$0 { viewModel.clearError() } }
            )) {
                Button("OK") { viewModel.clearError() }
            } message: {
                Text(viewModel.error ?? "")
            }
            .confirmationDialog("Settle Month", isPresented: $showSettleConfirmation) {
                Button("Mark as Settled") {
                    Task {
                        await viewModel.settleMonth()
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will lock the month and record the settlement. You can unsettle later if needed.")
            }
            .confirmationDialog("Unsettle Month", isPresented: $showUnsettleConfirmation) {
                Button("Unsettle", role: .destructive) {
                    Task {
                        await viewModel.unsettleMonth()
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will unlock the month and allow changes to transactions.")
            }
        }
    }
}

struct SettledBannerView: View {
    let settlement: Settlement?

    var body: some View {
        HStack {
            Image(systemName: "checkmark.seal.fill")
                .foregroundStyle(.green)

            VStack(alignment: .leading) {
                Text("Month Settled")
                    .font(.headline)

                if let settlement = settlement {
                    Text("Settled on \(formattedDate(settlement.settledDate))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()
        }
        .padding()
        .background(Color.green.opacity(0.1))
        .cornerRadius(12)
        .padding(.horizontal)
    }

    private func formattedDate(_ dateString: String) -> String {
        let inputFormatter = DateFormatter()
        inputFormatter.dateFormat = "yyyy-MM-dd"

        let outputFormatter = DateFormatter()
        outputFormatter.dateStyle = .medium

        if let date = inputFormatter.date(from: dateString) {
            return outputFormatter.string(from: date)
        }
        return dateString
    }
}

struct SummaryCardView: View {
    let summary: ReconciliationSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Settlement")
                .font(.headline)

            // Settlement Message
            Text(summary.settlementMessage)
                .font(.title3)
                .fontWeight(.semibold)
                .foregroundStyle(.primary)

            Divider()

            // Total Spent
            HStack {
                Text("Total Spent")
                Spacer()
                Text(formatCurrency(summary.totalSpent))
                    .fontWeight(.semibold)
            }

            // User Payments
            ForEach(Array(summary.userPayments.keys.sorted()), id: \.self) { userId in
                if let amount = summary.userPayments[userId],
                   let name = summary.memberNames[userId] {
                    HStack {
                        Text("\(name) paid")
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(formatCurrency(amount))
                    }
                }
            }

            // Balances
            ForEach(Array(summary.balances.keys.sorted()), id: \.self) { userId in
                if let balance = summary.balances[userId],
                   let name = summary.memberNames[userId] {
                    HStack {
                        Text("\(name)'s balance")
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(formatCurrency(balance))
                            .foregroundStyle(balance >= 0 ? .green : .red)
                    }
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
        .padding(.horizontal)
    }

    private func formatCurrency(_ amount: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: NSNumber(value: amount)) ?? "$\(amount)"
    }
}

struct BreakdownCardView: View {
    let breakdown: [CategoryBreakdown]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("By Category")
                .font(.headline)

            ForEach(breakdown) { category in
                HStack {
                    Text(category.categoryName)
                    Spacer()
                    Text("\(category.count) items")
                        .foregroundStyle(.secondary)
                    Text(formatCurrency(category.total))
                        .fontWeight(.medium)
                        .frame(width: 80, alignment: .trailing)
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
        .padding(.horizontal)
    }

    private func formatCurrency(_ amount: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: NSNumber(value: amount)) ?? "$\(amount)"
    }
}

struct BudgetStatusCardView: View {
    let budgets: [BudgetStatus]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Budget Status")
                .font(.headline)

            ForEach(budgets) { budget in
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("\(budget.giverDisplayName) → \(budget.receiverDisplayName)")
                            .font(.subheadline)
                            .fontWeight(.medium)

                        Spacer()

                        Text(formatCurrency(budget.spentAmount))
                        Text("/")
                            .foregroundStyle(.secondary)
                        Text(formatCurrency(budget.budgetAmount))
                            .foregroundStyle(.secondary)
                    }

                    ProgressView(value: min(budget.percentUsed / 100, 1.0))
                        .tint(budget.isOverBudget ? .red : .green)

                    if budget.isOverBudget {
                        Text("Over budget by \(formatCurrency(budget.spentAmount - budget.budgetAmount))")
                            .font(.caption)
                            .foregroundStyle(.red)
                    } else {
                        Text("\(formatCurrency(budget.remaining)) remaining")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.vertical, 4)
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
        .padding(.horizontal)
    }

    private func formatCurrency(_ amount: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: NSNumber(value: amount)) ?? "$\(amount)"
    }
}

#Preview {
    ReconciliationView()
        .environment(AuthManager())
}
