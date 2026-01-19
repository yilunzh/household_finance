import Foundation

struct User: Codable, Identifiable, Sendable {
    let id: Int
    let email: String
    let displayName: String?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case displayName = "display_name"
        case createdAt = "created_at"
    }
}

struct AuthResponse: Codable, Sendable {
    let accessToken: String
    let refreshToken: String
    let expiresIn: Int
    let user: User
    let households: [Household]

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
        case user
        case households
    }
}

struct TokenRefreshResponse: Codable, Sendable {
    let accessToken: String
    let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case expiresIn = "expires_in"
    }
}
