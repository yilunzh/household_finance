# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask-based web application for tracking and reconciling household expenses between two people. Supports multi-currency transactions (USD/CAD) with automatic conversion and monthly reconciliation calculations.

**Primary Currency**: USD (CAD transactions are converted to USD for reconciliation)

## Development Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# Install production dependencies
pip install -r requirements.txt

# For local development with testing tools:
pip install -r requirements-dev.txt

# Run the application (port 5001 to avoid macOS AirPlay conflict)
python app.py
```

Access at: http://localhost:5001

### Playwright MCP Setup (Optional)

The project includes Playwright MCP server integration for browser automation in Claude Code.

**Installation:**
```bash
# Install development dependencies (includes Playwright)
pip install -r requirements-dev.txt

# Download Chromium browser binaries
python -m playwright install chromium
```

**Note**: Playwright is only needed for local MCP integration, not for running the Flask app.

## Architecture

### Core Components

**app.py** - Main Flask application
- Routes for CRUD operations on transactions
- Monthly reconciliation endpoint
- CSV export functionality

**models.py** - Database schema (SQLAlchemy ORM)
- `Transaction` model with fields: date, merchant, amount, currency, amount_in_usd, paid_by, category, notes, month_year
- Categories: SHARED, I_PAY_FOR_WIFE, WIFE_PAYS_FOR_ME, PERSONAL_ME, PERSONAL_WIFE

**utils.py** - Business logic
- `get_exchange_rate()`: Fetches CAD↔USD rates from frankfurter.app API with caching
- `calculate_reconciliation()`: Core algorithm for determining who owes what based on category split logic

**templates/** - Server-rendered HTML with Tailwind CSS
- `base.html`: Base layout
- `index.html`: Transaction entry form and list view
- `reconciliation.html`: Monthly summary and settlement calculation

**static/app.js** - Client-side JavaScript
- AJAX form submission for transactions
- Dynamic UI updates without page reload

### Database

**SQLite** stored in `instance/database.db` (auto-created by Flask-SQLAlchemy)

**Schema changes**: Delete `instance/database.db` and restart app to recreate with new schema (acceptable for MVP)

## Reconciliation Logic

The core business logic calculates who owes what based on transaction categories:

**Split Rules:**
- SHARED: 50/50 split between both people
- I_PAY_FOR_WIFE: Wife owes 100%, I owe 0%
- WIFE_PAYS_FOR_ME: I owe 100%, Wife owes 0%
- PERSONAL_ME/PERSONAL_WIFE: 100% to the person (no split needed)

**Algorithm:**
1. Convert all amounts to USD (primary currency)
2. Sum what each person paid
3. Calculate each person's share based on category rules
4. Settlement = (person_paid - person_share)

See `utils.py:calculate_reconciliation()` for implementation.

## Currency Handling

**Primary Currency**: USD
- USD transactions: No conversion needed, stored as-is
- CAD transactions: Converted to USD using frankfurter.app API, stored in `amount_in_usd` field

**Exchange Rate API**: frankfurter.app (free, no auth required)
- Historical rates cached in memory to minimize API calls
- Fallback to current rate if historical unavailable
- Cache key format: `{from}_{to}_{date}`

**Important**: When adding/updating currency logic, ensure:
- CAD→USD conversion (not USD→CAD)
- USD is default in form dropdowns
- Display shows USD amounts with "USD" label
- CAD amounts show USD equivalent as secondary info

## Key Routes

- `GET /` - Main transaction list for current month
- `POST /transaction` - Create new transaction (converts CAD to USD)
- `PUT /transaction/<id>` - Update transaction
- `DELETE /transaction/<id>` - Delete transaction
- `GET /reconciliation/<month>` - Monthly settlement summary
- `GET /export/<month>` - Download CSV of transactions

## Frontend Architecture

**No build system** - Uses vanilla JavaScript with Tailwind CSS via CDN

**Form submission flow**:
1. JavaScript intercepts form submit (prevents page reload)
2. AJAX POST to `/transaction` endpoint
3. Server returns JSON with created transaction
4. JavaScript updates DOM or reloads page

**Currency dropdown**: USD must be first option (default selection)

## Common Gotchas

1. **Port 5001**: App uses port 5001 to avoid macOS AirPlay Receiver on port 5000
2. **Database location**: SQLite file is in `instance/database.db`, not root directory
3. **Currency direction**: System converts CAD→USD, not USD→CAD
4. **Month format**: Stored as "YYYY-MM" string in `month_year` field for easy filtering
5. **Decimal precision**: Use `Decimal` type for currency calculations to avoid floating-point errors

## Testing Changes

After modifying reconciliation logic or currency conversion:
1. Delete `instance/database.db`
2. Restart Flask app (recreates schema)
3. Add test transactions with different categories
4. Verify reconciliation math on `/reconciliation/<month>` page
5. Check that USD transactions stay in USD, CAD converts to USD

## Configuration

**Environment variables** (`.env` file):
- `SECRET_KEY`: Flask session secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL`: Defaults to `sqlite:///database.db`
- `FLASK_ENV`: Set to `development` for debug mode

## External Dependencies

- frankfurter.app: Free currency exchange API (no signup)
- Tailwind CSS: Loaded from CDN in templates
- SQLite: No installation needed, file-based database
