import SwiftUI

struct BudgetView: View {
    @Environment(AuthManager.self) private var authManager
    @State private var viewModel = BudgetViewModel()
    @State private var selectedTab = 0 // 0 = Budget Rules, 1 = Split Rules
    @State private var showAddBudgetRule = false
    @State private var showAddSplitRule = false
    @State private var editingBudgetRule: BudgetRule?
    @State private var editingSplitRule: SplitRule?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Tab Picker
                Picker("View", selection: $selectedTab) {
                    Text("Budget Rules").tag(0)
                    Text("Split Rules").tag(1)
                }
                .pickerStyle(.segmented)
                .padding()

                if viewModel.isLoading && viewModel.budgetRules.isEmpty && viewModel.splitRules.isEmpty {
                    Spacer()
                    ProgressView()
                    Spacer()
                } else {
                    if selectedTab == 0 {
                        BudgetRulesListView(
                            budgetRules: viewModel.budgetRules,
                            members: viewModel.members,
                            onEdit: { rule in editingBudgetRule = rule },
                            onDelete: { rule in Task { await viewModel.deleteBudgetRule(rule.id) } }
                        )
                    } else {
                        SplitRulesListView(
                            splitRules: viewModel.splitRules,
                            onEdit: { rule in editingSplitRule = rule },
                            onDelete: { rule in Task { await viewModel.deleteSplitRule(rule.id) } }
                        )
                    }
                }
            }
            .navigationTitle("Rules")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        if selectedTab == 0 {
                            showAddBudgetRule = true
                        } else {
                            showAddSplitRule = true
                        }
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .task {
                if let householdId = authManager.currentHouseholdId {
                    await viewModel.loadData(householdId: householdId)
                }
            }
            .refreshable {
                if let householdId = authManager.currentHouseholdId {
                    await viewModel.loadData(householdId: householdId)
                }
            }
            .sheet(isPresented: $showAddBudgetRule) {
                BudgetRuleEditSheet(
                    viewModel: viewModel,
                    rule: nil
                )
            }
            .sheet(item: $editingBudgetRule) { rule in
                BudgetRuleEditSheet(
                    viewModel: viewModel,
                    rule: rule
                )
            }
            .sheet(isPresented: $showAddSplitRule) {
                SplitRuleEditSheet(
                    viewModel: viewModel,
                    rule: nil
                )
            }
            .sheet(item: $editingSplitRule) { rule in
                SplitRuleEditSheet(
                    viewModel: viewModel,
                    rule: rule
                )
            }
            .alert("Error", isPresented: .init(
                get: { viewModel.error != nil },
                set: { if !$0 { viewModel.clearError() } }
            )) {
                Button("OK") { viewModel.clearError() }
            } message: {
                Text(viewModel.error ?? "")
            }
        }
    }
}

// MARK: - Budget Rules List

struct BudgetRulesListView: View {
    let budgetRules: [BudgetRule]
    let members: [HouseholdMember]
    let onEdit: (BudgetRule) -> Void
    let onDelete: (BudgetRule) -> Void

    var body: some View {
        if budgetRules.isEmpty {
            VStack(spacing: 12) {
                Spacer()
                Image(systemName: "dollarsign.circle")
                    .font(.system(size: 48))
                    .foregroundStyle(.secondary)
                Text("No Budget Rules")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                Text("Tap + to add a budget rule")
                    .font(.subheadline)
                    .foregroundStyle(.tertiary)
                Spacer()
            }
        } else {
            List {
                ForEach(budgetRules) { rule in
                    BudgetRuleRow(rule: rule)
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            Button(role: .destructive) {
                                onDelete(rule)
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                            Button {
                                onEdit(rule)
                            } label: {
                                Label("Edit", systemImage: "pencil")
                            }
                            .tint(.blue)
                        }
                }
            }
            .listStyle(.plain)
        }
    }
}

struct BudgetRuleRow: View {
    let rule: BudgetRule

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("\(rule.giverName) \u{2192} \(rule.receiverName)")
                    .font(.headline)
                Spacer()
                Text(formattedAmount)
                    .font(.headline)
                    .foregroundStyle(.green)
            }

            if !rule.expenseTypeNames.isEmpty {
                Text(rule.expenseTypeNames.joined(separator: ", "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }

    private var formattedAmount: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: NSNumber(value: rule.monthlyAmount)) ?? "$\(rule.monthlyAmount)"
    }
}

// MARK: - Split Rules List

struct SplitRulesListView: View {
    let splitRules: [SplitRule]
    let onEdit: (SplitRule) -> Void
    let onDelete: (SplitRule) -> Void

    var body: some View {
        if splitRules.isEmpty {
            VStack(spacing: 12) {
                Spacer()
                Image(systemName: "percent")
                    .font(.system(size: 48))
                    .foregroundStyle(.secondary)
                Text("No Split Rules")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                Text("Tap + to add a split rule")
                    .font(.subheadline)
                    .foregroundStyle(.tertiary)
                Spacer()
            }
        } else {
            List {
                ForEach(splitRules) { rule in
                    SplitRuleRow(rule: rule)
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            Button(role: .destructive) {
                                onDelete(rule)
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                            Button {
                                onEdit(rule)
                            } label: {
                                Label("Edit", systemImage: "pencil")
                            }
                            .tint(.blue)
                        }
                }
            }
            .listStyle(.plain)
        }
    }
}

struct SplitRuleRow: View {
    let rule: SplitRule

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(rule.description ?? "\(rule.member1Percent)% / \(rule.member2Percent)%")
                    .font(.headline)
                Spacer()
                if rule.isDefault {
                    Text("Default")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.blue.opacity(0.1))
                        .foregroundStyle(.blue)
                        .clipShape(Capsule())
                }
            }

            if let names = rule.expenseTypeNames, !names.isEmpty {
                Text(names.joined(separator: ", "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - View Model

@Observable
class BudgetViewModel {
    var budgetRules: [BudgetRule] = []
    var splitRules: [SplitRule] = []
    var expenseTypes: [ExpenseType] = []
    var members: [HouseholdMember] = []
    var householdId: Int?
    var error: String?
    var isLoading = false
    var isSaving = false

    private let network = NetworkManager.shared

    func loadData(householdId: Int) async {
        self.householdId = householdId
        isLoading = true
        defer { isLoading = false }

        await network.setHouseholdId(householdId)

        // Load budget rules, split rules, expense types, and members in parallel
        async let budgetRulesTask: () = loadBudgetRules()
        async let splitRulesTask: () = loadSplitRules()
        async let expenseTypesTask: () = loadExpenseTypes()
        async let membersTask: () = loadMembers(householdId: householdId)

        _ = await (budgetRulesTask, splitRulesTask, expenseTypesTask, membersTask)
    }

    private func loadBudgetRules() async {
        do {
            let response: BudgetRuleListResponse = try await network.request(
                endpoint: Endpoints.budgetRules,
                method: .get,
                requiresAuth: true,
                requiresHousehold: true
            )
            budgetRules = response.budgetRules
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func loadSplitRules() async {
        do {
            let response: SplitRuleListResponse = try await network.request(
                endpoint: Endpoints.splitRules,
                method: .get,
                requiresAuth: true,
                requiresHousehold: true
            )
            splitRules = response.splitRules
            // Also capture members from split rules response
            if members.isEmpty {
                members = response.members
            }
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func loadExpenseTypes() async {
        do {
            let response: ExpenseTypeListResponse = try await network.request(
                endpoint: Endpoints.expenseTypes,
                method: .get,
                requiresAuth: true,
                requiresHousehold: true
            )
            expenseTypes = response.expenseTypes
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func loadMembers(householdId: Int) async {
        do {
            let response: HouseholdDetailResponse = try await network.request(
                endpoint: Endpoints.household(householdId),
                method: .get,
                requiresAuth: true
            )
            members = response.members
        } catch {
            // Members already loaded from split rules response is fine
        }
    }

    // MARK: - Budget Rule CRUD

    func createBudgetRule(giverUserId: Int, receiverUserId: Int, monthlyAmount: Double, expenseTypeIds: [Int]) async -> Bool {
        isSaving = true
        defer { isSaving = false }

        do {
            let body: [String: Any] = [
                "giver_user_id": giverUserId,
                "receiver_user_id": receiverUserId,
                "monthly_amount": monthlyAmount,
                "expense_type_ids": expenseTypeIds
            ]

            let response: BudgetRuleResponse = try await network.request(
                endpoint: Endpoints.budgetRules,
                method: .post,
                body: BudgetRuleRequest(
                    giverUserId: giverUserId,
                    receiverUserId: receiverUserId,
                    monthlyAmount: monthlyAmount,
                    expenseTypeIds: expenseTypeIds
                ),
                requiresAuth: true,
                requiresHousehold: true
            )
            budgetRules.append(response.budgetRule)
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func updateBudgetRule(_ ruleId: Int, monthlyAmount: Double, expenseTypeIds: [Int]) async -> Bool {
        isSaving = true
        defer { isSaving = false }

        do {
            let response: BudgetRuleResponse = try await network.request(
                endpoint: Endpoints.budgetRule(ruleId),
                method: .put,
                body: BudgetRuleUpdateRequest(
                    monthlyAmount: monthlyAmount,
                    expenseTypeIds: expenseTypeIds
                ),
                requiresAuth: true,
                requiresHousehold: true
            )

            if let index = budgetRules.firstIndex(where: { $0.id == ruleId }) {
                budgetRules[index] = response.budgetRule
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

    func deleteBudgetRule(_ ruleId: Int) async {
        do {
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.budgetRule(ruleId),
                method: .delete,
                requiresAuth: true,
                requiresHousehold: true
            )
            budgetRules.removeAll { $0.id == ruleId }
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: - Split Rule CRUD

    func createSplitRule(member1Percent: Int, member2Percent: Int, isDefault: Bool, expenseTypeIds: [Int]) async -> Bool {
        isSaving = true
        defer { isSaving = false }

        do {
            let response: SplitRuleResponse = try await network.request(
                endpoint: Endpoints.splitRules,
                method: .post,
                body: SplitRuleRequest(
                    member1Percent: member1Percent,
                    member2Percent: member2Percent,
                    isDefault: isDefault,
                    expenseTypeIds: expenseTypeIds
                ),
                requiresAuth: true,
                requiresHousehold: true
            )
            splitRules.append(response.splitRule)

            // Reload to get updated list (other rules may have been modified)
            await loadSplitRules()
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func updateSplitRule(_ ruleId: Int, member1Percent: Int, member2Percent: Int, expenseTypeIds: [Int]) async -> Bool {
        isSaving = true
        defer { isSaving = false }

        do {
            let response: SplitRuleResponse = try await network.request(
                endpoint: Endpoints.splitRule(ruleId),
                method: .put,
                body: SplitRuleUpdateRequest(
                    member1Percent: member1Percent,
                    member2Percent: member2Percent,
                    expenseTypeIds: expenseTypeIds
                ),
                requiresAuth: true,
                requiresHousehold: true
            )

            if let index = splitRules.firstIndex(where: { $0.id == ruleId }) {
                splitRules[index] = response.splitRule
            }

            // Reload to get updated list (other rules may have been modified)
            await loadSplitRules()
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func deleteSplitRule(_ ruleId: Int) async {
        do {
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.splitRule(ruleId),
                method: .delete,
                requiresAuth: true,
                requiresHousehold: true
            )
            splitRules.removeAll { $0.id == ruleId }
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func clearError() {
        error = nil
    }
}

// MARK: - Request Models

struct BudgetRuleRequest: Codable {
    let giverUserId: Int
    let receiverUserId: Int
    let monthlyAmount: Double
    let expenseTypeIds: [Int]

    enum CodingKeys: String, CodingKey {
        case giverUserId = "giver_user_id"
        case receiverUserId = "receiver_user_id"
        case monthlyAmount = "monthly_amount"
        case expenseTypeIds = "expense_type_ids"
    }
}

struct BudgetRuleUpdateRequest: Codable {
    let monthlyAmount: Double
    let expenseTypeIds: [Int]

    enum CodingKeys: String, CodingKey {
        case monthlyAmount = "monthly_amount"
        case expenseTypeIds = "expense_type_ids"
    }
}

struct SplitRuleRequest: Codable {
    let member1Percent: Int
    let member2Percent: Int
    let isDefault: Bool
    let expenseTypeIds: [Int]

    enum CodingKeys: String, CodingKey {
        case member1Percent = "member1_percent"
        case member2Percent = "member2_percent"
        case isDefault = "is_default"
        case expenseTypeIds = "expense_type_ids"
    }
}

struct SplitRuleUpdateRequest: Codable {
    let member1Percent: Int
    let member2Percent: Int
    let expenseTypeIds: [Int]

    enum CodingKeys: String, CodingKey {
        case member1Percent = "member1_percent"
        case member2Percent = "member2_percent"
        case expenseTypeIds = "expense_type_ids"
    }
}

#Preview {
    BudgetView()
        .environment(AuthManager())
}
