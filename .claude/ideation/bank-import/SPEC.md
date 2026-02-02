# Bank Import Feature Specification

## Overview

Smart bank import: Screenshot/PDF → AI extracts → Review & select → Import

**Problem:** Monthly batch entry of 20+ transactions from bank statements is tedious and error-prone.

**Solution:** Allow users to capture bank statements (camera/screenshot/PDF), have AI extract transactions, then review and selectively import them with intelligent categorization.

---

## User Flow

```
1. CAPTURE      - Add bank statement (camera/library/PDF), multiple files
       ↓
2. PROCESSING   - Async extraction (continue using app)
       ↓
3. SELECT       - See all transactions, check which to import (categories read-only)
       ↓
4. CATEGORIZE   - Review only flagged items (uncertain, OCR failures)
       ↓
5. IMPORT       - Confirmation → Success
```

---

## Screen Specifications

### 1. Capture Screen

**Purpose:** Allow users to upload bank statements for processing

**Entry Points:**
- "Import from Bank" button on main transactions screen
- Quick action from empty state

**Components:**
| Component | Behavior |
|-----------|----------|
| Camera button | Opens camera for screenshot capture |
| Photo Library | Opens photo picker for existing screenshots |
| PDF Upload | Opens document picker for PDF files |
| File list | Shows queued files with remove option |
| Process button | Submits files for extraction |

**States:**
- Empty: No files selected
- Files queued: List of files ready to process
- Processing: Progress indicator, can navigate away

---

### 2. Select Screen

**Purpose:** Review extracted transactions and select which to import

**Entry Points:**
- Push notification when processing complete
- Badge on Import tab
- Direct navigation from capture flow

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  Import Transactions                              Done  │
├─────────────────────────────────────────────────────────┤
│  [Ready (12)] [Needs Attention (3)] [Skipped] [Imported]│
├─────────────────────────────────────────────────────────┤
│  Filters: [Expense Type ▼] [Split Category ▼]          │
├─────────────────────────────────────────────────────────┤
│  ☑ All                                                  │
├─────────────────────────────────────────────────────────┤
│  ☑  Whole Foods        Groceries   Shared   1/15  $87  │
│  ☑  Shell Gas          Gas         Mine     1/14  $45  │
│  ☑  Amazon             Shopping    Shared   1/14  $32  │
│  ☐  Venmo Payment      ?           ?        1/13  $50  │
│  ☑  Netflix            Subscript.  Shared   1/12  $15  │
│  ...                                                    │
├─────────────────────────────────────────────────────────┤
│  [Next: Review 3 Flagged Items]                        │
└─────────────────────────────────────────────────────────┘
```

**Components:**
| Component | Behavior | States |
|-----------|----------|--------|
| Category tabs | Filter by status | Ready, Needs Attention, Skipped, Already Imported |
| Filter dropdowns | Filter by expense type or split | All types listed |
| Select all checkbox | Toggle all visible items | Checked, unchecked, indeterminate |
| Transaction row | Dense display with checkbox | Selected, unselected, flagged |
| Primary action button | Proceed to next step | "Review X Flagged" or "Import X Items" |

**Transaction Row Columns:**
- Checkbox (selection)
- Merchant name
- Expense Type (read-only, shows "?" if uncertain)
- Split Category (read-only, shows "?" if uncertain)
- Date
- Amount

**Tab Definitions:**
| Tab | Contents |
|-----|----------|
| Ready | Transactions with confident categorization |
| Needs Attention | Uncertain categories, OCR failures, or manual review needed |
| Skipped | User deselected these |
| Already Imported | Detected duplicates (same merchant + amount + date) |

---

### 3. Categorize Screen

**Purpose:** Review and fix items that need attention

**Entry Points:**
- "Review X Flagged Items" from Select screen

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  ← Review Items                              3 of 3    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Venmo Payment                                   │   │
│  │  January 13, 2025                    $50.00     │   │
│  │                                                  │   │
│  │  Original text: "VENMO PAYMENT 1234567"         │   │
│  │                                                  │   │
│  │  Expense Type                                    │   │
│  │  [Select type...               ▼]               │   │
│  │                                                  │   │
│  │  Split Category                                  │   │
│  │  [Shared                       ▼]               │   │
│  │                                                  │   │
│  │  ☐ Remember this for "Venmo"                    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Skip]                              [Save & Next]     │
└─────────────────────────────────────────────────────────┘
```

**Components:**
| Component | Behavior |
|-----------|----------|
| Progress indicator | Shows X of Y items |
| Transaction card | Displays extracted data |
| Original text | Shows raw OCR for context |
| Expense Type picker | Dropdown with all types |
| Split Category picker | Dropdown with split options |
| Remember checkbox | Creates rule for future imports |
| Skip button | Moves to Skipped tab |
| Save & Next | Saves and advances |

**Edge Cases:**
| Case | Handling |
|------|----------|
| OCR failure | Show "Could not read" + manual entry fields |
| All items reviewed | "All done! Import X transactions" |
| No items need review | Skip directly to import confirmation |

---

### 4. Rules Management Screen (Settings)

**Purpose:** View and manage auto-categorization rules

**Entry Points:**
- Settings → Import Rules

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  ← Import Rules                                         │
├─────────────────────────────────────────────────────────┤
│  [Expense Type Rules] [Split Rules]                     │
├─────────────────────────────────────────────────────────┤
│  Default Split: [Shared ▼]                              │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │  "Whole Foods" → Groceries              [Edit]  │   │
│  │  "Amazon" → Shopping                    [Edit]  │   │
│  │  "Netflix" → Subscriptions              [Edit]  │   │
│  │  "Shell" → Gas                          [Edit]  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [+ Add Rule]                                           │
└─────────────────────────────────────────────────────────┘
```

**Components:**
| Component | Behavior |
|-----------|----------|
| Tab selector | Switch between Expense Type and Split rules |
| Default split picker | Sets default for unmatched transactions |
| Rule list | Shows all rules with edit button |
| Add rule button | Opens rule creation form |

**Rule Edit Form:**
| Field | Description |
|-------|-------------|
| Keyword | Merchant name to match (partial match) |
| Maps to | Expense type or split category |
| Delete button | Removes rule |

---

## Technical Considerations

### Data Models

**ImportSession**
- id, user_id, household_id
- status (processing, ready, completed, failed)
- created_at, completed_at
- source_files (JSON array of file references)

**ImportedTransaction**
- id, import_session_id
- raw_text (original OCR)
- merchant, amount, date
- suggested_expense_type_id, suggested_split
- confidence_score
- status (ready, needs_attention, skipped, imported)
- final_expense_type_id, final_split
- transaction_id (after import)

**AutoCategoryRule** (already exists, extend if needed)
- keyword
- expense_type_id
- split_category

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/import/sessions` | POST | Create import session, upload files |
| `/api/v1/import/sessions/{id}` | GET | Get session status and transactions |
| `/api/v1/import/sessions/{id}/transactions` | GET | List extracted transactions |
| `/api/v1/import/sessions/{id}/transactions/{tid}` | PUT | Update transaction categorization |
| `/api/v1/import/sessions/{id}/import` | POST | Import selected transactions |
| `/api/v1/import/rules` | GET/POST | List/create rules |
| `/api/v1/import/rules/{id}` | PUT/DELETE | Update/delete rule |

### Processing Pipeline

1. **File Upload** → Store in S3/local storage
2. **Queue Job** → Background processing
3. **OCR/AI Extraction** → Parse transactions from image/PDF
4. **Rule Matching** → Apply existing rules
5. **Confidence Scoring** → Flag uncertain items
6. **Duplicate Detection** → Check merchant + amount + date
7. **Ready for Review** → Push notification

### Duplicate Detection

Match on:
- Same merchant name (fuzzy match)
- Same amount (exact)
- Same date (exact)

If all three match existing transaction, mark as "Already Imported"

---

## Success Criteria

1. User can import 20+ transactions in under 2 minutes
2. 80%+ transactions auto-categorized correctly
3. Duplicate detection prevents re-imports
4. Rules reduce manual categorization over time
5. Async processing doesn't block app usage

---

## Out of Scope (v1)

- Direct bank API integration (Plaid, etc.)
- Automatic recurring import scheduling
- Multi-currency statement support
- Statement period auto-detection
- Export rules between households
