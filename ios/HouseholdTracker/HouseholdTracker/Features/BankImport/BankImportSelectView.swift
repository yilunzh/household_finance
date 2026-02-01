import SwiftUI

struct BankImportSelectView: View {
    @Bindable var viewModel: BankImportViewModel
    let sessionId: Int

    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @State private var showCategorize = false
    @State private var showImportConfirm = false
    @State private var showSuccess = false
    @State private var importedCount = 0
    @State private var pollTimer: Timer?

    var body: some View {
        VStack(spacing: 0) {
            // Tab Bar
            tabBar

            // Select All Row
            if shouldShowSelectAll {
                selectAllRow
            }

            // Transaction List
            ScrollView {
                if viewModel.isLoading && viewModel.transactions.isEmpty {
                    loadingState
                } else if viewModel.currentTabTransactions.isEmpty {
                    emptyState
                } else {
                    transactionList
                }
            }
            .background(backgroundColor)
        }
        .safeAreaInset(edge: .bottom) {
            bottomAction
        }
        .background(backgroundColor.ignoresSafeArea())
        .navigationTitle("Select Transactions")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                if viewModel.isLoading && !viewModel.transactions.isEmpty {
                    ProgressView()
                        .scaleEffect(0.8)
                }
            }
        }
        .task {
            await viewModel.loadConfig()
            await viewModel.loadSession(sessionId)
            startPollingIfNeeded()
        }
        .onDisappear {
            stopPolling()
        }
        .navigationDestination(isPresented: $showCategorize) {
            BankImportCategorizeView(viewModel: viewModel)
        }
        .confirmationDialog("Import Transactions?", isPresented: $showImportConfirm, titleVisibility: .visible) {
            Button("Import \(viewModel.selectedCount) Transactions") {
                Task {
                    if await viewModel.importSelected() {
                        HapticManager.success()
                        importedCount = viewModel.selectedCount
                        showSuccess = true
                    } else {
                        HapticManager.error()
                    }
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will create \(viewModel.selectedCount) transactions in your household.")
        }
        .alert("Import Complete!", isPresented: $showSuccess) {
            Button("Done") {
                dismiss()
            }
        } message: {
            Text("\(importedCount) transactions have been imported successfully.")
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

    // MARK: - Tab Bar

    private var tabBar: some View {
        HStack(spacing: Spacing.xxs) {
            SelectTabButton(
                title: "Ready",
                count: viewModel.readyTransactions.count,
                isSelected: viewModel.selectedTab == .ready,
                style: .normal
            ) {
                withAnimation(.easeInOut(duration: 0.2)) {
                    viewModel.selectedTab = .ready
                }
            }

            SelectTabButton(
                title: "Review",
                count: viewModel.needsAttentionTransactions.count,
                isSelected: viewModel.selectedTab == .needsAttention,
                style: viewModel.needsAttentionTransactions.isEmpty ? .normal : .attention
            ) {
                withAnimation(.easeInOut(duration: 0.2)) {
                    viewModel.selectedTab = .needsAttention
                }
            }

            SelectTabButton(
                title: "Skipped",
                count: nil,
                isSelected: viewModel.selectedTab == .skipped,
                style: .normal
            ) {
                withAnimation(.easeInOut(duration: 0.2)) {
                    viewModel.selectedTab = .skipped
                }
            }

            SelectTabButton(
                title: "Done",
                count: nil,
                isSelected: viewModel.selectedTab == .imported,
                style: .normal
            ) {
                withAnimation(.easeInOut(duration: 0.2)) {
                    viewModel.selectedTab = .imported
                }
            }
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
        .background(backgroundColor)
    }

    // MARK: - Select All Row

    private var shouldShowSelectAll: Bool {
        (viewModel.selectedTab == .ready || viewModel.selectedTab == .needsAttention) &&
        !viewModel.currentTabTransactions.isEmpty
    }

    private var selectAllRow: some View {
        HStack(spacing: Spacing.sm) {
            Button {
                HapticManager.selection()
                let allSelected = viewModel.currentTabTransactions.allSatisfy { $0.isSelected }
                Task {
                    await viewModel.selectAll(!allSelected)
                }
            } label: {
                HStack(spacing: Spacing.sm) {
                    Image(systemName: viewModel.currentTabTransactions.allSatisfy { $0.isSelected }
                          ? "checkmark.square.fill"
                          : "square")
                        .font(.system(size: 22))
                        .foregroundColor(
                            viewModel.currentTabTransactions.allSatisfy { $0.isSelected }
                            ? .brandPrimary
                            : .warm400
                        )

                    Text("Select All (\(viewModel.currentTabTransactions.count))")
                        .font(.labelMedium)
                        .foregroundColor(.warm600)
                }
            }
            .buttonStyle(.plain)

            Spacer()
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
        .background(Color.warm50)
    }

    // MARK: - Loading State

    private var loadingState: some View {
        VStack(spacing: Spacing.md) {
            ProgressView()
                .scaleEffect(1.2)

            Text("Loading transactions...")
                .font(.bodyMedium)
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.xxxl)
    }

    // MARK: - Transaction List

    private var transactionList: some View {
        LazyVStack(spacing: 0) {
            ForEach(Array(viewModel.currentTabTransactions.enumerated()), id: \.element.id) { index, transaction in
                SelectTransactionRow(
                    transaction: transaction,
                    expenseTypes: viewModel.expenseTypes,
                    isLast: index == viewModel.currentTabTransactions.count - 1,
                    onToggle: {
                        HapticManager.selection()
                        Task {
                            await viewModel.toggleSelection(transaction)
                        }
                    }
                )
            }
        }
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
        .padding(Spacing.md)
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: Spacing.md) {
            Image(systemName: emptyStateIcon)
                .font(.system(size: 48))
                .foregroundColor(.warm300)

            Text(emptyStateMessage)
                .font(.bodyMedium)
                .foregroundColor(.warm400)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.xxxl)
        .padding(.horizontal, Spacing.lg)
    }

    private var emptyStateIcon: String {
        switch viewModel.selectedTab {
        case .ready: return "checkmark.circle"
        case .needsAttention: return "sparkles"
        case .skipped: return "minus.circle"
        case .imported: return "checkmark.seal"
        }
    }

    private var emptyStateMessage: String {
        switch viewModel.selectedTab {
        case .ready: return "No transactions ready to import.\nReview items in \"Review\" tab first."
        case .needsAttention: return "All transactions look good!"
        case .skipped: return "No skipped transactions"
        case .imported: return "No imported transactions yet"
        }
    }

    // MARK: - Bottom Action

    private var bottomAction: some View {
        VStack(spacing: 0) {
            Divider()

            VStack(spacing: Spacing.sm) {
                if viewModel.needsAttentionTransactions.isEmpty {
                    // No items need review - go straight to import
                    PrimaryButton(
                        title: "Import \(viewModel.selectedCount) Transaction\(viewModel.selectedCount == 1 ? "" : "s")",
                        icon: .sparkle,
                        action: {
                            showImportConfirm = true
                        },
                        isLoading: viewModel.isImporting,
                        isDisabled: viewModel.selectedCount == 0 || viewModel.isImporting
                    )
                } else {
                    // Has items to review
                    PrimaryButton(
                        title: "Review \(viewModel.needsAttentionTransactions.count) Flagged Item\(viewModel.needsAttentionTransactions.count == 1 ? "" : "s")",
                        icon: .alert,
                        action: {
                            showCategorize = true
                        },
                        isDisabled: viewModel.isImporting
                    )
                }
            }
            .padding(Spacing.md)
        }
        .background(cardBackground)
    }

    // MARK: - Helpers

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .white
    }

    // MARK: - Polling

    private func startPollingIfNeeded() {
        guard viewModel.currentSession?.status == .processing ||
              viewModel.currentSession?.status == .pending else { return }

        pollTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { _ in
            Task {
                await viewModel.loadSession(sessionId)
                if viewModel.currentSession?.status == .ready {
                    await MainActor.run { stopPolling() }
                }
            }
        }
    }

    private func stopPolling() {
        pollTimer?.invalidate()
        pollTimer = nil
    }
}

// MARK: - Tab Button

private struct SelectTabButton: View {
    let title: String
    let count: Int?
    let isSelected: Bool
    let style: TabStyle
    let action: () -> Void

    enum TabStyle {
        case normal
        case attention
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: Spacing.xxs) {
                Text(title)
                    .font(.labelMedium)

                if let count = count, count > 0 {
                    Text("\(count)")
                        .font(.labelSmall)
                        .fontWeight(.bold)
                        .padding(.horizontal, Spacing.xs)
                        .padding(.vertical, Spacing.xxxs)
                        .background(badgeBackground)
                        .foregroundColor(badgeTextColor)
                        .cornerRadius(CornerRadius.full)
                }
            }
            .foregroundColor(isSelected ? .warm800 : .warm500)
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, Spacing.xs)
            .background(isSelected ? Color.white : Color.clear)
            .cornerRadius(CornerRadius.small)
            .shadow(color: isSelected ? .black.opacity(0.06) : .clear, radius: 2, y: 1)
        }
        .buttonStyle(.plain)
    }

    private var badgeBackground: Color {
        if isSelected {
            return style == .attention ? .amber500 : .brandPrimary
        }
        return style == .attention ? .amber500 : .warm200
    }

    private var badgeTextColor: Color {
        if isSelected || style == .attention {
            return .white
        }
        return .warm600
    }
}

// MARK: - Transaction Row

private struct SelectTransactionRow: View {
    let transaction: ExtractedTransaction
    let expenseTypes: [ExpenseType]
    let isLast: Bool
    let onToggle: () -> Void

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.sm) {
            // Checkbox
            Button(action: onToggle) {
                Image(systemName: transaction.isSelected ? "checkmark.square.fill" : "square")
                    .font(.system(size: 22))
                    .foregroundColor(transaction.isSelected ? .brandPrimary : .warm400)
            }
            .buttonStyle(.plain)
            .disabled(transaction.status == .imported)

            // Transaction Info
            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(transaction.merchant)
                    .font(.labelLarge)
                    .foregroundColor(textColor)
                    .lineLimit(1)

                HStack(spacing: Spacing.xs) {
                    // Expense Type
                    if let expenseTypeName = transaction.expenseTypeName {
                        Text(expenseTypeName)
                            .font(.labelSmall)
                            .foregroundColor(.warm500)
                    } else if transaction.needsReview {
                        Text("?")
                            .font(.labelSmall)
                            .fontWeight(.bold)
                            .foregroundColor(.amber600)
                    }

                    Text("·")
                        .font(.labelSmall)
                        .foregroundColor(.warm300)

                    // Split
                    Text(splitDisplayName)
                        .font(.labelSmall)
                        .foregroundColor(transaction.needsReview && transaction.expenseTypeId == nil ? .amber600 : .warm500)

                    // Flag indicator
                    if transaction.needsReview {
                        Spacer()
                        FlagIndicator(flags: transaction.flags)
                    }
                }
            }

            Spacer()

            // Amount & Date
            VStack(alignment: .trailing, spacing: Spacing.xxxs) {
                Text(formattedAmount)
                    .font(.amountSmall)
                    .foregroundColor(textColor)

                Text(transaction.displayDate)
                    .font(.labelSmall)
                    .foregroundColor(.warm400)
            }
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
        .background(transaction.needsReview ? Color.amber100.opacity(0.5) : Color.clear)
        .opacity(transaction.status == .imported ? 0.6 : 1.0)
        .overlay(alignment: .bottom) {
            if !isLast {
                Divider()
                    .padding(.leading, 44)
            }
        }
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var splitDisplayName: String {
        switch transaction.splitCategory {
        case "SHARED": return "Shared"
        case "MINE": return "Mine"
        case "PARTNER": return "Partner's"
        default: return transaction.splitCategory
        }
    }

    private var formattedAmount: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = transaction.currency
        return formatter.string(from: NSNumber(value: transaction.amount)) ?? "$\(transaction.amount)"
    }
}

// MARK: - Flag Indicator

private struct FlagIndicator: View {
    let flags: [String]

    var body: some View {
        HStack(spacing: Spacing.xxs) {
            Image(systemName: iconName)
                .font(.system(size: 10))

            Text(displayText)
                .font(.labelSmall)
        }
        .foregroundColor(flagColor)
        .padding(.horizontal, Spacing.xs)
        .padding(.vertical, Spacing.xxxs)
        .background(flagColor.opacity(0.15))
        .cornerRadius(CornerRadius.small)
    }

    private var iconName: String {
        if flags.contains("ocr_failure") { return "exclamationmark.triangle" }
        if flags.contains("low_confidence") { return "questionmark.circle" }
        if flags.contains("uncertain_category") { return "tag" }
        if flags.contains("potential_duplicate") { return "doc.on.doc" }
        return "exclamationmark.circle"
    }

    private var displayText: String {
        if flags.contains("ocr_failure") { return "OCR" }
        if flags.contains("low_confidence") { return "Low" }
        if flags.contains("uncertain_category") { return "?" }
        if flags.contains("potential_duplicate") { return "Dup?" }
        return "Review"
    }

    private var flagColor: Color {
        if flags.contains("ocr_failure") { return .rose500 }
        if flags.contains("potential_duplicate") { return .amber500 }
        return .amber500
    }
}

#Preview {
    NavigationStack {
        BankImportSelectView(viewModel: BankImportViewModel(), sessionId: 1)
    }
}
