import Foundation

// MARK: - Import Session

struct ImportSession: Codable, Identifiable, Hashable {
    let id: Int
    let householdId: Int
    let userId: Int
    let status: ImportStatus
    let sourceFiles: [SourceFile]
    let errorMessage: String?
    let createdAt: String
    let processingStartedAt: String?
    let processingCompletedAt: String?
    let importedAt: String?
    let transactionCounts: TransactionCounts?

    enum CodingKeys: String, CodingKey {
        case id
        case householdId = "household_id"
        case userId = "user_id"
        case status
        case sourceFiles = "source_files"
        case errorMessage = "error_message"
        case createdAt = "created_at"
        case processingStartedAt = "processing_started_at"
        case processingCompletedAt = "processing_completed_at"
        case importedAt = "imported_at"
        case transactionCounts = "transaction_counts"
    }

    struct TransactionCounts: Codable, Hashable {
        let total: Int
        let selected: Int
        let needsReview: Int
        let imported: Int
        let skipped: Int

        enum CodingKeys: String, CodingKey {
            case total
            case selected
            case needsReview = "needs_review"
            case imported
            case skipped
        }
    }
}

struct SourceFile: Codable, Hashable {
    let path: String
    let originalName: String?
    let type: String
    let size: Int?

    enum CodingKeys: String, CodingKey {
        case path
        case originalName = "original_name"
        case type
        case size
    }
}

enum ImportStatus: String, Codable {
    case pending
    case processing
    case ready
    case importing
    case completed
    case failed

    var displayName: String {
        switch self {
        case .pending: return "Pending"
        case .processing: return "Processing"
        case .ready: return "Ready for Review"
        case .importing: return "Importing"
        case .completed: return "Completed"
        case .failed: return "Failed"
        }
    }

    var isActive: Bool {
        switch self {
        case .pending, .processing, .ready, .importing:
            return true
        case .completed, .failed:
            return false
        }
    }
}

// MARK: - Extracted Transaction

struct ExtractedTransaction: Codable, Identifiable {
    let id: Int
    let sessionId: Int
    var merchant: String
    var amount: Double
    var currency: String
    var date: String
    let rawText: String?
    let confidence: Double
    var expenseTypeId: Int?
    var splitCategory: String
    var isSelected: Bool
    var status: ExtractedTransactionStatus
    let flags: [String]
    let expenseTypeName: String?

    enum CodingKeys: String, CodingKey {
        case id
        case sessionId = "session_id"
        case merchant
        case amount
        case currency
        case date
        case rawText = "raw_text"
        case confidence
        case expenseTypeId = "expense_type_id"
        case splitCategory = "split_category"
        case isSelected = "is_selected"
        case status
        case flags
        case expenseTypeName = "expense_type_name"
    }

    var needsReview: Bool {
        if flags.contains("low_confidence") { return true }
        if flags.contains("ocr_failure") { return true }
        if flags.contains("uncertain_category") { return true }
        if expenseTypeId == nil && status != .skipped { return true }
        return false
    }

    var displayDate: String {
        // Format: "yyyy-MM-dd" -> "Jan 15, 2024"
        let inputFormatter = DateFormatter()
        inputFormatter.dateFormat = "yyyy-MM-dd"
        guard let date = inputFormatter.date(from: date) else { return self.date }

        let outputFormatter = DateFormatter()
        outputFormatter.dateFormat = "MMM d, yyyy"
        return outputFormatter.string(from: date)
    }
}

enum ExtractedTransactionStatus: String, Codable {
    case pending
    case reviewed
    case imported
    case skipped
}

// MARK: - Import Settings

struct ImportSettings: Codable {
    var defaultCurrency: String
    var defaultSplitCategory: String
    var autoSkipDuplicates: Bool
    var autoSelectHighConfidence: Bool
    var confidenceThreshold: Double

    enum CodingKeys: String, CodingKey {
        case defaultCurrency = "default_currency"
        case defaultSplitCategory = "default_split_category"
        case autoSkipDuplicates = "auto_skip_duplicates"
        case autoSelectHighConfidence = "auto_select_high_confidence"
        case confidenceThreshold = "confidence_threshold"
    }

    static var defaults: ImportSettings {
        ImportSettings(
            defaultCurrency: "USD",
            defaultSplitCategory: "SHARED",
            autoSkipDuplicates: true,
            autoSelectHighConfidence: true,
            confidenceThreshold: 0.7
        )
    }
}

// MARK: - API Responses

struct ImportSessionsResponse: Codable {
    let sessions: [ImportSession]
    let count: Int
    let total: Int
}

struct ImportSessionResponse: Codable {
    let session: ImportSession
    let message: String?
}

struct ExtractedTransactionsResponse: Codable {
    let transactions: [ExtractedTransaction]
    let count: Int
}

struct ExtractedTransactionResponse: Codable {
    let transaction: ExtractedTransaction
}

struct ImportSettingsResponse: Codable {
    let settings: ImportSettings
}

struct ImportResultResponse: Codable {
    let success: Bool
    let importedCount: Int

    enum CodingKeys: String, CodingKey {
        case success
        case importedCount = "imported_count"
    }
}

// MARK: - Request Models

struct UpdateExtractedTransactionRequest: Codable {
    var merchant: String?
    var amount: Double?
    var date: String?
    var expenseTypeId: Int?
    var splitCategory: String?
    var isSelected: Bool?

    enum CodingKeys: String, CodingKey {
        case merchant
        case amount
        case date
        case expenseTypeId = "expense_type_id"
        case splitCategory = "split_category"
        case isSelected = "is_selected"
    }
}

struct ImportTransactionsRequest: Codable {
    var transactionIds: [Int]?

    enum CodingKeys: String, CodingKey {
        case transactionIds = "transaction_ids"
    }
}
