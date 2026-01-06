# Zhang Estate Expense Tracker - Technical Specification

**Version**: 1.0 MVP (Implemented)
**Date**: January 2026
**Status**: ✅ Implemented and Deployed to Production

## 1. Overview

### 1.1 Problem Statement
Manual expense reconciliation between two people sharing household expenses is time-consuming and error-prone:
- Manual transaction entry from bank statements
- Multi-currency handling (USD/CAD)
- Mixed expense types: shared vs reimbursements
- Complex calculation of who owes whom

### 1.2 Solution
Web-based expense tracking tool with automatic reconciliation calculations, focusing on ease and speed of transaction entry.

### 1.3 Scope - MVP Features
**In Scope:**
- Quick transaction entry form
- Transaction list view with modal-based editing
- Automatic currency conversion (CAD → USD, USD is primary currency)
- Monthly reconciliation calculations
- CSV export for backup
- Personalized display names (Bibi and Pi instead of ME/WIFE in UI)
- Production deployment on Render.com with persistent database storage

**Out of Scope (Future):**
- PDF parsing of bank statements
- Banking API integration
- User authentication
- Mobile app
- Advanced charts/analytics
- Smart categorization rules

---

## 2. Technical Architecture

### 2.1 Tech Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Backend | Python 3.9+ + Flask | Beginner-friendly, minimal setup |
| Database | SQLite | No installation, file-based, easy backup |
| Frontend | HTML + Tailwind CSS + Vanilla JS | Simple, no build tools needed |
| Currency API | frankfurter.app | Free, no signup required |
| Production Server | Gunicorn | WSGI server for production deployment |
| Hosting | Render.com | $7/month with persistent disk, auto-deploy from GitHub |

### 2.2 System Architecture

```
┌─────────────────┐
│   Web Browser   │
│  (User Access)  │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Flask Web App  │
│   (app.py)      │
├─────────────────┤
│  - Routes       │
│  - Templates    │
│  - Static Files │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│ SQLite │ │ External APIs│
│   DB   │ │ (Currency)   │
└────────┘ └──────────────┘
```

---

## 3. Data Model

### 3.1 Database Schema

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    merchant TEXT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency TEXT NOT NULL CHECK(currency IN ('USD', 'CAD')),
    amount_in_usd DECIMAL(10, 2) NOT NULL,  -- Primary currency is USD
    paid_by TEXT NOT NULL CHECK(paid_by IN ('ME', 'WIFE')),  -- Stored as ME/WIFE, displayed as Bibi/Pi
    category TEXT NOT NULL CHECK(category IN (
        'SHARED',
        'I_PAY_FOR_WIFE',
        'WIFE_PAYS_FOR_ME',
        'PERSONAL_ME',
        'PERSONAL_WIFE'
    )),
    notes TEXT,
    month_year TEXT NOT NULL,  -- Format: "2025-01"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_month_year ON transactions(month_year);
CREATE INDEX idx_date ON transactions(date);

CREATE TABLE settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_year TEXT NOT NULL UNIQUE,  -- Format: "2026-01", UNIQUE to prevent duplicates
    settled_date DATE NOT NULL,  -- When the month was marked as settled
    settlement_amount DECIMAL(10, 2) NOT NULL,  -- Absolute amount owed (always positive)
    from_person TEXT NOT NULL CHECK(from_person IN ('ME', 'WIFE', 'NONE')),  -- Who owes
    to_person TEXT NOT NULL CHECK(to_person IN ('ME', 'WIFE', 'NONE')),  -- Who is owed
    settlement_message TEXT NOT NULL,  -- "Pi owes Bibi $75.25" or "All settled up!"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_settlement_month ON settlements(month_year);
```

**Settlement Table Purpose:**
- Records permanent snapshot when a month is marked as "settled"
- Locks the month to prevent further transaction modifications
- Preserves historical settlement records even if transactions change
- UNIQUE constraint on month_year ensures only one settlement per month

### 3.2 Transaction Categories

| Category | Display Name | Who Paid | Who Benefits | Split Logic |
|----------|--------------|----------|--------------|-------------|
| SHARED | Shared Expense | Either | Both 50/50 | Each person pays 50% |
| I_PAY_FOR_WIFE | Bibi pays for Pi | Bibi | Pi 100% | Pi pays 100%, Bibi pays 0% |
| WIFE_PAYS_FOR_ME | Pi pays for Bibi | Pi | Bibi 100% | Bibi pays 100%, Pi pays 0% |
| PERSONAL_ME | Bibi's Personal | Bibi | Bibi 100% | No split (neutral) |
| PERSONAL_WIFE | Pi's Personal | Pi | Pi 100% | No split (neutral) |

**Note**: Database stores generic values (ME/WIFE) but UI displays personalized nicknames (Bibi/Pi).

---

## 4. API Design

### 4.1 REST Endpoints

| Method | Endpoint | Description | Request Body | Response | Status |
|--------|----------|-------------|--------------|----------|--------|
| GET | `/` | Main page with transaction list | - | HTML page | ✅ Implemented |
| POST | `/transaction` | Create transaction | Transaction JSON | `{success: bool, transaction: {...}}` | ✅ Implemented |
| PUT | `/transaction/<id>` | Update transaction | Transaction JSON | `{success: bool, transaction: {...}}` | ✅ Implemented & Connected to UI |
| DELETE | `/transaction/<id>` | Delete transaction | - | `{success: bool}` | ✅ Implemented |
| GET | `/reconciliation` | Monthly summary (default: current month) | - | HTML page | ✅ Implemented |
| GET | `/reconciliation/<month>` | Monthly summary for specific month | - | HTML page | ✅ Implemented |
| GET | `/export/<month>` | Export CSV | - | CSV file | ✅ Implemented |
| POST | `/settlement` | Mark month as settled and lock it | `{month_year: "YYYY-MM"}` | `{success: bool, settlement: {...}}` | ✅ Implemented |
| DELETE | `/settlement/<month>` | Unsettle month and unlock it | - | `{success: bool, message: string}` | ✅ Implemented |

### 4.2 Transaction JSON Schema

```json
{
  "date": "2025-01-15",
  "merchant": "Whole Foods",
  "amount": 125.50,
  "currency": "CAD",
  "paid_by": "ME",
  "category": "SHARED",
  "notes": "Weekly groceries"
}
```

---

## 5. Core Business Logic

### 5.1 Reconciliation Algorithm

**Step 1: Calculate Total Paid**
```
person_a_paid = SUM(transactions WHERE paid_by = 'ME')
person_b_paid = SUM(transactions WHERE paid_by = 'WIFE')
```

**Step 2: Calculate Each Person's Share**
```
person_a_share =
  + 50% of SHARED transactions
  + 100% of WIFE_PAYS_FOR_ME transactions
  + 100% of PERSONAL_ME transactions
  + 0% of I_PAY_FOR_WIFE transactions
  + 0% of PERSONAL_WIFE transactions

person_b_share =
  + 50% of SHARED transactions
  + 100% of I_PAY_FOR_WIFE transactions
  + 100% of PERSONAL_WIFE transactions
  + 0% of WIFE_PAYS_FOR_ME transactions
  + 0% of PERSONAL_ME transactions
```

**Step 3: Calculate Net Settlement**
```
person_a_balance = person_a_paid - person_a_share
person_b_balance = person_b_paid - person_b_share

if person_a_balance > 0:
    result = "WIFE owes ME ${person_a_balance}"
else:
    result = "ME owes WIFE ${abs(person_a_balance)}"
```

### 5.2 Worked Example

**Transactions:**
1. Groceries, $100 CAD, Paid by ME, SHARED
2. My coffee, $5 CAD, Paid by ME, PERSONAL_ME
3. Wife's book, $20 CAD, Paid by ME, I_PAY_FOR_WIFE
4. Dinner, $80 CAD, Paid by WIFE, SHARED
5. Gas, $50 CAD, Paid by WIFE, SHARED

**Calculations:**
```
ME paid: $100 + $5 + $20 = $125
WIFE paid: $80 + $50 = $130

MY share:
  Groceries (SHARED): $100 × 50% = $50
  My coffee (PERSONAL_ME): $5 × 100% = $5
  Wife's book (I_PAY_FOR_WIFE): $20 × 0% = $0
  Dinner (SHARED): $80 × 50% = $40
  Gas (SHARED): $50 × 50% = $25
  Total: $120

WIFE's share:
  Groceries (SHARED): $100 × 50% = $50
  My coffee (PERSONAL_ME): $5 × 0% = $0
  Wife's book (I_PAY_FOR_WIFE): $20 × 100% = $20
  Dinner (SHARED): $80 × 50% = $40
  Gas (SHARED): $50 × 50% = $25
  Total: $135

Settlement:
  ME: paid $125, should pay $120 → owed $5
  WIFE: paid $130, should pay $135 → short $5
  Result: WIFE owes ME $5
```

### 5.3 Currency Conversion

**Primary Currency**: USD (all reconciliations calculated in USD)

**Conversion Direction**: CAD → USD (not USD → CAD)

**API**: frankfurter.app (free, no auth)

**Endpoint**: `https://api.frankfurter.app/{date}`

**Implementation:**
```python
def get_exchange_rate(from_curr, to_curr, date):
    """
    Fetch historical exchange rate for given date.
    Cache results to minimize API calls.
    Converts CAD to USD for storage in amount_in_usd field.
    """
    # Check cache first
    # If not cached, call API
    # Return rate
```

**Caching Strategy:**
- Cache exchange rates by date (format: `CAD_USD_YYYY-MM-DD`)
- Rates don't change retroactively
- Store in memory (dict) for session-based caching

---

## 6. User Interface Design

### 6.1 Main Page (`/`)

**Layout:**
```
┌─────────────────────────────────────┐
│  Zhang Estate Expense Tracker       │
│  January 2026                    ▼  │ ← Month selector
├─────────────────────────────────────┤
│  Quick Add Transaction              │
│  ┌────┬─────────┬──────┬─────┐     │
│  │Date│Merchant │Amount│ ... │ [+] │ ← Form (sticky top)
│  └────┴─────────┴──────┴─────┘     │
├─────────────────────────────────────┤
│  Current Month Summary              │
│  Bibi paid: $X  │  Pi paid: $Y      │
│  Result: [WHO] owes [WHO] $Z        │
│  [View Full Reconciliation]         │
├─────────────────────────────────────┤
│  Transaction List                   │
│  ┌───────────────────────────────┐  │
│  │ 01/15  Groceries  $100  [Edit][×]│ ← Edit button opens modal
│  │ 01/14  Coffee     $5    [Edit][×]│
│  │ ...                            │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Edit Transaction            [×]    │ ← Modal overlay
├─────────────────────────────────────┤
│  Date:     [2026-01-15      ]       │
│  Merchant: [Groceries       ]       │
│  Amount:   [100.00          ]       │
│  Currency: [USD ▼           ]       │
│  Paid By:  [Bibi ▼          ]       │
│  Category: [Shared Expense ▼]       │
│  Notes:    [Weekly groceries]       │
│                                     │
│       [Cancel] [Save Changes]       │
└─────────────────────────────────────┘
```

**Form Fields:**
- Date (default: today)
- Merchant (text input)
- Amount (number)
- Currency (USD/CAD dropdown, USD default)
- Paid By (Bibi/Pi dropdown, displayed as nicknames but stored as ME/WIFE)
- Category (dropdown with friendly labels: "Shared Expense", "Bibi pays for Pi", etc.)
- Notes (optional textarea)

**Interactions:**
- Form submit → AJAX POST → Add to list without page reload
- Click Edit button → Opens modal dialog with pre-filled form
- Edit modal → Populate from data attributes → PUT request → Close modal and reload
- Click Delete (×) → Confirm and DELETE request
- Month selector → Load different month (query param: `?month=YYYY-MM`)
- Escape key or backdrop click → Close edit modal

**Edit Modal Implementation:**
- Transaction data stored in HTML `data-*` attributes on table rows
- JavaScript `openEditModal(id)` reads attributes and populates form
- Form submit sends PUT request to `/transaction/<id>`
- Success → Shows message → Reloads page after 500ms

### 6.2 Reconciliation Page (`/reconciliation/<month>`)

```
┌─────────────────────────────────────┐
│  Reconciliation - January 2026      │
│  [← Back] [Export CSV]              │
├─────────────────────────────────────┤
│  💰 Settlement                      │
│  ┌─────────────────────────────┐   │
│  │  Pi owes Bibi $247.50       │   │ ← Big, clear (uses nicknames)
│  │  [Mark as Settled]          │   │ ← Button (if not settled)
│  └─────────────────────────────┘   │
├─────────────────────────────────────┤
│  Summary                            │
│  Bibi paid:      $1,234.56          │
│  Pi paid:        $987.06            │
│                                     │
│  Bibi's share:   $987.06            │
│  Pi's share:     $1,234.56          │
├─────────────────────────────────────┤
│  Breakdown by Category              │
│  ┌──────────────────┬────┬──────┐  │
│  │ Category         │ #  │ Total│  │
│  ├──────────────────┼────┼──────┤  │
│  │ Shared Expense   │ 15 │ $800 │  │
│  │ Bibi pays for Pi │ 3  │ $120 │  │
│  │ ...              │    │      │  │
│  └──────────────────┴────┴──────┘  │
└─────────────────────────────────────┘
```

**When Month is Settled:**
```
┌─────────────────────────────────────┐
│  🔒 This month is locked            │
│  Settled on 2026-01-15              │ ← Yellow banner
├─────────────────────────────────────┤
│  💰 Settlement                      │
│  ┌─────────────────────────────┐   │
│  │  Pi owes Bibi $247.50       │   │ ← Historical record
│  │  Settled: January 15, 2026  │   │
│  │  🔓 Locked                  │   │
│  │  [Unsettle Month]           │   │ ← Button to unlock
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### 6.3 Monthly Settlement Feature

**Purpose**: Track when monthly reconciliations are settled and lock months to prevent accidental changes.

**User Flow:**

1. **Viewing Unsettled Month**:
   - Reconciliation page shows calculated settlement
   - "Mark as Settled" button is visible
   - Transactions can be added/edited/deleted

2. **Marking Month as Settled**:
   - User clicks "Mark as Settled" button
   - Confirmation dialog warns about locking
   - POST `/settlement` creates permanent record
   - Settlement record stores: date, amount, who owes whom, settlement message
   - Month becomes locked

3. **Locked Month Behavior**:
   - Yellow "This month is locked" banner appears on both pages
   - Add Transaction form is disabled (grayed out)
   - Edit/Delete buttons show "Locked" instead
   - API returns 403 Forbidden for add/edit/delete attempts
   - Reconciliation page shows historical settlement record

4. **Unsettling a Month**:
   - User clicks "Unsettle Month" button on reconciliation page
   - Confirmation dialog warns about unlocking
   - DELETE `/settlement/<month>` removes settlement record
   - Month becomes unlocked
   - Transactions can be added/edited/deleted again
   - Can re-settle later if needed

**Validation Rules:**
- Cannot settle a month with no transactions
- Cannot settle the same month twice (UNIQUE constraint)
- Cannot add/edit/delete transactions in settled months
- Unsettling removes the settlement record completely

---

## 7. Project Structure

```
household_tracker/
├── app.py                    # Main Flask application (~410 lines, includes settlement endpoints)
├── models.py                 # Database models (~110 lines, includes Settlement model)
├── utils.py                  # Helper functions (~120 lines)
├── requirements.txt          # Python dependencies (includes gunicorn)
├── Procfile                  # Production server config for Render
├── SPEC.md                   # This file (technical specification)
├── DEPLOYMENT.md             # Step-by-step production deployment guide
├── README.md                 # Setup & usage instructions
├── CLAUDE.md                 # Claude Code guidance for this project
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
│
├── static/
│   └── app.js               # Frontend JavaScript (~250 lines with edit modal)
│
├── templates/
│   ├── base.html            # Base template (~60 lines)
│   ├── index.html           # Main transaction page (~410 lines, includes locked month UI)
│   └── reconciliation.html  # Monthly summary (~345 lines, includes settlement tracking)
│
├── instance/
│   └── database.db          # SQLite database (development, created at runtime)
│
└── data/                    # Production database directory (Render persistent disk)
    └── database.db          # SQLite database (production)
```

---

## 8. Dependencies

### 8.1 requirements.txt

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.2.0
```

### 8.2 External Services

| Service | Purpose | Cost | URL |
|---------|---------|------|-----|
| frankfurter.app | Currency exchange rates | Free | https://www.frankfurter.app |
| Tailwind CSS CDN | UI styling | Free | https://cdn.tailwindcss.com |

---

## 9. Development Workflow

### 9.1 Setup Steps

```bash
# 1. Navigate to project
cd household_tracker

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python app.py

# 5. Open browser
open http://localhost:5000
```

### 9.2 Implementation Status

**✅ Backend Foundation (Completed)**
- ✅ Project structure set up
- ✅ Database models created (models.py with Transaction and Settlement models)
- ✅ Flask routes implemented (app.py with CRUD operations and settlement endpoints)
- ✅ Utility functions built (utils.py with reconciliation and currency conversion)

**✅ Frontend UI (Completed)**
- ✅ Base template with Tailwind CSS
- ✅ Transaction entry form on main page
- ✅ Transaction list view with data attributes
- ✅ Reconciliation page with category breakdown
- ✅ Edit modal dialog component

**✅ Interactivity (Completed)**
- ✅ JavaScript for AJAX form submission (no page reload)
- ✅ Modal-based editing implementation
- ✅ Delete confirmation and functionality
- ✅ Month selector for viewing different periods
- ✅ Currency conversion with CAD → USD

**✅ Testing & Production (Completed)**
- ✅ Application renamed to "Zhang Estate Expense Tracker"
- ✅ Personalized display names (Bibi/Pi)
- ✅ CSV export functionality
- ✅ Production configuration for Render.com
- ✅ Git repository initialized and pushed to GitHub
- ✅ Deployment guide created (DEPLOYMENT.md)

**✅ Settlement Tracking (Completed - January 2026)**
- ✅ Settlement table added to database schema
- ✅ POST /settlement endpoint to mark month as settled
- ✅ DELETE /settlement/<month> endpoint to unsettle month
- ✅ Settlement validation on all transaction endpoints (add/edit/delete)
- ✅ Locked month UI on index page (disabled form, locked buttons)
- ✅ Settlement tracking UI on reconciliation page
- ✅ JavaScript functions for marking settled and unsettling
- ✅ Database migration tested (Settlement table created successfully)

### 9.3 Testing Checklist

**Core Functionality:**
- ✅ Can add transaction manually
- ✅ CAD transactions convert to USD correctly (USD is primary currency)
- ✅ Can edit existing transaction via modal
- ✅ Can delete transaction with confirmation
- ✅ Reconciliation calculates correctly
- ✅ Can switch between months via dropdown
- ✅ CSV export works
- ⏳ Works on mobile browser (not yet tested)
- ✅ Exchange rate caching works (in-memory cache)
- ✅ All 5 category types work correctly

**Settlement Tracking:**
- ✅ Can mark month as settled via reconciliation page
- ✅ Settled month shows locked banner on both pages
- ✅ Add Transaction form disabled in settled months
- ✅ Edit/Delete buttons show "Locked" in settled months
- ✅ API returns 403 Forbidden for add/edit/delete in settled months
- ✅ Settlement record displays with date and amount
- ✅ Can unsettle a month to unlock it
- ✅ Cannot settle the same month twice (UNIQUE constraint)
- ✅ Cannot settle month with no transactions
- ✅ After unsettling, can add/edit/delete transactions again

---

## 10. Deployment

### 10.1 Production Platform: Render.com ✅

**Current Status**: Code is production-ready and pushed to GitHub at https://github.com/yilunzh/household_finance

**Why Render:**
- ✅ Persistent disk storage ($7/month) - database survives deployments
- ✅ Extremely beginner-friendly UI
- ✅ Auto-deploy from GitHub on push
- ✅ Free SSL/HTTPS certificate
- ✅ Free subdomain: `yourapp.onrender.com`
- ✅ Built-in health checks and auto-restart

**Deployment Files Created:**
- `Procfile`: Tells Render to use Gunicorn (`web: gunicorn app:app`)
- `DEPLOYMENT.md`: Complete step-by-step guide with screenshots and troubleshooting
- Updated `app.py`: Environment-based configuration for production vs development

**Production Configuration in app.py:**

```python
# Database path switches based on environment
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/database.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# Database initialization (runs when module is loaded by Gunicorn)
def init_db():
    """Create database tables if they don't exist."""
    with app.app_context():
        db.create_all()
        print('Database tables created (if not already existing)')

init_db()  # Called when app starts

# Port configuration
port = int(os.environ.get('PORT', 5001))
debug_mode = os.environ.get('FLASK_ENV') != 'production'
app.run(debug=debug_mode, host='0.0.0.0', port=port)
```

**Database Initialization:**
- The `init_db()` function is called at module level when the app starts
- Works with both development (`python app.py`) and production (Gunicorn)
- `db.create_all()` is idempotent - safe to call multiple times, only creates missing tables
- Ensures database tables exist before any requests are processed

**Persistent Disk Configuration (Render):**
- Disk name: `database-storage`
- Mount path: `/opt/render/project/src/data`
- Size: 1GB (enough for thousands of transactions)
- Database file: `/opt/render/project/src/data/database.db`

### 10.2 Environment Variables

**Required for Production:**

| Variable | Value | Notes |
|----------|-------|-------|
| `FLASK_ENV` | `production` | Disables debug mode, uses production database path |
| `SECRET_KEY` | Auto-generated by Render | Flask session encryption key |
| `PORT` | Set by Render automatically | Web server port (do not manually set) |

**Optional:**

| Variable | Value | Notes |
|----------|-------|-------|
| `PYTHON_VERSION` | `3.9.18` | Specify Python version for Render |

### 10.3 Deployment Steps

See `DEPLOYMENT.md` for complete step-by-step instructions including:
1. Render account creation
2. GitHub repository connection
3. Service configuration (persistent disk, environment variables)
4. Deployment verification
5. Testing procedures
6. Ongoing maintenance

**Cost**: $7/month for Starter tier with persistent disk storage

---

## 11. Success Criteria

The MVP is considered successful when:

1. ✅ **Speed**: Can add a transaction in under 10 seconds
2. ✅ **Automation**: Currency conversion happens automatically
3. ✅ **Clarity**: Who owes what is immediately visible
4. ✅ **Efficiency**: Faster than current Excel workflow
5. ✅ **Accessibility**: Both users can access it from any device

---

## 12. Future Enhancements

### Phase 2 (After 1-2 months of use)
- Smart categorization rules
- Bulk CSV import
- Historical reconciliation view
- Transaction search/filter

### Phase 3 (Advanced)
- PDF bank statement parsing
- Receipt photo upload
- Spending trends charts
- Custom split percentages

### Phase 4 (Enterprise)
- Banking API integration (Plaid)
- Multi-user support
- Mobile app
- Automated monthly settlements

---

## 13. Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Development | ✅ Completed | Implemented in January 2026 |
| Hosting | $7/month | Render.com Starter tier with persistent disk |
| Domain (optional) | $0 currently | Using free subdomain (yourapp.onrender.com) |
| Currency API | $0 | frankfurter.app free tier (sufficient for personal use) |
| **Total Monthly** | **$7** | **Ongoing** |
| **Annual** | **$84** | **No upfront costs** |

---

## 14. Key Code Snippets

### 14.1 Exchange Rate Function

```python
# utils.py
import requests
from datetime import datetime

_rate_cache = {}

def get_exchange_rate(from_curr, to_curr, date):
    """Get exchange rate for a specific date, with caching."""
    cache_key = f"{from_curr}_{to_curr}_{date}"

    if cache_key in _rate_cache:
        return _rate_cache[cache_key]

    # Call frankfurter.app API
    url = f"https://api.frankfurter.app/{date}"
    params = {'from': from_curr, 'to': to_curr}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        rate = response.json()['rates'][to_curr]
        _rate_cache[cache_key] = rate
        return rate

    # Fallback to current rate if historical not available
    return get_current_exchange_rate(from_curr, to_curr)
```

### 14.2 Reconciliation Calculation

```python
# utils.py
def calculate_reconciliation(transactions):
    """Calculate who owes what for a list of transactions."""
    me_paid = 0
    wife_paid = 0
    me_share = 0
    wife_share = 0

    for txn in transactions:
        amount_usd = txn.amount_in_usd  # Primary currency is USD

        # Track who paid
        if txn.paid_by == 'ME':
            me_paid += amount_usd
        else:
            wife_paid += amount_usd

        # Calculate each person's share
        if txn.category == 'SHARED':
            me_share += amount_usd * 0.5
            wife_share += amount_usd * 0.5
        elif txn.category == 'I_PAY_FOR_WIFE':
            wife_share += amount_usd
        elif txn.category == 'WIFE_PAYS_FOR_ME':
            me_share += amount_usd
        elif txn.category == 'PERSONAL_ME':
            me_share += amount_usd
        elif txn.category == 'PERSONAL_WIFE':
            wife_share += amount_usd

    # Calculate net balance
    me_balance = me_paid - me_share
    wife_balance = wife_paid - wife_share

    return {
        'me_paid': me_paid,
        'wife_paid': wife_paid,
        'me_share': me_share,
        'wife_share': wife_share,
        'me_balance': me_balance,
        'wife_balance': wife_balance,
        'settlement': format_settlement(me_balance, wife_balance)
    }

def format_settlement(me_balance, wife_balance):
    """Format the settlement message with personalized nicknames."""
    if me_balance > 0.01:  # Account for floating point
        return f"Pi owes Bibi ${me_balance:.2f}"
    elif wife_balance > 0.01:
        return f"Bibi owes Pi ${wife_balance:.2f}"
    else:
        return "All settled up!"
```

---

## Appendix: Sample Data

### Sample Transactions (for testing)

```json
[
  {
    "date": "2026-01-05",
    "merchant": "Whole Foods",
    "amount": 125.50,
    "currency": "CAD",
    "paid_by": "ME",
    "category": "SHARED"
  },
  {
    "date": "2026-01-07",
    "merchant": "Starbucks",
    "amount": 6.50,
    "currency": "CAD",
    "paid_by": "ME",
    "category": "PERSONAL_ME"
  },
  {
    "date": "2026-01-10",
    "merchant": "Amazon",
    "amount": 45.00,
    "currency": "USD",
    "paid_by": "WIFE",
    "category": "I_PAY_FOR_WIFE"
  },
  {
    "date": "2026-01-12",
    "merchant": "Gas Station",
    "amount": 60.00,
    "currency": "CAD",
    "paid_by": "WIFE",
    "category": "SHARED"
  }
]
```

---

**Document Version**: 1.2 (Updated to include Settlement Tracking feature)
**Last Updated**: January 6, 2026
**Author**: Claude (Sonnet 4.5)
**GitHub Repository**: https://github.com/yilunzh/household_finance
**Deployment Guide**: See DEPLOYMENT.md for production deployment instructions

**Recent Updates (v1.2):**
- Added Settlement table to database schema
- Added POST /settlement and DELETE /settlement/<month> endpoints
- Implemented month locking feature to prevent modifications to settled months
- Added settlement tracking UI to reconciliation page
- Added locked month UI to main transaction page
- All settlement features tested and verified
