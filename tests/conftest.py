"""
Shared pytest fixtures for household expense tracker tests.
"""
import pytest
import os
import sys
from datetime import date
from decimal import Decimal

from playwright.sync_api import sync_playwright

# Add project root and tests directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tests_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, tests_dir)

# ============================================================================
# Configuration
# ============================================================================

BASE_URL = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:5001')
HEADLESS = os.environ.get('HEADED', '').lower() not in ('1', 'true', 'yes')

# Centralized test user credentials
TEST_USERS = {
    'alice': {
        'email': 'test_alice@example.com',
        'password': 'TestPass123!',
        'name': 'Alice Smith',
        'display_name': 'Alice'
    },
    'bob': {
        'email': 'test_bob@example.com',
        'password': 'TestPass123!',
        'name': 'Bob Johnson',
        'display_name': 'Bob'
    },
    'charlie': {
        'email': 'test_charlie@example.com',
        'password': 'TestPass123!',
        'name': 'Charlie Davis',
        'display_name': 'Charlie'
    },
    'diana': {
        'email': 'test_diana@example.com',
        'password': 'TestPass123!',
        'name': 'Diana Lee',
        'display_name': 'Diana'
    }
}


# ============================================================================
# Flask App Fixtures (for unit tests)
# ============================================================================

@pytest.fixture(scope='session')
def app():
    """Create Flask app for testing."""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for API tests
    return flask_app


@pytest.fixture(scope='session')
def db(app):
    """Get database instance."""
    from extensions import db as _db
    with app.app_context():
        _db.create_all()
    return _db


@pytest.fixture
def app_context(app):
    """Provide app context for database operations."""
    with app.app_context():
        yield


@pytest.fixture
def clean_test_data(app, db):
    """Clean up test data before and after each test."""
    from models import User

    def _cleanup():
        with app.app_context():
            # Delete test users by email pattern
            for user_key in TEST_USERS:
                user = User.query.filter_by(email=TEST_USERS[user_key]['email']).first()
                if user:
                    # Get households where user is the only member
                    for membership in user.household_memberships:
                        household = membership.household
                        if len(household.members) == 1:
                            db.session.delete(household)
                    db.session.delete(user)

            # Also clean up any test_ prefixed emails
            test_users = User.query.filter(User.email.like('test_%@example.com')).all()
            for user in test_users:
                for membership in user.household_memberships:
                    if len(membership.household.members) == 1:
                        db.session.delete(membership.household)
                db.session.delete(user)

            db.session.commit()

    # Clean before test
    _cleanup()

    yield

    # Clean after test
    _cleanup()


# ============================================================================
# Browser Fixtures (for E2E tests)
# ============================================================================

@pytest.fixture(scope='function')
def page():
    """Create a fresh browser, context, and page for each test."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        yield page
        # Cleanup in reverse order, ignoring errors if already closed
        try:
            page.close()
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass


@pytest.fixture
def browser():
    """Standalone browser fixture for tests that need direct access."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        yield browser
        browser.close()


@pytest.fixture
def context(browser):
    """Create new browser context."""
    context = browser.new_context()
    yield context
    context.close()


# ============================================================================
# Authentication Helper Fixtures
# ============================================================================

@pytest.fixture
def register_user(page, clean_test_data):
    """Factory fixture to register a test user via UI."""
    registered = []

    def _register(user_key: str):
        user_data = TEST_USERS[user_key]
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="name"]', user_data['name'])
        page.fill('input[name="email"]', user_data['email'])
        page.fill('input[name="password"]', user_data['password'])
        page.fill('input[name="confirm_password"]', user_data['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        registered.append(user_key)
        return user_data

    return _register


@pytest.fixture
def login_as(page):
    """Factory fixture to login as a specific test user."""
    def _login(user_key: str):
        user_data = TEST_USERS[user_key]
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="email"]', user_data['email'])
        page.fill('input[name="password"]', user_data['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        return user_data

    return _login


@pytest.fixture
def logout(page):
    """Logout current user."""
    def _logout():
        page.goto(f"{BASE_URL}/logout")
        page.wait_for_load_state('networkidle')

    return _logout


# ============================================================================
# Household Helper Fixtures
# ============================================================================

@pytest.fixture
def create_household(page):
    """Factory fixture to create a household via UI."""
    def _create(name: str, display_name: str = None):
        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="name"]', name)
        # display_name is required, fill it if provided or use default
        display_input = page.locator('input[name="display_name"]')
        if display_input.count() > 0:
            if display_name:
                display_input.fill(display_name)
            # If no display_name provided, the form may have user's name prefilled
            # Just clear and set a default if empty
            elif not display_input.input_value():
                display_input.fill('Test User')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        return name

    return _create


@pytest.fixture
def setup_two_households(app, db, clean_test_data):
    """Set up two isolated households with users and transactions (database fixture)."""
    from models import User, Household, HouseholdMember, Transaction

    with app.app_context():
        # Create Alice
        alice = User(email=TEST_USERS['alice']['email'], name=TEST_USERS['alice']['name'])
        alice.set_password(TEST_USERS['alice']['password'])
        db.session.add(alice)

        # Create Bob
        bob = User(email=TEST_USERS['bob']['email'], name=TEST_USERS['bob']['name'])
        bob.set_password(TEST_USERS['bob']['password'])
        db.session.add(bob)

        # Create Charlie
        charlie = User(email=TEST_USERS['charlie']['email'], name=TEST_USERS['charlie']['name'])
        charlie.set_password(TEST_USERS['charlie']['password'])
        db.session.add(charlie)

        # Create Diana
        diana = User(email=TEST_USERS['diana']['email'], name=TEST_USERS['diana']['name'])
        diana.set_password(TEST_USERS['diana']['password'])
        db.session.add(diana)

        db.session.flush()

        # Household 1: Alice & Bob
        h1 = Household(name='Alice & Bob Household', created_by_user_id=alice.id)
        db.session.add(h1)
        db.session.flush()

        db.session.add(HouseholdMember(
            household_id=h1.id, user_id=alice.id, role='owner', display_name='Alice'
        ))
        db.session.add(HouseholdMember(
            household_id=h1.id, user_id=bob.id, role='member', display_name='Bob'
        ))

        # Household 2: Charlie & Diana
        h2 = Household(name='Charlie & Diana Household', created_by_user_id=charlie.id)
        db.session.add(h2)
        db.session.flush()

        db.session.add(HouseholdMember(
            household_id=h2.id, user_id=charlie.id, role='owner', display_name='Charlie'
        ))
        db.session.add(HouseholdMember(
            household_id=h2.id, user_id=diana.id, role='member', display_name='Diana'
        ))

        # Add transactions to Household 1
        month = date.today().strftime('%Y-%m')
        db.session.add(Transaction(
            household_id=h1.id, date=date.today(), merchant='Grocery Store',
            amount=Decimal('150.00'), currency='USD', amount_in_usd=Decimal('150.00'),
            paid_by_user_id=alice.id, category='SHARED', notes='Weekly groceries',
            month_year=month
        ))
        db.session.add(Transaction(
            household_id=h1.id, date=date.today(), merchant='Restaurant',
            amount=Decimal('80.00'), currency='USD', amount_in_usd=Decimal('80.00'),
            paid_by_user_id=bob.id, category='SHARED', notes='Dinner out',
            month_year=month
        ))

        # Add transactions to Household 2
        db.session.add(Transaction(
            household_id=h2.id, date=date.today(), merchant='Electronics Store',
            amount=Decimal('500.00'), currency='USD', amount_in_usd=Decimal('500.00'),
            paid_by_user_id=charlie.id, category='SHARED', notes='New laptop',
            month_year=month
        ))
        db.session.add(Transaction(
            household_id=h2.id, date=date.today(), merchant='Gas Station',
            amount=Decimal('60.00'), currency='USD', amount_in_usd=Decimal('60.00'),
            paid_by_user_id=diana.id, category='SHARED', notes='Fill up car',
            month_year=month
        ))

        db.session.commit()

        # Re-query to get IDs after commit
        alice = User.query.filter_by(email=TEST_USERS['alice']['email']).first()
        bob = User.query.filter_by(email=TEST_USERS['bob']['email']).first()
        charlie = User.query.filter_by(email=TEST_USERS['charlie']['email']).first()
        diana = User.query.filter_by(email=TEST_USERS['diana']['email']).first()
        h1 = Household.query.filter_by(name='Alice & Bob Household').first()
        h2 = Household.query.filter_by(name='Charlie & Diana Household').first()

        return {
            'household1_id': h1.id,
            'household2_id': h2.id,
            'alice_id': alice.id,
            'bob_id': bob.id,
            'charlie_id': charlie.id,
            'diana_id': diana.id
        }


# ============================================================================
# Transaction Helper Fixtures
# ============================================================================

@pytest.fixture
def add_transaction(page):
    """Factory fixture to add a transaction via UI."""
    def _add(merchant: str, amount: str, currency: str = 'USD',
             category: str = 'SHARED', notes: str = '', date_str: str = None):
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        # Fill date (default to today)
        if date_str:
            page.fill('input[name="date"]', date_str)

        page.fill('input[name="merchant"]', merchant)
        page.fill('input[name="amount"]', amount)
        page.select_option('select[name="currency"]', currency)
        page.select_option('select[name="category"]', category)

        if notes:
            notes_input = page.locator('input[name="notes"], textarea[name="notes"]')
            if notes_input.count() > 0:
                notes_input.first.fill(notes)

        page.click('button:has-text("Add Transaction")')
        page.wait_for_load_state('networkidle')

        return merchant

    return _add


# ============================================================================
# Utility Functions (for use in tests)
# ============================================================================

def get_csrf_token(page):
    """Extract CSRF token from page."""
    csrf_input = page.locator('input[name="csrf_token"]')
    if csrf_input.count() > 0:
        return csrf_input.first.get_attribute('value')

    # Try meta tag
    csrf_meta = page.locator('meta[name="csrf-token"]')
    if csrf_meta.count() > 0:
        return csrf_meta.first.get_attribute('content')

    return None


def wait_for_toast(page, text: str = None, timeout: int = 5000):
    """Wait for toast notification to appear."""
    toast = page.locator('[class*="toast"], [class*="notification"], [role="alert"]')
    toast.wait_for(timeout=timeout)
    if text:
        assert text.lower() in toast.text_content().lower()
    return toast


def confirm_dialog(page):
    """Handle custom confirmation dialog."""
    # Look for custom confirm modal
    confirm_btn = page.locator('button:has-text("Confirm"), button:has-text("Yes"), button:has-text("OK")')
    if confirm_btn.count() > 0:
        confirm_btn.first.click()
        page.wait_for_load_state('networkidle')
