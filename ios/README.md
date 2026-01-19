# Household Tracker iOS App

Native iOS companion app for the household expense tracker.

## Requirements

- Xcode 15.0+
- iOS 17.0+
- [xcodegen](https://github.com/yonaskolb/XcodeGen) (for project generation)

## Setup

### 1. Install xcodegen (one time)

```bash
brew install xcodegen
```

### 2. Generate Xcode project

```bash
cd ios/HouseholdTracker
xcodegen generate
```

This creates `HouseholdTracker.xcodeproj` from `project.yml`.

### 3. Open in Xcode

```bash
open HouseholdTracker.xcodeproj
```

### 4. Configure Signing

1. In Xcode, select the HouseholdTracker target
2. Go to Signing & Capabilities
3. Select your development team
4. Xcode will automatically create provisioning profiles

### 5. Run the App

1. Select a simulator or device
2. Press Cmd+R to build and run
3. Make sure the Flask backend is running on `localhost:5001`

## Development

### Backend Connection

The app connects to `http://localhost:5001/api/v1` in debug builds. For production builds, update the `baseURL` in `NetworkManager.swift`.

### Project Structure

```
HouseholdTracker/
├── HouseholdTrackerApp.swift  # App entry point
├── ContentView.swift          # Root view with auth routing
├── MainTabView.swift          # Main navigation tabs
├── Features/
│   ├── Auth/                  # Login, AuthManager
│   ├── Transactions/          # Transaction list, add/edit
│   ├── Reconciliation/        # Monthly summary
│   └── Households/            # Household selection
├── Core/
│   ├── Network/               # API client, JWT handling
│   └── Keychain/              # Secure token storage
├── Models/                    # Data models
└── Resources/                 # Assets, config files
```

### Architecture

- **MVVM** with `@Observable` (iOS 17+)
- **async/await** for all async operations
- **Actor-based** NetworkManager for thread safety
- **Keychain** for secure token storage

## Testing

### Unit Tests

Run from Xcode (Cmd+U) or command line:

```bash
xcodebuild test -scheme HouseholdTracker -destination 'platform=iOS Simulator,name=iPhone 15'
```

### E2E Tests (Maestro)

```bash
# Install Maestro
brew install maestro

# Run tests
maestro test maestro/
```

## Building for Release

1. Update version numbers in `project.yml`
2. Run `xcodegen generate`
3. Archive: Product → Archive
4. Upload to App Store Connect

## API Endpoints

The app uses these `/api/v1/` endpoints:

| Feature | Endpoints |
|---------|-----------|
| Auth | `/auth/login`, `/auth/register`, `/auth/refresh`, `/auth/logout` |
| User | `/user/me` |
| Households | `/households`, `/households/{id}`, `/households/{id}/members` |
| Transactions | `/transactions` (GET, POST), `/transactions/{id}` (GET, PUT, DELETE) |
| Reconciliation | `/reconciliation/{month}`, `/settlement` |
| Config | `/expense-types`, `/split-rules`, `/categories` |
