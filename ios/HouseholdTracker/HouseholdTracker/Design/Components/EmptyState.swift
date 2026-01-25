import SwiftUI

// MARK: - Empty State
/// Centered layout for empty data states with kawaii cat icon.

struct EmptyState: View {
    let icon: CatIcon.Name
    let title: String
    let message: String
    var actionTitle: String?
    var action: (() -> Void)?
    var secondaryActionTitle: String?
    var secondaryAction: (() -> Void)?

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(spacing: Spacing.lg) {
            // Animated icon
            CatIcon(name: icon, size: .xxl, color: iconColor)
                .modifier(GentleBounceModifier())

            // Text content
            VStack(spacing: Spacing.xs) {
                Text(title)
                    .font(.displaySmall)
                    .foregroundColor(.textSecondary)
                    .multilineTextAlignment(.center)

                Text(message)
                    .font(.bodyMedium)
                    .foregroundColor(.textTertiary)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }

            // Action buttons
            VStack(spacing: Spacing.sm) {
                if let actionTitle = actionTitle, let action = action {
                    PrimaryButton(
                        title: actionTitle,
                        icon: actionIcon,
                        action: action,
                        isFullWidth: false
                    )
                }

                if let secondaryActionTitle = secondaryActionTitle, let secondaryAction = secondaryAction {
                    GhostButton(
                        title: secondaryActionTitle,
                        action: secondaryAction
                    )
                }
            }
        }
        .padding(Spacing.xxl)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var iconColor: Color {
        switch icon {
        case .sleeping:
            return .warm400
        case .worried:
            return .rose400
        case .happy:
            return .sage500
        default:
            return colorScheme == .dark ? .warm500 : .warm400
        }
    }

    private var actionIcon: CatIcon.Name? {
        switch icon {
        case .sleeping, .ledger, .clipboard:
            return .plus
        default:
            return nil
        }
    }
}

// MARK: - Loading State
/// Loading indicator with kawaii cat animation.

struct LoadingState: View {
    var message: String = "Loading..."

    var body: some View {
        VStack(spacing: Spacing.md) {
            CatIcon(name: .clock, size: .xl, color: .warm400)
                .modifier(SpinModifier())

            Text(message)
                .font(.bodyMedium)
                .foregroundColor(.textTertiary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Error State
/// Error display with worried cat and retry option.

struct ErrorState: View {
    let title: String
    let message: String
    var retryAction: (() -> Void)?

    var body: some View {
        EmptyState(
            icon: .worried,
            title: title,
            message: message,
            actionTitle: retryAction != nil ? "Try Again" : nil,
            action: retryAction
        )
    }
}

// MARK: - Success State
/// Success display with happy/celebrate cat.

struct SuccessState: View {
    let title: String
    let message: String
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: Spacing.lg) {
            CatIcon(name: .celebrate, size: .xxl, color: .sage500)
                .modifier(CelebrateModifier())

            VStack(spacing: Spacing.xs) {
                Text(title)
                    .font(.displaySmall)
                    .foregroundColor(.textPrimary)
                    .multilineTextAlignment(.center)

                Text(message)
                    .font(.bodyMedium)
                    .foregroundColor(.textSecondary)
                    .multilineTextAlignment(.center)
            }

            if let actionTitle = actionTitle, let action = action {
                SecondaryButton(
                    title: actionTitle,
                    action: action,
                    isFullWidth: false
                )
            }
        }
        .padding(Spacing.xxl)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Animation Modifiers

struct GentleBounceModifier: ViewModifier {
    @State private var isAnimating = false

    func body(content: Content) -> some View {
        content
            .offset(y: isAnimating ? -5 : 0)
            .animation(
                Animation
                    .easeInOut(duration: 1.5)
                    .repeatForever(autoreverses: true),
                value: isAnimating
            )
            .onAppear { isAnimating = true }
    }
}

struct SpinModifier: ViewModifier {
    @State private var rotation: Double = 0

    func body(content: Content) -> some View {
        content
            .rotationEffect(.degrees(rotation))
            .animation(
                Animation
                    .linear(duration: 2)
                    .repeatForever(autoreverses: false),
                value: rotation
            )
            .onAppear { rotation = 360 }
    }
}

struct CelebrateModifier: ViewModifier {
    @State private var scale: CGFloat = 0.5
    @State private var opacity: Double = 0

    func body(content: Content) -> some View {
        content
            .scaleEffect(scale)
            .opacity(opacity)
            .onAppear {
                withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
                    scale = 1.0
                    opacity = 1.0
                }
            }
    }
}

// MARK: - Previews

#Preview("Empty States") {
    VStack {
        EmptyState(
            icon: .sleeping,
            title: "No Transactions",
            message: "You haven't added any transactions yet. Tap the button below to get started!",
            actionTitle: "Add Transaction",
            action: {}
        )
    }
}

#Preview("Loading State") {
    LoadingState(message: "Loading transactions...")
}

#Preview("Error State") {
    ErrorState(
        title: "Something went wrong",
        message: "We couldn't load your transactions. Please check your connection and try again.",
        retryAction: {}
    )
}

#Preview("Success State") {
    SuccessState(
        title: "Month Settled!",
        message: "January 2024 has been marked as settled. Great job keeping track!",
        actionTitle: "View Summary",
        action: {}
    )
}
