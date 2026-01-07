#!/usr/bin/env python3
"""
Test script to verify Phase 2 database schema.
Checks that all new tables and relationships exist correctly.
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import User, Household, HouseholdMember, Invitation, Transaction, Settlement
from sqlalchemy import inspect


def test_schema():
    """Verify all tables and columns exist in the database."""
    print("\n" + "=" * 60)
    print("PHASE 2 SCHEMA VERIFICATION TEST")
    print("=" * 60)

    with app.app_context():
        inspector = inspect(db.engine)

        # Get all table names
        tables = inspector.get_table_names()
        print(f"\n✓ Database tables found: {len(tables)}")
        for table in sorted(tables):
            print(f"  - {table}")

        # Expected tables
        expected_tables = {
            'users',
            'households',
            'household_members',
            'invitations',
            'transactions',
            'settlements'
        }

        missing_tables = expected_tables - set(tables)
        if missing_tables:
            print(f"\n✗ MISSING TABLES: {missing_tables}")
            return False
        else:
            print(f"\n✓ All {len(expected_tables)} expected tables exist")

        # Check User table columns
        print("\n" + "-" * 60)
        print("USER TABLE")
        print("-" * 60)
        user_cols = [col['name'] for col in inspector.get_columns('users')]
        print(f"Columns: {', '.join(user_cols)}")

        expected_user_cols = {'id', 'email', 'password_hash', 'name', 'is_active', 'created_at', 'last_login'}
        if expected_user_cols.issubset(set(user_cols)):
            print("✓ User table has all required columns")
        else:
            print(f"✗ Missing columns: {expected_user_cols - set(user_cols)}")

        # Check Household table columns
        print("\n" + "-" * 60)
        print("HOUSEHOLD TABLE")
        print("-" * 60)
        household_cols = [col['name'] for col in inspector.get_columns('households')]
        print(f"Columns: {', '.join(household_cols)}")

        expected_household_cols = {'id', 'name', 'created_at', 'created_by_user_id'}
        if expected_household_cols.issubset(set(household_cols)):
            print("✓ Household table has all required columns")
        else:
            print(f"✗ Missing columns: {expected_household_cols - set(household_cols)}")

        # Check HouseholdMember table columns
        print("\n" + "-" * 60)
        print("HOUSEHOLD_MEMBERS TABLE")
        print("-" * 60)
        member_cols = [col['name'] for col in inspector.get_columns('household_members')]
        print(f"Columns: {', '.join(member_cols)}")

        expected_member_cols = {'id', 'household_id', 'user_id', 'role', 'display_name', 'joined_at'}
        if expected_member_cols.issubset(set(member_cols)):
            print("✓ HouseholdMember table has all required columns")
        else:
            print(f"✗ Missing columns: {expected_member_cols - set(member_cols)}")

        # Check Invitation table columns
        print("\n" + "-" * 60)
        print("INVITATIONS TABLE")
        print("-" * 60)
        invitation_cols = [col['name'] for col in inspector.get_columns('invitations')]
        print(f"Columns: {', '.join(invitation_cols)}")

        expected_invitation_cols = {'id', 'household_id', 'email', 'token', 'status', 'expires_at', 'invited_by_user_id', 'created_at', 'accepted_at'}
        if expected_invitation_cols.issubset(set(invitation_cols)):
            print("✓ Invitation table has all required columns")
        else:
            print(f"✗ Missing columns: {expected_invitation_cols - set(invitation_cols)}")

        # Check Transaction table columns (NEW SCHEMA)
        print("\n" + "-" * 60)
        print("TRANSACTIONS TABLE (NEW SCHEMA)")
        print("-" * 60)
        transaction_cols = [col['name'] for col in inspector.get_columns('transactions')]
        print(f"Columns: {', '.join(transaction_cols)}")

        expected_transaction_cols = {'id', 'household_id', 'date', 'merchant', 'amount', 'currency', 'amount_in_usd', 'paid_by_user_id', 'category', 'notes', 'month_year', 'created_at'}
        if expected_transaction_cols.issubset(set(transaction_cols)):
            print("✓ Transaction table has all required columns (new schema)")
        else:
            print(f"✗ Missing columns: {expected_transaction_cols - set(transaction_cols)}")

        # Check for OLD columns that should be removed
        if 'paid_by' in transaction_cols:
            print("✗ WARNING: Old 'paid_by' column still exists (should be removed)")
        else:
            print("✓ Old 'paid_by' column removed")

        # Check Settlement table columns (NEW SCHEMA)
        print("\n" + "-" * 60)
        print("SETTLEMENTS TABLE (NEW SCHEMA)")
        print("-" * 60)
        settlement_cols = [col['name'] for col in inspector.get_columns('settlements')]
        print(f"Columns: {', '.join(settlement_cols)}")

        expected_settlement_cols = {'id', 'household_id', 'month_year', 'settled_date', 'settlement_amount', 'from_user_id', 'to_user_id', 'settlement_message', 'created_at'}
        if expected_settlement_cols.issubset(set(settlement_cols)):
            print("✓ Settlement table has all required columns (new schema)")
        else:
            print(f"✗ Missing columns: {expected_settlement_cols - set(settlement_cols)}")

        # Check for OLD columns that should be removed
        old_settlement_cols = {'from_person', 'to_person'}
        found_old_cols = old_settlement_cols.intersection(set(settlement_cols))
        if found_old_cols:
            print(f"✗ WARNING: Old columns still exist: {found_old_cols}")
        else:
            print("✓ Old 'from_person' and 'to_person' columns removed")

        # Check foreign keys
        print("\n" + "-" * 60)
        print("FOREIGN KEY CONSTRAINTS")
        print("-" * 60)

        transaction_fks = inspector.get_foreign_keys('transactions')
        print(f"Transaction foreign keys: {len(transaction_fks)}")
        for fk in transaction_fks:
            print(f"  - {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")

        settlement_fks = inspector.get_foreign_keys('settlements')
        print(f"\nSettlement foreign keys: {len(settlement_fks)}")
        for fk in settlement_fks:
            print(f"  - {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")

        # Check indexes
        print("\n" + "-" * 60)
        print("INDEXES")
        print("-" * 60)

        transaction_indexes = inspector.get_indexes('transactions')
        print(f"Transaction indexes: {len(transaction_indexes)}")
        for idx in transaction_indexes:
            print(f"  - {idx['name']}: {idx['column_names']}")

        print("\n" + "=" * 60)
        print("✅ SCHEMA VERIFICATION COMPLETE")
        print("=" * 60)

        return True


if __name__ == '__main__':
    try:
        success = test_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
