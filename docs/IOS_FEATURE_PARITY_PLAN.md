# iOS App Feature Parity Plan

> **Status**: Approved and ready for implementation
> **Created**: 2026-01-19
> **Current Phase**: Not started

## Executive Summary

The iOS app currently implements ~40% of web app functionality. This plan outlines the work needed to achieve full feature parity, organized into prioritized phases.

---

## Current State Analysis

### iOS App Has (Working)
- Authentication (login, register, logout)
- Transaction CRUD with receipt photos
- Month-based transaction filtering
- Monthly reconciliation view with budget status
- Settle/unsettle months
- Multi-household switching
- Create new household

### iOS App Missing (Gap)

| Feature | Web Has | iOS Has | API Exists |
|---------|---------|---------|------------|
| Profile editing (name) | ✓ | ✗ | ✗ |
| Change password | ✓ | ✗ | ✗ |
| Change email | ✓ | ✗ | ✗ |
| Delete account | ✓ | ✗ | ✗ |
| Password reset | ✓ | ✗ | ✗ |
| Send invitations | ✓ | ✗ | ✗ |
| Accept invitations | ✓ | ✗ | ✗ |
| Manage household members | ✓ | ✗ | ✗ |
| Rename household | ✓ | ✗ | ✗ |
| Transaction search | ✓ | ✗ | ✓ |
| Transaction edit from detail | ✓ | ✗ | ✓ |
| Budget rule CRUD | ✓ | ✗ | ✗ |
| Split rule CRUD | ✓ | ✗ | ✗ |
| Expense type CRUD | ✓ | ✗ | ✗ |
| Auto-categorization | ✓ | ✗ | ✗ |
| CSV export | ✓ | ✗ | ✗ |

---

## Implementation Phases

### Phase 1: Profile & Account Management (High Priority)
**Goal**: Users can manage their account from iOS
**Status**: ⬜ Not started

#### Backend API Work
Add to `blueprints/api_v1/`:
- `POST /api/v1/user/profile` - Update display name
- `POST /api/v1/user/password` - Change password
- `POST /api/v1/user/email/request` - Request email change
- `POST /api/v1/user/email/cancel` - Cancel pending change
- `DELETE /api/v1/user` - Delete account
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Complete password reset

#### iOS Work
- **ProfileEditView**: Edit display name with save
- **ChangePasswordView**: Current + new password form
- **ChangeEmailView**: Request email change flow
- **DeleteAccountView**: Confirmation + deletion
- **ForgotPasswordView**: Email entry → opens Safari/web for reset (reuses existing web flow)
- Update SettingsView to link to these

**Files to modify**:
- `blueprints/api_v1/auth.py` - Add profile/password endpoints
- `ios/HouseholdTracker/Views/Settings/` - New profile views

---

### Phase 2: Invitations (High Priority)
**Goal**: Users can invite others and accept invitations from iOS
**Status**: ⬜ Not started

#### Backend API Work
Add to `blueprints/api_v1/`:
- `POST /api/v1/households/<id>/invitations` - Send invitation
- `GET /api/v1/households/<id>/invitations` - List pending invitations
- `DELETE /api/v1/invitations/<id>` - Cancel invitation
- `GET /api/v1/invitations/<token>` - Get invitation details (public)
- `POST /api/v1/invitations/<token>/accept` - Accept invitation

#### iOS Work
- **InviteMemberView**: Email entry + send invitation → returns shareable link for iOS share sheet
- **PendingInvitationsView**: List with cancel option
- **AcceptInvitationView**: Deep link handler for invitation acceptance
- Register custom URL scheme `householdtracker://` in Info.plist
- Handle deep links: `householdtracker://invite/<token>`
- Invitation sends email via server AND returns link for manual sharing

**Files to modify**:
- New file: `blueprints/api_v1/invitations.py`
- `ios/HouseholdTracker/Views/Household/` - New invitation views
- `ios/HouseholdTracker/HouseholdTrackerApp.swift` - Deep link handling

---

### Phase 3: Household Management (Medium Priority)
**Goal**: Full household admin capabilities from iOS
**Status**: ⬜ Not started

#### Backend API Work
Add to `blueprints/api_v1/households.py`:
- `PUT /api/v1/households/<id>` - Rename household
- `PUT /api/v1/households/<id>/members/<user_id>` - Update member (display name)
- `DELETE /api/v1/households/<id>/members/<user_id>` - Remove member

#### iOS Work
- **HouseholdSettingsView**: Rename, manage members
- **MemberListView**: View/remove members (owner only)
- **EditMemberView**: Change display name

**Files to modify**:
- `blueprints/api_v1/households.py`
- `ios/HouseholdTracker/Views/Household/` - Settings views

---

### Phase 4: Transaction Enhancements (Medium Priority)
**Goal**: Search, filter, and edit transactions like web app
**Status**: ⬜ Not started

#### Backend API Work
None needed - API already supports filtering

#### iOS Work
- **TransactionSearchView**: Search bar + filter sheet
- Add filters: date range, category, expense type, paid by, amount range
- **Edit mode in TransactionDetailView**: Make fields editable
- Add edit/save button to detail view

**Files to modify**:
- `ios/HouseholdTracker/Views/Transactions/TransactionsView.swift` - Add search
- `ios/HouseholdTracker/Views/Transactions/TransactionDetailView.swift` - Add editing

---

### Phase 5: Budget & Split Rules (Medium Priority)
**Goal**: Create and manage budget/split rules from iOS
**Status**: ⬜ Not started

#### Backend API Work
Add to `blueprints/api_v1/`:
- `GET /api/v1/budget-rules` - List budget rules
- `POST /api/v1/budget-rules` - Create budget rule
- `PUT /api/v1/budget-rules/<id>` - Update budget rule
- `DELETE /api/v1/budget-rules/<id>` - Delete budget rule
- `GET /api/v1/split-rules` (exists) - Already implemented
- `POST /api/v1/split-rules` - Create split rule
- `PUT /api/v1/split-rules/<id>` - Update split rule
- `DELETE /api/v1/split-rules/<id>` - Delete split rule

#### iOS Work
- **BudgetView**: New 4th tab showing budget overview (alongside Transactions, Reconciliation, Settings)
- **BudgetRulesListView**: List all budget rules
- **BudgetRuleEditView**: Create/edit budget rule form
- **SplitRulesListView**: List all split rules
- **SplitRuleEditView**: Create/edit split rule form

**Files to modify**:
- New file: `blueprints/api_v1/budget.py`
- `ios/HouseholdTracker/Views/Budget/` - New budget views
- `ios/HouseholdTracker/Views/MainTabView.swift` - Add 4th Budget tab

---

### Phase 6: Expense Types & Auto-categorization (Lower Priority)
**Goal**: Manage custom categories and auto-categorization
**Status**: ⬜ Not started

#### Backend API Work
Add to `blueprints/api_v1/config.py`:
- `POST /api/v1/expense-types` - Create expense type
- `PUT /api/v1/expense-types/<id>` - Update expense type
- `DELETE /api/v1/expense-types/<id>` - Delete expense type
- `GET /api/v1/auto-category-rules` - List rules
- `POST /api/v1/auto-category-rules` - Create rule
- `PUT /api/v1/auto-category-rules/<id>` - Update rule
- `DELETE /api/v1/auto-category-rules/<id>` - Delete rule

#### iOS Work
- **ExpenseTypesListView**: Manage custom categories
- **ExpenseTypeEditView**: Create/edit category
- **AutoCategoryRulesView**: Manage auto-categorization
- Integrate auto-suggestion when entering merchant name

**Files to modify**:
- `blueprints/api_v1/config.py`
- `ios/HouseholdTracker/Views/Settings/` - Category management views

---

### Phase 7: Export & Reporting (Lower Priority)
**Goal**: Export data from iOS
**Status**: ⬜ Not started

#### Backend API Work
- `GET /api/v1/export/transactions` - CSV export endpoint
- `GET /api/v1/export/reconciliation/<month>` - Monthly report

#### iOS Work
- Share sheet integration for CSV export
- PDF generation for reconciliation reports

---

## API Endpoints Summary

### New Endpoints Needed

| Endpoint | Method | Purpose | Phase |
|----------|--------|---------|-------|
| `/api/v1/user/profile` | PUT | Update name | 1 |
| `/api/v1/user/password` | PUT | Change password | 1 |
| `/api/v1/user/email/request` | POST | Request email change | 1 |
| `/api/v1/user/email/cancel` | POST | Cancel email change | 1 |
| `/api/v1/user` | DELETE | Delete account | 1 |
| `/api/v1/auth/forgot-password` | POST | Password reset request | 1 |
| `/api/v1/auth/reset-password` | POST | Complete reset | 1 |
| `/api/v1/households/<id>/invitations` | GET/POST | Invitations | 2 |
| `/api/v1/invitations/<id>` | DELETE | Cancel invitation | 2 |
| `/api/v1/invitations/<token>` | GET | Get invitation (public) | 2 |
| `/api/v1/invitations/<token>/accept` | POST | Accept invitation | 2 |
| `/api/v1/households/<id>` | PUT | Rename household | 3 |
| `/api/v1/households/<id>/members/<id>` | PUT/DELETE | Member management | 3 |
| `/api/v1/budget-rules` | GET/POST | Budget rules | 5 |
| `/api/v1/budget-rules/<id>` | PUT/DELETE | Budget rule CRUD | 5 |
| `/api/v1/split-rules` | POST | Create split rule | 5 |
| `/api/v1/split-rules/<id>` | PUT/DELETE | Split rule CRUD | 5 |
| `/api/v1/expense-types` | POST | Create expense type | 6 |
| `/api/v1/expense-types/<id>` | PUT/DELETE | Expense type CRUD | 6 |
| `/api/v1/auto-category-rules` | CRUD | Auto-categorization | 6 |
| `/api/v1/export/*` | GET | Data export | 7 |

---

## iOS New Views Summary

### Phase 1 Views
- `ProfileEditView.swift`
- `ChangePasswordView.swift`
- `ChangeEmailView.swift`
- `DeleteAccountView.swift`
- `ForgotPasswordView.swift`

### Phase 2 Views
- `InviteMemberView.swift`
- `PendingInvitationsView.swift`
- `AcceptInvitationView.swift`

### Phase 3 Views
- `HouseholdSettingsView.swift`
- `MemberListView.swift`

### Phase 4 Views
- `TransactionSearchView.swift`
- `TransactionFilterSheet.swift`
- Update `TransactionDetailView.swift` for editing

### Phase 5 Views
- `BudgetView.swift` (new tab)
- `BudgetRulesListView.swift`
- `BudgetRuleEditView.swift`
- `SplitRulesListView.swift`
- `SplitRuleEditView.swift`

### Phase 6 Views
- `ExpenseTypesListView.swift`
- `ExpenseTypeEditView.swift`
- `AutoCategoryRulesView.swift`

---

## Verification Plan

### Per-Phase Testing
1. **Backend**: Run `pytest tests/` after API changes
2. **iOS**: Run Maestro tests after UI changes
3. **Integration**: Manual E2E testing of full flows

### Test Files to Add
- `tests/test_api_v1_profile.py` - Profile API tests
- `tests/test_api_v1_invitations.py` - Invitation API tests
- `tests/test_api_v1_budget.py` - Budget API tests
- `ios/HouseholdTracker/maestro/profile-flow.yaml`
- `ios/HouseholdTracker/maestro/invitation-flow.yaml`
- `ios/HouseholdTracker/maestro/budget-flow.yaml`

---

## Execution Order (Confirmed)

1. **Phase 1** (Profile) - Essential for user account management
2. **Phase 2** (Invitations) - Critical for onboarding new household members
3. **Phase 4** (Transaction Enhancements) - Quick win, no API work needed
4. **Phase 3** (Household Management) - Completes household admin
5. **Phase 5** (Budget/Split Rules) - Power user feature, **4th tab in navigation**
6. **Phase 6** (Expense Types) - Nice-to-have customization
7. **Phase 7** (Export) - Lower priority reporting

---

## Key Decisions

- **Priority**: Phase 1-2 first (account management + invitations)
- **Deep Links**: Custom URL scheme `householdtracker://invite/<token>`
- **Budget UI**: Dedicated 4th tab in main navigation
- **Offline**: No offline support (online-only approach)
- **Invitations**: Email + shareable link (matches web behavior)
- **Password Reset**: Email link redirects to web (reuses existing flow)
- **Push Notifications**: Deferred - focus on core features first
- **PR Strategy**: One PR per phase (7 separate, self-contained PRs)

---

## Progress Tracking

Use this section to track progress as phases are completed:

| Phase | Backend | iOS | Tests | PR |
|-------|---------|-----|-------|-----|
| 1. Profile | ✅ | ✅ | ✅ | - |
| 2. Invitations | ✅ | ✅ | ✅ | - |
| 3. Household Mgmt | ⬜ | ⬜ | ⬜ | - |
| 4. Transaction Search | N/A | ⬜ | ⬜ | - |
| 5. Budget/Split Rules | ⬜ | ⬜ | ⬜ | - |
| 6. Expense Types | ⬜ | ⬜ | ⬜ | - |
| 7. Export | ⬜ | ⬜ | ⬜ | - |

Legend: ⬜ Not started | 🟡 In progress | ✅ Complete

### Phase 1 Details (Completed)
**Backend changes:**
- Added 6 new API endpoints to `blueprints/api_v1/auth.py`
- Added CASCADE delete to RefreshToken and DeviceToken models
- All 18 tests passing

**iOS changes:**
- Added profile endpoints to `Endpoints.swift`
- Added 6 profile methods to `AuthManager.swift`
- Added 4 settings sheets (EditName, ChangePassword, ChangeEmail, DeleteAccount)
- Added ForgotPasswordSheet to LoginView
- Updated SettingsView with Security section

### Phase 2 Details (Completed)
**Backend changes:**
- Created `blueprints/api_v1/invitations.py` with 5 new API endpoints
- POST /api/v1/households/<id>/invitations - Send invitation
- GET /api/v1/households/<id>/invitations - List pending invitations
- DELETE /api/v1/invitations/<id> - Cancel invitation
- GET /api/v1/invitations/<token> - Get invitation details (public)
- POST /api/v1/invitations/<token>/accept - Accept invitation
- All 20 tests passing in `test_api_v1_invitations.py`

**iOS changes:**
- Added invitation endpoints to `Endpoints.swift`
- Added 5 invitation methods to `AuthManager.swift`
- Created `InviteMemberView.swift` with share sheet integration
- Created `PendingInvitationsView.swift` for listing/canceling invitations
- Created `AcceptInvitationView.swift` for deep link handling
- Updated `MainTabView.swift` with Members section in Settings
- Registered `householdtracker://` URL scheme in Info.plist
- Added deep link handling in `HouseholdTrackerApp.swift`
