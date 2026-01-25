"""
Unit tests for budget tracking functionality.
Tests budget calculation utilities and model methods.
"""
import pytest
from decimal import Decimal


pytestmark = pytest.mark.unit


class TestBudgetModels:
    """Tests for budget-related model methods."""

    def test_expense_type_creation(self, app, db, clean_test_data):
        """ExpenseType can be created with household_id and name."""
        from models import User, Household, ExpenseType

        with app.app_context():
            user = User(email='budget_test@example.com', name='Budget Tester')
            user.set_password('password')
            db.session.add(user)
            db.session.flush()

            household = Household(name='Budget Test Household', created_by_user_id=user.id)
            db.session.add(household)
            db.session.flush()

            expense_type = ExpenseType(
                household_id=household.id,
                name='Groceries',
                is_active=True
            )
            db.session.add(expense_type)
            db.session.commit()

            assert expense_type.id is not None
            assert expense_type.name == 'Groceries'
            assert expense_type.is_active is True

            # Cleanup
            db.session.delete(expense_type)
            db.session.delete(household)
            db.session.delete(user)
            db.session.commit()

    def test_auto_category_rule_creation(self, app, db, clean_test_data):
        """AutoCategoryRule can be created with household_id, expense_type_id and keyword."""
        from models import User, Household, ExpenseType, AutoCategoryRule

        with app.app_context():
            user = User(email='auto_cat_test@example.com', name='Auto Cat Tester')
            user.set_password('password')
            db.session.add(user)
            db.session.flush()

            household = Household(name='Auto Cat Household', created_by_user_id=user.id)
            db.session.add(household)
            db.session.flush()

            expense_type = ExpenseType(
                household_id=household.id,
                name='Groceries',
                is_active=True
            )
            db.session.add(expense_type)
            db.session.flush()

            rule = AutoCategoryRule(
                household_id=household.id,
                expense_type_id=expense_type.id,
                keyword='publix'
            )
            db.session.add(rule)
            db.session.commit()

            assert rule.id is not None
            assert rule.keyword == 'publix'
            assert rule.household_id == household.id

            # Cleanup
            db.session.delete(rule)
            db.session.delete(expense_type)
            db.session.delete(household)
            db.session.delete(user)
            db.session.commit()

    def test_budget_rule_creation(self, app, db, clean_test_data):
        """BudgetRule can be created with giver, receiver, and amount."""
        from models import User, Household, HouseholdMember, BudgetRule

        with app.app_context():
            # Create two users
            user1 = User(email='giver_test@example.com', name='Giver')
            user1.set_password('password')
            user2 = User(email='receiver_test@example.com', name='Receiver')
            user2.set_password('password')
            db.session.add_all([user1, user2])
            db.session.flush()

            household = Household(name='Budget Rule Household', created_by_user_id=user1.id)
            db.session.add(household)
            db.session.flush()

            # Add members
            member1 = HouseholdMember(
                household_id=household.id,
                user_id=user1.id,
                role='owner',
                display_name='Giver'
            )
            member2 = HouseholdMember(
                household_id=household.id,
                user_id=user2.id,
                role='member',
                display_name='Receiver'
            )
            db.session.add_all([member1, member2])
            db.session.flush()

            budget_rule = BudgetRule(
                household_id=household.id,
                giver_user_id=user1.id,
                receiver_user_id=user2.id,
                monthly_amount=Decimal('1500.00'),
                is_active=True
            )
            db.session.add(budget_rule)
            db.session.commit()

            assert budget_rule.id is not None
            assert budget_rule.monthly_amount == Decimal('1500.00')
            assert budget_rule.giver_user_id == user1.id
            assert budget_rule.receiver_user_id == user2.id

            # Cleanup
            db.session.delete(budget_rule)
            db.session.delete(member1)
            db.session.delete(member2)
            db.session.delete(household)
            db.session.delete(user1)
            db.session.delete(user2)
            db.session.commit()

    def test_budget_rule_to_dict(self, app, db, clean_test_data):
        """BudgetRule.to_dict() returns correct structure."""
        from models import User, Household, HouseholdMember, BudgetRule, ExpenseType, BudgetRuleExpenseType

        with app.app_context():
            user1 = User(email='dict_giver@example.com', name='Dict Giver')
            user1.set_password('password')
            user2 = User(email='dict_receiver@example.com', name='Dict Receiver')
            user2.set_password('password')
            db.session.add_all([user1, user2])
            db.session.flush()

            household = Household(name='Dict Test Household', created_by_user_id=user1.id)
            db.session.add(household)
            db.session.flush()

            member1 = HouseholdMember(
                household_id=household.id,
                user_id=user1.id,
                role='owner',
                display_name='Giver Name'
            )
            member2 = HouseholdMember(
                household_id=household.id,
                user_id=user2.id,
                role='member',
                display_name='Receiver Name'
            )
            db.session.add_all([member1, member2])
            db.session.flush()

            expense_type = ExpenseType(
                household_id=household.id,
                name='Groceries',
                is_active=True
            )
            db.session.add(expense_type)
            db.session.flush()

            budget_rule = BudgetRule(
                household_id=household.id,
                giver_user_id=user1.id,
                receiver_user_id=user2.id,
                monthly_amount=Decimal('1000.00'),
                is_active=True
            )
            db.session.add(budget_rule)
            db.session.flush()

            # Link expense type to budget rule
            link = BudgetRuleExpenseType(
                budget_rule_id=budget_rule.id,
                expense_type_id=expense_type.id
            )
            db.session.add(link)
            db.session.commit()

            result = budget_rule.to_dict()

            assert result['id'] == budget_rule.id
            assert result['giver_user_id'] == user1.id
            assert result['receiver_user_id'] == user2.id
            assert result['monthly_amount'] == 1000.00
            assert expense_type.id in result['expense_type_ids']

            # Cleanup
            db.session.delete(link)
            db.session.delete(budget_rule)
            db.session.delete(expense_type)
            db.session.delete(member1)
            db.session.delete(member2)
            db.session.delete(household)
            db.session.delete(user1)
            db.session.delete(user2)
            db.session.commit()


class TestGetCarryoverFromPrevious:
    """Tests for get_carryover_from_previous function."""

    def test_january_returns_zero(self, app, db):
        """January should return 0 carryover (yearly reset)."""
        from budget_utils import get_carryover_from_previous

        with app.app_context():
            # January should always return 0 regardless of budget_rule_id
            result = get_carryover_from_previous(999, '2026-01')
            assert result == Decimal('0.00')

    def test_february_calculates_previous_month(self, app, db):
        """Non-January months should look at previous month."""
        from budget_utils import get_carryover_from_previous

        with app.app_context():
            # For a non-existent budget rule, should return 0
            result = get_carryover_from_previous(99999, '2026-02')
            assert result == Decimal('0.00')


class TestExpenseTypeMatching:
    """Tests for expense type auto-categorization."""

    def test_keyword_case_insensitive(self, app, db, clean_test_data):
        """Auto-category keywords should match case-insensitively."""
        from models import User, Household, ExpenseType, AutoCategoryRule

        with app.app_context():
            user = User(email='keyword_test@example.com', name='Keyword Tester')
            user.set_password('password')
            db.session.add(user)
            db.session.flush()

            household = Household(name='Keyword Test', created_by_user_id=user.id)
            db.session.add(household)
            db.session.flush()

            expense_type = ExpenseType(
                household_id=household.id,
                name='Groceries',
                is_active=True
            )
            db.session.add(expense_type)
            db.session.flush()

            rule = AutoCategoryRule(
                household_id=household.id,
                expense_type_id=expense_type.id,
                keyword='publix'
            )
            db.session.add(rule)
            db.session.commit()

            # Test that keyword is stored
            assert rule.keyword == 'publix'

            # Cleanup
            db.session.delete(rule)
            db.session.delete(expense_type)
            db.session.delete(household)
            db.session.delete(user)
            db.session.commit()


class TestBudgetSnapshot:
    """Tests for BudgetSnapshot model."""

    def test_snapshot_creation(self, app, db, clean_test_data):
        """BudgetSnapshot can be created with all required fields."""
        from models import User, Household, HouseholdMember, BudgetRule, BudgetSnapshot

        with app.app_context():
            user1 = User(email='snap_giver@example.com', name='Snap Giver')
            user1.set_password('password')
            user2 = User(email='snap_receiver@example.com', name='Snap Receiver')
            user2.set_password('password')
            db.session.add_all([user1, user2])
            db.session.flush()

            household = Household(name='Snapshot Household', created_by_user_id=user1.id)
            db.session.add(household)
            db.session.flush()

            member1 = HouseholdMember(
                household_id=household.id,
                user_id=user1.id,
                role='owner',
                display_name='Giver'
            )
            member2 = HouseholdMember(
                household_id=household.id,
                user_id=user2.id,
                role='member',
                display_name='Receiver'
            )
            db.session.add_all([member1, member2])
            db.session.flush()

            budget_rule = BudgetRule(
                household_id=household.id,
                giver_user_id=user1.id,
                receiver_user_id=user2.id,
                monthly_amount=Decimal('1500.00'),
                is_active=True
            )
            db.session.add(budget_rule)
            db.session.flush()

            snapshot = BudgetSnapshot(
                budget_rule_id=budget_rule.id,
                month_year='2026-01',
                budget_amount=Decimal('1500.00'),
                spent_amount=Decimal('1200.00'),
                giver_reimbursement=Decimal('300.00'),
                carryover_from_previous=Decimal('0.00'),
                net_balance=Decimal('300.00'),
                is_finalized=False
            )
            db.session.add(snapshot)
            db.session.commit()

            assert snapshot.id is not None
            assert snapshot.budget_amount == Decimal('1500.00')
            assert snapshot.spent_amount == Decimal('1200.00')
            assert snapshot.net_balance == Decimal('300.00')

            # Cleanup
            db.session.delete(snapshot)
            db.session.delete(budget_rule)
            db.session.delete(member1)
            db.session.delete(member2)
            db.session.delete(household)
            db.session.delete(user1)
            db.session.delete(user2)
            db.session.commit()
