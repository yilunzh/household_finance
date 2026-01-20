import Foundation

enum Endpoints {
    // Auth
    static let login = "/auth/login"
    static let register = "/auth/register"
    static let refresh = "/auth/refresh"
    static let logout = "/auth/logout"
    static let forgotPassword = "/auth/forgot-password"
    static let userMe = "/user/me"

    // Profile Management
    static let userProfile = "/user/profile"
    static let userPassword = "/user/password"
    static let userEmailRequest = "/user/email/request"
    static let userEmailCancel = "/user/email/cancel"
    static let userDelete = "/user"

    // Households
    static let households = "/households"
    static func household(_ id: Int) -> String { "/households/\(id)" }
    static func householdMembers(_ id: Int) -> String { "/households/\(id)/members" }
    static func householdMember(_ householdId: Int, userId: Int) -> String { "/households/\(householdId)/members/\(userId)" }
    static func leaveHousehold(_ id: Int) -> String { "/households/\(id)/leave" }

    // Invitations
    static func householdInvitations(_ householdId: Int) -> String { "/households/\(householdId)/invitations" }
    static func cancelInvitation(_ id: Int) -> String { "/invitations/\(id)" }
    static func invitation(_ token: String) -> String { "/invitations/\(token)" }
    static func acceptInvitation(_ token: String) -> String { "/invitations/\(token)/accept" }

    // Transactions
    static let transactions = "/transactions"
    static func transaction(_ id: Int) -> String { "/transactions/\(id)" }

    // Reconciliation
    static func reconciliation(_ month: String) -> String { "/reconciliation/\(month)" }
    static let settlement = "/settlement"
    static func deleteSettlement(_ month: String) -> String { "/settlement/\(month)" }

    // Config
    static let expenseTypes = "/expense-types"
    static func expenseType(_ id: Int) -> String { "/expense-types/\(id)" }
    static let splitRules = "/split-rules"
    static let categories = "/categories"

    // Budget & Split Rules
    static let budgetRules = "/budget-rules"
    static func budgetRule(_ id: Int) -> String { "/budget-rules/\(id)" }
    static func splitRule(_ id: Int) -> String { "/split-rules/\(id)" }
}
