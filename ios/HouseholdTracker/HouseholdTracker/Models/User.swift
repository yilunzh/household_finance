import Foundation

struct User: Codable, Identifiable, Sendable {
    let id: Int
    let email: String
    let name: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case name
        case createdAt = "created_at"
    }
}

// Household info returned in auth response (different from full Household model)
struct UserHousehold: Codable, Identifiable, Sendable, Hashable {
    let id: Int
    let name: String
    let role: String
    let displayName: String
    let joinedAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case role
        case displayName = "display_name"
        case joinedAt = "joined_at"
    }
}

struct AuthResponse: Codable, Sendable {
    let accessToken: String
    let refreshToken: String
    let user: User
    let households: [UserHousehold]

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case user
        case households
    }
}

struct TokenRefreshResponse: Codable, Sendable {
    let accessToken: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
    }
}
