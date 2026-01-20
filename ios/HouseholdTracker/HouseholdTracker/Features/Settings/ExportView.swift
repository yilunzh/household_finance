import SwiftUI

struct ExportView: View {
    @Environment(AuthManager.self) private var authManager
    @State private var viewModel = ExportViewModel()
    @State private var selectedMonth: String = ""
    @State private var showShareSheet = false
    @State private var csvURL: URL?

    private let months: [String] = {
        var months: [String] = []
        let calendar = Calendar.current
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM"

        // Generate last 12 months
        for i in 0..<12 {
            if let date = calendar.date(byAdding: .month, value: -i, to: Date()) {
                months.append(dateFormatter.string(from: date))
            }
        }
        return months
    }()

    var body: some View {
        List {
            Section {
                Picker("Select Month", selection: $selectedMonth) {
                    ForEach(months, id: \.self) { month in
                        Text(formatMonth(month)).tag(month)
                    }
                }
            } header: {
                Text("Export Monthly Report")
            } footer: {
                Text("Export all transactions and a summary for the selected month as a CSV file.")
            }

            Section {
                Button {
                    Task {
                        await exportMonthlyTransactions()
                    }
                } label: {
                    HStack {
                        if viewModel.isExporting {
                            ProgressView()
                                .padding(.trailing, 8)
                        }
                        Label("Export Monthly CSV", systemImage: "square.and.arrow.up")
                    }
                }
                .disabled(selectedMonth.isEmpty || viewModel.isExporting)
            }

            Section {
                Button {
                    Task {
                        await exportAllTransactions()
                    }
                } label: {
                    HStack {
                        if viewModel.isExporting {
                            ProgressView()
                                .padding(.trailing, 8)
                        }
                        Label("Export All Transactions", systemImage: "doc.text")
                    }
                }
                .disabled(viewModel.isExporting)
            } footer: {
                Text("Export all transactions from all months as a CSV file.")
            }
        }
        .navigationTitle("Export Data")
        .onAppear {
            if selectedMonth.isEmpty, let firstMonth = months.first {
                selectedMonth = firstMonth
            }
        }
        .sheet(isPresented: $showShareSheet) {
            if let url = csvURL {
                ShareSheet(items: [url])
            }
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

    private func formatMonth(_ month: String) -> String {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM"
        guard let date = dateFormatter.date(from: month) else { return month }

        dateFormatter.dateFormat = "MMMM yyyy"
        return dateFormatter.string(from: date)
    }

    private func exportMonthlyTransactions() async {
        guard let householdId = authManager.currentHouseholdId else { return }

        if let url = await viewModel.exportMonthlyTransactions(
            householdId: householdId,
            month: selectedMonth
        ) {
            csvURL = url
            showShareSheet = true
        }
    }

    private func exportAllTransactions() async {
        guard let householdId = authManager.currentHouseholdId else { return }

        if let url = await viewModel.exportAllTransactions(householdId: householdId) {
            csvURL = url
            showShareSheet = true
        }
    }
}

// MARK: - Share Sheet

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

// MARK: - View Model

@Observable
class ExportViewModel {
    var isExporting = false
    var error: String?

    private let network = NetworkManager.shared

    func exportMonthlyTransactions(householdId: Int, month: String) async -> URL? {
        isExporting = true
        defer { isExporting = false }

        await network.setHouseholdId(householdId)

        do {
            let data = try await network.downloadData(
                endpoint: Endpoints.exportMonthlyTransactions(month)
            )

            // Save to temp file
            let tempDir = FileManager.default.temporaryDirectory
            let fileName = "expenses_\(month).csv"
            let fileURL = tempDir.appendingPathComponent(fileName)

            try data.write(to: fileURL)
            return fileURL
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return nil
        } catch {
            self.error = error.localizedDescription
            return nil
        }
    }

    func exportAllTransactions(householdId: Int) async -> URL? {
        isExporting = true
        defer { isExporting = false }

        await network.setHouseholdId(householdId)

        do {
            let data = try await network.downloadData(
                endpoint: Endpoints.exportTransactions
            )

            // Save to temp file
            let tempDir = FileManager.default.temporaryDirectory
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd"
            let fileName = "transactions_\(dateFormatter.string(from: Date())).csv"
            let fileURL = tempDir.appendingPathComponent(fileName)

            try data.write(to: fileURL)
            return fileURL
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return nil
        } catch {
            self.error = error.localizedDescription
            return nil
        }
    }

    func clearError() {
        error = nil
    }
}

#Preview {
    NavigationStack {
        ExportView()
            .environment(AuthManager())
    }
}
