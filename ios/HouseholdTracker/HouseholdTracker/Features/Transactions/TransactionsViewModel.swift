import Foundation
import Observation

@Observable
final class TransactionsViewModel: Sendable {
    private(set) var transactions: [Transaction] = []
    private(set) var expenseTypes: [ExpenseType] = []
    private(set) var categories: [TransactionCategory] = []
    private(set) var members: [HouseholdMember] = []

    private(set) var isLoading = false
    private(set) var error: String?

    private(set) var selectedMonth: String

    private let network = NetworkManager.shared

    init() {
        // Default to current month
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM"
        selectedMonth = formatter.string(from: Date())
    }

    // MARK: - Fetch Data

    @MainActor
    func fetchTransactions() async {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let response: TransactionListResponse = try await network.request(
                endpoint: "\(Endpoints.transactions)?month=\(selectedMonth)",
                requiresAuth: true,
                requiresHousehold: true
            )
            transactions = response.transactions
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    @MainActor
    func fetchConfig() async {
        do {
            async let expenseTypesTask: ExpenseTypeListResponse = network.request(
                endpoint: Endpoints.expenseTypes,
                requiresAuth: true,
                requiresHousehold: true
            )

            async let categoriesTask: CategoryListResponse = network.request(
                endpoint: Endpoints.categories,
                requiresAuth: true,
                requiresHousehold: true
            )

            let (expenseTypesResponse, categoriesResponse) = try await (expenseTypesTask, categoriesTask)
            expenseTypes = expenseTypesResponse.expenseTypes
            categories = categoriesResponse.categories
        } catch {
            // Silently fail - config is supplementary
        }
    }

    @MainActor
    func fetchMembers(householdId: Int) async {
        do {
            let response: HouseholdMembersResponse = try await network.request(
                endpoint: Endpoints.householdMembers(householdId),
                requiresAuth: true
            )
            members = response.members
        } catch {
            // Silently fail
        }
    }

    // MARK: - Month Navigation

    @MainActor
    func selectMonth(_ month: String) {
        selectedMonth = month
        Task {
            await fetchTransactions()
        }
    }

    @MainActor
    func previousMonth() {
        guard let newMonth = monthByAdding(-1) else { return }
        selectMonth(newMonth)
    }

    @MainActor
    func nextMonth() {
        guard let newMonth = monthByAdding(1) else { return }
        selectMonth(newMonth)
    }

    private func monthByAdding(_ months: Int) -> String? {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM"
        guard let date = formatter.date(from: selectedMonth),
              let newDate = Calendar.current.date(byAdding: .month, value: months, to: date) else {
            return nil
        }
        return formatter.string(from: newDate)
    }

    var formattedMonth: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM"
        guard let date = formatter.date(from: selectedMonth) else {
            return selectedMonth
        }
        formatter.dateFormat = "MMMM yyyy"
        return formatter.string(from: date)
    }

    // MARK: - CRUD Operations

    @MainActor
    func createTransaction(_ request: CreateTransactionRequest) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let response: TransactionResponse = try await network.request(
                endpoint: Endpoints.transactions,
                method: .post,
                body: request,
                requiresAuth: true,
                requiresHousehold: true
            )

            // Add to list if same month
            if response.transaction.monthYear == selectedMonth {
                transactions.insert(response.transaction, at: 0)
            }

            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    @MainActor
    func updateTransaction(_ id: Int, request: CreateTransactionRequest) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let response: TransactionResponse = try await network.request(
                endpoint: Endpoints.transaction(id),
                method: .put,
                body: request,
                requiresAuth: true,
                requiresHousehold: true
            )

            // Update in list
            if let index = transactions.firstIndex(where: { $0.id == id }) {
                transactions[index] = response.transaction
            }

            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    @MainActor
    func deleteTransaction(_ id: Int) async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            try await network.requestWithoutResponse(
                endpoint: Endpoints.transaction(id),
                method: .delete,
                requiresAuth: true,
                requiresHousehold: true
            )

            // Remove from list
            transactions.removeAll { $0.id == id }

            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func clearError() {
        error = nil
    }

    /// Update a transaction in the list without fetching from server
    @MainActor
    func updateTransactionInList(_ transaction: Transaction) {
        if let index = transactions.firstIndex(where: { $0.id == transaction.id }) {
            transactions[index] = transaction
        }
    }
}

// MARK: - Response Types

private struct HouseholdMembersResponse: Codable {
    let members: [HouseholdMember]
}
