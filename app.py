"""
Main Flask application for household expense tracker.
"""
import os
import logging
from flask import Flask, request, redirect

from extensions import db, csrf, limiter, login_manager, migrate
from household_context import get_current_household
from email_service import init_mail
from config import config, get_config_name
from blueprints.auth import auth_bp
from blueprints.profile import profile_bp
from blueprints.household import household_bp
from blueprints.transactions import transactions_bp
from blueprints.invitations import invitations_bp
from blueprints.reconciliation import reconciliation_bp
from blueprints.budget import budget_bp
from blueprints.api import api_bp
from blueprints.api_v1 import api_v1_bp

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
migrate.init_app(app, db)  # Flask-Migrate for database migrations
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
app.register_blueprint(api_v1_bp)

# Exempt API v1 routes from CSRF (they use JWT authentication)
csrf.exempt(api_v1_bp)


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
    """Create database tables if they don't exist.

    Note: Schema migrations are now handled by Flask-Migrate.
    Use 'flask db migrate' and 'flask db upgrade' for schema changes.
    """
    from sqlalchemy import text

    with app.app_context():
        db.create_all()
        print('Database tables created (if not already existing)')

        # Auto-migration: Add receipt_url column to transactions if missing
        try:
            db.session.execute(text(
                'ALTER TABLE transactions ADD COLUMN receipt_url VARCHAR(500)'
            ))
            db.session.commit()
            print('Added receipt_url column to transactions table')
        except Exception as e:
            db.session.rollback()
            if 'duplicate column' in str(e).lower():
                print('Column receipt_url already exists - skipping')
            else:
                # Column might already exist, which is fine
                print(f'Note: receipt_url migration skipped ({e})')

        # Auto-migration: Add category column to auto_category_rules if missing
        try:
            db.session.execute(text(
                'ALTER TABLE auto_category_rules ADD COLUMN category VARCHAR(20)'
            ))
            db.session.commit()
            print('Added category column to auto_category_rules table')
        except Exception as e:
            db.session.rollback()
            if 'duplicate column' in str(e).lower():
                print('Column category already exists - skipping')
            else:
                print(f'Note: category migration skipped ({e})')

        # Verify schema completeness - warn if any columns are missing
        verify_schema_completeness()


def verify_schema_completeness():
    """Check all model columns exist in database, log warnings for any missing.

    This runs at app startup to detect schema drift between code and database.
    If warnings appear, add ALTER TABLE migrations to init_db() above.
    """
    from sqlalchemy import inspect
    from models import (
        User, Household, HouseholdMember, Transaction, Settlement,
        Invitation, ExpenseType, AutoCategoryRule, BudgetRule,
        BudgetRuleExpenseType, BudgetSnapshot, SplitRule,
        SplitRuleExpenseType, RefreshToken, DeviceToken
    )

    all_models = [
        User, Household, HouseholdMember, Transaction, Settlement,
        Invitation, ExpenseType, AutoCategoryRule, BudgetRule,
        BudgetRuleExpenseType, BudgetSnapshot, SplitRule,
        SplitRuleExpenseType, RefreshToken, DeviceToken
    ]

    try:
        inspector = inspect(db.engine)
        issues_found = False

        for model in all_models:
            table_name = model.__tablename__
            try:
                db_columns = {col['name'] for col in inspector.get_columns(table_name)}
                model_columns = {col.name for col in model.__table__.columns}
                missing = model_columns - db_columns

                if missing:
                    issues_found = True
                    print(f'WARNING: Table "{table_name}" missing columns: {sorted(missing)}')
                    print('  -> Add ALTER TABLE migration to init_db() in app.py')
            except Exception as e:
                print(f'Note: Could not verify table "{table_name}": {e}')

        if not issues_found:
            print('Schema verification passed - all model columns exist in database')
    except Exception as e:
        print(f'Note: Schema verification skipped: {e}')


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
