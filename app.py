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
from blueprints.auth import auth_bp
from blueprints.profile import profile_bp
from blueprints.household import household_bp
from blueprints.transactions import transactions_bp
from blueprints.invitations import invitations_bp
from blueprints.reconciliation import reconciliation_bp
from blueprints.budget import budget_bp
from blueprints.api import api_bp
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

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(household_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(invitations_bp)
app.register_blueprint(reconciliation_bp)
app.register_blueprint(budget_bp)
app.register_blueprint(api_bp)


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
