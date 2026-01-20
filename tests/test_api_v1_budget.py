"""
Tests for API v1 budget and split rules endpoints.

Tests:
- GET /api/v1/budget-rules - List budget rules
- POST /api/v1/budget-rules - Create budget rule
- PUT /api/v1/budget-rules/<id> - Update budget rule
- DELETE /api/v1/budget-rules/<id> - Delete budget rule
- POST /api/v1/split-rules - Create split rule
- PUT /api/v1/split-rules/<id> - Update split rule
- DELETE /api/v1/split-rules/<id> - Delete split rule
"""
import pytest
from decimal import Decimal


@pytest.fixture
def api_client(app):
    """Create test client for API tests."""
    return app.test_client()


@pytest.fixture
def owner_user(app, db):
    """Create an owner user for budget tests."""
    from models import User, RefreshToken
    with app.app_context():
        existing = User.query.filter_by(email='budget_owner@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='budget_owner@example.com',
            name='Budget Owner',
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

        user = User.query.filter_by(email='budget_owner@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def member_user(app, db):
    """Create a member user for budget tests."""
    from models import User, RefreshToken
    with app.app_context():
        existing = User.query.filter_by(email='budget_member@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='budget_member@example.com',
            name='Budget Member',
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

        user = User.query.filter_by(email='budget_member@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_household(app, db, owner_user, member_user):
    """Create a test household with owner and member."""
    from models import Household, HouseholdMember, ExpenseType
    with app.app_context():
        household = Household(
            name='Budget Test Household',
            created_by_user_id=owner_user['id']
        )
        db.session.add(household)
        db.session.flush()

        owner_member = HouseholdMember(
            household_id=household.id,
            user_id=owner_user['id'],
            role='owner',
            display_name='Owner'
        )
        db.session.add(owner_member)

        other_member = HouseholdMember(
            household_id=household.id,
            user_id=member_user['id'],
            role='member',
            display_name='Member'
        )
        db.session.add(other_member)

        # Create expense types
        expense_type1 = ExpenseType(
            household_id=household.id,
            name='Grocery',
            icon='cart',
            color='green'
        )
        expense_type2 = ExpenseType(
            household_id=household.id,
            name='Dining',
            icon='utensils',
            color='orange'
        )
        db.session.add(expense_type1)
        db.session.add(expense_type2)
        db.session.commit()

        yield {
            'id': household.id,
            'name': household.name,
            'owner_id': owner_user['id'],
            'member_id': member_user['id'],
            'expense_type_ids': [expense_type1.id, expense_type2.id]
        }

        # Cleanup
        from models import BudgetRule, BudgetRuleExpenseType, SplitRule, SplitRuleExpenseType
        BudgetRuleExpenseType.query.filter(
            BudgetRuleExpenseType.budget_rule_id.in_(
                db.session.query(BudgetRule.id).filter_by(household_id=household.id)
            )
        ).delete(synchronize_session='fetch')
        BudgetRule.query.filter_by(household_id=household.id).delete()
        SplitRuleExpenseType.query.filter(
            SplitRuleExpenseType.split_rule_id.in_(
                db.session.query(SplitRule.id).filter_by(household_id=household.id)
            )
        ).delete(synchronize_session='fetch')
        SplitRule.query.filter_by(household_id=household.id).delete()
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


class TestBudgetRulesList:
    """Tests for GET /api/v1/budget-rules"""

    def test_list_budget_rules_empty(self, api_client, owner_user, test_household):
        """Test listing budget rules when none exist."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.get(
            '/api/v1/budget-rules',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'budget_rules' in data
        assert len(data['budget_rules']) == 0


class TestCreateBudgetRule:
    """Tests for POST /api/v1/budget-rules"""

    def test_create_budget_rule_success(self, api_client, owner_user, test_household, app):
        """Test successful budget rule creation."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.post(
            '/api/v1/budget-rules',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'giver_user_id': test_household['owner_id'],
                'receiver_user_id': test_household['member_id'],
                'monthly_amount': 500.00,
                'expense_type_ids': [test_household['expense_type_ids'][0]]
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'budget_rule' in data
        assert data['budget_rule']['monthly_amount'] == 500.00

    def test_create_budget_rule_missing_expense_types(self, api_client, owner_user, test_household):
        """Test creating budget rule without expense types fails."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.post(
            '/api/v1/budget-rules',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'giver_user_id': test_household['owner_id'],
                'receiver_user_id': test_household['member_id'],
                'monthly_amount': 500.00,
                'expense_type_ids': []
            }
        )

        assert response.status_code == 400
        assert 'expense type' in response.get_json()['error'].lower()

    def test_create_budget_rule_same_giver_receiver(self, api_client, owner_user, test_household):
        """Test creating budget rule with same giver/receiver fails."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.post(
            '/api/v1/budget-rules',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'giver_user_id': test_household['owner_id'],
                'receiver_user_id': test_household['owner_id'],
                'monthly_amount': 500.00,
                'expense_type_ids': [test_household['expense_type_ids'][0]]
            }
        )

        assert response.status_code == 400
        assert 'different' in response.get_json()['error'].lower()


class TestUpdateBudgetRule:
    """Tests for PUT /api/v1/budget-rules/<id>"""

    def test_update_budget_rule_amount(self, api_client, owner_user, test_household, app, db):
        """Test updating budget rule amount."""
        from models import BudgetRule, BudgetRuleExpenseType

        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        # Create a budget rule first
        with app.app_context():
            rule = BudgetRule(
                household_id=test_household['id'],
                giver_user_id=test_household['owner_id'],
                receiver_user_id=test_household['member_id'],
                monthly_amount=Decimal('500.00')
            )
            db.session.add(rule)
            db.session.flush()

            assoc = BudgetRuleExpenseType(
                budget_rule_id=rule.id,
                expense_type_id=test_household['expense_type_ids'][0]
            )
            db.session.add(assoc)
            db.session.commit()
            rule_id = rule.id

        response = api_client.put(
            f'/api/v1/budget-rules/{rule_id}',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'monthly_amount': 750.00
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['budget_rule']['monthly_amount'] == 750.00


class TestDeleteBudgetRule:
    """Tests for DELETE /api/v1/budget-rules/<id>"""

    def test_delete_budget_rule_success(self, api_client, owner_user, test_household, app, db):
        """Test soft-deleting a budget rule."""
        from models import BudgetRule, BudgetRuleExpenseType

        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        # Create a budget rule first
        with app.app_context():
            rule = BudgetRule(
                household_id=test_household['id'],
                giver_user_id=test_household['owner_id'],
                receiver_user_id=test_household['member_id'],
                monthly_amount=Decimal('500.00')
            )
            db.session.add(rule)
            db.session.flush()

            assoc = BudgetRuleExpenseType(
                budget_rule_id=rule.id,
                expense_type_id=test_household['expense_type_ids'][0]
            )
            db.session.add(assoc)
            db.session.commit()
            rule_id = rule.id

        response = api_client.delete(
            f'/api/v1/budget-rules/{rule_id}',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        assert response.get_json()['success'] is True

        # Verify soft deleted
        with app.app_context():
            rule = BudgetRule.query.get(rule_id)
            assert rule.is_active is False


class TestCreateSplitRule:
    """Tests for POST /api/v1/split-rules"""

    def test_create_split_rule_success(self, api_client, owner_user, test_household):
        """Test successful split rule creation."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.post(
            '/api/v1/split-rules',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'member1_percent': 60,
                'member2_percent': 40,
                'is_default': False,
                'expense_type_ids': [test_household['expense_type_ids'][0]]
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'split_rule' in data
        assert data['split_rule']['member1_percent'] == 60
        assert data['split_rule']['member2_percent'] == 40

    def test_create_default_split_rule(self, api_client, owner_user, test_household):
        """Test creating a default split rule."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.post(
            '/api/v1/split-rules',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'member1_percent': 50,
                'member2_percent': 50,
                'is_default': True,
                'expense_type_ids': []
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['split_rule']['is_default'] is True

    def test_create_split_rule_invalid_percentages(self, api_client, owner_user, test_household):
        """Test creating split rule with percentages not summing to 100."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.post(
            '/api/v1/split-rules',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'member1_percent': 60,
                'member2_percent': 60,
                'is_default': False,
                'expense_type_ids': [test_household['expense_type_ids'][0]]
            }
        )

        assert response.status_code == 400
        assert '100' in response.get_json()['error']


class TestUpdateSplitRule:
    """Tests for PUT /api/v1/split-rules/<id>"""

    def test_update_split_rule_percentages(self, api_client, owner_user, test_household, app, db):
        """Test updating split rule percentages."""
        from models import SplitRule, SplitRuleExpenseType

        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        # Create a split rule first
        with app.app_context():
            rule = SplitRule(
                household_id=test_household['id'],
                member1_percent=50,
                member2_percent=50,
                is_default=False
            )
            db.session.add(rule)
            db.session.flush()

            assoc = SplitRuleExpenseType(
                split_rule_id=rule.id,
                expense_type_id=test_household['expense_type_ids'][0]
            )
            db.session.add(assoc)
            db.session.commit()
            rule_id = rule.id

        response = api_client.put(
            f'/api/v1/split-rules/{rule_id}',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'member1_percent': 70,
                'member2_percent': 30
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['split_rule']['member1_percent'] == 70
        assert data['split_rule']['member2_percent'] == 30


class TestDeleteSplitRule:
    """Tests for DELETE /api/v1/split-rules/<id>"""

    def test_delete_split_rule_success(self, api_client, owner_user, test_household, app, db):
        """Test soft-deleting a split rule."""
        from models import SplitRule, SplitRuleExpenseType

        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        # Create a split rule first
        with app.app_context():
            rule = SplitRule(
                household_id=test_household['id'],
                member1_percent=50,
                member2_percent=50,
                is_default=False
            )
            db.session.add(rule)
            db.session.flush()

            assoc = SplitRuleExpenseType(
                split_rule_id=rule.id,
                expense_type_id=test_household['expense_type_ids'][0]
            )
            db.session.add(assoc)
            db.session.commit()
            rule_id = rule.id

        response = api_client.delete(
            f'/api/v1/split-rules/{rule_id}',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        assert response.get_json()['success'] is True

        # Verify soft deleted
        with app.app_context():
            rule = SplitRule.query.get(rule_id)
            assert rule.is_active is False
