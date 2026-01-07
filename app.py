"""
Main Flask application for household expense tracker.
"""
import os
import csv
from io import StringIO
from flask import Flask, render_template, request, jsonify, Response, flash, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta
from decimal import Decimal

from models import db, Transaction, Settlement, User, Household, HouseholdMember
from utils import get_exchange_rate, calculate_reconciliation
from auth import login_manager
from decorators import household_required
from household_context import (
    get_current_household_id,
    get_current_household,
    get_current_household_members
)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Use different database path for production (persistent disk) vs development
if os.environ.get('FLASK_ENV') == 'production':
    # Production: use /data directory which is mounted to persistent disk on Render
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/database.db'
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


# Initialize database tables when app starts (for production with Gunicorn)
def init_db():
    """Create database tables if they don't exist."""
    with app.app_context():
        db.create_all()
        print('Database tables created (if not already existing)')


# Call initialization when module is loaded
init_db()


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
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
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        # Check if account is active
        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'danger')
            return render_template('auth/login.html')

        # Login user
        login_user(user, remember=remember)

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

    app.run(debug=debug_mode, host='0.0.0.0', port=port)
