import SwiftUI

struct ExpenseTypesView: View {
    @Environment(AuthManager.self) private var authManager
    @State private var viewModel = ExpenseTypesViewModel()
    @State private var showAddExpenseType = false
    @State private var editingExpenseType: ExpenseType?

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.expenseTypes.isEmpty {
                ProgressView()
            } else if viewModel.expenseTypes.isEmpty {
                VStack(spacing: 12) {
                    Spacer()
                    Image(systemName: "tag")
                        .font(.system(size: 48))
                        .foregroundStyle(.secondary)
                    Text("No Expense Types")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                    Text("Tap + to add an expense type")
                        .font(.subheadline)
                        .foregroundStyle(.tertiary)
                    Spacer()
                }
            } else {
                List {
                    ForEach(viewModel.expenseTypes) { expenseType in
                        ExpenseTypeRow(expenseType: expenseType)
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button(role: .destructive) {
                                    Task {
                                        await viewModel.deleteExpenseType(expenseType.id)
                                    }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                                Button {
                                    editingExpenseType = expenseType
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
        .navigationTitle("Expense Types")
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                AccessibleBackButton("back-expense-types")
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showAddExpenseType = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .task {
            if let householdId = authManager.currentHouseholdId {
                await viewModel.loadExpenseTypes(householdId: householdId)
            }
        }
        .refreshable {
            if let householdId = authManager.currentHouseholdId {
                await viewModel.loadExpenseTypes(householdId: householdId)
            }
        }
        .sheet(isPresented: $showAddExpenseType) {
            ExpenseTypeEditSheet(
                viewModel: viewModel,
                expenseType: nil
            )
        }
        .sheet(item: $editingExpenseType) { expenseType in
            ExpenseTypeEditSheet(
                viewModel: viewModel,
                expenseType: expenseType
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

// MARK: - Expense Type Row

struct ExpenseTypeRow: View {
    let expenseType: ExpenseType

    var body: some View {
        HStack(spacing: 12) {
            // Icon circle
            Circle()
                .fill(colorFor(expenseType.color))
                .frame(width: 40, height: 40)
                .overlay {
                    if let icon = expenseType.icon {
                        Image(systemName: iconName(for: icon))
                            .foregroundStyle(.white)
                    } else {
                        Image(systemName: "tag")
                            .foregroundStyle(.white)
                    }
                }

            Text(expenseType.name)
                .font(.body)

            Spacer()
        }
        .padding(.vertical, 4)
    }

    private func colorFor(_ colorName: String?) -> Color {
        guard let colorName = colorName else { return .gray }
        switch colorName.lowercased() {
        case "red": return .red
        case "orange": return .orange
        case "yellow": return .yellow
        case "green", "emerald": return .green
        case "blue": return .blue
        case "purple": return .purple
        case "pink": return .pink
        case "brown", "terracotta": return .brown
        case "sage": return Color(red: 0.6, green: 0.75, blue: 0.6)
        default: return .gray
        }
    }

    private func iconName(for icon: String) -> String {
        // Map common icon names to SF Symbols
        switch icon.lowercased() {
        case "cart", "shopping-cart": return "cart"
        case "utensils", "food", "dining": return "fork.knife"
        case "home", "house", "household": return "house"
        case "car", "transport": return "car"
        case "medical", "health": return "heart"
        case "gift": return "gift"
        case "plane", "travel": return "airplane"
        case "coffee": return "cup.and.saucer"
        case "star": return "star"
        default: return icon
        }
    }
}

// MARK: - Expense Type Edit Sheet

struct ExpenseTypeEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var viewModel: ExpenseTypesViewModel
    let expenseType: ExpenseType?

    @State private var name: String = ""
    @State private var selectedIcon: String = "tag"
    @State private var selectedColor: String = "gray"

    private var isEditing: Bool { expenseType != nil }

    private let availableIcons = [
        ("tag", "Tag"),
        ("cart", "Shopping"),
        ("fork.knife", "Dining"),
        ("house", "Home"),
        ("car", "Transport"),
        ("heart", "Health"),
        ("gift", "Gift"),
        ("airplane", "Travel"),
        ("cup.and.saucer", "Coffee"),
        ("star", "Star")
    ]

    private let availableColors = [
        ("gray", Color.gray),
        ("red", Color.red),
        ("orange", Color.orange),
        ("yellow", Color.yellow),
        ("green", Color.green),
        ("blue", Color.blue),
        ("purple", Color.purple),
        ("pink", Color.pink),
        ("brown", Color.brown)
    ]

    var body: some View {
        NavigationStack {
            Form {
                Section("Name") {
                    TextField("Expense Type Name", text: $name)
                        .autocorrectionDisabled()
                }

                Section("Icon") {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 60))], spacing: 12) {
                        ForEach(availableIcons, id: \.0) { icon, _ in
                            Button {
                                selectedIcon = icon
                            } label: {
                                ZStack {
                                    Circle()
                                        .fill(selectedIcon == icon ? colorValue(selectedColor) : Color(.systemGray5))
                                        .frame(width: 50, height: 50)
                                    Image(systemName: icon)
                                        .foregroundStyle(selectedIcon == icon ? .white : .primary)
                                }
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.vertical, 8)
                }

                Section("Color") {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 50))], spacing: 12) {
                        ForEach(availableColors, id: \.0) { colorName, colorValue in
                            Button {
                                selectedColor = colorName
                            } label: {
                                ZStack {
                                    Circle()
                                        .fill(colorValue)
                                        .frame(width: 40, height: 40)
                                    if selectedColor == colorName {
                                        Image(systemName: "checkmark")
                                            .foregroundStyle(.white)
                                            .font(.headline)
                                    }
                                }
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.vertical, 8)
                }
            }
            .navigationTitle(isEditing ? "Edit Expense Type" : "New Expense Type")
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
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty || viewModel.isSaving)
                }
            }
            .onAppear {
                if let expenseType = expenseType {
                    name = expenseType.name
                    selectedIcon = expenseType.icon ?? "tag"
                    selectedColor = expenseType.color ?? "gray"
                }
            }
        }
    }

    private func colorValue(_ colorName: String) -> Color {
        availableColors.first { $0.0 == colorName }?.1 ?? .gray
    }

    private func save() async {
        let trimmedName = name.trimmingCharacters(in: .whitespaces)
        guard !trimmedName.isEmpty else { return }

        let success: Bool
        if let expenseType = expenseType {
            success = await viewModel.updateExpenseType(
                expenseType.id,
                name: trimmedName,
                icon: selectedIcon,
                color: selectedColor
            )
        } else {
            success = await viewModel.createExpenseType(
                name: trimmedName,
                icon: selectedIcon,
                color: selectedColor
            )
        }

        if success {
            dismiss()
        }
    }
}

// MARK: - View Model

@Observable
class ExpenseTypesViewModel {
    var expenseTypes: [ExpenseType] = []
    var householdId: Int?
    var error: String?
    var isLoading = false
    var isSaving = false

    private let network = NetworkManager.shared

    func loadExpenseTypes(householdId: Int) async {
        self.householdId = householdId
        isLoading = true
        defer { isLoading = false }

        await network.setHouseholdId(householdId)

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
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
        }
    }

    func createExpenseType(name: String, icon: String?, color: String?) async -> Bool {
        isSaving = true
        defer { isSaving = false }

        do {
            let response: ExpenseTypeResponse = try await network.request(
                endpoint: Endpoints.expenseTypes,
                method: .post,
                body: ExpenseTypeRequest(name: name, icon: icon, color: color),
                requiresAuth: true,
                requiresHousehold: true
            )
            expenseTypes.append(response.expenseType)
            expenseTypes.sort { $0.name < $1.name }
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    func updateExpenseType(_ id: Int, name: String, icon: String?, color: String?) async -> Bool {
        isSaving = true
        defer { isSaving = false }

        do {
            let response: ExpenseTypeResponse = try await network.request(
                endpoint: Endpoints.expenseType(id),
                method: .put,
                body: ExpenseTypeRequest(name: name, icon: icon, color: color),
                requiresAuth: true,
                requiresHousehold: true
            )

            if let index = expenseTypes.firstIndex(where: { $0.id == id }) {
                expenseTypes[index] = response.expenseType
            }
            expenseTypes.sort { $0.name < $1.name }
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
            return false
        }
    }

    func deleteExpenseType(_ id: Int) async {
        do {
            let _: SuccessResponse = try await network.request(
                endpoint: Endpoints.expenseType(id),
                method: .delete,
                requiresAuth: true,
                requiresHousehold: true
            )
            expenseTypes.removeAll { $0.id == id }
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            if !error.isCancellation {
                self.error = error.localizedDescription
            }
        }
    }

    func clearError() {
        error = nil
    }
}

// MARK: - Request Model

struct ExpenseTypeRequest: Codable {
    let name: String
    let icon: String?
    let color: String?
}

#Preview {
    NavigationStack {
        ExpenseTypesView()
            .environment(AuthManager())
    }
}
