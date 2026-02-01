import SwiftUI

struct BankImportSessionsView: View {
    @Environment(\.colorScheme) private var colorScheme
    @State private var viewModel = BankImportViewModel()
    @State private var showCapture = false
    @State private var selectedSession: ImportSession?
    @State private var pollTimer: Timer?

    var body: some View {
        NavigationStack {
            ZStack {
                backgroundColor.ignoresSafeArea()

                if viewModel.isLoading && viewModel.sessions.isEmpty {
                    ProgressView()
                        .scaleEffect(1.2)
                } else if viewModel.sessions.isEmpty {
                    EmptyState(
                        icon: .sparkle,
                        title: "No Imports Yet",
                        message: "Import your bank statements to quickly add transactions."
                    )
                } else {
                    ScrollView {
                        LazyVStack(spacing: Spacing.md) {
                            ForEach(viewModel.sessions) { session in
                                ImportSessionCard(
                                    session: session,
                                    onTap: {
                                        if session.status == .ready || session.status == .completed {
                                            selectedSession = session
                                        }
                                    },
                                    onDelete: {
                                        Task {
                                            if await viewModel.deleteSession(session.id) {
                                                HapticManager.success()
                                            } else {
                                                HapticManager.error()
                                            }
                                        }
                                    }
                                )
                            }
                        }
                        .padding(Spacing.md)
                    }
                    .refreshable {
                        await viewModel.loadSessions()
                    }
                }
            }
            .navigationTitle("Bank Import")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showCapture = true
                    } label: {
                        Label("Import", systemImage: "plus")
                            .foregroundColor(.brandPrimary)
                    }
                    .accessibilityIdentifier("addImportButton")
                }
            }
            .sheet(isPresented: $showCapture) {
                BankImportCaptureView(viewModel: viewModel) { session in
                    selectedSession = session
                    startPollingIfNeeded()
                }
            }
            .navigationDestination(item: $selectedSession) { session in
                BankImportSelectView(viewModel: viewModel, sessionId: session.id)
            }
            .task {
                await viewModel.loadSessions()
                startPollingIfNeeded()
            }
            .onDisappear {
                stopPolling()
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

    // MARK: - Polling

    private func startPollingIfNeeded() {
        // Check if any session is processing
        let hasProcessing = viewModel.sessions.contains { $0.status == .pending || $0.status == .processing }
        guard hasProcessing else { return }

        pollTimer?.invalidate()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { _ in
            Task {
                await viewModel.loadSessions()

                // Stop polling if no more processing sessions
                let stillProcessing = await MainActor.run {
                    viewModel.sessions.contains { $0.status == .pending || $0.status == .processing }
                }
                if !stillProcessing {
                    await MainActor.run {
                        stopPolling()
                    }
                }
            }
        }
    }

    private func stopPolling() {
        pollTimer?.invalidate()
        pollTimer = nil
    }
}

// MARK: - Import Session Card

struct ImportSessionCard: View {
    let session: ImportSession
    let onTap: () -> Void
    let onDelete: () -> Void

    @Environment(\.colorScheme) private var colorScheme
    @State private var showDeleteConfirm = false

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                // Header
                HStack {
                    ImportStatusBadge(status: session.status)

                    Spacer()

                    Text(formattedDate)
                        .font(.labelSmall)
                        .foregroundColor(.textTertiary)

                    Menu {
                        Button(role: .destructive) {
                            showDeleteConfirm = true
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    } label: {
                        Image(systemName: "ellipsis")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(.textTertiary)
                            .frame(width: 32, height: 32)
                    }
                }

                // File count
                Text("\(session.sourceFiles.count) file\(session.sourceFiles.count == 1 ? "" : "s") uploaded")
                    .font(.bodyMedium)
                    .foregroundColor(textColor)

                // Transaction counts (if available)
                if let counts = session.transactionCounts, counts.total > 0 {
                    HStack(spacing: Spacing.md) {
                        CountChip(count: counts.total, label: "Total")

                        if counts.selected > 0 {
                            CountChip(count: counts.selected, label: "Selected", color: .terracotta500)
                        }

                        if counts.needsReview > 0 {
                            CountChip(count: counts.needsReview, label: "Review", color: .amber500)
                        }
                    }
                }

                // Error message
                if let errorMessage = session.errorMessage {
                    Text(errorMessage)
                        .font(.labelSmall)
                        .foregroundColor(.danger)
                        .lineLimit(2)
                }

                // Progress indicator for processing
                if session.status == .pending || session.status == .processing {
                    HStack(spacing: Spacing.sm) {
                        ProgressView()
                            .scaleEffect(0.8)

                        Text(session.status == .pending ? "Waiting to process..." : "Extracting transactions...")
                            .font(.labelSmall)
                            .foregroundColor(.textSecondary)
                    }
                }
            }
            .padding(Spacing.md)
            .background(cardBackground)
            .cornerRadius(CornerRadius.large)
            .subtleShadow()
        }
        .buttonStyle(.plain)
        .disabled(!session.status.isActive && session.status != .completed)
        .confirmationDialog("Delete Import?", isPresented: $showDeleteConfirm, titleVisibility: .visible) {
            Button("Delete", role: .destructive, action: onDelete)
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will delete all extracted transactions and cannot be undone.")
        }
    }

    private var formattedDate: String {
        // Parse ISO date and format nicely
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate, .withTime, .withDashSeparatorInDate, .withColonSeparatorInTime]
        if let date = formatter.date(from: session.createdAt) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .medium
            displayFormatter.timeStyle = .short
            return displayFormatter.string(from: date)
        }
        return session.createdAt
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundCard
    }
}

// MARK: - Status Badge

struct ImportStatusBadge: View {
    let status: ImportStatus

    var body: some View {
        HStack(spacing: Spacing.xxs) {
            Circle()
                .fill(statusColor)
                .frame(width: 8, height: 8)

            Text(status.displayName)
                .font(.labelSmall)
                .foregroundColor(statusColor)
        }
        .padding(.horizontal, Spacing.sm)
        .padding(.vertical, Spacing.xxs)
        .background(statusColor.opacity(0.15))
        .cornerRadius(CornerRadius.full)
    }

    private var statusColor: Color {
        switch status {
        case .pending, .processing:
            return .amber500
        case .ready, .importing:
            return .terracotta500
        case .completed:
            return .sage500
        case .failed:
            return .rose500
        }
    }
}

// MARK: - Count Chip

struct CountChip: View {
    let count: Int
    let label: String
    var color: Color = .textSecondary

    var body: some View {
        HStack(spacing: Spacing.xxs) {
            Text("\(count)")
                .font(.labelMedium)
                .fontWeight(.semibold)
                .foregroundColor(color)

            Text(label)
                .font(.labelSmall)
                .foregroundColor(.textTertiary)
        }
    }
}

#Preview {
    BankImportSessionsView()
}
