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

    // Search and filter state
    var searchText: String = ""
    var filters: TransactionFilters = TransactionFilters()
    var isSearchActive: Bool = false

    private let network = NetworkManager.shared

    init() {
        // Default to current month
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM"
        selectedMonth = formatter.string(from: Date())
    }

    /// Check if any filters are active
    var hasActiveFilters: Bool {
        return !searchText.isEmpty || filters.hasActiveFilters
    }

    /// Number of active filters (for badge display)
    var activeFilterCount: Int {
        return filters.activeFilterCount + (searchText.isEmpty ? 0 : 1)
    }

    // MARK: - Fetch Data

    @MainActor
    func fetchTransactions() async {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            // Build query parameters
            var queryParams: [String] = []

            // Use month filter if search is not active
            if !isSearchActive {
                queryParams.append("month=\(selectedMonth)")
            }

            // Add search text
            if !searchText.isEmpty {
                let encoded = searchText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? searchText
                queryParams.append("search=\(encoded)")
            }

            // Add date range filters
            if let dateFrom = filters.dateFrom {
                let formatter = DateFormatter()
                formatter.dateFormat = "yyyy-MM-dd"
                queryParams.append("date_from=\(formatter.string(from: dateFrom))")
            }
            if let dateTo = filters.dateTo {
                let formatter = DateFormatter()
                formatter.dateFormat = "yyyy-MM-dd"
                queryParams.append("date_to=\(formatter.string(from: dateTo))")
            }

            // Add category filter
            if let category = filters.category {
                queryParams.append("category=\(category.code)")
            }

            // Add expense type filter
            if let expenseType = filters.expenseType {
                queryParams.append("expense_type_id=\(expenseType.id)")
            }

            // Add paid by filter
            if let paidBy = filters.paidBy {
                queryParams.append("paid_by=\(paidBy.userId)")
            }

            // Add amount range filters
            if let amountMin = filters.amountMin {
                queryParams.append("amount_min=\(amountMin)")
            }
            if let amountMax = filters.amountMax {
                queryParams.append("amount_max=\(amountMax)")
            }

            let queryString = queryParams.isEmpty ? "" : "?\(queryParams.joined(separator: "&"))"
            let response: TransactionListResponse = try await network.request(
                endpoint: "\(Endpoints.transactions)\(queryString)",
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

    /// Clear all search and filter state
    @MainActor
    func clearSearchAndFilters() {
        searchText = ""
        filters = TransactionFilters()
        isSearchActive = false
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

    // MARK: - Auto-Categorization

    @MainActor
    func fetchAutoCategorySuggestion(
        merchant: String? = nil,
        expenseTypeId: Int? = nil,
        paidByUserId: Int? = nil
    ) async -> AutoCategorizeResponse? {
        // Need at least merchant (non-empty) or expenseTypeId
        let hasMerchant = merchant != nil && !merchant!.trimmingCharacters(in: .whitespaces).isEmpty
        guard hasMerchant || expenseTypeId != nil else {
            print("[AutoCat] No merchant or expenseTypeId, skipping")
            return nil
        }

        print("[AutoCat] Fetching suggestion for merchant=\(merchant ?? "nil"), expenseTypeId=\(String(describing: expenseTypeId)), paidByUserId=\(String(describing: paidByUserId))")

        do {
            let request = AutoCategorizeRequest(
                merchant: merchant,
                expenseTypeId: expenseTypeId,
                paidByUserId: paidByUserId
            )
            let response: AutoCategorizeResponse = try await network.request(
                endpoint: Endpoints.autoCategorize,
                method: .post,
                body: request,
                requiresAuth: true,
                requiresHousehold: true
            )
            print("[AutoCat] Response: expense_type=\(String(describing: response.expenseType?.name)), category=\(String(describing: response.category))")
            // Return if we got an expense type OR a category
            return (response.expenseType != nil || response.category != nil) ? response : nil
        } catch {
            print("[AutoCat] Error: \(error)")
            return nil  // Silent fail - auto-categorization is optional
        }
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

// MARK: - Transaction Filters

struct TransactionFilters {
    var dateFrom: Date?
    var dateTo: Date?
    var category: TransactionCategory?
    var expenseType: ExpenseType?
    var paidBy: HouseholdMember?
    var amountMin: Double?
    var amountMax: Double?

    var hasActiveFilters: Bool {
        return dateFrom != nil || dateTo != nil || category != nil ||
               expenseType != nil || paidBy != nil || amountMin != nil || amountMax != nil
    }

    var activeFilterCount: Int {
        var count = 0
        if dateFrom != nil || dateTo != nil { count += 1 }  // Date range counts as 1
        if category != nil { count += 1 }
        if expenseType != nil { count += 1 }
        if paidBy != nil { count += 1 }
        if amountMin != nil || amountMax != nil { count += 1 }  // Amount range counts as 1
        return count
    }

    mutating func clear() {
        dateFrom = nil
        dateTo = nil
        category = nil
        expenseType = nil
        paidBy = nil
        amountMin = nil
        amountMax = nil
    }
}
