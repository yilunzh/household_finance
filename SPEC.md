# Zhang Estate Expense Tracker - Technical Specification

**Version**: 1.0 MVP
**Date**: January 2026
**Status**: Design Complete - Ready for Implementation

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
- Transaction list view with inline editing
- Automatic currency conversion (USD ↔ CAD)
- Monthly reconciliation calculations
- CSV export for backup

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
| Hosting | Railway / PythonAnywhere | $5-10/month, beginner-friendly |

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
    amount_in_cad DECIMAL(10, 2) NOT NULL,
    paid_by TEXT NOT NULL CHECK(paid_by IN ('ME', 'WIFE')),
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
```

### 3.2 Transaction Categories

| Category | Who Paid | Who Benefits | Split Logic |
|----------|----------|--------------|-------------|
| SHARED | Either | Both 50/50 | Each person pays 50% |
| I_PAY_FOR_WIFE | Me | Wife 100% | Wife pays 100%, I pay 0% |
| WIFE_PAYS_FOR_ME | Wife | Me 100% | I pay 100%, Wife pays 0% |
| PERSONAL_ME | Me | Me 100% | No split (neutral) |
| PERSONAL_WIFE | Wife | Wife 100% | No split (neutral) |

---

## 4. API Design

### 4.1 REST Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | `/` | Main page | - | HTML page |
| POST | `/transaction` | Create transaction | Transaction JSON | `{success: bool, transaction: {...}}` |
| PUT | `/transaction/<id>` | Update transaction | Transaction JSON | `{success: bool, transaction: {...}}` |
| DELETE | `/transaction/<id>` | Delete transaction | - | `{success: bool}` |
| GET | `/reconciliation/<month>` | Monthly summary | - | HTML page |
| GET | `/export/<month>` | Export CSV | - | CSV file |

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

**API**: frankfurter.app (free, no auth)

**Endpoint**: `https://api.frankfurter.app/{date}`

**Implementation:**
```python
def get_exchange_rate(from_curr, to_curr, date):
    """
    Fetch historical exchange rate for given date.
    Cache results to minimize API calls.
    """
    # Check cache first
    # If not cached, call API
    # Return rate
```

**Caching Strategy:**
- Cache exchange rates by date
- Rates don't change retroactively
- Store in memory (dict) or SQLite for persistence

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
│  ME paid: $X  │  WIFE paid: $Y      │
│  Result: [WHO] owes [WHO] $Z        │
│  [View Full Reconciliation]         │
├─────────────────────────────────────┤
│  Transaction List                   │
│  ┌───────────────────────────────┐  │
│  │ 01/15  Groceries  $100  [✎][×]│  │ ← Editable rows
│  │ 01/14  Coffee     $5    [✎][×]│  │
│  │ ...                            │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Form Fields:**
- Date (default: today)
- Merchant (text input)
- Amount (number)
- Currency (USD/CAD dropdown)
- Paid By (ME/WIFE dropdown)
- Category (dropdown with friendly labels)
- Notes (optional text)

**Interactions:**
- Form submit → AJAX POST → Add to list without page reload
- Click row → Enable inline editing
- Click [×] → Confirm and delete
- Month selector → Load different month

### 6.2 Reconciliation Page (`/reconciliation/<month>`)

```
┌─────────────────────────────────────┐
│  Reconciliation - January 2026      │
│  [← Back] [Export CSV]              │
├─────────────────────────────────────┤
│  💰 Settlement                      │
│  ┌─────────────────────────────┐   │
│  │  WIFE owes ME $247.50       │   │ ← Big, clear
│  └─────────────────────────────┘   │
├─────────────────────────────────────┤
│  Summary                            │
│  ME paid:        $1,234.56          │
│  WIFE paid:      $987.06            │
│                                     │
│  MY share:       $987.06            │
│  WIFE's share:   $1,234.56          │
├─────────────────────────────────────┤
│  Breakdown by Category              │
│  ┌─────────────────┬────┬──────┐   │
│  │ Category        │ # │ Total│   │
│  ├─────────────────┼────┼──────┤   │
│  │ Shared          │ 15 │ $800 │   │
│  │ I pay for wife  │ 3  │ $120 │   │
│  │ ...             │    │      │   │
│  └─────────────────┴────┴──────┘   │
└─────────────────────────────────────┘
```

---

## 7. Project Structure

```
household_tracker/
├── app.py                    # Main Flask application (~250 lines)
├── models.py                 # Database models (~80 lines)
├── utils.py                  # Helper functions (~120 lines)
├── requirements.txt          # Python dependencies
├── SPEC.md                   # This file
├── README.md                 # Setup & usage instructions
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
│
├── static/
│   ├── app.js               # Frontend JavaScript (~200 lines)
│   └── style.css            # Custom styles (optional, ~50 lines)
│
├── templates/
│   ├── base.html            # Base template (~60 lines)
│   ├── index.html           # Main transaction page (~180 lines)
│   └── reconciliation.html  # Monthly summary (~120 lines)
│
└── database.db              # SQLite database (created at runtime)
```

---

## 8. Dependencies

### 8.1 requirements.txt

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
requests==2.31.0
python-dotenv==1.0.0
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

### 9.2 Development Phases

**Week 1: Backend Foundation**
- Set up project structure
- Create database models (models.py)
- Implement Flask routes (app.py)
- Build utility functions (utils.py)
- Test with curl/Postman

**Week 2: Frontend UI**
- Create base template with Tailwind
- Build transaction entry form
- Create transaction list view
- Style reconciliation page

**Week 3: Interactivity**
- Add JavaScript for form submission
- Implement inline editing
- Add delete confirmation
- Real-time balance updates
- Currency conversion display

**Week 4: Testing & Polish**
- End-to-end testing with real data
- Bug fixes
- CSV export functionality
- Prepare for deployment

### 9.3 Testing Checklist

- [ ] Can add transaction manually
- [ ] USD transactions convert to CAD correctly
- [ ] Can edit existing transaction
- [ ] Can delete transaction
- [ ] Reconciliation calculates correctly
- [ ] Can switch between months
- [ ] CSV export works
- [ ] Works on mobile browser
- [ ] Exchange rate caching works
- [ ] All 5 category types work correctly

---

## 10. Deployment

### 10.1 Recommended: Railway

**Why Railway:**
- Beginner-friendly dashboard
- Free trial, then $5/month
- Automatic HTTPS
- GitHub integration
- Simple rollbacks

**Steps:**
1. Create Railway account
2. Connect GitHub repo
3. Add environment variables
4. Deploy
5. Railway provides URL

### 10.2 Alternative: PythonAnywhere

**Why PythonAnywhere:**
- Free tier available (for testing)
- $5/month for custom domain
- Beginner-friendly interface
- Good documentation

**Steps:**
1. Create account
2. Upload files or clone from GitHub
3. Configure web app
4. Set up virtual environment
5. Reload web app

### 10.3 Environment Variables

```bash
# .env file
FLASK_ENV=production
SECRET_KEY=<random-secret-key>
DATABASE_URL=sqlite:///database.db
```

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
| Development | 25-40 hours | Beginner pace |
| Hosting | $5-10/month | Railway or PythonAnywhere |
| Domain (optional) | $12/year | e.g., expenses.example.com |
| Currency API | $0 | Free tier sufficient |
| **Total Monthly** | **$5-10** | **Ongoing** |

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
        amount_cad = txn.amount_in_cad

        # Track who paid
        if txn.paid_by == 'ME':
            me_paid += amount_cad
        else:
            wife_paid += amount_cad

        # Calculate each person's share
        if txn.category == 'SHARED':
            me_share += amount_cad * 0.5
            wife_share += amount_cad * 0.5
        elif txn.category == 'I_PAY_FOR_WIFE':
            wife_share += amount_cad
        elif txn.category == 'WIFE_PAYS_FOR_ME':
            me_share += amount_cad
        elif txn.category == 'PERSONAL_ME':
            me_share += amount_cad
        elif txn.category == 'PERSONAL_WIFE':
            wife_share += amount_cad

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
    """Format the settlement message."""
    if me_balance > 0.01:  # Account for floating point
        return f"WIFE owes ME ${me_balance:.2f}"
    elif wife_balance > 0.01:
        return f"ME owes WIFE ${wife_balance:.2f}"
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

**Document Version**: 1.0
**Last Updated**: January 6, 2026
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
