import SwiftUI

// MARK: - Lucky Ledger Spacing System
// Consistent spacing scale used throughout the app

/// Spacing values for padding, margins, and gaps
enum Spacing {
    /// 2pt - Minimal spacing
    static let xxxs: CGFloat = 2

    /// 4pt - Extra extra small
    static let xxs: CGFloat = 4

    /// 8pt - Extra small
    static let xs: CGFloat = 8

    /// 12pt - Small
    static let sm: CGFloat = 12

    /// 16pt - Medium (default)
    static let md: CGFloat = 16

    /// 20pt - Large
    static let lg: CGFloat = 20

    /// 24pt - Extra large
    static let xl: CGFloat = 24

    /// 32pt - Extra extra large
    static let xxl: CGFloat = 32

    /// 48pt - Maximum
    static let xxxl: CGFloat = 48
}

// MARK: - Corner Radius

/// Corner radius values for rounded elements
enum CornerRadius {
    /// 8pt - Small elements (badges, small buttons)
    static let small: CGFloat = 8

    /// 12pt - Medium elements (inputs, cards)
    static let medium: CGFloat = 12

    /// 16pt - Large elements (sheets, modals)
    static let large: CGFloat = 16

    /// 20pt - Extra large elements (hero cards)
    static let xl: CGFloat = 20

    /// 24pt - Extra extra large (feature cards)
    static let xxl: CGFloat = 24

    /// 9999pt - Full/pill shape
    static let full: CGFloat = 9999
}

// MARK: - Icon Sizes

/// Standard icon sizes
enum IconSize {
    /// 16pt - Small inline icons
    static let sm: CGFloat = 16

    /// 20pt - Default icon size
    static let md: CGFloat = 20

    /// 24pt - Larger icons (navigation)
    static let lg: CGFloat = 24

    /// 32pt - Tab bar icons
    static let xl: CGFloat = 32

    /// 48pt - Feature icons
    static let xxl: CGFloat = 48

    /// 64pt - Hero/empty state icons
    static let xxxl: CGFloat = 64
}

// MARK: - Shadow Definitions

/// Shadow configuration for elevated elements
struct ShadowStyle {
    let color: Color
    let radius: CGFloat
    let x: CGFloat
    let y: CGFloat

    /// Subtle shadow for cards
    static let subtle = ShadowStyle(
        color: Color.warm900.opacity(0.05),
        radius: 8,
        x: 0,
        y: 4
    )

    /// Medium shadow for elevated elements
    static let medium = ShadowStyle(
        color: Color.warm900.opacity(0.08),
        radius: 12,
        x: 0,
        y: 6
    )

    /// Strong shadow for modals and popovers
    static let strong = ShadowStyle(
        color: Color.warm900.opacity(0.15),
        radius: 20,
        x: 0,
        y: 10
    )

    /// Brand shadow for primary buttons
    static let brand = ShadowStyle(
        color: Color.terracotta500.opacity(0.3),
        radius: 4,
        x: 0,
        y: 2
    )

    /// Success shadow for success buttons
    static let success = ShadowStyle(
        color: Color.sage500.opacity(0.3),
        radius: 4,
        x: 0,
        y: 2
    )
}

// MARK: - View Extensions for Spacing

extension View {

    /// Apply standard card padding
    func cardPadding() -> some View {
        self.padding(Spacing.md)
    }

    /// Apply standard section padding
    func sectionPadding() -> some View {
        self.padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.lg)
    }

    /// Apply standard horizontal padding
    func horizontalPadding() -> some View {
        self.padding(.horizontal, Spacing.md)
    }

    /// Apply standard vertical spacing
    func verticalSpacing(_ spacing: CGFloat = Spacing.md) -> some View {
        self.padding(.vertical, spacing)
    }
}

// MARK: - View Extensions for Corners

extension View {

    /// Apply small corner radius
    func smallRadius() -> some View {
        self.cornerRadius(CornerRadius.small)
    }

    /// Apply medium corner radius
    func mediumRadius() -> some View {
        self.cornerRadius(CornerRadius.medium)
    }

    /// Apply large corner radius
    func largeRadius() -> some View {
        self.cornerRadius(CornerRadius.large)
    }

    /// Apply extra large corner radius
    func xlRadius() -> some View {
        self.cornerRadius(CornerRadius.xl)
    }

    /// Apply pill shape (full radius)
    func pillShape() -> some View {
        self.cornerRadius(CornerRadius.full)
    }
}

// MARK: - View Extensions for Shadows

extension View {

    /// Apply subtle shadow
    func subtleShadow() -> some View {
        let style = ShadowStyle.subtle
        return self.shadow(color: style.color, radius: style.radius, x: style.x, y: style.y)
    }

    /// Apply medium shadow
    func mediumShadow() -> some View {
        let style = ShadowStyle.medium
        return self.shadow(color: style.color, radius: style.radius, x: style.x, y: style.y)
    }

    /// Apply strong shadow
    func strongShadow() -> some View {
        let style = ShadowStyle.strong
        return self.shadow(color: style.color, radius: style.radius, x: style.x, y: style.y)
    }

    /// Apply brand shadow (terracotta tinted)
    func brandShadow() -> some View {
        let style = ShadowStyle.brand
        return self.shadow(color: style.color, radius: style.radius, x: style.x, y: style.y)
    }

    /// Apply success shadow (sage tinted)
    func successShadow() -> some View {
        let style = ShadowStyle.success
        return self.shadow(color: style.color, radius: style.radius, x: style.x, y: style.y)
    }
}

// MARK: - Layout Constants

enum Layout {
    /// Standard content max width for readable text
    static let maxContentWidth: CGFloat = 600

    /// Navigation bar height
    static let navBarHeight: CGFloat = 44

    /// Tab bar height (icon 32 + label ~14 + padding)
    static let tabBarHeight: CGFloat = 60

    /// Standard button height
    static let buttonHeight: CGFloat = 48

    /// Small button height
    static let buttonHeightSmall: CGFloat = 36

    /// Input field height
    static let inputHeight: CGFloat = 48

    /// Card minimum height
    static let cardMinHeight: CGFloat = 64

    /// Avatar/icon circle sizes
    static let avatarSmall: CGFloat = 32
    static let avatarMedium: CGFloat = 44
    static let avatarLarge: CGFloat = 64
}
