# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask-based web application for tracking and reconciling household expenses between household members. Supports:
- **Multi-user authentication** with Flask-Login
- **Multi-household support** - users can belong to multiple households
- **Email invitations** for adding household members
- **Multi-currency transactions** (USD/CAD) with automatic conversion
- **Monthly reconciliation** calculations with settlement locking

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

# For stable testing (disables auto-reload):
NO_RELOAD=1 python app.py
```

Access at: http://localhost:5001

### Environment Variables

Copy `.env.example` to `.env` and configure:
- `SECRET_KEY`: Flask session secret (required for production)
- `FLASK_ENV`: Set to `production` for production deployment
- `SITE_URL`: Your production URL (for invitation emails)
- `MAIL_*`: SMTP configuration for sending invitations

## Architecture

### Core Components

**app.py** - Main Flask application
- Authentication routes (login, register, logout)
- Transaction CRUD with household isolation
- Reconciliation and settlement endpoints
- Invitation system routes
- Household management routes
- Security middleware (HTTPS enforcement, rate limiting, security headers)

**models.py** - Database schema (SQLAlchemy ORM)
- `User`: Authentication with password hashing
- `Household`: Multi-tenancy container
- `HouseholdMember`: User-household association with roles
- `Invitation`: Email invitation tokens
- `Transaction`: Expense records with household isolation
- `Settlement`: Monthly settlement snapshots

**auth.py** - Flask-Login configuration and user loader

**decorators.py** - Custom decorators
- `@household_required`: Ensures user has a household context

**household_context.py** - Session-based household management
- `get_current_household_id()`, `get_current_household()`
- `set_current_household()`, `ensure_household_context()`

**email_service.py** - Flask-Mail integration for invitations

**utils.py** - Business logic
- `get_exchange_rate()`: CAD→USD rates from frankfurter.app
- `calculate_reconciliation()`: Dynamic member-based settlement calculation

### Templates

```
templates/
├── auth/
│   ├── login.html
│   └── register.html
├── household/
│   ├── setup.html          # Create household wizard
│   ├── select.html         # Household switcher
│   ├── settings.html       # Manage household
│   ├── invite.html         # Send invitations
│   ├── invite_sent.html    # Invitation success
│   ├── accept_invite.html  # Accept invitation
│   └── invite_invalid.html # Invalid/expired token
├── base.html               # Layout with nav and household switcher
├── index.html              # Transaction list and form
└── reconciliation.html     # Monthly summary
```

### Database

**SQLite** stored in `instance/database.db` (auto-created)

**Key relationships:**
- User → HouseholdMember → Household (many-to-many)
- Household → Transaction, Settlement, Invitation (one-to-many)
- All queries MUST filter by `household_id` for data isolation

## Key Routes

### Authentication
- `GET/POST /register` - User registration (rate limited: 5/min)
- `GET/POST /login` - User login (rate limited: 10/min)
- `GET /logout` - Logout

### Transactions (require @household_required)
- `GET /` - Transaction list for current month
- `POST /transaction` - Create transaction
- `PUT /transaction/<id>` - Update transaction
- `DELETE /transaction/<id>` - Delete transaction

### Reconciliation
- `GET /reconciliation/<month>` - Monthly summary
- `POST /settlement` - Lock month as settled
- `DELETE /settlement/<month>` - Unlock month

### Invitations
- `GET/POST /household/invite` - Send invitation
- `GET/POST /invite/accept` - Accept invitation (public route)
- `POST /household/invite/<id>/cancel` - Cancel invitation

### Household Management
- `GET/POST /household/create` - Create new household
- `GET /household/select` - Select household
- `POST /household/switch/<id>` - Switch household
- `GET/POST /household/settings` - Manage household
- `POST /household/leave` - Leave household

## Security Features

### Production Security
- **HTTPS enforcement** via `X-Forwarded-Proto` header
- **Security headers**: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, CSP, HSTS
- **Rate limiting** on auth routes (Flask-Limiter)
- **CSRF protection** on all forms (Flask-WTF)
- **Secure session cookies** (HTTPOnly, SameSite, Secure in production)

### Data Isolation
Every database query MUST include `household_id` filter:
```python
# CORRECT
Transaction.query.filter_by(household_id=get_current_household_id(), ...)

# WRONG - leaks data between households
Transaction.query.filter_by(...)
```

## CI/CD

- **Security Review**: All PRs trigger an automated Claude security review via GitHub Actions
- Review checks: auth, data isolation, injection attacks, input validation, security headers

## Claude Code Workflow

### Documentation Updates
After completing a feature, trigger SPEC.md updates by saying:
- `/spec-update`
- "feature complete"
- "update spec"
- "update documentation"

The Stop hook gathers context (git changes, conversation, plan) and prompts for documentation updates.

### Hooks
Custom hooks are in `.claude/hooks/`:
- `spec-update-check.py` - Triggers SPEC.md updates on key phrases
- `sync-structure.py` - Generates project tree for SPEC.md

See `docs/archive/HOOKS_SPEC_UPDATE.md` for details.

## Local App Management

Before starting the app, always check if it's already running:
```bash
# Check if app is running on port 5001
lsof -i :5001

# If running, you'll see Python process - no need to start again
# If you need to restart (e.g., to reset rate limits or pick up code changes):
kill <PID> && python app.py

# To start fresh when port is free:
source venv/bin/activate && python app.py
```

**Rate limiting note**: The app uses in-memory rate limiting. If you hit "Too Many Requests" (50/hour limit), restart the app to reset limits.

## Common Gotchas

1. **Port 5001**: Avoids macOS AirPlay conflict on port 5000
2. **Household context**: All protected routes need `@household_required` decorator
3. **Data isolation**: Always filter by `household_id` in queries
4. **Currency direction**: System converts CAD→USD, not USD→CAD
5. **Session management**: `current_household_id` stored in Flask session
6. **Rate limiting**: Auth routes have request limits (10 login/min, 5 register/min)
7. **Render persistent disk**: `FLASK_ENV=production` must be set or database uses ephemeral storage and gets wiped on deploy

## Testing

```bash
# Run unit tests (default - excludes flaky Playwright E2E tests)
pytest

# Run specific test file
pytest tests/test_models.py

# Run E2E Playwright tests (currently flaky, excluded by default)
# pytest tests/test_auth.py tests/test_transactions.py --ignore=""

# Seed test users (test_alice@example.com / test_bob@example.com, password: password123)
python seed_test_users.py
```

**Note:** Playwright E2E tests are excluded by default in pytest.ini due to flakiness. Unit tests are in `test_budget.py`, `test_models.py`, and `test_utils.py`.

## Production Deployment (Render)

**CRITICAL**: `FLASK_ENV=production` must be set for persistent disk to work!
Without it, the app uses `instance/database.db` (ephemeral) instead of `/data/database.db` (persistent).

1. Set environment variables:
   - `FLASK_ENV=production` ← **Required for persistent disk**
   - `SECRET_KEY=<generate-secure-key>`
   - `SITE_URL=https://your-app.onrender.com`
   - Configure `MAIL_*` for email invitations

2. Database persists in `/data/database.db` (requires persistent disk mount at `/data`)

3. Security features activate automatically in production mode

## External Dependencies

- **frankfurter.app**: Free currency exchange API (no auth)
- **Tailwind CSS**: Loaded from CDN
- **Alpine.js**: Loaded from CDN (for dropdowns)
- **SQLite**: File-based database
- **Flask-Mail**: SMTP email sending (optional)

## Documentation

```
docs/
├── SPEC.md                    # Technical specification (source of truth)
├── DEPLOYMENT.md              # Production deployment guide
├── archive/
│   ├── AUTHENTICATION_PLAN.md # Completed implementation plan
│   └── HOOKS_SPEC_UPDATE.md   # SPEC.md auto-update hook docs
└── testing/
    ├── TESTING_PHASE3.md      # Phase 3 testing notes
    └── TESTING_PHASE4.md      # Phase 4 testing notes

.claude/                       # Claude Code configuration
├── settings.json              # MCP servers and hooks config
└── hooks/                     # Custom hooks
    ├── spec-update-check.py   # SPEC.md update trigger
    └── sync-structure.py      # Project tree generator

tests/                         # Python test scripts
├── test_auth.py               # Authentication unit tests
├── test_auth_playwright.py    # Playwright browser tests
├── test_schema.py             # Database schema tests
├── test_phase3_isolation.py   # Data isolation tests
├── test_phase4_dynamic_ui.py  # Dynamic UI tests
├── test_phase4_sync.py        # Sync tests
└── test_phase5_invitations.py # Invitation flow tests
```
