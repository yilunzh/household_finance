"""
Tests for API v1 merchant-suggestions endpoint.

Tests:
- GET /api/v1/merchant-suggestions - Combined merchant suggestions
"""
import pytest
from datetime import date
from decimal import Decimal


@pytest.fixture
def api_client(app):
    """Create test client for API tests."""
    return app.test_client()


@pytest.fixture
def test_user(app, db):
    """Create a test user."""
    from models import User, RefreshToken
    with app.app_context():
        existing = User.query.filter_by(email='merch_test@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='merch_test@example.com',
            name='Merchant Tester',
            is_active=True
        )
        user.set_password('Password123')
        db.session.add(user)
        db.session.commit()

        yield {
            'id': user.id,
            'email': user.email,
            'password': 'Password123'
        }

        user = User.query.filter_by(email='merch_test@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_household(app, db, test_user):
    """Create a household with rules and transactions for merchant suggestions."""
    from models import (
        Household, HouseholdMember, ExpenseType,
        AutoCategoryRule, Transaction
    )
    with app.app_context():
        household = Household(
            name='Merchant Suggest Household',
            created_by_user_id=test_user['id']
        )
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=test_user['id'],
            role='owner',
            display_name='Owner'
        )
        db.session.add(member)

        grocery_type = ExpenseType(
            household_id=household.id,
            name='Grocery',
            icon='cart',
            color='emerald'
        )
        db.session.add(grocery_type)
        db.session.flush()

        # Auto-category rules
        rule1 = AutoCategoryRule(
            household_id=household.id,
            keyword='Whole Foods',
            expense_type_id=grocery_type.id
        )
        db.session.add(rule1)

        rule2 = AutoCategoryRule(
            household_id=household.id,
            keyword='Trader Joe',
            expense_type_id=grocery_type.id
        )
        db.session.add(rule2)

        # Past transactions with merchants
        month = date.today().strftime('%Y-%m')
        txn1 = Transaction(
            household_id=household.id,
            date=date.today(),
            merchant='Amazon',
            amount=Decimal('50.00'),
            currency='USD',
            amount_in_usd=Decimal('50.00'),
            paid_by_user_id=test_user['id'],
            category='SHARED',
            month_year=month
        )
        db.session.add(txn1)

        # Duplicate merchant casing (should be deduped)
        txn2 = Transaction(
            household_id=household.id,
            date=date.today(),
            merchant='whole foods',
            amount=Decimal('80.00'),
            currency='USD',
            amount_in_usd=Decimal('80.00'),
            paid_by_user_id=test_user['id'],
            category='SHARED',
            month_year=month
        )
        db.session.add(txn2)

        # Unique transaction merchant
        txn3 = Transaction(
            household_id=household.id,
            date=date.today(),
            merchant='Costco',
            amount=Decimal('120.00'),
            currency='USD',
            amount_in_usd=Decimal('120.00'),
            paid_by_user_id=test_user['id'],
            category='SHARED',
            month_year=month
        )
        db.session.add(txn3)

        db.session.commit()

        yield {
            'id': household.id,
        }

        # Cleanup
        Transaction.query.filter_by(household_id=household.id).delete()
        AutoCategoryRule.query.filter_by(household_id=household.id).delete()
        ExpenseType.query.filter_by(household_id=household.id).delete()
        HouseholdMember.query.filter_by(household_id=household.id).delete()
        Household.query.filter_by(id=household.id).delete()
        db.session.commit()


def get_auth_token(client, email, password):
    """Helper to get auth token."""
    response = client.post('/api/v1/auth/login', json={
        'email': email,
        'password': password
    })
    return response.get_json()['access_token']


class TestMerchantSuggestions:
    """Tests for GET /api/v1/merchant-suggestions"""

    def test_returns_combined_merchants(self, api_client, test_user, test_household):
        """Test endpoint returns merchants from rules + transactions, deduplicated."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.get(
            '/api/v1/merchant-suggestions',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'merchants' in data
        merchants = data['merchants']

        # Rule keywords: "Whole Foods", "Trader Joe"
        # Transaction merchants: "Amazon", "whole foods" (deduped), "Costco"
        # Expected: Amazon, Costco, Trader Joe, Whole Foods (sorted, rule casing wins)
        assert 'Amazon' in merchants
        assert 'Costco' in merchants
        assert 'Trader Joe' in merchants
        assert 'Whole Foods' in merchants

        # "whole foods" (transaction) should NOT appear separately
        assert 'whole foods' not in merchants

        # Should be sorted alphabetically
        assert merchants == sorted(merchants, key=str.lower)

    def test_requires_auth(self, api_client, test_household):
        """Test endpoint requires authentication."""
        response = api_client.get(
            '/api/v1/merchant-suggestions',
            headers={
                'X-Household-ID': str(test_household['id'])
            }
        )
        assert response.status_code == 401

    def test_requires_household(self, app, db, api_client):
        """Test endpoint requires household context."""
        from models import User, RefreshToken
        with app.app_context():
            # Create a user with NO household
            existing = User.query.filter_by(email='no_house@example.com').first()
            if existing:
                RefreshToken.query.filter_by(user_id=existing.id).delete()
                db.session.delete(existing)
                db.session.commit()

            user = User(email='no_house@example.com', name='No House', is_active=True)
            user.set_password('Password123')
            db.session.add(user)
            db.session.commit()

            token = get_auth_token(api_client, 'no_house@example.com', 'Password123')

            response = api_client.get(
                '/api/v1/merchant-suggestions',
                headers={
                    'Authorization': f'Bearer {token}',
                }
            )
            assert response.status_code == 400

            # Cleanup
            user = User.query.filter_by(email='no_house@example.com').first()
            if user:
                RefreshToken.query.filter_by(user_id=user.id).delete()
                db.session.delete(user)
                db.session.commit()

    def test_empty_household(self, app, db, api_client, test_user):
        """Test endpoint returns empty list for household with no rules or transactions."""
        from models import Household, HouseholdMember

        with app.app_context():
            household = Household(
                name='Empty Household',
                created_by_user_id=test_user['id']
            )
            db.session.add(household)
            db.session.flush()

            member = HouseholdMember(
                household_id=household.id,
                user_id=test_user['id'],
                role='owner',
                display_name='Owner'
            )
            db.session.add(member)
            db.session.commit()

            token = get_auth_token(api_client, test_user['email'], test_user['password'])

            response = api_client.get(
                '/api/v1/merchant-suggestions',
                headers={
                    'Authorization': f'Bearer {token}',
                    'X-Household-ID': str(household.id)
                }
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['merchants'] == []

            # Cleanup
            HouseholdMember.query.filter_by(household_id=household.id).delete()
            Household.query.filter_by(id=household.id).delete()
            db.session.commit()
