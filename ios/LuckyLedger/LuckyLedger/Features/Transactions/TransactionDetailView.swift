import SwiftUI
import PhotosUI

struct TransactionDetailView: View {
    let transaction: Transaction
    let onUpdate: (Transaction) -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var isUploadingReceipt = false
    @State private var showReceiptFullScreen = false
    @State private var error: String?
    @State private var currentTransaction: Transaction

    private let network = NetworkManager.shared

    init(transaction: Transaction, onUpdate: @escaping (Transaction) -> Void) {
        self.transaction = transaction
        self.onUpdate = onUpdate
        self._currentTransaction = State(initialValue: transaction)
    }

    var body: some View {
        NavigationStack {
            List {
                // Transaction Details Section
                Section("Details") {
                    LabeledContent("Merchant", value: currentTransaction.merchant)
                    LabeledContent("Amount") {
                        Text(String(format: "$%.2f %@", currentTransaction.amount, currentTransaction.currency))
                    }
                    LabeledContent("Date", value: currentTransaction.date)
                    LabeledContent("Paid By", value: currentTransaction.paidByName ?? "Unknown")
                    if let expenseType = currentTransaction.expenseTypeName {
                        LabeledContent("Category", value: expenseType)
                    }
                    if let notes = currentTransaction.notes, !notes.isEmpty {
                        LabeledContent("Notes", value: notes)
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
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
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
        onUpdate: { _ in }
    )
}
