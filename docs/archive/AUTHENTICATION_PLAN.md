# Authentication & Multi-Household System Implementation Plan

## Overview

Transform the single-tenant household expense tracker into a secure, multi-household system where:
- **Users** can belong to multiple households and switch between them
- **Email-based invitations** allow partner onboarding
- **Existing data** migrates to a default household (zero data loss)
- **Complete data isolation** prevents households from seeing each other's data

## User Decisions

✅ **Multi-household support**: Yes - users can create/join multiple households
✅ **Invitation method**: Email-based invite links (secure tokens)
✅ **Data migration**: **START FRESH** - Drop existing data, clean schema (simpler implementation)

---

## Detailed Implementation Checklist

### Pre-Implementation (Day 0)
- [ ] Backup existing database: `cp instance/database.db instance/database.db.backup_$(date +%Y%m%d)`
- [ ] Create feature branch: `git checkout -b feature/authentication-multi-household`
- [ ] Review complete plan document
- [ ] Set up TodoWrite tracking for implementation phases

---

### Phase 1: Authentication Foundation (Days 1-2)

#### 1.1 Update Dependencies
- [ ] Add Flask-Login==0.6.3 to requirements.txt
- [ ] Add Flask-WTF==1.2.1 to requirements.txt
- [ ] Add email-validator==2.1.0 to requirements.txt
- [ ] Run `pip install -r requirements.txt`
- [ ] Verify all packages installed successfully

#### 1.2 Create User Model (models.py)
- [ ] Import UserMixin from flask_login
- [ ] Import generate_password_hash, check_password_hash from werkzeug.security
- [ ] Create User model class with fields: id, email, password_hash, name, is_active, created_at, last_login
- [ ] Add set_password(password) method
- [ ] Add check_password(password) method
- [ ] Add __repr__ method for debugging

#### 1.3 Create Authentication Module (auth.py)
- [ ] Create new file: auth.py
- [ ] Import LoginManager from flask_login
- [ ] Create LoginManager instance
- [ ] Configure login_view and login_message_category
- [ ] Create user_loader callback function
- [ ] Export login_manager for app initialization

#### 1.4 Create Decorators Module (decorators.py)
- [ ] Create new file: decorators.py
- [ ] Create placeholder @household_required decorator
- [ ] Create placeholder @household_owner_required decorator
- [ ] Add docstrings explaining decorator purposes

#### 1.5 Update Flask Application (app.py)
- [ ] Import LoginManager from auth.py
- [ ] Import and initialize CSRFProtect
- [ ] Initialize LoginManager with app
- [ ] Configure session security (HTTPOnly, SameSite, SECURE, PERMANENT_SESSION_LIFETIME)
- [ ] Add SECRET_KEY configuration

#### 1.6 Create Registration Route (app.py)
- [ ] Create GET /register route
- [ ] Create POST /register route with validation
- [ ] Add error handling and flash messages

#### 1.7 Create Login Route (app.py)
- [ ] Create GET /login route
- [ ] Create POST /login route with validation
- [ ] Handle 'next' parameter for redirects
- [ ] Add error handling and flash messages

#### 1.8 Create Logout Route (app.py)
- [ ] Create GET /logout route
- [ ] Call logout_user() and redirect

#### 1.9 Create Login Template (templates/auth/login.html)
- [ ] Create templates/auth directory
- [ ] Create login.html with form (email, password, CSRF token)
- [ ] Add link to registration page
- [ ] Style with Tailwind CSS

#### 1.10 Create Registration Template (templates/auth/register.html)
- [ ] Create register.html with form (name, email, password, confirm password, CSRF token)
- [ ] Add client-side password confirmation validation
- [ ] Style with Tailwind CSS

#### 1.11 Phase 1 Testing
- [ ] Delete old database and restart app
- [ ] Test user registration flow
- [ ] Test login with valid/invalid credentials
- [ ] Test logout functionality
- [ ] Test session persistence
- [ ] Verify password is hashed in database
- [ ] Commit Phase 1: `git commit -m "Phase 1: Authentication foundation"`

---

### Phase 2: Clean Schema Implementation (Days 3-4)

#### 2.1 Create New Models (models.py)
- [ ] Create Household model (id, name, created_at, created_by_user_id)
- [ ] Create HouseholdMember model (id, household_id, user_id, role, display_name, joined_at)
- [ ] Create Invitation model (id, household_id, email, token, status, expires_at, invited_by_user_id)
- [ ] Add relationships between models

#### 2.2 Update Existing Models (models.py)
- [ ] Update User model: add household_memberships relationship
- [ ] Update Transaction model: REMOVE paid_by, ADD household_id + paid_by_user_id
- [ ] Update Settlement model: REMOVE from_person/to_person, ADD household_id + from_user_id + to_user_id
- [ ] Add composite indexes for performance

#### 2.3 Database Schema Reset
- [ ] Backup current database
- [ ] Delete database: `rm instance/database.db`
- [ ] Create schema reset script with db.drop_all() and db.create_all()
- [ ] Run reset script and verify all tables created

#### 2.4 Create Household Context Module (household_context.py)
- [ ] Create new file: household_context.py
- [ ] Create get_current_household_id() function
- [ ] Create get_current_household() function
- [ ] Create get_current_household_members() function
- [ ] Create set_current_household(household_id) function

#### 2.5 Phase 2 Testing
- [ ] Verify all tables created with correct schema
- [ ] Test foreign key constraints
- [ ] Test unique constraints
- [ ] Commit Phase 2: `git commit -m "Phase 2: Clean multi-tenancy schema"`

---

### Phase 3: Data Isolation + Route Protection (Days 5-7)

#### 3.1 Implement Household Setup Flow (app.py)
- [ ] Create GET /household/setup route
- [ ] Create POST /household/setup route (create household + member)
- [ ] Update registration to redirect to /household/setup

#### 3.2 Update @household_required Decorator (decorators.py)
- [ ] Implement decorator logic: check login + household membership
- [ ] Add proper redirect handling

#### 3.3 Update All Routes with Data Isolation (app.py)
- [ ] Update index() route: add @household_required, filter by household_id
- [ ] Update add_transaction() route: add household_id to new transactions
- [ ] Update update_transaction() route: add ownership check
- [ ] Update delete_transaction() route: add ownership check
- [ ] Update reconciliation() route: filter by household_id
- [ ] Update mark_month_settled() route: add household_id
- [ ] Update unsettle_month() route: filter by household_id
- [ ] Update export_csv() route: filter by household_id

#### 3.4 Update Reconciliation Logic (utils.py)
- [ ] Update calculate_reconciliation() to use user_ids instead of 'ME'/'WIFE'
- [ ] Support dynamic user names from household members

#### 3.5 Phase 3 Testing
- [ ] Create 2 separate households with different users
- [ ] Add transactions to each household
- [ ] Verify complete data isolation between households
- [ ] Test ownership checks on edit/delete
- [ ] Commit Phase 3: `git commit -m "Phase 3: Data isolation and route protection"`

---

### Phase 4: Dynamic UI + Remove Hardcoding (Days 8-10)

#### 4.1 Update Templates (templates/)
- [ ] Update base.html: add household selector dropdown and user menu
- [ ] Update index.html: replace hardcoded paid_by dropdown with dynamic members
- [ ] Update index.html: update category dropdown with dynamic names
- [ ] Update reconciliation.html: replace hardcoded "Bibi"/"Pi" with dynamic names

#### 4.2 Create Household Switching JavaScript (static/js/household.js)
- [ ] Create household.js with switchHousehold() function
- [ ] Include script in base.html

#### 4.3 Update Models and Context (models.py, app.py)
- [ ] Update get_person_display_name() to use user_id + household_id
- [ ] Add context processor to inject household_context globally

#### 4.4 Phase 4 Testing
- [ ] Test household selector in navigation
- [ ] Test dynamic member names in forms
- [ ] Test switching between households
- [ ] Test with 3+ member household
- [ ] Commit Phase 4: `git commit -m "Phase 4: Dynamic UI and remove hardcoding"`

---

### Phase 5: Invitation System (Days 11-14)

#### 5.1 Setup Email Service
- [ ] Add Flask-Mail==0.9.1 to requirements.txt
- [ ] Create email_service.py module
- [ ] Configure email in app.py (MAIL_SERVER, MAIL_PORT, etc.)
- [ ] Add environment variables to .env

#### 5.2 Create Invitation Routes (app.py)
- [ ] Create GET/POST /household/invite route
- [ ] Create GET/POST /invite/accept route

#### 5.3 Create Invitation Templates
- [ ] Create templates/household/invite.html (send invitation form)
- [ ] Create templates/household/accept_invite.html (new user signup)
- [ ] Create templates/household/join_confirm.html (existing user)
- [ ] Create templates/emails/invitation.html (HTML email)
- [ ] Create templates/emails/invitation.txt (plain text email)

#### 5.4 Phase 5 Testing
- [ ] Send invitation to new email
- [ ] Accept invitation and signup
- [ ] Send invitation to existing user
- [ ] Test expired invitations
- [ ] Test canceling invitations
- [ ] Commit Phase 5: `git commit -m "Phase 5: Email invitation system"`

---

### Phase 6: Household Management (Days 15-17)

#### 6.1 Create Household Management Routes (app.py)
- [ ] Create POST /household/create route
- [ ] Create POST /household/switch/<id> route
- [ ] Create GET/POST /household/settings route
- [ ] Create POST /household/leave route

#### 6.2 Implement @household_owner_required Decorator (decorators.py)
- [ ] Update decorator to check role='owner'

#### 6.3 Create Household Management Templates
- [ ] Create templates/household/setup.html
- [ ] Create templates/household/select.html
- [ ] Create templates/household/settings.html

#### 6.4 Update Login Flow
- [ ] Update login route to handle household selection

#### 6.5 Phase 6 Testing
- [ ] Test creating multiple households
- [ ] Test switching between households
- [ ] Test household settings (rename, remove members)
- [ ] Test leaving household
- [ ] Commit Phase 6: `git commit -m "Phase 6: Household management"`

---

### Phase 7: Production Deployment (Days 18-21)

#### 7.1 Security Hardening
- [ ] Add HTTPS enforcement
- [ ] Add Flask-Limiter for rate limiting
- [ ] Add security headers
- [ ] Configure logging

#### 7.2 Production Configuration
- [ ] Create .env.example file
- [ ] Update DEPLOYMENT.md with environment variables
- [ ] Consider PostgreSQL migration (optional)

#### 7.3 Deploy to Production
- [ ] Update Render configuration
- [ ] Add health check endpoint
- [ ] Deploy to Render
- [ ] Monitor deployment logs

#### 7.4 Post-Deployment Verification
- [ ] Test all flows in production
- [ ] Verify email sending works
- [ ] Check logs for errors
- [ ] Test on mobile device

#### 7.5 Documentation
- [ ] Update CLAUDE.md
- [ ] Update README.md
- [ ] Update DEPLOYMENT.md
- [ ] Commit Phase 7: `git commit -m "Phase 7: Production deployment complete"`

---

### Post-Implementation
- [ ] Run linter on all Python files
- [ ] Review and optimize database queries
- [ ] Complete manual testing checklist
- [ ] Run security audit
- [ ] Create user guide
- [ ] Archive plan files

---

## Architecture Summary

### Current State
- **No authentication** - all routes are public
- **Hardcoded users** - 'ME' and 'WIFE' literals (Bibi/Pi)
- **Global data** - no isolation between households
- **Single-tenant** - designed for one couple only

### Target State
- **Flask-Login authentication** - secure session management
- **Multi-household multi-tenancy** - users can join multiple households
- **Dynamic user references** - user IDs instead of 'ME'/'WIFE'
- **Complete data isolation** - every query filtered by household_id

## Database Schema Changes

### New Models

```python
# User model
class User(db.Model, UserMixin):
    id, email, password_hash, name, is_active, is_placeholder, created_at, last_login

# Household model
class Household(db.Model):
    id, name, created_at, created_by_user_id

# HouseholdMember (association table)
class HouseholdMember(db.Model):
    id, household_id, user_id, role ('owner'/'member'), display_name, joined_at
    __table_args__ = UniqueConstraint('household_id', 'user_id')

# Invitation model
class Invitation(db.Model):
    id, household_id, email, token (48-char random), status, expires_at,
    invited_by_user_id, created_at, accepted_at
```

### Updated Models

```python
# Transaction - REPLACE paid_by with user references
- paid_by (DELETE - no longer needed)
+ household_id (FK to Household, NOT NULL, indexed)
+ paid_by_user_id (FK to User, NOT NULL, indexed)
+ Index: (household_id, month_year)

# Settlement - REPLACE from_person/to_person with user references
- from_person (DELETE - no longer needed)
- to_person (DELETE - no longer needed)
+ household_id (FK to Household, NOT NULL, indexed)
+ from_user_id (FK to User, NOT NULL)
+ to_user_id (FK to User, NOT NULL)
~ Unique constraint: month_year → (household_id, month_year)
```

## Implementation Phases

### Phase 1: Authentication Foundation (Week 1, Days 1-2)

**Goal:** Add user authentication without breaking existing functionality

**New Files:**
- `/auth.py` - Flask-Login setup, user_loader
- `/decorators.py` - @login_required, @household_required, @household_owner_required
- `/templates/auth/login.html` - Login form (email/password)
- `/templates/auth/register.html` - Registration form

**Modified Files:**
- `/app.py`:
  - Add Flask-Login initialization
  - Add CSRF protection (Flask-WTF)
  - Add auth routes: GET/POST `/login`, GET/POST `/register`, GET `/logout`
  - Configure session security (HTTPOnly, Secure, SameSite)
- `/models.py`:
  - Add User model with UserMixin
  - Password hashing methods: set_password(), check_password()
- `/requirements.txt`:
  - Add: Flask-Login==0.6.3, Flask-WTF==1.2.1, email-validator==2.1.0

**Data State:** No changes to transactions/settlements

**Testing:**
- User registration works
- Login/logout works
- Session persists across requests
- Password validation works

---

### Phase 2: Clean Schema Implementation (Week 1, Days 3-4)

**Goal:** Implement complete multi-tenancy schema from scratch

**New Files:**
- `/household_context.py` - Helper functions for household context

**Modified Files:**
- `/models.py`:
  - Add User, Household, HouseholdMember, Invitation models
  - **REPLACE Transaction model** - Remove paid_by, add household_id + paid_by_user_id
  - **REPLACE Settlement model** - Remove from_person/to_person, add household_id + user_ids
  - Add relationships (back_populates)
  - **NO backward compatibility** - clean schema

**Schema Reset:**
```python
# Drop old tables
db.drop_all()

# Create new schema with all models
db.create_all()

# Verify tables:
# - users
# - households
# - household_members
# - invitations
# - transactions (new schema with household_id, paid_by_user_id)
# - settlements (new schema with household_id, from_user_id, to_user_id)
```

**Data State:** Clean database, no existing data

**Testing:**
- Verify all tables created
- Verify foreign keys work
- Verify unique constraints enforced
- Test creating sample household + users

---

### Phase 3: Data Isolation + Route Protection (Week 1-2, Days 5-7)

**Goal:** Add household filtering to ALL queries and protect routes

**New Files:**
- `/household_context.py`:
  ```python
  get_current_household_id()
  get_current_household()
  get_current_household_members()
  set_current_household(household_id)
  ```

**Modified Files:**
- `/app.py` - **EVERY ROUTE** needs updates:

**Route Changes:**
```python
# index() - line 46
@app.route('/')
@household_required  # NEW
def index():
    household_id = get_current_household_id()  # NEW

    # OLD: Transaction.query.filter_by(month_year=month)
    # NEW:
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).all()

    members = get_current_household_members()  # NEW

    return render_template('index.html',
                          household_members=members)  # NEW

# add_transaction() - line 79
@app.route('/transaction', methods=['POST'])
@household_required  # NEW
def add_transaction():
    household_id = get_current_household_id()  # NEW

    transaction = Transaction(
        household_id=household_id,  # NEW
        paid_by_user_id=data['paid_by'],  # CHANGED from paid_by='ME'
        # ... rest of fields
    )

# update_transaction() - line 135
@app.route('/transaction/<int:transaction_id>', methods=['PUT'])
@household_required  # NEW
def update_transaction(transaction_id):
    household_id = get_current_household_id()  # NEW

    # OLD: transaction = Transaction.query.get_or_404(transaction_id)
    # NEW: Verify ownership
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        household_id=household_id
    ).first_or_404()

# Similar updates for:
# - delete_transaction()
# - reconciliation()
# - mark_month_settled()
# - unsettle_month()
# - export_csv()
```

- `/utils.py`:
  ```python
  # calculate_reconciliation() - update to use User objects
  def calculate_reconciliation(transactions, household_members):
      # Instead of hardcoded 'me_paid', 'wife_paid'
      # Use dynamic user_payments dict keyed by user_id
      # Return settlement message with actual user names
  ```

**Data State:** Full data isolation enforced

**Testing:**
- Create 2nd test household
- Add transactions to household 2
- Verify household 1 cannot see household 2 data
- Test ownership checks on edit/delete (should 404)
- Test settlement isolation

---

### Phase 4: Dynamic UI + Remove Hardcoding (Week 2, Days 8-10)

**Goal:** Replace hardcoded "Bibi"/"Pi" with dynamic member dropdowns

**Modified Files:**
- `/templates/base.html`:
  ```html
  <!-- Add after line 7 -->
  <div class="flex items-center gap-6">
      <!-- Household Selector -->
      <select onchange="switchHousehold(this.value)">
          {% for membership in current_user.household_memberships %}
          <option value="{{ membership.household.id }}"
                  {% if membership.household.id == current_household.id %}selected{% endif %}>
              {{ membership.household.name }}
          </option>
          {% endfor %}
      </select>

      <!-- User Menu -->
      <div>{{ current_user.name }}</div>
      <a href="{{ url_for('logout') }}">Logout</a>
  </div>
  ```

- `/templates/index.html`:
  ```html
  <!-- Line 144-146: Replace hardcoded paid_by dropdown -->
  <select id="paid_by" name="paid_by">
      {% for member in household_members %}
      <option value="{{ member.user_id }}">{{ member.display_name }}</option>
      {% endfor %}
  </select>

  <!-- Line 156-158: Update category display names -->
  <option value="I_PAY_FOR_WIFE">
      {{ member1.display_name }} pays for {{ member2.display_name }}
  </option>
  ```

- `/templates/reconciliation.html`:
  ```html
  <!-- Lines 118-123: Dynamic member names instead of Bibi/Pi -->
  <div class="flex justify-between">
      <span>{{ member1.display_name }} paid:</span>
      <span>${{ "%.2f"|format(summary[member1.user_id + '_paid']) }}</span>
  </div>
  ```

- `/models.py`:
  ```python
  # Update display name helpers to use HouseholdMember context
  @staticmethod
  def get_person_display_name(user_id, household_id):
      member = HouseholdMember.query.filter_by(
          user_id=user_id, household_id=household_id
      ).first()
      return member.display_name if member else "Unknown"
  ```

**Data State:** UI fully dynamic, supports 2+ member households

**Testing:**
- Create household with 3 members
- Verify dropdowns show all members
- Test reconciliation with multiple members
- Test category display names

---

### Phase 5: Invitation System (Week 2-3, Days 11-14)

**Goal:** Email-based partner invitations

**New Files:**
- `/email_service.py` - Email sending via Flask-Mail
- `/templates/household/invite.html` - Send invitation form
- `/templates/household/accept_invite.html` - Accept invitation (signup)
- `/templates/household/join_confirm.html` - Accept invitation (existing user)
- `/templates/emails/invitation.html` - Email template (HTML)
- `/templates/emails/invitation.txt` - Email template (plain text)

**Modified Files:**
- `/app.py` - Add invitation routes:
  ```python
  @app.route('/household/invite', methods=['GET', 'POST'])
  @household_required
  def send_invitation():
      # Generate token, create Invitation record
      # Send email with link: /invite/accept?token=abc123

  @app.route('/invite/accept', methods=['GET', 'POST'])
  def accept_invitation():
      # Validate token (exists, not expired, not used)
      # If user logged in: just add to household
      # If not logged in: show signup form (email pre-filled)
      # After signup: add to household, mark invitation accepted
  ```

- `/requirements.txt`:
  - Add: Flask-Mail==0.9.1

**Environment Variables (Render):**
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=<app-specific-password>
MAIL_DEFAULT_SENDER=noreply@zhangestate.com
```

**Testing:**
- Send invitation to new email
- Accept invitation → signup → auto-join household
- Send invitation to existing user
- Accept invitation → join household
- Test expired invitation (should fail)
- Test duplicate invitation (should prevent)

---

### Phase 6: Household Management (Week 3, Days 15-17)

**Goal:** Create/switch/manage households

**New Files:**
- `/templates/household/setup.html` - Create first household wizard
- `/templates/household/select.html` - Choose household (login flow)
- `/templates/household/settings.html` - Manage members, rename, invitations

**Modified Files:**
- `/app.py` - Add household management routes:
  ```python
  @app.route('/household/create', methods=['GET', 'POST'])
  @login_required
  def create_household():
      # Create new household, add user as owner
      # Set as current household

  @app.route('/household/switch/<int:household_id>', methods=['POST'])
  @login_required
  def switch_household(household_id):
      # Verify user is member
      # Update session: current_household_id
      # Redirect to /

  @app.route('/household/settings', methods=['GET', 'POST'])
  @household_owner_required
  def household_settings():
      # Rename household
      # View members
      # View pending invitations
      # Remove members (if owner)

  @app.route('/household/leave', methods=['POST'])
  @household_required
  def leave_household():
      # Remove HouseholdMember record
      # If last member, delete household + all data (CASCADE)
      # Redirect to household select
  ```

**Testing:**
- Create multiple households for one user
- Switch between households
- Verify data isolation when switching
- Test leaving household
- Test household deletion (when last member leaves)

---

### Phase 7: Production Deployment (Week 3-4, Days 18-21)

**Goal:** Prepare for production launch

**Database Migration:**
```bash
# Consider upgrading SQLite → PostgreSQL for better concurrency
# On Render:
# 1. Provision PostgreSQL (free tier)
# 2. Update DATABASE_URL in environment variables
# 3. Run migrations
```

**Security Hardening:**
- Add HTTPS enforcement in production
- Add rate limiting on login (Flask-Limiter)
- Add security headers (CSP, X-Frame-Options, etc.)
- Add logging for auth events

**Modified Files:**
- `/app.py`:
  ```python
  # Force HTTPS in production
  @app.before_request
  def force_https():
      if os.environ.get('FLASK_ENV') == 'production':
          if request.headers.get('X-Forwarded-Proto') == 'http':
              return redirect(request.url.replace('http://', 'https://'))

  # Rate limiting
  from flask_limiter import Limiter
  limiter = Limiter(app, key_func=lambda: request.remote_addr)

  @app.route('/login', methods=['POST'])
  @limiter.limit("5 per minute")
  def login():
      # Login logic
  ```

- `/requirements.txt`:
  - Add: Flask-Limiter==3.5.0, psycopg2-binary==2.9.9 (if PostgreSQL)

**Environment Variables (Production):**
```
SECRET_KEY=<generate-with-secrets.token_hex(32)>
DATABASE_URL=postgresql://... (or sqlite:///data/database.db)
FLASK_ENV=production
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=...
MAIL_PASSWORD=...
MAIL_DEFAULT_SENDER=...
```

**Deployment Checklist:**
- [ ] Backup production database
- [ ] Test migration on staging
- [ ] Set all environment variables
- [ ] Deploy new version
- [ ] Monitor logs for errors
- [ ] Test auth flows in production
- [ ] Test data isolation

---

## Critical Files Summary

### Files to Create (18 new files)
1. `/auth.py` - Flask-Login configuration
2. `/decorators.py` - Auth decorators
3. `/household_context.py` - Household helper functions
4. `/email_service.py` - Email sending
5. `/templates/auth/login.html`
6. `/templates/auth/register.html`
7. `/templates/household/setup.html`
8. `/templates/household/invite.html`
9. `/templates/household/accept_invite.html`
10. `/templates/household/join_confirm.html`
11. `/templates/household/select.html`
12. `/templates/household/settings.html`
13. `/templates/emails/invitation.html`
14. `/templates/emails/invitation.txt`
15. `/static/js/household.js` - Dropdown interactions
16. `/tests/test_auth.py` - Authentication tests
17. `/tests/test_data_isolation.py` - Security tests
18. `/tests/test_invitations.py` - Invitation flow tests

### Files to Modify (7 critical files)
1. `/models.py` - Add 4 new models, update 2 existing models
2. `/app.py` - Update ALL routes (8 routes), add 10+ new routes
3. `/utils.py` - Update reconciliation logic for dynamic users
4. `/templates/base.html` - Add navigation with household selector
5. `/templates/index.html` - Dynamic member dropdowns
6. `/templates/reconciliation.html` - Dynamic member names
7. `/requirements.txt` - Add 5 new packages

---

## UX Flows

### First-Time User Flow
```
1. Visit app → Redirect to /login
2. Click "Sign up" → /register
3. Fill form (email, password, name) → Submit
4. Auto-login → Redirect to /household/setup
5. Create household (enter name) → Submit
6. Optionally invite partner → /household/invite
7. Redirect to / (main app)
```

### Partner Accept Invitation Flow (New User)
```
1. Click email link → /invite/accept?token=abc123
2. See household name + inviter
3. Show signup form (email pre-filled)
4. Enter password, display name → Submit
5. Auto-login + join household
6. Redirect to / (main app)
```

### Partner Accept Invitation Flow (Existing User)
```
1. Click email link → /invite/accept?token=abc123
2. If not logged in → Redirect to /login?next=...
3. After login → Show join confirmation
4. Click "Join {Household Name}"
5. Add to household, switch to that household
6. Redirect to / (main app)
```

### Multi-Household Switching
```
1. User in nav dropdown sees current household name
2. Click dropdown → Shows all households
3. Select different household → POST /household/switch
4. Session updated: current_household_id
5. Page reloads with new household context
6. All data now filtered to new household
```

---

## Database Reset Strategy

### Simple Clean Start

**Approach:** Drop existing database and create clean schema

```bash
# 1. Optional: Backup old database for reference
cp instance/database.db instance/database.db.old_$(date +%Y%m%d)

# 2. Delete old database
rm instance/database.db

# 3. Create new schema with auth models
# This happens automatically on app startup with db.create_all()
```

**First User Experience:**
```
1. Visit app → No database → Redirect to /register
2. Register first user (email, password, name)
3. Auto-create first household
4. Redirect to main app (empty, no transactions)
5. Invite partner via email
6. Partner signs up → joins household
7. Start adding transactions
```

**Benefits:**
- ✅ No complex migration logic
- ✅ No data mapping (ME→User1, WIFE→User2)
- ✅ Clean schema from day 1
- ✅ Faster development
- ✅ No rollback needed

---

## Security Considerations

### Data Isolation Rules
**CRITICAL:** Every query MUST filter by household_id

```python
# ❌ BAD - Leaks data across households
Transaction.query.filter_by(month_year=month).all()

# ✅ GOOD - Isolated to current household
Transaction.query.filter_by(
    household_id=get_current_household_id(),
    month_year=month
).all()

# ❌ BAD - Allows editing other household's data
transaction = Transaction.query.get_or_404(transaction_id)

# ✅ GOOD - Verify ownership before edit
transaction = Transaction.query.filter_by(
    id=transaction_id,
    household_id=get_current_household_id()
).first_or_404()
```

### Session Security
```python
# Configure secure sessions
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JS access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
```

### Password Requirements
- Minimum 8 characters
- Hashed with werkzeug.security (PBKDF2)
- No plaintext storage

### Invitation Security
- 48-character random tokens (secrets.token_urlsafe)
- 7-day expiration
- One-time use only
- Tokens invalidated after acceptance

---

## Testing Strategy

### Unit Tests
```python
# tests/test_data_isolation.py
def test_household_a_cannot_see_household_b():
    # Create 2 households with transactions
    # Login as household A
    # Verify cannot see household B data

def test_cannot_edit_other_household_transaction():
    # Try to edit transaction from household B
    # Should return 404 (not 403, to avoid leaking existence)
```

### Integration Tests
```python
# tests/test_auth.py
def test_login_flow()
def test_registration_flow()
def test_session_persistence()
def test_logout_clears_session()

# tests/test_invitations.py
def test_send_invitation()
def test_accept_invitation_new_user()
def test_accept_invitation_existing_user()
def test_expired_invitation_fails()
```

### Manual Testing Checklist
- [ ] Register new user
- [ ] Login/logout
- [ ] Create household
- [ ] Invite partner via email
- [ ] Accept invitation (new user)
- [ ] Accept invitation (existing user)
- [ ] Add transaction in household A
- [ ] Create household B
- [ ] Switch to household B
- [ ] Verify household A data not visible
- [ ] Test reconciliation with 3+ members
- [ ] Test settlement locking
- [ ] Test leaving household
- [ ] Test deleting household

---

## Risk Assessment

### High Risk Items
1. **Data leakage between households** - Mitigated by: comprehensive query filtering, unit tests
2. **Session hijacking** - Mitigated by: secure session config, HTTPS enforcement
3. **Password security** - Mitigated by: werkzeug hashing, password requirements

### Medium Risk Items
1. **Email delivery failures** - Mitigated by: error logging, manual invitation fallback
2. **Invitation token leakage** - Mitigated by: HTTPS, short expiration, one-time use

### Low Risk Items
1. **UI compatibility** - Existing templates will be updated
2. **Deployment complexity** - Standard Flask deployment, no infrastructure changes

---

## Success Criteria

### Must Have (MVP)
- [ ] User registration/login working
- [ ] Household creation working
- [ ] Data isolated by household_id
- [ ] Email invitations working
- [ ] Multi-household switching working
- [ ] No data leakage between households

---

## Timeline Estimate

- **Week 1**: Authentication + Clean Schema + Core Routes (Days 1-7)
- **Week 2**: Dynamic UI + Invitations (Days 8-14)
- **Week 3**: Household Management + Polish (Days 15-21)

**Total:** 3 weeks for full implementation (simplified without migration)

---

## Next Steps After Plan Approval

1. **Immediate**: Optional backup of old database (for reference only)
2. **Day 1**: Start Phase 1 (Authentication foundation)
3. **Daily**: Commit after each phase completion
4. **End of Week 1**: Complete auth + schema + core routes
5. **End of Week 2**: Complete dynamic UI + invitations
6. **End of Week 3**: Complete household management + production deployment

---

**This is a complex, high-impact feature requiring careful execution. Follow the phases sequentially to minimize risk.**
