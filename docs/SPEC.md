# Zhang Estate Expense Tracker - Technical Specification

**Version**: 3.0 (iOS Mobile App & REST API)
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
**In Scope (v3.0):**
- Multi-user authentication (registration, login, logout)
- Multi-household support - users can belong to multiple households
- Email-based invitations for partner onboarding
- Quick transaction entry form
- Transaction list view with modal-based editing
- Transaction search and filter with collapsible sidebar
- Automatic currency conversion (CAD → USD, USD is primary currency)
- Monthly reconciliation calculations
- Settlement locking (mark months as settled)
- CSV export for backup
- Dynamic member display names per household
- Production security (HTTPS enforcement, rate limiting, security headers)
- Production deployment on Render.com with persistent database storage
- **iOS Mobile App** with SwiftUI and full feature parity
- **REST API v1** with JWT authentication for mobile app
- **Receipt photo uploads** for transactions
- **Budget tracking** with expense types and split rules
- **User profile management** with email change and account deletion

**Out of Scope (Future):**
- PDF parsing of bank statements
- Banking API integration
- Two-factor authentication
- Android mobile app
- Advanced charts/analytics

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
| Frontend | HTML + Tailwind CSS + Alpine.js | Simple, no build tools needed, warm theme |
| Currency API | frankfurter.app | Free, no signup required |
| Production Server | Gunicorn | WSGI server for production deployment |
| Hosting | Render.com | $7/month with persistent disk, auto-deploy from GitHub |

### 2.2 System Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Web Browser   │     │   iOS App       │
│  (User Access)  │     │  (SwiftUI)      │
└────────┬────────┘     └────────┬────────┘
         │ HTTP (Session)         │ HTTP (JWT)
         │                        │
         └──────────┬─────────────┘
                    ▼
┌─────────────────────────────────────────────────────┐
│                  Flask Web App                       │
├─────────────────────────────────────────────────────┤
│  app.py (Application Factory)                        │
│    ├── config.py (Configuration)                     │
│    ├── extensions.py (Flask Extensions)              │
│    └── blueprints/ (Domain Routes)                   │
│          ├── auth/          → /login, /register      │
│          ├── transactions/  → /, /transaction        │
│          ├── reconciliation/→ /reconciliation        │
│          ├── household/     → /household/*           │
│          ├── invitations/   → /invite/*              │
│          ├── budget/        → /budget                │
│          ├── profile/       → /profile               │
│          ├── api/           → /api/* (legacy)        │
│          └── api_v1/        → /api/v1/* (REST API)   │
├─────────────────────────────────────────────────────┤
│  services/ (Business Logic Layer)                    │
│    ├── currency_service.py                           │
│    ├── household_service.py                          │
│    ├── reconciliation_service.py                     │
│    └── transaction_service.py                        │
├─────────────────────────────────────────────────────┤
│  models.py (SQLAlchemy ORM)                          │
│  api_decorators.py (JWT Authentication)              │
│  templates/ (Jinja2 HTML)                            │
│  static/ (JS/CSS)                                    │
│  uploads/ (Receipt photos)                           │
└────────┬────────────────────────────────────────────┘
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
    last_login TIMESTAMP,
    password_reset_token VARCHAR(64) UNIQUE,
    password_reset_expires TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX ix_users_password_reset_token ON users(password_reset_token);

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

-- Expense types table (budget categorization)
CREATE TABLE expense_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,  -- e.g., "Grocery", "Dining", "Entertainment"
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(household_id, name)
);
CREATE INDEX idx_expense_types_household ON expense_types(household_id);

-- Auto-category rules (merchant keyword matching)
CREATE TABLE auto_category_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    keyword VARCHAR(100) NOT NULL,  -- Case-insensitive match, e.g., "publix", "whole foods"
    expense_type_id INTEGER NOT NULL REFERENCES expense_types(id) ON DELETE CASCADE,
    category VARCHAR(20),  -- Transaction category (SHARED, PERSONAL, etc.)
    priority INTEGER DEFAULT 0,  -- Higher = checked first
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_auto_rules_household ON auto_category_rules(household_id);
CREATE INDEX idx_household_keyword ON auto_category_rules(household_id, keyword);

-- Budget rules (giver/receiver/amount/categories)
CREATE TABLE budget_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    giver_user_id INTEGER NOT NULL REFERENCES users(id),  -- Who provides the budget
    receiver_user_id INTEGER NOT NULL REFERENCES users(id),  -- Who receives/spends
    monthly_amount DECIMAL(10, 2) NOT NULL,  -- Budget amount per month
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_budget_rules_household ON budget_rules(household_id);

-- Budget rule expense types (many-to-many)
CREATE TABLE budget_rule_expense_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_rule_id INTEGER NOT NULL REFERENCES budget_rules(id) ON DELETE CASCADE,
    expense_type_id INTEGER NOT NULL REFERENCES expense_types(id) ON DELETE CASCADE,
    UNIQUE(budget_rule_id, expense_type_id)
);

-- Budget snapshots (monthly summaries)
CREATE TABLE budget_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_rule_id INTEGER NOT NULL REFERENCES budget_rules(id) ON DELETE CASCADE,
    month_year VARCHAR(7) NOT NULL,  -- Format: "2026-01"
    budget_amount DECIMAL(10, 2) NOT NULL,
    spent_amount DECIMAL(10, 2) NOT NULL,
    giver_reimbursement DECIMAL(10, 2) NOT NULL,  -- Amount giver paid that should be reimbursed
    carryover_from_previous DECIMAL(10, 2) DEFAULT 0,
    net_balance DECIMAL(10, 2) NOT NULL,  -- Positive = surplus, negative = deficit
    is_finalized BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(budget_rule_id, month_year)
);

-- Add expense_type_id and receipt_url to transactions
ALTER TABLE transactions ADD COLUMN expense_type_id INTEGER REFERENCES expense_types(id);
ALTER TABLE transactions ADD COLUMN receipt_url VARCHAR(255);  -- Path to uploaded receipt image

-- Refresh tokens table (JWT token tracking for revocation)
CREATE TABLE refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash of token
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- Device tokens table (push notification tokens for mobile)
CREATE TABLE device_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL,  -- 'ios' or 'android'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, token)
);
CREATE INDEX idx_device_tokens_user ON device_tokens(user_id);

-- Split rules (custom split percentages for shared expenses)
CREATE TABLE split_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    member1_percent INTEGER NOT NULL DEFAULT 50,  -- Owner's percentage (0-100)
    member2_percent INTEGER NOT NULL DEFAULT 50,  -- Other member's percentage (0-100)
    is_default BOOLEAN DEFAULT FALSE,  -- If true, applies to all SHARED without specific rule
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_split_rules_household ON split_rules(household_id);

-- Split rule expense types (many-to-many: which expense types use this split)
CREATE TABLE split_rule_expense_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    split_rule_id INTEGER NOT NULL REFERENCES split_rules(id) ON DELETE CASCADE,
    expense_type_id INTEGER NOT NULL REFERENCES expense_types(id) ON DELETE CASCADE,
    UNIQUE(split_rule_id, expense_type_id)
);
```

**Key Design Decisions:**
- **Multi-tenancy**: All data (transactions, settlements, budgets) is isolated by `household_id`
- **Dynamic members**: Users have a `display_name` per household (not hardcoded)
- **Invitations**: Secure 48-char tokens with 7-day expiration
- **Settlements**: One per household per month (UNIQUE constraint)
- **Budget rules**: Giver provides budget to receiver for specific expense types
- **Auto-categorization**: Merchant keywords auto-detect expense types
- **Split rules**: Custom percentages (e.g., 60/40) with default + per-expense-type overrides
- **Cascade delete**: All household-owned models (expense_types, auto_category_rules, budget_rules, split_rules) cascade delete when household is deleted

### 3.2 Transaction Categories

| Category | Display Name | Split Logic |
|----------|--------------|-------------|
| SHARED | Shared (custom %) | Each member pays their configured percentage (default 50/50) |
| I_PAY_FOR_WIFE | Member 1 pays for Member 2 | Member 2 owes 100% |
| WIFE_PAYS_FOR_ME | Member 2 pays for Member 1 | Member 1 owes 100% |
| PERSONAL_ME | Personal (Member 1) | No split (neutral) |
| PERSONAL_WIFE | Personal (Member 2) | No split (neutral) |

**Note**: Category names are legacy from v1.0. Display names in the UI are dynamic based on household member `display_name` fields.

**Custom Split Percentages (v2.5):**
- SHARED transactions use configurable split percentages (e.g., 60/40, 70/30)
- Default split rule applies to all SHARED transactions without a specific expense type rule
- Per-expense-type split rules override the default (e.g., Groceries at 60/40, Dining at 50/50)
- UI displays actual percentages: "Shared 60/40" instead of generic "Shared"

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
| GET/POST | `/forgot-password` | Request password reset email | No (public) |
| GET/POST | `/reset-password/<token>` | Reset password with token | No (public) |

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

### 4.6 Budget Routes

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/budget` | Budget tracking (current month) | @household_required |
| GET | `/budget/<month>` | Budget tracking for specific month | @household_required |
| POST | `/api/auto-categorize` | Auto-detect expense type from merchant | @household_required |
| POST | `/expense-type` | Create expense type | @household_required |
| PUT | `/expense-type/<id>` | Update expense type | @household_required |
| DELETE | `/expense-type/<id>` | Delete expense type | @household_required |
| POST | `/auto-category-rule` | Add auto-category keyword | @household_required |
| DELETE | `/auto-category-rule/<id>` | Delete auto-category keyword | @household_required |
| POST | `/budget-rule` | Create budget rule | @household_required |
| PUT | `/budget-rule/<id>` | Update budget rule | @household_required |
| DELETE | `/budget-rule/<id>` | Delete budget rule | @household_required |

### 4.7 REST API v1 (Mobile App)

All API v1 routes are prefixed with `/api/v1/` and use JWT authentication.

#### 4.7.1 Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login, returns access + refresh tokens | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | Refresh token |
| POST | `/api/v1/auth/logout` | Logout (revoke refresh token) | Yes |
| GET | `/api/v1/auth/me` | Get current user info | Yes |

**JWT Token Flow:**
- Access tokens expire in 15 minutes
- Refresh tokens expire in 30 days
- Refresh tokens are stored server-side with SHA-256 hash for revocation
- Logout revokes the refresh token

#### 4.7.2 Transactions

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/transactions` | List transactions (with search/filter params) | @jwt_required |
| POST | `/api/v1/transactions` | Create transaction | @jwt_required |
| GET | `/api/v1/transactions/<id>` | Get transaction details | @jwt_required |
| PUT | `/api/v1/transactions/<id>` | Update transaction | @jwt_required |
| DELETE | `/api/v1/transactions/<id>` | Delete transaction | @jwt_required |
| POST | `/api/v1/transactions/<id>/receipt` | Upload receipt photo | @jwt_required |
| DELETE | `/api/v1/transactions/<id>/receipt` | Delete receipt | @jwt_required |
| GET | `/api/v1/receipts/<filename>` | Download receipt image | @jwt_required |

**Query Parameters for GET /transactions:**
- `month`: Filter by month (YYYY-MM format)
- `search`: Search in merchant or notes
- `category`: Filter by category code
- `expense_type_id`: Filter by expense type
- `paid_by_user_id`: Filter by who paid

#### 4.7.3 Households

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/households` | List user's households | @jwt_required |
| POST | `/api/v1/households` | Create household | @jwt_required |
| GET | `/api/v1/households/<id>` | Get household details | @jwt_required |
| GET | `/api/v1/households/<id>/members` | List household members | @jwt_required |
| PUT | `/api/v1/households/<id>/members/<user_id>` | Update member display name | @jwt_required (owner) |
| POST | `/api/v1/households/<id>/leave` | Leave household | @jwt_required |

#### 4.7.4 Invitations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/households/<id>/invitations` | List pending invitations | @jwt_required (owner) |
| POST | `/api/v1/households/<id>/invitations` | Send invitation | @jwt_required (owner) |
| DELETE | `/api/v1/invitations/<id>` | Cancel invitation | @jwt_required (owner) |
| POST | `/api/v1/invitations/accept` | Accept invitation by token | @jwt_required |

#### 4.7.5 Reconciliation

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/reconciliation/<month>` | Get monthly reconciliation | @jwt_required |

#### 4.7.6 Configuration

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/expense-types` | List expense types | @jwt_required |
| POST | `/api/v1/expense-types` | Create expense type | @jwt_required |
| PUT | `/api/v1/expense-types/<id>` | Update expense type | @jwt_required |
| DELETE | `/api/v1/expense-types/<id>` | Delete expense type | @jwt_required |
| GET | `/api/v1/split-rules` | List split rules | @jwt_required |
| POST | `/api/v1/split-rules` | Create split rule | @jwt_required |
| PUT | `/api/v1/split-rules/<id>` | Update split rule | @jwt_required |
| DELETE | `/api/v1/split-rules/<id>` | Delete split rule | @jwt_required |
| GET | `/api/v1/budget-rules` | List budget rules | @jwt_required |
| POST | `/api/v1/budget-rules` | Create budget rule | @jwt_required |
| PUT | `/api/v1/budget-rules/<id>` | Update budget rule | @jwt_required |
| DELETE | `/api/v1/budget-rules/<id>` | Delete budget rule | @jwt_required |
| GET | `/api/v1/categories` | List transaction categories | @jwt_required |

#### 4.7.7 Export

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/export/transactions` | Export all transactions as CSV | @jwt_required |
| GET | `/api/v1/export/transactions/<month>` | Export monthly transactions as CSV | @jwt_required |

#### 4.7.8 Profile

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/profile` | Get user profile | @jwt_required |
| PUT | `/api/v1/profile` | Update profile (name) | @jwt_required |
| POST | `/api/v1/profile/change-password` | Change password | @jwt_required |
| DELETE | `/api/v1/profile` | Delete account | @jwt_required |

### 4.8 Transaction JSON Schema

```json
{
  "date": "2026-01-15",
  "merchant": "Whole Foods",
  "amount": 125.50,
  "currency": "CAD",
  "paid_by": 1,  // user_id of the member who paid
  "category": "SHARED",
  "expense_type_id": 1,  // optional
  "notes": "Weekly groceries",
  "receipt_url": "/api/v1/receipts/abc123.jpg"  // optional, set via upload
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

### 5.4 Budget Tracking Logic

**Important**: Budget tracking is purely informational and does NOT affect settlement calculations. Settlement is calculated solely from transaction categories and split rules.

**Budget Rule Model**: "Giver provides Receiver $X/month for [expense types]"

Example: "Bob gives Alice $1500/month for Grocery, Dining"

**Auto-Split Defaulting Based on Budget Rules:**

When a transaction's expense type matches a budget rule:

| Who Pays | Auto-Default Split | Meaning |
|----------|-------------------|---------|
| Receiver (Alice) | "Alice only" (PERSONAL) | Alice spending from her budget - no reimbursement |
| Giver (Bob) | "Bob → Alice" (PAYS_FOR) | Bob paid, Alice should reimburse from budget |

**Budget Status Calculation:**
```python
def calculate_budget_status(budget_rule, month_year):
    # Get transactions matching expense types in budget rule
    budget_transactions = [txn for txn in transactions
                          if txn.expense_type_id in rule.expense_type_ids]

    spent_amount = sum(txn.amount_in_usd for txn in budget_transactions)

    # Track giver reimbursement (when giver paid for receiver's budget items)
    giver_reimbursement = sum(txn.amount_in_usd for txn in budget_transactions
                             if txn.paid_by_user_id == rule.giver_user_id)

    remaining = budget_amount - spent_amount
    percent_used = (spent_amount / budget_amount) * 100
    is_over_budget = spent_amount > budget_amount

    # Net balance includes carryover from previous months
    net_balance = budget_amount - spent_amount + carryover_from_previous

    return {budget_amount, spent_amount, giver_reimbursement,
            remaining, percent_used, is_over_budget, net_balance}
```

**Year-to-Date Tracking:**
- Cumulative surplus/deficit tracked across months within a year
- Resets to zero on January 1st
- Allows budget flexibility (under-spend one month, over-spend next)

**Auto-Categorization:**
- Merchant keywords (case-insensitive) auto-detect expense types
- Example: "publix", "whole foods" → Grocery expense type
- Applied when merchant field loses focus (blur event)

---

## 6. User Interface Design

### 6.0 Visual Theme

**Design Direction**: Warm & Playful - suitable for family/couple household tracking

**Color Palette** (via Tailwind custom config):

| Color | Hex | Usage |
|-------|-----|-------|
| Terracotta | `#C67B5C` | Primary buttons, accents, CTAs |
| Sage | `#8FAE8B` | Success states, positive amounts, settlement |
| Warm Cream | `#FDF8F3` | Page backgrounds |
| Soft Amber | `#E5A853` | Warnings, highlights, locked states |
| Dusty Rose | `#D4A5A5` | Error states, danger zone |
| Warm Gray | `#3D3833` | Primary text |

**Typography** (Google Fonts via CDN):
- **Display**: Quicksand - rounded, friendly headings
- **Body**: Nunito - clean, readable body text

**Custom SVG Illustrations** (inline, hand-drawn style):
- Cozy house with chimney (login page)
- Two people waving (register page)
- House with piggy bank (empty transactions state)
- Flying envelope with hearts (invitation sent)
- Confused envelope with question marks (invalid invite)
- High-five hands (settled month celebration)
- Open door with welcome mat (accept invitation)

**Animations** (Tailwind keyframes):
- `animate-bounce-gentle` - Subtle float for illustrations
- `animate-wiggle` - Playful shake for success icons
- `animate-fade-in` - Modal backdrops
- `animate-slide-up` - Modal content, toasts
- `animate-scale-in` - Pop-in effect
- Button hover: `-translate-y-0.5` lift effect

**Emoji Accents**:
- Navigation: 📊 Transactions, 🤝 Reconciliation, 💌 Invite, ⚙️ Settings
- Categories: 🤝 Shared, 👤 Personal, 💝 Pays for Partner
- Status indicators: 🔒 Locked, ✅ Settled

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
- Paid By (household members dropdown, defaults to logged-in user)
- Category (dropdown with friendly labels: "Shared Expense", "Bibi pays for Pi", etc.)
- Notes (optional textarea)

**Interactions:**
- Form submit → AJAX POST → Add to list without page reload
- Click Edit button → Opens modal dialog with pre-filled form
- Edit modal → Populate from data attributes → PUT request → Close modal and reload
- Click Delete (×) → Confirm and DELETE request
- Month selector → Load different month (query param: `?month=YYYY-MM`)
- Escape key or backdrop click → Close edit modal

**Transaction Sorting:**
- Primary: Transaction date (newest first)
- Secondary: Created timestamp (most recently added first when dates are equal)

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
├── app.py                    # Application factory and startup (~200 lines)
├── config.py                 # Flask configuration (dev/prod)
├── extensions.py             # Flask extensions (db, csrf, limiter, mail)
├── models.py                 # SQLAlchemy models (~450 lines)
├── auth.py                   # Flask-Login configuration
├── decorators.py             # @household_required decorator (web)
├── api_decorators.py         # @jwt_required, @api_household_required (API)
├── household_context.py      # Household session helpers
├── email_service.py          # Flask-Mail integration
├── utils.py                  # Helper functions (~180 lines)
├── budget_utils.py           # Budget calculation utilities (~220 lines)
├── migrate_budget_tables.py  # Database migration script for budget feature
├── requirements.txt          # Python dependencies
├── requirements-dev.txt      # Dev dependencies (playwright)
├── Procfile                  # Production server config for Render
├── CLAUDE.md                 # Claude Code guidance for this project
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
│
├── blueprints/               # Domain-specific route modules
│   ├── __init__.py           # Blueprint registration
│   ├── auth/                 # Authentication routes
│   │   ├── __init__.py
│   │   └── routes.py         # login, register, logout, password reset
│   ├── transactions/         # Transaction CRUD
│   │   ├── __init__.py
│   │   └── routes.py         # index, create, update, delete, CSV export
│   ├── reconciliation/       # Monthly reconciliation
│   │   ├── __init__.py
│   │   └── routes.py         # view, settle, unsettle
│   ├── household/            # Household management
│   │   ├── __init__.py
│   │   └── routes.py         # create, settings, switch, leave
│   ├── invitations/          # Invitation system
│   │   ├── __init__.py
│   │   └── routes.py         # send, accept, cancel
│   ├── budget/               # Budget tracking
│   │   ├── __init__.py
│   │   └── routes.py         # view budget status
│   ├── profile/              # User profile management
│   │   ├── __init__.py
│   │   └── routes.py         # view, update profile, change email
│   ├── api/                  # JSON API endpoints (legacy)
│   │   ├── __init__.py
│   │   └── routes.py         # expense types, budget rules, auto-categorize
│   └── api_v1/               # REST API for mobile app (JWT auth)
│       ├── __init__.py
│       ├── auth.py           # register, login, refresh, logout
│       ├── transactions.py   # CRUD + receipt upload/download
│       ├── households.py     # list, create, members, leave
│       ├── invitations.py    # send, accept, cancel invitations
│       ├── reconciliation.py # monthly summaries
│       ├── config.py         # expense types, split rules, categories
│       ├── budget.py         # budget rules, split rules CRUD
│       ├── export.py         # CSV export endpoints
│       └── profile.py        # user profile management
│
├── services/                 # Business logic layer
│   ├── __init__.py
│   ├── currency_service.py   # Exchange rate fetching and caching
│   ├── household_service.py  # Household operations
│   ├── reconciliation_service.py  # Settlement calculations
│   └── transaction_service.py     # Transaction CRUD operations
│
├── migrations/               # Alembic database migrations
│   ├── alembic.ini
│   ├── env.py
│   └── script.py.mako
│
├── static/
│   └── app.js               # Frontend JavaScript (~300 lines)
│
├── templates/
│   ├── auth/
│   │   ├── login.html           # Login form
│   │   ├── register.html        # Registration form
│   │   ├── forgot_password.html # Request password reset
│   │   ├── reset_password.html  # Enter new password
│   │   ├── reset_sent.html      # Reset email sent confirmation
│   │   └── reset_invalid.html   # Invalid/expired token
│   ├── household/
│   │   ├── setup.html       # Create household wizard
│   │   ├── select.html      # Household switcher
│   │   ├── settings.html    # Manage household (+ expense types, budget rules)
│   │   ├── invite.html      # Send invitations
│   │   ├── invite_sent.html # Invitation success
│   │   ├── accept_invite.html # Accept invitation
│   │   └── invite_invalid.html # Invalid token
│   ├── budget/
│   │   └── index.html       # Budget tracking page
│   ├── profile/
│   │   ├── index.html           # Profile settings
│   │   ├── email_change_sent.html
│   │   ├── email_confirmed.html
│   │   └── email_invalid.html
│   ├── base.html            # Base template with nav
│   ├── index.html           # Main transaction page (+ expense type dropdown)
│   └── reconciliation.html  # Monthly summary
│
├── tests/                   # Test suite (88 unit tests)
│   ├── conftest.py          # Pytest fixtures
│   ├── test_models.py       # Model unit tests
│   ├── test_utils.py        # Utility function tests (incl. budget/reconciliation regression tests)
│   ├── test_budget.py       # Budget feature tests
│   ├── test_profile.py      # User profile tests
│   └── test_search.py       # Transaction search tests
│
├── instance/
│   └── database.db          # SQLite database (development)
│
├── data/                    # Production database directory (Render)
│   └── database.db          # SQLite database (production)
│
├── uploads/                 # Receipt photo uploads (created at runtime)
│   └── receipts/            # Receipt images (UUID filenames)
│
├── ios/                     # iOS mobile app
│   └── HouseholdTracker/    # Xcode project (see Section 8.3 for details)
│
├── docs/
│   ├── SPEC.md              # This file (technical specification)
│   └── DEPLOYMENT.md        # Production deployment guide
│
└── .claude/                 # Claude Code configuration
    ├── settings.json        # MCP servers and hooks config
    ├── hooks/
    │   ├── pre-commit-check.py   # Blocking: tests + lint + branch policy
    │   ├── post-edit-verify.py   # Advisory: test reminders
    │   ├── completion-checklist.py
    │   ├── spec-update-check.py  # SPEC.md update trigger
    │   └── sync-structure.py     # Project tree generator
    └── agents/
        └── test-first.md    # TDD specialist subagent
```

---

## 8. iOS Mobile App

### 8.1 Overview

Native iOS app built with SwiftUI, providing full feature parity with the web application. Uses JWT authentication to communicate with the REST API v1.

### 8.2 Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Swift | 5.9+ |
| UI Framework | SwiftUI | iOS 17+ |
| Networking | URLSession | Native |
| State Management | @Observable, @Environment | SwiftUI |
| Build System | Xcode | 15+ |
| Testing | Maestro | E2E UI tests |

### 8.3 Project Structure

```
ios/HouseholdTracker/
├── HouseholdTracker/
│   ├── HouseholdTrackerApp.swift    # App entry point
│   ├── ContentView.swift             # Root navigation
│   ├── Models/
│   │   ├── Transaction.swift         # Transaction model
│   │   ├── Household.swift           # Household model
│   │   ├── User.swift                # User model
│   │   ├── ExpenseType.swift         # Expense type model
│   │   ├── SplitRule.swift           # Split rule model
│   │   ├── BudgetRule.swift          # Budget rule model
│   │   └── Reconciliation.swift      # Reconciliation model
│   ├── Services/
│   │   ├── APIService.swift          # HTTP client with JWT auth
│   │   ├── AuthService.swift         # Login, register, token refresh
│   │   └── KeychainService.swift     # Secure token storage
│   ├── Views/
│   │   ├── Auth/
│   │   │   ├── LoginView.swift
│   │   │   └── RegisterView.swift
│   │   ├── Transactions/
│   │   │   ├── TransactionListView.swift
│   │   │   ├── TransactionDetailView.swift
│   │   │   ├── AddTransactionView.swift
│   │   │   ├── EditTransactionView.swift
│   │   │   └── TransactionSearchView.swift
│   │   ├── Households/
│   │   │   ├── HouseholdListView.swift
│   │   │   ├── HouseholdDetailView.swift
│   │   │   ├── CreateHouseholdView.swift
│   │   │   ├── HouseholdMembersView.swift
│   │   │   └── InvitationsView.swift
│   │   ├── Reconciliation/
│   │   │   └── ReconciliationView.swift
│   │   ├── Settings/
│   │   │   ├── SettingsView.swift
│   │   │   ├── ExpenseTypesView.swift
│   │   │   ├── SplitRulesView.swift
│   │   │   ├── BudgetRulesView.swift
│   │   │   └── ExportView.swift
│   │   └── Profile/
│   │       └── ProfileView.swift
│   └── Assets.xcassets/
├── maestro/                          # E2E test flows
│   ├── login-flow.yaml
│   ├── logout.yaml
│   ├── add-transaction.yaml
│   ├── reconciliation.yaml
│   └── receipt-flow.yaml
└── HouseholdTracker.xcodeproj/
```

### 8.4 Key Features

| Feature | iOS Implementation |
|---------|-------------------|
| Authentication | JWT tokens stored in Keychain |
| Transaction CRUD | Full create, read, update, delete |
| Transaction Search | Filter by month, category, expense type, paid by |
| Receipt Photos | Camera/library upload, image viewer |
| Household Management | Create, switch, leave, invite members |
| Reconciliation | Monthly summary with settlement |
| Expense Types | CRUD with icon/color picker |
| Split Rules | Custom percentage configuration |
| Budget Rules | Giver/receiver/amount setup |
| CSV Export | Share sheet integration |
| Profile | Name update, password change, account deletion |

### 8.4.1 Transaction List UI

The transaction list displays each transaction with visual differentiation:

**Expense Type Icons**: Each expense type maps to a semantic cat icon:
| Expense Type | Icon | Rationale |
|--------------|------|-----------|
| Groceries | coins | Money/shopping |
| Food/Dining | happy | Happy cat eating |
| Travel | rocket | Movement/journey |
| Entertainment | celebrate | Fun/celebration |
| Gas/Fuel | rocket | Vehicle/movement |
| Bills/Utilities | lightbulb | Utilities/power |
| Health/Medical | heart | Care/wellness |
| Home/House | house | Housing |
| Other/unset | (category icon) | Fallback |

**Visual Improvements (v3.1)**:
- Expense type text shown below merchant (falls back to "Other" if not set)
- "Paid by" text uses `.textSecondary` for better contrast (WCAG AA)
- Required field asterisks use brand terracotta color instead of red
- Extra bottom padding prevents last transaction from being cut off by tab bar

### 8.5 Authentication Flow

```
┌─────────────┐     POST /auth/login      ┌─────────────┐
│  iOS App    │ ───────────────────────▶  │   Server    │
│             │                           │             │
│             │  ◀─────────────────────   │             │
│             │  {access_token,           │             │
│             │   refresh_token}          │             │
└─────────────┘                           └─────────────┘
      │
      │ Store tokens in Keychain
      ▼
┌─────────────┐     GET /transactions     ┌─────────────┐
│  iOS App    │ ───────────────────────▶  │   Server    │
│  (with JWT) │  Authorization: Bearer    │             │
│             │  <access_token>           │             │
└─────────────┘                           └─────────────┘
      │
      │ If 401 Unauthorized
      ▼
┌─────────────┐     POST /auth/refresh    ┌─────────────┐
│  iOS App    │ ───────────────────────▶  │   Server    │
│             │  {refresh_token}          │             │
│             │  ◀─────────────────────   │             │
│             │  {new_access_token}       │             │
└─────────────┘                           └─────────────┘
```

### 8.6 Testing with Maestro

```bash
# Set Java path (required)
export JAVA_HOME="/usr/local/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"

# Navigate to iOS project
cd ios/HouseholdTracker

# Run a specific test
~/.maestro/bin/maestro test maestro/login-flow.yaml

# Run all tests
~/.maestro/bin/maestro test maestro/
```

**Test credentials**: `demo_alice@example.com` / `password123`

---

## 9. Dependencies

### 9.1 requirements.txt

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-Mail==0.10.0
Flask-Limiter==3.5.0
Flask-Migrate==4.0.5
email-validator==2.1.0
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.2.0
PyJWT==2.8.0
Pillow==10.2.0
```

### 9.2 External Services

| Service | Purpose | Cost | URL |
|---------|---------|------|-----|
| frankfurter.app | Currency exchange rates | Free | https://www.frankfurter.app |
| Tailwind CSS CDN | UI styling with custom config | Free | https://cdn.tailwindcss.com |
| Alpine.js CDN | Dropdown interactions | Free | https://cdn.jsdelivr.net/npm/alpinejs |
| Google Fonts | Typography (Quicksand, Nunito) | Free | https://fonts.googleapis.com |

---

## 10. Security

### 10.1 Authentication Security

- **Password hashing**: werkzeug PBKDF2:SHA256
- **Minimum password length**: 8 characters
- **Session cookies**: HTTPOnly, Secure (production), SameSite=Lax

### 10.2 Rate Limiting

| Route | Limit |
|-------|-------|
| POST /login | 10/minute |
| POST /register | 5/minute |
| POST /forgot-password | 3/minute |
| POST /reset-password | 5/minute |

### 10.3 Security Headers (Production)

```python
response.headers['X-Frame-Options'] = 'DENY'
response.headers['X-Content-Type-Options'] = 'nosniff'
response.headers['X-XSS-Protection'] = '1; mode=block'
response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
response.headers['Content-Security-Policy'] = "default-src 'self' ..."
response.headers['Strict-Transport-Security'] = 'max-age=31536000'
```

### 10.4 HTTPS Enforcement

Production automatically redirects HTTP to HTTPS via `X-Forwarded-Proto` header check.

### 10.5 Data Isolation

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

### 10.6 Invitation Security

- 48-character random tokens (secrets.token_urlsafe)
- 7-day expiration
- One-time use only
- Tokens invalidated after acceptance

### 10.7 Password Reset Security

- 32-character random tokens (secrets.token_urlsafe)
- 1-hour expiration (shorter than invitations for security)
- One-time use only (token cleared after successful reset)
- Does not reveal if email exists (always shows "check your email")
- Rate limited to prevent email enumeration attacks

---

## 11. Development Workflow

### 11.1 Setup Steps

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
open http://localhost:5001

# 6. (Optional) Seed test users for development
python seed_test_users.py
# Creates: test_alice@example.com / test_bob@example.com (password: password123)
```

### 11.2 Implementation Status

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

**✅ v2.2 - Frontend Redesign (Completed)**
- ✅ Warm & playful visual theme (terracotta, sage, cream palette)
- ✅ Custom typography (Quicksand + Nunito via Google Fonts)
- ✅ Custom hand-drawn SVG illustrations for all pages
- ✅ Tailwind custom config with extended color palette
- ✅ CSS animations (bounce, wiggle, fade-in, slide-up, scale-in)
- ✅ Button hover lift effects and smooth transitions
- ✅ Emoji accents throughout UI
- ✅ Redesigned all 12 templates with cohesive warm theme

**✅ v2.3 - Budget Tracking (Completed)**
- ✅ Expense types with household-level management
- ✅ Auto-category rules (merchant keyword matching)
- ✅ Budget rules (giver/receiver/amount/expense types)
- ✅ Budget tracking page with monthly status and progress bars
- ✅ Year-to-date cumulative tracking with January reset
- ✅ Auto-split defaulting based on budget rules
- ✅ Expense type dropdown in transaction form (add and edit)
- ✅ Settings page sections for expense types and budget rules
- ✅ Database migration script for production deployment

**✅ v2.4 - Password Reset & UI Polish (Completed)**
- ✅ Forgot password flow with email reset link
- ✅ Password reset token with 1-hour expiration
- ✅ Rate limiting on forgot/reset endpoints
- ✅ Auto-migration for new database columns on app startup
- ✅ "Forgot password?" link on login page
- ✅ Branded HTML email template for reset emails
- ✅ UI: Notes field moved next to Split dropdown (same row)
- ✅ UI: Visual divider between Add Transaction form and transaction list
- ✅ Improved split category labels ("For X (by Y)" format)

**✅ v2.5 - UX Improvements & Custom Split Percentages (Completed)**
- ✅ Transaction sorting: date desc, then created_at desc (newest additions first for same date)
- ✅ Paid By field defaults to logged-in user when adding transactions
- ✅ Test user seeding script (`seed_test_users.py`) for local development
- ✅ Form layout: Split and Notes fields aligned to grid (3/4 column split matching row above)
- ✅ Custom split percentages: configurable splits beyond 50/50 (e.g., 60/40, 70/30)
- ✅ Split rules: default household split + per-expense-type overrides
- ✅ Split rule management UI in Settings page
- ✅ Transaction list displays actual split percentages (e.g., "Shared 60/40")

**✅ v2.6 - Codebase Refactoring (Completed)**
- ✅ Extract Flask configuration into `config.py` (development/production configs)
- ✅ Extract Flask extensions into `extensions.py` (db, csrf, limiter, mail)
- ✅ Implement Blueprint architecture - split monolithic `app.py` into domain modules:
  - `blueprints/auth/` - Login, register, logout, password reset
  - `blueprints/transactions/` - Transaction CRUD, CSV export
  - `blueprints/reconciliation/` - Monthly reconciliation, settlements
  - `blueprints/household/` - Household management, switching
  - `blueprints/invitations/` - Invitation send/accept/cancel
  - `blueprints/budget/` - Budget tracking
  - `blueprints/profile/` - User profile management
  - `blueprints/api/` - JSON API endpoints for expense types, rules
- ✅ Create services layer for business logic:
  - `services/currency_service.py` - Exchange rate fetching/caching
  - `services/household_service.py` - Household operations
  - `services/reconciliation_service.py` - Settlement calculations
  - `services/transaction_service.py` - Transaction CRUD
- ✅ Add Alembic migrations support (`migrations/`)
- ✅ Update all `url_for()` calls to use blueprint namespaces
- ✅ Update all templates with correct route references
- ✅ Enhanced seed script with sample transactions, categories, and rules

**✅ v2.7 - REST API v1 for Mobile App (Completed)**
- ✅ JWT-based authentication with access/refresh tokens
- ✅ Server-side refresh token tracking for revocation
- ✅ `@jwt_required` and `@api_household_required` decorators
- ✅ Transaction CRUD API endpoints
- ✅ Household management API endpoints
- ✅ Reconciliation API endpoint
- ✅ Configuration API (expense types, split rules, categories)

**✅ v2.8 - Receipt Photo Upload (Completed)**
- ✅ Receipt upload endpoint (`POST /api/v1/transactions/<id>/receipt`)
- ✅ Receipt download endpoint (`GET /api/v1/receipts/<filename>`)
- ✅ Receipt deletion endpoint (`DELETE /api/v1/transactions/<id>/receipt`)
- ✅ Secure file storage with UUID filenames
- ✅ Image validation (JPEG, PNG, GIF, WebP)
- ✅ `receipt_url` field on Transaction model

**✅ v2.9 - Transaction Search & Filter (Completed)**
- ✅ Search by merchant name or notes
- ✅ Filter by month, category, expense type, paid by
- ✅ Collapsible filter sidebar in web UI
- ✅ API query parameters for mobile app

**✅ v3.0 - iOS Mobile App (Completed)**
- ✅ SwiftUI native iOS app with iOS 17+ support
- ✅ JWT authentication with Keychain storage
- ✅ Full transaction CRUD with receipt photo support
- ✅ Household management (create, switch, leave, invite)
- ✅ Reconciliation view with monthly summary
- ✅ Expense types CRUD with icon/color picker
- ✅ Split rules and budget rules configuration
- ✅ CSV export with iOS share sheet
- ✅ Profile management with password change
- ✅ Maestro E2E test suite
- ✅ Security fixes (header injection, CSV injection, data isolation)

**✅ v3.1 - iOS UI Improvements (Completed)**
- ✅ Expense type icon mapping for visual differentiation in transaction list
- ✅ "Paid by" text contrast increased for better readability
- ✅ Required field asterisks use brand terracotta color instead of red
- ✅ Transaction list bottom padding prevents tab bar overlap
- ✅ "Other" fallback displayed when expense type is not set

### 11.3 Testing Checklist

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

## 12. Deployment

### 12.1 Production Platform: Render.com

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

### 12.2 Environment Variables

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

### 12.3 Deployment Steps

See `DEPLOYMENT.md` for complete step-by-step instructions including:
1. Render account creation
2. GitHub repository connection
3. Service configuration (persistent disk, environment variables)
4. Deployment verification
5. Testing procedures
6. Ongoing maintenance

**Cost**: $7/month for Starter tier with persistent disk storage

---

## 13. Success Criteria

The MVP is considered successful when:

1. ✅ **Speed**: Can add a transaction in under 10 seconds
2. ✅ **Automation**: Currency conversion happens automatically
3. ✅ **Clarity**: Who owes what is immediately visible
4. ✅ **Efficiency**: Faster than current Excel workflow
5. ✅ **Accessibility**: Both users can access it from any device

---

## 14. Future Enhancements

### Phase 4 (Next)
- Email verification on signup
- Two-factor authentication
- Push notifications for iOS app
- Bulk CSV import

### Phase 5 (Advanced)
- PDF bank statement parsing
- Spending trends charts
- Audit log of changes
- Android mobile app

### Phase 6 (Enterprise)
- Banking API integration (Plaid)
- Automated monthly settlements
- Multi-currency base (beyond USD)

---

## 15. Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Development | ✅ Completed | Implemented in January 2026 |
| Hosting | $7/month | Render.com Starter tier with persistent disk |
| Domain (optional) | $0 currently | Using free subdomain (yourapp.onrender.com) |
| Currency API | $0 | frankfurter.app free tier (sufficient for personal use) |
| **Total Monthly** | **$7** | **Ongoing** |
| **Annual** | **$84** | **No upfront costs** |

---

## 16. Key Code Snippets

### 16.1 Exchange Rate Function

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

### 16.2 Reconciliation Calculation

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
| 2.2 | Jan 2026 | Frontend redesign: warm theme, custom illustrations, animations |
| 2.3 | Jan 2026 | Budget tracking: expense types, budget rules, auto-split, auto-categorization |
| 2.4 | Jan 2026 | Password reset flow, UI spacing improvements, split category label clarity |
| 2.5 | Jan 2026 | Custom split percentages, split rules UI, UX improvements (sorting, form alignment) |
| 2.6 | Jan 2026 | Codebase refactoring: Blueprint architecture, services layer, config extraction |
| 2.7 | Jan 2026 | REST API v1 with JWT authentication for mobile app |
| 2.8 | Jan 2026 | Receipt photo upload feature |
| 2.9 | Jan 2026 | Transaction search and filter with collapsible sidebar |
| 3.0 | Jan 2026 | iOS mobile app with full feature parity, security fixes |
| 3.1 | Jan 2026 | iOS UI improvements: expense type icons, text contrast, brand colors |
| 3.2 | Jan 2026 | iOS auto-categorization, fix auto_category_rules schema (add household_id, category, priority columns) |
| 3.3 | Jan 2026 | Fix reconciliation double-counting bug, add cascade delete for budget models, regression test coverage |

---

**Document Version**: 3.3
**Last Updated**: January 31, 2026
**GitHub Repository**: https://github.com/yilunzh/household_finance
