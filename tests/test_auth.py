"""
E2E tests for authentication flows.
Tests registration, login, logout, and session persistence.
"""
import pytest
from conftest import BASE_URL, TEST_USERS


pytestmark = pytest.mark.integration


class TestRegistration:
    """User registration tests."""

    def test_register_new_user_success(self, page, clean_test_data):
        """New user can register with valid credentials."""
        user = TEST_USERS['alice']
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Should redirect away from register page (to household setup or index)
        assert '/register' not in page.url

    def test_register_duplicate_email_rejected(self, page, register_user, logout):
        """Registration with existing email shows error."""
        register_user('alice')
        logout()

        user = TEST_USERS['alice']
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="name"]', 'Another Name')
        page.fill('input[name="email"]', user['email'])  # Same email
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Should stay on register page with error
        content = page.content().lower()
        assert 'already' in content or 'exists' in content or '/register' in page.url

    def test_register_password_too_short_rejected(self, page, clean_test_data):
        """Password under 8 characters shows error."""
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="name"]', 'Test User')
        page.fill('input[name="email"]', 'short@example.com')
        page.fill('input[name="password"]', 'short')
        page.fill('input[name="confirm_password"]', 'short')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        assert '8 character' in content or 'too short' in content or '/register' in page.url

    def test_register_password_mismatch_rejected(self, page, clean_test_data):
        """Mismatched passwords show error."""
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="name"]', 'Test User')
        page.fill('input[name="email"]', 'mismatch@example.com')
        page.fill('input[name="password"]', 'password123')
        page.fill('input[name="confirm_password"]', 'differentpassword')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        assert 'match' in content or 'mismatch' in content or '/register' in page.url

    def test_register_missing_fields_rejected(self, page, clean_test_data):
        """Missing required fields shows error."""
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')

        # Submit with only email filled
        page.fill('input[name="email"]', 'incomplete@example.com')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Should stay on register page
        assert '/register' in page.url


class TestLogin:
    """User login tests."""

    def test_login_valid_credentials_success(self, page, clean_test_data):
        """User can login with correct credentials."""
        user = TEST_USERS['alice']

        # First register the user
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Logout
        page.goto(f"{BASE_URL}/logout")
        page.wait_for_load_state('networkidle')

        # Now login
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Should redirect away from login page
        assert '/login' not in page.url

    def test_login_invalid_password_rejected(self, page, clean_test_data):
        """Invalid password shows error."""
        user = TEST_USERS['bob']

        # First register the user
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Logout
        page.goto(f"{BASE_URL}/logout")
        page.wait_for_load_state('networkidle')

        # Try login with wrong password
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', 'wrongpassword')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        assert 'invalid' in content or 'incorrect' in content or '/login' in page.url

    def test_login_nonexistent_user_rejected(self, page, clean_test_data):
        """Login with non-existent email shows error."""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="email"]', 'nonexistent@example.com')
        page.fill('input[name="password"]', 'password123')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        assert 'invalid' in content or 'incorrect' in content or '/login' in page.url

    def test_login_remember_me_checkbox(self, page, clean_test_data):
        """Remember me checkbox is present and functional."""
        user = TEST_USERS['charlie']

        # Register user
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Logout
        page.goto(f"{BASE_URL}/logout")
        page.wait_for_load_state('networkidle')

        # Login with remember me
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state('networkidle')

        # Check remember me checkbox exists
        remember_checkbox = page.locator('input[name="remember"], input[type="checkbox"]')
        assert remember_checkbox.count() > 0

        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        remember_checkbox.first.check()
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        assert '/login' not in page.url


class TestLogout:
    """Logout tests."""

    def test_logout_success(self, page, clean_test_data):
        """Logged in user can logout."""
        user = TEST_USERS['alice']

        # Register and create household
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Create household
        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', 'Test Household')
        display_input = page.locator('input[name="display_name"]')
        if display_input.count() > 0 and not display_input.input_value():
            display_input.fill('Alice')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Logout
        page.goto(f"{BASE_URL}/logout")
        page.wait_for_load_state('networkidle')

        # Should redirect to login page
        assert '/login' in page.url

    def test_logout_clears_session(self, page, clean_test_data):
        """After logout, accessing protected routes redirects to login."""
        user = TEST_USERS['bob']

        # Register
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Create household
        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', 'Test Household')
        display_input = page.locator('input[name="display_name"]')
        if display_input.count() > 0 and not display_input.input_value():
            display_input.fill('Bob')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Logout
        page.goto(f"{BASE_URL}/logout")
        page.wait_for_load_state('networkidle')

        # Try to access protected route
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        # Should redirect to login
        assert '/login' in page.url


class TestProtectedRoutes:
    """Tests for protected route access."""

    def test_unauthenticated_redirects_to_login(self, page, clean_test_data):
        """Unauthenticated access to protected routes redirects to login."""
        protected_routes = ['/', '/reconciliation', '/household/settings', '/household/invite']

        for route in protected_routes:
            page.goto(f"{BASE_URL}{route}")
            page.wait_for_load_state('networkidle')

            assert '/login' in page.url, f"Route {route} should redirect to login"

    def test_authenticated_can_access_protected(self, page, clean_test_data):
        """Authenticated user with household can access protected routes."""
        user = TEST_USERS['charlie']

        # Register
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Create household
        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', 'Test Household')
        display_input = page.locator('input[name="display_name"]')
        if display_input.count() > 0 and not display_input.input_value():
            display_input.fill('Charlie')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        assert '/login' not in page.url


class TestSessionPersistence:
    """Session management tests."""

    def test_session_persists_across_pages(self, page, clean_test_data):
        """User remains logged in across page navigation."""
        user = TEST_USERS['diana']

        # Register
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Create household
        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', 'Test Household')
        display_input = page.locator('input[name="display_name"]')
        if display_input.count() > 0 and not display_input.input_value():
            display_input.fill('Diana')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Navigate to index
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')
        assert '/login' not in page.url

        # Navigate to reconciliation
        page.goto(f"{BASE_URL}/reconciliation")
        page.wait_for_load_state('networkidle')
        assert '/login' not in page.url

        # Navigate to settings
        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')
        assert '/login' not in page.url

    def test_session_persists_on_refresh(self, page, clean_test_data):
        """User remains logged in after page refresh."""
        user = TEST_USERS['alice']

        # Register
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', user['name'])
        page.fill('input[name="email"]', user['email'])
        page.fill('input[name="password"]', user['password'])
        page.fill('input[name="confirm_password"]', user['password'])
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Create household
        page.goto(f"{BASE_URL}/household/create")
        page.wait_for_load_state('networkidle')
        page.fill('input[name="name"]', 'Test Household')
        display_input = page.locator('input[name="display_name"]')
        if display_input.count() > 0 and not display_input.input_value():
            display_input.fill('Alice')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')
        assert '/login' not in page.url

        # Refresh page
        page.reload()
        page.wait_for_load_state('networkidle')
        assert '/login' not in page.url


class TestLoginPageUI:
    """Tests for login page UI elements."""

    def test_login_page_has_register_link(self, page, clean_test_data):
        """Login page should have link to registration."""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state('networkidle')

        register_link = page.locator('a[href*="register"]')
        assert register_link.count() > 0

    def test_register_page_has_login_link(self, page, clean_test_data):
        """Registration page should have link to login."""
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state('networkidle')

        login_link = page.locator('a[href*="login"]')
        assert login_link.count() > 0
