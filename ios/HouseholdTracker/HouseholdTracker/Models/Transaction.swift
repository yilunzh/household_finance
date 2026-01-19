import Foundation

struct Transaction: Codable, Identifiable, Sendable {
    let id: Int
    let householdId: Int
    let amount: Double
    let amountInUsd: Double
    let currency: String
    let merchant: String
    let category: String
    let date: String
    let monthYear: String
    let notes: String?
    let paidByUserId: Int?
    let paidByName: String?
    let expenseTypeId: Int?
    let expenseTypeName: String?
    let receiptUrl: String?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case householdId = "household_id"
        case amount
        case amountInUsd = "amount_in_usd"
        case currency
        case merchant
        case category
        case date
        case monthYear = "month_year"
        case notes
        case paidByUserId = "paid_by_user_id"
        case paidByName = "paid_by_name"
        case expenseTypeId = "expense_type_id"
        case expenseTypeName = "expense_type_name"
        case receiptUrl = "receipt_url"
        case createdAt = "created_at"
    }

    /// Returns the full URL for the receipt image
    var fullReceiptUrl: URL? {
        guard let receiptUrl = receiptUrl else { return nil }
        // Use 127.0.0.1 instead of localhost for iOS simulator compatibility
        #if DEBUG
        let baseURL = "http://127.0.0.1:5001"
        #else
        let baseURL = "https://your-production-url.com"  // TODO: Make configurable
        #endif
        return URL(string: "\(baseURL)\(receiptUrl)")
    }
}

struct TransactionListResponse: Codable, Sendable {
    let transactions: [Transaction]
    let pagination: Pagination?
}

struct Pagination: Codable, Sendable {
    let page: Int
    let perPage: Int
    let total: Int
    let totalPages: Int

    enum CodingKeys: String, CodingKey {
        case page
        case perPage = "per_page"
        case total
        case totalPages = "total_pages"
    }
}

struct CreateTransactionRequest: Codable, Sendable {
    let amount: Double
    let currency: String
    let merchant: String
    let category: String
    let date: String
    let paidBy: Int
    let expenseTypeId: Int?
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case amount
        case currency
        case merchant
        case category
        case date
        case paidBy = "paid_by"
        case expenseTypeId = "expense_type_id"
        case notes
    }
}

struct TransactionResponse: Codable, Sendable {
    let transaction: Transaction
}
