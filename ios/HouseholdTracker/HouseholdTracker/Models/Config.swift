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

struct TransactionCategory: Codable, Identifiable, Sendable, Hashable {
    let code: String
    let name: String
    let description: String

    var id: String { code }
}

struct CategoryListResponse: Codable, Sendable {
    let categories: [TransactionCategory]
}

struct SplitRule: Codable, Identifiable, Sendable {
    let id: Int
    let member1Percent: Int
    let member2Percent: Int
    let isDefault: Bool
    let expenseTypeIds: [Int]?
    let description: String?

    enum CodingKeys: String, CodingKey {
        case id
        case member1Percent = "member1_percent"
        case member2Percent = "member2_percent"
        case isDefault = "is_default"
        case expenseTypeIds = "expense_type_ids"
        case description
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
