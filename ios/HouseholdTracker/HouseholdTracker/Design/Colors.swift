import SwiftUI

// MARK: - Color Extension with Hex Initializer

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Lucky Ledger Color Palette

extension Color {

    // MARK: - Brand Colors (Terracotta Family)
    // Primary action color - warm orange-brown

    static let terracotta50 = Color(hex: "FEF6F3")
    static let terracotta100 = Color(hex: "FCE8E0")
    static let terracotta200 = Color(hex: "F9D5C7")
    static let terracotta300 = Color(hex: "F4B8A0")
    static let terracotta400 = Color(hex: "ED9370")
    static let terracotta500 = Color(hex: "E4714A")  // Primary
    static let terracotta600 = Color(hex: "D05A34")  // Pressed/Hover
    static let terracotta700 = Color(hex: "AE4728")  // Dark accent
    static let terracotta800 = Color(hex: "8F3B24")
    static let terracotta900 = Color(hex: "773423")

    // MARK: - Success Colors (Sage Family)
    // Used for success states, settlements, approval

    static let sage50 = Color(hex: "F6F9F6")
    static let sage100 = Color(hex: "E8F0E8")
    static let sage200 = Color(hex: "D4E3D4")
    static let sage300 = Color(hex: "B3CFB3")
    static let sage400 = Color(hex: "8AB38A")
    static let sage500 = Color(hex: "6B9B6B")  // Primary success
    static let sage600 = Color(hex: "558055")  // Pressed
    static let sage700 = Color(hex: "466746")  // Dark
    static let sage800 = Color(hex: "3A533A")
    static let sage900 = Color(hex: "314531")

    // MARK: - Neutral Colors (Warm Gray Family)
    // Text, borders, backgrounds, secondary elements

    static let warm50 = Color(hex: "FAFAF9")
    static let warm100 = Color(hex: "F5F5F4")
    static let warm200 = Color(hex: "E7E5E4")
    static let warm300 = Color(hex: "D6D3D1")
    static let warm400 = Color(hex: "A8A29E")
    static let warm500 = Color(hex: "78716C")
    static let warm600 = Color(hex: "57534E")
    static let warm700 = Color(hex: "44403C")
    static let warm800 = Color(hex: "292524")
    static let warm900 = Color(hex: "1C1917")

    // MARK: - Background Colors (Cream Family)
    // Subtle warm backgrounds

    static let cream50 = Color(hex: "FFFDF9")
    static let cream100 = Color(hex: "FEF9F0")
    static let cream200 = Color(hex: "FDF3E3")
    static let cream300 = Color(hex: "FBE9CE")
    static let cream400 = Color(hex: "F7D9AE")

    // MARK: - Danger Colors (Rose Family)
    // Errors, destructive actions, warnings

    static let rose50 = Color(hex: "FFF1F2")
    static let rose100 = Color(hex: "FFE4E6")
    static let rose200 = Color(hex: "FECDD3")
    static let rose300 = Color(hex: "FDA4AF")
    static let rose400 = Color(hex: "FB7185")
    static let rose500 = Color(hex: "F43F5E")  // Primary danger
    static let rose600 = Color(hex: "E11D48")  // Pressed
    static let rose700 = Color(hex: "BE123C")

    // MARK: - Warning Colors (Amber Family)
    // Caution states, pending items

    static let amber50 = Color(hex: "FFFBEB")
    static let amber100 = Color(hex: "FEF3C7")
    static let amber200 = Color(hex: "FDE68A")
    static let amber300 = Color(hex: "FCD34D")
    static let amber400 = Color(hex: "FBBF24")
    static let amber500 = Color(hex: "F59E0B")  // Primary warning
    static let amber600 = Color(hex: "D97706")  // Pressed
    static let amber700 = Color(hex: "B45309")
}

// MARK: - Semantic Color Aliases

extension Color {

    // MARK: - Brand
    static let brandPrimary = terracotta500
    static let brandPrimaryPressed = terracotta600
    static let brandPrimaryLight = terracotta100

    // MARK: - Status
    static let success = sage500
    static let successPressed = sage600
    static let successLight = sage100

    static let danger = rose500
    static let dangerPressed = rose600
    static let dangerLight = rose100

    static let warning = amber500
    static let warningPressed = amber600
    static let warningLight = amber100

    // MARK: - Text (Light Mode)
    static let textPrimary = warm900
    static let textSecondary = warm600
    static let textTertiary = warm400
    static let textPlaceholder = warm400
    static let textInverse = Color.white
    static let textLink = terracotta600

    // MARK: - Backgrounds (Light Mode)
    static let backgroundPrimary = cream50
    static let backgroundSecondary = cream100
    static let backgroundTertiary = cream200
    static let backgroundCard = Color.white
    static let backgroundInput = cream50

    // MARK: - Borders
    static let borderDefault = warm200
    static let borderFocused = terracotta400
    static let borderError = rose400

    // MARK: - Shadows
    static let shadowDefault = warm900.opacity(0.08)
    static let shadowElevated = warm900.opacity(0.12)
}

// MARK: - Dark Mode Support

extension Color {

    // MARK: - Text (Dark Mode)
    static let textPrimaryDark = warm50
    static let textSecondaryDark = warm300
    static let textTertiaryDark = warm500
    static let textPlaceholderDark = warm500

    // MARK: - Backgrounds (Dark Mode)
    static let backgroundPrimaryDark = warm900
    static let backgroundSecondaryDark = warm800
    static let backgroundTertiaryDark = warm700
    static let backgroundCardDark = warm800
    static let backgroundInputDark = warm700

    // MARK: - Borders (Dark Mode)
    static let borderDefaultDark = warm700
    static let borderFocusedDark = terracotta400
}

// MARK: - Adaptive Colors (for @Environment(\.colorScheme))

struct AppColors {
    let colorScheme: ColorScheme

    init(_ colorScheme: ColorScheme) {
        self.colorScheme = colorScheme
    }

    // Text
    var textPrimary: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    var textSecondary: Color {
        colorScheme == .dark ? .textSecondaryDark : .textSecondary
    }

    var textTertiary: Color {
        colorScheme == .dark ? .textTertiaryDark : .textTertiary
    }

    var textPlaceholder: Color {
        colorScheme == .dark ? .textPlaceholderDark : .textPlaceholder
    }

    // Backgrounds
    var backgroundPrimary: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }

    var backgroundSecondary: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    var backgroundTertiary: Color {
        colorScheme == .dark ? .backgroundTertiaryDark : .backgroundTertiary
    }

    var backgroundCard: Color {
        colorScheme == .dark ? .backgroundCardDark : .backgroundCard
    }

    var backgroundInput: Color {
        colorScheme == .dark ? .backgroundInputDark : .backgroundInput
    }

    // Borders
    var borderDefault: Color {
        colorScheme == .dark ? .borderDefaultDark : .borderDefault
    }

    var borderFocused: Color {
        colorScheme == .dark ? .borderFocusedDark : .borderFocused
    }
}

// MARK: - Environment Key for Colors

private struct AppColorsKey: EnvironmentKey {
    static let defaultValue = AppColors(.light)
}

extension EnvironmentValues {
    var appColors: AppColors {
        get { self[AppColorsKey.self] }
        set { self[AppColorsKey.self] = newValue }
    }
}

// MARK: - View Extension for Easy Access

extension View {
    func withAppColors() -> some View {
        modifier(AppColorsModifier())
    }
}

private struct AppColorsModifier: ViewModifier {
    @Environment(\.colorScheme) private var colorScheme

    func body(content: Content) -> some View {
        content.environment(\.appColors, AppColors(colorScheme))
    }
}
