import SwiftUI

// MARK: - Lucky Ledger Typography System
// Uses iOS system rounded fonts to approximate web's Quicksand (display) and Nunito (body)

extension Font {

    // MARK: - Display Fonts
    // Used for headings, titles, and prominent text
    // Matches web's Quicksand - warm, friendly, slightly rounded

    /// Large display text (32pt bold rounded) - Page titles
    static let displayLarge = Font.system(size: 32, weight: .bold, design: .rounded)

    /// Medium display text (24pt semibold rounded) - Section headings
    static let displayMedium = Font.system(size: 24, weight: .semibold, design: .rounded)

    /// Small display text (20pt semibold rounded) - Card titles
    static let displaySmall = Font.system(size: 20, weight: .semibold, design: .rounded)

    // MARK: - Body Fonts
    // Used for regular content text
    // Matches web's Nunito - clean, highly legible

    /// Large body text (17pt regular rounded) - Primary content
    static let bodyLarge = Font.system(size: 17, weight: .regular, design: .rounded)

    /// Medium body text (15pt regular rounded) - Secondary content
    static let bodyMedium = Font.system(size: 15, weight: .regular, design: .rounded)

    /// Small body text (13pt regular rounded) - Tertiary content
    static let bodySmall = Font.system(size: 13, weight: .regular, design: .rounded)

    // MARK: - Label Fonts
    // Used for UI labels, buttons, form fields

    /// Large label (15pt semibold rounded) - Buttons, prominent labels
    static let labelLarge = Font.system(size: 15, weight: .semibold, design: .rounded)

    /// Medium label (13pt semibold rounded) - Form labels
    static let labelMedium = Font.system(size: 13, weight: .semibold, design: .rounded)

    /// Small label (11pt medium rounded) - Badges, tags, captions
    static let labelSmall = Font.system(size: 11, weight: .medium, design: .rounded)

    // MARK: - Amount Fonts
    // Used for currency amounts - monospaced digits for alignment

    /// Large amount (28pt bold rounded monospaced) - Hero amounts
    static let amountLarge = Font.system(size: 28, weight: .bold, design: .rounded).monospacedDigit()

    /// Medium amount (20pt semibold rounded monospaced) - Transaction amounts
    static let amountMedium = Font.system(size: 20, weight: .semibold, design: .rounded).monospacedDigit()

    /// Small amount (15pt medium rounded monospaced) - Inline amounts
    static let amountSmall = Font.system(size: 15, weight: .medium, design: .rounded).monospacedDigit()

    // MARK: - Caption Fonts
    // Used for timestamps, metadata, footnotes

    /// Caption (12pt regular rounded) - Timestamps, metadata
    static let caption = Font.system(size: 12, weight: .regular, design: .rounded)

    /// Caption emphasis (12pt medium rounded) - Emphasized metadata
    static let captionEmphasis = Font.system(size: 12, weight: .medium, design: .rounded)
}

// MARK: - Text Styles Convenience

extension View {

    /// Apply display large style
    func displayLargeStyle() -> some View {
        self.font(.displayLarge)
            .foregroundColor(.textPrimary)
    }

    /// Apply display medium style
    func displayMediumStyle() -> some View {
        self.font(.displayMedium)
            .foregroundColor(.textPrimary)
    }

    /// Apply display small style
    func displaySmallStyle() -> some View {
        self.font(.displaySmall)
            .foregroundColor(.textPrimary)
    }

    /// Apply body style
    func bodyStyle() -> some View {
        self.font(.bodyLarge)
            .foregroundColor(.textPrimary)
    }

    /// Apply secondary text style
    func secondaryStyle() -> some View {
        self.font(.bodyMedium)
            .foregroundColor(.textSecondary)
    }

    /// Apply tertiary/muted text style
    func tertiaryStyle() -> some View {
        self.font(.bodySmall)
            .foregroundColor(.textTertiary)
    }

    /// Apply label style
    func labelStyle() -> some View {
        self.font(.labelMedium)
            .foregroundColor(.textSecondary)
    }

    /// Apply amount style (positive)
    func amountStyle() -> some View {
        self.font(.amountMedium)
            .foregroundColor(.textPrimary)
    }

    /// Apply large amount style
    func amountLargeStyle() -> some View {
        self.font(.amountLarge)
            .foregroundColor(.textPrimary)
    }
}

// MARK: - Line Heights & Letter Spacing
// These can be applied via custom modifiers if needed

struct TypographyMetrics {
    /// Standard line height multiplier
    static let lineHeightNormal: CGFloat = 1.4

    /// Tight line height for headings
    static let lineHeightTight: CGFloat = 1.2

    /// Relaxed line height for body text
    static let lineHeightRelaxed: CGFloat = 1.6
}
