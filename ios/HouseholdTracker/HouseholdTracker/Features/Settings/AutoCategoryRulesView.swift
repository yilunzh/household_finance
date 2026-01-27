import SwiftUI

struct AutoCategoryRulesView: View {
    @Environment(AuthManager.self) private var authManager
    @State private var viewModel = AutoCategoryRulesViewModel()
    @State private var showAddRule = false
    @State private var editingRule: AutoCategoryRule?

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.rules.isEmpty {
                ProgressView()
            } else if viewModel.rules.isEmpty {
                VStack(spacing: 12) {
                    Spacer()
                    CatIcon(name: .lightbulb, size: .xl, color: .warm400)
                    Text("No Auto-Category Rules")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                    Text("Rules automatically assign expense types to transactions based on merchant keywords.")
                        .font(.subheadline)
                        .foregroundStyle(.tertiary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)
                    Spacer()
                }
            } else {
                List {
                    ForEach(viewModel.rules) { rule in
                        AutoCategoryRuleRow(rule: rule)
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button(role: .destructive) {
                                    Task {
                                        await viewModel.deleteRule(rule.id)
                                    }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                                Button {
                                    editingRule = rule
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
        .navigationTitle("Auto-Category Rules")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showAddRule = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .task {
            if let householdId = authManager.currentHouseholdId {
                await viewModel.loadRules(householdId: householdId)
            }
        }
        .refreshable {
            if let householdId = authManager.currentHouseholdId {
                await viewModel.loadRules(householdId: householdId)
            }
        }
        .sheet(isPresented: $showAddRule) {
            AutoCategoryRuleEditSheet(
                viewModel: viewModel,
                rule: nil
            )
        }
        .sheet(item: $editingRule) { rule in
            AutoCategoryRuleEditSheet(
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

// MARK: - Rule Row

struct AutoCategoryRuleRow: View {
    let rule: AutoCategoryRule

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Text(rule.keyword)
                    .font(.body)
                    .fontWeight(.medium)

                Image(systemName: "arrow.right")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Text(rule.expenseTypeName ?? "Unknown")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Spacer()
            }

            HStack(spacing: 8) {
                if rule.priority > 0 {
                    Text("Priority: \(rule.priority)")
                        .font(.caption)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.blue.opacity(0.7))
                        .cornerRadius(4)
                }

                if let category = rule.category {
                    Text(categoryLabel(for: category))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private func categoryLabel(for code: String) -> String {
        switch code {
        case "SHARED": return "Shared"
        case "I_PAY_FOR_WIFE": return "For Partner (by me)"
        case "WIFE_PAYS_FOR_ME": return "For Me (by partner)"
        case "PERSONAL_ME": return "Personal"
        case "PERSONAL_WIFE": return "Personal (partner)"
        default: return code
        }
    }
}

// MARK: - Edit Sheet

struct AutoCategoryRuleEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var viewModel: AutoCategoryRulesViewModel
    let rule: AutoCategoryRule?

    @State private var keyword: String = ""
    @State private var selectedExpenseTypeId: Int?
    @State private var selectedCategory: String = ""
    @State private var priority: Int = 0

    private var isEditing: Bool { rule != nil }

    private let categoryOptions: [(code: String, label: String)] = [
        ("", "None"),
        ("SHARED", "Shared"),
        ("I_PAY_FOR_WIFE", "For Partner (by me)"),
        ("WIFE_PAYS_FOR_ME", "For Me (by partner)"),
        ("PERSONAL_ME", "Personal"),
        ("PERSONAL_WIFE", "Personal (partner)")
    ]

    private var canSave: Bool {
        !keyword.trimmingCharacters(in: .whitespaces).isEmpty
        && selectedExpenseTypeId != nil
        && !viewModel.isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Keyword") {
                    TextField("e.g. Whole Foods", text: $keyword)
                        .autocorrectionDisabled()
                }

                Section("Expense Type") {
                    Picker("Expense Type", selection: $selectedExpenseTypeId) {
                        Text("Select...").tag(nil as Int?)
                        ForEach(viewModel.expenseTypes) { expenseType in
                            Text(expenseType.name).tag(expenseType.id as Int?)
                        }
                    }
                }

                Section("Category") {
                    Picker("Category", selection: $selectedCategory) {
                        ForEach(categoryOptions, id: \.code) { option in
                            Text(option.label).tag(option.code)
                        }
                    }
                }

                Section {
                    Stepper("Priority: \(priority)", value: $priority, in: 0...100)
                } header: {
                    Text("Priority")
                } footer: {
                    Text("Higher priority rules are checked first when multiple rules could match.")
                }
            }
            .navigationTitle(isEditing ? "Edit Rule" : "New Rule")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await save()
                        }
                    }
                    .disabled(!canSave)
                }
            }
            .onAppear {
                if let rule = rule {
                    keyword = rule.keyword
                    selectedExpenseTypeId = rule.expenseTypeId
                    selectedCategory = rule.category ?? ""
                    priority = rule.priority
                }
            }
        }
    }

    private func save() async {
        let trimmedKeyword = keyword.trimmingCharacters(in: .whitespaces)
        guard !trimmedKeyword.isEmpty, let expenseTypeId = selectedExpenseTypeId else { return }

        let category: String? = selectedCategory.isEmpty ? nil : selectedCategory

        let success: Bool
        if let rule = rule {
            success = await viewModel.updateRule(
                rule.id,
                keyword: trimmedKeyword,
                expenseTypeId: expenseTypeId,
                category: category,
                priority: priority
            )
        } else {
            success = await viewModel.createRule(
                keyword: trimmedKeyword,
                expenseTypeId: expenseTypeId,
                category: category,
                priority: priority
            )
        }

        if success {
            dismiss()
        }
    }
}

// MARK: - View Model

@Observable
class AutoCategoryRulesViewModel {
    var rules: [AutoCategoryRule] = []
    var expenseTypes: [ExpenseType] = []
    var error: String?
    var isLoading = false
    var isSaving = false

    private var householdId: Int?
    private let network = NetworkManager.shared

    func loadRules(householdId: Int) async {
        self.householdId = householdId
        isLoading = true
        defer { isLoading = false }

        await network.setHouseholdId(householdId)

        // Load rules and expense types in parallel
        async let rulesTask: AutoCategoryRuleListResponse = network.request(
            endpoint: Endpoints.autoCategoryRules,
            method: .get,
            requiresAuth: true,
            requiresHousehold: true
        )
        async let typesTask: ExpenseTypeListResponse = network.request(
            endpoint: Endpoints.expenseTypes,
            method: .get,
            requiresAuth: true,
            requiresHousehold: true
        )

        do {
            let (rulesResponse, typesResponse) = try await (rulesTask, typesTask)
            rules = rulesResponse.rules
            expenseTypes = typesResponse.expenseTypes
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func createRule(keyword: String, expenseTypeId: Int, category: String?, priority: Int) async -> Bool {
        isSaving = true
        defer { isSaving = false }

        do {
            let response: AutoCategoryRuleResponse = try await network.request(
                endpoint: Endpoints.autoCategoryRules,
                method: .post,
                body: AutoCategoryRuleRequest(
                    keyword: keyword,
                    expenseTypeId: expenseTypeId,
                    category: category,
                    priority: priority
                ),
                requiresAuth: true,
                requiresHousehold: true
            )
            rules.append(response.rule)
            sortRules()
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func updateRule(_ id: Int, keyword: String, expenseTypeId: Int, category: String?, priority: Int) async -> Bool {
        isSaving = true
        defer { isSaving = false }

        do {
            let response: AutoCategoryRuleResponse = try await network.request(
                endpoint: Endpoints.autoCategoryRule(id),
                method: .put,
                body: AutoCategoryRuleRequest(
                    keyword: keyword,
                    expenseTypeId: expenseTypeId,
                    category: category,
                    priority: priority
                ),
                requiresAuth: true,
                requiresHousehold: true
            )

            if let index = rules.firstIndex(where: { $0.id == id }) {
                rules[index] = response.rule
            }
            sortRules()
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func deleteRule(_ id: Int) async {
        do {
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.autoCategoryRule(id),
                method: .delete,
                requiresAuth: true,
                requiresHousehold: true
            )
            rules.removeAll { $0.id == id }
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    func clearError() {
        error = nil
    }

    private func sortRules() {
        rules.sort { a, b in
            if a.priority != b.priority {
                return a.priority > b.priority
            }
            return a.keyword < b.keyword
        }
    }
}

#Preview {
    NavigationStack {
        AutoCategoryRulesView()
            .environment(AuthManager())
    }
}
