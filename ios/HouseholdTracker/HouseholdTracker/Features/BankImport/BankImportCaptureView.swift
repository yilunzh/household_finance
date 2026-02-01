import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

struct BankImportCaptureView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @Bindable var viewModel: BankImportViewModel
    var onSessionCreated: ((ImportSession) -> Void)?

    @State private var showCamera = false
    @State private var isDragging = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.xl) {
                    // Hero Section
                    heroSection

                    // Drop Zone
                    dropZone

                    // Action Buttons Row
                    actionButtons

                    // Selected Files
                    if hasSelectedFiles {
                        selectedFilesSection
                    }

                    Spacer(minLength: Spacing.xxl)
                }
                .padding(.horizontal, Spacing.md)
                .padding(.top, Spacing.lg)
            }
            .safeAreaInset(edge: .bottom) {
                if hasSelectedFiles {
                    bottomAction
                }
            }
            .background(backgroundColor.ignoresSafeArea())
            .navigationTitle("Import")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(.brandPrimary)
                }
            }
            .sheet(isPresented: $showCamera) {
                CameraView(onCapture: { image in
                    handleCapturedImage(image)
                    showCamera = false
                })
            }
            .alert("Error", isPresented: .init(
                get: { viewModel.error != nil },
                set: { if !$0 { viewModel.clearError() } }
            )) {
                Button("OK") { viewModel.clearError() }
            } message: {
                Text(viewModel.error ?? "")
            }
        }
    }

    // MARK: - Hero Section

    private var heroSection: some View {
        VStack(spacing: Spacing.md) {
            // Animated Icon
            ZStack {
                // Background glow
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [Color.terracotta100, Color.terracotta50.opacity(0)],
                            center: .center,
                            startRadius: 20,
                            endRadius: 50
                        )
                    )
                    .frame(width: 100, height: 100)

                // Icon container
                ZStack {
                    RoundedRectangle(cornerRadius: 20)
                        .fill(
                            LinearGradient(
                                colors: [Color.terracotta100, Color.terracotta200],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 72, height: 72)

                    CatIcon(name: .sparkle, size: .xl, color: .terracotta600)
                }
            }

            Text("Add Statement")
                .font(.displayMedium)
                .foregroundColor(textColor)

            Text("Import transactions from your bank")
                .font(.bodyMedium)
                .foregroundColor(.textSecondary)
        }
    }

    // MARK: - Drop Zone

    private var dropZone: some View {
        PhotosPicker(
            selection: $viewModel.selectedPhotos,
            maxSelectionCount: 10,
            matching: .images
        ) {
            VStack(spacing: Spacing.md) {
                // Paper Illustration
                paperIllustration
                    .padding(.bottom, Spacing.xs)

                Text("Drop files or tap to browse")
                    .font(.labelLarge)
                    .foregroundColor(.warm700)

                Text("PDF, PNG, or JPG")
                    .font(.labelSmall)
                    .foregroundColor(.warm400)
            }
            .frame(maxWidth: .infinity)
            .frame(minHeight: 180)
            .background(cardBackground)
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.xl)
                    .strokeBorder(
                        isDragging ? Color.terracotta400 : Color.warm200,
                        style: StrokeStyle(lineWidth: 2, dash: [8, 4])
                    )
            )
            .cornerRadius(CornerRadius.xl)
        }
        .buttonStyle(.plain)
    }

    private var paperIllustration: some View {
        ZStack {
            // Left paper
            PaperShape(amount: "$247")
                .rotationEffect(.degrees(-6))
                .offset(x: -20)

            // Right paper
            PaperShape(amount: "$89")
                .rotationEffect(.degrees(4))
                .offset(x: 20)
        }
        .frame(width: 100, height: 72)
    }

    // MARK: - Action Buttons

    private var actionButtons: some View {
        HStack(spacing: Spacing.sm) {
            // Camera
            CaptureActionButton(
                icon: "camera.fill",
                label: "Camera",
                backgroundColor: .sage100,
                iconColor: .sage600
            ) {
                showCamera = true
            }

            // Photos
            PhotosPicker(
                selection: $viewModel.selectedPhotos,
                maxSelectionCount: 10,
                matching: .images
            ) {
                CaptureActionButtonContent(
                    icon: "photo.fill",
                    label: "Photos",
                    backgroundColor: .terracotta100,
                    iconColor: .terracotta600
                )
            }
            .buttonStyle(.plain)

            // Files
            FilesButton(viewModel: viewModel)
        }
    }

    // MARK: - Selected Files Section

    @ViewBuilder
    private var selectedFilesSection: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Text("Ready to import")
                    .font(.labelLarge)
                    .foregroundColor(textColor)

                Spacer()

                Text("\(totalFileCount)")
                    .font(.labelMedium)
                    .fontWeight(.bold)
                    .foregroundColor(.warm600)
                    .padding(.horizontal, Spacing.sm)
                    .padding(.vertical, Spacing.xxs)
                    .background(Color.warm100)
                    .cornerRadius(CornerRadius.full)
            }

            VStack(spacing: 0) {
                ForEach(Array(allSelectedFiles.enumerated()), id: \.element.id) { index, file in
                    FileRow(
                        name: file.name,
                        type: file.type,
                        isLast: index == allSelectedFiles.count - 1
                    ) {
                        removeFile(file)
                    }
                }
            }
            .background(cardBackground)
            .cornerRadius(CornerRadius.large)
            .subtleShadow()
        }
    }

    private struct SelectedFile: Identifiable {
        let id: String
        let name: String
        let type: FileRow.FileType
        let isPhoto: Bool
        let photoIndex: Int?
        let fileURL: URL?
    }

    private var allSelectedFiles: [SelectedFile] {
        var files: [SelectedFile] = []

        for (index, _) in viewModel.selectedPhotos.enumerated() {
            files.append(SelectedFile(
                id: "photo_\(index)",
                name: "Photo \(index + 1)",
                type: .image,
                isPhoto: true,
                photoIndex: index,
                fileURL: nil
            ))
        }

        for url in viewModel.selectedFiles {
            files.append(SelectedFile(
                id: url.absoluteString,
                name: url.lastPathComponent,
                type: url.pathExtension.lowercased() == "pdf" ? .pdf : .image,
                isPhoto: false,
                photoIndex: nil,
                fileURL: url
            ))
        }

        return files
    }

    private func removeFile(_ file: SelectedFile) {
        if file.isPhoto, let index = file.photoIndex, index < viewModel.selectedPhotos.count {
            viewModel.selectedPhotos.remove(at: index)
        } else if let url = file.fileURL {
            viewModel.selectedFiles.removeAll { $0 == url }
        }
    }

    // MARK: - Bottom Action

    private var bottomAction: some View {
        VStack(spacing: 0) {
            Divider()

            PrimaryButton(
                title: viewModel.isUploading ? "Uploading..." : "Continue",
                icon: .sparkle,
                action: {
                    Task {
                        if let session = await viewModel.uploadFiles() {
                            HapticManager.success()
                            onSessionCreated?(session)
                            dismiss()
                        } else {
                            HapticManager.error()
                        }
                    }
                },
                isLoading: viewModel.isUploading,
                isDisabled: viewModel.isUploading
            )
            .padding(Spacing.md)
        }
        .background(cardBackground)
    }

    // MARK: - Helpers

    private var hasSelectedFiles: Bool {
        !viewModel.selectedPhotos.isEmpty || !viewModel.selectedFiles.isEmpty
    }

    private var totalFileCount: Int {
        viewModel.selectedPhotos.count + viewModel.selectedFiles.count
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .white
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }

    private func handleCapturedImage(_ image: UIImage) {
        if let data = image.jpegData(compressionQuality: 0.8) {
            let tempURL = FileManager.default.temporaryDirectory
                .appendingPathComponent("capture_\(Date().timeIntervalSince1970).jpg")
            try? data.write(to: tempURL)
            viewModel.selectedFiles.append(tempURL)
        }
    }
}

// MARK: - Paper Shape Illustration

private struct PaperShape: View {
    let amount: String

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            // Lines
            RoundedRectangle(cornerRadius: 2)
                .fill(Color.warm200)
                .frame(width: 25, height: 3)

            RoundedRectangle(cornerRadius: 2)
                .fill(Color.warm200)
                .frame(width: 40, height: 3)

            RoundedRectangle(cornerRadius: 2)
                .fill(Color.warm200)
                .frame(width: 30, height: 3)

            Spacer()

            // Amount
            HStack {
                Spacer()
                Text(amount)
                    .font(.system(size: 11, weight: .bold, design: .rounded))
                    .foregroundColor(.terracotta500)
            }
        }
        .padding(10)
        .frame(width: 56, height: 72)
        .background(Color.cream100)
        .cornerRadius(8)
        .shadow(color: .black.opacity(0.06), radius: 4, y: 2)
    }
}

// MARK: - Capture Action Button

private struct CaptureActionButton: View {
    let icon: String
    let label: String
    let backgroundColor: Color
    let iconColor: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            CaptureActionButtonContent(
                icon: icon,
                label: label,
                backgroundColor: backgroundColor,
                iconColor: iconColor
            )
        }
        .buttonStyle(.plain)
    }
}

private struct CaptureActionButtonContent: View {
    let icon: String
    let label: String
    let backgroundColor: Color
    let iconColor: Color

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(spacing: Spacing.xs) {
            ZStack {
                RoundedRectangle(cornerRadius: CornerRadius.medium)
                    .fill(backgroundColor)
                    .frame(width: 44, height: 44)

                Image(systemName: icon)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundColor(iconColor)
            }

            Text(label)
                .font(.labelMedium)
                .foregroundColor(colorScheme == .dark ? .warm300 : .warm700)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.md)
        .background(colorScheme == .dark ? Color.backgroundSecondaryDark : .white)
        .cornerRadius(CornerRadius.large)
        .overlay(
            RoundedRectangle(cornerRadius: CornerRadius.large)
                .stroke(Color.warm200, lineWidth: 1)
        )
    }
}

// MARK: - Files Button

private struct FilesButton: View {
    @Bindable var viewModel: BankImportViewModel
    @State private var showFilePicker = false

    var body: some View {
        Button {
            showFilePicker = true
        } label: {
            CaptureActionButtonContent(
                icon: "doc.fill",
                label: "Files",
                backgroundColor: .cream200,
                iconColor: .warm600
            )
        }
        .buttonStyle(.plain)
        .fileImporter(
            isPresented: $showFilePicker,
            allowedContentTypes: [.pdf, .image],
            allowsMultipleSelection: true
        ) { result in
            switch result {
            case .success(let urls):
                viewModel.selectedFiles.append(contentsOf: urls)
            case .failure(let error):
                viewModel.error = error.localizedDescription
            }
        }
    }
}

// MARK: - File Row

private struct FileRow: View {
    let name: String
    let type: FileType
    let isLast: Bool
    let onRemove: () -> Void

    @Environment(\.colorScheme) private var colorScheme

    enum FileType {
        case pdf, image

        var icon: String {
            switch self {
            case .pdf: return "doc.fill"
            case .image: return "photo.fill"
            }
        }
    }

    var body: some View {
        HStack(spacing: Spacing.sm) {
            // Thumbnail
            ZStack {
                RoundedRectangle(cornerRadius: CornerRadius.small)
                    .fill(Color.cream100)
                    .frame(width: 40, height: 40)

                Image(systemName: type.icon)
                    .font(.system(size: 16))
                    .foregroundColor(.terracotta500)
            }

            // File info
            VStack(alignment: .leading, spacing: 2) {
                Text(name)
                    .font(.labelLarge)
                    .foregroundColor(colorScheme == .dark ? .textPrimaryDark : .textPrimary)
                    .lineLimit(1)
            }

            Spacer()

            // Remove button
            Button(action: onRemove) {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 20))
                    .foregroundColor(.warm400)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm)
        .overlay(alignment: .bottom) {
            if !isLast {
                Divider()
                    .padding(.leading, 56)
            }
        }
    }
}

// MARK: - Camera View

struct CameraView: UIViewControllerRepresentable {
    let onCapture: (UIImage) -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onCapture: onCapture)
    }

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onCapture: (UIImage) -> Void

        init(onCapture: @escaping (UIImage) -> Void) {
            self.onCapture = onCapture
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let image = info[.originalImage] as? UIImage {
                onCapture(image)
            }
            picker.dismiss(animated: true)
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}

#Preview {
    BankImportCaptureView(viewModel: BankImportViewModel())
}
