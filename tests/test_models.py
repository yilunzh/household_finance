"""
Unit tests for database models.
Tests schema, model methods, and relationships.
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import inspect


pytestmark = pytest.mark.unit


class TestSchema:
    """Verify database schema structure."""

    def test_all_tables_exist(self, app, db):
        """All expected tables should exist in database."""
        with app.app_context():
            inspector = inspect(db.engine)
            tables = set(inspector.get_table_names())

            expected_tables = {
                'users',
                'households',
                'household_members',
                'invitations',
                'transactions',
                'settlements',
                # Budget tracking tables
                'expense_types',
                'auto_category_rules',
                'budget_rules',
                'budget_rule_expense_types',
                'budget_snapshots'
            }

            missing = expected_tables - tables
            assert not missing, f"Missing tables: {missing}"

    def test_user_table_columns(self, app, db):
        """User table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('users')}

            expected = {'id', 'email', 'password_hash', 'name', 'is_active', 'created_at', 'last_login'}
            missing = expected - columns
            assert not missing, f"Missing user columns: {missing}"

    def test_household_table_columns(self, app, db):
        """Household table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('households')}

            expected = {'id', 'name', 'created_at', 'created_by_user_id'}
            missing = expected - columns
            assert not missing, f"Missing household columns: {missing}"

    def test_household_member_table_columns(self, app, db):
        """HouseholdMember table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('household_members')}

            expected = {'id', 'household_id', 'user_id', 'role', 'display_name', 'joined_at'}
            missing = expected - columns
            assert not missing, f"Missing household_member columns: {missing}"

    def test_transaction_table_columns(self, app, db):
        """Transaction table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('transactions')}

            expected = {'id', 'household_id', 'date', 'merchant', 'amount', 'currency',
                        'amount_in_usd', 'paid_by_user_id', 'category', 'notes', 'month_year',
                        'created_at', 'expense_type_id'}
            missing = expected - columns
            assert not missing, f"Missing transaction columns: {missing}"

            # Old 'paid_by' column should be removed
            assert 'paid_by' not in columns, "Old 'paid_by' column should be removed"

    def test_settlement_table_columns(self, app, db):
        """Settlement table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('settlements')}

            expected = {'id', 'household_id', 'month_year', 'settled_date', 'settlement_amount',
                        'from_user_id', 'to_user_id', 'settlement_message', 'created_at'}
            missing = expected - columns
            assert not missing, f"Missing settlement columns: {missing}"

            # Old columns should be removed
            assert 'from_person' not in columns, "Old 'from_person' column should be removed"
            assert 'to_person' not in columns, "Old 'to_person' column should be removed"

    def test_invitation_table_columns(self, app, db):
        """Invitation table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('invitations')}

            expected = {'id', 'household_id', 'email', 'token', 'status', 'expires_at',
                        'invited_by_user_id', 'created_at', 'accepted_at'}
            missing = expected - columns
            assert not missing, f"Missing invitation columns: {missing}"

    def test_expense_type_table_columns(self, app, db):
        """ExpenseType table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('expense_types')}

            expected = {'id', 'household_id', 'name', 'is_active', 'created_at'}
            missing = expected - columns
            assert not missing, f"Missing expense_type columns: {missing}"

    def test_auto_category_rule_table_columns(self, app, db):
        """AutoCategoryRule table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('auto_category_rules')}

            expected = {'id', 'household_id', 'expense_type_id', 'keyword', 'priority', 'created_at'}
            missing = expected - columns
            assert not missing, f"Missing auto_category_rule columns: {missing}"

    def test_budget_rule_table_columns(self, app, db):
        """BudgetRule table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('budget_rules')}

            expected = {'id', 'household_id', 'giver_user_id', 'receiver_user_id',
                        'monthly_amount', 'is_active', 'created_at'}
            missing = expected - columns
            assert not missing, f"Missing budget_rule columns: {missing}"

    def test_budget_rule_expense_type_table_columns(self, app, db):
        """BudgetRuleExpenseType table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('budget_rule_expense_types')}

            expected = {'id', 'budget_rule_id', 'expense_type_id'}
            missing = expected - columns
            assert not missing, f"Missing budget_rule_expense_type columns: {missing}"

    def test_budget_snapshot_table_columns(self, app, db):
        """BudgetSnapshot table should have all required columns."""
        with app.app_context():
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('budget_snapshots')}

            expected = {'id', 'budget_rule_id', 'month_year', 'budget_amount', 'spent_amount',
                        'giver_reimbursement', 'carryover_from_previous', 'net_balance',
                        'is_finalized', 'created_at'}
            missing = expected - columns
            assert not missing, f"Missing budget_snapshot columns: {missing}"

    def test_transaction_has_household_month_index(self, app, db):
        """Transaction table should have composite index on household_id and month_year."""
        with app.app_context():
            inspector = inspect(db.engine)
            indexes = inspector.get_indexes('transactions')
            index_columns = [set(idx['column_names']) for idx in indexes]

            # Check for composite index
            has_composite = any({'household_id', 'month_year'}.issubset(cols) for cols in index_columns)
            assert has_composite, "Missing composite index on (household_id, month_year)"


class TestUserModel:
    """Tests for User model methods."""

    def test_set_password_hashes_correctly(self, app, db):
        """set_password should hash password using PBKDF2."""
        from models import User

        with app.app_context():
            user = User(email='test@example.com', name='Test User')
            user.set_password('mypassword')

            assert user.password_hash is not None
            assert user.password_hash != 'mypassword'
            assert 'pbkdf2:sha256' in user.password_hash

    def test_check_password_valid(self, app, db):
        """check_password should return True for correct password."""
        from models import User

        with app.app_context():
            user = User(email='test@example.com', name='Test User')
            user.set_password('mypassword')

            assert user.check_password('mypassword') is True

    def test_check_password_invalid(self, app, db):
        """check_password should return False for incorrect password."""
        from models import User

        with app.app_context():
            user = User(email='test@example.com', name='Test User')
            user.set_password('mypassword')

            assert user.check_password('wrongpassword') is False

    def test_user_repr(self, app, db):
        """User repr should show id and email."""
        from models import User

        with app.app_context():
            user = User(email='test@example.com', name='Test User')
            user.id = 1

            assert '<User 1: test@example.com>' in repr(user)


class TestInvitationModel:
    """Tests for Invitation model methods."""

    def test_is_valid_pending_not_expired(self, app, db):
        """Invitation should be valid if pending and not expired."""
        from models import Invitation

        with app.app_context():
            invitation = Invitation(
                household_id=1,
                email='invite@example.com',
                token='abc123',
                status='pending',
                expires_at=datetime.utcnow() + timedelta(days=7),
                invited_by_user_id=1
            )

            assert invitation.is_valid() is True

    def test_is_valid_expired(self, app, db):
        """Invitation should not be valid if expired."""
        from models import Invitation

        with app.app_context():
            invitation = Invitation(
                household_id=1,
                email='invite@example.com',
                token='abc123',
                status='pending',
                expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
                invited_by_user_id=1
            )

            assert invitation.is_valid() is False

    def test_is_valid_accepted(self, app, db):
        """Invitation should not be valid if already accepted."""
        from models import Invitation

        with app.app_context():
            invitation = Invitation(
                household_id=1,
                email='invite@example.com',
                token='abc123',
                status='accepted',  # Already accepted
                expires_at=datetime.utcnow() + timedelta(days=7),
                invited_by_user_id=1
            )

            assert invitation.is_valid() is False


class TestTransactionModel:
    """Tests for Transaction model methods."""

    def test_to_dict_returns_all_fields(self, app, db, clean_test_data):
        """to_dict should return all transaction fields."""
        from models import User, Household, HouseholdMember, Transaction

        with app.app_context():
            # Create test user and household
            user = User(email='test_txn@example.com', name='Test User')
            user.set_password('password')
            db.session.add(user)
            db.session.flush()

            household = Household(name='Test Household', created_by_user_id=user.id)
            db.session.add(household)
            db.session.flush()

            member = HouseholdMember(
                household_id=household.id,
                user_id=user.id,
                role='owner',
                display_name='Tester'
            )
            db.session.add(member)
            db.session.flush()

            txn = Transaction(
                household_id=household.id,
                date=date(2024, 1, 15),
                merchant='Test Store',
                amount=Decimal('100.50'),
                currency='USD',
                amount_in_usd=Decimal('100.50'),
                paid_by_user_id=user.id,
                category='SHARED',
                notes='Test note',
                month_year='2024-01'
            )
            db.session.add(txn)
            db.session.commit()

            result = txn.to_dict()

            assert result['merchant'] == 'Test Store'
            assert result['amount'] == 100.50
            assert result['currency'] == 'USD'
            assert result['amount_in_usd'] == 100.50
            assert result['category'] == 'SHARED'
            assert result['notes'] == 'Test note'
            assert result['month_year'] == '2024-01'
            assert result['date'] == '2024-01-15'
            assert result['paid_by_name'] == 'Tester'

            # Cleanup
            db.session.delete(txn)
            db.session.delete(member)
            db.session.delete(household)
            db.session.delete(user)
            db.session.commit()

    def test_get_category_display_name(self, app, db):
        """get_category_display_name should return readable names."""
        from models import Transaction

        with app.app_context():
            assert Transaction.get_category_display_name('SHARED') == 'Shared'
            # Category display names may vary - just check they're not empty/unknown
            i_pay_display = Transaction.get_category_display_name('I_PAY_FOR_WIFE')
            assert i_pay_display and 'Unknown' not in i_pay_display
            personal_display = Transaction.get_category_display_name('PERSONAL_ME')
            assert personal_display and 'Unknown' not in personal_display


class TestSettlementModel:
    """Tests for Settlement model methods."""

    def test_is_month_settled_true(self, app, db, clean_test_data):
        """is_month_settled should return True when settlement exists."""
        from models import User, Household, HouseholdMember, Settlement

        with app.app_context():
            # Create test data
            user1 = User(email='test_settle1@example.com', name='User 1')
            user1.set_password('password')
            user2 = User(email='test_settle2@example.com', name='User 2')
            user2.set_password('password')
            db.session.add_all([user1, user2])
            db.session.flush()

            household = Household(name='Test Household', created_by_user_id=user1.id)
            db.session.add(household)
            db.session.flush()

            settlement = Settlement(
                household_id=household.id,
                month_year='2024-01',
                settled_date=date.today(),
                settlement_amount=Decimal('50.00'),
                from_user_id=user1.id,
                to_user_id=user2.id,
                settlement_message='User 1 owes User 2 $50.00'
            )
            db.session.add(settlement)
            db.session.commit()

            assert Settlement.is_month_settled(household.id, '2024-01') is True
            assert Settlement.is_month_settled(household.id, '2024-02') is False

            # Cleanup
            db.session.delete(settlement)
            db.session.delete(household)
            db.session.delete(user1)
            db.session.delete(user2)
            db.session.commit()

    def test_get_settlement_returns_record(self, app, db, clean_test_data):
        """get_settlement should return the settlement record."""
        from models import User, Household, Settlement

        with app.app_context():
            user1 = User(email='test_get1@example.com', name='User 1')
            user1.set_password('password')
            user2 = User(email='test_get2@example.com', name='User 2')
            user2.set_password('password')
            db.session.add_all([user1, user2])
            db.session.flush()

            household = Household(name='Test Household', created_by_user_id=user1.id)
            db.session.add(household)
            db.session.flush()

            settlement = Settlement(
                household_id=household.id,
                month_year='2024-01',
                settled_date=date.today(),
                settlement_amount=Decimal('75.00'),
                from_user_id=user2.id,
                to_user_id=user1.id,
                settlement_message='User 2 owes User 1 $75.00'
            )
            db.session.add(settlement)
            db.session.commit()

            result = Settlement.get_settlement(household.id, '2024-01')
            assert result is not None
            assert result.settlement_amount == Decimal('75.00')
            assert result.settlement_message == 'User 2 owes User 1 $75.00'

            # Cleanup
            db.session.delete(settlement)
            db.session.delete(household)
            db.session.delete(user1)
            db.session.delete(user2)
            db.session.commit()

    def test_to_dict_returns_all_fields(self, app, db, clean_test_data):
        """to_dict should return all settlement fields."""
        from models import User, Household, Settlement

        with app.app_context():
            user1 = User(email='test_dict1@example.com', name='User 1')
            user1.set_password('password')
            user2 = User(email='test_dict2@example.com', name='User 2')
            user2.set_password('password')
            db.session.add_all([user1, user2])
            db.session.flush()

            household = Household(name='Test Household', created_by_user_id=user1.id)
            db.session.add(household)
            db.session.flush()

            settlement = Settlement(
                household_id=household.id,
                month_year='2024-02',
                settled_date=date(2024, 2, 28),
                settlement_amount=Decimal('123.45'),
                from_user_id=user1.id,
                to_user_id=user2.id,
                settlement_message='Test settlement'
            )
            db.session.add(settlement)
            db.session.commit()

            result = settlement.to_dict()

            assert result['month_year'] == '2024-02'
            assert result['settled_date'] == '2024-02-28'
            assert result['settlement_amount'] == 123.45
            assert result['settlement_message'] == 'Test settlement'

            # Cleanup
            db.session.delete(settlement)
            db.session.delete(household)
            db.session.delete(user1)
            db.session.delete(user2)
            db.session.commit()
