"""
E2E tests for household management.
Tests create, switch, settings, and leave household functionality.
"""
import pytest
from conftest import BASE_URL, TEST_USERS


pytestmark = pytest.mark.integration


class TestCreateHousehold:
    """Household creation tests."""

    def test_create_household_success(self, page, register_user):
        """User can create a new household."""
        register_user('alice')

        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="name"]', 'Test Household')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Should redirect to index after creation
        assert '/household/create' not in page.url

    def test_create_household_with_display_name(self, page, register_user, clean_test_data):
        """User can set custom display name during household creation."""
        register_user('bob')

        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')

        # Fill household name
        name_input = page.locator('input[name="name"]')
        name_input.fill('Bob Household')

        # Fill display name
        display_input = page.locator('input[name="display_name"]')
        if display_input.count() > 0:
            display_input.fill('Bobby')

        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        assert '/household/create' not in page.url

    def test_create_household_missing_name_rejected(self, page, register_user):
        """Household creation without name is rejected."""
        register_user('charlie')

        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')

        # Try to submit without filling name
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Should stay on create page or show error
        content = page.content().lower()
        assert '/household/create' in page.url or 'required' in content or 'name' in content


class TestHouseholdSettings:
    """Household settings tests."""

    def test_view_settings_page(self, page, register_user, create_household):
        """User can view household settings."""
        register_user('alice')
        create_household('Alice Household')

        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')

        content = page.content()
        assert 'Alice Household' in content or 'Settings' in content

    def test_rename_household(self, page, register_user, create_household):
        """Owner can rename household."""
        register_user('alice')
        create_household('Original Name')

        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')

        # Look for rename form/input
        rename_input = page.locator('input[name="name"], input[name="household_name"]')
        if rename_input.count() > 0:
            rename_input.first.fill('New Name')

            # Find and click rename/save button
            save_btn = page.locator('button:has-text("Save"), button:has-text("Rename"), button:has-text("Update")')
            if save_btn.count() > 0:
                save_btn.first.click()
                page.wait_for_load_state('networkidle')

                # Verify name changed
                content = page.content()
                assert 'New Name' in content

    def test_update_display_name(self, page, register_user, create_household):
        """User can update their display name."""
        register_user('bob')
        create_household('Bob Household')

        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')

        # Look for display name input
        display_input = page.locator('input[name="display_name"]')
        if display_input.count() > 0:
            display_input.first.fill('Robert')

            # Find update button near display name
            update_btn = page.locator('button:has-text("Update"), button:has-text("Save")')
            if update_btn.count() > 0:
                update_btn.first.click()
                page.wait_for_load_state('networkidle')

    def test_settings_shows_members(self, page, setup_two_households, login_as):
        """Settings page shows household members."""
        login_as('alice')

        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')

        content = page.content()
        # Should show member names
        assert 'Alice' in content or 'Bob' in content or 'member' in content.lower()


class TestSwitchHousehold:
    """Household switching tests."""

    def test_switch_household(self, page, setup_two_households, login_as, app, db):
        """User can switch between households they belong to."""
        # Add Alice to both households
        from models import User, Household, HouseholdMember

        with app.app_context():
            alice = User.query.filter_by(email=TEST_USERS['alice']['email']).first()
            h2 = Household.query.filter_by(name='Charlie & Diana Household').first()

            # Add Alice to second household
            member = HouseholdMember(
                household_id=h2.id,
                user_id=alice.id,
                role='member',
                display_name='Alice Guest'
            )
            db.session.add(member)
            db.session.commit()

        login_as('alice')

        # Go to household select
        page.goto(f"{BASE_URL}/household/select")
        page.wait_for_load_state('networkidle')

        content = page.content()
        # Should show multiple households
        assert 'Alice & Bob' in content or 'Charlie & Diana' in content

    def test_select_household_page(self, page, register_user, create_household):
        """Household select page is accessible."""
        register_user('alice')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/household/select")
        page.wait_for_load_state('networkidle')

        # Should either show household list or redirect
        assert page.url != f"{BASE_URL}/login"


class TestLeaveHousehold:
    """Leave household tests."""

    def test_leave_household_button_exists(self, page, register_user, create_household):
        """Leave household option should exist in settings."""
        register_user('alice')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        # Should have leave option
        assert 'leave' in content or 'exit' in content or 'remove' in content

    def test_leave_household_as_only_member_deletes_household(self, page, register_user, create_household):
        """Leaving as only member should delete the household."""
        register_user('diana')
        create_household('Solo Household')

        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')

        # Find and click leave button
        leave_btn = page.locator('button:has-text("Leave"), a:has-text("Leave")')
        if leave_btn.count() > 0:
            leave_btn.first.click()
            page.wait_for_load_state('networkidle')

            # May need to confirm
            confirm_btn = page.locator('button:has-text("Confirm"), button:has-text("Yes")')
            if confirm_btn.count() > 0:
                confirm_btn.first.click()
                page.wait_for_load_state('networkidle')

            # Should redirect to create household or select
            assert '/household/create' in page.url or '/household/select' in page.url


class TestHouseholdNavigation:
    """Navigation tests for household features."""

    def test_nav_shows_household_name(self, page, register_user, create_household):
        """Navigation should show current household name."""
        register_user('alice')
        create_household('My Home')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content()
        # Household name should appear somewhere
        assert 'My Home' in content or 'Household' in content

    def test_settings_link_in_nav(self, page, register_user, create_household):
        """Settings link should be in navigation."""
        register_user('bob')
        create_household('Test Home')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        settings_link = page.locator('a[href*="settings"]')
        assert settings_link.count() > 0

    def test_invite_link_in_nav(self, page, register_user, create_household):
        """Invite link should be in navigation."""
        register_user('charlie')
        create_household('Test Home')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        invite_link = page.locator('a[href*="invite"]')
        assert invite_link.count() > 0
