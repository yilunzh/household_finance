import SwiftUI
import PhotosUI

struct TransactionDetailView: View {
    let transaction: Transaction
    @Bindable var viewModel: TransactionsViewModel
    let onUpdate: (Transaction) -> Void

    @Environment(\.dismiss) private var dismiss
    @Environment(AuthManager.self) private var authManager

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

    var body: some View {
        NavigationStack {
            List {
                // Transaction Details Section
                Section("Details") {
                    if isEditing {
                        // Editable fields
                        TextField("Merchant", text: $editMerchant)

                        HStack {
                            TextField("Amount", text: $editAmount)
                                .keyboardType(.decimalPad)
                            Picker("Currency", selection: $editCurrency) {
                                ForEach(currencies, id: \.self) { currency in
                                    Text(currency).tag(currency)
                                }
                            }
                            .pickerStyle(.menu)
                        }

                        DatePicker("Date", selection: $editDate, displayedComponents: .date)

                        Picker("Category", selection: $editCategory) {
                            Text("Select...").tag(nil as TransactionCategory?)
                            ForEach(viewModel.categories) { category in
                                Text(category.name).tag(category as TransactionCategory?)
                            }
                        }

                        if !viewModel.expenseTypes.isEmpty {
                            Picker("Expense Type", selection: $editExpenseType) {
                                Text("None").tag(nil as ExpenseType?)
                                ForEach(viewModel.expenseTypes) { expenseType in
                                    Text(expenseType.name).tag(expenseType as ExpenseType?)
                                }
                            }
                        }

                        Picker("Paid By", selection: $editPaidBy) {
                            Text("Select...").tag(nil as HouseholdMember?)
                            ForEach(viewModel.members) { member in
                                Text(member.displayName).tag(member as HouseholdMember?)
                            }
                        }

                        TextField("Notes (optional)", text: $editNotes, axis: .vertical)
                            .lineLimit(3...6)
                    } else {
                        // Read-only view
                        LabeledContent("Merchant", value: currentTransaction.merchant)
                        LabeledContent("Amount") {
                            Text(String(format: "$%.2f %@", currentTransaction.amount, currentTransaction.currency))
                        }
                        LabeledContent("Date", value: currentTransaction.date)
                        LabeledContent("Paid By", value: currentTransaction.paidByName ?? "Unknown")
                        if let expenseType = currentTransaction.expenseTypeName {
                            LabeledContent("Expense Type", value: expenseType)
                        }
                        LabeledContent("Category", value: categoryDisplayName)
                        if let notes = currentTransaction.notes, !notes.isEmpty {
                            LabeledContent("Notes", value: notes)
                        }
                    }
                }

                // Receipt Section
                Section("Receipt") {
                    if let receiptUrl = currentTransaction.receiptUrl {
                        // Show receipt thumbnail
                        Button {
                            showReceiptFullScreen = true
                        } label: {
                            HStack {
                                AsyncImage(url: currentTransaction.fullReceiptUrl) { phase in
                                    switch phase {
                                    case .empty:
                                        ProgressView()
                                            .frame(width: 60, height: 60)
                                    case .success(let image):
                                        image
                                            .resizable()
                                            .aspectRatio(contentMode: .fill)
                                            .frame(width: 60, height: 60)
                                            .clipShape(RoundedRectangle(cornerRadius: 8))
                                    case .failure:
                                        Image(systemName: "photo")
                                            .frame(width: 60, height: 60)
                                            .foregroundStyle(.secondary)
                                    @unknown default:
                                        EmptyView()
                                    }
                                }

                                VStack(alignment: .leading) {
                                    Text("View Receipt")
                                        .foregroundStyle(.primary)
                                    Text("Tap to view full size")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }

                                Spacer()

                                Image(systemName: "chevron.right")
                                    .foregroundStyle(.secondary)
                            }
                        }

                        Button(role: .destructive) {
                            Task {
                                await deleteReceipt()
                            }
                        } label: {
                            Label("Remove Receipt", systemImage: "trash")
                        }
                    } else {
                        // Photo picker for adding receipt
                        PhotosPicker(selection: $selectedPhotoItem, matching: .images) {
                            Label(
                                isUploadingReceipt ? "Uploading..." : "Add Receipt Photo",
                                systemImage: isUploadingReceipt ? "arrow.up.circle" : "camera"
                            )
                        }
                        .disabled(isUploadingReceipt)
                    }
                }

                if let error = error {
                    Section {
                        Text(error)
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Transaction")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if isEditing {
                        Button("Cancel") {
                            isEditing = false
                        }
                        .disabled(isSaving)
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    if isEditing {
                        Button("Save") {
                            Task {
                                await saveTransaction()
                            }
                        }
                        .disabled(!isEditFormValid || isSaving)
                    } else {
                        HStack {
                            Button("Edit") {
                                startEditing()
                            }
                            Button("Done") {
                                dismiss()
                            }
                        }
                    }
                }
            }
            .interactiveDismissDisabled(isEditing || isSaving)
            .onChange(of: selectedPhotoItem) { _, newValue in
                if let newValue {
                    Task {
                        await uploadReceipt(from: newValue)
                    }
                }
            }
            .fullScreenCover(isPresented: $showReceiptFullScreen) {
                ReceiptFullScreenView(url: currentTransaction.fullReceiptUrl)
            }
        }
    }

    private func uploadReceipt(from item: PhotosPickerItem) async {
        isUploadingReceipt = true
        error = nil
        defer { isUploadingReceipt = false }

        do {
            // Load image data
            guard let data = try await item.loadTransferable(type: Data.self) else {
                error = "Could not load image"
                return
            }

            // Convert to UIImage and compress
            guard let image = UIImage(data: data),
                  let compressedData = ImageCompressor.compress(image) else {
                error = "Could not process image"
                return
            }

            // Upload
            let filename = "receipt_\(currentTransaction.id).jpg"
            let updatedTransaction = try await network.uploadReceipt(
                transactionId: currentTransaction.id,
                imageData: compressedData,
                filename: filename
            )

            currentTransaction = updatedTransaction
            onUpdate(updatedTransaction)
            selectedPhotoItem = nil

        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
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
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
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
        // Populate edit fields with current values
        editMerchant = currentTransaction.merchant
        editAmount = String(format: "%.2f", currentTransaction.amount)
        editCurrency = currentTransaction.currency
        editNotes = currentTransaction.notes ?? ""

        // Parse date
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        editDate = dateFormatter.date(from: currentTransaction.date) ?? Date()

        // Find matching category
        editCategory = viewModel.categories.first { $0.code == currentTransaction.category }

        // Find matching expense type
        if let expenseTypeId = currentTransaction.expenseTypeId {
            editExpenseType = viewModel.expenseTypes.first { $0.id == expenseTypeId }
        } else {
            editExpenseType = nil
        }

        // Find matching paid by member
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
              let paidBy = editPaidBy else {
            return
        }

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
            // Update the current transaction display
            if let index = viewModel.transactions.firstIndex(where: { $0.id == currentTransaction.id }) {
                currentTransaction = viewModel.transactions[index]
                onUpdate(currentTransaction)
            }
            isEditing = false
        } else {
            error = viewModel.error
        }
    }
}

struct ReceiptFullScreenView: View {
    let url: URL?

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            GeometryReader { geometry in
                if let url = url {
                    AsyncImage(url: url) { phase in
                        switch phase {
                        case .empty:
                            ProgressView()
                                .frame(maxWidth: .infinity, maxHeight: .infinity)
                        case .success(let image):
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fit)
                                .frame(width: geometry.size.width, height: geometry.size.height)
                        case .failure:
                            VStack {
                                Image(systemName: "exclamationmark.triangle")
                                    .font(.largeTitle)
                                Text("Failed to load receipt")
                            }
                            .foregroundStyle(.secondary)
                        @unknown default:
                            EmptyView()
                        }
                    }
                } else {
                    Text("No receipt URL")
                        .foregroundStyle(.secondary)
                }
            }
            .background(Color.black)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                    .tint(.white)
                }
            }
            .toolbarBackground(.black, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
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
