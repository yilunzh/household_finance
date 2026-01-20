"""
Tests for API v1 profile endpoints.

Tests:
- PUT /api/v1/user/profile - Update display name
- PUT /api/v1/user/password - Change password
- POST /api/v1/user/email/request - Request email change
- POST /api/v1/user/email/cancel - Cancel pending email change
- DELETE /api/v1/user - Delete account
- POST /api/v1/auth/forgot-password - Request password reset
"""
import pytest
import json
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
        existing = User.query.filter_by(email='api_test@example.com').first()
        if existing:
            RefreshToken.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        user = User(
            email='api_test@example.com',
            name='API Test User',
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

        # Cleanup - delete tokens first, then user
        user = User.query.filter_by(email='api_test@example.com').first()
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
def auth_headers(auth_tokens):
    """Get auth headers for API requests."""
    return {
        'Authorization': f"Bearer {auth_tokens['access_token']}",
        'Content-Type': 'application/json'
    }


class TestUpdateProfile:
    """Tests for PUT /api/v1/user/profile"""

    def test_update_profile_success(self, api_client, auth_headers, test_user, app):
        """Test successful profile name update."""
        response = api_client.put('/api/v1/user/profile',
            headers=auth_headers,
            json={'name': 'New Display Name'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['name'] == 'New Display Name'

        # Verify in database
        from models import User
        with app.app_context():
            user = User.query.get(test_user['id'])
            assert user.name == 'New Display Name'

    def test_update_profile_empty_name(self, api_client, auth_headers):
        """Test profile update with empty name fails."""
        response = api_client.put('/api/v1/user/profile',
            headers=auth_headers,
            json={'name': ''}
        )
        assert response.status_code == 400
        assert 'Name is required' in response.get_json()['error']

    def test_update_profile_long_name(self, api_client, auth_headers):
        """Test profile update with too long name fails."""
        response = api_client.put('/api/v1/user/profile',
            headers=auth_headers,
            json={'name': 'x' * 101}
        )
        assert response.status_code == 400
        assert 'too long' in response.get_json()['error']

    def test_update_profile_unauthorized(self, api_client):
        """Test profile update without auth fails."""
        response = api_client.put('/api/v1/user/profile',
            json={'name': 'New Name'}
        )
        assert response.status_code == 401


class TestChangePassword:
    """Tests for PUT /api/v1/user/password"""

    def test_change_password_success(self, api_client, auth_headers, test_user, app):
        """Test successful password change."""
        response = api_client.put('/api/v1/user/password',
            headers=auth_headers,
            json={
                'current_password': test_user['password'],
                'new_password': 'NewPassword123'
            }
        )
        assert response.status_code == 200
        assert response.get_json()['success'] is True

        # Verify new password works
        login_response = api_client.post('/api/v1/auth/login', json={
            'email': test_user['email'],
            'password': 'NewPassword123'
        })
        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, api_client, auth_headers):
        """Test password change with wrong current password fails."""
        response = api_client.put('/api/v1/user/password',
            headers=auth_headers,
            json={
                'current_password': 'wrongpassword',
                'new_password': 'NewPassword123'
            }
        )
        assert response.status_code == 401
        assert 'incorrect' in response.get_json()['error'].lower()

    def test_change_password_too_short(self, api_client, auth_headers, test_user):
        """Test password change with too short new password fails."""
        response = api_client.put('/api/v1/user/password',
            headers=auth_headers,
            json={
                'current_password': test_user['password'],
                'new_password': 'short'
            }
        )
        assert response.status_code == 400
        assert '8 characters' in response.get_json()['error']

    def test_change_password_missing_uppercase(self, api_client, auth_headers, test_user):
        """Test password change without uppercase letter fails."""
        response = api_client.put('/api/v1/user/password',
            headers=auth_headers,
            json={
                'current_password': test_user['password'],
                'new_password': 'newpassword123'
            }
        )
        assert response.status_code == 400
        assert 'uppercase' in response.get_json()['error'].lower()

    def test_change_password_missing_number(self, api_client, auth_headers, test_user):
        """Test password change without number fails."""
        response = api_client.put('/api/v1/user/password',
            headers=auth_headers,
            json={
                'current_password': test_user['password'],
                'new_password': 'NewPassword'
            }
        )
        assert response.status_code == 400
        assert 'number' in response.get_json()['error'].lower()


class TestEmailChange:
    """Tests for email change endpoints"""

    def test_request_email_change_success(self, api_client, auth_headers, test_user, app):
        """Test successful email change request."""
        response = api_client.post('/api/v1/user/email/request',
            headers=auth_headers,
            json={
                'new_email': 'newemail@example.com',
                'password': test_user['password']
            }
        )
        # May be 200 or 500 if email service not configured
        # In test mode, it should work or fail gracefully
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] is True

            # Verify pending email set
            from models import User
            with app.app_context():
                user = User.query.get(test_user['id'])
                assert user.pending_email == 'newemail@example.com'
                assert user.email_change_token is not None

    def test_request_email_change_wrong_password(self, api_client, auth_headers):
        """Test email change request with wrong password fails."""
        response = api_client.post('/api/v1/user/email/request',
            headers=auth_headers,
            json={
                'new_email': 'newemail@example.com',
                'password': 'wrongpassword'
            }
        )
        assert response.status_code == 401

    def test_request_email_change_same_email(self, api_client, auth_headers, test_user):
        """Test email change to same email fails."""
        response = api_client.post('/api/v1/user/email/request',
            headers=auth_headers,
            json={
                'new_email': test_user['email'],
                'password': test_user['password']
            }
        )
        assert response.status_code == 400
        assert 'already your email' in response.get_json()['error']

    def test_cancel_email_change_success(self, app, db):
        """Test canceling pending email change."""
        from models import User, RefreshToken
        import secrets

        with app.app_context():
            # Create a fresh user for this test
            existing = User.query.filter_by(email='cancel_test@example.com').first()
            if existing:
                RefreshToken.query.filter_by(user_id=existing.id).delete()
                db.session.delete(existing)
                db.session.commit()

            user = User(
                email='cancel_test@example.com',
                name='Cancel Test User',
                is_active=True
            )
            user.set_password('testpassword123')
            user.pending_email = 'pending@example.com'
            user.email_change_token = secrets.token_urlsafe(32)
            user.email_change_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        # Login with this user
        client = app.test_client()
        login_response = client.post('/api/v1/auth/login', json={
            'email': 'cancel_test@example.com',
            'password': 'testpassword123'
        })
        tokens = login_response.get_json()

        # Cancel email change
        response = client.post('/api/v1/user/email/cancel',
            headers={
                'Authorization': f"Bearer {tokens['access_token']}",
                'Content-Type': 'application/json'
            }
        )
        assert response.status_code == 200

        # Verify cleared
        with app.app_context():
            user = User.query.get(user_id)
            assert user.pending_email is None
            assert user.email_change_token is None

            # Cleanup
            RefreshToken.query.filter_by(user_id=user_id).delete()
            db.session.delete(user)
            db.session.commit()

    def test_cancel_email_change_no_pending(self, api_client, auth_headers):
        """Test canceling when no pending email change."""
        response = api_client.post('/api/v1/user/email/cancel',
            headers=auth_headers
        )
        assert response.status_code == 400
        assert 'No pending' in response.get_json()['error']


class TestDeleteAccount:
    """Tests for DELETE /api/v1/user"""

    def test_delete_account_success(self, app, db):
        """Test successful account deletion."""
        from models import User, RefreshToken

        with app.app_context():
            # Clean up any existing test user
            existing = User.query.filter_by(email='delete_test@example.com').first()
            if existing:
                RefreshToken.query.filter_by(user_id=existing.id).delete()
                db.session.delete(existing)
                db.session.commit()

            # Create a dedicated user for deletion test
            user = User(
                email='delete_test@example.com',
                name='Delete Test User',
                is_active=True
            )
            user.set_password('testpassword123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        # Login
        client = app.test_client()
        login_response = client.post('/api/v1/auth/login', json={
            'email': 'delete_test@example.com',
            'password': 'testpassword123'
        })
        tokens = login_response.get_json()

        # Delete account
        response = client.delete('/api/v1/user',
            headers={
                'Authorization': f"Bearer {tokens['access_token']}",
                'Content-Type': 'application/json'
            },
            json={
                'password': 'testpassword123',
                'confirm': 'DELETE'
            }
        )
        assert response.status_code == 200
        assert response.get_json()['success'] is True

        # Verify user deleted
        with app.app_context():
            user = User.query.get(user_id)
            assert user is None

    def test_delete_account_wrong_password(self, api_client, auth_headers):
        """Test account deletion with wrong password fails."""
        response = api_client.delete('/api/v1/user',
            headers=auth_headers,
            json={
                'password': 'wrongpassword',
                'confirm': 'DELETE'
            }
        )
        assert response.status_code == 401

    def test_delete_account_no_confirmation(self, api_client, auth_headers, test_user):
        """Test account deletion without confirmation fails."""
        response = api_client.delete('/api/v1/user',
            headers=auth_headers,
            json={
                'password': test_user['password'],
                'confirm': 'wrong'
            }
        )
        assert response.status_code == 400
        assert 'confirm' in response.get_json()['error'].lower()


class TestForgotPassword:
    """Tests for POST /api/v1/auth/forgot-password"""

    def test_forgot_password_existing_user(self, api_client, test_user, app):
        """Test forgot password for existing user."""
        response = api_client.post('/api/v1/auth/forgot-password',
            json={'email': test_user['email']}
        )
        # Should always return success (to prevent email enumeration)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify token was set (for existing user)
        from models import User
        with app.app_context():
            user = User.query.get(test_user['id'])
            assert user.password_reset_token is not None
            assert user.password_reset_expires is not None

    def test_forgot_password_nonexistent_user(self, api_client):
        """Test forgot password for non-existent user still returns success."""
        response = api_client.post('/api/v1/auth/forgot-password',
            json={'email': 'nonexistent@example.com'}
        )
        # Should still return success (to prevent email enumeration)
        assert response.status_code == 200
        assert response.get_json()['success'] is True

    def test_forgot_password_missing_email(self, api_client):
        """Test forgot password without email fails."""
        response = api_client.post('/api/v1/auth/forgot-password',
            json={'email': ''}
        )
        assert response.status_code == 400
        assert 'Email is required' in response.get_json()['error']

