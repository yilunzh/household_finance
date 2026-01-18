"""
Tests for user profile functionality.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal


@pytest.mark.unit
class TestUserModelEmailFields:
    """Test the new email change fields on User model."""

    def test_user_has_email_change_columns(self, app, db):
        """Verify email change columns exist on users table."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]

        assert 'pending_email' in columns
        assert 'email_change_token' in columns
        assert 'email_change_expires' in columns

    def test_pending_email_can_be_set(self, app, db):
        """Test setting pending email on a user."""
        from models import User

        user = User(
            email='test@example.com',
            name='Test User'
        )
        user.set_password('password123')
        user.pending_email = 'new@example.com'
        user.email_change_token = 'abc123token'
        user.email_change_expires = datetime.utcnow() + timedelta(hours=1)

        db.session.add(user)
        db.session.commit()

        # Reload from database
        saved_user = User.query.filter_by(email='test@example.com').first()
        assert saved_user.pending_email == 'new@example.com'
        assert saved_user.email_change_token == 'abc123token'
        assert saved_user.email_change_expires is not None


@pytest.mark.unit
class TestTransactionAnonymization:
    """Test transaction anonymization for deleted users."""

    def test_transaction_paid_by_user_id_nullable(self, app, db):
        """Verify paid_by_user_id can be NULL (for anonymized transactions)."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = {col['name']: col for col in inspector.get_columns('transactions')}

        # paid_by_user_id should be nullable
        assert columns['paid_by_user_id']['nullable'] is True

    def test_get_paid_by_display_name_deleted_member(self, app, db):
        """Test that NULL paid_by_user_id returns 'Deleted Member'."""
        from models import User, Household, HouseholdMember, Transaction
        from datetime import date

        # Create user and household
        user = User(email='owner@test.com', name='Owner')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

        household = Household(name='Test Household', created_by_user_id=user.id)
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=user.id,
            role='owner',
            display_name='Owner'
        )
        db.session.add(member)
        db.session.flush()

        # Create transaction with NULL paid_by_user_id (simulating deleted user)
        transaction = Transaction(
            household_id=household.id,
            date=date.today(),
            merchant='Test Store',
            amount=Decimal('50.00'),
            currency='USD',
            amount_in_usd=Decimal('50.00'),
            paid_by_user_id=None,  # Anonymized
            category='SHARED',
            month_year=date.today().strftime('%Y-%m')
        )
        db.session.add(transaction)
        db.session.commit()

        # Verify display name returns "Deleted Member"
        assert transaction.get_paid_by_display_name() == 'Deleted Member'

    def test_get_paid_by_display_name_former_member(self, app, db):
        """Test that user with no membership returns 'Former Member'."""
        from models import User, Household, HouseholdMember, Transaction
        from datetime import date

        # Create two users and household
        owner = User(email='owner@test.com', name='Owner')
        owner.set_password('password123')
        former = User(email='former@test.com', name='Former')
        former.set_password('password123')
        db.session.add_all([owner, former])
        db.session.flush()

        household = Household(name='Test Household', created_by_user_id=owner.id)
        db.session.add(household)
        db.session.flush()

        # Only owner is a member (former left but transaction remains)
        owner_member = HouseholdMember(
            household_id=household.id,
            user_id=owner.id,
            role='owner',
            display_name='Owner'
        )
        db.session.add(owner_member)
        db.session.flush()

        # Create transaction paid by former member who is no longer in household
        transaction = Transaction(
            household_id=household.id,
            date=date.today(),
            merchant='Test Store',
            amount=Decimal('50.00'),
            currency='USD',
            amount_in_usd=Decimal('50.00'),
            paid_by_user_id=former.id,  # User exists but not a member
            category='SHARED',
            month_year=date.today().strftime('%Y-%m')
        )
        db.session.add(transaction)
        db.session.commit()

        # Verify display name returns "Former Member"
        assert transaction.get_paid_by_display_name() == 'Former Member'


@pytest.mark.unit
class TestCalculateUserStats:
    """Test the calculate_user_stats utility function."""

    def test_stats_with_no_households(self, app, db):
        """User with no households returns empty stats."""
        from models import User
        from utils import calculate_user_stats

        user = User(email='solo@test.com', name='Solo User')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        stats = calculate_user_stats(user.id)

        assert stats['ytd_total_paid'] == 0
        assert stats['monthly_average'] == 0
        assert stats['total_owed_to_user'] == 0
        assert stats['total_owed_by_user'] == 0
        assert stats['household_breakdown'] == []
        assert stats['monthly_trend'] == []

    def test_stats_with_transactions(self, app, db):
        """User stats calculation with transactions."""
        from models import User, Household, HouseholdMember, Transaction
        from utils import calculate_user_stats
        from datetime import date

        # Create user and household
        user = User(email='test@test.com', name='Test User')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

        household = Household(name='Test Household', created_by_user_id=user.id)
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=user.id,
            role='owner',
            display_name='Test'
        )
        db.session.add(member)
        db.session.flush()

        # Create current year transaction
        current_year = datetime.utcnow().year
        current_month = date.today().strftime('%Y-%m')

        transaction = Transaction(
            household_id=household.id,
            date=date.today(),
            merchant='Test Store',
            amount=Decimal('100.00'),
            currency='USD',
            amount_in_usd=Decimal('100.00'),
            paid_by_user_id=user.id,
            category='SHARED',
            month_year=current_month
        )
        db.session.add(transaction)
        db.session.commit()

        stats = calculate_user_stats(user.id)

        assert stats['ytd_total_paid'] == 100.00
        assert stats['monthly_average'] == 100.00
        assert len(stats['household_breakdown']) == 1
        assert stats['household_breakdown'][0]['household_name'] == 'Test Household'
        assert stats['household_breakdown'][0]['total_paid'] == 100.00


@pytest.mark.unit
class TestProfileRoutes:
    """Test profile route functionality."""

    def test_profile_requires_login(self, client, app):
        """Profile page requires authentication."""
        response = client.get('/profile')
        # Should redirect to login
        assert response.status_code in [302, 303]
        assert '/login' in response.headers['Location']

    def test_profile_page_loads(self, client, app, db):
        """Profile page loads for authenticated user."""
        from models import User, Household, HouseholdMember

        # Create user
        user = User(email='test@test.com', name='Test User')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

        # Create household for user
        household = Household(name='Test Household', created_by_user_id=user.id)
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=user.id,
            role='owner',
            display_name='Test'
        )
        db.session.add(member)
        db.session.commit()

        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['current_household_id'] = household.id

        response = client.get('/profile')
        assert response.status_code == 200
        assert b'Your Profile' in response.data

    def test_update_name_success(self, client, app, db):
        """User can update their name."""
        from models import User, Household, HouseholdMember

        user = User(email='test@test.com', name='Old Name')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

        household = Household(name='Test Household', created_by_user_id=user.id)
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=user.id,
            role='owner',
            display_name='Test'
        )
        db.session.add(member)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['current_household_id'] = household.id

        response = client.post('/profile/update-name', data={
            'name': 'New Name'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Reload user
        db.session.refresh(user)
        assert user.name == 'New Name'

    def test_password_change_requires_current(self, client, app, db):
        """Password change requires correct current password."""
        from models import User, Household, HouseholdMember

        user = User(email='test@test.com', name='Test User')
        user.set_password('currentpass')
        db.session.add(user)
        db.session.flush()

        household = Household(name='Test Household', created_by_user_id=user.id)
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=user.id,
            role='owner',
            display_name='Test'
        )
        db.session.add(member)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['current_household_id'] = household.id

        # Try with wrong current password
        response = client.post('/profile/change-password', data={
            'current_password': 'wrongpass',
            'new_password': 'newpassword',
            'confirm_password': 'newpassword'
        }, follow_redirects=True)

        assert b'Current password is incorrect' in response.data


# Fixtures
@pytest.fixture
def app():
    """Create test application."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    return flask_app


@pytest.fixture
def db(app):
    """Create test database."""
    from models import db as _db
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()
