import Foundation
import Observation

@Observable
final class ReconciliationViewModel: Sendable {
    private(set) var reconciliation: ReconciliationResponse?
    private(set) var isLoading = false
    private(set) var error: String?

    private(set) var selectedMonth: String

    private let network = NetworkManager.shared

    init() {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM"
        selectedMonth = formatter.string(from: Date())
    }

    // MARK: - Fetch Data

    @MainActor
    func fetchReconciliation() async {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            reconciliation = try await network.request(
                endpoint: Endpoints.reconciliation(selectedMonth),
                requiresAuth: true,
                requiresHousehold: true
            )
        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: - Month Navigation

    @MainActor
    func selectMonth(_ month: String) {
        selectedMonth = month
        Task {
            await fetchReconciliation()
        }
    }

    @MainActor
    func previousMonth() {
        guard let newMonth = monthByAdding(-1) else { return }
        selectMonth(newMonth)
    }

    @MainActor
    func nextMonth() {
        guard let newMonth = monthByAdding(1) else { return }
        selectMonth(newMonth)
    }

    private func monthByAdding(_ months: Int) -> String? {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM"
        guard let date = formatter.date(from: selectedMonth),
              let newDate = Calendar.current.date(byAdding: .month, value: months, to: date) else {
            return nil
        }
        return formatter.string(from: newDate)
    }

    var formattedMonth: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM"
        guard let date = formatter.date(from: selectedMonth) else {
            return selectedMonth
        }
        formatter.dateFormat = "MMMM yyyy"
        return formatter.string(from: date)
    }

    // MARK: - Settlement

    @MainActor
    func settleMonth() async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let body = ["month": selectedMonth]
            let _: SettlementResponse = try await network.request(
                endpoint: Endpoints.settlement,
                method: .post,
                body: body,
                requiresAuth: true,
                requiresHousehold: true
            )

            // Refresh data
            await fetchReconciliation()
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    @MainActor
    func unsettleMonth() async -> Bool {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            try await network.requestWithoutResponse(
                endpoint: Endpoints.deleteSettlement(selectedMonth),
                method: .delete,
                requiresAuth: true,
                requiresHousehold: true
            )

            // Refresh data
            await fetchReconciliation()
            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            return false
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func clearError() {
        error = nil
    }
}

// MARK: - Response Types

private struct SettlementResponse: Codable {
    let settlement: Settlement
}
