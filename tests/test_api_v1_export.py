"""
Tests for API v1 export endpoints.

Tests:
- GET /api/v1/export/transactions - Export all transactions
- GET /api/v1/export/transactions/<month> - Export monthly transactions
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
        existing = User.query.filter_by(email='export_test@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='export_test@example.com',
            name='Export Tester',
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

        user = User.query.filter_by(email='export_test@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_household(app, db, test_user):
    """Create a test household with transactions."""
    from models import Household, HouseholdMember, Transaction
    with app.app_context():
        household = Household(
            name='Export Test Household',
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

        # Create some transactions
        txn1 = Transaction(
            household_id=household.id,
            date=date(2024, 1, 15),
            merchant='Grocery Store',
            amount=Decimal('50.00'),
            currency='USD',
            amount_in_usd=Decimal('50.00'),
            category='SHARED',
            paid_by_user_id=test_user['id'],
            month_year='2024-01'
        )
        txn2 = Transaction(
            household_id=household.id,
            date=date(2024, 1, 20),
            merchant='Restaurant',
            amount=Decimal('30.00'),
            currency='USD',
            amount_in_usd=Decimal('30.00'),
            category='SHARED',
            paid_by_user_id=test_user['id'],
            month_year='2024-01'
        )
        db.session.add(txn1)
        db.session.add(txn2)
        db.session.commit()

        yield {
            'id': household.id,
            'name': household.name
        }

        # Cleanup
        Transaction.query.filter_by(household_id=household.id).delete()
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


class TestExportAllTransactions:
    """Tests for GET /api/v1/export/transactions"""

    def test_export_all_transactions(self, api_client, test_user, test_household):
        """Test exporting all transactions as CSV."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.get(
            '/api/v1/export/transactions',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'
        assert 'attachment' in response.headers.get('Content-Disposition', '')

        # Check CSV content
        csv_content = response.data.decode('utf-8')
        assert 'Date,Merchant,Amount,Currency' in csv_content
        assert 'Grocery Store' in csv_content
        assert 'Restaurant' in csv_content

    def test_export_with_date_filter(self, api_client, test_user, test_household):
        """Test exporting transactions with date filter."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.get(
            '/api/v1/export/transactions?start_date=2024-01-15&end_date=2024-01-15',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        csv_content = response.data.decode('utf-8')
        assert 'Grocery Store' in csv_content
        # Restaurant is on 2024-01-20, should not be included
        lines = csv_content.strip().split('\n')
        # Header + 1 data row
        assert len(lines) == 2


class TestExportMonthlyTransactions:
    """Tests for GET /api/v1/export/transactions/<month>"""

    def test_export_monthly_transactions(self, api_client, test_user, test_household):
        """Test exporting transactions for a specific month."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.get(
            '/api/v1/export/transactions/2024-01',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        assert 'expenses_2024-01.csv' in response.headers.get('Content-Disposition', '')

        csv_content = response.data.decode('utf-8')
        assert 'SUMMARY' in csv_content
        assert 'Settlement' in csv_content

    def test_export_empty_month(self, api_client, test_user, test_household):
        """Test exporting transactions for month with no data."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.get(
            '/api/v1/export/transactions/2025-12',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        csv_content = response.data.decode('utf-8')
        # Should have header and summary but no data rows
        assert 'SUMMARY' in csv_content

    def test_export_invalid_month(self, api_client, test_user, test_household):
        """Test exporting with invalid month format."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.get(
            '/api/v1/export/transactions/invalid',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 400
