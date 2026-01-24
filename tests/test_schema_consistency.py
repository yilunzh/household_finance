"""
Schema consistency tests - verify all model columns exist in database.

This test file auto-validates that every column defined in SQLAlchemy models
actually exists in the database schema. This catches issues where:
- A new column is added to a model but migration is forgotten
- A column name is mistyped between model and migration
- Production database is missing columns added in code

The test runs in CI on every PR to catch schema drift before deployment.
"""
import pytest
from sqlalchemy import inspect


def test_all_model_columns_exist_in_database(app, db):
    """Verify every column defined in models exists in the actual database.

    This test imports all models and checks that every column defined
    in the SQLAlchemy model has a corresponding column in the database.

    If this test fails, it means:
    1. A new column was added to a model
    2. The migration was not added to init_db() in app.py
    3. Production would crash when accessing that column

    Fix: Add ALTER TABLE statement to init_db() in app.py
    """
    from models import (
        User, Household, HouseholdMember, Transaction, Settlement,
        Invitation, ExpenseType, AutoCategoryRule, BudgetRule,
        BudgetRuleExpenseType, BudgetSnapshot, SplitRule,
        SplitRuleExpenseType, RefreshToken, DeviceToken
    )

    # All models to check
    all_models = [
        User, Household, HouseholdMember, Transaction, Settlement,
        Invitation, ExpenseType, AutoCategoryRule, BudgetRule,
        BudgetRuleExpenseType, BudgetSnapshot, SplitRule,
        SplitRuleExpenseType, RefreshToken, DeviceToken
    ]

    with app.app_context():
        inspector = inspect(db.engine)
        errors = []

        for model in all_models:
            table_name = model.__tablename__

            # Get columns from database
            try:
                db_columns = {col['name'] for col in inspector.get_columns(table_name)}
            except Exception as e:
                errors.append(f"Table '{table_name}' does not exist in database: {e}")
                continue

            # Get columns from model
            model_columns = {col.name for col in model.__table__.columns}

            # Find columns in model but missing from database
            missing_columns = model_columns - db_columns

            if missing_columns:
                errors.append(
                    f"Table '{table_name}' missing columns: {sorted(missing_columns)}. "
                    f"Add ALTER TABLE migration to init_db() in app.py"
                )

        if errors:
            pytest.fail("\n".join(errors))


def test_all_tables_exist(app, db):
    """Verify all model tables exist in the database."""
    from models import (
        User, Household, HouseholdMember, Transaction, Settlement,
        Invitation, ExpenseType, AutoCategoryRule, BudgetRule,
        BudgetRuleExpenseType, BudgetSnapshot, SplitRule,
        SplitRuleExpenseType, RefreshToken, DeviceToken
    )

    expected_tables = {
        'users', 'households', 'household_members', 'transactions',
        'settlements', 'invitations', 'expense_types', 'auto_category_rules',
        'budget_rules', 'budget_rule_expense_types', 'budget_snapshots',
        'split_rules', 'split_rule_expense_types', 'refresh_tokens',
        'device_tokens'
    }

    with app.app_context():
        inspector = inspect(db.engine)
        actual_tables = set(inspector.get_table_names())

        missing_tables = expected_tables - actual_tables
        if missing_tables:
            pytest.fail(
                f"Missing tables: {sorted(missing_tables)}. "
                f"Run db.create_all() or add table creation to init_db()"
            )
