import Foundation

struct Household: Codable, Identifiable, Sendable, Hashable {
    let id: Int
    let name: String
    let createdAt: String
    let role: String?
    let memberCount: Int?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case createdAt = "created_at"
        case role
        case memberCount = "member_count"
    }
}

struct HouseholdMember: Codable, Identifiable, Sendable, Hashable {
    let userId: Int
    let displayName: String
    let role: String

    var id: Int { userId }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case displayName = "display_name"
        case role
    }
}

struct HouseholdListResponse: Codable, Sendable {
    let households: [Household]
}

struct HouseholdDetailResponse: Codable, Sendable {
    let household: Household
    let members: [HouseholdMember]
}
