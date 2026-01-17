"""Seed test users for local development."""
from app import app, db
from models import User, Household, HouseholdMember
from datetime import datetime

with app.app_context():
    # Create or get test users
    alice = User.query.filter_by(email='test_alice@example.com').first()
    bob = User.query.filter_by(email='test_bob@example.com').first()

    if not alice:
        alice = User(email='test_alice@example.com', name='Test Alice')
        db.session.add(alice)
    if not bob:
        bob = User(email='test_bob@example.com', name='Test Bob')
        db.session.add(bob)

    alice.set_password('password123')
    bob.set_password('password123')
    db.session.commit()

    # Create shared household if they don't have one together
    existing = HouseholdMember.query.filter_by(user_id=alice.id).first()
    if not existing:
        household = Household(name='Test Household', created_by_user_id=alice.id)
        db.session.add(household)
        db.session.commit()

        db.session.add(HouseholdMember(
            user_id=alice.id, household_id=household.id,
            role='admin', display_name='Alice', joined_at=datetime.utcnow()
        ))
        db.session.add(HouseholdMember(
            user_id=bob.id, household_id=household.id,
            role='member', display_name='Bob', joined_at=datetime.utcnow()
        ))
        db.session.commit()
        print(f'Created Test Household (ID: {household.id})')

    print('Test users ready:')
    print('  test_alice@example.com / password123')
    print('  test_bob@example.com / password123')
