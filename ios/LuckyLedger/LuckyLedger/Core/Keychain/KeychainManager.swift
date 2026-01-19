import Foundation
import Security

actor KeychainManager {
    static let shared = KeychainManager()

    private let service = "com.luckyledger.app"

    private enum Keys {
        static let accessToken = "accessToken"
        static let refreshToken = "refreshToken"
        static let tokenExpiry = "tokenExpiry"
    }

    private init() {}

    // MARK: - Access Token

    func saveAccessToken(_ token: String, expiresIn: Int) throws {
        try save(key: Keys.accessToken, data: token.data(using: .utf8)!)

        let expiryDate = Date().addingTimeInterval(TimeInterval(expiresIn))
        let expiryData = try JSONEncoder().encode(expiryDate)
        try save(key: Keys.tokenExpiry, data: expiryData)
    }

    func getAccessToken() -> String? {
        guard let data = load(key: Keys.accessToken) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func isAccessTokenValid() -> Bool {
        guard let expiryData = load(key: Keys.tokenExpiry),
              let expiryDate = try? JSONDecoder().decode(Date.self, from: expiryData) else {
            return false
        }
        // Consider token invalid if it expires within 60 seconds
        return expiryDate > Date().addingTimeInterval(60)
    }

    // MARK: - Refresh Token

    func saveRefreshToken(_ token: String) throws {
        try save(key: Keys.refreshToken, data: token.data(using: .utf8)!)
    }

    func getRefreshToken() -> String? {
        guard let data = load(key: Keys.refreshToken) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    // MARK: - Clear All

    func clearAll() {
        delete(key: Keys.accessToken)
        delete(key: Keys.refreshToken)
        delete(key: Keys.tokenExpiry)
    }

    // MARK: - Private Helpers

    private func save(key: String, data: Data) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]

        // Delete existing item first
        SecItemDelete(query as CFDictionary)

        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.saveFailed(status)
        }
    }

    private func load(key: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess else { return nil }
        return result as? Data
    }

    private func delete(key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key
        ]

        SecItemDelete(query as CFDictionary)
    }
}

enum KeychainError: Error {
    case saveFailed(OSStatus)
    case loadFailed(OSStatus)
}
