"""
Unit tests for transaction search functionality.
Tests the search_transactions method in TransactionService.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

pytestmark = pytest.mark.unit


class TestTransactionSearch:
    """Tests for TransactionService.search_transactions method."""

    @pytest.fixture
    def search_test_data(self, app, db):
        """Set up test data for search tests."""
        from models import User, Household, HouseholdMember, Transaction, ExpenseType

        with app.app_context():
            # Clean up any existing test data first
            existing_user = User.query.filter_by(email='search_test@example.com').first()
            if existing_user:
                # Delete associated households where user is sole member
                for membership in existing_user.household_memberships:
                    if len(membership.household.members) == 1:
                        db.session.delete(membership.household)
                db.session.delete(existing_user)

            existing_user2 = User.query.filter_by(email='search_test2@example.com').first()
            if existing_user2:
                for membership in existing_user2.household_memberships:
                    if len(membership.household.members) == 1:
                        db.session.delete(membership.household)
                db.session.delete(existing_user2)

            db.session.commit()

            # Create user
            user = User(email='search_test@example.com', name='Search Test User')
            user.set_password('TestPass123!')
            db.session.add(user)

            # Create second user
            user2 = User(email='search_test2@example.com', name='Search Test User 2')
            user2.set_password('TestPass123!')
            db.session.add(user2)

            db.session.flush()

            # Create household
            household = Household(name='Search Test Household', created_by_user_id=user.id)
            db.session.add(household)
            db.session.flush()

            # Add members
            member1 = HouseholdMember(
                household_id=household.id,
                user_id=user.id,
                role='owner',
                display_name='Owner'
            )
            member2 = HouseholdMember(
                household_id=household.id,
                user_id=user2.id,
                role='member',
                display_name='Member'
            )
            db.session.add(member1)
            db.session.add(member2)

            # Create expense type
            expense_type = ExpenseType(
                household_id=household.id,
                name='Groceries'
            )
            db.session.add(expense_type)
            db.session.flush()

            # Create transactions with various attributes for testing
            today = date.today()
            yesterday = today - timedelta(days=1)
            last_week = today - timedelta(days=7)
            last_month = today - timedelta(days=30)

            transactions_data = [
                # Transaction 1: Recent, high amount, SHARED, user1 paid
                {
                    'date': today,
                    'merchant': 'Whole Foods Market',
                    'amount': Decimal('150.00'),
                    'currency': 'USD',
                    'amount_in_usd': Decimal('150.00'),
                    'paid_by_user_id': user.id,
                    'category': 'SHARED',
                    'expense_type_id': expense_type.id,
                    'notes': 'Weekly groceries shopping',
                    'month_year': today.strftime('%Y-%m'),
                },
                # Transaction 2: Yesterday, medium amount, PERSONAL_ME
                {
                    'date': yesterday,
                    'merchant': 'Starbucks Coffee',
                    'amount': Decimal('25.00'),
                    'currency': 'USD',
                    'amount_in_usd': Decimal('25.00'),
                    'paid_by_user_id': user.id,
                    'category': 'PERSONAL_ME',
                    'expense_type_id': None,
                    'notes': 'Morning coffee',
                    'month_year': yesterday.strftime('%Y-%m'),
                },
                # Transaction 3: Last week, user2 paid, SHARED
                {
                    'date': last_week,
                    'merchant': 'Amazon',
                    'amount': Decimal('75.50'),
                    'currency': 'USD',
                    'amount_in_usd': Decimal('75.50'),
                    'paid_by_user_id': user2.id,
                    'category': 'SHARED',
                    'expense_type_id': None,
                    'notes': 'Household supplies',
                    'month_year': last_week.strftime('%Y-%m'),
                },
                # Transaction 4: Last month, I_PAY_FOR_WIFE
                {
                    'date': last_month,
                    'merchant': 'Restaurant',
                    'amount': Decimal('80.00'),
                    'currency': 'USD',
                    'amount_in_usd': Decimal('80.00'),
                    'paid_by_user_id': user.id,
                    'category': 'I_PAY_FOR_WIFE',
                    'expense_type_id': None,
                    'notes': 'Birthday dinner',
                    'month_year': last_month.strftime('%Y-%m'),
                },
                # Transaction 5: CAD transaction (converted)
                {
                    'date': today,
                    'merchant': 'Canadian Store',
                    'amount': Decimal('100.00'),
                    'currency': 'CAD',
                    'amount_in_usd': Decimal('72.00'),  # Simulated conversion
                    'paid_by_user_id': user.id,
                    'category': 'SHARED',
                    'expense_type_id': expense_type.id,
                    'notes': 'Cross-border shopping',
                    'month_year': today.strftime('%Y-%m'),
                },
            ]

            for txn_data in transactions_data:
                txn = Transaction(household_id=household.id, **txn_data)
                db.session.add(txn)

            # Create a second household with a transaction (for isolation testing)
            household2 = Household(name='Other Household', created_by_user_id=user.id)
            db.session.add(household2)
            db.session.flush()

            other_txn = Transaction(
                household_id=household2.id,
                date=today,
                merchant='Other Store',
                amount=Decimal('999.99'),
                currency='USD',
                amount_in_usd=Decimal('999.99'),
                paid_by_user_id=user.id,
                category='SHARED',
                notes='Should not appear in searches',
                month_year=today.strftime('%Y-%m'),
            )
            db.session.add(other_txn)

            db.session.commit()

            # Store IDs - use the same IDs that were used when creating transactions
            # (after flush, IDs are assigned and stable)
            return {
                'household_id': household.id,
                'household2_id': household2.id,
                'user_id': user.id,
                'user2_id': user2.id,
                'expense_type_id': expense_type.id,
                'today': today,
                'yesterday': yesterday,
                'last_week': last_week,
                'last_month': last_month,
            }

    def test_search_no_filters_returns_all(self, app, search_test_data):
        """Search with no filters returns all transactions for household."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={}
            )

            # Should return all 5 transactions from the test household
            assert len(results) == 5

    def test_search_by_merchant_name(self, app, search_test_data):
        """Search finds transactions by merchant name (case-insensitive)."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'search': 'whole foods'}
            )

            assert len(results) == 1
            assert results[0].merchant == 'Whole Foods Market'

    def test_search_by_notes(self, app, search_test_data):
        """Search finds transactions by notes content."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'search': 'birthday'}
            )

            assert len(results) == 1
            assert 'Birthday' in results[0].notes

    def test_search_phrase_match(self, app, search_test_data):
        """Multi-word search matches exact phrase."""
        from services.transaction_service import TransactionService

        with app.app_context():
            # Should find "Weekly groceries shopping"
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'search': 'groceries shopping'}
            )

            assert len(results) == 1

            # Partial phrase should also work
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'search': 'morning coffee'}
            )

            assert len(results) == 1

    def test_search_case_insensitive(self, app, search_test_data):
        """Search is case-insensitive."""
        from services.transaction_service import TransactionService

        with app.app_context():
            # Uppercase search
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'search': 'STARBUCKS'}
            )

            assert len(results) == 1
            assert 'Starbucks' in results[0].merchant

    def test_filter_by_date_range(self, app, search_test_data):
        """Date range filter returns correct transactions."""
        from services.transaction_service import TransactionService

        with app.app_context():
            today = search_test_data['today']
            yesterday = search_test_data['yesterday']

            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={
                    'date_from': yesterday.strftime('%Y-%m-%d'),
                    'date_to': today.strftime('%Y-%m-%d'),
                }
            )

            # Should include today's 2 transactions + yesterday's 1
            assert len(results) == 3
            for txn in results:
                assert txn.date >= yesterday
                assert txn.date <= today

    def test_filter_by_date_from_only(self, app, search_test_data):
        """Date from filter without date to works."""
        from services.transaction_service import TransactionService

        with app.app_context():
            yesterday = search_test_data['yesterday']

            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'date_from': yesterday.strftime('%Y-%m-%d')}
            )

            # Should include today (2) + yesterday (1) = 3
            assert len(results) == 3
            for txn in results:
                assert txn.date >= yesterday

    def test_filter_by_category(self, app, search_test_data):
        """Category filter returns only matching transactions."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'category': 'SHARED'}
            )

            # 3 SHARED transactions
            assert len(results) == 3
            for txn in results:
                assert txn.category == 'SHARED'

    def test_filter_by_paid_by(self, app, search_test_data):
        """Paid by filter returns only transactions paid by that user."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'paid_by': search_test_data['user2_id']}
            )

            # Only 1 transaction paid by user2
            assert len(results) == 1
            assert results[0].paid_by_user_id == search_test_data['user2_id']

    def test_filter_by_expense_type(self, app, search_test_data):
        """Expense type filter works correctly."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'expense_type_id': search_test_data['expense_type_id']}
            )

            # 2 transactions have the Groceries expense type
            assert len(results) == 2
            for txn in results:
                assert txn.expense_type_id == search_test_data['expense_type_id']

    def test_filter_by_amount_min(self, app, search_test_data):
        """Amount min filter works correctly (uses USD amount)."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'amount_min': 75.0}
            )

            # Transactions >= $75 USD: 150, 75.50, 80 = 3
            assert len(results) == 3
            for txn in results:
                assert float(txn.amount_in_usd) >= 75.0

    def test_filter_by_amount_max(self, app, search_test_data):
        """Amount max filter works correctly."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'amount_max': 50.0}
            )

            # Transactions <= $50 USD: 25 = 1
            assert len(results) == 1
            for txn in results:
                assert float(txn.amount_in_usd) <= 50.0

    def test_filter_by_amount_range(self, app, search_test_data):
        """Amount min and max together work correctly."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={
                    'amount_min': 70.0,
                    'amount_max': 100.0,
                }
            )

            # Transactions between $70-$100: 75.50, 80, 72 = 3
            assert len(results) == 3
            for txn in results:
                assert 70.0 <= float(txn.amount_in_usd) <= 100.0

    def test_combined_filters(self, app, search_test_data):
        """Multiple filters applied together work correctly (AND logic)."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={
                    'category': 'SHARED',
                    'paid_by': search_test_data['user_id'],
                }
            )

            # SHARED transactions paid by user1: Whole Foods, Canadian Store = 2
            assert len(results) == 2
            for txn in results:
                assert txn.category == 'SHARED'
                assert txn.paid_by_user_id == search_test_data['user_id']

    def test_empty_results(self, app, search_test_data):
        """Returns empty list when no transactions match."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'search': 'nonexistent merchant xyz'}
            )

            assert len(results) == 0

    def test_household_isolation(self, app, search_test_data):
        """Search only returns transactions from specified household."""
        from services.transaction_service import TransactionService

        with app.app_context():
            # Search in test household - should NOT find "Other Store"
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={'search': 'Other Store'}
            )

            assert len(results) == 0

            # Search in other household - should find it
            results = TransactionService.search_transactions(
                household_id=search_test_data['household2_id'],
                filters={'search': 'Other Store'}
            )

            assert len(results) == 1

    def test_results_ordered_by_date_desc(self, app, search_test_data):
        """Results are ordered by date descending."""
        from services.transaction_service import TransactionService

        with app.app_context():
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={}
            )

            # Verify descending order
            dates = [txn.date for txn in results]
            assert dates == sorted(dates, reverse=True)

    def test_invalid_date_format_ignored(self, app, search_test_data):
        """Invalid date format is gracefully ignored."""
        from services.transaction_service import TransactionService

        with app.app_context():
            # Should not raise error, just ignore invalid date
            results = TransactionService.search_transactions(
                household_id=search_test_data['household_id'],
                filters={
                    'date_from': 'invalid-date',
                    'date_to': 'also-invalid',
                }
            )

            # Should return all transactions (filter ignored)
            assert len(results) == 5


class TestSearchAPIEndpoint:
    """Tests for the /api/transactions/search endpoint."""

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def logged_in_client(self, app, db, client):
        """Create logged in test client with household."""
        from models import User, Household, HouseholdMember, Transaction

        with app.app_context():
            # Clean up existing test data
            existing_user = User.query.filter_by(email='api_test@example.com').first()
            if existing_user:
                for membership in existing_user.household_memberships:
                    if len(membership.household.members) == 1:
                        db.session.delete(membership.household)
                db.session.delete(existing_user)
            db.session.commit()

            # Create user
            user = User(email='api_test@example.com', name='API Test User')
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.flush()

            # Create household
            household = Household(name='API Test Household', created_by_user_id=user.id)
            db.session.add(household)
            db.session.flush()

            # Add member
            member = HouseholdMember(
                household_id=household.id,
                user_id=user.id,
                role='owner',
                display_name='Tester'
            )
            db.session.add(member)

            # Add a transaction
            txn = Transaction(
                household_id=household.id,
                date=date.today(),
                merchant='Test Merchant',
                amount=Decimal('50.00'),
                currency='USD',
                amount_in_usd=Decimal('50.00'),
                paid_by_user_id=user.id,
                category='SHARED',
                notes='Test transaction',
                month_year=date.today().strftime('%Y-%m'),
            )
            db.session.add(txn)
            db.session.commit()

            user_id = user.id
            household_id = household.id

        # Login via test client
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['current_household_id'] = household_id

        return client, household_id

    def test_endpoint_requires_auth(self, client):
        """Endpoint requires authentication."""
        response = client.get('/api/transactions/search')
        # Should redirect to login or return 401
        assert response.status_code in [302, 401]

    def test_endpoint_returns_json(self, logged_in_client):
        """Endpoint returns JSON response."""
        client, _ = logged_in_client
        response = client.get('/api/transactions/search')

        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = response.get_json()
        assert 'success' in data
        assert 'transactions' in data
        assert 'count' in data

    def test_endpoint_accepts_filters(self, logged_in_client):
        """Endpoint accepts filter parameters."""
        client, _ = logged_in_client
        response = client.get('/api/transactions/search?search=Test')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['transactions']) >= 1

    def test_endpoint_returns_transaction_dict(self, logged_in_client):
        """Endpoint returns transaction data as dict."""
        client, _ = logged_in_client
        response = client.get('/api/transactions/search')

        data = response.get_json()
        assert len(data['transactions']) >= 1

        txn = data['transactions'][0]
        # Check expected fields from to_dict()
        assert 'id' in txn
        assert 'date' in txn
        assert 'merchant' in txn
        assert 'amount' in txn
        assert 'currency' in txn
        assert 'amount_in_usd' in txn
        assert 'paid_by_user_id' in txn
        assert 'category' in txn
