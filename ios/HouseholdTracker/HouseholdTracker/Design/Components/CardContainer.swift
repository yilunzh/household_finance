import SwiftUI

// MARK: - Card Container
/// Styled card container with optional gradient background.

struct CardContainer<Content: View>: View {
    let content: Content
    var hasGradient: Bool = false
    var hasBorder: Bool = true

    @Environment(\.colorScheme) private var colorScheme

    init(
        hasGradient: Bool = false,
        hasBorder: Bool = true,
        @ViewBuilder content: () -> Content
    ) {
        self.hasGradient = hasGradient
        self.hasBorder = hasBorder
        self.content = content()
    }

    var body: some View {
        content
            .padding(Spacing.md)
            .background(cardBackground)
            .cornerRadius(CornerRadius.xl)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.xl)
                    .stroke(borderColor, lineWidth: hasBorder ? 1 : 0)
            )
            .subtleShadow()
    }

    private var cardBackground: some View {
        Group {
            if hasGradient {
                LinearGradient(
                    colors: gradientColors,
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            } else {
                backgroundColor
            }
        }
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundCardDark : .backgroundCard
    }

    private var gradientColors: [Color] {
        if colorScheme == .dark {
            return [.warm800, .warm700]
        } else {
            return [.white, .cream200]
        }
    }

    private var borderColor: Color {
        colorScheme == .dark ? .borderDefaultDark : .borderDefault
    }
}

// MARK: - Feature Card
/// Highlighted card for summary/feature sections with decorative elements.

struct FeatureCard<Content: View>: View {
    let content: Content
    var accentColor: Color = .terracotta500

    @Environment(\.colorScheme) private var colorScheme

    init(
        accentColor: Color = .terracotta500,
        @ViewBuilder content: () -> Content
    ) {
        self.accentColor = accentColor
        self.content = content()
    }

    var body: some View {
        content
            .padding(Spacing.lg)
            .background(
                ZStack {
                    // Base gradient
                    LinearGradient(
                        colors: gradientColors,
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )

                    // Decorative corner accent
                    VStack {
                        HStack {
                            Spacer()
                            Circle()
                                .fill(accentColor.opacity(0.1))
                                .frame(width: 100, height: 100)
                                .offset(x: 30, y: -30)
                        }
                        Spacer()
                    }
                }
            )
            .cornerRadius(CornerRadius.xxl)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.xxl)
                    .stroke(borderColor, lineWidth: 1)
            )
            .mediumShadow()
    }

    private var gradientColors: [Color] {
        if colorScheme == .dark {
            return [.warm800, .warm700]
        } else {
            return [.white, .cream200]
        }
    }

    private var borderColor: Color {
        colorScheme == .dark ? .borderDefaultDark : .borderDefault
    }
}

// MARK: - List Row Card
/// Card style for list items/transaction rows.

struct ListRowCard<Content: View>: View {
    let content: Content
    var isHighlighted: Bool = false

    @Environment(\.colorScheme) private var colorScheme

    init(
        isHighlighted: Bool = false,
        @ViewBuilder content: () -> Content
    ) {
        self.isHighlighted = isHighlighted
        self.content = content()
    }

    var body: some View {
        content
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
            .background(backgroundColor)
            .cornerRadius(CornerRadius.medium)
    }

    private var backgroundColor: Color {
        if isHighlighted {
            return colorScheme == .dark ? .warm700 : .cream100
        }
        return colorScheme == .dark ? .backgroundCardDark : .backgroundCard
    }
}

// MARK: - Section Card
/// Card for form sections with title.

struct SectionCard<Content: View>: View {
    let title: String?
    let content: Content

    @Environment(\.colorScheme) private var colorScheme

    init(
        title: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            if let title = title {
                Text(title.uppercased())
                    .font(.labelSmall)
                    .foregroundColor(.textTertiary)
                    .padding(.horizontal, Spacing.xs)
            }

            VStack(spacing: 0) {
                content
            }
            .background(backgroundColor)
            .cornerRadius(CornerRadius.large)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.large)
                    .stroke(borderColor, lineWidth: 1)
            )
        }
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundCardDark : .backgroundCard
    }

    private var borderColor: Color {
        colorScheme == .dark ? .borderDefaultDark : .borderDefault
    }
}

// MARK: - Section Row
/// Individual row within a SectionCard.

struct SectionRow<Content: View>: View {
    let content: Content
    var showDivider: Bool = true

    init(
        showDivider: Bool = true,
        @ViewBuilder content: () -> Content
    ) {
        self.showDivider = showDivider
        self.content = content()
    }

    var body: some View {
        VStack(spacing: 0) {
            content
                .padding(.horizontal, Spacing.md)
                .padding(.vertical, Spacing.sm)

            if showDivider {
                Divider()
                    .background(Color.borderDefault)
                    .padding(.leading, Spacing.md)
            }
        }
    }
}

// MARK: - Previews

#Preview("Card Container") {
    VStack(spacing: 16) {
        CardContainer {
            Text("Basic Card")
                .font(.bodyLarge)
        }

        CardContainer(hasGradient: true) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Gradient Card")
                    .font(.displaySmall)
                Text("With subtle background gradient")
                    .font(.bodyMedium)
                    .foregroundColor(.textSecondary)
            }
        }
    }
    .padding()
}

#Preview("Feature Card") {
    FeatureCard(accentColor: .sage500) {
        VStack(spacing: 12) {
            CatIcon(name: .celebrate, size: .xl, color: .sage500)
            Text("Monthly Summary")
                .font(.displaySmall)
            Text("Alice owes Bob $150.00")
                .font(.bodyLarge)
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity)
    }
    .padding()
}

#Preview("Section Card") {
    SectionCard(title: "Household") {
        SectionRow {
            HStack {
                CatIcon(name: .house, size: .md, color: .warm600)
                Text("Johnson Family")
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundColor(.textTertiary)
            }
        }
        SectionRow {
            HStack {
                CatIcon(name: .group, size: .md, color: .warm600)
                Text("Members (2)")
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundColor(.textTertiary)
            }
        }
        SectionRow(showDivider: false) {
            HStack {
                CatIcon(name: .envelope, size: .md, color: .warm600)
                Text("Invitations")
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundColor(.textTertiary)
            }
        }
    }
    .padding()
}
