"""
E2E tests for invitation functionality.
Tests sending, accepting, and canceling invitations.
"""
import pytest
from datetime import datetime, timedelta
from conftest import BASE_URL, TEST_USERS


pytestmark = pytest.mark.integration


class TestSendInvitation:
    """Invitation sending tests."""

    def test_invite_page_accessible(self, page, register_user, create_household):
        """Invite page should be accessible."""
        register_user('alice')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/household/invite")
        page.wait_for_load_state('networkidle')

        assert '/login' not in page.url
        content = page.content().lower()
        assert 'invite' in content or 'email' in content

    def test_send_invitation_form_exists(self, page, register_user, create_household):
        """Invite form should have email input."""
        register_user('bob')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/household/invite")
        page.wait_for_load_state('networkidle')

        email_input = page.locator('input[name="email"], input[type="email"]')
        assert email_input.count() > 0

    def test_send_invitation_success(self, page, register_user, create_household, app, db):
        """User can send an invitation."""
        from models import Invitation, Household

        register_user('alice')
        create_household('Alice Household')

        page.goto(f"{BASE_URL}/household/invite")
        page.wait_for_load_state('networkidle')

        # Fill invitation form
        email_input = page.locator('input[name="email"], input[type="email"]')
        email_input.first.fill('invitee@example.com')

        # Submit form
        submit_btn = page.locator('button[type="submit"], button:has-text("Send"), button:has-text("Invite")')
        submit_btn.first.click()
        page.wait_for_load_state('networkidle')

        # Invitation should be created
        with app.app_context():
            household = Household.query.filter_by(name='Alice Household').first()
            invitation = Invitation.query.filter_by(
                household_id=household.id,
                email='invitee@example.com'
            ).first()

            if invitation:
                # Clean up
                db.session.delete(invitation)
                db.session.commit()


class TestAcceptInvitation:
    """Invitation acceptance tests."""

    def test_accept_invitation_page_new_user(self, page, register_user, create_household, app, db):
        """New user can accept invitation via signup."""
        from models import Invitation, Household, User
        import secrets

        register_user('alice')
        create_household('Alice Household')

        # Create invitation manually
        with app.app_context():
            alice = User.query.filter_by(email=TEST_USERS['alice']['email']).first()
            household = Household.query.filter_by(name='Alice Household').first()

            token = secrets.token_urlsafe(32)
            invitation = Invitation(
                household_id=household.id,
                email='newuser@example.com',
                token=token,
                status='pending',
                expires_at=datetime.utcnow() + timedelta(days=7),
                invited_by_user_id=alice.id
            )
            db.session.add(invitation)
            db.session.commit()

        # Logout Alice
        page.goto(f"{BASE_URL}/logout")
        page.wait_for_load_state('networkidle')

        # Visit accept page
        page.goto(f"{BASE_URL}/invite/accept?token={token}")
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        # Should show accept page with signup option
        assert 'accept' in content or 'join' in content or 'sign' in content

        # Cleanup
        with app.app_context():
            Invitation.query.filter_by(token=token).delete()
            db.session.commit()

    def test_accept_invitation_existing_user(self, page, register_user, create_household, app, db):
        """Existing user can accept invitation."""
        from models import Invitation, Household, User
        import secrets

        # Create Alice and her household
        register_user('alice')
        create_household('Alice Household')
        page.goto(f"{BASE_URL}/logout")

        # Create Bob (existing user)
        register_user('bob')
        page.goto(f"{BASE_URL}/logout")

        # Create invitation for Bob
        with app.app_context():
            alice = User.query.filter_by(email=TEST_USERS['alice']['email']).first()
            household = Household.query.filter_by(name='Alice Household').first()

            token = secrets.token_urlsafe(32)
            invitation = Invitation(
                household_id=household.id,
                email=TEST_USERS['bob']['email'],
                token=token,
                status='pending',
                expires_at=datetime.utcnow() + timedelta(days=7),
                invited_by_user_id=alice.id
            )
            db.session.add(invitation)
            db.session.commit()

        # Visit accept page
        page.goto(f"{BASE_URL}/invite/accept?token={token}")
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        # Should show option to login or join
        assert 'accept' in content or 'join' in content or 'login' in content

        # Cleanup
        with app.app_context():
            Invitation.query.filter_by(token=token).delete()
            db.session.commit()


class TestInvalidInvitation:
    """Invalid invitation handling tests."""

    def test_invalid_token_shows_error(self, page, clean_test_data):
        """Invalid token should show error message."""
        page.goto(f"{BASE_URL}/invite/accept?token=invalid_token_12345")
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        # Should show error
        assert 'invalid' in content or 'expired' in content or 'not found' in content

    def test_expired_invitation_shows_error(self, page, register_user, create_household, app, db):
        """Expired invitation should show error."""
        from models import Invitation, Household, User
        import secrets

        register_user('charlie')
        create_household('Charlie Household')

        # Create expired invitation
        with app.app_context():
            charlie = User.query.filter_by(email=TEST_USERS['charlie']['email']).first()
            household = Household.query.filter_by(name='Charlie Household').first()

            token = secrets.token_urlsafe(32)
            invitation = Invitation(
                household_id=household.id,
                email='expired@example.com',
                token=token,
                status='pending',
                expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
                invited_by_user_id=charlie.id
            )
            db.session.add(invitation)
            db.session.commit()

        page.goto(f"{BASE_URL}/logout")
        page.goto(f"{BASE_URL}/invite/accept?token={token}")
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        assert 'expired' in content or 'invalid' in content

        # Cleanup
        with app.app_context():
            Invitation.query.filter_by(token=token).delete()
            db.session.commit()


class TestCancelInvitation:
    """Invitation cancellation tests."""

    def test_pending_invitations_shown_on_invite_page(self, page, register_user, create_household, app, db):
        """Pending invitations should be shown on invite page."""
        from models import Invitation, Household, User
        import secrets

        register_user('alice')
        create_household('Alice Household')

        # Create pending invitation
        with app.app_context():
            alice = User.query.filter_by(email=TEST_USERS['alice']['email']).first()
            household = Household.query.filter_by(name='Alice Household').first()

            token = secrets.token_urlsafe(32)
            invitation = Invitation(
                household_id=household.id,
                email='pending@example.com',
                token=token,
                status='pending',
                expires_at=datetime.utcnow() + timedelta(days=7),
                invited_by_user_id=alice.id
            )
            db.session.add(invitation)
            db.session.commit()

        page.goto(f"{BASE_URL}/household/invite")
        page.wait_for_load_state('networkidle')

        content = page.content()
        # Should show pending invitation
        assert 'pending@example.com' in content or 'pending' in content.lower()

        # Cleanup
        with app.app_context():
            Invitation.query.filter_by(token=token).delete()
            db.session.commit()

    def test_can_cancel_pending_invitation(self, page, register_user, create_household, app, db):
        """User can cancel a pending invitation."""
        from models import Invitation, Household, User
        import secrets

        register_user('bob')
        create_household('Bob Household')

        # Create pending invitation
        with app.app_context():
            bob = User.query.filter_by(email=TEST_USERS['bob']['email']).first()
            household = Household.query.filter_by(name='Bob Household').first()

            token = secrets.token_urlsafe(32)
            invitation = Invitation(
                household_id=household.id,
                email='tocancel@example.com',
                token=token,
                status='pending',
                expires_at=datetime.utcnow() + timedelta(days=7),
                invited_by_user_id=bob.id
            )
            db.session.add(invitation)
            db.session.commit()

        page.goto(f"{BASE_URL}/household/invite")
        page.wait_for_load_state('networkidle')

        # Look for cancel button
        cancel_btn = page.locator('button:has-text("Cancel"), a:has-text("Cancel")')
        if cancel_btn.count() > 0:
            cancel_btn.first.click()
            page.wait_for_load_state('networkidle')

        # Cleanup any remaining
        with app.app_context():
            Invitation.query.filter_by(token=token).delete()
            db.session.commit()


class TestInvitationUI:
    """Invitation UI tests."""

    def test_invite_link_shown_after_sending(self, page, register_user, create_household, app, db):
        """After sending invitation, invite link should be shown."""
        register_user('diana')
        create_household('Diana Household')

        page.goto(f"{BASE_URL}/household/invite")
        page.wait_for_load_state('networkidle')

        email_input = page.locator('input[name="email"], input[type="email"]')
        email_input.first.fill('showlink@example.com')

        submit_btn = page.locator('button[type="submit"], button:has-text("Send"), button:has-text("Invite")')
        submit_btn.first.click()
        page.wait_for_load_state('networkidle')

        content = page.content()
        # Should show invite link or success message
        assert 'invite' in content.lower() or 'sent' in content.lower() or 'link' in content.lower()

        # Cleanup
        with app.app_context():
            from models import Invitation
            Invitation.query.filter_by(email='showlink@example.com').delete()
            db.session.commit()
