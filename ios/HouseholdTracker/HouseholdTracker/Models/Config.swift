import Foundation

struct ExpenseType: Codable, Identifiable, Sendable, Hashable {
    let id: Int
    let name: String
    let icon: String?
    let color: String?
}

struct ExpenseTypeListResponse: Codable, Sendable {
    let expenseTypes: [ExpenseType]

    enum CodingKeys: String, CodingKey {
        case expenseTypes = "expense_types"
    }
}

struct ExpenseTypeResponse: Codable, Sendable {
    let expenseType: ExpenseType

    enum CodingKeys: String, CodingKey {
        case expenseType = "expense_type"
    }
}

struct TransactionCategory: Codable, Identifiable, Sendable, Hashable {
    let code: String
    let name: String
    let description: String

    var id: String { code }
}

struct CategoryListResponse: Codable, Sendable {
    let categories: [TransactionCategory]
}

struct SplitRule: Codable, Identifiable, Sendable, Hashable {
    let id: Int
    let member1Percent: Int
    let member2Percent: Int
    let isDefault: Bool
    let expenseTypeIds: [Int]?
    let expenseTypeNames: [String]?
    let description: String?

    enum CodingKeys: String, CodingKey {
        case id
        case member1Percent = "member1_percent"
        case member2Percent = "member2_percent"
        case isDefault = "is_default"
        case expenseTypeIds = "expense_type_ids"
        case expenseTypeNames = "expense_type_names"
        case description
    }
}

struct BudgetRule: Codable, Identifiable, Sendable, Hashable {
    let id: Int
    let householdId: Int
    let giverUserId: Int
    let giverName: String
    let receiverUserId: Int
    let receiverName: String
    let monthlyAmount: Double
    let expenseTypeIds: [Int]
    let expenseTypeNames: [String]
    let isActive: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case householdId = "household_id"
        case giverUserId = "giver_user_id"
        case giverName = "giver_name"
        case receiverUserId = "receiver_user_id"
        case receiverName = "receiver_name"
        case monthlyAmount = "monthly_amount"
        case expenseTypeIds = "expense_type_ids"
        case expenseTypeNames = "expense_type_names"
        case isActive = "is_active"
    }
}

struct SplitRuleListResponse: Codable, Sendable {
    let splitRules: [SplitRule]
    let members: [HouseholdMember]

    enum CodingKeys: String, CodingKey {
        case splitRules = "split_rules"
        case members
    }
}

struct SplitRuleResponse: Codable, Sendable {
    let splitRule: SplitRule

    enum CodingKeys: String, CodingKey {
        case splitRule = "split_rule"
    }
}

struct BudgetRuleListResponse: Codable, Sendable {
    let budgetRules: [BudgetRule]

    enum CodingKeys: String, CodingKey {
        case budgetRules = "budget_rules"
    }
}

struct BudgetRuleResponse: Codable, Sendable {
    let budgetRule: BudgetRule

    enum CodingKeys: String, CodingKey {
        case budgetRule = "budget_rule"
    }
}

// MARK: - Auto-Categorization

struct AutoCategorizeRequest: Codable, Sendable {
    let merchant: String?
    let expenseTypeId: Int?
    let paidByUserId: Int?

    enum CodingKeys: String, CodingKey {
        case merchant
        case expenseTypeId = "expense_type_id"
        case paidByUserId = "paid_by_user_id"
    }
}

struct AutoCategorizeResponse: Codable, Sendable {
    let expenseType: ExpenseType?
    let matchedRule: AutoCategoryRuleInfo?
    let category: String?

    enum CodingKeys: String, CodingKey {
        case expenseType = "expense_type"
        case matchedRule = "matched_rule"
        case category
    }
}

struct AutoCategoryRuleInfo: Codable, Sendable {
    let id: Int
    let keyword: String
    let expenseTypeId: Int
    let priority: Int

    enum CodingKeys: String, CodingKey {
        case id, keyword
        case expenseTypeId = "expense_type_id"
        case priority
    }
}
