import SwiftUI

struct BudgetView: View {
    @Environment(AuthManager.self) private var authManager
    @Environment(\.colorScheme) private var colorScheme
    @State private var viewModel = BudgetViewModel()
    @State private var selectedTab = 0 // 0 = Budget Rules, 1 = Split Rules
    @State private var showAddBudgetRule = false
    @State private var showAddSplitRule = false
    @State private var editingBudgetRule: BudgetRule?
    @State private var editingSplitRule: SplitRule?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Styled Tab Picker
                HStack(spacing: Spacing.sm) {
                    StyledTabButton(
                        title: "Budget Rules",
                        icon: .coins,
                        isSelected: selectedTab == 0,
                        action: {
                            HapticManager.selection()
                            withAnimation(.spring(response: 0.3)) {
                                selectedTab = 0
                            }
                        }
                    )

                    StyledTabButton(
                        title: "Split Rules",
                        icon: .highfive,
                        isSelected: selectedTab == 1,
                        action: {
                            HapticManager.selection()
                            withAnimation(.spring(response: 0.3)) {
                                selectedTab = 1
                            }
                        }
                    )
                }
                .padding(.horizontal, Spacing.md)
                .padding(.vertical, Spacing.sm)

                if viewModel.isLoading && viewModel.budgetRules.isEmpty && viewModel.splitRules.isEmpty {
                    LoadingState(message: "Loading rules...")
                } else {
                    if selectedTab == 0 {
                        StyledBudgetRulesListView(
                            budgetRules: viewModel.budgetRules,
                            members: viewModel.members,
                            onEdit: { rule in editingBudgetRule = rule },
                            onDelete: { rule in
                                HapticManager.warning()
                                Task { await viewModel.deleteBudgetRule(rule.id) }
                            }
                        )
                    } else {
                        StyledSplitRulesListView(
                            splitRules: viewModel.splitRules,
                            onEdit: { rule in editingSplitRule = rule },
                            onDelete: { rule in
                                HapticManager.warning()
                                Task { await viewModel.deleteSplitRule(rule.id) }
                            }
                        )
                    }
                }
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle("Rules")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        HapticManager.buttonTap()
                        if selectedTab == 0 {
                            showAddBudgetRule = true
                        } else {
                            showAddSplitRule = true
                        }
                    } label: {
                        CatIcon(name: .plus, size: .md, color: .brandPrimary)
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

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

// MARK: - Styled Tab Button

struct StyledTabButton: View {
    let title: String
    let icon: CatIcon.Name
    let isSelected: Bool
    let action: () -> Void

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        Button(action: action) {
            HStack(spacing: Spacing.xs) {
                CatIcon(name: icon, size: .sm, color: isSelected ? .white : .warm500)
                Text(title)
                    .font(.labelMedium)
            }
            .foregroundColor(isSelected ? .white : .warm600)
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
            .frame(maxWidth: .infinity)
            .background(isSelected ? Color.brandPrimary : Color.clear)
            .cornerRadius(CornerRadius.large)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.large)
                    .stroke(isSelected ? Color.clear : Color.warm300, lineWidth: 1)
            )
        }
    }
}

// MARK: - Styled Budget Rules List

struct StyledBudgetRulesListView: View {
    let budgetRules: [BudgetRule]
    let members: [HouseholdMember]
    let onEdit: (BudgetRule) -> Void
    let onDelete: (BudgetRule) -> Void

    var body: some View {
        if budgetRules.isEmpty {
            EmptyState(
                icon: .coins,
                title: "No Budget Rules",
                message: "Set monthly spending limits between household members.",
                actionTitle: nil,
                action: nil
            )
        } else {
            ScrollView {
                LazyVStack(spacing: Spacing.sm) {
                    ForEach(budgetRules) { rule in
                        StyledBudgetRuleRow(rule: rule)
                            .contextMenu {
                                Button {
                                    HapticManager.light()
                                    onEdit(rule)
                                } label: {
                                    Label("Edit", systemImage: "pencil")
                                }

                                Button(role: .destructive) {
                                    onDelete(rule)
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                            .onTapGesture {
                                HapticManager.light()
                                onEdit(rule)
                            }
                    }
                }
                .padding(.horizontal, Spacing.md)
                .padding(.vertical, Spacing.sm)
            }
        }
    }
}

// MARK: - Styled Budget Rule Row

struct StyledBudgetRuleRow: View {
    let rule: BudgetRule

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            // Icon
            ZStack {
                Circle()
                    .fill(Color.sage100)
                    .frame(width: 44, height: 44)

                CatIcon(name: .coins, size: .md, color: .sage600)
            }

            // Details
            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                HStack(spacing: Spacing.xs) {
                    Text(rule.giverName)
                        .font(.labelMedium)
                        .foregroundColor(textColor)

                    Image(systemName: "arrow.right")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.brandPrimary)

                    Text(rule.receiverName)
                        .font(.labelMedium)
                        .foregroundColor(textColor)
                }

                if !rule.expenseTypeNames.isEmpty {
                    Text(rule.expenseTypeNames.joined(separator: ", "))
                        .font(.labelSmall)
                        .foregroundColor(.textTertiary)
                        .lineLimit(1)
                }
            }

            Spacer()

            // Amount
            Text(formattedAmount)
                .font(.amountMedium)
                .foregroundColor(.success)
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    private var formattedAmount: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: NSNumber(value: rule.monthlyAmount)) ?? "$\(rule.monthlyAmount)"
    }
}

// MARK: - Styled Split Rules List

struct StyledSplitRulesListView: View {
    let splitRules: [SplitRule]
    let onEdit: (SplitRule) -> Void
    let onDelete: (SplitRule) -> Void

    var body: some View {
        if splitRules.isEmpty {
            EmptyState(
                icon: .highfive,
                title: "No Split Rules",
                message: "Customize how shared expenses are divided between members.",
                actionTitle: nil,
                action: nil
            )
        } else {
            ScrollView {
                LazyVStack(spacing: Spacing.sm) {
                    ForEach(splitRules) { rule in
                        StyledSplitRuleRow(rule: rule)
                            .contextMenu {
                                Button {
                                    HapticManager.light()
                                    onEdit(rule)
                                } label: {
                                    Label("Edit", systemImage: "pencil")
                                }

                                Button(role: .destructive) {
                                    onDelete(rule)
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                            .onTapGesture {
                                HapticManager.light()
                                onEdit(rule)
                            }
                    }
                }
                .padding(.horizontal, Spacing.md)
                .padding(.vertical, Spacing.sm)
            }
        }
    }
}

// MARK: - Styled Split Rule Row

struct StyledSplitRuleRow: View {
    let rule: SplitRule

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            // Icon
            ZStack {
                Circle()
                    .fill(Color.terracotta100)
                    .frame(width: 44, height: 44)

                CatIcon(name: .highfive, size: .md, color: .terracotta600)
            }

            // Details
            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                HStack(spacing: Spacing.xs) {
                    Text(rule.description ?? "\(rule.member1Percent)% / \(rule.member2Percent)%")
                        .font(.labelMedium)
                        .foregroundColor(textColor)

                    if rule.isDefault {
                        Badge(text: "Default", style: .default)
                    }
                }

                if let names = rule.expenseTypeNames, !names.isEmpty {
                    Text(names.joined(separator: ", "))
                        .font(.labelSmall)
                        .foregroundColor(.textTertiary)
                        .lineLimit(1)
                }
            }

            Spacer()

            // Split visualization
            HStack(spacing: Spacing.xxs) {
                Text("\(rule.member1Percent)%")
                    .font(.labelSmall)
                    .foregroundColor(.brandPrimary)

                Text("/")
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)

                Text("\(rule.member2Percent)%")
                    .font(.labelSmall)
                    .foregroundColor(.sage600)
            }
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, Spacing.xxs)
            .background(Color.warm100)
            .cornerRadius(CornerRadius.medium)
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
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
