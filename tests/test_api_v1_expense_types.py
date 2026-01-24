"""
Tests for API v1 expense types CRUD endpoints.

Tests:
- POST /api/v1/expense-types - Create expense type
- PUT /api/v1/expense-types/<id> - Update expense type
- DELETE /api/v1/expense-types/<id> - Delete expense type
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
        existing = User.query.filter_by(email='expense_test@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='expense_test@example.com',
            name='Expense Tester',
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

        user = User.query.filter_by(email='expense_test@example.com').first()
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
            name='Expense Test Household',
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

        # Create an existing expense type
        expense_type = ExpenseType(
            household_id=household.id,
            name='Existing Type',
            icon='star',
            color='blue'
        )
        db.session.add(expense_type)
        db.session.commit()

        yield {
            'id': household.id,
            'name': household.name,
            'expense_type_id': expense_type.id
        }

        # Cleanup
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


class TestCreateExpenseType:
    """Tests for POST /api/v1/expense-types"""

    def test_create_expense_type_success(self, api_client, test_user, test_household):
        """Test successful expense type creation."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/expense-types',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'name': 'Grocery',
                'icon': 'cart',
                'color': 'emerald'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'expense_type' in data
        assert data['expense_type']['name'] == 'Grocery'
        assert data['expense_type']['icon'] == 'cart'
        assert data['expense_type']['color'] == 'emerald'

    def test_create_expense_type_minimal(self, api_client, test_user, test_household):
        """Test creating expense type with just name."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/expense-types',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'name': 'Bills'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['expense_type']['name'] == 'Bills'
        assert data['expense_type']['icon'] is None
        assert data['expense_type']['color'] is None

    def test_create_expense_type_empty_name(self, api_client, test_user, test_household):
        """Test creating expense type with empty name fails."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/expense-types',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'name': '  '
            }
        )

        assert response.status_code == 400
        assert 'required' in response.get_json()['error'].lower()

    def test_create_expense_type_duplicate_name(self, api_client, test_user, test_household):
        """Test creating expense type with duplicate name fails."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.post(
            '/api/v1/expense-types',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'name': 'Existing Type'  # Same as fixture
            }
        )

        assert response.status_code == 400
        assert 'already exists' in response.get_json()['error'].lower()


class TestUpdateExpenseType:
    """Tests for PUT /api/v1/expense-types/<id>"""

    def test_update_expense_type_name(self, api_client, test_user, test_household):
        """Test updating expense type name."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.put(
            f'/api/v1/expense-types/{test_household["expense_type_id"]}',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'name': 'Updated Type'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type']['name'] == 'Updated Type'

    def test_update_expense_type_all_fields(self, api_client, test_user, test_household):
        """Test updating all expense type fields."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.put(
            f'/api/v1/expense-types/{test_household["expense_type_id"]}',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'name': 'New Name',
                'icon': 'new-icon',
                'color': 'red'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['expense_type']['name'] == 'New Name'
        assert data['expense_type']['icon'] == 'new-icon'
        assert data['expense_type']['color'] == 'red'

    def test_update_expense_type_not_found(self, api_client, test_user, test_household):
        """Test updating non-existent expense type."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.put(
            '/api/v1/expense-types/99999',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            },
            json={
                'name': 'New Name'
            }
        )

        assert response.status_code == 404


class TestDeleteExpenseType:
    """Tests for DELETE /api/v1/expense-types/<id>"""

    def test_delete_expense_type_success(self, api_client, test_user, test_household, app, db):
        """Test soft-deleting an expense type."""
        from models import ExpenseType

        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.delete(
            f'/api/v1/expense-types/{test_household["expense_type_id"]}',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 200
        assert response.get_json()['success'] is True

        # Verify soft deleted
        with app.app_context():
            expense_type = db.session.get(ExpenseType, test_household['expense_type_id'])
            assert expense_type.is_active is False

    def test_delete_expense_type_not_found(self, api_client, test_user, test_household):
        """Test deleting non-existent expense type."""
        token = get_auth_token(api_client, test_user['email'], test_user['password'])

        response = api_client.delete(
            '/api/v1/expense-types/99999',
            headers={
                'Authorization': f'Bearer {token}',
                'X-Household-ID': str(test_household['id'])
            }
        )

        assert response.status_code == 404
