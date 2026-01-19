import Foundation

enum Endpoints {
    // Auth
    static let login = "/auth/login"
    static let register = "/auth/register"
    static let refresh = "/auth/refresh"
    static let logout = "/auth/logout"
    static let userMe = "/user/me"

    // Households
    static let households = "/households"
    static func household(_ id: Int) -> String { "/households/\(id)" }
    static func householdMembers(_ id: Int) -> String { "/households/\(id)/members" }
    static func leaveHousehold(_ id: Int) -> String { "/households/\(id)/leave" }

    // Transactions
    static let transactions = "/transactions"
    static func transaction(_ id: Int) -> String { "/transactions/\(id)" }

    // Reconciliation
    static func reconciliation(_ month: String) -> String { "/reconciliation/\(month)" }
    static let settlement = "/settlement"
    static func deleteSettlement(_ month: String) -> String { "/settlement/\(month)" }

    // Config
    static let expenseTypes = "/expense-types"
    static let splitRules = "/split-rules"
    static let categories = "/categories"
}
