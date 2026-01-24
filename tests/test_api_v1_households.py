"""
Tests for API v1 household management endpoints.

Tests:
- PUT /api/v1/households/<id> - Rename household
- PUT /api/v1/households/<id>/members/<user_id> - Update member
- DELETE /api/v1/households/<id>/members/<user_id> - Remove member
"""
import pytest


@pytest.fixture
def api_client(app):
    """Create test client for API tests."""
    return app.test_client()


@pytest.fixture
def owner_user(app, db):
    """Create an owner user for household tests."""
    from models import User, RefreshToken
    with app.app_context():
        # Clean up any existing test user
        existing = User.query.filter_by(email='household_owner@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='household_owner@example.com',
            name='Household Owner',
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

        # Cleanup
        user = User.query.filter_by(email='household_owner@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def member_user(app, db):
    """Create a member user for household tests."""
    from models import User, RefreshToken
    with app.app_context():
        existing = User.query.filter_by(email='household_member@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='household_member@example.com',
            name='Household Member',
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

        user = User.query.filter_by(email='household_member@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_household(app, db, owner_user):
    """Create a test household with owner."""
    from models import Household, HouseholdMember
    with app.app_context():
        household = Household(
            name='Test Household',
            created_by_user_id=owner_user['id']
        )
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=owner_user['id'],
            role='owner',
            display_name='Owner'
        )
        db.session.add(member)
        db.session.commit()

        yield {
            'id': household.id,
            'name': household.name,
            'owner_id': owner_user['id']
        }

        # Cleanup
        HouseholdMember.query.filter_by(household_id=household.id).delete()
        Household.query.filter_by(id=household.id).delete()
        db.session.commit()


@pytest.fixture
def household_with_member(app, db, test_household, member_user):
    """Add member user to the test household."""
    from models import HouseholdMember
    with app.app_context():
        member = HouseholdMember(
            household_id=test_household['id'],
            user_id=member_user['id'],
            role='member',
            display_name='Member'
        )
        db.session.add(member)
        db.session.commit()

        yield {
            **test_household,
            'member_id': member_user['id']
        }


def get_auth_token(client, email, password):
    """Helper to get auth token."""
    response = client.post('/api/v1/auth/login', json={
        'email': email,
        'password': password
    })
    return response.get_json()['access_token']


class TestRenameHousehold:
    """Tests for PUT /api/v1/households/<id>"""

    def test_rename_household_success(self, api_client, owner_user, test_household, app):
        """Test successful household rename by owner."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.put(
            f"/api/v1/households/{test_household['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={'name': 'New Household Name'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['household']['name'] == 'New Household Name'

        # Verify in database
        from models import Household
        with app.app_context():
            household = Household.query.get(test_household['id'])
            assert household.name == 'New Household Name'

    def test_rename_household_not_owner(self, api_client, member_user, household_with_member):
        """Test that non-owners cannot rename household."""
        token = get_auth_token(api_client, member_user['email'], member_user['password'])

        response = api_client.put(
            f"/api/v1/households/{household_with_member['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={'name': 'New Name'}
        )

        assert response.status_code == 403
        assert 'owner' in response.get_json()['error'].lower()

    def test_rename_household_empty_name(self, api_client, owner_user, test_household):
        """Test rename with empty name fails."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.put(
            f"/api/v1/households/{test_household['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={'name': ''}
        )

        assert response.status_code == 400
        assert 'required' in response.get_json()['error'].lower()

    def test_rename_household_not_member(self, api_client, member_user, test_household):
        """Test rename by non-member fails."""
        token = get_auth_token(api_client, member_user['email'], member_user['password'])

        response = api_client.put(
            f"/api/v1/households/{test_household['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={'name': 'New Name'}
        )

        assert response.status_code == 403


class TestUpdateMember:
    """Tests for PUT /api/v1/households/<id>/members/<user_id>"""

    def test_update_own_display_name(self, api_client, member_user, household_with_member, app):
        """Test member can update their own display name."""
        token = get_auth_token(api_client, member_user['email'], member_user['password'])

        response = api_client.put(
            f"/api/v1/households/{household_with_member['id']}/members/{member_user['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={'display_name': 'New Display Name'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['member']['display_name'] == 'New Display Name'

    def test_owner_update_member_name(self, api_client, owner_user, member_user, household_with_member, app):
        """Test owner can update any member's display name."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.put(
            f"/api/v1/households/{household_with_member['id']}/members/{member_user['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={'display_name': 'Owner Set Name'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['member']['display_name'] == 'Owner Set Name'

    def test_member_cannot_update_other_member(self, api_client, member_user, owner_user, household_with_member):
        """Test member cannot update another member's display name."""
        token = get_auth_token(api_client, member_user['email'], member_user['password'])

        response = api_client.put(
            f"/api/v1/households/{household_with_member['id']}/members/{owner_user['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={'display_name': 'Unauthorized Change'}
        )

        assert response.status_code == 403

    def test_update_member_empty_name(self, api_client, member_user, household_with_member):
        """Test update with empty display name fails."""
        token = get_auth_token(api_client, member_user['email'], member_user['password'])

        response = api_client.put(
            f"/api/v1/households/{household_with_member['id']}/members/{member_user['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={'display_name': ''}
        )

        assert response.status_code == 400


class TestRemoveMember:
    """Tests for DELETE /api/v1/households/<id>/members/<user_id>"""

    def test_owner_remove_member_success(self, api_client, owner_user, member_user, household_with_member, app):
        """Test owner can remove a member."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.delete(
            f"/api/v1/households/{household_with_member['id']}/members/{member_user['id']}",
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        assert response.get_json()['success'] is True

        # Verify member removed
        from models import HouseholdMember
        with app.app_context():
            member = HouseholdMember.query.filter_by(
                household_id=household_with_member['id'],
                user_id=member_user['id']
            ).first()
            assert member is None

    def test_member_cannot_remove_others(self, api_client, member_user, owner_user, household_with_member):
        """Test non-owner cannot remove members."""
        token = get_auth_token(api_client, member_user['email'], member_user['password'])

        response = api_client.delete(
            f"/api/v1/households/{household_with_member['id']}/members/{owner_user['id']}",
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403
        assert 'owner' in response.get_json()['error'].lower()

    def test_owner_cannot_remove_self(self, api_client, owner_user, test_household):
        """Test owner cannot remove themselves via this endpoint."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.delete(
            f"/api/v1/households/{test_household['id']}/members/{owner_user['id']}",
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 400
        assert 'leave' in response.get_json()['error'].lower()

    def test_remove_nonexistent_member(self, api_client, owner_user, test_household):
        """Test removing non-existent member fails."""
        token = get_auth_token(api_client, owner_user['email'], owner_user['password'])

        response = api_client.delete(
            f"/api/v1/households/{test_household['id']}/members/99999",
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404
