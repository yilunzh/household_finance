import SwiftUI

// MARK: - Custom Tab Bar
/// Kawaii cat-themed tab bar replacing the system tab bar.

struct CustomTabBar: View {
    @Binding var selectedTab: Tab
    @Environment(\.colorScheme) private var colorScheme

    // MARK: - Tab Definition
    enum Tab: Int, CaseIterable, Identifiable {
        case transactions = 0
        case reconciliation = 1
        case budget = 2
        case settings = 3

        var id: Int { rawValue }

        var icon: CatIcon.Name {
            switch self {
            case .transactions: return .ledger
            case .reconciliation: return .highfive
            case .budget: return .coins
            case .settings: return .gear
            }
        }

        var title: String {
            switch self {
            case .transactions: return "Transactions"
            case .reconciliation: return "Summary"
            case .budget: return "Budget"
            case .settings: return "Settings"
            }
        }
    }

    var body: some View {
        HStack(spacing: 0) {
            ForEach(Tab.allCases) { tab in
                TabBarItem(
                    tab: tab,
                    isSelected: selectedTab == tab
                ) {
                    HapticManager.tabSelected()
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        selectedTab = tab
                    }
                }
            }
        }
        .padding(.horizontal, Spacing.sm)
        .padding(.top, Spacing.sm)
        .padding(.bottom, bottomPadding)
        .background(
            backgroundColor
                .shadow(color: Color.warm900.opacity(0.08), radius: 12, x: 0, y: -4)
                .ignoresSafeArea(edges: .bottom)
        )
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundCardDark : .backgroundCard
    }

    private var bottomPadding: CGFloat {
        // Account for home indicator on devices without home button
        let window = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap { $0.windows }
            .first { $0.isKeyWindow }

        let safeAreaBottom = window?.safeAreaInsets.bottom ?? 0
        return safeAreaBottom > 0 ? safeAreaBottom : Spacing.sm
    }
}

// MARK: - Tab Bar Item

struct TabBarItem: View {
    let tab: CustomTabBar.Tab
    let isSelected: Bool
    let action: () -> Void

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        Button(action: action) {
            VStack(spacing: Spacing.xxs) {
                ZStack {
                    // Background pill for selected state
                    if isSelected {
                        Capsule()
                            .fill(selectedBackground)
                            .frame(width: 56, height: 32)
                    }

                    CatIcon(
                        name: tab.icon,
                        size: .lg,
                        color: iconColor
                    )
                    .scaleEffect(isSelected ? 1.1 : 1.0)
                }
                .frame(height: 32)

                Text(tab.title)
                    .font(.labelSmall)
                    .foregroundColor(textColor)
            }
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private var selectedBackground: Color {
        colorScheme == .dark ? Color.terracotta700.opacity(0.3) : Color.terracotta100
    }

    private var iconColor: Color {
        isSelected ? .brandPrimary : (colorScheme == .dark ? .warm500 : .warm400)
    }

    private var textColor: Color {
        isSelected ? .brandPrimary : (colorScheme == .dark ? .warm500 : .warm400)
    }
}

// MARK: - Tab Bar Container
/// Wrapper view that provides custom tab bar with content.

struct TabBarContainer<Content: View>: View {
    @Binding var selectedTab: CustomTabBar.Tab
    let content: Content

    @Environment(\.colorScheme) private var colorScheme

    init(
        selectedTab: Binding<CustomTabBar.Tab>,
        @ViewBuilder content: () -> Content
    ) {
        self._selectedTab = selectedTab
        self.content = content()
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            // Main content
            content
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(backgroundColor.ignoresSafeArea())

            // Custom tab bar
            CustomTabBar(selectedTab: $selectedTab)
        }
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

// MARK: - Preview

#Preview("Custom Tab Bar") {
    struct PreviewWrapper: View {
        @State private var selectedTab: CustomTabBar.Tab = .transactions

        var body: some View {
            TabBarContainer(selectedTab: $selectedTab) {
                Group {
                    switch selectedTab {
                    case .transactions:
                        VStack {
                            Text("Transactions")
                                .font(.displayLarge)
                            Spacer()
                        }
                        .padding(.top, 100)
                    case .reconciliation:
                        Text("Reconciliation")
                    case .budget:
                        Text("Budget")
                    case .settings:
                        Text("Settings")
                    }
                }
            }
        }
    }

    return PreviewWrapper()
}

#Preview("Tab Bar Dark Mode") {
    struct PreviewWrapper: View {
        @State private var selectedTab: CustomTabBar.Tab = .reconciliation

        var body: some View {
            TabBarContainer(selectedTab: $selectedTab) {
                Text("Dark Mode Preview")
            }
            .preferredColorScheme(.dark)
        }
    }

    return PreviewWrapper()
}
