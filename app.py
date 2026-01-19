"""
Main Flask application for household expense tracker.
"""
import os
import csv
import logging
from io import StringIO
from flask import Flask, render_template, request, jsonify, Response, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta
from decimal import Decimal

from extensions import db, csrf, limiter, login_manager, mail
from models import (
    Transaction, Settlement, User, Household, HouseholdMember, Invitation,
    ExpenseType, AutoCategoryRule, BudgetRule, BudgetRuleExpenseType, BudgetSnapshot,
    SplitRule, SplitRuleExpenseType
)
from utils import get_exchange_rate, calculate_reconciliation
from budget_utils import calculate_budget_status, get_yearly_cumulative, create_or_update_budget_snapshot
from decorators import household_required
from household_context import (
    get_current_household_id,
    get_current_household,
    get_current_household_members
)
from email_service import init_mail, send_invitation_email, send_password_reset_email, is_mail_configured
from config import config, get_config_name
import secrets

# Import auth to register the user_loader callback
import auth  # noqa: F401

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load configuration from centralized config module
config_name = get_config_name()
app.config.from_object(config[config_name])

# Initialize extensions with app
db.init_app(app)
csrf.init_app(app)
login_manager.init_app(app)
limiter.init_app(app)  # Reads RATELIMIT_* from app.config
init_mail(app)  # Initialize Flask-Mail for invitations


# ============================================================================
# Security Middleware
# ============================================================================

@app.before_request
def enforce_https():
    """Redirect HTTP to HTTPS in production."""
    if not app.debug:  # Production mode
        # Check X-Forwarded-Proto header (set by reverse proxies like Render)
        if request.headers.get('X-Forwarded-Proto') == 'http':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'

    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Enable XSS filter
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Content Security Policy (relaxed for CDN resources) - production only
    csp_policy = app.config.get('CSP_POLICY')
    if csp_policy:
        response.headers['Content-Security-Policy'] = csp_policy

    # Strict Transport Security (HTTPS only in production)
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response


# Initialize database tables when app starts (for production with Gunicorn)
def init_db():
    """Create database tables if they don't exist."""
    with app.app_context():
        db.create_all()
        print('Database tables created (if not already existing)')

        # Run migrations for new columns
        _run_migrations()


def _run_migrations():
    """Add new columns to existing tables if they don't exist."""
    from sqlalchemy import text, inspect

    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('users')]

    # Migration: Add password reset columns (added 2026-01)
    if 'password_reset_token' not in columns:
        try:
            db.session.execute(text('ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(64)'))
            db.session.execute(text('CREATE UNIQUE INDEX ix_users_password_reset_token ON users (password_reset_token)'))
            db.session.commit()
            print('Migration: Added password_reset_token column')
        except Exception as e:
            print(f'Migration password_reset_token skipped: {e}')

    if 'password_reset_expires' not in columns:
        try:
            db.session.execute(text('ALTER TABLE users ADD COLUMN password_reset_expires DATETIME'))
            db.session.commit()
            print('Migration: Added password_reset_expires column')
        except Exception as e:
            print(f'Migration password_reset_expires skipped: {e}')

    # Migration: Create split_rules table (added 2026-01)
    if 'split_rules' not in inspector.get_table_names():
        try:
            db.session.execute(text('''
                CREATE TABLE split_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    household_id INTEGER NOT NULL REFERENCES households(id),
                    member1_percent INTEGER NOT NULL DEFAULT 50,
                    member2_percent INTEGER NOT NULL DEFAULT 50,
                    is_default BOOLEAN DEFAULT FALSE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            db.session.execute(text(
                'CREATE INDEX idx_split_rules_household ON split_rules(household_id)'
            ))
            db.session.commit()
            print('Migration: Created split_rules table')
        except Exception as e:
            db.session.rollback()
            print(f'Migration split_rules skipped: {e}')

    # Migration: Create split_rule_expense_types table (added 2026-01)
    if 'split_rule_expense_types' not in inspector.get_table_names():
        try:
            db.session.execute(text('''
                CREATE TABLE split_rule_expense_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    split_rule_id INTEGER NOT NULL REFERENCES split_rules(id),
                    expense_type_id INTEGER NOT NULL REFERENCES expense_types(id),
                    UNIQUE(split_rule_id, expense_type_id)
                )
            '''))
            db.session.execute(text(
                'CREATE INDEX idx_split_rule_expense_types_rule ON split_rule_expense_types(split_rule_id)'
            ))
            db.session.execute(text(
                'CREATE INDEX idx_split_rule_expense_types_type ON split_rule_expense_types(expense_type_id)'
            ))
            db.session.commit()
            print('Migration: Created split_rule_expense_types table')
        except Exception as e:
            db.session.rollback()
            print(f'Migration split_rule_expense_types skipped: {e}')

    # Migration: Add email change columns to users table (added 2026-01)
    if 'pending_email' not in columns:
        try:
            db.session.execute(text('ALTER TABLE users ADD COLUMN pending_email VARCHAR(120)'))
            db.session.commit()
            print('Migration: Added pending_email column')
        except Exception as e:
            print(f'Migration pending_email skipped: {e}')

    if 'email_change_token' not in columns:
        try:
            db.session.execute(text('ALTER TABLE users ADD COLUMN email_change_token VARCHAR(64)'))
            db.session.execute(text('CREATE UNIQUE INDEX ix_users_email_change_token ON users (email_change_token)'))
            db.session.commit()
            print('Migration: Added email_change_token column')
        except Exception as e:
            print(f'Migration email_change_token skipped: {e}')

    if 'email_change_expires' not in columns:
        try:
            db.session.execute(text('ALTER TABLE users ADD COLUMN email_change_expires DATETIME'))
            db.session.commit()
            print('Migration: Added email_change_expires column')
        except Exception as e:
            print(f'Migration email_change_expires skipped: {e}')


# Call initialization when module is loaded
init_db()


# Context processor to make current_household available in all templates
@app.context_processor
def inject_current_household():
    """Inject current_household into all templates."""
    return {'current_household': get_current_household()}


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    """User registration page."""
    # If user is already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()

        print(f"[DEBUG] Registration attempt: email={email}, name={name}")

        # Validation
        if not email or not password or not name:
            print("[DEBUG] Validation failed: missing fields")
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register.html')

        # Create new user
        user = User(email=email, name=name)
        user.set_password(password)

        try:
            print("[DEBUG] Attempting to save user to database...")
            db.session.add(user)
            db.session.commit()
            print("[DEBUG] User saved successfully!")

            # Auto-login after registration
            login_user(user, remember=True)
            print("[DEBUG] User logged in successfully!")

            flash(f'Welcome, {user.name}! Your account has been created.', 'success')
            # TODO: Phase 2 - Redirect to household setup
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            print(f'[ERROR] Registration error: {e}')
            import traceback
            traceback.print_exc()
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    """User login page."""
    # If user is already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'

        # Validation
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        # Find user by email
        user = User.query.filter_by(email=email).first()

        # Check password
        if user is None or not user.check_password(password):
            logger.warning(f"Failed login attempt for email: {email} from IP: {request.remote_addr}")
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        # Check if account is active
        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'danger')
            return render_template('auth/login.html')

        # Login user
        login_user(user, remember=remember)
        logger.info(f"Successful login for user: {user.email} (ID: {user.id}) from IP: {request.remote_addr}")

        # Update last login timestamp
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Handle 'next' parameter for redirect
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page)

        flash(f'Welcome back, {user.name}!', 'success')
        # TODO: Phase 2 - Redirect to household selection if multiple households
        return redirect(url_for('index'))

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per minute", methods=["POST"])
def forgot_password():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('auth/forgot_password.html')

        # Find user - but don't reveal if they exist
        user = User.query.filter_by(email=email).first()

        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            # Send email
            send_password_reset_email(user, token)
            logger.info(f"Password reset requested for: {email}")

        # Always show success message (don't reveal if email exists)
        return render_template('auth/reset_sent.html', email=email)

    return render_template('auth/forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # Find user by token
    user = User.query.filter_by(password_reset_token=token).first()

    # Check if token is valid and not expired
    if not user or not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        flash('This password reset link is invalid or has expired.', 'danger')
        return render_template('auth/reset_invalid.html')

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not password or not confirm_password:
            flash('Please fill in all fields.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        # Update password and clear token
        user.set_password(password)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()

        logger.info(f"Password reset completed for user: {user.email}")
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/reset_password.html', token=token)


# ============================================================================
# Profile Routes
# ============================================================================

@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('profile/index.html')


@app.route('/profile/update-name', methods=['POST'])
@login_required
def profile_update_name():
    """Update user's account name."""
    name = request.form.get('name', '').strip()

    if not name:
        flash('Name cannot be empty.', 'danger')
        return redirect(url_for('profile'))

    if len(name) > 100:
        flash('Name is too long (max 100 characters).', 'danger')
        return redirect(url_for('profile'))

    current_user.name = name
    db.session.commit()

    flash('Your name has been updated.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/request-email-change', methods=['POST'])
@login_required
@limiter.limit("3 per minute")
def profile_request_email_change():
    """Request email change - sends verification to new email."""
    import secrets

    new_email = request.form.get('new_email', '').strip().lower()
    password = request.form.get('password', '')

    # Validate password
    if not current_user.check_password(password):
        flash('Incorrect password.', 'danger')
        return redirect(url_for('profile'))

    # Validate email format
    if not new_email or '@' not in new_email:
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('profile'))

    # Check if email is same as current
    if new_email == current_user.email:
        flash('This is already your email address.', 'warning')
        return redirect(url_for('profile'))

    # Check if email is already in use
    existing = User.query.filter_by(email=new_email).first()
    if existing:
        flash('This email address is already in use.', 'danger')
        return redirect(url_for('profile'))

    # Generate verification token
    token = secrets.token_urlsafe(32)
    current_user.pending_email = new_email
    current_user.email_change_token = token
    current_user.email_change_expires = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    # Send verification email
    try:
        from email_service import send_email_change_verification
        send_email_change_verification(current_user, new_email, token)
    except Exception as e:
        logger.error(f"Failed to send email change verification: {e}")
        flash('Failed to send verification email. Please try again.', 'danger')
        return redirect(url_for('profile'))

    return render_template('profile/email_change_sent.html', new_email=new_email)


@app.route('/profile/confirm-email/<token>')
def profile_confirm_email(token):
    """Confirm email change with token."""
    user = User.query.filter_by(email_change_token=token).first()

    if not user:
        return render_template('profile/email_invalid.html')

    if user.email_change_expires < datetime.utcnow():
        # Token expired - clear it
        user.pending_email = None
        user.email_change_token = None
        user.email_change_expires = None
        db.session.commit()
        return render_template('profile/email_invalid.html')

    # Update email
    new_email = user.pending_email
    user.email = new_email
    user.pending_email = None
    user.email_change_token = None
    user.email_change_expires = None
    db.session.commit()

    logger.info(f"Email changed for user {user.id} to {new_email}")
    flash('Your email address has been updated.', 'success')
    return render_template('profile/email_confirmed.html', new_email=new_email)


@app.route('/profile/cancel-email-change', methods=['POST'])
@login_required
def profile_cancel_email_change():
    """Cancel pending email change."""
    current_user.pending_email = None
    current_user.email_change_token = None
    current_user.email_change_expires = None
    db.session.commit()

    flash('Email change has been cancelled.', 'info')
    return redirect(url_for('profile'))


@app.route('/profile/change-password', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def profile_change_password():
    """Change user's password."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    # Validate current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile'))

    # Validate new password
    if len(new_password) < 8:
        flash('New password must be at least 8 characters.', 'danger')
        return redirect(url_for('profile'))

    # Confirm passwords match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('profile'))

    # Update password
    current_user.set_password(new_password)
    db.session.commit()

    logger.info(f"Password changed for user: {current_user.email}")
    flash('Your password has been updated.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/delete-account', methods=['POST'])
@login_required
def profile_delete_account():
    """Delete user account and anonymize transactions."""
    password = request.form.get('password', '')
    confirm_delete = request.form.get('confirm_delete', '')

    # Validate password
    if not current_user.check_password(password):
        flash('Incorrect password.', 'danger')
        return redirect(url_for('profile'))

    # Require explicit confirmation
    if confirm_delete != 'DELETE':
        flash('Please type DELETE to confirm account deletion.', 'danger')
        return redirect(url_for('profile'))

    user_id = current_user.id
    user_email = current_user.email

    # Anonymize transactions - set paid_by_user_id to NULL
    Transaction.query.filter_by(paid_by_user_id=user_id).update({'paid_by_user_id': None})

    # Handle household memberships
    for membership in current_user.household_memberships:
        household = membership.household
        member_count = HouseholdMember.query.filter_by(household_id=household.id).count()

        if member_count == 1:
            # Sole member - delete household (transactions already anonymized)
            db.session.delete(household)
        elif membership.role == 'owner':
            # Transfer ownership to another member
            other_member = HouseholdMember.query.filter(
                HouseholdMember.household_id == household.id,
                HouseholdMember.user_id != user_id
            ).first()
            if other_member:
                other_member.role = 'owner'

    # Delete user (CASCADE handles HouseholdMember records)
    db.session.delete(current_user)
    db.session.commit()

    # Logout
    logout_user()

    logger.info(f"Account deleted for user: {user_email}")
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('login'))


@app.route('/api/profile/stats')
@login_required
def api_profile_stats():
    """Get user profile statistics."""
    from utils import calculate_user_stats
    stats = calculate_user_stats(current_user.id)
    return jsonify({'success': True, 'stats': stats})


# ============================================================================
# Main Routes
# ============================================================================

@app.route('/')
@household_required
def index():
    """Main page with transaction form and list."""
    household_id = get_current_household_id()
    household_members = get_current_household_members()

    # Get month from query params, default to current month
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    # Get all transactions for the month (FILTERED BY HOUSEHOLD)
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()

    # Calculate quick summary with split rules
    from utils import build_split_rules_lookup
    split_rules_lookup = build_split_rules_lookup(household_id)
    if transactions:
        summary = calculate_reconciliation(transactions, household_members, None, split_rules_lookup)
    else:
        summary = None

    # Build split info dict for template display: {expense_type_id: (member1_pct, member2_pct)}
    split_display_info = {}
    for key, rule in split_rules_lookup.items():
        split_display_info[key] = (rule.member1_percent, rule.member2_percent)

    # Get list of available months for dropdown (FILTERED BY HOUSEHOLD)
    existing_months = db.session.query(Transaction.month_year).distinct().filter(
        Transaction.household_id == household_id
    ).order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in existing_months]

    # Always ensure current month is in list
    current_month_str = datetime.now().strftime('%Y-%m')
    if current_month_str not in months:
        months.insert(0, current_month_str)

    # If viewing a month not in list (manually typed URL), add it
    if month not in months:
        # Insert in correct chronological position
        months.append(month)
        months.sort(reverse=True)

    # Check if month is settled (HOUSEHOLD-SCOPED)
    is_settled = Settlement.is_month_settled(household_id, month)

    # Get expense types for the dropdown
    expense_types = ExpenseType.query.filter_by(
        household_id=household_id,
        is_active=True
    ).order_by(ExpenseType.name).all()

    # Get budget rules for auto-defaulting split category
    budget_rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()
    budget_rules_json = [r.to_dict() for r in budget_rules]

    return render_template(
        'index.html',
        transactions=transactions,
        current_month=month,
        months=months,
        summary=summary,
        is_settled=is_settled,
        household_members=household_members,
        expense_types=expense_types,
        budget_rules_json=budget_rules_json,
        split_display_info=split_display_info
    )


@app.route('/transaction', methods=['POST'])
@household_required
def add_transaction():
    """Add a new transaction."""
    try:
        household_id = get_current_household_id()
        data = request.json

        # Parse date
        txn_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Get exchange rate if needed
        amount = Decimal(str(data['amount']))
        currency = data['currency']

        if currency == 'CAD':
            rate = get_exchange_rate('CAD', 'USD', txn_date)
            amount_in_usd = amount * Decimal(str(rate))
        else:
            amount_in_usd = amount

        # Check if month is settled (locked) - HOUSEHOLD-SCOPED
        month_year_to_check = txn_date.strftime('%Y-%m')
        if Settlement.is_month_settled(household_id, month_year_to_check):
            return jsonify({
                'success': False,
                'error': f'Cannot add transaction to settled month {month_year_to_check}. This month is locked.'
            }), 403

        # Validate paid_by_user_id belongs to this household
        paid_by_user_id = int(data['paid_by'])  # Now expects user_id instead of 'ME'/'WIFE'
        member = HouseholdMember.query.filter_by(
            household_id=household_id,
            user_id=paid_by_user_id
        ).first()

        if not member:
            return jsonify({
                'success': False,
                'error': 'Invalid user selected. User is not a member of this household.'
            }), 400

        # Handle expense_type_id (optional)
        expense_type_id = data.get('expense_type_id')
        if expense_type_id:
            expense_type_id = int(expense_type_id)
            # Verify it belongs to this household
            expense_type = ExpenseType.query.filter_by(
                id=expense_type_id,
                household_id=household_id,
                is_active=True
            ).first()
            if not expense_type:
                expense_type_id = None

        # Create transaction (NEW SCHEMA)
        transaction = Transaction(
            household_id=household_id,
            date=txn_date,
            merchant=data['merchant'],
            amount=amount,
            currency=currency,
            amount_in_usd=amount_in_usd,
            paid_by_user_id=paid_by_user_id,
            category=data['category'],
            expense_type_id=expense_type_id,
            notes=data.get('notes', ''),
            month_year=txn_date.strftime('%Y-%m')
        )

        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/transaction/<int:transaction_id>', methods=['PUT'])
@household_required
def update_transaction(transaction_id):
    """Update an existing transaction."""
    try:
        household_id = get_current_household_id()

        # Verify ownership: transaction must belong to current household
        transaction = Transaction.query.filter_by(
            id=transaction_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        # Check if OLD month is settled (HOUSEHOLD-SCOPED)
        if Settlement.is_month_settled(household_id, transaction.month_year):
            return jsonify({
                'success': False,
                'error': f'Cannot edit transaction in settled month {transaction.month_year}. This month is locked.'
            }), 403

        # Also check if NEW month (if date changed) is settled
        if 'date' in data:
            new_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            new_month_year = new_date.strftime('%Y-%m')
            if new_month_year != transaction.month_year and Settlement.is_month_settled(household_id, new_month_year):
                return jsonify({
                    'success': False,
                    'error': f'Cannot move transaction to settled month {new_month_year}. That month is locked.'
                }), 403

        # Update fields
        if 'date' in data:
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            transaction.month_year = transaction.date.strftime('%Y-%m')

        if 'merchant' in data:
            transaction.merchant = data['merchant']

        if 'amount' in data or 'currency' in data:
            amount = Decimal(str(data.get('amount', transaction.amount)))
            currency = data.get('currency', transaction.currency)

            transaction.amount = amount
            transaction.currency = currency

            # Recalculate amount_in_usd
            if currency == 'CAD':
                rate = get_exchange_rate('CAD', 'USD', transaction.date)
                transaction.amount_in_usd = amount * Decimal(str(rate))
            else:
                transaction.amount_in_usd = amount

        if 'paid_by' in data:
            # Validate user belongs to household
            paid_by_user_id = int(data['paid_by'])
            member = HouseholdMember.query.filter_by(
                household_id=household_id,
                user_id=paid_by_user_id
            ).first()

            if not member:
                return jsonify({
                    'success': False,
                    'error': 'Invalid user selected.'
                }), 400

            transaction.paid_by_user_id = paid_by_user_id

        if 'category' in data:
            transaction.category = data['category']

        if 'expense_type_id' in data:
            expense_type_id = data['expense_type_id']
            if expense_type_id:
                expense_type_id = int(expense_type_id)
                # Verify it belongs to this household
                expense_type = ExpenseType.query.filter_by(
                    id=expense_type_id,
                    household_id=household_id,
                    is_active=True
                ).first()
                transaction.expense_type_id = expense_type_id if expense_type else None
            else:
                transaction.expense_type_id = None

        if 'notes' in data:
            transaction.notes = data['notes']

        db.session.commit()

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/transaction/<int:transaction_id>', methods=['DELETE'])
@household_required
def delete_transaction(transaction_id):
    """Delete a transaction."""
    try:
        household_id = get_current_household_id()

        # Verify ownership: transaction must belong to current household
        transaction = Transaction.query.filter_by(
            id=transaction_id,
            household_id=household_id
        ).first_or_404()

        # Check if month is settled (HOUSEHOLD-SCOPED)
        if Settlement.is_month_settled(household_id, transaction.month_year):
            return jsonify({
                'success': False,
                'error': f'Cannot delete transaction in settled month {transaction.month_year}. This month is locked.'
            }), 403

        db.session.delete(transaction)
        db.session.commit()

        return jsonify({
            'success': True
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/settlement', methods=['POST'])
@household_required
def mark_month_settled():
    """Mark a month as settled and record the settlement snapshot."""
    try:
        household_id = get_current_household_id()
        household_members = get_current_household_members()
        data = request.json
        month_year = data['month_year']

        # Validation: Check if already settled (HOUSEHOLD-SCOPED)
        if Settlement.is_month_settled(household_id, month_year):
            return jsonify({'success': False, 'error': 'This month has already been settled.'}), 400

        # Validation: Must have transactions (HOUSEHOLD-SCOPED)
        transactions = Transaction.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).all()

        if not transactions:
            return jsonify({'success': False, 'error': 'Cannot settle a month with no transactions.'}), 400

        # Get split rules for custom SHARED splits
        from utils import build_split_rules_lookup
        split_rules_lookup = build_split_rules_lookup(household_id)

        # Calculate reconciliation with household members and split rules
        summary = calculate_reconciliation(transactions, household_members, None, split_rules_lookup)

        # Extract balances (NEW: use dynamic user balances)
        # For now, assume 2-person household (will be enhanced in Phase 4)
        user_balances = summary.get('user_balances', {})

        if len(user_balances) != 2:
            return jsonify({
                'success': False,
                'error': 'Settlement currently only supports 2-person households.'
            }), 400

        # Get the two users and their balances
        user_ids = list(user_balances.keys())
        user1_id = user_ids[0]
        user2_id = user_ids[1]
        user1_balance = Decimal(str(user_balances[user1_id]))
        user2_balance = Decimal(str(user_balances[user2_id]))

        # Determine direction of debt (NEW SCHEMA)
        if user1_balance > Decimal('0.01'):  # User2 owes User1
            from_user_id, to_user_id, settlement_amount = user2_id, user1_id, user1_balance
        elif user2_balance > Decimal('0.01'):  # User1 owes User2
            from_user_id, to_user_id, settlement_amount = user1_id, user2_id, user2_balance
        else:  # All settled up
            from_user_id, to_user_id, settlement_amount = user1_id, user2_id, Decimal('0.00')

        # Create settlement record (NEW SCHEMA)
        settlement = Settlement(
            household_id=household_id,
            month_year=month_year,
            settled_date=datetime.now().date(),
            settlement_amount=settlement_amount,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            settlement_message=summary['settlement']
        )

        db.session.add(settlement)

        # Create budget snapshots for all active budget rules
        budget_rules = BudgetRule.query.filter_by(
            household_id=household_id,
            is_active=True
        ).all()

        for budget_rule in budget_rules:
            create_or_update_budget_snapshot(budget_rule, month_year, finalize=True)

        db.session.commit()

        return jsonify({'success': True, 'settlement': settlement.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/settlement/<month_year>', methods=['DELETE'])
@household_required
def unsettle_month(month_year):
    """Remove settlement record to unlock a month for editing."""
    try:
        household_id = get_current_household_id()

        # Get settlement for this household (HOUSEHOLD-SCOPED)
        settlement = Settlement.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).first()

        if not settlement:
            return jsonify({
                'success': False,
                'error': 'This month is not settled.'
            }), 404

        db.session.delete(settlement)

        # Unfinalize budget snapshots for this month
        budget_rules = BudgetRule.query.filter_by(
            household_id=household_id,
            is_active=True
        ).all()

        for budget_rule in budget_rules:
            snapshot = BudgetSnapshot.query.filter_by(
                budget_rule_id=budget_rule.id,
                month_year=month_year
            ).first()
            if snapshot:
                snapshot.is_finalized = False

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Month {month_year} has been unsettled and is now unlocked.'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/reconciliation')
@app.route('/reconciliation/<month>')
@household_required
def reconciliation(month=None):
    """Show monthly reconciliation summary."""
    household_id = get_current_household_id()
    household_members = get_current_household_members()

    if month is None:
        month = datetime.now().strftime('%Y-%m')

    # Get all transactions for the month (FILTERED BY HOUSEHOLD)
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).all()

    # Get budget rules and calculate budget data for reconciliation
    budget_rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    budget_data = []
    for rule in budget_rules:
        status = calculate_budget_status(rule, month, transactions)
        budget_data.append({
            'rule': rule,
            'giver_name': rule.get_giver_display_name(),
            'giver_user_id': rule.giver_user_id,
            'receiver_name': rule.get_receiver_display_name(),
            'receiver_user_id': rule.receiver_user_id,
            'monthly_amount': rule.monthly_amount,
            'expense_type_names': rule.get_expense_type_names(),
            'status': status,
        })

    # Get split rules for custom SHARED splits
    from utils import build_split_rules_lookup
    split_rules_lookup = build_split_rules_lookup(household_id)

    # Calculate reconciliation with household members, budget data, and split rules
    summary = calculate_reconciliation(transactions, household_members, budget_data, split_rules_lookup)

    # Get list of available months (FILTERED BY HOUSEHOLD)
    all_months = db.session.query(Transaction.month_year).distinct().filter(
        Transaction.household_id == household_id
    ).order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in all_months]

    # Check if month is settled (HOUSEHOLD-SCOPED)
    settlement = Settlement.get_settlement(household_id, month)

    # Get split rules for display
    split_rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()
    split_rules_data = [r.to_dict(household_members) for r in split_rules]

    # Build split info dict for template display: {expense_type_id: (member1_pct, member2_pct)}
    split_display_info = {}
    for key, rule in split_rules_lookup.items():
        split_display_info[key] = (rule.member1_percent, rule.member2_percent)

    return render_template(
        'reconciliation.html',
        summary=summary,
        month=month,
        months=months,
        transactions=transactions,
        settlement=settlement,
        household_members=household_members,
        budget_data=budget_data,
        split_rules=split_rules_data,
        split_display_info=split_display_info
    )


@app.route('/export/<month>')
@household_required
def export_csv(month):
    """Export transactions for a month as CSV."""
    household_id = get_current_household_id()
    household_members = get_current_household_members()

    # Get transactions for this household (FILTERED BY HOUSEHOLD)
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).order_by(Transaction.date).all()

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Date', 'Merchant', 'Amount', 'Currency', 'Amount (USD)',
        'Paid By', 'Category', 'Notes'
    ])

    # Write transactions
    for txn in transactions:
        writer.writerow([
            txn.date.strftime('%Y-%m-%d'),
            txn.merchant,
            f'{float(txn.amount):.2f}',
            txn.currency,
            f'{float(txn.amount_in_usd):.2f}',  # FIXED: was amount_in_cad
            txn.get_paid_by_display_name(),  # NEW: Use household member display name
            Transaction.get_category_display_name(txn.category, household_members),
            txn.notes or ''
        ])

    # Add summary (with household members)
    summary = calculate_reconciliation(transactions, household_members)
    writer.writerow([])
    writer.writerow(['SUMMARY'])

    # Dynamic member names in summary
    for member in household_members:
        user_id = member.user_id
        if user_id in summary.get('user_payments', {}):
            paid_amount = summary['user_payments'][user_id]
            writer.writerow([f'{member.display_name} paid', f'${paid_amount:.2f}'])

    writer.writerow([])
    writer.writerow(['Settlement', summary['settlement']])

    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=expenses_{month}.csv'
        }
    )


# ============================================================================
# Invitation Routes
# ============================================================================

@app.route('/household/invite', methods=['GET', 'POST'])
@household_required
def send_invitation():
    """Send an invitation to join the household."""
    household_id = get_current_household_id()
    household = get_current_household()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        # Validation
        if not email:
            flash('Email address is required.', 'danger')
            return redirect(url_for('send_invitation'))

        # Check if email is already a member of this household
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            existing_member = HouseholdMember.query.filter_by(
                household_id=household_id,
                user_id=existing_user.id
            ).first()
            if existing_member:
                flash('This user is already a member of your household.', 'warning')
                return redirect(url_for('send_invitation'))

        # Check for existing pending invitation
        existing_invite = Invitation.query.filter_by(
            household_id=household_id,
            email=email,
            status='pending'
        ).first()
        if existing_invite:
            if existing_invite.is_valid():
                flash('An invitation has already been sent to this email.', 'warning')
                return redirect(url_for('send_invitation'))
            else:
                # Mark old invitation as expired
                existing_invite.status = 'expired'
                db.session.commit()

        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Create invitation
        invitation = Invitation(
            household_id=household_id,
            email=email,
            token=token,
            status='pending',
            expires_at=datetime.utcnow() + timedelta(days=7),
            invited_by_user_id=current_user.id
        )

        db.session.add(invitation)
        db.session.commit()

        # Send email
        email_sent = send_invitation_email(invitation, household, current_user)

        # Build invite URL for display if email not configured
        site_url = os.environ.get('SITE_URL', 'http://localhost:5001')
        invite_url = f"{site_url}/invite/accept?token={token}"

        return render_template(
            'household/invite_sent.html',
            email=email,
            email_sent=email_sent,
            invite_url=invite_url
        )

    # GET request - show invite form
    pending_invitations = Invitation.query.filter_by(
        household_id=household_id,
        status='pending'
    ).order_by(Invitation.created_at.desc()).all()

    # Filter to only valid (non-expired) invitations
    pending_invitations = [inv for inv in pending_invitations if inv.is_valid()]

    return render_template(
        'household/invite.html',
        household=household,
        pending_invitations=pending_invitations,
        mail_configured=is_mail_configured()
    )


@app.route('/household/invite/<int:invitation_id>/cancel', methods=['POST'])
@household_required
def cancel_invitation(invitation_id):
    """Cancel a pending invitation."""
    household_id = get_current_household_id()

    invitation = Invitation.query.filter_by(
        id=invitation_id,
        household_id=household_id,
        status='pending'
    ).first_or_404()

    invitation.status = 'cancelled'
    db.session.commit()

    flash('Invitation has been cancelled.', 'info')
    return redirect(url_for('send_invitation'))


@app.route('/invite/accept', methods=['GET', 'POST'])
def accept_invitation():
    """Accept an invitation to join a household."""
    token = request.args.get('token') or request.form.get('token')

    if not token:
        return render_template('household/invite_invalid.html', reason='not_found')

    # Find invitation by token
    invitation = Invitation.query.filter_by(token=token).first()

    if not invitation:
        return render_template('household/invite_invalid.html', reason='not_found')

    if invitation.status == 'accepted':
        return render_template('household/invite_invalid.html', reason='used')

    if not invitation.is_valid():
        return render_template('household/invite_invalid.html', reason='expired')

    # Get household and inviter info
    household = Household.query.get(invitation.household_id)
    inviter = User.query.get(invitation.invited_by_user_id)

    if request.method == 'POST':
        action = request.form.get('action')
        display_name = request.form.get('display_name', '').strip()

        if action == 'join' and current_user.is_authenticated:
            # Logged-in user joining
            if not display_name:
                display_name = current_user.name

            # Check if already a member
            existing_member = HouseholdMember.query.filter_by(
                household_id=invitation.household_id,
                user_id=current_user.id
            ).first()

            if existing_member:
                flash('You are already a member of this household.', 'warning')
                return redirect(url_for('index'))

            # Add user to household
            member = HouseholdMember(
                household_id=invitation.household_id,
                user_id=current_user.id,
                role='member',
                display_name=display_name
            )
            db.session.add(member)

            # Mark invitation as accepted
            invitation.status = 'accepted'
            invitation.accepted_at = datetime.utcnow()
            db.session.commit()

            flash(f'Welcome to {household.name}!', 'success')
            return redirect(url_for('index'))

        elif action == 'signup':
            # New user signup
            email = invitation.email  # Use invitation email
            name = request.form.get('name', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not display_name:
                display_name = name

            # Validation
            if not name or not password:
                flash('Name and password are required.', 'danger')
                return render_template(
                    'household/accept_invite.html',
                    invitation=invitation,
                    household=household,
                    inviter=inviter,
                    token=token
                )

            if len(password) < 8:
                flash('Password must be at least 8 characters.', 'danger')
                return render_template(
                    'household/accept_invite.html',
                    invitation=invitation,
                    household=household,
                    inviter=inviter,
                    token=token
                )

            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template(
                    'household/accept_invite.html',
                    invitation=invitation,
                    household=household,
                    inviter=inviter,
                    token=token
                )

            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('An account with this email already exists. Please log in instead.', 'warning')
                return redirect(url_for('login', next=url_for('accept_invitation', token=token)))

            # Create new user
            user = User(email=email, name=name)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # Get user ID

            # Add user to household
            member = HouseholdMember(
                household_id=invitation.household_id,
                user_id=user.id,
                role='member',
                display_name=display_name or name
            )
            db.session.add(member)

            # Mark invitation as accepted
            invitation.status = 'accepted'
            invitation.accepted_at = datetime.utcnow()

            db.session.commit()

            # Auto-login
            login_user(user, remember=True)

            flash(f'Welcome to {household.name}!', 'success')
            return redirect(url_for('index'))

    # GET request - show accept form
    return render_template(
        'household/accept_invite.html',
        invitation=invitation,
        household=household,
        inviter=inviter,
        token=token,
        suggested_name=None  # Could pre-fill from invitation if stored
    )


# ============================================================================
# Household Management Routes
# ============================================================================

@app.route('/household/create', methods=['GET', 'POST'])
@login_required
def create_household():
    """Create a new household."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()

        if not name:
            flash('Household name is required.', 'danger')
            return render_template('household/setup.html')

        if not display_name:
            display_name = current_user.name

        # Create household
        household = Household(
            name=name,
            created_by_user_id=current_user.id
        )
        db.session.add(household)
        db.session.flush()  # Get household ID

        # Add creator as owner
        member = HouseholdMember(
            household_id=household.id,
            user_id=current_user.id,
            role='owner',
            display_name=display_name
        )
        db.session.add(member)
        db.session.commit()

        # Set as current household in session
        from flask import session
        session['current_household_id'] = household.id

        flash(f'Household "{name}" created successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('household/setup.html')


@app.route('/household/select')
@login_required
def select_household():
    """Show household selection page."""
    households = current_user.household_memberships

    if not households:
        return redirect(url_for('create_household'))

    return render_template('household/select.html', households=households)


@app.route('/household/switch/<int:household_id>', methods=['POST'])
@login_required
def switch_household(household_id):
    """Switch to a different household."""
    # Verify user is a member of this household
    membership = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    if not membership:
        flash('You are not a member of this household.', 'danger')
        return redirect(url_for('select_household'))

    # Update session
    from flask import session
    session['current_household_id'] = household_id

    flash(f'Switched to {membership.household.name}', 'success')
    return redirect(url_for('index'))


@app.route('/household/settings', methods=['GET'])
@household_required
def household_settings():
    """View household settings."""
    household_id = get_current_household_id()
    household = get_current_household()

    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    # Get current user's membership
    current_member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    is_owner = current_member and current_member.role == 'owner'

    # Get pending invitations
    pending_invitations = Invitation.query.filter_by(
        household_id=household_id,
        status='pending'
    ).all()
    pending_invitations = [inv for inv in pending_invitations if inv.is_valid()]

    return render_template(
        'household/settings.html',
        household=household,
        members=members,
        current_member=current_member,
        is_owner=is_owner,
        member_count=len(members),
        pending_invitations=pending_invitations
    )


@app.route('/household/settings', methods=['POST'])
@household_required
def update_household():
    """Update household settings."""
    household_id = get_current_household_id()
    household = get_current_household()
    action = request.form.get('action')

    current_member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    is_owner = current_member and current_member.role == 'owner'

    if action == 'rename':
        if not is_owner:
            flash('Only the owner can rename the household.', 'danger')
            return redirect(url_for('household_settings'))

        new_name = request.form.get('name', '').strip()
        if new_name:
            household.name = new_name
            db.session.commit()
            flash('Household name updated.', 'success')

    elif action == 'update_display_name':
        new_display_name = request.form.get('display_name', '').strip()
        if new_display_name and current_member:
            current_member.display_name = new_display_name
            db.session.commit()
            flash('Your display name updated.', 'success')

    return redirect(url_for('household_settings'))


@app.route('/household/member/<int:member_id>/remove', methods=['POST'])
@household_required
def remove_member(member_id):
    """Remove a member from the household (owner only)."""
    household_id = get_current_household_id()

    # Verify current user is owner
    current_member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    if not current_member or current_member.role != 'owner':
        flash('Only the owner can remove members.', 'danger')
        return redirect(url_for('household_settings'))

    # Find member to remove
    member = HouseholdMember.query.filter_by(
        id=member_id,
        household_id=household_id
    ).first_or_404()

    # Cannot remove yourself
    if member.user_id == current_user.id:
        flash('You cannot remove yourself. Use "Leave Household" instead.', 'warning')
        return redirect(url_for('household_settings'))

    db.session.delete(member)
    db.session.commit()

    flash(f'{member.display_name} has been removed from the household.', 'success')
    return redirect(url_for('household_settings'))


@app.route('/household/leave', methods=['POST'])
@household_required
def leave_household():
    """Leave the current household."""
    household_id = get_current_household_id()
    household = get_current_household()

    # Find current user's membership
    member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    if not member:
        flash('You are not a member of this household.', 'danger')
        return redirect(url_for('index'))

    # Count remaining members
    member_count = HouseholdMember.query.filter_by(household_id=household_id).count()

    if member_count == 1:
        # Last member - delete household and all data
        household_name = household.name
        db.session.delete(household)  # CASCADE deletes members, transactions, settlements
        db.session.commit()
        flash(f'Household "{household_name}" has been deleted.', 'info')
    else:
        # Just remove membership
        db.session.delete(member)
        db.session.commit()
        flash(f'You have left {household.name}.', 'info')

    # Clear session
    from flask import session
    session.pop('current_household_id', None)

    # Check if user has other households
    if current_user.household_memberships:
        return redirect(url_for('select_household'))
    else:
        return redirect(url_for('create_household'))


# ============================================================================
# Expense Types API Routes
# ============================================================================

@app.route('/api/expense-types', methods=['GET'])
@household_required
def get_expense_types():
    """Get all expense types for the current household."""
    household_id = get_current_household_id()

    expense_types = ExpenseType.query.filter_by(
        household_id=household_id,
        is_active=True
    ).order_by(ExpenseType.name).all()

    return jsonify({
        'success': True,
        'expense_types': [et.to_dict() for et in expense_types]
    })


@app.route('/api/expense-types', methods=['POST'])
@household_required
def create_expense_type():
    """Create a new expense type."""
    try:
        household_id = get_current_household_id()
        data = request.json

        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required.'}), 400

        # Check for duplicate name
        existing = ExpenseType.query.filter_by(
            household_id=household_id,
            name=name
        ).first()

        if existing:
            if existing.is_active:
                return jsonify({'success': False, 'error': 'An expense type with this name already exists.'}), 400
            else:
                # Reactivate existing expense type
                existing.is_active = True
                existing.icon = data.get('icon')
                existing.color = data.get('color')
                db.session.commit()
                return jsonify({'success': True, 'expense_type': existing.to_dict()})

        expense_type = ExpenseType(
            household_id=household_id,
            name=name,
            icon=data.get('icon'),
            color=data.get('color')
        )

        db.session.add(expense_type)
        db.session.commit()

        return jsonify({'success': True, 'expense_type': expense_type.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/expense-types/<int:expense_type_id>', methods=['PUT'])
@household_required
def update_expense_type(expense_type_id):
    """Update an expense type."""
    try:
        household_id = get_current_household_id()

        expense_type = ExpenseType.query.filter_by(
            id=expense_type_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'success': False, 'error': 'Name cannot be empty.'}), 400

            # Check for duplicate name
            existing = ExpenseType.query.filter(
                ExpenseType.household_id == household_id,
                ExpenseType.name == name,
                ExpenseType.id != expense_type_id
            ).first()

            if existing:
                return jsonify({'success': False, 'error': 'An expense type with this name already exists.'}), 400

            expense_type.name = name

        if 'icon' in data:
            expense_type.icon = data['icon']

        if 'color' in data:
            expense_type.color = data['color']

        db.session.commit()

        return jsonify({'success': True, 'expense_type': expense_type.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/expense-types/<int:expense_type_id>', methods=['DELETE'])
@household_required
def delete_expense_type(expense_type_id):
    """Deactivate an expense type (soft delete)."""
    try:
        household_id = get_current_household_id()

        expense_type = ExpenseType.query.filter_by(
            id=expense_type_id,
            household_id=household_id
        ).first_or_404()

        # Check if expense type is used in budget rules
        budget_usage = BudgetRuleExpenseType.query.filter_by(
            expense_type_id=expense_type_id
        ).join(BudgetRule).filter(
            BudgetRule.is_active.is_(True)
        ).first()

        if budget_usage:
            return jsonify({
                'success': False,
                'error': 'Cannot delete expense type that is used in active budget rules.'
            }), 400

        # Soft delete
        expense_type.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# Auto-Category Rules API Routes
# ============================================================================

@app.route('/api/auto-category-rules', methods=['GET'])
@household_required
def get_auto_category_rules():
    """Get all auto-category rules for the current household."""
    household_id = get_current_household_id()

    rules = AutoCategoryRule.query.filter_by(
        household_id=household_id
    ).order_by(AutoCategoryRule.priority.desc(), AutoCategoryRule.keyword).all()

    return jsonify({
        'success': True,
        'rules': [r.to_dict() for r in rules]
    })


@app.route('/api/auto-category-rules', methods=['POST'])
@household_required
def create_auto_category_rule():
    """Create a new auto-category rule."""
    try:
        household_id = get_current_household_id()
        data = request.json

        keyword = data.get('keyword', '').strip()
        expense_type_id = data.get('expense_type_id')

        if not keyword:
            return jsonify({'success': False, 'error': 'Keyword is required.'}), 400

        if not expense_type_id:
            return jsonify({'success': False, 'error': 'Expense type is required.'}), 400

        # Verify expense type belongs to household
        expense_type = ExpenseType.query.filter_by(
            id=expense_type_id,
            household_id=household_id,
            is_active=True
        ).first()

        if not expense_type:
            return jsonify({'success': False, 'error': 'Invalid expense type.'}), 400

        rule = AutoCategoryRule(
            household_id=household_id,
            keyword=keyword,
            expense_type_id=expense_type_id,
            priority=data.get('priority', 0)
        )

        db.session.add(rule)
        db.session.commit()

        return jsonify({'success': True, 'rule': rule.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/auto-category-rules/<int:rule_id>', methods=['PUT'])
@household_required
def update_auto_category_rule(rule_id):
    """Update an auto-category rule."""
    try:
        household_id = get_current_household_id()

        rule = AutoCategoryRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        if 'keyword' in data:
            keyword = data['keyword'].strip()
            if not keyword:
                return jsonify({'success': False, 'error': 'Keyword cannot be empty.'}), 400
            rule.keyword = keyword

        if 'expense_type_id' in data:
            expense_type = ExpenseType.query.filter_by(
                id=data['expense_type_id'],
                household_id=household_id,
                is_active=True
            ).first()

            if not expense_type:
                return jsonify({'success': False, 'error': 'Invalid expense type.'}), 400

            rule.expense_type_id = data['expense_type_id']

        if 'priority' in data:
            rule.priority = data['priority']

        db.session.commit()

        return jsonify({'success': True, 'rule': rule.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/auto-category-rules/<int:rule_id>', methods=['DELETE'])
@household_required
def delete_auto_category_rule(rule_id):
    """Delete an auto-category rule."""
    try:
        household_id = get_current_household_id()

        rule = AutoCategoryRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        db.session.delete(rule)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/auto-categorize', methods=['POST'])
@household_required
def auto_categorize():
    """Get suggested expense type for a merchant name."""
    household_id = get_current_household_id()
    data = request.json

    merchant = data.get('merchant', '').strip().lower()

    if not merchant:
        return jsonify({'success': True, 'expense_type': None})

    # Find matching rule (highest priority first)
    rules = AutoCategoryRule.query.filter_by(
        household_id=household_id
    ).order_by(AutoCategoryRule.priority.desc()).all()

    for rule in rules:
        if rule.keyword.lower() in merchant:
            return jsonify({
                'success': True,
                'expense_type': rule.expense_type.to_dict() if rule.expense_type else None,
                'matched_rule': rule.to_dict()
            })

    return jsonify({'success': True, 'expense_type': None})


# ============================================================================
# Budget Rules API Routes
# ============================================================================

@app.route('/api/budget-rules', methods=['GET'])
@household_required
def get_budget_rules():
    """Get all budget rules for the current household."""
    household_id = get_current_household_id()

    rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    return jsonify({
        'success': True,
        'rules': [r.to_dict() for r in rules]
    })


@app.route('/api/budget-rules', methods=['POST'])
@household_required
def create_budget_rule():
    """Create a new budget rule."""
    try:
        household_id = get_current_household_id()
        data = request.json

        giver_user_id = data.get('giver_user_id')
        receiver_user_id = data.get('receiver_user_id')
        monthly_amount = data.get('monthly_amount')
        expense_type_ids = data.get('expense_type_ids', [])

        # Validation
        if not giver_user_id or not receiver_user_id:
            return jsonify({'success': False, 'error': 'Giver and receiver are required.'}), 400

        if giver_user_id == receiver_user_id:
            return jsonify({'success': False, 'error': 'Giver and receiver must be different.'}), 400

        if not monthly_amount or float(monthly_amount) <= 0:
            return jsonify({'success': False, 'error': 'Monthly amount must be positive.'}), 400

        if not expense_type_ids:
            return jsonify({'success': False, 'error': 'At least one expense type is required.'}), 400

        # Verify both users are members of household
        for user_id in [giver_user_id, receiver_user_id]:
            member = HouseholdMember.query.filter_by(
                household_id=household_id,
                user_id=user_id
            ).first()
            if not member:
                return jsonify({'success': False, 'error': 'Invalid user selected.'}), 400

        # Check if expense types are already used in other active budget rules
        for et_id in expense_type_ids:
            existing_usage = BudgetRuleExpenseType.query.filter_by(
                expense_type_id=et_id
            ).join(BudgetRule).filter(
                BudgetRule.household_id == household_id,
                BudgetRule.is_active.is_(True)
            ).first()

            if existing_usage:
                expense_type = ExpenseType.query.get(et_id)
                return jsonify({
                    'success': False,
                    'error': f'Expense type "{expense_type.name}" is already used in another budget rule.'
                }), 400

        # Create budget rule
        budget_rule = BudgetRule(
            household_id=household_id,
            giver_user_id=giver_user_id,
            receiver_user_id=receiver_user_id,
            monthly_amount=Decimal(str(monthly_amount))
        )

        db.session.add(budget_rule)
        db.session.flush()  # Get the ID

        # Add expense type associations
        for et_id in expense_type_ids:
            assoc = BudgetRuleExpenseType(
                budget_rule_id=budget_rule.id,
                expense_type_id=et_id
            )
            db.session.add(assoc)

        db.session.commit()

        return jsonify({'success': True, 'rule': budget_rule.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/budget-rules/<int:rule_id>', methods=['PUT'])
@household_required
def update_budget_rule(rule_id):
    """Update a budget rule."""
    try:
        household_id = get_current_household_id()

        budget_rule = BudgetRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        if 'monthly_amount' in data:
            amount = float(data['monthly_amount'])
            if amount <= 0:
                return jsonify({'success': False, 'error': 'Monthly amount must be positive.'}), 400
            budget_rule.monthly_amount = Decimal(str(amount))

        if 'expense_type_ids' in data:
            expense_type_ids = data['expense_type_ids']

            if not expense_type_ids:
                return jsonify({'success': False, 'error': 'At least one expense type is required.'}), 400

            # Check for conflicts with other budget rules
            for et_id in expense_type_ids:
                existing_usage = BudgetRuleExpenseType.query.filter_by(
                    expense_type_id=et_id
                ).join(BudgetRule).filter(
                    BudgetRule.household_id == household_id,
                    BudgetRule.is_active.is_(True),
                    BudgetRule.id != rule_id
                ).first()

                if existing_usage:
                    expense_type = ExpenseType.query.get(et_id)
                    return jsonify({
                        'success': False,
                        'error': f'Expense type "{expense_type.name}" is already used in another budget rule.'
                    }), 400

            # Remove existing associations
            BudgetRuleExpenseType.query.filter_by(budget_rule_id=rule_id).delete()

            # Add new associations
            for et_id in expense_type_ids:
                assoc = BudgetRuleExpenseType(
                    budget_rule_id=rule_id,
                    expense_type_id=et_id
                )
                db.session.add(assoc)

        db.session.commit()

        return jsonify({'success': True, 'rule': budget_rule.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/budget-rules/<int:rule_id>', methods=['DELETE'])
@household_required
def delete_budget_rule(rule_id):
    """Deactivate a budget rule (soft delete)."""
    try:
        household_id = get_current_household_id()

        budget_rule = BudgetRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        budget_rule.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# Split Rules API Routes
# ============================================================================

@app.route('/api/split-rules', methods=['GET'])
@household_required
def get_split_rules():
    """Get all split rules for the current household."""
    household_id = get_current_household_id()
    household_members = get_current_household_members()

    rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    return jsonify({
        'success': True,
        'rules': [r.to_dict(household_members) for r in rules]
    })


@app.route('/api/split-rules', methods=['POST'])
@household_required
def create_split_rule():
    """Create a new split rule."""
    try:
        household_id = get_current_household_id()
        household_members = get_current_household_members()
        data = request.json

        member1_percent = int(data.get('member1_percent', 50))
        member2_percent = int(data.get('member2_percent', 50))
        is_default = bool(data.get('is_default', False))
        expense_type_ids = data.get('expense_type_ids', [])

        # Validation
        if member1_percent + member2_percent != 100:
            return jsonify({'success': False, 'error': 'Percentages must sum to 100.'}), 400

        if member1_percent < 0 or member2_percent < 0:
            return jsonify({'success': False, 'error': 'Percentages cannot be negative.'}), 400

        # If it's a default rule, check no other default exists
        if is_default:
            existing_default = SplitRule.query.filter_by(
                household_id=household_id,
                is_default=True,
                is_active=True
            ).first()
            if existing_default:
                return jsonify({'success': False, 'error': 'A default split rule already exists.'}), 400
        else:
            # Non-default rules require expense types
            if not expense_type_ids:
                return jsonify({'success': False, 'error': 'Select at least one expense category, or mark as default.'}), 400

        # Create the rule
        rule = SplitRule(
            household_id=household_id,
            member1_percent=member1_percent,
            member2_percent=member2_percent,
            is_default=is_default
        )
        db.session.add(rule)
        db.session.flush()  # Get the ID

        # Handle expense type associations
        # Auto-remove from other rules if already assigned (per design spec)
        for et_id in expense_type_ids:
            # Remove from other rules
            SplitRuleExpenseType.query.filter_by(
                expense_type_id=et_id
            ).filter(
                SplitRuleExpenseType.split_rule_id != rule.id
            ).delete(synchronize_session='fetch')

            # Add to this rule
            assoc = SplitRuleExpenseType(
                split_rule_id=rule.id,
                expense_type_id=et_id
            )
            db.session.add(assoc)

        db.session.commit()

        # Auto-delete any rules that are now empty (no expense types and not default)
        _cleanup_empty_split_rules(household_id, exclude_rule_id=rule.id)

        return jsonify({'success': True, 'rule': rule.to_dict(household_members)})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/split-rules/<int:rule_id>', methods=['PUT'])
@household_required
def update_split_rule(rule_id):
    """Update a split rule."""
    try:
        household_id = get_current_household_id()
        household_members = get_current_household_members()

        split_rule = SplitRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        # Update percentages
        if 'member1_percent' in data and 'member2_percent' in data:
            member1_percent = int(data['member1_percent'])
            member2_percent = int(data['member2_percent'])

            if member1_percent + member2_percent != 100:
                return jsonify({'success': False, 'error': 'Percentages must sum to 100.'}), 400

            if member1_percent < 0 or member2_percent < 0:
                return jsonify({'success': False, 'error': 'Percentages cannot be negative.'}), 400

            split_rule.member1_percent = member1_percent
            split_rule.member2_percent = member2_percent

        # Update expense types
        if 'expense_type_ids' in data:
            expense_type_ids = data['expense_type_ids']

            # Non-default rules need at least one expense type
            if not split_rule.is_default and not expense_type_ids:
                return jsonify({'success': False, 'error': 'Non-default rules require at least one expense category.'}), 400

            # Remove existing associations for this rule
            SplitRuleExpenseType.query.filter_by(split_rule_id=rule_id).delete()

            # Add new associations, removing from other rules
            for et_id in expense_type_ids:
                # Remove from other rules
                SplitRuleExpenseType.query.filter_by(
                    expense_type_id=et_id
                ).filter(
                    SplitRuleExpenseType.split_rule_id != rule_id
                ).delete(synchronize_session='fetch')

                # Add to this rule
                assoc = SplitRuleExpenseType(
                    split_rule_id=rule_id,
                    expense_type_id=et_id
                )
                db.session.add(assoc)

        db.session.commit()

        # Auto-delete any rules that are now empty
        _cleanup_empty_split_rules(household_id, exclude_rule_id=rule_id)

        return jsonify({'success': True, 'rule': split_rule.to_dict(household_members)})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/split-rules/<int:rule_id>', methods=['DELETE'])
@household_required
def delete_split_rule(rule_id):
    """Deactivate a split rule (soft delete)."""
    try:
        household_id = get_current_household_id()

        split_rule = SplitRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        split_rule.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


def _cleanup_empty_split_rules(household_id, exclude_rule_id=None):
    """Delete split rules that have no expense types and are not default."""
    rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_active=True,
        is_default=False
    ).all()

    for rule in rules:
        if rule.id == exclude_rule_id:
            continue
        # Check if rule has any expense types
        if not rule.expense_types:
            rule.is_active = False

    db.session.commit()


# ============================================================================
# Budget Page Routes
# ============================================================================

@app.route('/budget')
@app.route('/budget/<month>')
@household_required
def budget_page(month=None):
    """Budget tracking page."""
    household_id = get_current_household_id()

    # Get month from URL or default to current month
    if not month:
        month = datetime.now().strftime('%Y-%m')

    # Get available months (same as index page)
    existing_months = db.session.query(Transaction.month_year).distinct().filter(
        Transaction.household_id == household_id
    ).order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in existing_months]

    # Ensure current month is in list
    current_month_str = datetime.now().strftime('%Y-%m')
    if current_month_str not in months:
        months.insert(0, current_month_str)

    if month not in months:
        months.append(month)
        months.sort(reverse=True)

    # Get all transactions for the month
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).all()

    # Get budget rules
    budget_rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    # Calculate status for each budget rule
    budget_data = []
    current_year = month.split('-')[0]

    for rule in budget_rules:
        status = calculate_budget_status(rule, month, transactions)
        yearly_cumulative = get_yearly_cumulative(rule.id, current_year)

        budget_data.append({
            'rule': rule,
            'giver_name': rule.get_giver_display_name(),
            'giver_user_id': rule.giver_user_id,
            'receiver_name': rule.get_receiver_display_name(),
            'receiver_user_id': rule.receiver_user_id,
            'monthly_amount': rule.monthly_amount,
            'expense_type_names': rule.get_expense_type_names(),
            'status': status,
            'yearly_cumulative': yearly_cumulative,
        })

    return render_template(
        'budget/index.html',
        current_month=month,
        months=months,
        budget_rules=budget_rules,
        budget_data=budget_data,
        current_year=current_year
    )


@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized!')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Get port from environment variable (Render provides this)
    # Default to 5001 for local development (avoids macOS AirPlay Receiver conflict)
    port = int(os.environ.get('PORT', 5001))

    # Allow disabling auto-reload for stable testing (NO_RELOAD=1 python app.py)
    use_reloader = os.environ.get('NO_RELOAD') != '1'

    # Debug mode is set by config (True for development, False for production)
    app.run(debug=app.debug, host='0.0.0.0', port=port, use_reloader=use_reloader)
