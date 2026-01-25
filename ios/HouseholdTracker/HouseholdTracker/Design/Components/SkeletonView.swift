import SwiftUI

/// A shimmering skeleton placeholder for loading states
struct SkeletonView: View {
    let width: CGFloat?
    let height: CGFloat

    @State private var isAnimating = false

    init(width: CGFloat? = nil, height: CGFloat = 16) {
        self.width = width
        self.height = height
    }

    var body: some View {
        RoundedRectangle(cornerRadius: CornerRadius.small)
            .fill(
                LinearGradient(
                    colors: [
                        Color.warm200,
                        Color.warm100,
                        Color.warm200
                    ],
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .frame(width: width, height: height)
            .mask(
                RoundedRectangle(cornerRadius: CornerRadius.small)
            )
            .overlay(
                GeometryReader { geometry in
                    RoundedRectangle(cornerRadius: CornerRadius.small)
                        .fill(
                            LinearGradient(
                                colors: [
                                    .clear,
                                    Color.white.opacity(0.4),
                                    .clear
                                ],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geometry.size.width * 0.6)
                        .offset(x: isAnimating ? geometry.size.width : -geometry.size.width * 0.6)
                }
                .mask(
                    RoundedRectangle(cornerRadius: CornerRadius.small)
                )
            )
            .onAppear {
                withAnimation(
                    .linear(duration: 1.5)
                    .repeatForever(autoreverses: false)
                ) {
                    isAnimating = true
                }
            }
    }
}

/// A skeleton placeholder for text lines
struct SkeletonText: View {
    let lines: Int
    let lastLineWidth: CGFloat

    init(lines: Int = 1, lastLineWidth: CGFloat = 0.6) {
        self.lines = lines
        self.lastLineWidth = lastLineWidth
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xs) {
            ForEach(0..<lines, id: \.self) { index in
                if index == lines - 1 && lines > 1 {
                    SkeletonView(height: 14)
                        .frame(maxWidth: .infinity)
                        .frame(width: UIScreen.main.bounds.width * lastLineWidth, alignment: .leading)
                } else {
                    SkeletonView(height: 14)
                }
            }
        }
    }
}

/// A skeleton placeholder for a transaction row
struct SkeletonTransactionRow: View {
    @Environment(\.colorScheme) private var colorScheme

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    var body: some View {
        HStack(spacing: Spacing.md) {
            // Category icon placeholder
            SkeletonView(width: 40, height: 40)
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: Spacing.xs) {
                // Merchant name
                SkeletonView(width: 120, height: 16)

                // Date and category
                HStack(spacing: Spacing.xs) {
                    SkeletonView(width: 60, height: 12)
                    SkeletonView(width: 50, height: 12)
                }
            }

            Spacer()

            VStack(alignment: .trailing, spacing: Spacing.xs) {
                // Amount
                SkeletonView(width: 70, height: 18)

                // Paid by
                SkeletonView(width: 50, height: 12)
            }
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
    }
}

/// A skeleton placeholder for a card section
struct SkeletonCard: View {
    @Environment(\.colorScheme) private var colorScheme

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SkeletonView(width: 100, height: 14)

            SkeletonView(height: 20)

            HStack(spacing: Spacing.md) {
                SkeletonView(height: 14)
                SkeletonView(height: 14)
            }
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
    }
}

/// A skeleton placeholder for the reconciliation summary
struct SkeletonReconciliationSummary: View {
    @Environment(\.colorScheme) private var colorScheme

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundSecondary
    }

    var body: some View {
        VStack(spacing: Spacing.lg) {
            // Summary card
            VStack(spacing: Spacing.md) {
                HStack {
                    SkeletonView(width: 80, height: 14)
                    Spacer()
                    SkeletonView(width: 100, height: 24)
                }

                Divider().background(Color.warm200)

                HStack {
                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        SkeletonView(width: 60, height: 12)
                        SkeletonView(width: 80, height: 18)
                    }

                    Spacer()

                    VStack(alignment: .trailing, spacing: Spacing.xs) {
                        SkeletonView(width: 60, height: 12)
                        SkeletonView(width: 80, height: 18)
                    }
                }
            }
            .padding(Spacing.md)
            .background(cardBackground)
            .cornerRadius(CornerRadius.large)
            .subtleShadow()

            // Category breakdown
            VStack(spacing: Spacing.sm) {
                ForEach(0..<3, id: \.self) { _ in
                    HStack(spacing: Spacing.sm) {
                        SkeletonView(width: 24, height: 24)
                            .clipShape(Circle())
                        SkeletonView(width: 100, height: 14)
                        Spacer()
                        SkeletonView(width: 60, height: 14)
                    }
                }
            }
            .padding(Spacing.md)
            .background(cardBackground)
            .cornerRadius(CornerRadius.large)
            .subtleShadow()
        }
    }
}

/// A loading overlay with a bouncing cat icon
struct LoadingOverlay: View {
    @State private var bounceOffset: CGFloat = 0

    var body: some View {
        ZStack {
            Color.black.opacity(0.3)
                .ignoresSafeArea()

            VStack(spacing: Spacing.md) {
                CatIcon(name: .happy, size: .xxl, color: .brandPrimary)
                    .offset(y: bounceOffset)
                    .onAppear {
                        withAnimation(
                            .easeInOut(duration: 0.5)
                            .repeatForever(autoreverses: true)
                        ) {
                            bounceOffset = -10
                        }
                    }

                Text("Loading...")
                    .font(.labelLarge)
                    .foregroundColor(.textSecondary)
            }
            .padding(Spacing.xl)
            .background(Color.backgroundSecondary)
            .cornerRadius(CornerRadius.xl)
            .subtleShadow()
        }
    }
}

#Preview("Skeleton Views") {
    VStack(spacing: Spacing.lg) {
        SkeletonView(width: 200, height: 20)

        SkeletonText(lines: 3)

        SkeletonTransactionRow()

        SkeletonCard()
    }
    .padding()
    .background(Color.backgroundPrimary)
}

#Preview("Loading Overlay") {
    ZStack {
        Color.backgroundPrimary
            .ignoresSafeArea()

        LoadingOverlay()
    }
}
