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

## Development Workflow

### Phase 0: BRANCH FIRST (Feature Branches Required)

Before making ANY changes:

1. **Check current branch**: `git branch --show-current`
2. **For new features**: Create feature branch
   ```bash
   git checkout -b feature/<feature-name>
   ```
3. **For bug fixes**: Create fix branch
   ```bash
   git checkout -b fix/<bug-description>
   ```
4. **NEVER commit directly to main** - All changes go through branches → PR

Only small, trivial changes (typo fixes, config tweaks) can go directly to main.

### Merge Requirements

Before merging any PR:
1. **All CI checks must pass** - lint, tests, security review
2. **Wait for checks to complete** - Do NOT merge while checks are "in progress"
3. **If CI fails** - Fix issues in the branch, push, wait for CI again

Never merge a PR with failing or pending CI checks.

### CI & Quality Guidelines

**1. Don't add CI checks the codebase doesn't pass**
- Before adding a new CI check (linter, formatter, etc.), verify existing code passes it
- Either fix existing code first, OR don't add the check yet
- Example: Don't add `black --check` if code isn't already formatted with black

**2. Test hooks locally before merging**
- Run hook scripts directly to verify they work: `python .claude/hooks/<hook>.py`
- Check output format is valid JSON with expected fields
- Verify hooks don't error on edge cases (no staged files, etc.)

**3. Align local hooks with CI**
- Pre-commit hook and CI should run the same checks
- If CI uses `pytest -m unit`, local hook should too
- Prevents "works locally, fails in CI" issues

**4. Keep PRs small and focused**
- Smaller PRs = easier to debug when CI fails
- One logical change per PR when possible
- Large changes should be broken into sequential PRs

### Phase 1: CLARIFY FIRST (Ask Questions Before Coding)

Before writing ANY implementation code, you MUST:

1. **Read related code** - Understand existing patterns
2. **Ask clarifying questions** about:
   - Ambiguous requirements ("Should X also handle Y?")
   - User-facing text (error messages, labels, emails)
   - Edge cases ("What happens if Z?")
   - Scope boundaries ("Does this include W?")
3. **Wait for answers** - Do NOT assume. Wrong assumptions = rework.

Example good clarification:
> "Before implementing the export feature:
> 1. Should CSV include settled months only, or all months?
> 2. What columns should be included?
> 3. Should there be a date range filter?"

### Phase 2: PLAN (Create Todo List)

After clarification, create a todo list with:
- Implementation steps
- Test steps (which tests to update/add)
- Verification step ("Run pytest, confirm passing")

### Phase 3: IMPLEMENT (Autonomous Execution)

Now proceed WITHOUT asking for confirmation:
1. Make incremental changes
2. Run related tests after each change
3. Fix failures immediately
4. Continue to next step

### Context Checkpoints (IMPORTANT)

**Every 3-5 major code edits**, update `.claude/session-context.md` with:

```markdown
## Current Goal
What we're trying to accomplish

## Decisions Made
- Key choice 1 and rationale
- Key choice 2 and rationale

## Files Modified
- file1.py - what changed
- file2.html - what changed

## What's Next
- Remaining step 1
- Remaining step 2
```

**Why this matters:**
- Prevents context loss during long sessions
- Hooks will remind you at 3 edits, insist at 5 edits
- Session end is blocked if incomplete work detected without handoff

**For multi-session work**, write `.claude/handoff.md` before ending with the same sections.

See global `~/.claude/CLAUDE.md` for full context management details.

### Phase 4: VERIFY (Before Claiming Done)

Before saying "done":
1. Run `pytest tests/` - all must pass
2. If user-facing: present options for review
3. Mark todo items completed

**For route/template/blueprint changes (ENFORCED BY HOOK):**

The pre-commit hook blocks commits to UI-affecting files without Playwright verification:
1. Ensure app is running on port 5001
2. Use `browser_navigate` to visit affected pages
3. Use `browser_snapshot` to verify pages load correctly
4. Run `touch .playwright-verified` to mark verification complete
5. Commit proceeds

Files that trigger this check:
- `app.py` (routes)
- `blueprints/**/*.py` (blueprint routes)
- `templates/**/*.html` (templates)
- Any Python file with `@app.route`, `@bp.route`, or `Blueprint(`

### User-Facing Changes (Escalate)

For templates, error messages, reconciliation output, CSV exports, and emails:
1. Propose 2-3 options
2. Recommend one with rationale
3. Wait for selection before implementing

Example:
> "For the error message when a user tries to edit a settled month:
> 1. **'This month is settled and cannot be edited'** (Recommended - clear and direct)
> 2. 'Settlement locked. Unlock in Reconciliation to edit.'
> 3. 'Cannot modify transactions in settled periods.'
> Which do you prefer?"

### Backend Changes (Autonomous)

For routes, models, business logic, test structure:
- Follow existing patterns
- Implement without asking
- Just verify tests pass

### Decision Quick Reference

| Change Type | Action |
|------------|--------|
| New route | Autonomous + **Playwright verify** before commit |
| Route refactoring | Autonomous + **Playwright verify** before commit |
| Template change | ESCALATE + **Playwright verify** before commit |
| Model change | Autonomous - update test_models.py first |
| Business logic | Autonomous - update test_utils.py first |
| Error message | ESCALATE - propose options |
| Email text | ESCALATE - propose options |
| CSV format | ESCALATE - propose options |

### Unit Test Files
- `tests/test_models.py` - Database models and schema
- `tests/test_utils.py` - Business logic (reconciliation, exchange rates)
- `tests/test_budget.py` - Budget tracking features

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
- `pre-commit-check.py` - **Blocking**: Runs tests + lint; blocks direct commits to main; requires Playwright verification for route/template changes
- `post-edit-verify.py` - **Advisory**: Reminds to run tests after editing Python files
- `checkpoint-reminder.py` - **Advisory**: Reminds to checkpoint every 3-5 edits
- `checkpoint-validator.py` - **Advisory**: Validates checkpoint has required sections
- `completion-checklist.py` - **Blocking**: Ensures tests were run before session ends
- `session-handoff.py` - **Blocking**: Detects incomplete work via git/step count/todos
- `spec-update-check.py` - Triggers SPEC.md updates on key phrases
- `sync-structure.py` - Generates project tree for SPEC.md

### Subagents
Custom subagents are in `.claude/agents/`:
- `test-first.md` - TDD specialist, auto-invoked for new features

See `docs/archive/HOOKS_SPEC_UPDATE.md` for hook details.

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

## iOS App Testing (Maestro)

The iOS app uses [Maestro](https://maestro.mobile.dev/) for E2E UI testing. Test files are in `ios/LuckyLedger/maestro/`.

### Prerequisites

1. **Maestro installed** via:
   ```bash
   curl -Ls "https://get.maestro.mobile.dev" | bash
   ```

2. **Java Runtime** - Maestro requires Java. On macOS with Homebrew:
   ```bash
   brew install openjdk@17
   ```

3. **iOS Simulator running** with the app installed

### Running Maestro Tests

**IMPORTANT:** Maestro requires Java in PATH. Always set JAVA_HOME before running:

```bash
# Set Java path (required every time in a new shell)
export JAVA_HOME="/usr/local/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"

# Navigate to iOS project
cd ios/LuckyLedger

# Run a specific test
~/.maestro/bin/maestro test maestro/receipt-flow.yaml

# Run all tests
~/.maestro/bin/maestro test maestro/
```

### Available Test Flows

| Test File | Description |
|-----------|-------------|
| `login-flow.yaml` | Login with test credentials |
| `logout.yaml` | Logout flow |
| `add-transaction.yaml` | Add a new transaction |
| `reconciliation.yaml` | View reconciliation |
| `receipt-flow.yaml` | View transaction details and receipts |

### Test Credentials

- Email: `demo_alice@example.com`
- Password: `password123`

### Common Issues

1. **"Unable to locate a Java Runtime"**
   - Solution: Set JAVA_HOME before running Maestro (see above)

2. **"Config Section Required" error**
   - All Maestro flow files must start with `appId: com.luckyledger.app` followed by `---`

3. **Wrong Maestro installed**
   - Do NOT install via `brew install maestro` (installs wrong app)
   - Use the curl command above for the mobile testing tool

### Debug Output

Test artifacts (screenshots, logs) are saved to:
```
~/.maestro/tests/<timestamp>/
```

Check `screenshot-❌-*.png` for failure screenshots.

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
├── hooks/                     # Custom hooks
│   ├── pre-commit-check.py    # Blocking: tests + lint + branch policy
│   ├── post-edit-verify.py    # Advisory: test reminders after edits
│   ├── completion-checklist.py # Blocking: ensures tests run
│   ├── spec-update-check.py   # SPEC.md update trigger
│   └── sync-structure.py      # Project tree generator
└── agents/                    # Custom subagents
    └── test-first.md          # TDD specialist for new features

tests/                         # Python test scripts
├── test_auth.py               # Authentication unit tests
├── test_auth_playwright.py    # Playwright browser tests
├── test_schema.py             # Database schema tests
├── test_phase3_isolation.py   # Data isolation tests
├── test_phase4_dynamic_ui.py  # Dynamic UI tests
├── test_phase4_sync.py        # Sync tests
└── test_phase5_invitations.py # Invitation flow tests
```
