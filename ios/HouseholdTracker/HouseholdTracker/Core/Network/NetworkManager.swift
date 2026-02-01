import Foundation

actor NetworkManager {
    static let shared = NetworkManager()

    #if targetEnvironment(simulator)
    private let baseURL = "http://localhost:5001/api/v1"
    #else
    private let baseURL = "https://household-finance.onrender.com/api/v1"
    #endif

    private let keychain = KeychainManager.shared
    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        return decoder
    }()

    private var householdId: Int?
    private var isRefreshing = false
    private var refreshContinuations: [CheckedContinuation<String, Error>] = []

    private init() {}

    // MARK: - Household Context

    func setHouseholdId(_ id: Int?) {
        householdId = id
    }

    func getHouseholdId() -> Int? {
        householdId
    }

    // MARK: - Public Request Methods

    func request<T: Decodable>(
        endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        requiresAuth: Bool = true,
        requiresHousehold: Bool = false
    ) async throws -> T {
        let data = try await performRequest(
            endpoint: endpoint,
            method: method,
            body: body,
            requiresAuth: requiresAuth,
            requiresHousehold: requiresHousehold
        )

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    func requestWithoutResponse(
        endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        requiresAuth: Bool = true,
        requiresHousehold: Bool = false
    ) async throws {
        _ = try await performRequest(
            endpoint: endpoint,
            method: method,
            body: body,
            requiresAuth: requiresAuth,
            requiresHousehold: requiresHousehold
        )
    }

    func downloadData(
        endpoint: String,
        requiresAuth: Bool = true,
        requiresHousehold: Bool = true
    ) async throws -> Data {
        return try await performRequest(
            endpoint: endpoint,
            method: .get,
            body: nil,
            requiresAuth: requiresAuth,
            requiresHousehold: requiresHousehold
        )
    }

    // MARK: - Private Implementation

    private func performRequest(
        endpoint: String,
        method: HTTPMethod,
        body: Encodable?,
        requiresAuth: Bool,
        requiresHousehold: Bool
    ) async throws -> Data {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth header if required
        if requiresAuth {
            let token = try await getValidAccessToken()
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Add household header if required
        if requiresHousehold {
            guard let householdId = householdId else {
                throw APIError.httpError(statusCode: 400, message: "No household selected")
            }
            request.setValue(String(householdId), forHTTPHeaderField: "X-Household-ID")
        }

        // Add body if present
        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        // Handle 401 - try to refresh token once
        if httpResponse.statusCode == 401 && requiresAuth {
            // Token might have expired during request, try refreshing
            _ = try await refreshAccessToken()
            // Retry the request
            return try await performRequest(
                endpoint: endpoint,
                method: method,
                body: body,
                requiresAuth: requiresAuth,
                requiresHousehold: requiresHousehold
            )
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let errorMessage = try? decoder.decode(APIErrorResponse.self, from: data).error
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: errorMessage)
        }

        return data
    }

    // MARK: - Token Management

    private func getValidAccessToken() async throws -> String {
        // Check if current token is valid
        if await keychain.isAccessTokenValid(),
           let token = await keychain.getAccessToken() {
            return token
        }

        // Token expired or missing, need to refresh
        return try await refreshAccessToken()
    }

    private func refreshAccessToken() async throws -> String {
        // If already refreshing, wait for the result
        if isRefreshing {
            return try await withCheckedThrowingContinuation { continuation in
                refreshContinuations.append(continuation)
            }
        }

        isRefreshing = true
        defer {
            isRefreshing = false
            refreshContinuations.removeAll()
        }

        guard let refreshToken = await keychain.getRefreshToken() else {
            throw APIError.unauthorized
        }

        guard let url = URL(string: "\(baseURL)/auth/refresh") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["refresh_token": refreshToken]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            // Refresh failed, user needs to log in again
            await keychain.clearAll()
            throw APIError.unauthorized
        }

        let tokenResponse = try decoder.decode(TokenRefreshResponse.self, from: data)

        // Save new access token (default 15 min expiry since API doesn't return it)
        try await keychain.saveAccessToken(tokenResponse.accessToken, expiresIn: 900)

        // Resume any waiting requests
        for continuation in refreshContinuations {
            continuation.resume(returning: tokenResponse.accessToken)
        }

        return tokenResponse.accessToken
    }

    // MARK: - Auth Methods (no token required)

    func login(email: String, password: String) async throws -> AuthResponse {
        let body = ["email": email, "password": password]

        guard let url = URL(string: "\(baseURL)/auth/login") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            let errorMessage = try? decoder.decode(APIErrorResponse.self, from: data).error
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: errorMessage)
        }

        let authResponse = try decoder.decode(AuthResponse.self, from: data)

        // Save tokens (default 15 min expiry since API doesn't return it)
        try await keychain.saveAccessToken(authResponse.accessToken, expiresIn: 900)
        try await keychain.saveRefreshToken(authResponse.refreshToken)

        return authResponse
    }

    func register(email: String, password: String, displayName: String?) async throws -> AuthResponse {
        var body: [String: String] = ["email": email, "password": password]
        if let displayName = displayName {
            body["display_name"] = displayName
        }

        guard let url = URL(string: "\(baseURL)/auth/register") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            let errorMessage = try? decoder.decode(APIErrorResponse.self, from: data).error
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: errorMessage)
        }

        let authResponse = try decoder.decode(AuthResponse.self, from: data)

        // Save tokens (default 15 min expiry since API doesn't return it)
        try await keychain.saveAccessToken(authResponse.accessToken, expiresIn: 900)
        try await keychain.saveRefreshToken(authResponse.refreshToken)

        return authResponse
    }

    func logout() async {
        // Try to logout on server (best effort)
        if let refreshToken = await keychain.getRefreshToken() {
            try? await requestWithoutResponse(
                endpoint: "/auth/logout",
                method: .post,
                body: ["refresh_token": refreshToken],
                requiresAuth: true,
                requiresHousehold: false
            )
        }

        // Clear local tokens
        await keychain.clearAll()
        householdId = nil
    }

    func hasValidSession() async -> Bool {
        await keychain.getRefreshToken() != nil
    }

    // MARK: - Receipt Upload

    /// Upload a receipt image for a transaction
    func uploadReceipt(transactionId: Int, imageData: Data, filename: String) async throws -> Transaction {
        let accessToken = try await getValidAccessToken()

        guard let householdId = householdId else {
            throw APIError.noHouseholdSelected
        }

        guard let url = URL(string: "\(baseURL)/transactions/\(transactionId)/receipt") else {
            throw APIError.invalidURL
        }

        // Create multipart form data
        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        request.setValue("\(householdId)", forHTTPHeaderField: "X-Household-ID")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Add file data
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            let errorMessage = try? decoder.decode(APIErrorResponse.self, from: data).error
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: errorMessage)
        }

        struct ReceiptResponse: Codable {
            let transaction: Transaction
            let receiptUrl: String

            enum CodingKeys: String, CodingKey {
                case transaction
                case receiptUrl = "receipt_url"
            }
        }

        let receiptResponse = try decoder.decode(ReceiptResponse.self, from: data)
        return receiptResponse.transaction
    }

    /// Delete a receipt from a transaction
    func deleteReceipt(transactionId: Int) async throws -> Transaction {
        let response: TransactionResponse = try await request(
            endpoint: "/transactions/\(transactionId)/receipt",
            method: .delete,
            requiresAuth: true
        )
        return response.transaction
    }

    // MARK: - Bank Import Upload

    /// Upload bank statement files to create an import session
    func uploadBankStatements(files: [(data: Data, filename: String, mimeType: String)]) async throws -> ImportSessionResponse {
        let accessToken = try await getValidAccessToken()

        guard let householdId = householdId else {
            throw APIError.noHouseholdSelected
        }

        guard let url = URL(string: "\(baseURL)/import/sessions") else {
            throw APIError.invalidURL
        }

        // Create multipart form data
        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        request.setValue("\(householdId)", forHTTPHeaderField: "X-Household-ID")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Add each file
        for file in files {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"files\"; filename=\"\(file.filename)\"\r\n".data(using: .utf8)!)
            body.append("Content-Type: \(file.mimeType)\r\n\r\n".data(using: .utf8)!)
            body.append(file.data)
            body.append("\r\n".data(using: .utf8)!)
        }
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let errorMessage = try? decoder.decode(APIErrorResponse.self, from: data).error
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: errorMessage)
        }

        return try decoder.decode(ImportSessionResponse.self, from: data)
    }
}

// MARK: - HTTP Method

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case delete = "DELETE"
}
