"""Seed test users and sample data for local development."""
from app import app
from extensions import db
from models import (
    User, Household, HouseholdMember, Transaction, ExpenseType,
    AutoCategoryRule, SplitRule, SplitRuleExpenseType, BudgetRule, BudgetRuleExpenseType
)
from datetime import datetime, date
from decimal import Decimal

with app.app_context():
    # Ensure tables exist
    db.create_all()
    print("Database tables created (if not already existing)")

    # ===== 1. CREATE DEMO USERS =====
    # Using 'demo_' prefix to avoid conflict with test cleanup (which deletes 'test_%' users)
    alice = User.query.filter_by(email='demo_alice@example.com').first()
    bob = User.query.filter_by(email='demo_bob@example.com').first()

    if not alice:
        alice = User(email='demo_alice@example.com', name='Demo Alice')
        db.session.add(alice)
    if not bob:
        bob = User(email='demo_bob@example.com', name='Demo Bob')
        db.session.add(bob)

    alice.set_password('password123')
    bob.set_password('password123')
    db.session.commit()

    # ===== 2. CREATE HOUSEHOLD =====
    existing = HouseholdMember.query.filter_by(user_id=alice.id).first()
    if not existing:
        household = Household(name='Demo Household', created_by_user_id=alice.id)
        db.session.add(household)
        db.session.commit()

        db.session.add(HouseholdMember(
            user_id=alice.id, household_id=household.id,
            role='owner', display_name='Alice', joined_at=datetime.utcnow()
        ))
        db.session.add(HouseholdMember(
            user_id=bob.id, household_id=household.id,
            role='member', display_name='Bob', joined_at=datetime.utcnow()
        ))
        db.session.commit()
        print(f'Created Demo Household (ID: {household.id})')
    else:
        household = existing.household
        print(f'Using existing Demo Household (ID: {household.id})')

    household_id = household.id
    alice_user_id = alice.id
    bob_user_id = bob.id

    # ===== 3. EXPENSE CATEGORIES =====
    existing_types = ExpenseType.query.filter_by(household_id=household_id).count()
    if existing_types == 0:
        expense_types = [
            {"name": "Grocery", "icon": "cat-cart", "color": "sage"},
            {"name": "Dining", "icon": "cat-food", "color": "terracotta"},
            {"name": "Utilities", "icon": "cat-lightbulb", "color": "amber"},
            {"name": "Transportation", "icon": "cat-car", "color": "warm"},
            {"name": "Entertainment", "icon": "cat-happy", "color": "rose"},
            {"name": "Healthcare", "icon": "cat-heart", "color": "sage"},
            {"name": "Shopping", "icon": "cat-bag", "color": "terracotta"},
            {"name": "Subscriptions", "icon": "cat-repeat", "color": "amber"},
        ]
        for et in expense_types:
            db.session.add(ExpenseType(
                household_id=household_id,
                name=et["name"],
                icon=et["icon"],
                color=et["color"]
            ))
        db.session.commit()
        print(f'Created {len(expense_types)} expense categories')

    # Get expense type IDs
    expense_type_map = {et.name: et.id for et in ExpenseType.query.filter_by(household_id=household_id).all()}

    # ===== 4. AUTO-CATEGORIZATION RULES =====
    existing_rules = AutoCategoryRule.query.filter_by(household_id=household_id).count()
    if existing_rules == 0:
        auto_rules = [
            # Grocery
            {"keyword": "whole foods", "expense_type": "Grocery", "priority": 10},
            {"keyword": "trader joe", "expense_type": "Grocery", "priority": 10},
            {"keyword": "costco", "expense_type": "Grocery", "priority": 10},
            {"keyword": "safeway", "expense_type": "Grocery", "priority": 10},
            {"keyword": "kroger", "expense_type": "Grocery", "priority": 10},
            {"keyword": "walmart", "expense_type": "Grocery", "priority": 5},
            {"keyword": "target", "expense_type": "Grocery", "priority": 5},
            # Dining
            {"keyword": "restaurant", "expense_type": "Dining", "priority": 10},
            {"keyword": "doordash", "expense_type": "Dining", "priority": 10},
            {"keyword": "uber eats", "expense_type": "Dining", "priority": 10},
            {"keyword": "grubhub", "expense_type": "Dining", "priority": 10},
            {"keyword": "starbucks", "expense_type": "Dining", "priority": 10},
            {"keyword": "mcdonald", "expense_type": "Dining", "priority": 10},
            {"keyword": "chipotle", "expense_type": "Dining", "priority": 10},
            # Utilities
            {"keyword": "electric", "expense_type": "Utilities", "priority": 10},
            {"keyword": "pg&e", "expense_type": "Utilities", "priority": 10},
            {"keyword": "water bill", "expense_type": "Utilities", "priority": 10},
            {"keyword": "gas bill", "expense_type": "Utilities", "priority": 10},
            {"keyword": "internet", "expense_type": "Utilities", "priority": 10},
            {"keyword": "comcast", "expense_type": "Utilities", "priority": 10},
            {"keyword": "at&t", "expense_type": "Utilities", "priority": 10},
            # Transportation
            {"keyword": "gas station", "expense_type": "Transportation", "priority": 10},
            {"keyword": "shell", "expense_type": "Transportation", "priority": 10},
            {"keyword": "chevron", "expense_type": "Transportation", "priority": 10},
            {"keyword": "uber", "expense_type": "Transportation", "priority": 5},
            {"keyword": "lyft", "expense_type": "Transportation", "priority": 10},
            {"keyword": "parking", "expense_type": "Transportation", "priority": 10},
            # Entertainment
            {"keyword": "movie", "expense_type": "Entertainment", "priority": 10},
            {"keyword": "theater", "expense_type": "Entertainment", "priority": 10},
            {"keyword": "concert", "expense_type": "Entertainment", "priority": 10},
            {"keyword": "spotify", "expense_type": "Entertainment", "priority": 10},
            # Healthcare
            {"keyword": "pharmacy", "expense_type": "Healthcare", "priority": 10},
            {"keyword": "cvs", "expense_type": "Healthcare", "priority": 10},
            {"keyword": "walgreens", "expense_type": "Healthcare", "priority": 10},
            {"keyword": "doctor", "expense_type": "Healthcare", "priority": 10},
            {"keyword": "hospital", "expense_type": "Healthcare", "priority": 10},
            # Subscriptions
            {"keyword": "netflix", "expense_type": "Subscriptions", "priority": 10},
            {"keyword": "hulu", "expense_type": "Subscriptions", "priority": 10},
            {"keyword": "disney+", "expense_type": "Subscriptions", "priority": 10},
            {"keyword": "amazon prime", "expense_type": "Subscriptions", "priority": 10},
            {"keyword": "youtube", "expense_type": "Subscriptions", "priority": 10},
        ]
        for rule in auto_rules:
            if rule["expense_type"] in expense_type_map:
                db.session.add(AutoCategoryRule(
                    household_id=household_id,
                    keyword=rule["keyword"],
                    expense_type_id=expense_type_map[rule["expense_type"]],
                    priority=rule["priority"]
                ))
        db.session.commit()
        print(f'Created {len(auto_rules)} auto-categorization rules')

    # ===== 5. SPLIT RULES =====
    existing_splits = SplitRule.query.filter_by(household_id=household_id).count()
    if existing_splits == 0:
        # Default 50/50 split
        default_split = SplitRule(
            household_id=household_id,
            member1_percent=50,
            member2_percent=50,
            is_default=True
        )
        db.session.add(default_split)
        db.session.flush()

        # Grocery: 60/40 (Alice pays more)
        grocery_split = SplitRule(
            household_id=household_id,
            member1_percent=60,
            member2_percent=40,
            is_default=False
        )
        db.session.add(grocery_split)
        db.session.flush()
        db.session.add(SplitRuleExpenseType(
            split_rule_id=grocery_split.id,
            expense_type_id=expense_type_map["Grocery"]
        ))

        # Dining: 40/60 (Bob pays more)
        dining_split = SplitRule(
            household_id=household_id,
            member1_percent=40,
            member2_percent=60,
            is_default=False
        )
        db.session.add(dining_split)
        db.session.flush()
        db.session.add(SplitRuleExpenseType(
            split_rule_id=dining_split.id,
            expense_type_id=expense_type_map["Dining"]
        ))

        db.session.commit()
        print('Created 3 split rules (default 50/50, Grocery 60/40, Dining 40/60)')

    # ===== 6. BUDGET RULES =====
    existing_budgets = BudgetRule.query.filter_by(household_id=household_id).count()
    if existing_budgets == 0:
        # Alice gives Bob $500/month for Grocery
        grocery_budget = BudgetRule(
            household_id=household_id,
            giver_user_id=alice_user_id,
            receiver_user_id=bob_user_id,
            monthly_amount=Decimal("500.00")
        )
        db.session.add(grocery_budget)
        db.session.flush()
        db.session.add(BudgetRuleExpenseType(
            budget_rule_id=grocery_budget.id,
            expense_type_id=expense_type_map["Grocery"]
        ))

        # Bob gives Alice $200/month for Entertainment + Subscriptions
        entertainment_budget = BudgetRule(
            household_id=household_id,
            giver_user_id=bob_user_id,
            receiver_user_id=alice_user_id,
            monthly_amount=Decimal("200.00")
        )
        db.session.add(entertainment_budget)
        db.session.flush()
        db.session.add(BudgetRuleExpenseType(
            budget_rule_id=entertainment_budget.id,
            expense_type_id=expense_type_map["Entertainment"]
        ))
        db.session.add(BudgetRuleExpenseType(
            budget_rule_id=entertainment_budget.id,
            expense_type_id=expense_type_map["Subscriptions"]
        ))

        db.session.commit()
        print('Created 2 budget rules (Grocery $500, Entertainment+Subscriptions $200)')

    # ===== 7. TEST TRANSACTIONS =====
    existing_txns = Transaction.query.filter_by(household_id=household_id).count()
    if existing_txns == 0:
        transactions = [
            # January 2026 transactions
            {"date": date(2026, 1, 2), "merchant": "Whole Foods", "amount": 125.50, "paid_by": alice_user_id, "category": "SHARED", "expense_type": "Grocery"},
            {"date": date(2026, 1, 3), "merchant": "Netflix", "amount": 15.99, "paid_by": bob_user_id, "category": "SHARED", "expense_type": "Subscriptions"},
            {"date": date(2026, 1, 5), "merchant": "Shell Gas Station", "amount": 45.00, "paid_by": alice_user_id, "category": "SHARED", "expense_type": "Transportation"},
            {"date": date(2026, 1, 7), "merchant": "Costco", "amount": 210.75, "paid_by": bob_user_id, "category": "SHARED", "expense_type": "Grocery"},
            {"date": date(2026, 1, 8), "merchant": "PG&E Electric Bill", "amount": 89.00, "paid_by": alice_user_id, "category": "SHARED", "expense_type": "Utilities"},
            {"date": date(2026, 1, 10), "merchant": "Trader Joe's", "amount": 67.30, "paid_by": bob_user_id, "category": "SHARED", "expense_type": "Grocery"},
            {"date": date(2026, 1, 11), "merchant": "Chipotle", "amount": 24.50, "paid_by": alice_user_id, "category": "SHARED", "expense_type": "Dining"},
            {"date": date(2026, 1, 12), "merchant": "Spotify Premium", "amount": 10.99, "paid_by": alice_user_id, "category": "SHARED", "expense_type": "Subscriptions"},
            {"date": date(2026, 1, 14), "merchant": "CVS Pharmacy", "amount": 32.45, "paid_by": bob_user_id, "category": "SHARED", "expense_type": "Healthcare"},
            {"date": date(2026, 1, 15), "merchant": "Comcast Internet", "amount": 79.99, "paid_by": alice_user_id, "category": "SHARED", "expense_type": "Utilities"},
            {"date": date(2026, 1, 16), "merchant": "Movie Theater", "amount": 28.00, "paid_by": bob_user_id, "category": "SHARED", "expense_type": "Entertainment"},
            {"date": date(2026, 1, 17), "merchant": "Safeway", "amount": 95.20, "paid_by": alice_user_id, "category": "SHARED", "expense_type": "Grocery"},
            {"date": date(2026, 1, 18), "merchant": "Uber Ride", "amount": 18.50, "paid_by": bob_user_id, "category": "SHARED", "expense_type": "Transportation"},
            # Personal transactions
            {"date": date(2026, 1, 9), "merchant": "Alice's Haircut", "amount": 65.00, "paid_by": alice_user_id, "category": "PERSONAL_ME", "expense_type": None, "notes": "Personal expense"},
            {"date": date(2026, 1, 13), "merchant": "Bob's Golf", "amount": 80.00, "paid_by": bob_user_id, "category": "PERSONAL_WIFE", "expense_type": None, "notes": "Personal expense"},
        ]

        for t in transactions:
            month_year = t["date"].strftime("%Y-%m")
            expense_type_id = expense_type_map.get(t.get("expense_type")) if t.get("expense_type") else None
            txn = Transaction(
                household_id=household_id,
                date=t["date"],
                merchant=t["merchant"],
                amount=Decimal(str(t["amount"])),
                currency="USD",
                amount_in_usd=Decimal(str(t["amount"])),
                paid_by_user_id=t["paid_by"],
                category=t["category"],
                expense_type_id=expense_type_id,
                notes=t.get("notes"),
                month_year=month_year
            )
            db.session.add(txn)

        db.session.commit()
        print(f'Created {len(transactions)} test transactions')

    print('\nDemo data ready:')
    print('  demo_alice@example.com / password123')
    print('  demo_bob@example.com / password123')
