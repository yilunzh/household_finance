import SwiftUI
import PhotosUI

struct TransactionDetailView: View {
    let transaction: Transaction
    @Bindable var viewModel: TransactionsViewModel
    let onUpdate: (Transaction) -> Void

    @Environment(\.dismiss) private var dismiss
    @Environment(AuthManager.self) private var authManager
    @Environment(\.colorScheme) private var colorScheme

    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var isUploadingReceipt = false
    @State private var showReceiptFullScreen = false
    @State private var error: String?
    @State private var currentTransaction: Transaction

    // Edit mode state
    @State private var isEditing = false
    @State private var isSaving = false
    @State private var editMerchant: String = ""
    @State private var editAmount: String = ""
    @State private var editCurrency: String = "USD"
    @State private var editDate: Date = Date()
    @State private var editCategory: TransactionCategory?
    @State private var editExpenseType: ExpenseType?
    @State private var editPaidBy: HouseholdMember?
    @State private var editNotes: String = ""

    private let network = NetworkManager.shared
    private let currencies = ["USD", "CAD"]

    init(transaction: Transaction, viewModel: TransactionsViewModel, onUpdate: @escaping (Transaction) -> Void) {
        self.transaction = transaction
        self.viewModel = viewModel
        self.onUpdate = onUpdate
        self._currentTransaction = State(initialValue: transaction)
    }

    // MARK: - Computed Properties

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    amountHeader
                    detailsCard
                    notesCard
                    receiptCard
                    errorDisplay
                    saveButton
                }
                .padding(Spacing.md)
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle(isEditing ? "Edit Transaction" : "Transaction")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { toolbarContent }
            .interactiveDismissDisabled(isEditing || isSaving)
            .onChange(of: selectedPhotoItem) { _, newValue in
                if let newValue {
                    Task { await uploadReceipt(from: newValue) }
                }
            }
            .fullScreenCover(isPresented: $showReceiptFullScreen) {
                ReceiptFullScreenView(url: currentTransaction.fullReceiptUrl)
            }
        }
    }

    // MARK: - View Components

    @ViewBuilder
    private var amountHeader: some View {
        VStack(spacing: Spacing.xs) {
            if isEditing {
                editableAmountView
            } else {
                readOnlyAmountView
            }
        }
        .padding(Spacing.lg)
        .frame(maxWidth: .infinity)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
    }

    @ViewBuilder
    private var editableAmountView: some View {
        HStack(spacing: Spacing.md) {
            currencyMenu
            TextField("0.00", text: $editAmount)
                .keyboardType(.decimalPad)
                .font(.amountLarge)
                .foregroundColor(textColor)
                .multilineTextAlignment(.trailing)
        }
    }

    @ViewBuilder
    private var currencyMenu: some View {
        Menu {
            ForEach(currencies, id: \.self) { curr in
                Button {
                    HapticManager.selection()
                    editCurrency = curr
                } label: {
                    HStack {
                        Text(curr)
                        if editCurrency == curr {
                            Image(systemName: "checkmark")
                        }
                    }
                }
            }
        } label: {
            HStack(spacing: Spacing.xxs) {
                Text(editCurrency)
                    .font(.labelLarge)
                    .foregroundColor(.brandPrimary)
                Image(systemName: "chevron.down")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.brandPrimary)
            }
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, Spacing.xs)
            .background(Color.terracotta100)
            .cornerRadius(CornerRadius.medium)
        }
    }

    @ViewBuilder
    private var readOnlyAmountView: some View {
        Text(String(format: "$%.2f", currentTransaction.amount))
            .font(.amountLarge)
            .foregroundColor(textColor)

        Text(currentTransaction.currency)
            .font(.labelMedium)
            .foregroundColor(.textSecondary)
    }

    @ViewBuilder
    private var detailsCard: some View {
        VStack(spacing: Spacing.md) {
            Text("Details")
                .font(.labelMedium)
                .foregroundColor(.textSecondary)
                .frame(maxWidth: .infinity, alignment: .leading)

            VStack(spacing: Spacing.sm) {
                if isEditing {
                    editableDetailsContent
                } else {
                    readOnlyDetailsContent
                }
            }
            .padding(Spacing.md)
            .background(cardBackground)
            .cornerRadius(CornerRadius.large)
            .subtleShadow()
        }
    }

    @ViewBuilder
    private var editableDetailsContent: some View {
        merchantField
        Divider().background(Color.warm200)
        dateField
        Divider().background(Color.warm200)
        categoryField
        expenseTypeField
        Divider().background(Color.warm200)
        paidByField
    }

    @ViewBuilder
    private var merchantField: some View {
        DetailFormField(icon: .ledger, label: "Merchant") {
            TextField("Where did you spend?", text: $editMerchant)
                .font(.bodyLarge)
                .foregroundColor(textColor)
        }
    }

    @ViewBuilder
    private var dateField: some View {
        DetailFormField(icon: .calendar, label: "Date") {
            DatePicker("", selection: $editDate, displayedComponents: .date)
                .labelsHidden()
                .tint(.brandPrimary)
        }
    }

    @ViewBuilder
    private var categoryField: some View {
        DetailFormField(icon: .highfive, label: "Category") {
            Menu {
                ForEach(viewModel.categories) { category in
                    Button {
                        HapticManager.selection()
                        editCategory = category
                    } label: {
                        HStack {
                            Text(category.name)
                            if editCategory?.id == category.id {
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                }
            } label: {
                HStack {
                    Text(editCategory?.name ?? "Select...")
                        .font(.bodyLarge)
                        .foregroundColor(editCategory == nil ? .textTertiary : textColor)
                    Spacer()
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.system(size: 12))
                        .foregroundColor(.warm400)
                }
            }
        }
    }

    @ViewBuilder
    private var expenseTypeField: some View {
        if !viewModel.expenseTypes.isEmpty {
            Divider().background(Color.warm200)

            DetailFormField(icon: .clipboard, label: "Expense Type") {
                Menu {
                    Button {
                        HapticManager.selection()
                        editExpenseType = nil
                    } label: {
                        HStack {
                            Text("None")
                            if editExpenseType == nil {
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                    ForEach(viewModel.expenseTypes) { expenseType in
                        Button {
                            HapticManager.selection()
                            editExpenseType = expenseType
                        } label: {
                            HStack {
                                Text(expenseType.name)
                                if editExpenseType?.id == expenseType.id {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                    }
                } label: {
                    HStack {
                        Text(editExpenseType?.name ?? "None")
                            .font(.bodyLarge)
                            .foregroundColor(editExpenseType == nil ? .textTertiary : textColor)
                        Spacer()
                        Image(systemName: "chevron.up.chevron.down")
                            .font(.system(size: 12))
                            .foregroundColor(.warm400)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var paidByField: some View {
        DetailFormField(icon: .happy, label: "Paid By") {
            Menu {
                ForEach(viewModel.members) { member in
                    Button {
                        HapticManager.selection()
                        editPaidBy = member
                    } label: {
                        HStack {
                            Text(member.displayName)
                            if editPaidBy?.id == member.id {
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                }
            } label: {
                HStack {
                    Text(editPaidBy?.displayName ?? "Select...")
                        .font(.bodyLarge)
                        .foregroundColor(editPaidBy == nil ? .textTertiary : textColor)
                    Spacer()
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.system(size: 12))
                        .foregroundColor(.warm400)
                }
            }
        }
    }

    @ViewBuilder
    private var readOnlyDetailsContent: some View {
        DetailRow(icon: .ledger, label: "Merchant", value: currentTransaction.merchant)
        Divider().background(Color.warm200)
        DetailRow(icon: .calendar, label: "Date", value: currentTransaction.date)
        Divider().background(Color.warm200)
        DetailRow(icon: .happy, label: "Paid By", value: currentTransaction.paidByName ?? "Unknown")
        Divider().background(Color.warm200)
        DetailRow(icon: .highfive, label: "Category", value: categoryDisplayName)
        if let expenseType = currentTransaction.expenseTypeName {
            Divider().background(Color.warm200)
            DetailRow(icon: .clipboard, label: "Expense Type", value: expenseType)
        }
    }

    @ViewBuilder
    private var notesCard: some View {
        if isEditing || (currentTransaction.notes != nil && !currentTransaction.notes!.isEmpty) {
            VStack(spacing: Spacing.md) {
                Text("Notes")
                    .font(.labelMedium)
                    .foregroundColor(.textSecondary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                HStack(alignment: .top, spacing: Spacing.sm) {
                    CatIcon(name: .pencil, size: .sm, color: .warm400)
                        .padding(.top, Spacing.xxs)

                    if isEditing {
                        TextField("Add notes (optional)", text: $editNotes, axis: .vertical)
                            .font(.bodyLarge)
                            .foregroundColor(textColor)
                            .lineLimit(3...6)
                    } else {
                        Text(currentTransaction.notes ?? "")
                            .font(.bodyLarge)
                            .foregroundColor(textColor)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(Spacing.md)
                .background(cardBackground)
                .cornerRadius(CornerRadius.large)
                .subtleShadow()
            }
        }
    }

    @ViewBuilder
    private var receiptCard: some View {
        VStack(spacing: Spacing.md) {
            Text("Receipt")
                .font(.labelMedium)
                .foregroundColor(.textSecondary)
                .frame(maxWidth: .infinity, alignment: .leading)

            VStack(spacing: Spacing.sm) {
                if currentTransaction.receiptUrl != nil {
                    receiptThumbnail
                    Divider().background(Color.warm200)
                    removeReceiptButton
                } else {
                    addReceiptPicker
                }
            }
            .padding(Spacing.md)
            .background(cardBackground)
            .cornerRadius(CornerRadius.large)
            .subtleShadow()
        }
    }

    @ViewBuilder
    private var receiptThumbnail: some View {
        Button {
            HapticManager.buttonTap()
            showReceiptFullScreen = true
        } label: {
            HStack(spacing: Spacing.md) {
                AsyncImage(url: currentTransaction.fullReceiptUrl) { phase in
                    switch phase {
                    case .empty:
                        ProgressView().frame(width: 60, height: 60)
                    case .success(let image):
                        image.resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 60, height: 60)
                            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.medium))
                    case .failure:
                        CatIcon(name: .worried, size: .lg, color: .warm400)
                            .frame(width: 60, height: 60)
                    @unknown default:
                        EmptyView()
                    }
                }

                VStack(alignment: .leading, spacing: Spacing.xxxs) {
                    Text("View Receipt")
                        .font(.bodyLarge)
                        .foregroundColor(textColor)
                    Text("Tap to view full size")
                        .font(.labelSmall)
                        .foregroundColor(.textTertiary)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.warm400)
            }
        }
    }

    @ViewBuilder
    private var removeReceiptButton: some View {
        Button {
            HapticManager.buttonTap()
            Task { await deleteReceipt() }
        } label: {
            HStack(spacing: Spacing.sm) {
                CatIcon(name: .trash, size: .sm, color: .danger)
                Text("Remove Receipt")
                    .font(.bodyMedium)
                    .foregroundColor(.danger)
                Spacer()
            }
        }
    }

    @ViewBuilder
    private var addReceiptPicker: some View {
        PhotosPicker(selection: $selectedPhotoItem, matching: .images) {
            HStack(spacing: Spacing.sm) {
                if isUploadingReceipt {
                    ProgressView().frame(width: 20, height: 20)
                } else {
                    CatIcon(name: .plus, size: .sm, color: .brandPrimary)
                }
                Text(isUploadingReceipt ? "Uploading..." : "Add Receipt Photo")
                    .font(.bodyMedium)
                    .foregroundColor(.brandPrimary)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.warm400)
            }
        }
        .disabled(isUploadingReceipt)
    }

    @ViewBuilder
    private var errorDisplay: some View {
        if let error = error {
            HStack(spacing: Spacing.sm) {
                CatIcon(name: .worried, size: .sm, color: .danger)
                Text(error)
                    .font(.labelMedium)
                    .foregroundColor(.danger)
            }
            .padding(Spacing.md)
            .frame(maxWidth: .infinity)
            .background(Color.rose50)
            .cornerRadius(CornerRadius.medium)
        }
    }

    @ViewBuilder
    private var saveButton: some View {
        if isEditing {
            PrimaryButton(
                title: "Save Changes",
                icon: .sparkle,
                action: { Task { await saveTransaction() } },
                isLoading: isSaving,
                isDisabled: !isEditFormValid
            )
        }
    }

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .cancellationAction) {
            if isEditing {
                Button {
                    HapticManager.buttonTap()
                    isEditing = false
                } label: {
                    Text("Cancel").foregroundColor(.brandPrimary)
                }
                .disabled(isSaving)
            }
        }

        ToolbarItem(placement: .primaryAction) {
            if !isEditing {
                HStack(spacing: Spacing.sm) {
                    Button {
                        HapticManager.buttonTap()
                        startEditing()
                    } label: {
                        CatIcon(name: .pencil, size: .sm, color: .brandPrimary)
                    }
                    Button {
                        HapticManager.buttonTap()
                        dismiss()
                    } label: {
                        Text("Done").foregroundColor(.brandPrimary)
                    }
                }
            }
        }
    }

    // MARK: - Actions

    private func uploadReceipt(from item: PhotosPickerItem) async {
        isUploadingReceipt = true
        error = nil
        defer { isUploadingReceipt = false }

        do {
            guard let data = try await item.loadTransferable(type: Data.self) else {
                error = "Could not load image"
                HapticManager.error()
                return
            }

            guard let image = UIImage(data: data),
                  let compressedData = ImageCompressor.compress(image) else {
                error = "Could not process image"
                HapticManager.error()
                return
            }

            let filename = "receipt_\(currentTransaction.id).jpg"
            let updatedTransaction = try await network.uploadReceipt(
                transactionId: currentTransaction.id,
                imageData: compressedData,
                filename: filename
            )

            currentTransaction = updatedTransaction
            onUpdate(updatedTransaction)
            selectedPhotoItem = nil
            HapticManager.success()

        } catch let apiError as APIError {
            error = apiError.errorDescription
            HapticManager.error()
        } catch {
            self.error = error.localizedDescription
            HapticManager.error()
        }
    }

    private func deleteReceipt() async {
        isUploadingReceipt = true
        error = nil
        defer { isUploadingReceipt = false }

        do {
            let updatedTransaction = try await network.deleteReceipt(transactionId: currentTransaction.id)
            currentTransaction = updatedTransaction
            onUpdate(updatedTransaction)
            HapticManager.success()
        } catch let apiError as APIError {
            error = apiError.errorDescription
            HapticManager.error()
        } catch {
            self.error = error.localizedDescription
            HapticManager.error()
        }
    }

    // MARK: - Edit Mode Helpers

    private var categoryDisplayName: String {
        switch currentTransaction.category {
        case "SHARED": return "Shared"
        case "I_PAY_FOR_WIFE": return "I pay for partner"
        case "WIFE_PAYS_FOR_ME": return "Partner pays for me"
        case "PERSONAL_ME": return "Personal (me)"
        case "PERSONAL_WIFE": return "Personal (partner)"
        default: return currentTransaction.category
        }
    }

    private var isEditFormValid: Bool {
        guard let amount = Double(editAmount), amount > 0 else { return false }
        return !editMerchant.trimmingCharacters(in: .whitespaces).isEmpty
            && editCategory != nil
            && editPaidBy != nil
    }

    private func startEditing() {
        HapticManager.buttonTap()
        editMerchant = currentTransaction.merchant
        editAmount = String(format: "%.2f", currentTransaction.amount)
        editCurrency = currentTransaction.currency
        editNotes = currentTransaction.notes ?? ""

        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        editDate = dateFormatter.date(from: currentTransaction.date) ?? Date()

        editCategory = viewModel.categories.first { $0.code == currentTransaction.category }

        if let expenseTypeId = currentTransaction.expenseTypeId {
            editExpenseType = viewModel.expenseTypes.first { $0.id == expenseTypeId }
        } else {
            editExpenseType = nil
        }

        if let paidByUserId = currentTransaction.paidByUserId {
            editPaidBy = viewModel.members.first { $0.userId == paidByUserId }
        } else {
            editPaidBy = nil
        }

        isEditing = true
    }

    private func saveTransaction() async {
        guard let amount = Double(editAmount),
              let category = editCategory,
              let paidBy = editPaidBy else { return }

        HapticManager.buttonTap()
        isSaving = true
        error = nil
        defer { isSaving = false }

        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        let dateString = dateFormatter.string(from: editDate)

        let request = CreateTransactionRequest(
            amount: amount,
            currency: editCurrency,
            merchant: editMerchant.trimmingCharacters(in: .whitespaces),
            category: category.code,
            date: dateString,
            paidBy: paidBy.userId,
            expenseTypeId: editExpenseType?.id,
            notes: editNotes.isEmpty ? nil : editNotes
        )

        let success = await viewModel.updateTransaction(currentTransaction.id, request: request)

        if success {
            HapticManager.success()
            if let index = viewModel.transactions.firstIndex(where: { $0.id == currentTransaction.id }) {
                currentTransaction = viewModel.transactions[index]
                onUpdate(currentTransaction)
            }
            isEditing = false
        } else {
            HapticManager.error()
            error = viewModel.error
        }
    }
}

// MARK: - Detail Form Field

private struct DetailFormField<Content: View>: View {
    let icon: CatIcon.Name
    let label: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        HStack(spacing: Spacing.sm) {
            CatIcon(name: icon, size: .sm, color: .warm400)
            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(label)
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)
                content()
            }
        }
    }
}

// MARK: - Detail Row

private struct DetailRow: View {
    let icon: CatIcon.Name
    let label: String
    let value: String

    @Environment(\.colorScheme) private var colorScheme

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    var body: some View {
        HStack(spacing: Spacing.sm) {
            CatIcon(name: icon, size: .sm, color: .warm400)
            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(label)
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)
                Text(value)
                    .font(.bodyLarge)
                    .foregroundColor(textColor)
            }
            Spacer()
        }
    }
}

// MARK: - Receipt Full Screen View

struct ReceiptFullScreenView: View {
    let url: URL?

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            GeometryReader { geometry in
                receiptContent(geometry: geometry)
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        HapticManager.buttonTap()
                        dismiss()
                    } label: {
                        Text("Done")
                            .font(.labelLarge)
                            .foregroundColor(.white)
                    }
                }
            }
            .toolbarBackground(.black, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }

    @ViewBuilder
    private func receiptContent(geometry: GeometryProxy) -> some View {
        if let url = url {
            AsyncImage(url: url) { phase in
                switch phase {
                case .empty:
                    loadingView
                case .success(let image):
                    image.resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: geometry.size.width, height: geometry.size.height)
                case .failure:
                    errorView
                @unknown default:
                    EmptyView()
                }
            }
        } else {
            noReceiptView
        }
    }

    private var loadingView: some View {
        VStack(spacing: Spacing.md) {
            ProgressView().tint(.white)
            Text("Loading receipt...")
                .font(.labelMedium)
                .foregroundColor(.white.opacity(0.7))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var errorView: some View {
        VStack(spacing: Spacing.md) {
            CatIcon(name: .worried, size: .xxl, color: .white.opacity(0.7))
            Text("Failed to load receipt")
                .font(.bodyLarge)
                .foregroundColor(.white.opacity(0.7))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var noReceiptView: some View {
        VStack(spacing: Spacing.md) {
            CatIcon(name: .sleeping, size: .xxl, color: .white.opacity(0.7))
            Text("No receipt available")
                .font(.bodyLarge)
                .foregroundColor(.white.opacity(0.7))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

#Preview {
    TransactionDetailView(
        transaction: Transaction(
            id: 1,
            householdId: 1,
            amount: 50.00,
            amountInUsd: 50.00,
            currency: "USD",
            merchant: "Test Merchant",
            category: "SHARED",
            date: "2024-01-15",
            monthYear: "2024-01",
            notes: "Test notes",
            paidByUserId: 1,
            paidByName: "Alice",
            expenseTypeId: 1,
            expenseTypeName: "Grocery",
            receiptUrl: nil,
            createdAt: "2024-01-15 10:00:00"
        ),
        viewModel: TransactionsViewModel(),
        onUpdate: { _ in }
    )
    .environment(AuthManager())
}
