import SwiftUI

// MARK: - Primary Button
/// Terracotta filled button for primary actions.

struct PrimaryButton: View {
    let title: String
    var icon: CatIcon.Name?
    let action: () -> Void
    var isLoading: Bool = false
    var isDisabled: Bool = false
    var isFullWidth: Bool = true

    var body: some View {
        Button(action: {
            HapticManager.buttonTap()
            action()
        }) {
            HStack(spacing: Spacing.xs) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.8)
                } else {
                    if let icon = icon {
                        CatIcon(name: icon, size: .sm, color: .white)
                    }
                    Text(title)
                        .font(.labelLarge)
                }
            }
            .frame(maxWidth: isFullWidth ? .infinity : nil)
            .frame(height: Layout.buttonHeight)
            .padding(.horizontal, Spacing.lg)
            .background(isDisabled ? Color.warm300 : Color.brandPrimary)
            .foregroundColor(.white)
            .cornerRadius(CornerRadius.large)
            .brandShadow()
        }
        .disabled(isDisabled || isLoading)
        .scaleEffect(isLoading ? 0.98 : 1.0)
        .animation(.spring(response: 0.3), value: isLoading)
    }
}

// MARK: - Secondary Button
/// Sage filled button for success/settlement actions.

struct SecondaryButton: View {
    let title: String
    var icon: CatIcon.Name?
    let action: () -> Void
    var isLoading: Bool = false
    var isDisabled: Bool = false
    var isFullWidth: Bool = true

    var body: some View {
        Button(action: {
            HapticManager.buttonTap()
            action()
        }) {
            HStack(spacing: Spacing.xs) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.8)
                } else {
                    if let icon = icon {
                        CatIcon(name: icon, size: .sm, color: .white)
                    }
                    Text(title)
                        .font(.labelLarge)
                }
            }
            .frame(maxWidth: isFullWidth ? .infinity : nil)
            .frame(height: Layout.buttonHeight)
            .padding(.horizontal, Spacing.lg)
            .background(isDisabled ? Color.warm300 : Color.success)
            .foregroundColor(.white)
            .cornerRadius(CornerRadius.large)
            .successShadow()
        }
        .disabled(isDisabled || isLoading)
        .scaleEffect(isLoading ? 0.98 : 1.0)
        .animation(.spring(response: 0.3), value: isLoading)
    }
}

// MARK: - Danger Button
/// Rose colored button for destructive actions.

struct DangerButton: View {
    let title: String
    var icon: CatIcon.Name?
    let action: () -> Void
    var isLoading: Bool = false
    var isDisabled: Bool = false
    var style: DangerStyle = .text

    enum DangerStyle {
        case text      // Text-only style
        case outlined  // Outlined style
        case filled    // Filled background
    }

    var body: some View {
        Button(action: {
            HapticManager.warning()
            action()
        }) {
            HStack(spacing: Spacing.xs) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: textColor))
                        .scaleEffect(0.8)
                } else {
                    if let icon = icon {
                        CatIcon(name: icon, size: .sm, color: textColor)
                    }
                    Text(title)
                        .font(.labelLarge)
                }
            }
            .foregroundColor(textColor)
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
            .background(backgroundColor)
            .cornerRadius(CornerRadius.medium)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.medium)
                    .stroke(borderColor, lineWidth: style == .outlined ? 2 : 0)
            )
        }
        .disabled(isDisabled || isLoading)
    }

    private var textColor: Color {
        switch style {
        case .text, .outlined:
            return isDisabled ? .warm400 : .danger
        case .filled:
            return .white
        }
    }

    private var backgroundColor: Color {
        switch style {
        case .text:
            return .clear
        case .outlined:
            return .clear
        case .filled:
            return isDisabled ? .warm300 : .danger
        }
    }

    private var borderColor: Color {
        switch style {
        case .outlined:
            return isDisabled ? .warm300 : .danger
        default:
            return .clear
        }
    }
}

// MARK: - Ghost Button
/// Transparent button with border for tertiary actions.

struct GhostButton: View {
    let title: String
    var icon: CatIcon.Name?
    let action: () -> Void
    var isDisabled: Bool = false

    var body: some View {
        Button(action: {
            HapticManager.buttonTap()
            action()
        }) {
            HStack(spacing: Spacing.xs) {
                if let icon = icon {
                    CatIcon(name: icon, size: .sm, color: isDisabled ? .warm400 : .warm600)
                }
                Text(title)
                    .font(.labelLarge)
            }
            .foregroundColor(isDisabled ? .warm400 : .warm600)
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
            .background(Color.clear)
            .cornerRadius(CornerRadius.medium)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.medium)
                    .stroke(isDisabled ? Color.warm200 : Color.warm300, lineWidth: 2)
            )
        }
        .disabled(isDisabled)
    }
}

// MARK: - Icon Button
/// Circular button with just an icon.

struct IconButton: View {
    let icon: CatIcon.Name
    let action: () -> Void
    var size: IconButtonSize = .medium
    var style: IconButtonStyle = .ghost
    var isDisabled: Bool = false

    enum IconButtonSize {
        case small, medium, large

        var dimension: CGFloat {
            switch self {
            case .small: return 32
            case .medium: return 44
            case .large: return 56
            }
        }

        var iconSize: CatIcon.Size {
            switch self {
            case .small: return .sm
            case .medium: return .md
            case .large: return .lg
            }
        }
    }

    enum IconButtonStyle {
        case ghost      // No background
        case filled     // Brand color background
        case tinted     // Light brand color background
    }

    var body: some View {
        Button(action: {
            HapticManager.buttonTap()
            action()
        }) {
            CatIcon(name: icon, size: size.iconSize, color: iconColor)
                .frame(width: size.dimension, height: size.dimension)
                .background(backgroundColor)
                .cornerRadius(size.dimension / 2)
        }
        .disabled(isDisabled)
    }

    private var iconColor: Color {
        switch style {
        case .ghost:
            return isDisabled ? .warm400 : .warm600
        case .filled:
            return .white
        case .tinted:
            return isDisabled ? .warm400 : .brandPrimary
        }
    }

    private var backgroundColor: Color {
        switch style {
        case .ghost:
            return .clear
        case .filled:
            return isDisabled ? .warm300 : .brandPrimary
        case .tinted:
            return isDisabled ? .warm100 : .terracotta100
        }
    }
}

// MARK: - Previews

#Preview("Primary Buttons") {
    VStack(spacing: 16) {
        PrimaryButton(title: "Add Transaction", icon: .plus, action: {})
        PrimaryButton(title: "Loading...", action: {}, isLoading: true)
        PrimaryButton(title: "Disabled", action: {}, isDisabled: true)
    }
    .padding()
}

#Preview("Secondary Buttons") {
    VStack(spacing: 16) {
        SecondaryButton(title: "Mark as Settled", icon: .celebrate, action: {})
        SecondaryButton(title: "Confirm", action: {})
    }
    .padding()
}

#Preview("Danger Buttons") {
    VStack(spacing: 16) {
        DangerButton(title: "Delete", icon: .trash, action: {}, style: .text)
        DangerButton(title: "Delete", icon: .trash, action: {}, style: .outlined)
        DangerButton(title: "Delete", icon: .trash, action: {}, style: .filled)
    }
    .padding()
}

#Preview("Icon Buttons") {
    HStack(spacing: 16) {
        IconButton(icon: .plus, action: {}, style: .ghost)
        IconButton(icon: .plus, action: {}, style: .tinted)
        IconButton(icon: .plus, action: {}, style: .filled)
    }
    .padding()
}
