# Zhang Estate Expense Tracker - Technical Specification

**Version**: 2.0 (Multi-User, Multi-Household)
**Date**: January 2026
**Status**: Implemented and Deployed to Production

## 1. Overview

### 1.1 Problem Statement
Manual expense reconciliation between two people sharing household expenses is time-consuming and error-prone:
- Manual transaction entry from bank statements
- Multi-currency handling (USD/CAD)
- Mixed expense types: shared vs reimbursements
- Complex calculation of who owes whom

### 1.2 Solution
Web-based expense tracking tool with automatic reconciliation calculations, focusing on ease and speed of transaction entry.

### 1.3 Scope
**In Scope (v2.0):**
- Multi-user authentication (registration, login, logout)
- Multi-household support - users can belong to multiple households
- Email-based invitations for partner onboarding
- Quick transaction entry form
- Transaction list view with modal-based editing
- Automatic currency conversion (CAD → USD, USD is primary currency)
- Monthly reconciliation calculations
- Settlement locking (mark months as settled)
- CSV export for backup
- Dynamic member display names per household
- Production security (HTTPS enforcement, rate limiting, security headers)
- Production deployment on Render.com with persistent database storage

**Out of Scope (Future):**
- PDF parsing of bank statements
- Banking API integration
- Password reset flow
- Two-factor authentication
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
| ORM | Flask-SQLAlchemy | Database abstraction layer |
| Authentication | Flask-Login | Session management, user authentication |
| CSRF Protection | Flask-WTF | Form protection, CSRF tokens |
| Email | Flask-Mail | Sending invitation emails |
| Rate Limiting | Flask-Limiter | Protecting authentication routes |
| Frontend | HTML + Tailwind CSS + Alpine.js | Simple, no build tools needed |
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
-- Users table (authentication)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);

-- Households table (multi-tenancy)
CREATE TABLE households (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER NOT NULL REFERENCES users(id)
);

-- Household members (many-to-many association)
CREATE TABLE household_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'owner' or 'member'
    display_name VARCHAR(50) NOT NULL,  -- e.g., "Bibi", "Pi"
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(household_id, user_id)
);
CREATE INDEX idx_hm_household ON household_members(household_id);
CREATE INDEX idx_hm_user ON household_members(user_id);

-- Invitations table (partner onboarding)
CREATE TABLE invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    email VARCHAR(120) NOT NULL,
    token VARCHAR(64) UNIQUE NOT NULL,  -- 48-char random token
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'accepted', 'expired'
    expires_at TIMESTAMP NOT NULL,  -- 7 days from creation
    invited_by_user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP
);
CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_email ON invitations(email);

-- Transactions table (expense records)
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    merchant VARCHAR(200) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,  -- 'USD' or 'CAD'
    amount_in_usd DECIMAL(10, 2) NOT NULL,  -- Primary currency is USD
    paid_by_user_id INTEGER NOT NULL REFERENCES users(id),
    category VARCHAR(20) NOT NULL,  -- SHARED, I_PAY_FOR_WIFE, etc.
    notes TEXT,
    month_year VARCHAR(7) NOT NULL,  -- Format: "2026-01"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_household_month ON transactions(household_id, month_year);
CREATE INDEX idx_date ON transactions(date);

-- Settlements table (monthly settlement snapshots)
CREATE TABLE settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    month_year VARCHAR(7) NOT NULL,  -- Format: "2026-01"
    settled_date DATE NOT NULL,  -- When the month was marked as settled
    settlement_amount DECIMAL(10, 2) NOT NULL,  -- Absolute amount owed (always positive)
    from_user_id INTEGER NOT NULL REFERENCES users(id),  -- Who owes
    to_user_id INTEGER NOT NULL REFERENCES users(id),  -- Who is owed
    settlement_message VARCHAR(200) NOT NULL,  -- "Pi owes Bibi $75.25"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(household_id, month_year)
);
CREATE INDEX idx_settlement_household_month ON settlements(household_id, month_year);
```

**Key Design Decisions:**
- **Multi-tenancy**: All data (transactions, settlements) is isolated by `household_id`
- **Dynamic members**: Users have a `display_name` per household (not hardcoded)
- **Invitations**: Secure 48-char tokens with 7-day expiration
- **Settlements**: One per household per month (UNIQUE constraint)

### 3.2 Transaction Categories

| Category | Display Name | Split Logic |
|----------|--------------|-------------|
| SHARED | Shared 50/50 | Each member pays 50% |
| I_PAY_FOR_WIFE | Member 1 pays for Member 2 | Member 2 owes 100% |
| WIFE_PAYS_FOR_ME | Member 2 pays for Member 1 | Member 1 owes 100% |
| PERSONAL_ME | Personal (Member 1) | No split (neutral) |
| PERSONAL_WIFE | Personal (Member 2) | No split (neutral) |

**Note**: Category names are legacy from v1.0. Display names in the UI are dynamic based on household member `display_name` fields.

### 3.3 Entity Relationships

```
User ──< HouseholdMember >── Household
                                │
                                ├──< Transaction
                                ├──< Settlement
                                └──< Invitation
```

---

## 4. API Design

### 4.1 Authentication Routes

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET/POST | `/register` | User registration | No (public) |
| GET/POST | `/login` | User login | No (public) |
| GET | `/logout` | User logout | Yes |

### 4.2 Transaction Routes

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | Main page with transaction list | @household_required |
| POST | `/transaction` | Create transaction | @household_required |
| PUT | `/transaction/<id>` | Update transaction | @household_required |
| DELETE | `/transaction/<id>` | Delete transaction | @household_required |

### 4.3 Reconciliation Routes

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/reconciliation` | Monthly summary (current month) | @household_required |
| GET | `/reconciliation/<month>` | Monthly summary for specific month | @household_required |
| GET | `/export/<month>` | Export CSV | @household_required |
| POST | `/settlement` | Mark month as settled | @household_required |
| DELETE | `/settlement/<month>` | Unsettle month | @household_required |

### 4.4 Invitation Routes

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET/POST | `/household/invite` | Send invitation | @household_required |
| POST | `/household/invite/<id>/cancel` | Cancel pending invitation | @household_required |
| GET/POST | `/invite/accept` | Accept invitation | No (public) |

### 4.5 Household Management Routes

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET/POST | `/household/create` | Create new household | @login_required |
| GET | `/household/select` | Select household (multi-household users) | @login_required |
| POST | `/household/switch/<id>` | Switch to different household | @login_required |
| GET/POST | `/household/settings` | Manage household settings | @household_required |
| POST | `/household/leave` | Leave current household | @household_required |

### 4.6 Transaction JSON Schema

```json
{
  "date": "2026-01-15",
  "merchant": "Whole Foods",
  "amount": 125.50,
  "currency": "CAD",
  "paid_by": 1,  // user_id of the member who paid
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
├── app.py                    # Main Flask application (~700 lines)
├── models.py                 # SQLAlchemy models (~240 lines)
├── auth.py                   # Flask-Login configuration
├── decorators.py             # @household_required decorator
├── household_context.py      # Household session helpers
├── email_service.py          # Flask-Mail integration
├── utils.py                  # Helper functions (~150 lines)
├── requirements.txt          # Python dependencies
├── requirements-dev.txt      # Dev dependencies (playwright)
├── Procfile                  # Production server config for Render
├── SPEC.md                   # This file (technical specification)
├── CLAUDE.md                 # Claude Code guidance for this project
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
│
├── static/
│   └── app.js               # Frontend JavaScript (~300 lines)
│
├── templates/
│   ├── auth/
│   │   ├── login.html       # Login form
│   │   └── register.html    # Registration form
│   ├── household/
│   │   ├── setup.html       # Create household wizard
│   │   ├── select.html      # Household switcher
│   │   ├── settings.html    # Manage household
│   │   ├── invite.html      # Send invitations
│   │   ├── invite_sent.html # Invitation success
│   │   ├── accept_invite.html # Accept invitation
│   │   └── invite_invalid.html # Invalid token
│   ├── base.html            # Base template with nav
│   ├── index.html           # Main transaction page
│   └── reconciliation.html  # Monthly summary
│
├── instance/
│   └── database.db          # SQLite database (development)
│
├── data/                    # Production database directory (Render)
│   └── database.db          # SQLite database (production)
│
└── .claude/                 # Claude Code configuration
    ├── settings.json        # MCP servers and hooks config
    └── hooks/
        ├── spec-update-check.py  # Stop hook for SPEC.md updates
        └── sync-structure.py     # Project tree generator utility
```

---

## 8. Dependencies

### 8.1 requirements.txt

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-Mail==0.10.0
Flask-Limiter==3.5.0
email-validator==2.1.0
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.2.0
```

### 8.2 External Services

| Service | Purpose | Cost | URL |
|---------|---------|------|-----|
| frankfurter.app | Currency exchange rates | Free | https://www.frankfurter.app |
| Tailwind CSS CDN | UI styling | Free | https://cdn.tailwindcss.com |
| Alpine.js CDN | Dropdown interactions | Free | https://cdn.jsdelivr.net/npm/alpinejs |

---

## 9. Security

### 9.1 Authentication Security

- **Password hashing**: werkzeug PBKDF2:SHA256
- **Minimum password length**: 8 characters
- **Session cookies**: HTTPOnly, Secure (production), SameSite=Lax

### 9.2 Rate Limiting

| Route | Limit |
|-------|-------|
| POST /login | 10/minute |
| POST /register | 5/minute |

### 9.3 Security Headers (Production)

```python
response.headers['X-Frame-Options'] = 'DENY'
response.headers['X-Content-Type-Options'] = 'nosniff'
response.headers['X-XSS-Protection'] = '1; mode=block'
response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
response.headers['Content-Security-Policy'] = "default-src 'self' ..."
response.headers['Strict-Transport-Security'] = 'max-age=31536000'
```

### 9.4 HTTPS Enforcement

Production automatically redirects HTTP to HTTPS via `X-Forwarded-Proto` header check.

### 9.5 Data Isolation

**Critical**: Every database query MUST filter by `household_id`:

```python
# CORRECT - Isolated to current household
Transaction.query.filter_by(
    household_id=get_current_household_id(),
    month_year=month
).all()

# WRONG - Leaks data between households
Transaction.query.filter_by(month_year=month).all()
```

### 9.6 Invitation Security

- 48-character random tokens (secrets.token_urlsafe)
- 7-day expiration
- One-time use only
- Tokens invalidated after acceptance

---

## 10. Development Workflow

### 10.1 Setup Steps

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

### 10.2 Implementation Status

**✅ v1.0 - Core Features (Completed)**
- ✅ Project structure and database models
- ✅ Transaction CRUD operations
- ✅ Currency conversion (CAD → USD)
- ✅ Monthly reconciliation calculations
- ✅ CSV export functionality

**✅ v1.2 - Settlement Tracking (Completed)**
- ✅ Settlement table and month locking
- ✅ Locked month UI (disabled forms)
- ✅ Unsettle functionality

**✅ v2.0 - Multi-User & Multi-Household (Completed)**
- ✅ User authentication (registration, login, logout)
- ✅ Flask-Login session management
- ✅ Multi-household support with switching
- ✅ Email invitation system with secure tokens
- ✅ Household management (create, settings, leave)
- ✅ Dynamic member display names per household
- ✅ Data isolation by household_id
- ✅ Rate limiting on auth routes (Flask-Limiter)
- ✅ Security headers (CSP, X-Frame-Options, HSTS)
- ✅ HTTPS enforcement in production
- ✅ CSRF protection on all forms

### 10.3 Testing Checklist

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

## 11. Deployment

### 11.1 Production Platform: Render.com

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

### 11.2 Environment Variables

**Required for Production:**

| Variable | Value | Notes |
|----------|-------|-------|
| `FLASK_ENV` | `production` | Disables debug mode, enables security features |
| `SECRET_KEY` | 64-char hex string | Flask session encryption key |
| `SITE_URL` | `https://your-app.onrender.com` | Base URL for invitation links |

**Email Configuration (Optional - for invitations):**

| Variable | Value | Notes |
|----------|-------|-------|
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server |
| `MAIL_PORT` | `587` | TLS port |
| `MAIL_USE_TLS` | `True` | Enable TLS |
| `MAIL_USERNAME` | Your email | SMTP username |
| `MAIL_PASSWORD` | App-specific password | For Gmail, create at myaccount.google.com |
| `MAIL_DEFAULT_SENDER` | `noreply@example.com` | From address |

**Note:** If email is not configured, invitation links are displayed on-screen instead of emailed.

### 11.3 Deployment Steps

See `DEPLOYMENT.md` for complete step-by-step instructions including:
1. Render account creation
2. GitHub repository connection
3. Service configuration (persistent disk, environment variables)
4. Deployment verification
5. Testing procedures
6. Ongoing maintenance

**Cost**: $7/month for Starter tier with persistent disk storage

---

## 12. Success Criteria

The MVP is considered successful when:

1. ✅ **Speed**: Can add a transaction in under 10 seconds
2. ✅ **Automation**: Currency conversion happens automatically
3. ✅ **Clarity**: Who owes what is immediately visible
4. ✅ **Efficiency**: Faster than current Excel workflow
5. ✅ **Accessibility**: Both users can access it from any device

---

## 13. Future Enhancements

### Phase 3 (Next)
- Password reset flow
- Email verification on signup
- Two-factor authentication
- Smart categorization rules
- Bulk CSV import
- Transaction search/filter

### Phase 4 (Advanced)
- PDF bank statement parsing
- Receipt photo upload
- Spending trends charts
- Custom split percentages
- Audit log of changes

### Phase 5 (Enterprise)
- Banking API integration (Plaid)
- Mobile app
- Automated monthly settlements

---

## 14. Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Development | ✅ Completed | Implemented in January 2026 |
| Hosting | $7/month | Render.com Starter tier with persistent disk |
| Domain (optional) | $0 currently | Using free subdomain (yourapp.onrender.com) |
| Currency API | $0 | frankfurter.app free tier (sufficient for personal use) |
| **Total Monthly** | **$7** | **Ongoing** |
| **Annual** | **$84** | **No upfront costs** |

---

## 15. Key Code Snippets

### 15.1 Exchange Rate Function

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

### 15.2 Reconciliation Calculation

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

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 2026 | Initial MVP - single tenant, hardcoded users |
| 1.2 | Jan 2026 | Added settlement tracking and month locking |
| 2.0 | Jan 2026 | Multi-user auth, multi-household, invitations, security |
| 2.1 | Jan 2026 | Added Claude Code Stop hook for automated SPEC.md documentation updates |

---

**Document Version**: 2.1
**Last Updated**: January 7, 2026
**GitHub Repository**: https://github.com/yilunzh/household_finance
