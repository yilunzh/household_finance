import Foundation

struct ReconciliationResponse: Codable, Sendable {
    let month: String
    let isSettled: Bool
    let settlement: Settlement?
    let transactions: [Transaction]
    let summary: ReconciliationSummary
    let budgetStatus: [BudgetStatus]?

    enum CodingKeys: String, CodingKey {
        case month
        case isSettled = "is_settled"
        case settlement
        case transactions
        case summary
        case budgetStatus = "budget_status"
    }
}

struct ReconciliationSummary: Codable, Sendable {
    let userPayments: [String: Double]
    let userShares: [String: Double]
    let balances: [String: Double]
    let settlementMessage: String
    let totalSpent: Double
    let breakdown: [CategoryBreakdown]
    let memberNames: [String: String]

    enum CodingKeys: String, CodingKey {
        case userPayments = "user_payments"
        case userShares = "user_shares"
        case balances
        case settlementMessage = "settlement_message"
        case totalSpent = "total_spent"
        case breakdown
        case memberNames = "member_names"
    }
}

struct CategoryBreakdown: Codable, Sendable, Identifiable {
    let category: String
    let categoryName: String
    let count: Int
    let total: Double

    var id: String { category }

    enum CodingKeys: String, CodingKey {
        case category
        case categoryName = "category_name"
        case count
        case total
    }
}

struct Settlement: Codable, Sendable, Identifiable {
    let id: Int
    let householdId: Int
    let monthYear: String
    let settledDate: String
    let settlementAmount: Double
    let fromUserId: Int
    let toUserId: Int
    let settlementMessage: String?

    enum CodingKeys: String, CodingKey {
        case id
        case householdId = "household_id"
        case monthYear = "month_year"
        case settledDate = "settled_date"
        case settlementAmount = "settlement_amount"
        case fromUserId = "from_user_id"
        case toUserId = "to_user_id"
        case settlementMessage = "settlement_message"
    }
}

struct BudgetStatus: Codable, Sendable, Identifiable {
    let ruleId: Int
    let budgetAmount: Double
    let spentAmount: Double
    let remaining: Double
    let percentUsed: Double
    let isOverBudget: Bool
    let giverUserId: Int
    let receiverUserId: Int
    let giverDisplayName: String
    let receiverDisplayName: String

    var id: Int { ruleId }

    enum CodingKeys: String, CodingKey {
        case ruleId = "rule_id"
        case budgetAmount = "budget_amount"
        case spentAmount = "spent_amount"
        case remaining
        case percentUsed = "percent_used"
        case isOverBudget = "is_over_budget"
        case giverUserId = "giver_user_id"
        case receiverUserId = "receiver_user_id"
        case giverDisplayName = "giver_display_name"
        case receiverDisplayName = "receiver_display_name"
    }
}
