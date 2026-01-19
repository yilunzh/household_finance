import UIKit

enum ImageCompressor {
    /// Maximum width for receipt images
    static let maxWidth: CGFloat = 1200

    /// Maximum file size in bytes (1MB)
    static let maxFileSize = 1_000_000

    /// Compress and resize an image for upload
    /// - Parameter image: The original UIImage
    /// - Returns: Compressed JPEG data, or nil if compression fails
    static func compress(_ image: UIImage) -> Data? {
        // Resize if needed
        let resized = resizeIfNeeded(image)

        // Start with high quality and reduce until under max size
        var quality: CGFloat = 0.8
        var data = resized.jpegData(compressionQuality: quality)

        while let currentData = data, currentData.count > maxFileSize, quality > 0.1 {
            quality -= 0.1
            data = resized.jpegData(compressionQuality: quality)
        }

        return data
    }

    /// Resize image if width exceeds maxWidth, maintaining aspect ratio
    private static func resizeIfNeeded(_ image: UIImage) -> UIImage {
        guard image.size.width > maxWidth else { return image }

        let scale = maxWidth / image.size.width
        let newHeight = image.size.height * scale
        let newSize = CGSize(width: maxWidth, height: newHeight)

        let renderer = UIGraphicsImageRenderer(size: newSize)
        return renderer.image { _ in
            image.draw(in: CGRect(origin: .zero, size: newSize))
        }
    }
}
