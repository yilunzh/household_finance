import SwiftUI

struct BankImportSelectView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @Bindable var viewModel: BankImportViewModel
    let sessionId: Int

    @State private var showCategorize = false
    @State private var showImportConfirm = false
    @State private var showSuccess = false
    @State private var importedCount = 0

    var body: some View {
        VStack(spacing: 0) {
            // Tab bar
            TabBarHeader(selectedTab: $viewModel.selectedTab)

            // Content
            ZStack {
                backgroundColor.ignoresSafeArea()

                if viewModel.isLoading && viewModel.transactions.isEmpty {
                    ProgressView()
                        .scaleEffect(1.2)
                } else if viewModel.currentTabTransactions.isEmpty {
                    EmptyTabState(tab: viewModel.selectedTab)
                } else {
                    ScrollView {
                        LazyVStack(spacing: Spacing.sm) {
                            ForEach(viewModel.currentTabTransactions) { transaction in
                                TransactionRow(
                                    transaction: transaction,
                                    expenseTypes: viewModel.expenseTypes,
                                    onToggle: {
                                        Task {
                                            await viewModel.toggleSelection(transaction)
                                        }
                                    },
                                    onEdit: {
                                        // TODO: Show edit sheet
                                    }
                                )
                            }
                        }
                        .padding(Spacing.md)
                    }
                }
            }

            // Footer
            ImportFooter(
                selectedCount: viewModel.selectedCount,
                needsAttentionCount: viewModel.needsAttentionTransactions.count,
                isImporting: viewModel.isImporting,
                onReview: { showCategorize = true },
                onImport: { showImportConfirm = true }
            )
        }
        .navigationTitle("Review Transactions")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Menu {
                    Button {
                        Task { await viewModel.selectAll(true) }
                    } label: {
                        Label("Select All", systemImage: "checkmark.circle")
                    }

                    Button {
                        Task { await viewModel.selectAll(false) }
                    } label: {
                        Label("Deselect All", systemImage: "circle")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .foregroundColor(.brandPrimary)
                }
            }
        }
        .task {
            await viewModel.loadConfig()
            await viewModel.loadSession(sessionId)
        }
        .sheet(isPresented: $showCategorize) {
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

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

// MARK: - Tab Bar Header

struct TabBarHeader: View {
    @Binding var selectedTab: BankImportViewModel.TransactionTab

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: Spacing.xs) {
                ForEach(BankImportViewModel.TransactionTab.allCases, id: \.self) { tab in
                    TabButton(tab: tab, isSelected: selectedTab == tab) {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            selectedTab = tab
                        }
                    }
                }
            }
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
        }
        .background(Color.backgroundSecondary)
    }
}

struct TabButton: View {
    let tab: BankImportViewModel.TransactionTab
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: Spacing.xxs) {
                Image(systemName: tab.systemImage)
                    .font(.system(size: 12))

                Text(tab.rawValue)
                    .font(.labelMedium)
            }
            .foregroundColor(isSelected ? .white : .textSecondary)
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, Spacing.xs)
            .background(isSelected ? Color.terracotta500 : Color.clear)
            .cornerRadius(CornerRadius.full)
        }
    }
}

// MARK: - Empty Tab State

struct EmptyTabState: View {
    let tab: BankImportViewModel.TransactionTab

    var body: some View {
        VStack(spacing: Spacing.md) {
            Image(systemName: tab.systemImage)
                .font(.system(size: 48))
                .foregroundColor(.textTertiary)

            Text(emptyMessage)
                .font(.bodyMedium)
                .foregroundColor(.textSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(Spacing.xl)
    }

    private var emptyMessage: String {
        switch tab {
        case .ready:
            return "No transactions ready to import.\nReview items in \"Needs Attention\" first."
        case .needsAttention:
            return "All transactions have been reviewed!"
        case .skipped:
            return "No skipped transactions."
        case .imported:
            return "No transactions imported yet."
        }
    }
}

// MARK: - Transaction Row

struct TransactionRow: View {
    let transaction: ExtractedTransaction
    let expenseTypes: [ExpenseType]
    let onToggle: () -> Void
    let onEdit: () -> Void

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.sm) {
            // Checkbox
            Button(action: onToggle) {
                Image(systemName: transaction.isSelected ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 24))
                    .foregroundColor(transaction.isSelected ? .terracotta500 : .warm300)
            }
            .disabled(transaction.status == .imported)

            // Main content
            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                HStack {
                    Text(transaction.merchant)
                        .font(.bodyLarge)
                        .foregroundColor(textColor)
                        .lineLimit(1)

                    Spacer()

                    Text(formattedAmount)
                        .font(.labelLarge)
                        .foregroundColor(textColor)
                }

                HStack(spacing: Spacing.xs) {
                    // Date
                    Text(transaction.displayDate)
                        .font(.labelSmall)
                        .foregroundColor(.textTertiary)

                    if let typeName = transaction.expenseTypeName ?? expenseTypes.first(where: { $0.id == transaction.expenseTypeId })?.name {
                        Text("•")
                            .foregroundColor(.textTertiary)

                        Text(typeName)
                            .font(.labelSmall)
                            .foregroundColor(.textSecondary)
                    }

                    // Flags
                    if transaction.needsReview {
                        Spacer()
                        FlagBadge(flags: transaction.flags)
                    }
                }
            }

            // Edit button (for items that need review)
            if transaction.needsReview && transaction.status != .imported {
                Button(action: onEdit) {
                    Image(systemName: "pencil.circle")
                        .font(.system(size: 20))
                        .foregroundColor(.terracotta500)
                }
            }
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.medium)
        .opacity(transaction.status == .imported ? 0.6 : 1.0)
    }

    private var formattedAmount: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = transaction.currency
        return formatter.string(from: NSNumber(value: transaction.amount)) ?? "$\(transaction.amount)"
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundCard
    }
}

// MARK: - Flag Badge

struct FlagBadge: View {
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
        if flags.contains("ocr_failure") { return "OCR Issue" }
        if flags.contains("low_confidence") { return "Low Confidence" }
        if flags.contains("uncertain_category") { return "Uncategorized" }
        if flags.contains("potential_duplicate") { return "Duplicate?" }
        return "Review"
    }

    private var flagColor: Color {
        if flags.contains("ocr_failure") { return .rose500 }
        if flags.contains("potential_duplicate") { return .amber500 }
        return .amber500
    }
}

// MARK: - Import Footer

struct ImportFooter: View {
    let selectedCount: Int
    let needsAttentionCount: Int
    let isImporting: Bool
    let onReview: () -> Void
    let onImport: () -> Void

    var body: some View {
        VStack(spacing: Spacing.sm) {
            Divider()

            HStack(spacing: Spacing.md) {
                if needsAttentionCount > 0 {
                    Button(action: onReview) {
                        HStack(spacing: Spacing.xs) {
                            Image(systemName: "exclamationmark.circle")
                            Text("Review \(needsAttentionCount)")
                        }
                        .font(.labelMedium)
                        .foregroundColor(.amber600)
                        .padding(.horizontal, Spacing.md)
                        .padding(.vertical, Spacing.sm)
                        .background(Color.amber100)
                        .cornerRadius(CornerRadius.medium)
                    }
                }

                Spacer()

                Button(action: onImport) {
                    HStack(spacing: Spacing.xs) {
                        if isImporting {
                            ProgressView()
                                .scaleEffect(0.8)
                                .tint(.white)
                        } else {
                            Image(systemName: "arrow.down.doc")
                        }
                        Text("Import \(selectedCount)")
                    }
                    .font(.labelLarge)
                    .foregroundColor(.white)
                    .padding(.horizontal, Spacing.lg)
                    .padding(.vertical, Spacing.sm)
                    .background(selectedCount > 0 ? Color.terracotta500 : Color.warm300)
                    .cornerRadius(CornerRadius.medium)
                }
                .disabled(selectedCount == 0 || isImporting)
            }
            .padding(.horizontal, Spacing.md)
            .padding(.bottom, Spacing.md)
        }
        .background(Color.backgroundCard)
    }
}

#Preview {
    NavigationStack {
        BankImportSelectView(viewModel: BankImportViewModel(), sessionId: 1)
    }
}
