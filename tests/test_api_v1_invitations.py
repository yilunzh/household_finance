"""
Tests for API v1 invitation endpoints.

Tests:
- POST /api/v1/households/<id>/invitations - Send invitation
- GET /api/v1/households/<id>/invitations - List pending invitations
- DELETE /api/v1/invitations/<id> - Cancel invitation
- GET /api/v1/invitations/<token> - Get invitation details (public)
- POST /api/v1/invitations/<token>/accept - Accept invitation
"""
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def api_client(app):
    """Create test client for API tests."""
    return app.test_client()


@pytest.fixture
def test_user(app, db):
    """Create a test user for API tests."""
    from models import User, RefreshToken
    with app.app_context():
        # Clean up any existing test user and their tokens
        existing = User.query.filter_by(email='invite_test@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='invite_test@example.com',
            name='Invite Test User',
            is_active=True
        )
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()

        yield {
            'id': user.id,
            'email': user.email,
            'password': 'testpassword123'
        }

        # Cleanup
        user = User.query.filter_by(email='invite_test@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def test_user2(app, db):
    """Create a second test user for accepting invitations."""
    from models import User, RefreshToken
    with app.app_context():
        existing = User.query.filter_by(email='invite_test2@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='invite_test2@example.com',
            name='Invite Test User 2',
            is_active=True
        )
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()

        yield {
            'id': user.id,
            'email': user.email,
            'password': 'testpassword123'
        }

        # Cleanup
        user = User.query.filter_by(email='invite_test2@example.com').first()
        if user:
            RefreshToken.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()


@pytest.fixture
def auth_tokens(api_client, test_user):
    """Get auth tokens for test user."""
    response = api_client.post('/api/v1/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    data = response.get_json()
    return {
        'access_token': data['access_token'],
        'refresh_token': data['refresh_token']
    }


@pytest.fixture
def auth_tokens2(api_client, test_user2):
    """Get auth tokens for second test user."""
    response = api_client.post('/api/v1/auth/login', json={
        'email': test_user2['email'],
        'password': test_user2['password']
    })
    data = response.get_json()
    return {
        'access_token': data['access_token'],
        'refresh_token': data['refresh_token']
    }


@pytest.fixture
def auth_headers(auth_tokens):
    """Get auth headers for API requests."""
    return {
        'Authorization': f"Bearer {auth_tokens['access_token']}",
        'Content-Type': 'application/json'
    }


@pytest.fixture
def auth_headers2(auth_tokens2):
    """Get auth headers for second user API requests."""
    return {
        'Authorization': f"Bearer {auth_tokens2['access_token']}",
        'Content-Type': 'application/json'
    }


def _cleanup_household(db, household_id):
    """Clean up all records associated with a household."""
    from models import (Household, HouseholdMember, Invitation,
                        ExpenseType, BudgetRule, SplitRule,
                        AutoCategoryRule, Transaction, Settlement)

    # BudgetRule cascade deletes BudgetSnapshot and BudgetRuleExpenseType
    BudgetRule.query.filter_by(household_id=household_id).delete()
    # SplitRule cascade deletes SplitRuleExpenseType
    SplitRule.query.filter_by(household_id=household_id).delete()
    AutoCategoryRule.query.filter_by(household_id=household_id).delete()
    Transaction.query.filter_by(household_id=household_id).delete()
    Settlement.query.filter_by(household_id=household_id).delete()
    Invitation.query.filter_by(household_id=household_id).delete()
    ExpenseType.query.filter_by(household_id=household_id).delete()
    HouseholdMember.query.filter_by(household_id=household_id).delete()


@pytest.fixture
def test_household(app, db, test_user):
    """Create a test household for the test user."""
    from models import Household, HouseholdMember
    with app.app_context():
        # Clean up any existing test household
        existing = Household.query.filter_by(name='Test Household').first()
        if existing:
            _cleanup_household(db, existing.id)
            db.session.delete(existing)
            db.session.commit()

        household = Household(
            name='Test Household',
            created_by_user_id=test_user['id']
        )
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=test_user['id'],
            role='owner',
            display_name='Test Owner'
        )
        db.session.add(member)
        db.session.commit()

        yield {
            'id': household.id,
            'name': household.name,
            'owner_id': test_user['id']
        }

        # Cleanup
        household = Household.query.filter_by(name='Test Household').first()
        if household:
            _cleanup_household(db, household.id)
            db.session.delete(household)
            db.session.commit()


class TestSendInvitation:
    """Tests for POST /api/v1/households/<id>/invitations"""

    def test_send_invitation_success(self, api_client, auth_headers, test_household, app):
        """Test successfully sending an invitation."""
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'newuser@example.com'}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert 'invitation' in data
        assert data['invitation']['email'] == 'newuser@example.com'
        assert data['invitation']['status'] == 'pending'
        assert 'invite_url' in data
        assert 'deep_link_url' in data
        assert 'householdtracker://invite/' in data['deep_link_url']

    def test_send_invitation_not_member(self, api_client, auth_headers2, test_household):
        """Test sending invitation when not a member."""
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers2,
            json={'email': 'newuser@example.com'}
        )
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_send_invitation_missing_email(self, api_client, auth_headers, test_household):
        """Test sending invitation without email."""
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': ''}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Email is required'

    def test_send_invitation_invalid_email(self, api_client, auth_headers, test_household):
        """Test sending invitation with invalid email."""
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'notanemail'}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Invalid email address'

    def test_send_invitation_existing_member(self, api_client, auth_headers, test_household, test_user):
        """Test sending invitation to existing member."""
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': test_user['email']}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'already a member' in data['error']

    def test_send_invitation_duplicate_pending(self, api_client, auth_headers, test_household):
        """Test sending duplicate invitation to same email."""
        # Send first invitation
        response1 = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'duplicate@example.com'}
        )
        assert response1.status_code == 201

        # Try to send again
        response2 = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'duplicate@example.com'}
        )
        assert response2.status_code == 400
        data = response2.get_json()
        assert 'already been sent' in data['error']


class TestListInvitations:
    """Tests for GET /api/v1/households/<id>/invitations"""

    def test_list_invitations_success(self, api_client, auth_headers, test_household):
        """Test listing pending invitations."""
        # Create some invitations
        api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'list1@example.com'}
        )
        api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'list2@example.com'}
        )

        response = api_client.get(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'invitations' in data
        assert len(data['invitations']) >= 2
        emails = [inv['email'] for inv in data['invitations']]
        assert 'list1@example.com' in emails
        assert 'list2@example.com' in emails

    def test_list_invitations_not_member(self, api_client, auth_headers2, test_household):
        """Test listing invitations when not a member."""
        response = api_client.get(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers2
        )
        assert response.status_code == 403


class TestCancelInvitation:
    """Tests for DELETE /api/v1/invitations/<id>"""

    def test_cancel_invitation_success(self, api_client, auth_headers, test_household, app, db):
        """Test canceling an invitation."""
        # Create an invitation
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'cancel@example.com'}
        )
        invitation_id = response.get_json()['invitation']['id']

        # Cancel it
        response = api_client.delete(
            f'/api/v1/invitations/{invitation_id}',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify status changed
        from models import Invitation
        with app.app_context():
            invitation = Invitation.query.get(invitation_id)
            assert invitation.status == 'cancelled'

    def test_cancel_invitation_not_found(self, api_client, auth_headers):
        """Test canceling non-existent invitation."""
        response = api_client.delete(
            '/api/v1/invitations/99999',
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_cancel_invitation_not_authorized(self, api_client, auth_headers, auth_headers2, test_household):
        """Test canceling invitation when not a member."""
        # Create an invitation as user 1
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'cancel_auth@example.com'}
        )
        invitation_id = response.get_json()['invitation']['id']

        # Try to cancel as user 2
        response = api_client.delete(
            f'/api/v1/invitations/{invitation_id}',
            headers=auth_headers2
        )
        assert response.status_code == 403


class TestGetInvitation:
    """Tests for GET /api/v1/invitations/<token> (public)"""

    def test_get_invitation_success(self, api_client, auth_headers, test_household):
        """Test getting invitation details by token."""
        # Create an invitation
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'getinfo@example.com'}
        )
        token = response.get_json()['invitation']['token']

        # Get details (no auth required)
        response = api_client.get(f'/api/v1/invitations/{token}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'invitation' in data
        assert data['invitation']['email'] == 'getinfo@example.com'
        assert 'household' in data
        assert data['household']['name'] == 'Test Household'
        assert 'inviter' in data

    def test_get_invitation_not_found(self, api_client):
        """Test getting non-existent invitation."""
        response = api_client.get('/api/v1/invitations/nonexistent_token')
        assert response.status_code == 404

    def test_get_invitation_expired(self, api_client, auth_headers, test_household, app, db):
        """Test getting expired invitation."""
        # Create an invitation
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'expired@example.com'}
        )
        token = response.get_json()['invitation']['token']
        invitation_id = response.get_json()['invitation']['id']

        # Manually expire the invitation
        from models import Invitation
        with app.app_context():
            invitation = Invitation.query.get(invitation_id)
            invitation.expires_at = datetime.utcnow() - timedelta(days=1)
            db.session.commit()

        # Try to get it
        response = api_client.get(f'/api/v1/invitations/{token}')
        assert response.status_code == 400
        data = response.get_json()
        assert 'expired' in data['error']


class TestAcceptInvitation:
    """Tests for POST /api/v1/invitations/<token>/accept"""

    def test_accept_invitation_success(self, api_client, auth_headers, auth_headers2, test_household, test_user2, app, db):
        """Test successfully accepting an invitation."""
        # Create an invitation for user 2's email
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': test_user2['email']}
        )
        assert response.status_code == 201
        token = response.get_json()['invitation']['token']

        # Accept as user 2
        response = api_client.post(
            f'/api/v1/invitations/{token}/accept',
            headers=auth_headers2,
            json={'display_name': 'New Member'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['household']['name'] == 'Test Household'
        assert data['household']['role'] == 'member'
        assert data['household']['display_name'] == 'New Member'

        # Verify membership
        from models import HouseholdMember
        with app.app_context():
            member = HouseholdMember.query.filter_by(
                household_id=test_household['id'],
                user_id=test_user2['id']
            ).first()
            assert member is not None
            assert member.display_name == 'New Member'

    def test_accept_invitation_default_name(self, api_client, auth_headers, auth_headers2, test_household, test_user2, app, db):
        """Test accepting invitation without display name uses user's name."""
        # Clean up any existing membership first
        from models import HouseholdMember
        with app.app_context():
            existing = HouseholdMember.query.filter_by(
                household_id=test_household['id'],
                user_id=test_user2['id']
            ).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()

        # Create invitation
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'default_name@example.com'}
        )
        token = response.get_json()['invitation']['token']

        # Accept without display name
        response = api_client.post(
            f'/api/v1/invitations/{token}/accept',
            headers=auth_headers2,
            json={}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['household']['display_name'] == 'Invite Test User 2'

    def test_accept_invitation_not_found(self, api_client, auth_headers2):
        """Test accepting non-existent invitation."""
        response = api_client.post(
            '/api/v1/invitations/nonexistent_token/accept',
            headers=auth_headers2
        )
        assert response.status_code == 404

    def test_accept_invitation_already_member(self, api_client, auth_headers, test_household):
        """Test accepting invitation when already a member."""
        # Create invitation for user who is already a member
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'already_member@example.com'}
        )
        token = response.get_json()['invitation']['token']

        # Try to accept as the owner (who is already a member)
        response = api_client.post(
            f'/api/v1/invitations/{token}/accept',
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'already a member' in data['error']

    def test_accept_invitation_expired(self, api_client, auth_headers, auth_headers2, test_household, app, db):
        """Test accepting expired invitation."""
        # Create invitation
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'accept_expired@example.com'}
        )
        token = response.get_json()['invitation']['token']
        invitation_id = response.get_json()['invitation']['id']

        # Manually expire
        from models import Invitation
        with app.app_context():
            invitation = Invitation.query.get(invitation_id)
            invitation.expires_at = datetime.utcnow() - timedelta(days=1)
            db.session.commit()

        # Try to accept
        response = api_client.post(
            f'/api/v1/invitations/{token}/accept',
            headers=auth_headers2
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'expired' in data['error']

    def test_accept_invitation_already_accepted(self, api_client, auth_headers, auth_headers2, test_household, test_user2, app, db):
        """Test accepting invitation that was already accepted."""
        # Clean up membership
        from models import HouseholdMember
        with app.app_context():
            existing = HouseholdMember.query.filter_by(
                household_id=test_household['id'],
                user_id=test_user2['id']
            ).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()

        # Create and accept invitation
        response = api_client.post(
            f'/api/v1/households/{test_household["id"]}/invitations',
            headers=auth_headers,
            json={'email': 'double_accept@example.com'}
        )
        token = response.get_json()['invitation']['token']

        # Accept first time
        response = api_client.post(
            f'/api/v1/invitations/{token}/accept',
            headers=auth_headers2
        )
        assert response.status_code == 200

        # Try to accept again
        response = api_client.post(
            f'/api/v1/invitations/{token}/accept',
            headers=auth_headers2
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'already been used' in data['error']
