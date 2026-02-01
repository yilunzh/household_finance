import SwiftUI
import PhotosUI

@Observable
class BankImportViewModel {
    // MARK: - Published State

    var sessions: [ImportSession] = []
    var currentSession: ImportSession?
    var transactions: [ExtractedTransaction] = []
    var settings: ImportSettings = .defaults

    // Config data
    var expenseTypes: [ExpenseType] = []
    var categories: [TransactionCategory] = []

    var isLoading = false
    var isUploading = false
    var isImporting = false
    var error: String?

    // File picker state
    var selectedPhotos: [PhotosPickerItem] = []
    var selectedFiles: [URL] = []

    // Filter state
    var selectedTab: TransactionTab = .ready

    private let network = NetworkManager.shared

    // MARK: - Computed Properties

    var readyTransactions: [ExtractedTransaction] {
        transactions.filter { $0.isSelected && !$0.needsReview && $0.status == .pending }
    }

    var needsAttentionTransactions: [ExtractedTransaction] {
        transactions.filter { $0.isSelected && $0.needsReview && $0.status == .pending }
    }

    var skippedTransactions: [ExtractedTransaction] {
        transactions.filter { !$0.isSelected && $0.status != .imported }
    }

    var importedTransactions: [ExtractedTransaction] {
        transactions.filter { $0.status == .imported }
    }

    var selectedCount: Int {
        transactions.filter { $0.isSelected && $0.status == .pending }.count
    }

    var currentTabTransactions: [ExtractedTransaction] {
        switch selectedTab {
        case .ready:
            return readyTransactions
        case .needsAttention:
            return needsAttentionTransactions
        case .skipped:
            return skippedTransactions
        case .imported:
            return importedTransactions
        }
    }

    // MARK: - Enums

    enum TransactionTab: String, CaseIterable {
        case ready = "Ready"
        case needsAttention = "Needs Attention"
        case skipped = "Skipped"
        case imported = "Imported"

        var systemImage: String {
            switch self {
            case .ready: return "checkmark.circle"
            case .needsAttention: return "exclamationmark.circle"
            case .skipped: return "minus.circle"
            case .imported: return "checkmark.seal"
            }
        }
    }

    // MARK: - Session Management

    @MainActor
    func loadSessions() async {
        isLoading = true
        defer { isLoading = false }

        do {
            let response: ImportSessionsResponse = try await network.request(
                endpoint: Endpoints.importSessions,
                requiresAuth: true,
                requiresHousehold: false
            )
            sessions = response.sessions
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
        }
    }

    @MainActor
    func loadSession(_ sessionId: Int) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let response: ImportSessionResponse = try await network.request(
                endpoint: Endpoints.importSession(sessionId),
                requiresAuth: true,
                requiresHousehold: false
            )
            currentSession = response.session

            // If session is ready, load transactions
            if response.session.status == .ready {
                await loadTransactions(sessionId)
            }
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
        }
    }

    @MainActor
    func deleteSession(_ sessionId: Int) async -> Bool {
        do {
            try await network.requestWithoutResponse(
                endpoint: Endpoints.importSession(sessionId),
                method: .delete,
                requiresAuth: true,
                requiresHousehold: false
            )
            sessions.removeAll { $0.id == sessionId }
            if currentSession?.id == sessionId {
                currentSession = nil
            }
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    // MARK: - File Upload

    @MainActor
    func uploadFiles() async -> ImportSession? {
        guard !selectedPhotos.isEmpty || !selectedFiles.isEmpty else {
            error = "Please select files to upload"
            return nil
        }

        isUploading = true
        defer { isUploading = false }

        var files: [(data: Data, filename: String, mimeType: String)] = []

        // Process photos
        for (index, item) in selectedPhotos.enumerated() {
            if let data = try? await item.loadTransferable(type: Data.self) {
                files.append((
                    data: data,
                    filename: "photo_\(index + 1).jpg",
                    mimeType: "image/jpeg"
                ))
            }
        }

        // Process files (PDFs)
        for url in selectedFiles {
            if url.startAccessingSecurityScopedResource() {
                defer { url.stopAccessingSecurityScopedResource() }
                if let data = try? Data(contentsOf: url) {
                    let mimeType = url.pathExtension.lowercased() == "pdf" ? "application/pdf" : "image/jpeg"
                    files.append((
                        data: data,
                        filename: url.lastPathComponent,
                        mimeType: mimeType
                    ))
                }
            }
        }

        guard !files.isEmpty else {
            error = "Could not read selected files"
            return nil
        }

        do {
            let response = try await network.uploadBankStatements(files: files)
            currentSession = response.session
            sessions.insert(response.session, at: 0)
            selectedPhotos = []
            selectedFiles = []
            return response.session
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return nil
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return nil
        }
    }

    // MARK: - Transactions

    @MainActor
    func loadTransactions(_ sessionId: Int) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let response: ExtractedTransactionsResponse = try await network.request(
                endpoint: Endpoints.importSessionTransactions(sessionId),
                requiresAuth: true,
                requiresHousehold: false
            )
            transactions = response.transactions
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
        }
    }

    @MainActor
    func updateTransaction(_ transaction: ExtractedTransaction, update: UpdateExtractedTransactionRequest) async -> Bool {
        guard let sessionId = currentSession?.id else { return false }

        do {
            let response: ExtractedTransactionResponse = try await network.request(
                endpoint: Endpoints.importSessionTransaction(sessionId, transactionId: transaction.id),
                method: .put,
                body: update,
                requiresAuth: true,
                requiresHousehold: false
            )

            // Update local state
            if let index = transactions.firstIndex(where: { $0.id == transaction.id }) {
                transactions[index] = response.transaction
            }
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    @MainActor
    func toggleSelection(_ transaction: ExtractedTransaction) async {
        let update = UpdateExtractedTransactionRequest(isSelected: !transaction.isSelected)
        _ = await updateTransaction(transaction, update: update)
    }

    @MainActor
    func selectAll(_ select: Bool) async {
        for transaction in transactions where transaction.status == .pending {
            if transaction.isSelected != select {
                let update = UpdateExtractedTransactionRequest(isSelected: select)
                _ = await updateTransaction(transaction, update: update)
            }
        }
    }

    // MARK: - Import

    @MainActor
    func importSelected() async -> Bool {
        guard let sessionId = currentSession?.id else { return false }

        isImporting = true
        defer { isImporting = false }

        do {
            let response: ImportResultResponse = try await network.request(
                endpoint: Endpoints.importSessionImport(sessionId),
                method: .post,
                requiresAuth: true,
                requiresHousehold: false
            )

            if response.success {
                // Reload session to get updated status
                await loadSession(sessionId)
            }
            return response.success
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    // MARK: - Settings

    @MainActor
    func loadSettings() async {
        do {
            let response: ImportSettingsResponse = try await network.request(
                endpoint: Endpoints.importSettings,
                requiresAuth: true,
                requiresHousehold: false
            )
            settings = response.settings
        } catch {
            // Settings are optional, use defaults on error
            settings = .defaults
        }
    }

    @MainActor
    func updateSettings(_ newSettings: ImportSettings) async -> Bool {
        do {
            let response: ImportSettingsResponse = try await network.request(
                endpoint: Endpoints.importSettings,
                method: .put,
                body: newSettings,
                requiresAuth: true,
                requiresHousehold: false
            )
            settings = response.settings
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    // MARK: - Config Data

    @MainActor
    func loadConfig() async {
        // Load expense types
        do {
            let response: ExpenseTypeListResponse = try await network.request(
                endpoint: Endpoints.expenseTypes,
                requiresAuth: true,
                requiresHousehold: true
            )
            expenseTypes = response.expenseTypes
        } catch {
            // Non-critical, continue
        }

        // Load categories
        do {
            let response: CategoryListResponse = try await network.request(
                endpoint: Endpoints.categories,
                requiresAuth: true,
                requiresHousehold: true
            )
            categories = response.categories
        } catch {
            // Non-critical, continue
        }
    }

    // MARK: - Helpers

    func clearError() {
        error = nil
    }

    func reset() {
        currentSession = nil
        transactions = []
        selectedPhotos = []
        selectedFiles = []
        selectedTab = .ready
    }
}
