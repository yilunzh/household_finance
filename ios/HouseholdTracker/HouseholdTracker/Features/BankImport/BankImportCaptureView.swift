import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

struct BankImportCaptureView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @Bindable var viewModel: BankImportViewModel
    var onSessionCreated: ((ImportSession) -> Void)?

    @State private var showImagePicker = false
    @State private var showFilePicker = false
    @State private var showCamera = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.xl) {
                    // Header illustration
                    VStack(spacing: Spacing.md) {
                        ZStack {
                            Circle()
                                .fill(Color.terracotta100)
                                .frame(width: 120, height: 120)

                            CatIcon(name: .sparkle, size: .xl, color: .terracotta500)
                        }

                        Text("Import Bank Statement")
                            .font(.displayMedium)
                            .foregroundColor(textColor)

                        Text("Upload photos or PDFs of your bank statements and we'll extract the transactions automatically.")
                            .font(.bodyMedium)
                            .foregroundColor(.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, Spacing.lg)
                    }
                    .padding(.top, Spacing.lg)

                    // Upload options
                    VStack(spacing: Spacing.md) {
                        // Camera option
                        UploadOptionCard(
                            icon: .happy,
                            title: "Take Photo",
                            description: "Use your camera to capture a statement",
                            action: { showCamera = true }
                        )

                        // Photo Library option
                        PhotosPicker(
                            selection: $viewModel.selectedPhotos,
                            maxSelectionCount: 10,
                            matching: .images
                        ) {
                            UploadOptionCardContent(
                                icon: .clipboard,
                                title: "Photo Library",
                                description: "Select photos from your library"
                            )
                        }
                        .buttonStyle(.plain)

                        // Files option
                        UploadOptionCard(
                            icon: .folder,
                            title: "Choose File",
                            description: "Select PDF or image files",
                            action: { showFilePicker = true }
                        )
                    }
                    .padding(.horizontal, Spacing.md)

                    // Selected files preview
                    if !viewModel.selectedPhotos.isEmpty || !viewModel.selectedFiles.isEmpty {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            Text("Selected Files")
                                .font(.labelLarge)
                                .foregroundColor(textColor)
                                .padding(.horizontal, Spacing.md)

                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: Spacing.sm) {
                                    ForEach(0..<viewModel.selectedPhotos.count, id: \.self) { index in
                                        SelectedFileChip(
                                            name: "Photo \(index + 1)",
                                            onRemove: {
                                                viewModel.selectedPhotos.remove(at: index)
                                            }
                                        )
                                    }

                                    ForEach(viewModel.selectedFiles, id: \.absoluteString) { url in
                                        SelectedFileChip(
                                            name: url.lastPathComponent,
                                            onRemove: {
                                                viewModel.selectedFiles.removeAll { $0 == url }
                                            }
                                        )
                                    }
                                }
                                .padding(.horizontal, Spacing.md)
                            }
                        }

                        // Upload button
                        PrimaryButton(
                            title: viewModel.isUploading ? "Uploading..." : "Start Import",
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
                        .padding(.horizontal, Spacing.md)
                    }

                    Spacer(minLength: Spacing.xxl)
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
                    if let data = image.jpegData(compressionQuality: 0.8) {
                        // Convert to PhotosPickerItem workaround: save to temp and load
                        let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent("capture_\(Date().timeIntervalSince1970).jpg")
                        try? data.write(to: tempURL)
                        viewModel.selectedFiles.append(tempURL)
                    }
                    showCamera = false
                })
            }
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

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var backgroundColor: Color {
        colorScheme == .dark ? .backgroundPrimaryDark : .backgroundPrimary
    }
}

// MARK: - Upload Option Card

struct UploadOptionCard: View {
    let icon: CatIcon.Name
    let title: String
    let description: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            UploadOptionCardContent(icon: icon, title: title, description: description)
        }
        .buttonStyle(.plain)
    }
}

struct UploadOptionCardContent: View {
    let icon: CatIcon.Name
    let title: String
    let description: String
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: Spacing.md) {
            ZStack {
                Circle()
                    .fill(Color.terracotta100)
                    .frame(width: 48, height: 48)

                CatIcon(name: icon, size: .md, color: .terracotta500)
            }

            VStack(alignment: .leading, spacing: Spacing.xxxs) {
                Text(title)
                    .font(.labelLarge)
                    .foregroundColor(textColor)

                Text(description)
                    .font(.bodySmall)
                    .foregroundColor(.textSecondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(.textTertiary)
        }
        .padding(Spacing.md)
        .background(cardBackground)
        .cornerRadius(CornerRadius.large)
        .subtleShadow()
    }

    private var textColor: Color {
        colorScheme == .dark ? .textPrimaryDark : .textPrimary
    }

    private var cardBackground: Color {
        colorScheme == .dark ? .backgroundSecondaryDark : .backgroundCard
    }
}

// MARK: - Selected File Chip

struct SelectedFileChip: View {
    let name: String
    let onRemove: () -> Void

    var body: some View {
        HStack(spacing: Spacing.xs) {
            CatIcon(name: .folder, size: .sm, color: .terracotta500)

            Text(name)
                .font(.labelMedium)
                .foregroundColor(.textPrimary)
                .lineLimit(1)

            Button(action: onRemove) {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 16))
                    .foregroundColor(.warm400)
            }
        }
        .padding(.horizontal, Spacing.sm)
        .padding(.vertical, Spacing.xs)
        .background(Color.terracotta100)
        .cornerRadius(CornerRadius.medium)
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
