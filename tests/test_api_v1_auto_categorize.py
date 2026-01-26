"""
Tests for API v1 auto-categorize endpoint.

Tests:
- POST /api/v1/auto-categorize - Get suggested expense type for a merchant
"""
import pytest


@pytest.fixture
def api_client(app):
    """Create test client for API tests."""
    return app.test_client()


@pytest.fixture
def test_user(app, db):
    """Create a test user."""
    from models import User, RefreshToken
    with app.app_context():
        existing = User.query.filter_by(email='autocat_test@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='autocat_test@example.com',
            name='AutoCat Tester',
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

        user = User.query.filter_by(email='autocat_test@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_user2(app, db):
    """Create a second test user for budget rule tests."""
    from models import User, RefreshToken
    with app.app_context():
        existing = User.query.filter_by(email='autocat_test2@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='autocat_test2@example.com',
            name='AutoCat Tester 2',
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

        user = User.query.filter_by(email='autocat_test2@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_household_with_rules(app, db, test_user, test_user2):
    """Create a test household with expense types, auto-category rules, and budget rules."""
    from models import (
        Household, HouseholdMember, ExpenseType, AutoCategoryRule,
        BudgetRule, BudgetRuleExpenseType
    )
    from decimal import Decimal
    with app.app_context():
        household = Household(
            name='AutoCat Test Household',
            created_by_user_id=test_user['id']
        )
        db.session.add(household)
        db.session.flush()

        # Owner (member1)
        member1 = HouseholdMember(
            household_id=household.id,
            user_id=test_user['id'],
            role='owner',
            display_name='Owner'
        )
        db.session.add(member1)

        # Second member
        member2 = HouseholdMember(
            household_id=household.id,
            user_id=test_user2['id'],
            role='member',
            display_name='Partner'
        )
        db.session.add(member2)

        # Create expense types
        grocery_type = ExpenseType(
            household_id=household.id,
            name='Grocery',
            icon='cart',
            color='emerald'
        )
        db.session.add(grocery_type)

        coffee_type = ExpenseType(
            household_id=household.id,
            name='Coffee',
            icon='mug',
            color='brown'
        )
        db.session.add(coffee_type)
        db.session.flush()

        # Create auto-category rules
        rule1 = AutoCategoryRule(
            household_id=household.id,
            keyword='whole foods',
            expense_type_id=grocery_type.id,
            priority=10
        )
        db.session.add(rule1)

        rule2 = AutoCategoryRule(
            household_id=household.id,
            keyword='trader joe',
            expense_type_id=grocery_type.id,
            priority=5
        )
        db.session.add(rule2)

        rule3 = AutoCategoryRule(
            household_id=household.id,
            keyword='starbucks',
            expense_type_id=coffee_type.id,
            priority=10
        )
        db.session.add(rule3)

        # Budget rule: Owner (giver) gives Partner (receiver) for Grocery
        budget_rule = BudgetRule(
            household_id=household.id,
            giver_user_id=test_user['id'],
            receiver_user_id=test_user2['id'],
            monthly_amount=Decimal('500.00')
        )
        db.session.add(budget_rule)
        db.session.flush()

        budget_rule_et = BudgetRuleExpenseType(
            budget_rule_id=budget_rule.id,
            expense_type_id=grocery_type.id
        )
        db.session.add(budget_rule_et)

        db.session.commit()

        yield {
            'id': household.id,
            'name': household.name,
            'grocery_type_id': grocery_type.id,
            'coffee_type_id': coffee_type.id,
            'owner_user_id': test_user['id'],
            'partner_user_id': test_user2['id'],
        }

        # Cleanup
        BudgetRuleExpenseType.query.filter_by(budget_rule_id=budget_rule.id).delete()
        BudgetRule.query.filter_by(household_id=household.id).delete()
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


class TestAutoCategorize:
    """Tests for POST /api/v1/auto-categorize"""

    def test_auto_categorize_exact_match(self, api_client, test_user, test_household_with_rules):
        """Test auto-categorization with exact keyword match."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household_with_rules['id'])
            },
            json={
                'merchant': 'Whole Foods Market'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is not None
        assert data['expense_type']['name'] == 'Grocery'
        assert data['matched_rule'] is not None
        assert data['matched_rule']['keyword'] == 'whole foods'

    def test_auto_categorize_case_insensitive(self, api_client, test_user, test_household_with_rules):
        """Test auto-categorization is case insensitive."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household_with_rules['id'])
            },
            json={
                'merchant': 'STARBUCKS COFFEE'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is not None
        assert data['expense_type']['name'] == 'Coffee'

    def test_auto_categorize_partial_match(self, api_client, test_user, test_household_with_rules):
        """Test auto-categorization with partial match in merchant name."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household_with_rules['id'])
            },
            json={
                'merchant': "Trader Joe's #123 San Francisco"
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is not None
        assert data['expense_type']['name'] == 'Grocery'

    def test_auto_categorize_no_match(self, api_client, test_user, test_household_with_rules):
        """Test auto-categorization returns null when no match."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household_with_rules['id'])
            },
            json={
                'merchant': 'Unknown Store XYZ'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is None
        assert data['matched_rule'] is None

    def test_auto_categorize_empty_merchant(self, api_client, test_user, test_household_with_rules):
        """Test auto-categorization with empty merchant returns null."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household_with_rules['id'])
            },
            json={
                'merchant': '   '
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is None
        assert data['matched_rule'] is None

    def test_auto_categorize_no_body(self, api_client, test_user, test_household_with_rules):
        """Test auto-categorization with empty JSON body returns null."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household_with_rules['id'])
            },
            json={}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is None
        assert data['matched_rule'] is None

    def test_auto_categorize_requires_auth(self, api_client, test_household_with_rules):
        """Test auto-categorization requires authentication."""
        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'X-Household-ID': str(test_household_with_rules['id'])
            },
            json={
                'merchant': 'Whole Foods'
            }
        )

        assert response.status_code == 401

    def test_auto_categorize_with_paid_by_giver(self, api_client, test_user, test_household_with_rules):
        """Giver paid for grocery → I_PAY_FOR_WIFE (receiver is not owner)."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        h = test_household_with_rules

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(h['id'])
            },
            json={
                'merchant': 'Whole Foods Market',
                'paid_by_user_id': h['owner_user_id']  # owner is giver
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is not None
        assert data['expense_type']['name'] == 'Grocery'
        # Owner(giver) paid, receiver is partner(not owner) → I_PAY_FOR_WIFE
        assert data['category'] == 'I_PAY_FOR_WIFE'

    def test_auto_categorize_with_paid_by_receiver(self, api_client, test_user, test_household_with_rules):
        """Receiver paid for grocery → PERSONAL_WIFE (receiver is not owner)."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        h = test_household_with_rules

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(h['id'])
            },
            json={
                'merchant': 'Whole Foods Market',
                'paid_by_user_id': h['partner_user_id']  # partner is receiver
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is not None
        assert data['expense_type']['name'] == 'Grocery'
        # Partner(receiver) paid, receiver is not owner → PERSONAL_WIFE
        assert data['category'] == 'PERSONAL_WIFE'

    def test_budget_category_by_expense_type_id(self, api_client, test_user, test_household_with_rules):
        """Provide expense_type_id + paid_by_user_id (no merchant) → correct category."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        h = test_household_with_rules

        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(h['id'])
            },
            json={
                'expense_type_id': h['grocery_type_id'],
                'paid_by_user_id': h['owner_user_id']
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is not None
        assert data['expense_type']['name'] == 'Grocery'
        assert data['category'] == 'I_PAY_FOR_WIFE'
        # No merchant provided, so no matched_rule
        assert data['matched_rule'] is None

    def test_auto_categorize_defaults_paid_by_to_jwt_user(self, api_client, test_user, test_household_with_rules):
        """Merchant-only request defaults paid_by_user_id to JWT user, enabling budget lookup."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        h = test_household_with_rules

        # Send only merchant — no paid_by_user_id
        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(h['id'])
            },
            json={
                'merchant': 'Whole Foods Market'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type']['name'] == 'Grocery'
        assert data['matched_rule']['keyword'] == 'whole foods'
        # JWT user is owner (giver in budget rule) → I_PAY_FOR_WIFE
        assert data['category'] == 'I_PAY_FOR_WIFE'

    def test_no_budget_rule_no_category_override(self, api_client, test_user, test_household_with_rules):
        """Expense type without budget rule → static rule category or null."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        h = test_household_with_rules

        # Coffee has no budget rule
        response = api_client.post(
            '/api/v1/auto-categorize',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(h['id'])
            },
            json={
                'expense_type_id': h['coffee_type_id'],
                'paid_by_user_id': h['owner_user_id']
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type'] is not None
        assert data['expense_type']['name'] == 'Coffee'
        # No budget rule for coffee → category should be None
        assert data['category'] is None
