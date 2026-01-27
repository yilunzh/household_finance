"""
Tests for API v1 auto-category rules CRUD endpoints.

Tests:
- GET /api/v1/auto-category-rules - List rules
- POST /api/v1/auto-category-rules - Create rule
- PUT /api/v1/auto-category-rules/<id> - Update rule
- DELETE /api/v1/auto-category-rules/<id> - Delete rule
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
        existing = User.query.filter_by(email='acrules_test@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='acrules_test@example.com',
            name='ACRules Tester',
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

        user = User.query.filter_by(email='acrules_test@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_user2(app, db):
    """Create a second test user for cross-household isolation tests."""
    from models import User, RefreshToken
    with app.app_context():
        existing = User.query.filter_by(email='acrules_test2@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='acrules_test2@example.com',
            name='ACRules Tester 2',
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

        user = User.query.filter_by(email='acrules_test2@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_household(app, db, test_user):
    """Create a test household with expense types."""
    from models import Household, HouseholdMember, ExpenseType
    with app.app_context():
        household = Household(
            name='ACRules Test Household',
            created_by_user_id=test_user['id']
        )
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=test_user['id'],
            role='owner',
            display_name='Owner'
        )
        db.session.add(member)

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
        db.session.commit()

        yield {
            'id': household.id,
            'grocery_type_id': grocery_type.id,
            'coffee_type_id': coffee_type.id,
        }

        # Cleanup
        from models import AutoCategoryRule
        AutoCategoryRule.query.filter_by(household_id=household.id).delete()
        ExpenseType.query.filter_by(household_id=household.id).delete()
        HouseholdMember.query.filter_by(household_id=household.id).delete()
        Household.query.filter_by(id=household.id).delete()
        db.session.commit()


@pytest.fixture
def test_household2(app, db, test_user2):
    """Create a second household for cross-household isolation tests."""
    from models import Household, HouseholdMember, ExpenseType
    with app.app_context():
        household = Household(
            name='ACRules Test Household 2',
            created_by_user_id=test_user2['id']
        )
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=test_user2['id'],
            role='owner',
            display_name='Owner2'
        )
        db.session.add(member)

        dining_type = ExpenseType(
            household_id=household.id,
            name='Dining',
            icon='fork.knife',
            color='red'
        )
        db.session.add(dining_type)
        db.session.flush()
        db.session.commit()

        yield {
            'id': household.id,
            'dining_type_id': dining_type.id,
        }

        from models import AutoCategoryRule
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


def auth_headers(token, household_id):
    """Helper to build auth + household headers."""
    return {
        'Authorization': f'Bearer {token}',
        'X-Household-ID': str(household_id)
    }


class TestListAutoCategoryRules:
    """Tests for GET /api/v1/auto-category-rules"""

    def test_list_empty(self, api_client, test_user, test_household):
        """Empty household returns empty rules list."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.get(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id'])
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['rules'] == []

    def test_list_populated(self, app, db, api_client, test_user, test_household):
        """Returns rules with expense type names."""
        from models import AutoCategoryRule
        with app.app_context():
            rule = AutoCategoryRule(
                household_id=test_household['id'],
                keyword='whole foods',
                expense_type_id=test_household['grocery_type_id']
            )
            db.session.add(rule)
            db.session.commit()

        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.get(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id'])
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['rules']) == 1
        assert data['rules'][0]['keyword'] == 'whole foods'
        assert data['rules'][0]['expense_type_name'] == 'Grocery'

    def test_list_ordered_by_keyword(self, app, db, api_client, test_user, test_household):
        """Rules ordered alphabetically by keyword."""
        from models import AutoCategoryRule
        with app.app_context():
            db.session.add(AutoCategoryRule(
                household_id=test_household['id'],
                keyword='beta store',
                expense_type_id=test_household['grocery_type_id']
            ))
            db.session.add(AutoCategoryRule(
                household_id=test_household['id'],
                keyword='alpha store',
                expense_type_id=test_household['grocery_type_id']
            ))
            db.session.add(AutoCategoryRule(
                household_id=test_household['id'],
                keyword='gamma store',
                expense_type_id=test_household['coffee_type_id']
            ))
            db.session.commit()

        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.get(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id'])
        )
        assert response.status_code == 200
        rules = response.get_json()['rules']
        assert len(rules) == 3
        assert rules[0]['keyword'] == 'alpha store'
        assert rules[1]['keyword'] == 'beta store'
        assert rules[2]['keyword'] == 'gamma store'

    def test_list_requires_auth(self, api_client, test_household):
        """Requires JWT authentication."""
        response = api_client.get(
            '/api/v1/auto-category-rules',
            headers={'X-Household-ID': str(test_household['id'])}
        )
        assert response.status_code == 401

    def test_list_cross_household_isolation(
            self, app, db, api_client, test_user,
            test_user2, test_household, test_household2):
        """Rules from other households are not visible."""
        from models import AutoCategoryRule
        with app.app_context():
            # Add rule to household 2
            rule = AutoCategoryRule(
                household_id=test_household2['id'],
                keyword='other household rule',
                expense_type_id=test_household2['dining_type_id']
            )
            db.session.add(rule)
            db.session.commit()

        # User 1 should not see household 2's rules
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.get(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id'])
        )
        assert response.status_code == 200
        assert len(response.get_json()['rules']) == 0


class TestCreateAutoCategoryRule:
    """Tests for POST /api/v1/auto-category-rules"""

    def test_create_success(self, api_client, test_user, test_household):
        """Create a basic rule."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id']),
            json={
                'keyword': 'Whole Foods',
                'expense_type_id': test_household['grocery_type_id']
            }
        )
        assert response.status_code == 201
        rule = response.get_json()['rule']
        assert rule['keyword'] == 'Whole Foods'
        assert rule['expense_type_id'] == test_household['grocery_type_id']
        assert rule['expense_type_name'] == 'Grocery'

    def test_create_missing_keyword(self, api_client, test_user, test_household):
        """Keyword is required."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id']),
            json={
                'expense_type_id': test_household['grocery_type_id']
            }
        )
        assert response.status_code == 400
        assert 'keyword' in response.get_json()['error'].lower()

    def test_create_empty_keyword(self, api_client, test_user, test_household):
        """Empty/whitespace keyword rejected."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id']),
            json={
                'keyword': '   ',
                'expense_type_id': test_household['grocery_type_id']
            }
        )
        assert response.status_code == 400

    def test_create_missing_expense_type(self, api_client, test_user, test_household):
        """Expense type is required."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id']),
            json={
                'keyword': 'Whole Foods'
            }
        )
        assert response.status_code == 400
        assert 'expense type' in response.get_json()['error'].lower()

    def test_create_invalid_expense_type(self, api_client, test_user, test_household):
        """Non-existent expense type rejected."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id']),
            json={
                'keyword': 'Whole Foods',
                'expense_type_id': 99999
            }
        )
        assert response.status_code == 400
        assert 'not found' in response.get_json()['error'].lower()

    def test_create_duplicate_keyword(self, api_client, test_user, test_household):
        """Duplicate keyword in same household rejected."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        # Create first rule
        api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id']),
            json={
                'keyword': 'Whole Foods',
                'expense_type_id': test_household['grocery_type_id']
            }
        )
        # Try duplicate (case-insensitive)
        response = api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id']),
            json={
                'keyword': 'whole foods',
                'expense_type_id': test_household['coffee_type_id']
            }
        )
        assert response.status_code == 400
        assert 'already exists' in response.get_json()['error'].lower()


class TestUpdateAutoCategoryRule:
    """Tests for PUT /api/v1/auto-category-rules/<id>"""

    def _create_rule(self, client, token, household_id, keyword, expense_type_id):
        """Helper to create a rule and return it."""
        response = client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, household_id),
            json={
                'keyword': keyword,
                'expense_type_id': expense_type_id
            }
        )
        return response.get_json()['rule']

    def test_update_keyword(self, api_client, test_user, test_household):
        """Update keyword."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        rule = self._create_rule(
            api_client, token, test_household['id'],
            'Old Keyword', test_household['grocery_type_id']
        )

        response = api_client.put(
            f'/api/v1/auto-category-rules/{rule["id"]}',
            headers=auth_headers(token, test_household['id']),
            json={'keyword': 'New Keyword'}
        )
        assert response.status_code == 200
        assert response.get_json()['rule']['keyword'] == 'New Keyword'

    def test_update_expense_type(self, api_client, test_user, test_household):
        """Update expense type."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        rule = self._create_rule(
            api_client, token, test_household['id'],
            'Test Store', test_household['grocery_type_id']
        )

        response = api_client.put(
            f'/api/v1/auto-category-rules/{rule["id"]}',
            headers=auth_headers(token, test_household['id']),
            json={'expense_type_id': test_household['coffee_type_id']}
        )
        assert response.status_code == 200
        assert response.get_json()['rule']['expense_type_id'] == test_household['coffee_type_id']
        assert response.get_json()['rule']['expense_type_name'] == 'Coffee'

    def test_update_not_found(self, api_client, test_user, test_household):
        """Non-existent rule returns 404."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.put(
            '/api/v1/auto-category-rules/99999',
            headers=auth_headers(token, test_household['id']),
            json={'keyword': 'Test'}
        )
        assert response.status_code == 404

    def test_update_cross_household_isolation(
            self, api_client, test_user, test_user2,
            test_household, test_household2):
        """Cannot update rules in another household."""
        # Create rule in household 1
        token1 = get_auth_token(api_client, test_user['email'], test_user['password'])
        rule = self._create_rule(
            api_client, token1, test_household['id'],
            'Isolated Rule', test_household['grocery_type_id']
        )

        # Try to update from household 2
        token2 = get_auth_token(api_client, test_user2['email'], test_user2['password'])
        response = api_client.put(
            f'/api/v1/auto-category-rules/{rule["id"]}',
            headers=auth_headers(token2, test_household2['id']),
            json={'keyword': 'Hacked'}
        )
        assert response.status_code == 404

    def test_update_duplicate_keyword(self, api_client, test_user, test_household):
        """Cannot update keyword to one that already exists."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        self._create_rule(
            api_client, token, test_household['id'],
            'Existing Keyword', test_household['grocery_type_id']
        )
        rule2 = self._create_rule(
            api_client, token, test_household['id'],
            'Other Keyword', test_household['coffee_type_id']
        )

        response = api_client.put(
            f'/api/v1/auto-category-rules/{rule2["id"]}',
            headers=auth_headers(token, test_household['id']),
            json={'keyword': 'existing keyword'}
        )
        assert response.status_code == 400
        assert 'already exists' in response.get_json()['error'].lower()


class TestDeleteAutoCategoryRule:
    """Tests for DELETE /api/v1/auto-category-rules/<id>"""

    def test_delete_success(self, api_client, test_user, test_household):
        """Delete a rule."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        # Create
        create_resp = api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id']),
            json={
                'keyword': 'To Delete',
                'expense_type_id': test_household['grocery_type_id']
            }
        )
        rule_id = create_resp.get_json()['rule']['id']

        # Delete
        response = api_client.delete(
            f'/api/v1/auto-category-rules/{rule_id}',
            headers=auth_headers(token, test_household['id'])
        )
        assert response.status_code == 200
        assert response.get_json()['success'] is True

        # Verify gone
        list_resp = api_client.get(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token, test_household['id'])
        )
        rule_ids = [r['id'] for r in list_resp.get_json()['rules']]
        assert rule_id not in rule_ids

    def test_delete_not_found(self, api_client, test_user, test_household):
        """Non-existent rule returns 404."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])
        response = api_client.delete(
            '/api/v1/auto-category-rules/99999',
            headers=auth_headers(token, test_household['id'])
        )
        assert response.status_code == 404

    def test_delete_cross_household_isolation(
            self, api_client, test_user, test_user2,
            test_household, test_household2):
        """Cannot delete rules from another household."""
        # Create rule in household 1
        token1 = get_auth_token(api_client, test_user['email'], test_user['password'])
        create_resp = api_client.post(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token1, test_household['id']),
            json={
                'keyword': 'Protected Rule',
                'expense_type_id': test_household['grocery_type_id']
            }
        )
        rule_id = create_resp.get_json()['rule']['id']

        # Try to delete from household 2
        token2 = get_auth_token(api_client, test_user2['email'], test_user2['password'])
        response = api_client.delete(
            f'/api/v1/auto-category-rules/{rule_id}',
            headers=auth_headers(token2, test_household2['id'])
        )
        assert response.status_code == 404

        # Verify still exists in household 1
        list_resp = api_client.get(
            '/api/v1/auto-category-rules',
            headers=auth_headers(token1, test_household['id'])
        )
        rule_ids = [r['id'] for r in list_resp.get_json()['rules']]
        assert rule_id in rule_ids
