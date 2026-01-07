"""
Main Flask application for household expense tracker.
"""
import os
import csv
import logging
from io import StringIO
from flask import Flask, render_template, request, jsonify, Response, flash, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from flask_login import login_user, logout_user, current_user, login_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
from decimal import Decimal

from models import db, Transaction, Settlement, User, Household, HouseholdMember, Invitation
from utils import get_exchange_rate, calculate_reconciliation
from auth import login_manager
from decorators import household_required
from household_context import (
    get_current_household_id,
    get_current_household,
    get_current_household_members
)
from email_service import init_mail, send_invitation_email, is_mail_configured
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Use different database path for production (persistent disk) vs development
if os.environ.get('FLASK_ENV') == 'production':
    # Production: use /data directory which is mounted to persistent disk on Render
    # Note: 4 slashes = sqlite:// + absolute path /data/database.db
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////data/database.db'
else:
    # Development: use instance folder locally
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session security configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Only enable SECURE cookies in production (requires HTTPS)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize extensions
db.init_app(app)
csrf = CSRFProtect(app)
login_manager.init_app(app)
init_mail(app)  # Initialize Flask-Mail for invitations

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


# ============================================================================
# Security Middleware
# ============================================================================

@app.before_request
def enforce_https():
    """Redirect HTTP to HTTPS in production."""
    if os.environ.get('FLASK_ENV') == 'production':
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

    # Content Security Policy (relaxed for CDN resources)
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self';"
        )

    # Strict Transport Security (HTTPS only in production)
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response


# Initialize database tables when app starts (for production with Gunicorn)
def init_db():
    """Create database tables if they don't exist."""
    with app.app_context():
        db.create_all()
        print('Database tables created (if not already existing)')


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
            print(f"[DEBUG] Validation failed: missing fields")
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
            print(f"[DEBUG] Attempting to save user to database...")
            db.session.add(user)
            db.session.commit()
            print(f"[DEBUG] User saved successfully!")

            # Auto-login after registration
            login_user(user, remember=True)
            print(f"[DEBUG] User logged in successfully!")

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
    ).order_by(Transaction.date.desc()).all()

    # Calculate quick summary
    summary = calculate_reconciliation(transactions, household_members) if transactions else None

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

    return render_template(
        'index.html',
        transactions=transactions,
        current_month=month,
        months=months,
        summary=summary,
        is_settled=is_settled,
        household_members=household_members
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

        # Calculate reconciliation with household members
        summary = calculate_reconciliation(transactions, household_members)

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

    # Calculate reconciliation with household members
    summary = calculate_reconciliation(transactions, household_members)

    # Get list of available months (FILTERED BY HOUSEHOLD)
    all_months = db.session.query(Transaction.month_year).distinct().filter(
        Transaction.household_id == household_id
    ).order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in all_months]

    # Check if month is settled (HOUSEHOLD-SCOPED)
    settlement = Settlement.get_settlement(household_id, month)

    return render_template(
        'reconciliation.html',
        summary=summary,
        month=month,
        months=months,
        transactions=transactions,
        settlement=settlement,
        household_members=household_members
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
            Transaction.get_category_display_name(txn.category),
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
        display_name = request.form.get('display_name', '').strip()

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

    # Disable debug mode in production for security
    debug_mode = os.environ.get('FLASK_ENV') != 'production'

    # Allow disabling auto-reload for stable testing (NO_RELOAD=1 python app.py)
    use_reloader = os.environ.get('NO_RELOAD') != '1'

    app.run(debug=debug_mode, host='0.0.0.0', port=port, use_reloader=use_reloader)
