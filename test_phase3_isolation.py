#!/usr/bin/env python3
"""
Phase 3 Data Isolation Testing
Tests that household data is completely isolated and secure.
"""
import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import User, Household, HouseholdMember, Transaction, Settlement
from utils import calculate_reconciliation


def setup_test_data():
    """Create test households and users for isolation testing."""
    print("\n" + "=" * 70)
    print("SETTING UP TEST DATA")
    print("=" * 70)

    with app.app_context():
        # Clean up existing test data
        print("\n🧹 Cleaning up old test data...")
        User.query.filter(User.email.like('test%@example.com')).delete()
        db.session.commit()

        # Create User 1 (Alice)
        print("\n👤 Creating User 1: Alice")
        alice = User(email='testalice@example.com', name='Alice Smith')
        alice.set_password('password123')
        db.session.add(alice)
        db.session.commit()
        print(f"   ✓ Created user: {alice.name} (ID: {alice.id})")

        # Create User 2 (Bob)
        print("\n👤 Creating User 2: Bob")
        bob = User(email='testbob@example.com', name='Bob Johnson')
        bob.set_password('password123')
        db.session.add(bob)
        db.session.commit()
        print(f"   ✓ Created user: {bob.name} (ID: {bob.id})")

        # Create User 3 (Charlie)
        print("\n👤 Creating User 3: Charlie")
        charlie = User(email='testcharlie@example.com', name='Charlie Davis')
        charlie.set_password('password123')
        db.session.add(charlie)
        db.session.commit()
        print(f"   ✓ Created user: {charlie.name} (ID: {charlie.id})")

        # Create User 4 (Diana)
        print("\n👤 Creating User 4: Diana")
        diana = User(email='testdiana@example.com', name='Diana Lee')
        diana.set_password('password123')
        db.session.add(diana)
        db.session.commit()
        print(f"   ✓ Created user: {diana.name} (ID: {diana.id})")

        # Create Household 1 (Alice & Bob)
        print("\n🏠 Creating Household 1: 'Alice & Bob Household'")
        household1 = Household(
            name='Alice & Bob Household',
            created_by_user_id=alice.id
        )
        db.session.add(household1)
        db.session.commit()
        print(f"   ✓ Created household ID: {household1.id}")

        # Add Alice to Household 1
        member1_alice = HouseholdMember(
            household_id=household1.id,
            user_id=alice.id,
            role='owner',
            display_name='Alice'
        )
        db.session.add(member1_alice)

        # Add Bob to Household 1
        member1_bob = HouseholdMember(
            household_id=household1.id,
            user_id=bob.id,
            role='member',
            display_name='Bob'
        )
        db.session.add(member1_bob)
        db.session.commit()
        print(f"   ✓ Added members: Alice (owner), Bob (member)")

        # Create Household 2 (Charlie & Diana)
        print("\n🏠 Creating Household 2: 'Charlie & Diana Household'")
        household2 = Household(
            name='Charlie & Diana Household',
            created_by_user_id=charlie.id
        )
        db.session.add(household2)
        db.session.commit()
        print(f"   ✓ Created household ID: {household2.id}")

        # Add Charlie to Household 2
        member2_charlie = HouseholdMember(
            household_id=household2.id,
            user_id=charlie.id,
            role='owner',
            display_name='Charlie'
        )
        db.session.add(member2_charlie)

        # Add Diana to Household 2
        member2_diana = HouseholdMember(
            household_id=household2.id,
            user_id=diana.id,
            role='member',
            display_name='Diana'
        )
        db.session.add(member2_diana)
        db.session.commit()
        print(f"   ✓ Added members: Charlie (owner), Diana (member)")

        # Create transactions for Household 1
        print("\n💰 Creating transactions for Household 1...")
        txn1_h1 = Transaction(
            household_id=household1.id,
            date=date.today(),
            merchant='Grocery Store',
            amount=Decimal('150.00'),
            currency='USD',
            amount_in_usd=Decimal('150.00'),
            paid_by_user_id=alice.id,
            category='SHARED',
            notes='Weekly groceries',
            month_year=date.today().strftime('%Y-%m')
        )
        db.session.add(txn1_h1)

        txn2_h1 = Transaction(
            household_id=household1.id,
            date=date.today(),
            merchant='Restaurant',
            amount=Decimal('80.00'),
            currency='USD',
            amount_in_usd=Decimal('80.00'),
            paid_by_user_id=bob.id,
            category='SHARED',
            notes='Dinner out',
            month_year=date.today().strftime('%Y-%m')
        )
        db.session.add(txn2_h1)
        db.session.commit()
        print(f"   ✓ Created 2 transactions for Household 1")

        # Create transactions for Household 2
        print("\n💰 Creating transactions for Household 2...")
        txn1_h2 = Transaction(
            household_id=household2.id,
            date=date.today(),
            merchant='Electronics Store',
            amount=Decimal('500.00'),
            currency='USD',
            amount_in_usd=Decimal('500.00'),
            paid_by_user_id=charlie.id,
            category='SHARED',
            notes='New laptop',
            month_year=date.today().strftime('%Y-%m')
        )
        db.session.add(txn1_h2)

        txn2_h2 = Transaction(
            household_id=household2.id,
            date=date.today(),
            merchant='Gas Station',
            amount=Decimal('60.00'),
            currency='USD',
            amount_in_usd=Decimal('60.00'),
            paid_by_user_id=diana.id,
            category='SHARED',
            notes='Fill up car',
            month_year=date.today().strftime('%Y-%m')
        )
        db.session.add(txn2_h2)
        db.session.commit()
        print(f"   ✓ Created 2 transactions for Household 2")

        print("\n✅ Test data setup complete!")
        return household1.id, household2.id, alice.id, bob.id, charlie.id, diana.id


def test_data_isolation():
    """Test that household data is completely isolated."""
    print("\n" + "=" * 70)
    print("DATA ISOLATION TESTS")
    print("=" * 70)

    h1_id, h2_id, alice_id, bob_id, charlie_id, diana_id = setup_test_data()

    with app.app_context():
        print("\n📊 Test 1: Transaction Isolation")
        print("-" * 70)

        # Query transactions for Household 1
        h1_transactions = Transaction.query.filter_by(household_id=h1_id).all()
        print(f"   Household 1 has {len(h1_transactions)} transactions")
        for txn in h1_transactions:
            print(f"      - {txn.merchant}: ${txn.amount_in_usd}")

        # Query transactions for Household 2
        h2_transactions = Transaction.query.filter_by(household_id=h2_id).all()
        print(f"   Household 2 has {len(h2_transactions)} transactions")
        for txn in h2_transactions:
            print(f"      - {txn.merchant}: ${txn.amount_in_usd}")

        # Verify isolation
        if len(h1_transactions) == 2 and len(h2_transactions) == 2:
            print("   ✅ PASS: Each household has correct number of transactions")
        else:
            print("   ❌ FAIL: Transaction counts incorrect")
            return False

        # Verify no cross-contamination
        h1_merchants = {txn.merchant for txn in h1_transactions}
        h2_merchants = {txn.merchant for txn in h2_transactions}

        if not h1_merchants.intersection(h2_merchants):
            print("   ✅ PASS: No transaction overlap between households")
        else:
            print("   ❌ FAIL: Transactions leaked between households!")
            return False

        print("\n📊 Test 2: Settlement Isolation")
        print("-" * 70)

        # Create settlement for Household 1
        month_year = date.today().strftime('%Y-%m')
        h1_members = HouseholdMember.query.filter_by(household_id=h1_id).all()
        h1_summary = calculate_reconciliation(h1_transactions, h1_members)

        settlement1 = Settlement(
            household_id=h1_id,
            month_year=month_year,
            settled_date=date.today(),
            settlement_amount=Decimal('50.00'),
            from_user_id=bob_id,
            to_user_id=alice_id,
            settlement_message=h1_summary['settlement']
        )
        db.session.add(settlement1)
        db.session.commit()
        print(f"   ✓ Created settlement for Household 1: {settlement1.settlement_message}")

        # Try to query settlement from Household 2's perspective (should find nothing)
        h2_settlement = Settlement.query.filter_by(
            household_id=h2_id,
            month_year=month_year
        ).first()

        if h2_settlement is None:
            print("   ✅ PASS: Household 2 cannot see Household 1's settlement")
        else:
            print("   ❌ FAIL: Settlement leaked between households!")
            return False

        # Query settlement from Household 1's perspective (should find it)
        h1_settlement = Settlement.query.filter_by(
            household_id=h1_id,
            month_year=month_year
        ).first()

        if h1_settlement is not None:
            print("   ✅ PASS: Household 1 can see its own settlement")
        else:
            print("   ❌ FAIL: Household 1 cannot find its own settlement!")
            return False

        print("\n📊 Test 3: Ownership Verification (Update/Delete)")
        print("-" * 70)

        # Get a transaction from Household 1
        h1_txn = h1_transactions[0]

        # Try to query it with Household 2's ID (should return None)
        wrong_household_query = Transaction.query.filter_by(
            id=h1_txn.id,
            household_id=h2_id
        ).first()

        if wrong_household_query is None:
            print("   ✅ PASS: Cannot query Household 1 transaction with Household 2 ID")
        else:
            print("   ❌ FAIL: Transaction leaked across household boundary!")
            return False

        # Query it with correct Household 1 ID (should succeed)
        correct_household_query = Transaction.query.filter_by(
            id=h1_txn.id,
            household_id=h1_id
        ).first()

        if correct_household_query is not None:
            print("   ✅ PASS: Can query transaction with correct household ID")
        else:
            print("   ❌ FAIL: Cannot query transaction with correct household ID!")
            return False

        print("\n📊 Test 4: Reconciliation Calculation")
        print("-" * 70)

        # Calculate reconciliation for Household 1
        h1_members = HouseholdMember.query.filter_by(household_id=h1_id).all()
        h1_summary = calculate_reconciliation(h1_transactions, h1_members)

        print(f"   Household 1 summary:")
        print(f"      Settlement: {h1_summary['settlement']}")
        print(f"      Member names: {h1_summary['member_names']}")
        print(f"      User balances: {h1_summary['user_balances']}")

        if 'Alice' in h1_summary['member_names'].values() and 'Bob' in h1_summary['member_names'].values():
            print("   ✅ PASS: Reconciliation uses correct member names")
        else:
            print("   ❌ FAIL: Member names incorrect in reconciliation")
            return False

        # Calculate reconciliation for Household 2
        h2_members = HouseholdMember.query.filter_by(household_id=h2_id).all()
        h2_summary = calculate_reconciliation(h2_transactions, h2_members)

        print(f"\n   Household 2 summary:")
        print(f"      Settlement: {h2_summary['settlement']}")
        print(f"      Member names: {h2_summary['member_names']}")
        print(f"      User balances: {h2_summary['user_balances']}")

        if 'Charlie' in h2_summary['member_names'].values() and 'Diana' in h2_summary['member_names'].values():
            print("   ✅ PASS: Reconciliation uses correct member names")
        else:
            print("   ❌ FAIL: Member names incorrect in reconciliation")
            return False

        print("\n📊 Test 5: Month Filtering")
        print("-" * 70)

        # Get distinct months for Household 1
        h1_months = db.session.query(Transaction.month_year).distinct().filter(
            Transaction.household_id == h1_id
        ).all()

        # Get distinct months for Household 2
        h2_months = db.session.query(Transaction.month_year).distinct().filter(
            Transaction.household_id == h2_id
        ).all()

        print(f"   Household 1 months: {[m[0] for m in h1_months]}")
        print(f"   Household 2 months: {[m[0] for m in h2_months]}")

        if len(h1_months) > 0 and len(h2_months) > 0:
            print("   ✅ PASS: Month filtering works for both households")
        else:
            print("   ❌ FAIL: Month filtering failed")
            return False

        print("\n" + "=" * 70)
        print("✅ ALL DATA ISOLATION TESTS PASSED!")
        print("=" * 70)

        print("\n📝 Test Users Created:")
        print(f"   Alice:   email=testalice@example.com   password=password123")
        print(f"   Bob:     email=testbob@example.com     password=password123")
        print(f"   Charlie: email=testcharlie@example.com password=password123")
        print(f"   Diana:   email=testdiana@example.com   password=password123")

        print("\n🏠 Test Households:")
        print(f"   Household 1 (ID {h1_id}): Alice & Bob")
        print(f"   Household 2 (ID {h2_id}): Charlie & Diana")

        return True


if __name__ == '__main__':
    try:
        success = test_data_isolation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
