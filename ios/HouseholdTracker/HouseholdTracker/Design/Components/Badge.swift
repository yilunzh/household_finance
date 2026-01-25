import SwiftUI

// MARK: - Badge
/// Pill-shaped tag for labels, status indicators, and categories.

struct Badge: View {
    let text: String
    var icon: CatIcon.Name?
    var style: BadgeStyle = .default

    enum BadgeStyle {
        case `default`    // Terracotta tint
        case success      // Sage tint
        case warning      // Amber tint
        case danger       // Rose tint
        case neutral      // Warm gray tint
        case custom(background: Color, text: Color)

        var backgroundColor: Color {
            switch self {
            case .default: return .terracotta100
            case .success: return .sage100
            case .warning: return .amber100
            case .danger: return .rose100
            case .neutral: return .warm100
            case .custom(let bg, _): return bg
            }
        }

        var textColor: Color {
            switch self {
            case .default: return .terracotta700
            case .success: return .sage700
            case .warning: return .amber700
            case .danger: return .rose700
            case .neutral: return .warm700
            case .custom(_, let text): return text
            }
        }
    }

    var body: some View {
        HStack(spacing: Spacing.xxs) {
            if let icon = icon {
                CatIcon(name: icon, size: .sm, color: style.textColor)
            }
            Text(text)
                .font(.labelSmall)
        }
        .foregroundColor(style.textColor)
        .padding(.horizontal, Spacing.xs)
        .padding(.vertical, Spacing.xxxs)
        .background(style.backgroundColor)
        .cornerRadius(CornerRadius.full)
    }
}

// MARK: - Split Type Badge
/// Badge specifically for transaction split types.

struct SplitTypeBadge: View {
    let splitType: SplitType

    enum SplitType {
        case shared
        case forMember(String)
        case personal

        var text: String {
            switch self {
            case .shared: return "Shared"
            case .forMember(let name): return "For \(name)"
            case .personal: return "Personal"
            }
        }

        var emoji: String {
            switch self {
            case .shared: return "🤝"
            case .forMember: return "💝"
            case .personal: return "👤"
            }
        }

        var badgeStyle: Badge.BadgeStyle {
            switch self {
            case .shared: return .default
            case .forMember: return .custom(background: .rose100, text: .rose700)
            case .personal: return .neutral
            }
        }
    }

    var body: some View {
        Badge(
            text: "\(splitType.emoji) \(splitType.text)",
            style: splitType.badgeStyle
        )
    }
}

// MARK: - Status Badge
/// Badge for status indicators (settled, locked, pending).

struct StatusBadge: View {
    let status: Status

    enum Status {
        case settled
        case locked
        case pending
        case overBudget
        case underBudget

        var text: String {
            switch self {
            case .settled: return "Settled"
            case .locked: return "Locked"
            case .pending: return "Pending"
            case .overBudget: return "Over Budget"
            case .underBudget: return "Under Budget"
            }
        }

        var icon: CatIcon.Name {
            switch self {
            case .settled: return .celebrate
            case .locked: return .lock
            case .pending: return .clock
            case .overBudget: return .worried
            case .underBudget: return .happy
            }
        }

        var badgeStyle: Badge.BadgeStyle {
            switch self {
            case .settled: return .success
            case .locked: return .neutral
            case .pending: return .warning
            case .overBudget: return .danger
            case .underBudget: return .success
            }
        }
    }

    var body: some View {
        Badge(
            text: status.text,
            icon: status.icon,
            style: status.badgeStyle
        )
    }
}

// MARK: - Count Badge
/// Small circular badge for showing counts (notifications, etc.).

struct CountBadge: View {
    let count: Int
    var style: BadgeStyle = .danger

    enum BadgeStyle {
        case danger
        case brand

        var backgroundColor: Color {
            switch self {
            case .danger: return .danger
            case .brand: return .brandPrimary
            }
        }
    }

    var body: some View {
        if count > 0 {
            Text(count > 99 ? "99+" : "\(count)")
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundColor(.white)
                .padding(.horizontal, count > 9 ? 6 : 4)
                .padding(.vertical, 2)
                .background(style.backgroundColor)
                .cornerRadius(CornerRadius.full)
                .fixedSize()
        }
    }
}

// MARK: - Previews

#Preview("Badge Styles") {
    VStack(spacing: 16) {
        HStack(spacing: 8) {
            Badge(text: "Default", style: .default)
            Badge(text: "Success", style: .success)
            Badge(text: "Warning", style: .warning)
            Badge(text: "Danger", style: .danger)
            Badge(text: "Neutral", style: .neutral)
        }

        HStack(spacing: 8) {
            Badge(text: "With Icon", icon: .happy, style: .success)
            Badge(text: "Alert", icon: .alert, style: .warning)
        }
    }
    .padding()
}

#Preview("Split Type Badges") {
    HStack(spacing: 8) {
        SplitTypeBadge(splitType: .shared)
        SplitTypeBadge(splitType: .forMember("Bob"))
        SplitTypeBadge(splitType: .personal)
    }
    .padding()
}

#Preview("Status Badges") {
    VStack(spacing: 8) {
        HStack(spacing: 8) {
            StatusBadge(status: .settled)
            StatusBadge(status: .locked)
            StatusBadge(status: .pending)
        }
        HStack(spacing: 8) {
            StatusBadge(status: .overBudget)
            StatusBadge(status: .underBudget)
        }
    }
    .padding()
}

#Preview("Count Badges") {
    HStack(spacing: 16) {
        ZStack(alignment: .topTrailing) {
            CatIcon(name: .envelope, size: .lg, color: .warm600)
            CountBadge(count: 3)
                .offset(x: 8, y: -8)
        }

        ZStack(alignment: .topTrailing) {
            CatIcon(name: .envelope, size: .lg, color: .warm600)
            CountBadge(count: 42)
                .offset(x: 8, y: -8)
        }

        ZStack(alignment: .topTrailing) {
            CatIcon(name: .envelope, size: .lg, color: .warm600)
            CountBadge(count: 100)
                .offset(x: 8, y: -8)
        }
    }
    .padding()
}
