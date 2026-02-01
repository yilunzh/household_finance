# Implementation Plan: Bank Import

## Status: IN PROGRESS (MVP Complete, AI extraction pending)
## Last Updated: 2026-01-31
## Depends On: architecture.md

---

## Progress Summary

| Epic | Status | Notes |
|------|--------|-------|
| E1: Backend Foundation | ✅ DONE | All models and APIs implemented |
| E2: AI Extraction | ⏳ PARTIAL | Mock service only, GPT-4V not integrated |
| E3: Review & Import | ✅ DONE | Full CRUD + import API |
| E4: Rules System | ✅ DONE | AutoCategoryRule CRUD |
| E5: iOS Capture | ✅ DONE | Camera/Photos/Files with redesigned UI |
| E6: iOS Review | ✅ DONE | Select + Categorize screens |
| E7: Notifications | ❌ NOT STARTED | Push notifications deferred |
| E8: Polish | ⏳ PARTIAL | Maestro test done, cleanup pending |

---

## Epic Overview

| Epic | Description | Stories | Complexity |
|------|-------------|---------|------------|
| E1: Backend Foundation | Data models, file storage, basic APIs | 5 stories | M |
| E2: AI Extraction | Document processing with GPT-4V | 4 stories | L |
| E3: Review & Import | Transaction review and import APIs | 4 stories | M |
| E4: Rules System | Auto-categorization rules management | 3 stories | S |
| E5: iOS Capture | Camera/photo/PDF upload from iOS | 3 stories | M |
| E6: iOS Review | Select and categorize screens | 4 stories | L |
| E7: Notifications | Push notifications for processing complete | 2 stories | S |
| E8: Polish | Error handling, edge cases, cleanup | 3 stories | M |

**Total: 28 stories**

---

## Epic 1: Backend Foundation

**Goal:** Establish data layer and file handling infrastructure
**Dependencies:** None (starting point)

### Story 1.1: Create ImportSession Model

**As a** developer
**I want** an ImportSession database model
**So that** I can track bank statement uploads through their lifecycle

**Acceptance Criteria:**
- [x] `ImportSession` model created with fields: id, household_id, user_id, status, source_files (JSON), error_message, timestamps
- [x] Status values: pending, processing, ready, completed, failed
- [x] Foreign key relationships to Household and User
- [x] Migration script runs successfully
- [x] Model can be queried by household_id and user_id

**Technical Notes:**
- Follow existing model patterns in models.py
- source_files stores JSON array of file metadata

**Test Requirements:**
- [x] Unit: Create/read/update ImportSession
- [x] Unit: Status transitions
- [x] Unit: Relationship cascades

**Complexity:** S
**Depends On:** None
**Status:** ✅ DONE

---

### Story 1.2: Create ExtractedTransaction Model

**As a** developer
**I want** an ExtractedTransaction model
**So that** I can store parsed transactions from bank statements

**Acceptance Criteria:**
- [ ] `ExtractedTransaction` model with fields: id, session_id, merchant, amount, currency, date, raw_text, confidence, expense_type_id, split_category, is_selected, status, flags (JSON)
- [ ] Status values: pending, reviewed, imported, skipped
- [ ] Relationship to ImportSession with cascade delete
- [ ] Optional relationship to ExpenseType
- [ ] Migration runs successfully

**Technical Notes:**
- flags JSON stores: needs_review, duplicate_of, ocr_uncertain, etc.
- confidence is float 0.0-1.0

**Test Requirements:**
- [ ] Unit: CRUD operations
- [ ] Unit: Cascade delete with session
- [ ] Unit: JSON flags serialization

**Complexity:** S
**Depends On:** 1.1

---

### Story 1.3: Create ImportSettings Model

**As a** user
**I want** my import preferences saved
**So that** I don't have to reconfigure each import

**Acceptance Criteria:**
- [ ] `ImportSettings` model with: user_id, default_currency, default_split_category, auto_skip_duplicates, auto_select_high_confidence
- [ ] One settings record per user (upsert pattern)
- [ ] Default values for new users: USD, shared, true, true

**Technical Notes:**
- Settings are user-scoped, not household-scoped

**Test Requirements:**
- [ ] Unit: Create default settings
- [ ] Unit: Update settings
- [ ] Unit: Get or create pattern

**Complexity:** S
**Depends On:** None

---

### Story 1.4: Implement Secure File Storage

**As a** system
**I want** uploaded files stored securely
**So that** user financial data is protected

**Acceptance Criteria:**
- [ ] Files stored in `/data/imports/` (outside web root)
- [ ] Files encrypted at rest using Fernet
- [ ] Unique filename generation (UUID + timestamp)
- [ ] File metadata stored in ImportSession.source_files
- [ ] Secure delete function (overwrite before unlink)
- [ ] Max file size: 10MB per file, 50MB per session

**Technical Notes:**
- Use cryptography.fernet for encryption
- Store encryption key in environment variable
- Clean up function for orphaned files

**Test Requirements:**
- [ ] Unit: File encryption/decryption roundtrip
- [ ] Unit: Secure delete overwrites file
- [ ] Unit: Size limit enforcement
- [ ] Integration: Upload → store → retrieve → delete

**Complexity:** M
**Depends On:** 1.1

---

### Story 1.5: Create Session Upload API

**As a** mobile app user
**I want** to upload bank statement files
**So that** I can start the import process

**Acceptance Criteria:**
- [ ] `POST /api/v1/import/sessions` accepts multipart file upload
- [ ] Supports multiple files (up to 5)
- [ ] Accepts: PDF, PNG, JPG, HEIC
- [ ] Creates ImportSession in 'pending' status
- [ ] Returns session_id for status polling
- [ ] Validates file types and sizes
- [ ] Requires JWT authentication

**Technical Notes:**
- Use Flask request.files for multipart
- Validate MIME types and magic bytes
- Return 413 for oversized files

**Test Requirements:**
- [ ] Unit: File type validation
- [ ] Unit: Size limit validation
- [ ] Integration: Upload creates session
- [ ] Integration: Multiple files per session
- [ ] Integration: Auth required

**Complexity:** M
**Depends On:** 1.1, 1.4

---

## Epic 2: AI Extraction

**Goal:** Extract transactions from uploaded documents using AI
**Dependencies:** E1 (Backend Foundation)

### Story 2.1: Create Extraction Service Interface

**As a** developer
**I want** an abstracted extraction service
**So that** I can swap AI providers without changing business logic

**Acceptance Criteria:**
- [ ] `ExtractionService` abstract base class with `extract(file_path) -> list[dict]` method
- [ ] `MockExtractionService` for testing (returns hardcoded data)
- [ ] `GPT4VExtractionService` implementation (can be stubbed initially)
- [ ] Service returns standardized transaction dict: merchant, amount, currency, date, raw_text, confidence

**Technical Notes:**
- Use dependency injection pattern
- Configure service via environment variable

**Test Requirements:**
- [ ] Unit: Mock service returns expected format
- [ ] Unit: Service selection based on config

**Complexity:** S
**Depends On:** None

---

### Story 2.2: Implement GPT-4V Extraction

**As a** system
**I want** to use GPT-4V to extract transactions
**So that** bank statements are parsed accurately

**Acceptance Criteria:**
- [ ] Sends image/PDF to OpenAI API
- [ ] Prompt instructs model to extract: merchant, amount, currency, date
- [ ] Parses structured JSON response
- [ ] Handles API errors gracefully (retry, fallback)
- [ ] Logs API usage for cost tracking
- [ ] Confidence scores based on model response

**Technical Notes:**
- Use openai Python package
- PDF needs conversion to images first (pdf2image)
- Rate limit: 3 requests/minute initially
- Store API key in environment

**Test Requirements:**
- [ ] Unit: Response parsing (mock API)
- [ ] Unit: Error handling (mock failures)
- [ ] Integration: Real API call with test image (manual/CI-skip)

**Complexity:** L
**Depends On:** 2.1

---

### Story 2.3: Implement Background Processing

**As a** user
**I want** extraction to happen in the background
**So that** I can continue using the app while waiting

**Acceptance Criteria:**
- [ ] Upload returns immediately with session_id
- [ ] Extraction runs in ThreadPoolExecutor
- [ ] Session status updates: pending → processing → ready/failed
- [ ] Error message populated on failure
- [ ] Processing timestamps recorded

**Technical Notes:**
- Use concurrent.futures.ThreadPoolExecutor
- Max 2 workers for MVP
- Consider Celery for scale (future)

**Test Requirements:**
- [ ] Unit: Status transitions
- [ ] Integration: Async processing completes
- [ ] Integration: Error handling populates message

**Complexity:** M
**Depends On:** 2.2, 1.5

---

### Story 2.4: Implement Rule Matching & Duplicate Detection

**As a** system
**I want** extracted transactions auto-categorized
**So that** users have less manual work

**Acceptance Criteria:**
- [ ] Match merchant against AutoCategoryRule (substring match)
- [ ] Apply expense_type_id and split_category from matching rule
- [ ] Detect duplicates: same merchant + amount + date (±1 day)
- [ ] Flag duplicates in ExtractedTransaction.flags
- [ ] Low confidence (< 0.7) flagged for review

**Technical Notes:**
- Use existing AutoCategoryRule model
- Fuzzy date matching: allow ±1 day variance
- Amount must match exactly

**Test Requirements:**
- [ ] Unit: Rule matching priority (most specific wins)
- [ ] Unit: Duplicate detection logic
- [ ] Unit: Flag setting for low confidence
- [ ] Integration: Full pipeline with rules

**Complexity:** M
**Depends On:** 2.3, 1.2

---

## Epic 3: Review & Import

**Goal:** Allow users to review, edit, and import extracted transactions
**Dependencies:** E2 (AI Extraction)

### Story 3.1: Get Session Status API

**As a** mobile app
**I want** to poll session status
**So that** I know when extraction is complete

**Acceptance Criteria:**
- [ ] `GET /api/v1/import/sessions/:id` returns session details
- [ ] Includes: status, created_at, processing timestamps, error_message
- [ ] Includes transaction count by status (pending, reviewed, etc.)
- [ ] 404 if session not found or wrong user
- [ ] 403 if session belongs to different user

**Technical Notes:**
- Only session owner can view (user_id check)
- Include summary stats in response

**Test Requirements:**
- [ ] Unit: Response format
- [ ] Integration: Status reflects processing state
- [ ] Integration: Auth/ownership checks

**Complexity:** S
**Depends On:** 1.1

---

### Story 3.2: List Session Transactions API

**As a** mobile app user
**I want** to see all extracted transactions
**So that** I can review and select which to import

**Acceptance Criteria:**
- [ ] `GET /api/v1/import/sessions/:id/transactions` returns transaction list
- [ ] Filterable by: status, is_selected, needs_review flag
- [ ] Sortable by: date, amount, merchant
- [ ] Includes: id, merchant, amount, date, expense_type, split_category, flags, is_selected
- [ ] Pagination support (limit/offset)

**Technical Notes:**
- Default sort: date descending
- Include expense_type name in response (join)

**Test Requirements:**
- [ ] Unit: Filter logic
- [ ] Unit: Sort logic
- [ ] Integration: Returns extracted transactions
- [ ] Integration: Pagination works

**Complexity:** M
**Depends On:** 3.1, 1.2

---

### Story 3.3: Update Transaction API

**As a** user
**I want** to edit extracted transaction details
**So that** I can fix OCR errors and assign categories

**Acceptance Criteria:**
- [ ] `PUT /api/v1/import/sessions/:sid/transactions/:tid` updates transaction
- [ ] Editable fields: merchant, amount, date, expense_type_id, split_category, is_selected
- [ ] Validates expense_type belongs to household
- [ ] Updates status to 'reviewed' after edit
- [ ] Returns updated transaction

**Technical Notes:**
- Validate expense_type_id against household's types
- Clear flags.ocr_uncertain after manual edit

**Test Requirements:**
- [ ] Unit: Field validation
- [ ] Unit: Status transition to reviewed
- [ ] Integration: Update persists
- [ ] Integration: Cross-household type rejected

**Complexity:** S
**Depends On:** 3.2

---

### Story 3.4: Import Transactions API

**As a** user
**I want** to finalize my import
**So that** selected transactions become real transactions

**Acceptance Criteria:**
- [ ] `POST /api/v1/import/sessions/:id/import` creates Transaction records
- [ ] Only imports transactions where is_selected = true
- [ ] Creates Transaction with: merchant (as description), amount, date, expense_type_id, split_category, paid_by (current user)
- [ ] Updates ExtractedTransaction status to 'imported' or 'skipped'
- [ ] Updates ImportSession status to 'completed'
- [ ] Deletes source files immediately after import
- [ ] Returns count of imported transactions

**Technical Notes:**
- Use database transaction for atomicity
- Call secure_delete for all source files
- Log to ImportAuditLog

**Test Requirements:**
- [ ] Unit: Only selected transactions imported
- [ ] Unit: Transaction fields mapped correctly
- [ ] Integration: Full import flow
- [ ] Integration: Files deleted after import
- [ ] Integration: Audit log created

**Complexity:** M
**Depends On:** 3.3, 1.4

---

## Epic 4: Rules System

**Goal:** Allow users to manage auto-categorization rules
**Dependencies:** None (can parallel with other epics)

### Story 4.1: List Rules API

**As a** user
**I want** to see my categorization rules
**So that** I can review how imports will be categorized

**Acceptance Criteria:**
- [ ] `GET /api/v1/import/rules` returns user's rules
- [ ] Includes: id, merchant_pattern, expense_type_id, expense_type_name, split_category
- [ ] Filtered by current household
- [ ] Sorted by merchant_pattern alphabetically

**Technical Notes:**
- Use existing AutoCategoryRule model
- Join with ExpenseType for name

**Test Requirements:**
- [ ] Unit: Response format
- [ ] Integration: Returns household rules
- [ ] Integration: Excludes other household rules

**Complexity:** S
**Depends On:** None

---

### Story 4.2: Create/Update Rule API

**As a** user
**I want** to create and edit rules
**So that** future imports are categorized correctly

**Acceptance Criteria:**
- [ ] `POST /api/v1/import/rules` creates new rule
- [ ] `PUT /api/v1/import/rules/:id` updates rule
- [ ] Required: merchant_pattern, expense_type_id
- [ ] Optional: split_category (defaults to 'shared')
- [ ] Validates expense_type belongs to household
- [ ] Validates merchant_pattern uniqueness per household

**Technical Notes:**
- merchant_pattern is case-insensitive match
- Normalize pattern (lowercase, trim)

**Test Requirements:**
- [ ] Unit: Validation logic
- [ ] Unit: Uniqueness constraint
- [ ] Integration: Create persists
- [ ] Integration: Update persists

**Complexity:** S
**Depends On:** 4.1

---

### Story 4.3: Delete Rule API

**As a** user
**I want** to delete rules
**So that** I can remove incorrect categorizations

**Acceptance Criteria:**
- [ ] `DELETE /api/v1/import/rules/:id` deletes rule
- [ ] Returns 404 if rule not found
- [ ] Returns 403 if rule belongs to different household
- [ ] Returns 204 on success

**Technical Notes:**
- Soft delete not needed; rules are cheap to recreate

**Test Requirements:**
- [ ] Integration: Delete removes rule
- [ ] Integration: Cross-household delete rejected

**Complexity:** S
**Depends On:** 4.1

---

## Epic 5: iOS Capture

**Goal:** Build iOS interface for uploading bank statements
**Dependencies:** E1 (Backend Foundation)

### Story 5.1: Capture Screen UI

**As a** iOS user
**I want** a screen to upload bank statements
**So that** I can start the import process

**Acceptance Criteria:**
- [ ] New "Import" tab or button on Transactions screen
- [ ] CaptureView with three options: Camera, Photo Library, Files
- [ ] Visual design matches prototype (terracotta/sage/cream)
- [ ] Shows selected files with remove option
- [ ] "Process" button disabled until files selected
- [ ] Maximum 5 files indicator

**Technical Notes:**
- Use PHPickerViewController for photos
- Use UIDocumentPickerViewController for files
- Use UIImagePickerController for camera

**Test Requirements:**
- [ ] E2E: Navigate to capture screen
- [ ] E2E: Select photo shows in list
- [ ] E2E: Remove file works

**Complexity:** M
**Depends On:** None (UI only)

---

### Story 5.2: File Upload Implementation

**As a** iOS user
**I want** to upload my selected files
**So that** they can be processed

**Acceptance Criteria:**
- [ ] Tapping "Process" uploads files to backend
- [ ] Shows upload progress indicator
- [ ] Handles upload errors with retry option
- [ ] Stores session_id for status polling
- [ ] Transitions to processing state after upload

**Technical Notes:**
- Use URLSession with multipart/form-data
- Compress images before upload (max 2MB each)
- Handle network errors gracefully

**Test Requirements:**
- [ ] Unit: Multipart request formatting
- [ ] Unit: Image compression
- [ ] E2E: Upload flow (with mock server)

**Complexity:** M
**Depends On:** 5.1, 1.5

---

### Story 5.3: Processing Status UI

**As a** iOS user
**I want** to see processing progress
**So that** I know when my import is ready

**Acceptance Criteria:**
- [ ] Processing screen shows spinner/animation
- [ ] Polls session status every 3 seconds
- [ ] Shows "Processing your statement..." message
- [ ] Transitions to Select screen when status = 'ready'
- [ ] Shows error message if status = 'failed' with retry option

**Technical Notes:**
- Use Timer for polling
- Cancel timer when view disappears
- Deep link support for push notification

**Test Requirements:**
- [ ] Unit: Polling logic
- [ ] E2E: Transition on ready status

**Complexity:** S
**Depends On:** 5.2, 3.1

---

## Epic 6: iOS Review

**Goal:** Build iOS interface for reviewing and importing transactions
**Dependencies:** E3 (Review & Import APIs), E5 (iOS Capture)

### Story 6.1: Select Screen - Transaction List

**As a** iOS user
**I want** to see all extracted transactions
**So that** I can choose which to import

**Acceptance Criteria:**
- [ ] SelectView shows transaction list in table format
- [ ] Columns: checkbox, merchant, type, split, date, amount
- [ ] Tab bar: Ready | Needs Attention | Skipped | Already Imported
- [ ] Select all / deselect all functionality
- [ ] Filter dropdowns for expense type and split
- [ ] Visual design matches prototype

**Technical Notes:**
- Use SwiftUI List with custom row
- Tab counts update dynamically
- Consider LazyVStack for performance

**Test Requirements:**
- [ ] E2E: Screen loads with transactions
- [ ] E2E: Tabs filter correctly
- [ ] E2E: Select/deselect works

**Complexity:** L
**Depends On:** 3.2

---

### Story 6.2: Select Screen - Inline Editing

**As a** iOS user
**I want** to edit transaction details inline
**So that** I can fix issues without leaving the list

**Acceptance Criteria:**
- [ ] Tapping row expands inline editor
- [ ] Editor shows: merchant (text), expense type (picker), split (picker), date (picker), amount (text)
- [ ] Save button updates transaction via API
- [ ] Cancel button reverts changes
- [ ] Visual feedback on save (checkmark animation)

**Technical Notes:**
- Use disclosure group or custom expansion
- Debounce API calls
- Optimistic UI update

**Test Requirements:**
- [ ] E2E: Expand row shows editor
- [ ] E2E: Edit and save persists
- [ ] E2E: Cancel reverts

**Complexity:** M
**Depends On:** 6.1, 3.3

---

### Story 6.3: Categorize Screen (Needs Attention)

**As a** iOS user
**I want** a focused view for flagged transactions
**So that** I can quickly fix issues

**Acceptance Criteria:**
- [ ] CategorizeView shows one transaction at a time (card format)
- [ ] Progress indicator: "2 of 5 items"
- [ ] Shows flag reason: "Low confidence" or "Possible duplicate"
- [ ] Previous/Next navigation
- [ ] Edit form pre-populated
- [ ] "Skip" button moves to next
- [ ] "All done" state when no more items

**Technical Notes:**
- Filter transactions where needs_review = true
- Page through with index
- Mark reviewed after save

**Test Requirements:**
- [ ] E2E: Navigate through flagged items
- [ ] E2E: Edit updates and advances
- [ ] E2E: All done state displays

**Complexity:** M
**Depends On:** 6.2

---

### Story 6.4: Import Confirmation

**As a** iOS user
**I want** to confirm my import
**So that** I can finalize the process

**Acceptance Criteria:**
- [ ] "Import X Transactions" button on Select screen
- [ ] Confirmation dialog: "Import 15 transactions?"
- [ ] Progress indicator during import
- [ ] Success screen with count: "15 transactions imported!"
- [ ] "View Transactions" button returns to main list
- [ ] Session cleaned up after import

**Technical Notes:**
- Call import API
- Navigate back to transactions list
- Clear import session from local state

**Test Requirements:**
- [ ] E2E: Confirmation dialog appears
- [ ] E2E: Import completes successfully
- [ ] E2E: Navigation to transactions

**Complexity:** S
**Depends On:** 6.3, 3.4

---

## Epic 7: Notifications

**Goal:** Notify user when background processing completes
**Dependencies:** E2 (Background Processing)

### Story 7.1: Send Push Notification

**As a** system
**I want** to send push notification when ready
**So that** user knows to return to app

**Acceptance Criteria:**
- [ ] After extraction completes, send APNs notification
- [ ] Notification title: "Import Ready"
- [ ] Notification body: "Your bank statement has been processed. X transactions found."
- [ ] Notification includes session_id in data payload
- [ ] Only sent if user has push enabled

**Technical Notes:**
- Use existing DeviceToken model
- Use PyAPNs2 library
- Handle token invalidation

**Test Requirements:**
- [ ] Unit: Notification payload format
- [ ] Integration: Notification sent on completion (mock APNs)

**Complexity:** M
**Depends On:** 2.3

---

### Story 7.2: Handle Push Deep Link

**As a** iOS user
**I want** tapping notification to open my import
**So that** I can review immediately

**Acceptance Criteria:**
- [ ] Tapping notification opens app to Select screen
- [ ] Session ID passed via deep link
- [ ] If session expired/invalid, show friendly error
- [ ] Works from terminated and background states

**Technical Notes:**
- Use UNUserNotificationCenter delegate
- Parse session_id from notification data
- Navigate to SelectView with session

**Test Requirements:**
- [ ] E2E: Deep link navigation (manual test)

**Complexity:** S
**Depends On:** 7.1, 6.1

---

## Epic 8: Polish

**Goal:** Handle edge cases, improve reliability, clean up
**Dependencies:** All other epics

### Story 8.1: Error Handling & Recovery

**As a** user
**I want** graceful error handling
**So that** I can recover from failures

**Acceptance Criteria:**
- [ ] Network errors show retry option
- [ ] API errors show user-friendly messages
- [ ] Timeout errors handled (30s for extraction)
- [ ] Partial extraction saves what succeeded
- [ ] Session can be resumed after app restart

**Technical Notes:**
- Map API error codes to user messages
- Store session state locally for resume
- Log errors for debugging

**Test Requirements:**
- [ ] Unit: Error message mapping
- [ ] Integration: Recovery from network failure
- [ ] Integration: Resume incomplete session

**Complexity:** M
**Depends On:** All

---

### Story 8.2: Cleanup & Expiration

**As a** system
**I want** to clean up old sessions
**So that** storage isn't wasted

**Acceptance Criteria:**
- [ ] Incomplete sessions expire after 7 days
- [ ] Expired sessions' files are deleted
- [ ] Cleanup job runs daily
- [ ] Completed sessions can be deleted immediately
- [ ] Audit log retained for 90 days

**Technical Notes:**
- Use APScheduler or cron for cleanup job
- Secure delete for all files
- Log cleanup actions

**Test Requirements:**
- [ ] Unit: Expiration logic
- [ ] Integration: Cleanup job runs

**Complexity:** S
**Depends On:** 3.4

---

### Story 8.3: Comprehensive Testing

**As a** developer
**I want** full test coverage
**So that** the feature is reliable

**Acceptance Criteria:**
- [ ] Unit tests for all services
- [ ] Integration tests for all APIs
- [ ] E2E Maestro tests for iOS flows
- [ ] Test coverage > 80% for new code
- [ ] CI pipeline includes all tests

**Technical Notes:**
- Add tests incrementally with each story
- Mock external services (OpenAI)
- Use fixtures for test data

**Test Requirements:**
- [ ] Meta: All tests passing
- [ ] Meta: Coverage report generated

**Complexity:** M
**Depends On:** All

---

## Dependency Graph

```
E1: Backend Foundation
├─ 1.1 ImportSession ──────────────────────────────┐
│   └─ 1.2 ExtractedTransaction                    │
├─ 1.3 ImportSettings                              │
├─ 1.4 File Storage ◄──────────────────────────────┤
│   └─ 1.5 Upload API ─────────────────────────────┤
│                                                  │
E2: AI Extraction                                  │
├─ 2.1 Service Interface                           │
│   └─ 2.2 GPT-4V Implementation                   │
│       └─ 2.3 Background Processing ◄─────────────┤
│           └─ 2.4 Rule Matching ──────────────────┤
│                                                  │
E3: Review & Import                                │
├─ 3.1 Session Status API ◄────────────────────────┤
│   └─ 3.2 List Transactions ◄─────────────────────┤
│       └─ 3.3 Update Transaction                  │
│           └─ 3.4 Import API ─────────────────────┤
│                                                  │
E4: Rules System (parallel)                        │
├─ 4.1 List Rules                                  │
│   └─ 4.2 Create/Update Rule                      │
│   └─ 4.3 Delete Rule                             │
│                                                  │
E5: iOS Capture                                    │
├─ 5.1 Capture UI ◄────────────────────────────────┤
│   └─ 5.2 File Upload ◄───────────────────────────┤
│       └─ 5.3 Processing Status ◄─────────────────┤
│                                                  │
E6: iOS Review                                     │
├─ 6.1 Select Screen ◄─────────────────────────────┤
│   └─ 6.2 Inline Editing                          │
│       └─ 6.3 Categorize Screen                   │
│           └─ 6.4 Import Confirmation ◄───────────┤
│                                                  │
E7: Notifications                                  │
├─ 7.1 Send Push ◄─────────────────────────────────┘
│   └─ 7.2 Deep Link
│
E8: Polish
├─ 8.1 Error Handling
├─ 8.2 Cleanup
└─ 8.3 Testing
```

---

## Implementation Order

Suggested sequence based on dependencies and enabling user testing:

### Phase 1: Backend MVP (Stories: 1.1-1.5, 2.1, 3.1)
Build foundation to enable file upload and basic status tracking.
- Database models created
- File upload working
- Mock extraction service
- Can poll session status

**Exit Criteria:** Can upload file via API and see session status

### Phase 2: AI Integration (Stories: 2.2-2.4)
Add real document processing.
- GPT-4V integration
- Background processing
- Rule matching and duplicate detection

**Exit Criteria:** Uploaded document produces extracted transactions

### Phase 3: Review APIs (Stories: 3.2-3.4, 4.1-4.3)
Complete backend for review workflow.
- Transaction list/edit APIs
- Import finalization
- Rules CRUD

**Exit Criteria:** Can complete full import via API

### Phase 4: iOS Capture (Stories: 5.1-5.3)
Build iOS upload interface.
- Capture screen UI
- File upload
- Processing status

**Exit Criteria:** Can upload from iOS and see processing

### Phase 5: iOS Review (Stories: 6.1-6.4)
Build iOS review interface.
- Select screen with tabs
- Inline editing
- Categorize flagged items
- Import confirmation

**Exit Criteria:** Full iOS flow working

### Phase 6: Notifications & Polish (Stories: 7.1-7.2, 8.1-8.3)
Final touches.
- Push notifications
- Error handling
- Cleanup jobs
- Testing

**Exit Criteria:** Feature complete, tested, ready for release

---

## Definition of Done

A story is complete when:
- [ ] All acceptance criteria pass
- [ ] Unit tests written and passing
- [ ] Integration tests (if applicable) passing
- [ ] Code reviewed (self-review for solo dev)
- [ ] No new linter warnings
- [ ] Documentation updated (API docs for endpoints)
- [ ] Tested manually in development environment
