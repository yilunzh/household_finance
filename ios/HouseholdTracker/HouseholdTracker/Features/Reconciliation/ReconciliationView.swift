import SwiftUI

struct ReconciliationView: View {
    @Environment(\.colorScheme) private var colorScheme
    @State private var viewModel = ReconciliationViewModel()
    @State private var showSettleConfirmation = false
    @State private var showUnsettleConfirmation = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Month Selector
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

                if viewModel.isLoading && viewModel.reconciliation == nil {
                    LoadingState(message: "Loading summary...")
                } else if let reconciliation = viewModel.reconciliation {
                    ScrollView {
                        VStack(spacing: Spacing.md) {
                            // Settlement Banner
                            if reconciliation.isSettled {
                                StyledSettledBanner(settlement: reconciliation.settlement)
                            }

                            // Summary Card
                            StyledSummaryCard(summary: reconciliation.summary)

                            // Category Breakdown
                            if !reconciliation.summary.breakdown.isEmpty {
                                StyledBreakdownCard(breakdown: reconciliation.summary.breakdown)
                            }

                            // Budget Status
                            if let budgetStatus = reconciliation.budgetStatus, !budgetStatus.isEmpty {
                                StyledBudgetStatusCard(budgets: budgetStatus)
                            }

                            // Settlement Button
                            if !reconciliation.isSettled {
                                SecondaryButton(
                                    title: "Mark as Settled",
                                    icon: .celebrate,
                                    action: {
                                        showSettleConfirmation = true
                                    }
                                )
                                .padding(.horizontal, Spacing.md)
                            } else {
                                DangerButton(
                                    title: "Unsettle Month",
                                    icon: .unlock,
                                    action: {
                                        showUnsettleConfirmation = true
                                    },
                                    style: .outlined
                                )
                                .padding(.horizontal, Spacing.md)
                            }

                            Spacer(minLength: Spacing.xxl)
                        }
                        .padding(.top, Spacing.sm)
                    }
                    .refreshable {
                        await viewModel.fetchReconciliation()
                    }
                } else {
                    EmptyState(
                        icon: .sleeping,
                        title: "No data available",
                        message: "There are no transactions for this month yet."
                    )
                }
            }
            .background(backgroundColor.ignoresSafeArea())
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
                    HapticManager.success()
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
                    HapticManager.warning()
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

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

// MARK: - Styled Settled Banner

struct StyledSettledBanner: View {
    let settlement: Settlement?

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            ZStack {
                Circle()
                    .fill(Color.sage100)
                    .frame(width: 44, height: 44)

                CatIcon(name: .lock, size: .md, color: .sage600)
            }

            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text("Month Settled")
                    .font(.labelLarge)
                    .foregroundColor(textColor)

                if let settlement = settlement {
                    Text("Settled on \(formattedDate(settlement.settledDate))")
                        .font(.labelSmall)
                        .foregroundColor(.textSecondary)
                }
            }

            Spacer()

            CatIcon(name: .celebrate, size: .lg, color: .sage500)
        }
        .padding(Spacing.md)
        .background(
            LinearGradient(
                colors: [Color.sage50, Color.sage100.opacity(0.5)],
                startPoint: .leading,
                endPoint: .trailing
            )
        )
        .cornerRadius(CornerRadius.large)
        .overlay(
            RoundedRectangle(cornerRadius: CornerRadius.large)
                .stroke(Color.sage200, lineWidth: 1)
        )
        .padding(.horizontal, Spacing.md)
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
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

// MARK: - Styled Summary Card

struct StyledSummaryCard: View {
    let summary: ReconciliationSummary

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            // Header
            HStack {
                CatIcon(name: .highfive, size: .md, color: .brandPrimary)
                Text("Settlement")
                    .font(.labelLarge)
                    .foregroundColor(textColor)
            }

            // Settlement Message - highlighted
            HStack {
                Text(summary.settlementMessage)
                    .font(.bodyLarge)
                    .fontWeight(.semibold)
                    .foregroundColor(.textPrimary)  // Always dark text on light background
            }
            .padding(Spacing.sm)
            .frame(maxWidth: .infinity)
            .background(Color.terracotta50)
            .cornerRadius(CornerRadius.medium)

            Divider()
                .background(Color.warm200)

            // Total Spent
            HStack {
                Text("Total Spent")
                    .font(.labelMedium)
                    .foregroundColor(textColor)
                Spacer()
                Text(formatCurrency(summary.totalSpent))
                    .font(.amountMedium)
                    .foregroundColor(.brandPrimary)
            }

            // User Payments
            ForEach(Array(summary.userPayments.keys.sorted()), id: \.self) { userId in
                if let amount = summary.userPayments[userId],
                   let name = summary.memberNames[userId] {
                    HStack {
                        Text("\(name) paid")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                        Spacer()
                        Text(formatCurrency(amount))
                            .font(.amountSmall)
                            .foregroundColor(textColor)
                    }
                }
            }

            // Balances
            ForEach(Array(summary.balances.keys.sorted()), id: \.self) { userId in
                if let balance = summary.balances[userId],
                   let name = summary.memberNames[userId] {
                    HStack {
                        Text("\(name)'s balance")
                            .font(.labelMedium)
                            .foregroundColor(.textSecondary)
                        Spacer()
                        Text(formatCurrency(balance))
                            .font(.amountSmall)
                            .foregroundColor(balance >= 0 ? .success : .danger)
                    }
                }
            }
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
        .padding(.horizontal, Spacing.md)
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    private func formatCurrency(_ amount: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: NSNumber(value: amount)) ?? "$\(amount)"
    }
}

// MARK: - Styled Breakdown Card

struct StyledBreakdownCard: View {
    let breakdown: [CategoryBreakdown]

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            // Header
            HStack {
                CatIcon(name: .clipboard, size: .md, color: .brandPrimary)
                Text("By Category")
                    .font(.labelLarge)
                    .foregroundColor(textColor)
            }

            ForEach(breakdown) { category in
                HStack(spacing: Spacing.sm) {
                    // Category icon circle
                    ZStack {
                        Circle()
                            .fill(categoryColor(for: category.categoryName).opacity(0.15))
                            .frame(width: 32, height: 32)

                        CatIcon(name: categoryIcon(for: category.categoryName), size: .sm, color: categoryColor(for: category.categoryName))
                    }

                    Text(category.categoryName)
                        .font(.labelMedium)
                        .foregroundColor(textColor)

                    Spacer()

                    Text("\(category.count)")
                        .font(.labelSmall)
                        .foregroundColor(.textSecondary)
                        .padding(.horizontal, Spacing.xs)
                        .padding(.vertical, Spacing.xxxs)
                        .background(Color.warm200)
                        .cornerRadius(CornerRadius.full)

                    Text(formatCurrency(category.total))
                        .font(.amountSmall)
                        .foregroundColor(textColor)
                        .frame(width: 80, alignment: .trailing)
                }
            }
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
        .padding(.horizontal, Spacing.md)
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    private func categoryColor(for name: String) -> Color {
        switch name.uppercased() {
        case "SHARED":
            return .brandPrimary
        case "PERSONAL_ME", "PERSONAL_WIFE":
            return .sage500
        default:
            return .warm500
        }
    }

    private func categoryIcon(for name: String) -> CatIcon.Name {
        switch name.uppercased() {
        case "SHARED":
            return .highfive
        case "PERSONAL_ME":
            return .happy
        case "PERSONAL_WIFE":
            return .wave
        default:
            return .coins
        }
    }

    private func formatCurrency(_ amount: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: NSNumber(value: amount)) ?? "$\(amount)"
    }
}

// MARK: - Styled Budget Status Card

struct StyledBudgetStatusCard: View {
    let budgets: [BudgetStatus]

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            // Header
            HStack {
                CatIcon(name: .coins, size: .md, color: .brandPrimary)
                Text("Budget Status")
                    .font(.labelLarge)
                    .foregroundColor(textColor)
            }

            ForEach(budgets) { budget in
                VStack(alignment: .leading, spacing: Spacing.sm) {
                    HStack {
                        Text("\(budget.giverDisplayName) → \(budget.receiverDisplayName)")
                            .font(.labelMedium)
                            .foregroundColor(textColor)

                        Spacer()

                        Text(formatCurrency(budget.spentAmount))
                            .font(.amountSmall)
                            .foregroundColor(budget.isOverBudget ? .danger : textColor)
                        Text("/")
                            .font(.labelSmall)
                            .foregroundColor(.textTertiary)
                        Text(formatCurrency(budget.budgetAmount))
                            .font(.labelSmall)
                            .foregroundColor(.textSecondary)
                    }

                    // Custom progress bar
                    GeometryReader { geometry in
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: CornerRadius.small)
                                .fill(Color.warm200)
                                .frame(height: 8)

                            RoundedRectangle(cornerRadius: CornerRadius.small)
                                .fill(budget.isOverBudget ? Color.danger : Color.success)
                                .frame(width: geometry.size.width * min(CGFloat(budget.percentUsed / 100), 1.0), height: 8)
                        }
                    }
                    .frame(height: 8)

                    HStack {
                        if budget.isOverBudget {
                            CatIcon(name: .worried, size: .sm, color: .rose700)
                            Text("Over budget by \(formatCurrency(budget.spentAmount - budget.budgetAmount))")
                                .font(.labelSmall)
                                .foregroundColor(.rose700)  // Darker for contrast on light background
                        } else {
                            CatIcon(name: .happy, size: .sm, color: .sage700)
                            Text("\(formatCurrency(budget.remaining)) remaining")
                                .font(.labelSmall)
                                .foregroundColor(.sage700)  // Darker for contrast on light background
                        }
                    }
                }
                .padding(Spacing.sm)
                .background(budget.isOverBudget ? Color.rose50.opacity(0.5) : Color.sage50.opacity(0.5))
                .cornerRadius(CornerRadius.medium)
            }
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
        .padding(.horizontal, Spacing.md)
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
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
