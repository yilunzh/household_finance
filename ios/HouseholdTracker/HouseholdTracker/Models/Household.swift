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
    let email: String?
    let name: String?
    let joinedAt: String?

    var id: Int { userId }

    var isOwner: Bool { role == "owner" }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case displayName = "display_name"
        case role
        case email
        case name
        case joinedAt = "joined_at"
    }
}

struct HouseholdListResponse: Codable, Sendable {
    let households: [Household]
}

struct HouseholdDetailResponse: Codable, Sendable {
    let household: Household
    let members: [HouseholdMember]
}

struct HouseholdResponse: Codable, Sendable {
    let household: Household
}

struct MemberResponse: Codable, Sendable {
    let member: HouseholdMember
}

struct MembersResponse: Codable, Sendable {
    let members: [HouseholdMember]
}

struct SuccessResponse: Codable, Sendable {
    let success: Bool
}
