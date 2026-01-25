import SwiftUI
import UIKit

// MARK: - Haptic Manager
/// Centralized haptic feedback for consistent tactile experience.

enum HapticManager {

    // MARK: - Impact Feedback
    /// Standard impact feedback for various intensities.

    /// Light impact - subtle tap feedback
    static func light() {
        impact(.light)
    }

    /// Medium impact - standard feedback
    static func medium() {
        impact(.medium)
    }

    /// Heavy impact - strong feedback
    static func heavy() {
        impact(.heavy)
    }

    /// Soft impact - gentle feedback
    static func soft() {
        impact(.soft)
    }

    /// Rigid impact - firm feedback
    static func rigid() {
        impact(.rigid)
    }

    private static func impact(_ style: UIImpactFeedbackGenerator.FeedbackStyle) {
        let generator = UIImpactFeedbackGenerator(style: style)
        generator.prepare()
        generator.impactOccurred()
    }

    // MARK: - Notification Feedback
    /// Semantic feedback for specific events.

    /// Success feedback - task completed successfully
    static func success() {
        notification(.success)
    }

    /// Warning feedback - caution required
    static func warning() {
        notification(.warning)
    }

    /// Error feedback - something went wrong
    static func error() {
        notification(.error)
    }

    private static func notification(_ type: UINotificationFeedbackGenerator.FeedbackType) {
        let generator = UINotificationFeedbackGenerator()
        generator.prepare()
        generator.notificationOccurred(type)
    }

    // MARK: - Selection Feedback
    /// Selection changed feedback.

    static func selection() {
        let generator = UISelectionFeedbackGenerator()
        generator.prepare()
        generator.selectionChanged()
    }

    // MARK: - Contextual Feedback
    /// Convenience methods for specific UI contexts.

    /// Button tap - light impact
    static func buttonTap() {
        light()
    }

    /// Tab selection - selection feedback
    static func tabSelected() {
        selection()
    }

    /// Item deleted - medium impact
    static func deleted() {
        medium()
    }

    /// Pull to refresh - soft impact
    static func refresh() {
        soft()
    }

    /// Form submitted - success notification
    static func submitted() {
        success()
    }

    /// Navigation - light impact
    static func navigate() {
        light()
    }

    /// Toggle switched - selection feedback
    static func toggle() {
        selection()
    }

    /// Drag started/ended - light impact
    static func drag() {
        light()
    }

    /// Long press recognized - medium impact
    static func longPress() {
        medium()
    }

    /// Swipe action triggered - rigid impact
    static func swipeAction() {
        rigid()
    }
}

// MARK: - View Extension for Haptic Feedback

extension View {

    /// Add haptic feedback to a tap gesture.
    func hapticTap(_ feedback: @escaping () -> Void = HapticManager.buttonTap) -> some View {
        self.simultaneousGesture(
            TapGesture().onEnded { _ in
                feedback()
            }
        )
    }

    /// Add success haptic when a condition becomes true.
    func hapticOnSuccess(_ condition: Bool) -> some View {
        self.onChange(of: condition) { _, newValue in
            if newValue {
                HapticManager.success()
            }
        }
    }

    /// Add error haptic when a condition becomes true.
    func hapticOnError(_ condition: Bool) -> some View {
        self.onChange(of: condition) { _, newValue in
            if newValue {
                HapticManager.error()
            }
        }
    }
}
