import SwiftUI

// MARK: - CatIcon Component
/// Renders kawaii cat icons from the asset catalog with consistent sizing and color support.

struct CatIcon: View {

    // MARK: - Icon Names
    /// All available kawaii cat icons extracted from the web app.
    enum Name: String, CaseIterable {
        // Navigation & Primary Actions
        case ledger = "cat-ledger"
        case highfive = "cat-highfive"
        case coins = "cat-coins"
        case gear = "cat-gear"
        case plus = "cat-plus"
        case menu = "cat-menu"

        // Status & Feedback
        case happy = "cat-happy"
        case worried = "cat-worried"
        case sleeping = "cat-sleeping"
        case alert = "cat-alert"
        case celebrate = "cat-celebrate"

        // Actions
        case pencil = "cat-pencil"
        case trash = "cat-trash"
        case download = "cat-download"
        case lock = "cat-lock"
        case unlock = "cat-unlock"

        // Objects & Concepts
        case house = "cat-house"
        case calendar = "cat-calendar"
        case envelope = "cat-envelope"
        case sparkle = "cat-sparkle"
        case clock = "cat-clock"
        case clipboard = "cat-clipboard"
        case folder = "cat-folder"
        case lightbulb = "cat-lightbulb"
        case heart = "cat-heart"
        case crown = "cat-crown"
        case rocket = "cat-rocket"
        case group = "cat-group"
        case silhouette = "cat-silhouette"
        case stop = "cat-stop"
        case wave = "cat-wave"

        /// Human-readable description
        var description: String {
            switch self {
            case .ledger: return "Transactions"
            case .highfive: return "Reconciliation"
            case .coins: return "Budget"
            case .gear: return "Settings"
            case .plus: return "Add"
            case .menu: return "Menu"
            case .happy: return "Success"
            case .worried: return "Warning"
            case .sleeping: return "Empty"
            case .alert: return "Alert"
            case .celebrate: return "Celebration"
            case .pencil: return "Edit"
            case .trash: return "Delete"
            case .download: return "Download"
            case .lock: return "Locked"
            case .unlock: return "Unlocked"
            case .house: return "Household"
            case .calendar: return "Calendar"
            case .envelope: return "Invitation"
            case .sparkle: return "Create"
            case .clock: return "Pending"
            case .clipboard: return "List"
            case .folder: return "Folder"
            case .lightbulb: return "Info"
            case .heart: return "Love"
            case .crown: return "Owner"
            case .rocket: return "Launch"
            case .group: return "Members"
            case .silhouette: return "User"
            case .stop: return "Stop"
            case .wave: return "Goodbye"
            }
        }
    }

    // MARK: - Icon Sizes
    /// Predefined sizes matching the design system.
    enum Size {
        case sm   // 16pt - Small inline icons
        case md   // 24pt - Default icon size
        case lg   // 32pt - Tab bar icons
        case xl   // 48pt - Feature icons
        case xxl  // 64pt - Hero/empty state icons

        var dimension: CGFloat {
            switch self {
            case .sm: return IconSize.sm
            case .md: return IconSize.lg   // 24pt for standard UI
            case .lg: return IconSize.xl   // 32pt for emphasis
            case .xl: return IconSize.xxl  // 48pt for features
            case .xxl: return IconSize.xxxl // 64pt for heroes
            }
        }
    }

    // MARK: - Properties
    let name: Name
    var size: Size = .md
    var color: Color = .warm700

    // MARK: - Body
    var body: some View {
        Image(name.rawValue)
            .resizable()
            .renderingMode(.template)
            .foregroundColor(color)
            .frame(width: size.dimension, height: size.dimension)
            .accessibilityLabel(name.description)
    }
}

// MARK: - Convenience Initializers

extension CatIcon {

    /// Create a CatIcon with a specific pixel size (for custom sizes).
    init(name: Name, pixelSize: CGFloat, color: Color = .warm700) {
        self.name = name
        self.size = .md  // Ignored when using frame directly
        self.color = color
    }
}

// MARK: - Preview

#Preview("All Icons") {
    ScrollView {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 80))], spacing: 20) {
            ForEach(CatIcon.Name.allCases, id: \.self) { icon in
                VStack(spacing: 8) {
                    CatIcon(name: icon, size: .lg, color: .terracotta500)
                    Text(icon.description)
                        .font(.labelSmall)
                        .foregroundColor(.textSecondary)
                }
            }
        }
        .padding()
    }
}

#Preview("Icon Sizes") {
    VStack(spacing: 20) {
        HStack(spacing: 20) {
            CatIcon(name: .happy, size: .sm, color: .sage500)
            CatIcon(name: .happy, size: .md, color: .sage500)
            CatIcon(name: .happy, size: .lg, color: .sage500)
            CatIcon(name: .happy, size: .xl, color: .sage500)
            CatIcon(name: .happy, size: .xxl, color: .sage500)
        }

        HStack(spacing: 20) {
            CatIcon(name: .worried, size: .lg, color: .rose500)
            CatIcon(name: .sleeping, size: .lg, color: .warm400)
            CatIcon(name: .celebrate, size: .lg, color: .amber500)
        }
    }
    .padding()
}

#Preview("Navigation Icons") {
    HStack(spacing: 32) {
        VStack(spacing: 4) {
            CatIcon(name: .ledger, size: .lg, color: .terracotta500)
            Text("Transactions")
                .font(.labelSmall)
        }
        VStack(spacing: 4) {
            CatIcon(name: .highfive, size: .lg, color: .warm400)
            Text("Summary")
                .font(.labelSmall)
        }
        VStack(spacing: 4) {
            CatIcon(name: .coins, size: .lg, color: .warm400)
            Text("Budget")
                .font(.labelSmall)
        }
        VStack(spacing: 4) {
            CatIcon(name: .gear, size: .lg, color: .warm400)
            Text("Settings")
                .font(.labelSmall)
        }
    }
    .foregroundColor(.textSecondary)
    .padding()
}
